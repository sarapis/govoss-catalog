#!/usr/bin/env python3
"""Regression test for harvest.get()'s raise semantics and _refuse_short_scan().

    python3 test_harvest_get.py

F8 (REVIEW-govoss-catalog-2026-08-28.md) left these untested because they need a
stubbed opener. They are load-bearing for the harvest's one safety net: a source
that FAILS keeps its last good checkpoint, and a source that returns data
overwrites it. So get() must never turn a failure into data:

  * 401/403/404 raise at once - retrying a refusal or a missing page wastes the
    rate budget and changes nothing;
  * anything else (5xx, a dropped connection) is retried, then RAISED;
  * a 429 waits out the SERVER'S window (Retry-After / RateLimit-Reset) for every
    thread on that host, without spending a try; bounded, then raised (2026-10-14:
    1.5s retries burned 2,903 openCode and code.europa.eu fetches into 429s);
  * a 200 whose body is not JSON raises too - a bot-challenge page answers 200
    (the Adullact forge did), and "a responding endpoint is not a working
    source" is recurring bug 1 in CLAUDE.md;
  * it never returns None, so no adapter can mistake a failure for "no entries".

_refuse_short_scan() is the guard the multi-org adapter (os2) relies on: it
swallows per-org failures, so returning their partial list would checkpoint it.

Offline: urllib's opener and time.sleep are replaced for the duration.
"""
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
import urllib.error

_s = importlib.util.spec_from_file_location("harvest", "harvest.py")
h = importlib.util.module_from_spec(_s)
_s.loader.exec_module(h)


class Resp(io.BytesIO):
    headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def opener(script):
    """A fake urlopen playing `script` in order: bytes = a 200 body, an int = that
    HTTP status as an HTTPError, an Exception = raised as-is."""
    calls = []

    def urlopen(req, timeout=None, context=None):
        calls.append(req)
        if len(calls) > 50:                  # a retry loop with no bound fails, not hangs
            raise RuntimeError("runaway: more than 50 attempts")
        step = script[min(len(calls), len(script)) - 1]
        hdrs = {}
        if isinstance(step, tuple):          # (status or body, response headers)
            step, hdrs = step
        if isinstance(step, int):
            raise urllib.error.HTTPError(req.full_url, step, "status %d" % step, hdrs, None)
        if isinstance(step, Exception):
            raise step
        r = Resp(step)
        r.headers = hdrs
        return r
    return urlopen, calls


