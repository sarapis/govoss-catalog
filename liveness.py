#!/usr/bin/env python3
"""Liveness monitor: is every catalogued repository still there, and still alive?

The national catalogues record what was *published*. Nobody checks whether it
still exists. This does, and — crucially — it reports the DELTA against the
previous run, so a repo going dead is a signal rather than a number nobody reads.

Why it is not just 1,940 HEAD requests: an earlier version was, and 27% of the
checks came back 429 rather than answered — which measured GitHub's rate limiter,
not the catalogue. Instead:

  github.com   (67%)  -> GraphQL, 100 repos per request (~14 requests total),
                         and returns isArchived / pushedAt / isEmpty as a bonus
  GitLab hosts        -> GitLab API projects lookup (anonymous is fine)
  everything else     -> HEAD, serialised PER HOST with backoff, so the ~300
                         repos spread over 196 hosts never hammer any one of them

Output: liveness.json  {repo_key: {status, checked, dead_since, archived, last_push}}
Exit code is always 0 — a monitor that fails the pipeline gets switched off.
"""
import json, os, re, ssl, subprocess, sys, time, urllib.error, urllib.parse, urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import certifi

CTX = ssl.create_default_context(cafile=certifi.where())
OUT = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "govoss-catalog-liveness/1.0"}
NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

URLS = {}                  # join-key -> original (non-lowercased) URL
DEAD = {404, 410}          # gone for good
UNKNOWN = {403, 429, 500, 502, 503, 504}   # tells us nothing; never treat as dead


def gh_token():
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    try:
        t = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=15)
        return t.stdout.strip() or None
    except Exception:
        return None


