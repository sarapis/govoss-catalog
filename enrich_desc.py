#!/usr/bin/env python3
"""Fill missing descriptions from the GitHub API, where upstream actually has one.

Runs AFTER harvest.py and BEFORE merge_translations.py — recovered text is often
not English (Swedish repos describe themselves in Swedish), so it has to reach
the translation step like any other source string.

Why this exists: 318 active entries had no description at all, and sampling
showed the reason differs by source. iMio, OS2 and ARTE genuinely have none — 12
of 12 sampled were empty on GitHub too, which is why filters.py must NOT treat a
missing description as evidence something is not software (that rule was removed
once already, after it hid Products.PloneMeeting). Offentligkod is different: it
is ingested from a recutils file in git that carries no description field, while
the repos it points at do have one — Alaveteli, Apache Camel and BasicUse all had
text we were not showing.

So this is source-agnostic on purpose: it asks about any entry that has a GitHub
repo and no description, and simply finds nothing for the sources that have
nothing.

Provenance: a recovered description is marked `desc_from: "github-api"`, so it is
never confused with one the catalogue itself published — the same rule as
translated vs desc_en, and inferred vs source categories.

Best effort. Unauthenticated GitHub allows 60 requests an hour, which is not
enough for the candidate set, so set GITHUB_TOKEN. Without it this step fills
what it can, says so, and exits 0 — it must never fail a gated run.
"""
import datetime, json, os, re, ssl, time, urllib.request, urllib.error, importlib.util
import certifi

OUT = os.path.dirname(os.path.abspath(__file__))
CACHE = f"{OUT}/out/gh_desc.json"
CTX = ssl.create_default_context(cafile=certifi.where())

_h = importlib.util.spec_from_file_location("harvest", f"{OUT}/harvest.py")


def _gh_token():
    """liveness.gh_token(): GITHUB_TOKEN, then a chmod-600 file, then `gh`.

    Imported, not copied. This step read GITHUB_TOKEN alone until 2026-08-14 —
    never set under launchd — so every scheduled run got 60 requests/hour
    against 251 candidates, about 31 weeks to converge, while liveness.py had
    been resolving a token via `gh` the whole time. Two copies of a rule are two
    rules; that is why sources.py and theme.py exist.

    Safe to import: liveness.py guards its entry point with __name__, so nothing
    runs. (harvest.py does NOT, which is why detect_lang below is loaded through
    importlib instead — the two are not interchangeable.)
    """
    import liveness
    return liveness.gh_token()


def _detect_lang(text):
    """harvest.detect_lang, loaded lazily: importing harvest executes its module
    body, so only pay that if there is something to detect."""
    global _detect
    try:
        return _detect(text)
    except NameError:
        pass
    m = importlib.util.module_from_spec(_h)
    _h.loader.exec_module(m)
    globals()["_detect"] = m.detect_lang
    return _detect(text)


def slug(repo_url):
    m = re.search(r"github\.com/([^/]+)/([^/#?]+)", repo_url or "")
    if not m:
        return None
    return f"{m.group(1)}/{re.sub(r'\.git$', '', m.group(2))}"


EMPTY_TTL_DAYS = 30


def http_outcome(code, headers):
    """What a GitHub API error means for the cache (review 2026-11-10, M14):
      "gone"  - 404/410: the repo is gone; cache "" (no description to fetch).
      "stop"  - a RATE limit: 429, or 403 with X-RateLimit-Remaining: 0 or a
                Retry-After. Stop, keep what we have.
      "retry" - anything else (401 expired token, 5xx, a permission 403): NOT
                evidence of an empty description; ask again next run. These
                used to be cached as "" forever, and any 403 stopped the run
                while the log said "rate limited"."""
    headers = headers or {}
    if code in (404, 410):
        return "gone"
    if code == 429 or (code == 403 and (str(headers.get("X-RateLimit-Remaining")) == "0"
                                        or headers.get("Retry-After"))):
        return "stop"
    return "retry"


def stale_empty(cache, s, today):
    """A cached "" is re-asked after EMPTY_TTL_DAYS (a description can be added
    later; and entries cached before 2026-11 may be failures, not empties).
    Undated "" is stale."""
    if cache.get(s) != "":
        return False
    at = (cache.get("_empty_checked") or {}).get(s)
    try:
        return (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(at)).days \
            >= EMPTY_TTL_DAYS
    except (TypeError, ValueError):
        return True


def main():
    catalog = json.load(open(f"{OUT}/catalog.json"))
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    today = datetime.date.today().isoformat()
    checked = cache.setdefault("_empty_checked", {})

    todo = []
    for r in catalog:
        if (r.get("short_desc") or "").strip():
            continue
        s = slug(r.get("repo"))
        if s:
            todo.append((s, r))
    want = sorted({s for s, _ in todo if s not in cache or stale_empty(cache, s, today)})
    print(f"{len(todo)} entries with a GitHub repo and no description; "
          f"{len(want)} not yet cached")

    hdr = {"User-Agent": "govoss-catalog/0.2", "Accept": "application/vnd.github+json"}
    tok = _gh_token()
    if tok:
        hdr["Authorization"] = "Bearer " + tok
    else:
        print("   no GitHub token (GITHUB_TOKEN / ~/.config/govoss/github-token / "
              "gh auth token) — capped at 60 requests/hour, will fill what it can")

    asked = stopped = 0
    for s in want:
        try:
            req = urllib.request.Request(f"https://api.github.com/repos/{s}", headers=hdr)
            with urllib.request.urlopen(req, timeout=25, context=CTX) as resp:
                cache[s] = (json.load(resp).get("description") or "").strip()
            if cache[s] == "":
                checked[s] = today
            asked += 1
        except urllib.error.HTTPError as ex:
            what = http_outcome(ex.code, ex.headers)
            if what == "stop":                  # rate limited — stop, keep what we have
                stopped = 1
                print(f"   rate limited after {asked} requests; "
                      f"{len(want) - asked} left for the next run")
                break
            if what == "gone":
                cache[s] = ""                   # 404/410: repo gone, nothing to fetch
                checked[s] = today
            # "retry": not cached, asked again next run
        except Exception:
            pass                                # transient: retry next run, do not cache
        time.sleep(0.05)

    os.makedirs(f"{OUT}/out", exist_ok=True)
    json.dump(cache, open(CACHE, "w"), indent=1, sort_keys=True, ensure_ascii=False)

    filled = 0
    langs = {}
    for s, r in todo:
        d = (cache.get(s) or "").strip()
        if not d:
            continue
        r["short_desc"] = d
        r["desc_from"] = "github-api"
        lang = _detect_lang(d)
        r["desc_lang"] = lang
        langs[lang] = langs.get(lang, 0) + 1
        filled += 1

    json.dump(catalog, open(f"{OUT}/catalog.json", "w"), indent=1, default=str)
    still = sum(1 for r in catalog
                if not (r.get("short_desc") or "").strip() and not r.get("excluded"))
    print(f"filled {filled} descriptions from GitHub {langs or ''}; "
          f"{still} active entries still have none"
          + (" (rate limited, rerun to continue)" if stopped else ""))


if __name__ == "__main__":
    main()
