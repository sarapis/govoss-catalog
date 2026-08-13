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
import json, os, re, ssl, time, urllib.request, urllib.error, importlib.util
import certifi

OUT = os.path.dirname(os.path.abspath(__file__))
CACHE = f"{OUT}/out/gh_desc.json"
CTX = ssl.create_default_context(cafile=certifi.where())

_h = importlib.util.spec_from_file_location("harvest", f"{OUT}/harvest.py")


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


def main():
    catalog = json.load(open(f"{OUT}/catalog.json"))
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}

    todo = []
    for r in catalog:
        if (r.get("short_desc") or "").strip():
            continue
        s = slug(r.get("repo"))
        if s:
            todo.append((s, r))
    want = sorted({s for s, _ in todo if s not in cache})
    print(f"{len(todo)} entries with a GitHub repo and no description; "
          f"{len(want)} not yet cached")

    hdr = {"User-Agent": "govoss-catalog/0.2", "Accept": "application/vnd.github+json"}
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        hdr["Authorization"] = "Bearer " + tok
    else:
        print("   no GITHUB_TOKEN — capped at 60 requests/hour, will fill what it can")

    asked = stopped = 0
    for s in want:
        try:
            req = urllib.request.Request(f"https://api.github.com/repos/{s}", headers=hdr)
            with urllib.request.urlopen(req, timeout=25, context=CTX) as resp:
                cache[s] = (json.load(resp).get("description") or "").strip()
            asked += 1
        except urllib.error.HTTPError as ex:
            if ex.code in (403, 429):          # rate limited — stop, keep what we have
                stopped = 1
                print(f"   rate limited after {asked} requests; "
                      f"{len(want) - asked} left for the next run")
                break
            cache[s] = ""                       # 404/410: repo gone, nothing to fetch
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