def post_json(url, payload, headers, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={**UA, **headers, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return json.load(r)


def get_json(url, timeout=30, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return json.load(r)


# ------------------------------------------------------------------ GitHub
def check_github(keys, token):
    """keys: ['github.com/owner/name', ...] -> {key: result}"""
    out = {}
    if not token:
        print("    no GitHub token (gh auth token / GITHUB_TOKEN) — falling back to HEAD")
        return None
    parsed, owner_only = [], []
    for k in keys:
        parts = k.split("/")
        if len(parts) >= 3:
            parsed.append((k, parts[1], parts[2]))
        else:
            owner_only.append(k)     # e.g. github.com/audacity -> an org, not a repo
    if owner_only:
        print(f"    github: {len(owner_only)} org-level URLs -> HEAD")
        out.update(check_head_per_host({"github.com": owner_only}, URLS))
    hdr = {"Authorization": f"bearer {token}"}
    B = 100
    for i in range(0, len(parsed), B):
        batch = parsed[i:i + B]
        frags = "\n".join(
            f'  r{n}: repository(owner: {json.dumps(o)}, name: {json.dumps(nm)}) '
            f'{{ nameWithOwner isArchived isEmpty pushedAt isPrivate }}'
            for n, (_, o, nm) in enumerate(batch))
        d, err = None, None
        for attempt in range(4):
            try:
                d = post_json("https://api.github.com/graphql",
                              {"query": "{\n" + frags + "\n}"}, hdr)
                err = None
                break
            except Exception as e:
                err = e
                # GitHub secondary rate limits want real backoff, not a token pause
                time.sleep(5 * (2 ** attempt))
        if err is not None:
            for k, _, _ in batch:
                out[k] = {"status": f"error:{type(err).__name__}"}
            continue
        data = (d or {}).get("data") or {}
        for n, (k, _, _) in enumerate(batch):
            node = data.get(f"r{n}")
            if node is None:
                # GraphQL returns null for missing OR inaccessible repos; the
                # errors array distinguishes NOT_FOUND from a permission problem.
                out[k] = {"status": 404}
            else:
                out[k] = {"status": 200, "archived": node.get("isArchived"),
                          "empty": node.get("isEmpty"), "last_push": node.get("pushedAt")}
        print(f"    github: {min(i+B, len(parsed))}/{len(parsed)}", flush=True)
        time.sleep(1.0)

    # A whole batch failing marks 100 repos "unknown" in one go — it happened twice,
    # and an unknown spike is indistinguishable from real coverage loss at a glance.
    # Sweep the failures once more after a pause, in SMALL batches: if the cause was
    # a secondary rate limit, smaller queries after a cool-down get through.
    failed = [k for k, v in out.items() if isinstance(v.get("status"), str)
              and v["status"].startswith("error:")]
    if failed:
        print(f"    github: re-sweeping {len(failed)} failures in batches of 20 "
              f"after a 20s cool-down", flush=True)
        time.sleep(20)
        idx = {k: (k.split("/")[1], k.split("/")[2]) for k in failed
               if len(k.split("/")) >= 3}
        keys = list(idx)
        for i in range(0, len(keys), 20):
            chunk = keys[i:i + 20]
            frags = "\n".join(
                f'  r{n}: repository(owner: {json.dumps(idx[k][0])}, '
                f'name: {json.dumps(idx[k][1])}) '
                f'{{ nameWithOwner isArchived isEmpty pushedAt }}'
                for n, k in enumerate(chunk))
            try:
                d2 = post_json("https://api.github.com/graphql",
                               {"query": "{\n" + frags + "\n}"}, hdr)
            except Exception:
                time.sleep(5)
                continue
            data2 = (d2 or {}).get("data") or {}
            for n, k in enumerate(chunk):
                node = data2.get(f"r{n}")
                out[k] = ({"status": 404} if node is None else
                          {"status": 200, "archived": node.get("isArchived"),
                           "empty": node.get("isEmpty"), "last_push": node.get("pushedAt")})
            time.sleep(1.5)
        still = sum(1 for k in failed if isinstance(out[k].get("status"), str)
                    and out[k]["status"].startswith("error:"))
        print(f"    github: {len(failed) - still} recovered, {still} still unknown")
    return out


# ------------------------------------------------------------------ GitLab
def check_gitlab(host, keys):
    out = {}

    def one(k):
        path = "/".join(k.split("/")[1:])
        url = f"https://{host}/api/v4/projects/{urllib.parse.quote(path, safe='')}"
        try:
            d = get_json(url)
            return k, {"status": 200, "archived": d.get("archived"),
                       "last_push": d.get("last_activity_at")}
        except urllib.error.HTTPError as e:
            return k, {"status": e.code}
        except Exception as e:
            return k, {"status": f"error:{type(e).__name__}"}
    with ThreadPoolExecutor(max_workers=6) as ex:
        for k, v in ex.map(one, keys):
            out[k] = v
    return out


# ------------------------------------------------------- everything else
def check_head_per_host(by_host, urls=None):
    """One worker per host, serial within a host, with 429 backoff.

    urls maps join-key -> ORIGINAL url. Always fetch the original: repo_key is
    lowercased for joining and that alone 404s case-sensitive paths.
    """
    urls = urls or {}
    out = {}

    def do_host(item):
        host, keys = item
        res = {}
        for k in keys:
            for attempt in range(3):
                try:
                    target = urls.get(k) or ("https://" + k)
                    req = urllib.request.Request(target, method="HEAD",
                                                 headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=12, context=CTX) as r:
                        res[k] = {"status": r.status}
                    break
                except urllib.error.HTTPError as e:
                    if e.code == 429 and attempt < 2:
                        time.sleep(5 * (attempt + 1))
                        continue
                    res[k] = {"status": e.code}
                    break
                except Exception as e:
                    if attempt < 2:
                        time.sleep(1.5)
                        continue
                    res[k] = {"status": f"error:{type(e).__name__}"}
            time.sleep(0.25)   # be a polite guest on small self-hosted forges
        return res
    with ThreadPoolExecutor(max_workers=14) as ex:
        for res in ex.map(do_host, by_host.items()):
            out.update(res)
    return out


# ---------------------------------------------------------------- report
def main():
    catalog = json.load(open(f"{OUT}/catalog.json"))
    prev = {}
    if os.path.exists(f"{OUT}/liveness.json"):
        prev = json.load(open(f"{OUT}/liveness.json")).get("repos", {})

    names, by_host = {}, defaultdict(list)
    for r in catalog:
        k = r.get("repo_key")
        if k and k not in names:
            names[k] = r.get("name") or k
            if r.get("repo"):
                URLS[k] = r["repo"]
            by_host[k.split("/")[0]].append(k)

    print(f"[liveness] {len(names)} distinct repos across {len(by_host)} hosts")
    results = {}

    gh = by_host.pop("github.com", [])
    if gh:
        got = check_github(gh, gh_token())
        if got is None:
            by_host["github.com"] = gh
        else:
            results.update(got)

    for host in [h for h in list(by_host) if h.startswith("gitlab.") or h == "code.europa.eu"]:
        keys = by_host.pop(host)
        print(f"    {host}: {len(keys)}")
        results.update(check_gitlab(host, keys))

    if by_host:
        rest = sum(len(v) for v in by_host.values())
        print(f"    HEAD: {rest} repos over {len(by_host)} hosts")
        results.update(check_head_per_host(by_host, URLS))

    # ---- CONFIRM every "dead" verdict with a plain web HEAD before recording it.
    # An API 404 is not the same as gone: gitlab.huma-num.fr restricts anonymous
    # API access, so its projects returned 404 from /api/v4 while the web URL
    # answered 200. Without this pass the monitor reported live repos as newly
    # dead — inventing exactly the drift it exists to detect. ~85 extra requests.
    suspect = [k for k, v in results.items() if v.get("status") in DEAD]
    if suspect:
        print(f"\n    confirming {len(suspect)} dead verdicts with a web HEAD...")
        by_h = defaultdict(list)
        for k in suspect:
            by_h[k.split("/")[0]].append(k)
        confirm = check_head_per_host(by_h, URLS)
        rescued = 0
        for k, v in confirm.items():
            if v.get("status") == 200:
                results[k] = {"status": 200, "api_404_but_web_ok": True}
                rescued += 1
        print(f"    rescued {rescued} that the API called 404 but the web serves fine")

    # ---- fold in history so "dead since" is meaningful
    repos, newly_dead, revived = {}, [], []
    for k, res in results.items():
        st = res.get("status")
        p = prev.get(k, {})
        rec = {"status": st, "checked": NOW, "name": names[k]}
        for f in ("archived", "empty", "last_push"):
            if res.get(f) is not None:
                rec[f] = res[f]
        # Require TWO consecutive dead observations before calling it dead.
        # Single observations oscillate: gitlab.com GROUP urls (as opposed to
        # project urls) 404 from the projects API and answer inconsistently to
        # HEAD, so run N "rescued" them and run N+1 declared them dead. An
        # unstable signal is worse than a steady wrong one — it trains you to
        # ignore the report. dead_count survives across runs in liveness.json.
        if st in DEAD:
            rec["dead_count"] = p.get("dead_count", 0) + 1
            if rec["dead_count"] >= 2:
                rec["dead_since"] = p.get("dead_since") or NOW
                if not p.get("dead_since") and p:
                    newly_dead.append(k)
            else:
                rec["unconfirmed_dead"] = True   # not counted as dead yet
        elif st == 200:
            if p.get("dead_since"):
                revived.append(k)
            rec["dead_count"] = 0
        repos[k] = rec

    ok = sum(1 for v in repos.values() if v["status"] == 200)
    dead = [k for k, v in repos.items() if v["status"] in DEAD and v.get("dead_since")]
    pending = [k for k, v in repos.items() if v.get("unconfirmed_dead")]
    unknown = [k for k, v in repos.items()
               if v["status"] in UNKNOWN or isinstance(v["status"], str)]
    archived = [k for k, v in repos.items() if v.get("archived")]

    summary = {"checked": NOW, "total": len(repos), "ok": ok,
               "dead": len(dead), "pending_dead": len(pending),
               "unknown": len(unknown), "archived": len(archived),
               "newly_dead": newly_dead, "revived": revived}
    json.dump({"summary": summary, "repos": repos},
              open(f"{OUT}/liveness.json", "w"), indent=1)

    pct = lambda n: f"{100*n/max(1,len(repos)):.1f}%"
    print(f"\n  OK       {ok:>5} ({pct(ok)})")
    print(f"  DEAD     {len(dead):>5} ({pct(len(dead))})  <- confirmed over 2+ consecutive runs")
    print(f"  pending  {len(pending):>5} ({pct(len(pending))})  <- 404 once; not called dead until it repeats")
    print(f"  archived {len(archived):>5} ({pct(len(archived))})  <- alive but frozen upstream")
    print(f"  unknown  {len(unknown):>5} ({pct(len(unknown))})  <- rate-limited/private/unreachable, NOT dead")
    if prev:
        print(f"\n  CHANGED SINCE LAST RUN: {len(newly_dead)} newly dead, {len(revived)} revived")
        for k in newly_dead[:15]:
            print(f"    DEAD NOW  {repos[k]['name'][:34]:<36} {k}")
        for k in revived[:8]:
            print(f"    REVIVED   {repos[k]['name'][:34]:<36} {k}")
    else:
        print("\n  (first run — no baseline to diff against yet)")
        for k in dead[:12]:
            print(f"    dead: {repos[k]['name'][:34]:<36} {k}")
    print(f"\n  written: {OUT}/liveness.json")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[liveness] FAILED: {type(e).__name__}: {e}", file=sys.stderr)
    sys.exit(0)