def main():
    failed, ran = [], []

    def check(label, got, want):
        ran.append(label)
        if got != want:
            failed.append(f"{label}: expected {want!r}, got {got!r}")

    real_open, real_sleep = h.urllib.request.urlopen, h.time.sleep
    slept = []
    h.time.sleep = slept.append

    def run(script, url="https://example.org/api", keep_hold=False, **kw):
        """-> (result or the exception's type name, number of attempts)"""
        if not keep_hold:
            h._HOLD.clear()
        del slept[:]
        fake, calls = opener(script)
        h.urllib.request.urlopen = fake
        try:
            return h.get(url, **kw), len(calls), calls
        except Exception as ex:
            return type(ex).__name__ + (":%d" % ex.code if isinstance(ex, urllib.error.HTTPError) else ""), len(calls), calls

    try:
        # ---- success
        got, n, _ = run([b'{"a": 1}'])
        check("a JSON 200 is parsed", (got, n), ({"a": 1}, 1))
        got, n, _ = run([b"raw bytes"], raw=True)
        check("raw=True returns the bytes", (got, n), (b"raw bytes", 1))

        # ---- refusals and missing pages: raise at ONCE, no retry
        for code in (401, 403, 404):
            got, n, _ = run([code, b'{"a": 1}'])
            check(f"{code} raises immediately, one attempt", (got, n), (f"HTTPError:{code}", 1))

        # ---- transient failures are retried, then raised - never None
        got, n, _ = run([503, 503, 503])
        check("503 x3 is retried, then raised", (got, n), ("HTTPError:503", 3))
        # ---- 429: wait out the server's window, shared by every thread on the host
        got, n, _ = run([(429, {"Retry-After": "30"}), b'{"ok": 1}'])
        check("429 + Retry-After waits that long (+1s), then recovers",
              (got, n, [round(x) for x in slept]), ({"ok": 1}, 2, [31]))
        reset = h.time.time() + 600
        got, n, _ = run([(429, {"RateLimit-Reset": str(int(reset))}), b"{}"])
        check("429 + GitLab RateLimit-Reset (an epoch) waits until it",
              len(slept) == 1 and 595 < slept[0] <= 602, True)
        got, n, _ = run([429, b"{}"])
        check("429 with no header waits 60s", [round(x) for x in slept], [60])
        got, n, _ = run([(429, {"Retry-After": "99999"}), b"{}"])
        check("one wait is capped at RATE_WAIT_MAX", [round(x) for x in slept], [h.RATE_WAIT_MAX])
        got, n, _ = run([429, b"{}"], tries=1)
        check("a 429 does not spend a try (tries=1 still recovers)", (got, n), ({}, 2))
        got, n, _ = run([429])
        check("429 forever is bounded, then RAISED - never None",
              (got, n), ("HTTPError:429", h.RATE_WAITS + 1))
        got, n, _ = run([(b"{}", {"RateLimit-Remaining": "0", "Retry-After": "40"})])
        run([b"{}"], keep_hold=True)
        check("Remaining: 0 on a SUCCESS holds the next call to that host",
              len(slept) == 1 and 39 < slept[0] <= 41, True)
        run([b"{}"], url="https://other.example/api", keep_hold=True)
        check("...but not a call to another host", slept, [])
        got, n, _ = run([(b"{}", {"RateLimit-Remaining": "7"})])
        run([b"{}"], keep_hold=True)
        check("Remaining > 0 holds nothing", slept, [])
        got, n, _ = run([OSError("reset"), b'{"ok": true}'])
        check("a dropped connection then a 200 recovers", (got, n), ({"ok": True}, 2))
        got, n, _ = run([502, 500, b"[]"])
        check("recovers on the last try", (got, n), ([], 3))
        got, n, _ = run([OSError("down")], tries=1)
        check("tries=1 makes exactly one attempt", (got, n), ("OSError", 1))

        # ---- THE BOT PAGE: a 200 that is not JSON must fail, not become data
        page = b"<html>Making sure you're not a bot!</html>"
        got, n, _ = run([page, page, page])
        check("a 200 HTML challenge page raises (retried first)", (got, n), ("JSONDecodeError", 3))
        got, n, _ = run([page], raw=True)
        check("...but raw=True hands the bytes back for the caller to judge", got, page)

        # ---- never None, whatever the failure
        outcomes = [run(s)[0] for s in ([404], [503] * 3, [OSError("x")] * 3, [b"nope"] * 3)]
        check("no failure mode returns None", any(o is None for o in outcomes), False)

        # ---- the User-Agent is always sent, and caller headers are merged in
        _, _, calls = run([b"{}"], headers={"Authorization": "Bearer t"})
        hdrs = {k.lower(): v for k, v in calls[0].header_items()}
        check("User-Agent sent", "user-agent" in hdrs, True)
        check("caller header merged", hdrs.get("authorization"), "Bearer t")
    finally:
        h.urllib.request.urlopen, h.time.sleep = real_open, real_sleep

    # ---- _refuse_short_scan(): raise only on failure AND shrinkage
    tmp = tempfile.mkdtemp()
    real_cache = h.CACHE
    h.CACHE = tmp
    try:
        json.dump([{}] * 10, open(os.path.join(tmp, "src_os2.json"), "w"))

        def refuse(out, broke):
            try:
                h._refuse_short_scan("os2", "OS2", out, broke, "OS2_ORGS")
                return "kept"
            except RuntimeError as ex:
                return "refused" if "10 in the last good checkpoint" in str(ex) else str(ex)
        check("no org failed: never refuses, even if smaller", refuse([{}] * 3, []), "kept")
        check("an org failed AND the scan shrank: refuses", refuse([{}] * 7, ["os2web"]), "refused")
        check("an org failed but nothing was lost: keeps", refuse([{}] * 10, ["os2web"]), "kept")
        check("an org failed and the scan GREW: keeps", refuse([{}] * 12, ["os2web"]), "kept")
        os.remove(os.path.join(tmp, "src_os2.json"))
        check("no previous checkpoint: nothing to protect, keeps", refuse([{}], ["os2web"]), "kept")
    finally:
        h.CACHE = real_cache

    # ---- ch(): the Federal Chancellery catalogue API (opensource.admin.ch)
    # Page ids: real pairs read off the live list page on 2026-09-29. A port that
    # drifts from hashUrl() gives every Swiss entry a dead deep link.
    for url, pid in (("https://github.com/agridata-ch/backend.git", "3xfy5y"),
                     ("https://github.com/opendata-swiss/ckanext-geocat.git", "t78sgz"),
                     ("https://github.com/agroscope-ch/digiRhythm.git", "d8rezf"),
                     ("https://github.com/oblique-bit/oblique-stackblitz.git", "8a5mbf")):
        check("ch_page_id(%s)" % url.rsplit("/", 1)[-1], h.ch_page_id(url), pid)

    PC = ("publiccodeYmlVersion: 0.4\nname: Loom\nurl: https://gitlab.com/swiss-armed-forces/loom\n"
          "description:\n  en:\n    shortDescription: Document search\n")
    def api_row(i, url="https://github.com/swiss-armed-forces/loom.git", pc=PC, active=True):
        return {"id": "id-%d" % i, "url": url, "aliases": [], "publiccodeYml": pc,
                "active": active, "vitality": None}
    real_get = h.get
    tmp = tempfile.mkdtemp()
    real_cache = h.CACHE
    h.CACHE = tmp
    try:
        def run_ch(rows, links=None, prev=None):
            if prev is not None:
                json.dump([{}] * prev, open(os.path.join(tmp, "src_ch.json"), "w"))
            elif os.path.exists(os.path.join(tmp, "src_ch.json")):
                os.remove(os.path.join(tmp, "src_ch.json"))
            h.get = lambda *a, **k: {"data": rows, "links": links or {"next": None}}
            try:
                return h.ch()
            except RuntimeError as ex:
                return "refused: " + str(ex)[:40]
        many = [api_row(0)] + [api_row(i, url="https://github.com/x/r%d.git" % i,
                                        pc=PC.replace("name: Loom", "name: r%d" % i)
                                              .replace("/loom", "/r%d" % i))
                               for i in range(1, 60)]
        got = run_ch(many)
        r0 = got[0] if isinstance(got, list) else {}
        check("repo comes from publiccode.yml `url`, not the API's (Loom's GitLab original)",
              r0.get("repo"), "https://gitlab.com/swiss-armed-forces/loom")
        check("entry_url deep-links the catalogue page",
              r0.get("entry_url"), h.CH_PAGE % h.ch_page_id("https://github.com/swiss-armed-forces/loom.git"))
        check("source and tier", (r0.get("source"), r0.get("tier")), ("CH/swiss", "publiccode"))
        check("an inactive row is skipped",
              len(run_ch(many + [api_row(99, url="https://github.com/x/gone.git", active=False)])), 60)
        check("a paginated answer is refused as partial",
              str(run_ch(many, links={"next": "?page[after]=x"})).startswith("refused"), True)
        check("shrinking by more than a fifth is refused",
              str(run_ch(many, prev=100)).startswith("refused"), True)
        check("a normal week against the checkpoint is kept",
              isinstance(run_ch(many, prev=62), list), True)
        check("under 50 entries is refused even with no checkpoint",
              str(run_ch(many[:10])).startswith("refused"), True)
    finally:
        h.get, h.CACHE = real_get, real_cache

    # ---- gitlab_scan(): a FAILED file fetch is not "no publiccode.yml"
    # (2026-10-07: ~110 failed fetches on openCode were read as "none" and an
    # 86-short list was published). 404/401/403 mean none; anything else counts,
    # and a failure AND a shrink against the checkpoint refuses the result.
    PCY = b"publiccodeYmlVersion: 0.4\nname: P%d\nurl: https://example.org/p%d\n"
    def gl_get(mode):
        def fake(url, **kw):
            if url.endswith("&page=1") or "page=1&" in url:
                return [{"id": i, "default_branch": "main", "web_url": "https://g/p%d" % i,
                         "http_url_to_repo": "https://g/p%d.git" % i,
                         "path_with_namespace": "g/p%d" % i} for i in range(4)]
            if "/projects?" in url:
                return []
            pid = int(url.split("/projects/")[1].split("/")[0])
            code = mode.get(pid)
            if code == "ok":
                return PCY % (pid, pid)
            if isinstance(code, int):
                raise urllib.error.HTTPError(url, code, "x", {}, io.BytesIO(b""))
            raise TimeoutError("slow")
        return fake
    tmp = tempfile.mkdtemp()
    real_get, real_cache = h.get, h.CACHE
    h.CACHE = tmp
    try:
        def scan(mode, prev=None):
            ck = os.path.join(tmp, "src_gl.json")
            if prev is not None:
                json.dump([{}] * prev, open(ck, "w"))
            elif os.path.exists(ck):
                os.remove(ck)
            h.get = gl_get(mode)
            try:
                return len(h.gitlab_scan("https://g", "X/g", "XX", key="gl")[0])
            except RuntimeError as ex:
                return "refused"
        check("404/403 mean 'no publiccode.yml', never a failure",
              scan({0: "ok", 1: 404, 2: 403, 3: "ok"}, prev=4), 2)
        check("a 429 that shrinks the list is refused",
              scan({0: "ok", 1: 429, 2: "ok", 3: "ok"}, prev=4), "refused")
        check("a timeout that shrinks the list is refused",
              scan({0: "ok", 1: "slow", 2: "ok", 3: "ok"}, prev=4), "refused")
        check("a failure with nothing lost is kept",
              scan({0: "ok", 1: 500, 2: "ok", 3: "ok"}, prev=3), 3)
        check("a failure with no checkpoint to protect is kept",
              scan({0: "ok", 1: 500, 2: "ok", 3: "ok"}), 3)
    finally:
        h.get, h.CACHE = real_get, real_cache

    # ---- github_org_scan() and nl_forgejo(): the same rule, which had reached
    # only gitlab_scan (review 2026-11-10, M8). A failed publiccode.yml fetch
    # used to downgrade the repo to index tier silently (GitHub, Forgejo).
    def gh_get(mode):
        def fake(url, **kw):
            if "/orgs/o/repos" in url:
                return ([{"name": "r%d" % i, "full_name": "o/r%d" % i, "html_url": "https://github.com/o/r%d" % i,
                          "description": "d", "default_branch": "main"} for i in range(4)]
                        if url.endswith("page=1") else [])
            if "/repos/search" in url:
                return ({"data": [{"name": "r%d" % i, "full_name": "o/r%d" % i,
                                   "html_url": "https://code.overheid.nl/o/r%d" % i,
                                   "description": "d", "default_branch": "main"} for i in range(4)]}
                        if url.endswith("page=1") else {"data": []})
            i = int(re.search(r"/r(\d)/", url).group(1))
            code = mode.get(i)
            if code == "ok":
                return PCY % (i, i)
            if isinstance(code, int):
                raise urllib.error.HTTPError(url, code, "x", {}, io.BytesIO(b""))
            raise TimeoutError("slow")
        return fake
    tmp = tempfile.mkdtemp()
    real_get, real_cache = h.get, h.CACHE
    h.CACHE = tmp
    try:
        def scan2(fn, key, mode, prev=None):
            ck = os.path.join(tmp, "src_%s.json" % key)
            if prev is not None:
                json.dump([{}] * prev, open(ck, "w"))
            elif os.path.exists(ck):
                os.remove(ck)
            h.get = gh_get(mode)
            try:
                out = fn()
                out = out[0] if isinstance(out, tuple) else out
                return (len(out), sum(1 for r in out if r["tier"] == "publiccode"))
            except RuntimeError:
                return "refused"
        for label, fn, key in (("github_org_scan", lambda: h.github_org_scan("o", "X/o", "XX", key="gho"), "gho"),
                               ("nl_forgejo", h.nl_forgejo, "nl")):
            check(f"{label}: 404 means no publiccode.yml (index tier), never a failure",
                  scan2(fn, key, {0: "ok", 1: 404, 2: "ok", 3: "ok"}, prev=4), (4, 3))
            check(f"{label}: a timeout is NOT 'none' - never downgraded to index tier",
                  scan2(fn, key, {0: "ok", 1: "slow", 2: "ok", 3: "ok"}), (3, 3))
            check(f"{label}: a 500 that shrinks the list is refused",
                  scan2(fn, key, {0: "ok", 1: 500, 2: "ok", 3: "ok"}, prev=4), "refused")
        fails = []
        h.get = gh_get({0: "ok", 1: 503, 2: "ok", 3: "ok"})
        h.github_org_scan("o", "X/o", "XX", failures=fails)
        check("github_org_scan: failures= collects the failed fetches (os2 refuses on them)",
              fails, ["o: 503"])
    finally:
        h.get, h.CACHE = real_get, real_cache

    # ---- from_publiccode(): someone else's file is coerced, never raised on (M1).
    # One malformed publiccode.yml used to fail its whole source, and an integer
    # name passed harvest and crashed four later stages on .strip().
    base = {"name": "X", "url": "https://example.org/x",
            "description": {"it": {"shortDescription": "ciao"}}}
    for label, extra in (("legal: MIT", {"legal": "MIT"}),
                         ("maintenance: internal", {"maintenance": "internal"}),
                         ("description: a string", {"description": "hello"}),
                         ("description: a list", {"description": ["a"]}),
                         ("shortDescription: an int", {"description": {"en": {"shortDescription": 5}}}),
                         ("features: a string", {"description": {"en": {"shortDescription": "s", "features": "f"}}}),
                         ("contacts: a string", {"maintenance": {"contacts": "bob"}}),
                         ("categories: a string", {"categories": "cms"}),
                         ("url: a list", {"url": ["x"]})):
        try:
            r = h.from_publiccode(dict(base, **extra), "X/s", "XX")
            got = all(isinstance(r.get(k), str) for k in ("name",)) and \
                all(isinstance(r[k], str) for k in ("short_desc", "repo", "license") if r.get(k) is not None)
        except Exception as ex:
            got = "raised %s" % type(ex).__name__
        check(f"from_publiccode: {label} is coerced, not raised", got, True)
    check("parse_pc + from_publiccode: name: 2048 becomes the TEXT '2048'",
          h.from_publiccode(h.parse_pc(b"name: 2048\nurl: https://e.org/x\n"), "X/s", "XX")["name"], "2048")
    check("parse_pc: a name that is not text at all is no name", h.parse_pc(b"name: [a, b]\n"), None)
    r = h.from_publiccode({"name": " Keep Me ", "url": "https://e.org/k", "legal": {"license": "MIT"},
                           "categories": ["cms"], "description": {"en": {"shortDescription": "s",
                                                                        "features": ["a", "b"]}}}, "X/s", "XX")
    check("from_publiccode: a well-formed file is read exactly as before (name not stripped)",
          (r["name"], r["license"], r["categories"], r["short_desc"], r["features"], r["desc_lang"]),
          (" Keep Me ", "MIT", ["cms"], "s", ["a", "b"], "en"))

    # ---- enrich_desc: only a 404/410 is cached as "no description", only a real
    # rate limit stops the run, and a cached "" is re-asked once stale (M14).
    import enrich_desc as ed
    check("enrich: 404/410 gone", (ed.http_outcome(404, {}), ed.http_outcome(410, {})), ("gone", "gone"))
    check("enrich: 401 / 500 / permission 403 are retried, never cached as empty",
          [ed.http_outcome(c, {"X-RateLimit-Remaining": "4000"}) for c in (401, 500, 403)],
          ["retry"] * 3)
    check("enrich: 429, or 403 with no requests left / Retry-After, stops",
          [ed.http_outcome(429, {}), ed.http_outcome(403, {"X-RateLimit-Remaining": "0"}),
           ed.http_outcome(403, {"Retry-After": "60"})], ["stop"] * 3)
    c = {"a/b": "", "c/d": "", "e/f": "", "g/h": "text",
         "_empty_checked": {"a/b": "2026-11-01", "c/d": "2026-09-01"}}
    check("enrich: a cached '' is re-asked when stale or undated, kept when fresh",
          [ed.stale_empty(c, k, "2026-11-11") for k in ("a/b", "c/d", "e/f", "g/h")],
          [False, True, True, False])

    for f in failed:
        print(f"FAIL  {f}")
    n = len(ran)
    print(f"\n{n - len(failed)}/{n} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
