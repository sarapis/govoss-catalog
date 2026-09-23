#!/usr/bin/env python3
"""Regression test for the crosswalk's input caches - crosswalk.cached(),
site_lookup() and cache_problems().

    python3 test_crosswalk_cache.py

Until 2026-09-23 every crosswalk input (Comptoir du Libre, Wikidata's P1324 dump,
Wikidata's P856 website matches) was reused for as long as its file existed.
comptoir.json dated from 08-11 and the Wikidata files from 08-13, six weekly
runs later, and nothing said so. Worse, the website cache stored MATCHES only,
so a homepage added after 08-13 was never asked at all.

The rules pinned here:
  * no recorded `fetched_at` is STALE, never fresh (a missing measurement is not
    a fresh one);
  * `fetched_at` advances ONLY on success, so a failure cannot make old data
    look new - the invariant cache/_fetched.json already keeps;
  * a failed fetch falls back to the old copy and records the error;
  * the website cache asks only NEW homepages while fresh, all of them once
    stale, and a failed batch keeps its old match and is retried;
  * /sources.html warns on an input older than 14 days or never refreshed, and
    says nothing on a fresh checkout.

Offline: every fetch is a fake, every file lives in a temp dir.
"""
import json
import os
import sys
import tempfile

import crosswalk as cw

NOW = "2026-09-23T07:00:00Z"
DAY = lambda d: "2026-09-%02dT07:00:00Z" % (23 - d)   # d days before NOW


class Boom(Exception):
    pass


