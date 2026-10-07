#!/usr/bin/env python3
"""Regression test for harvest.get()'s raise semantics and _refuse_short_scan().

    python3 test_harvest_get.py

F8 (REVIEW-govoss-catalog-2026-08-28.md) left these untested because they need a
stubbed opener. They are load-bearing for the harvest's one safety net: a source
that FAILS keeps its last good checkpoint, and a source that returns data
overwrites it. So get() must never turn a failure into data:

  * 401/403/404 raise at once - retrying a refusal or a missing page wastes the
    rate budget and changes nothing;
  * anything else (5xx, 429, a dropped connection) is retried, then RAISED;
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
import sys
import tempfile
import urllib.error

_s = importlib.util.spec_from_file_location("harvest", "harvest.py")
h = importlib.util.module_from_spec(_s)
_s.loader.exec_module(h)


class Resp(io.BytesIO):
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
        step = script[min(len(calls), len(script)) - 1]
        if isinstance(step, int):
            raise urllib.error.HTTPError(req.full_url, step, "status %d" % step, {}, None)
        if isinstance(step, Exception):
            raise step
        return Resp(step)
    return urlopen, calls


def main():
    failed, ran = [], []

    def check(label, got, want):
        ran.append(label)
        if got != want:
            failed.append(f"{label}: expected {want!r}, got {got!r}")

    real_open, real_sleep = h.urllib.request.urlopen, h.time.sleep
    h.time.sleep = lambda s: None

    def run(script, **kw):
        """-> (result or the exception's type name, number of attempts)"""
        fake, calls = opener(script)
        h.urllib.request.urlopen = fake
        try:
            return h.get("https://example.org/api", **kw), len(calls), calls
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
        got, n, _ = run([429, 429, 429])
        check("429 is load, not a refusal: retried", n, 3)
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

    for f in failed:
        print(f"FAIL  {f}")
    n = len(ran)
    print(f"\n{n - len(failed)}/{n} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
