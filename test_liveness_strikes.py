#!/usr/bin/env python3
"""Regression test for liveness.fold_history() — the two-strike state machine.

    python3 test_liveness_strikes.py

Review finding F8 named this and dedupe identity as the two pure, regression-prone
functions "one incident away" from earning a suite the way detect_lang earned its
own after five recurrences. This is that suite, written before the incident.

Every rule below exists because the monitor was wrong in a specific way first:

  * TWO consecutive dead observations before a dead verdict. Single observations
    oscillate — `gitlab.com/opentestfactory` is a GROUP url, not a project url,
    so the projects API 404s it and HEAD answers inconsistently; one run
    "rescued" it and the next declared it dead. An unstable signal is worse than
    a steady wrong one, because it trains you to ignore the report.
  * 403/429/5xx are UNKNOWN, never dead. An earlier sweep was 1,940 serial HEAD
    requests and 27% came back 429 — treating rate-limiting as death would have
    invented drift out of nothing.
  * A repo seen for the FIRST time cannot be "newly dead". `newly_dead` is a
    delta, and a delta against no previous observation is not a change.
  * A per-run timestamp never goes on a record. `checked` used to be stamped on
    all 3,005 repos, so every record differed every run: 47,563 diff lines
    against ~90 real changes.

⚠ An UNKNOWN observation RESETS dead_count, because neither branch of the state
machine runs and the new record simply carries no count. That is deliberate and
conservative — it delays a verdict rather than hurrying one — and it is asserted
below so it cannot be "fixed" into a hidden behaviour change.
"""
import sys

import liveness

NOW = "2026-09-14T07:00:00Z"
OLD = "2026-08-31T07:00:00Z"


def fold(status, prev=None, **res):
    """One repo through one sweep. Returns (record, newly_dead, revived)."""
    repos, nd, rv = liveness.fold_history(
        {"k": dict({"status": status}, **res)},
        {"k": prev} if prev is not None else {},
        {"k": "Example"}, NOW)
    return repos["k"], nd, rv


