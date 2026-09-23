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

_refuse_short_scan() is the guard multi-org adapters (os2, ch) rely on: they
swallow per-org failures, so returning their partial list would checkpoint it.

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

    for f in failed:
        print(f"FAIL  {f}")
    n = len(ran)
    print(f"\n{n - len(failed)}/{n} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