def main():
    failed, ran = [], []

    def check(label, got, want):
        ran.append(label)          # counted, never hard-coded: a stale n reports a phantom pass
        if got != want:
            failed.append(f"{label}: expected {want!r}, got {got!r}")

    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "c.json")
    calls = []

    def ok():
        calls.append(1)
        return {"v": "new"}

    def bad():
        calls.append(1)
        raise Boom("endpoint down")

    def seed(v="old"):
        json.dump({"v": v}, open(path, "w"))

    # ---- _age_days
    check("age of a stamp", cw._age_days(DAY(3), NOW), 3.0)
    check("no stamp is None (stale), not 0", cw._age_days(None, NOW), None)
    check("garbage stamp is None", cw._age_days("last tuesday", NOW), None)

    # ---- cached(): fresh copy is reused, no fetch
    seed(); calls.clear()
    st = {"x": {"fetched_at": DAY(2), "error": None}}
    check("fresh: returns the copy", cw.cached("x", path, ok, st, NOW), {"v": "old"})
    check("fresh: no fetch", len(calls), 0)
    check("fresh: stamp unchanged", st["x"]["fetched_at"], DAY(2))

    # ---- stale copy is refreshed and the clock restarts
    seed(); calls.clear()
    st = {"x": {"fetched_at": DAY(9), "error": "old error"}}
    check("stale: returns new data", cw.cached("x", path, ok, st, NOW), {"v": "new"})
    check("stale: file rewritten", json.load(open(path)), {"v": "new"})
    check("stale: stamp advanced on success", st["x"], {"fetched_at": NOW, "error": None})

    # ---- THE AUGUST BUG: a file with no recorded stamp was reused forever
    seed(); calls.clear()
    st = {}
    check("no stamp: refreshed, not reused", cw.cached("x", path, ok, st, NOW), {"v": "new"})
    check("no stamp: fetched", len(calls), 1)

    # ---- a failed refresh falls back, records why, and does NOT advance
    seed(); calls.clear()
    st = {"x": {"fetched_at": DAY(20), "error": None}}
    check("failure: old copy returned", cw.cached("x", path, bad, st, NOW), {"v": "old"})
    check("failure: stamp NOT advanced", st["x"]["fetched_at"], DAY(20))
    check("failure: error recorded", st["x"]["error"], "Boom: endpoint down")
    check("failure: old file kept", json.load(open(path)), {"v": "old"})

    # ---- failure with nothing on disk raises, so the caller's handler decides
    os.remove(path)
    try:
        cw.cached("x", path, bad, {}, NOW)
        raised = False
    except Boom:
        raised = True
    check("failure with no copy raises", raised, True)

    # ---- site_lookup(): the asked set
    class Ask:
        def __init__(self, answers, fail=()):
            self.answers, self.fail, self.sent = answers, set(fail), []

        def batches(self, cands):
            return [[c] for c in cands]           # one site per batch, so failures isolate

        def __call__(self, batch):
            self.sent += batch
            if set(batch) & self.fail:
                raise Boom("chunk")
            return {s: {self.answers[s]} for s in batch if s in self.answers}

    old = {"asked": ["a.org", "b.org"], "found": {"a.org": ["Q1"]}}
    ask = Ask({"c.org": "Q3", "a.org": "Q1"})
    new, nf = cw.site_lookup(["a.org", "b.org", "c.org"], ask, old, fresh=True)
    check("fresh: only the NEW homepage is sent", ask.sent, ["c.org"])
    check("fresh: asked set grows", new["asked"], ["a.org", "b.org", "c.org"])
    check("fresh: old and new matches kept", new["found"], {"a.org": ["Q1"], "c.org": ["Q3"]})
    check("fresh: no failures", nf, 0)

    ask = Ask({"a.org": "Q9"})
    new, nf = cw.site_lookup(["a.org", "b.org"], ask, old, fresh=False)
    check("stale: everything is re-sent", sorted(ask.sent), ["a.org", "b.org"])
    check("stale: a changed answer replaces the old one", new["found"], {"a.org": ["Q9"]})

    ask = Ask({}, fail={"a.org"})
    new, nf = cw.site_lookup(["a.org", "b.org"], ask, old, fresh=False)
    check("failed batch: counted", nf, 1)
    check("failed batch: keeps its old match", new["found"], {"a.org": ["Q1"]})
    check("failed batch: left un-asked, so retried", new["asked"], ["b.org"])

    ask = Ask({})
    new, _ = cw.site_lookup(["b.org"], ask, old, fresh=False)
    check("stale: a homepage no longer held drops out", new["found"], {})

    # ---- p1324_rows(): the dump is accepted only when COMPLETE. The service
    # returned HTTP 200 with 11,116 of 28,759 rows on 2026-09-23.
    head = "item,r\n"
    row = lambda i: "http://www.wikidata.org/entity/Q%d,https://github.com/o/r%d\n" % (i, i)
    full = head + "".join(row(i) for i in range(1000))
    check("complete dump accepted", len(cw.p1324_rows(full, 1000)), 1000)
    check("rows parsed to [qid, url]", cw.p1324_rows(full, 1000)[0], ["Q0", "https://github.com/o/r0"])
    try:
        cw.p1324_rows(head + "".join(row(i) for i in range(390)), 1000)
        trunc = "accepted"
    except RuntimeError as ex:
        trunc = "rejected" if "390 of 1000" in str(ex) else str(ex)
    check("a truncated dump (39%, as measured) is rejected", trunc, "rejected")
    cut = full + "http://www.wikidata.org/entity/Q9999,https://git"   # half-written row
    check("a half-written last row is dropped, not stored",
          cw.p1324_rows(cut, 1000)[-1], ["Q999", "https://github.com/o/r999"])
    check("edits between COUNT and dump (<0.5%) are tolerated",
          len(cw.p1324_rows(head + "".join(row(i) for i in range(997)), 1000)), 997)

    # ---- _retry_once(): a network failure gets one more try; an HTTP answer is final
    import urllib.error
    tries = []

    def flaky():
        tries.append(1)
        if len(tries) == 1:
            raise OSError("connection reset")
        return "ok"
    check("network failure retried once, then succeeds", (cw._retry_once(flaky, pause=0), len(tries)), ("ok", 2))
    tries.clear()

    def gone():
        tries.append(1)
        raise urllib.error.HTTPError("u", 404, "Not Found", {}, None)
    check("an HTTP 404 is an answer: no retry", (cw._retry_once(gone, pause=0), len(tries)), (None, 1))
    tries.clear()

    def down():
        tries.append(1)
        raise OSError("down")
    check("two network failures give None, not a raise", (cw._retry_once(down, pause=0), len(tries)), (None, 2))

    # ---- software_qids(): one 503 used to raise out of the whole Wikidata stage.
    # Now each batch gets one retry, and a batch that still fails is UNVERIFIED:
    # its QIDs are not stamped, and the other batches' are.
    real_sparql, real_sleep = cw._sparql, cw.time.sleep
    cw.time.sleep = lambda s: None
    calls = []

    def fake(query, timeout=None):
        calls.append(query)
        if "wd:Q2 " in query + " " and len([c for c in calls if "wd:Q2 " in c + " "]) <= 2:
            raise OSError("503 Backend fetch failed")     # batch with Q2 fails twice
        if "wd:Q1 " in query + " " and len(calls) == 1:
            raise OSError("503 once")                     # batch with Q1 fails once
        ids = [w[3:] for w in query.split() if w.startswith("wd:Q") and w != "wd:Q7397"]
        return [{"item": {"value": "http://www.wikidata.org/entity/" + q}} for q in ids]
    cw._sparql = fake
    try:
        ok, unver = cw.software_qids({"Q1", "Q2", "Q3"}, chunk=1)
        raised = None
    except Exception as ex:
        ok, unver, raised = set(), set(), ex
    finally:
        cw._sparql, cw.time.sleep = real_sparql, real_sleep
    check("software_qids never raises on a failed batch", raised, None)
    check("a batch that fails ONCE is retried and verified", "Q1" in ok, True)
    check("a batch that fails twice is unverified, not stamped", (sorted(unver), "Q2" in ok), (["Q2"], False))
    check("other batches still verified", "Q3" in ok, True)

    # ---- cache_problems(): the /sources.html sensor
    good = {n: {"fetched_at": DAY(1), "error": None} for n in cw.CACHE_NAMES}
    check("all fresh: silent", cw.cache_problems(good, NOW), [])
    check("fresh checkout (no state): silent", cw.cache_problems({}, NOW), [])
    st = dict(good, wikidata_repo={"fetched_at": DAY(20), "error": "Boom: timeout"})
    p = cw.cache_problems(st, NOW)
    check("old input: one warn", [lvl for lvl, _ in p], ["warn"])
    check("old input: names it, its age and why",
          bool(p) and all(x in p[0][1] for x in ("Wikidata (repositories)", "20 days",
                                                "Boom: timeout")), True)
    st = dict(good, comptoir={"error": "Boom: down"})
    p = cw.cache_problems(st, NOW)
    check("never refreshed, state otherwise present: warns", len(p), 1)
    check("exactly at the threshold: silent",
          cw.cache_problems(dict(good, comptoir={"fetched_at": DAY(14)}), NOW), [])

    for f in failed:
        print(f"FAIL  {f}")
    n = len(ran)
    print(f"\n{n - len(failed)}/{n} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