def main():
    failed, ran = [], []

    def check(label, got, want):
        ran.append(label)          # counted, never hard-coded: a stale n reports a phantom pass
        if got != want:
            failed.append(f"{label}: expected {want!r}, got {got!r}")

    # ---- first sighting of a 404: pending, never dead, never "newly" dead
    rec, nd, rv = fold(404)
    check("1st dead: dead_count", rec.get("dead_count"), 1)
    check("1st dead: unconfirmed", rec.get("unconfirmed_dead"), True)
    check("1st dead: no dead_since", rec.get("dead_since"), None)
    check("1st dead: not newly_dead", nd, [])

    # ---- second consecutive 404 on a repo we HAVE seen: dead, and newly so
    rec, nd, rv = fold(404, prev={"status": 404, "dead_count": 1,
                                  "unconfirmed_dead": True})
    check("2nd dead: dead_count", rec.get("dead_count"), 2)
    check("2nd dead: dead_since stamped now", rec.get("dead_since"), NOW)
    check("2nd dead: newly_dead", nd, ["k"])
    check("2nd dead: unconfirmed cleared", rec.get("unconfirmed_dead"), None)

    # ---- already dead, still dead: dead_since is PRESERVED, not restamped,
    # and it is not reported as newly dead a second time.
    rec, nd, rv = fold(404, prev={"status": 404, "dead_count": 2, "dead_since": OLD})
    check("still dead: dead_since preserved", rec.get("dead_since"), OLD)
    check("still dead: count keeps rising", rec.get("dead_count"), 3)
    check("still dead: not re-reported", nd, [])

    # ---- a repo whose FIRST EVER observation is its second strike cannot be
    # newly dead: `and p` guards on there being a previous record at all.
    rec, nd, rv = fold(404, prev={})
    check("no prior record: not newly_dead", nd, [])
    check("no prior record: still pending", rec.get("unconfirmed_dead"), True)

    # ---- 410 Gone counts as dead too
    rec, nd, rv = fold(410, prev={"status": 410, "dead_count": 1})
    check("410 is dead", rec.get("dead_since"), NOW)

    # ---- UNKNOWN statuses: never dead, and they reset the strike count
    for st in sorted(liveness.UNKNOWN):
        rec, nd, rv = fold(st, prev={"status": 404, "dead_count": 1})
        check(f"status {st}: no dead/pending verdict",
              bool(rec.get("dead_since") or rec.get("unconfirmed_dead")), False)
        check(f"status {st}: dead_count reset", rec.get("dead_count"), None)
    # A rate-limited sweep must not be able to kill a repo, even twice running.
    rec, nd, rv = fold(429, prev={"status": 429})
    check("429 twice: still not dead", rec.get("dead_since"), None)
    check("429 twice: nothing newly dead", nd, [])

    # A transport error arrives as a STRING, not an int — also never dead.
    rec, nd, rv = fold("URLError", prev={"status": 404, "dead_count": 1})
    check("string status: not dead", rec.get("dead_since"), None)
    check("string status: count reset", rec.get("dead_count"), None)

    # ---- revival: a 200 on something previously dead
    rec, nd, rv = fold(200, prev={"status": 404, "dead_count": 2, "dead_since": OLD})
    check("revived: reported", rv, ["k"])
    check("revived: count zeroed", rec.get("dead_count"), 0)
    check("revived: dead_since dropped", rec.get("dead_since"), None)

    # A 200 on something merely PENDING is not a revival — it never died.
    rec, nd, rv = fold(200, prev={"status": 404, "dead_count": 1,
                                  "unconfirmed_dead": True})
    check("pending then ok: not a revival", rv, [])
    check("pending then ok: count zeroed", rec.get("dead_count"), 0)

    # ---- the oscillation that motivated two strikes, played out over 4 sweeps.
    # A group URL that 404s, answers 200, 404s again must NEVER be called dead.
    prev, verdicts = {}, []
    for st in (404, 200, 404, 200):
        repos, nd, rv = liveness.fold_history(
            {"k": {"status": st}}, {"k": prev}, {"k": "Example"}, NOW)
        prev = repos["k"]
        verdicts.append(bool(prev.get("dead_since")))
    check("oscillating repo never declared dead", verdicts, [False] * 4)

    # ---- a CONFIRMED verdict survives an unknown week (review 2026-11-10, M5):
    # dead, then a 503/transport error, then dead again is ONE death, same date.
    for st in (503, "error:URLError", "unconfirmed:403", "error:graphql"):
        rec, nd, rv = fold(st, prev={"status": 404, "dead_count": 2, "dead_since": OLD})
        check(f"dead then {st}: dead_since kept", rec.get("dead_since"), OLD)
        check(f"dead then {st}: not revived", rv, [])
        rec2, nd2, rv2 = fold(404, prev=rec)
        check(f"dead, {st}, dead: same date, not newly dead",
              (rec2.get("dead_since"), nd2), (OLD, []))
        rec3, nd3, rv3 = fold(200, prev=rec)
        check(f"dead, {st}, 200: revived", rv3, ["k"])

    # ---- the confirm pass (M6): only a 200 rescues, only 404/410 confirms
    res = {"a": {"status": 404}, "b": {"status": 404}, "c": {"status": 404},
           "d": {"status": 404}, "e": {"status": 404}}
    got = liveness.apply_confirm(res, {"a": {"status": 200}, "b": {"status": 404},
                                       "c": {"status": 403}, "d": {"status": "error:timeout"},
                                       "e": {"status": 410}})
    check("confirm: counts (rescued, unconfirmed)", got, (1, 2))
    check("confirm: statuses", {k: v["status"] for k, v in res.items()},
          {"a": 200, "b": 404, "c": "unconfirmed:403", "d": "unconfirmed:error:timeout",
           "e": 404})
    rec, nd, rv = fold(res["c"]["status"], prev={"status": 404, "dead_count": 1,
                                                 "unconfirmed_dead": True})
    check("confirm: an unconfirmed 404 is no strike", rec.get("dead_since"), None)

    # ---- a GraphQL 200 with only top-level errors is a failed batch, not 100 x 404
    # (both the first pass and the small-batch re-sweep read the response)
    real_post, real_sleep = liveness.post_json, liveness.time.sleep
    try:
        liveness.post_json = lambda *a, **k: {"errors": [{"message": "boom"}]}
        liveness.time.sleep = lambda s: None
        out = liveness.check_github(["github.com/o/r1", "github.com/o/r2"], "t")
    finally:
        liveness.post_json, liveness.time.sleep = real_post, real_sleep
    check("graphql errors-only: batch error, never 404",
          sorted(v["status"] for v in (out or {}).values()), ["error:graphql"] * 2)

    # ---- extra fields ride along only when present, and no per-run timestamp
    # is ever written onto a record.
    rec, nd, rv = fold(200, archived=True, last_push="2024-01-01T00:00:00Z", empty=None)
    check("archived carried", rec.get("archived"), True)
    check("last_push carried", rec.get("last_push"), "2024-01-01T00:00:00Z")
    check("empty=None omitted", "empty" in rec, False)
    check("NO per-record timestamp", [f for f in rec if "check" in f.lower()], [])
    check("name carried", rec.get("name"), "Example")

    for f in failed:
        print(f"FAIL  {f}")
    n = len(ran)
    print(f"\n{n - len(failed)}/{n} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
