#!/usr/bin/env python3
"""Stamp when each entry first appeared, into cache/_first_seen.json.

    python3 first_seen.py            # stamp today's new entries
    python3 first_seen.py --backfill # recover real dates from git history first

Nothing in the catalogue recorded when an entry arrived. The weekly run knew the
COUNT — history.json carries `+16` — but not which sixteen, so "what's new" could
not be shown or even asked.

This is the same shape as cache/_fetched.json: a small persisted summary that the
pipeline maintains, committed with the rest of cache/ by run.sh's `record` step.
Two rules carried over from it, for the same reasons:

  * **A date is only ever written ONCE.** An id already in the file keeps its
    date forever. If stamping could overwrite, every entry would read as new on
    any run that rebuilt from a fresh checkout, which is exactly the "reused data
    looks fresh" failure _fetched.json exists to prevent.
  * **Written sorted, one line per id.** cache/ is committed weekly; unsorted
    output would churn the diff by thousands of lines against ~20 real additions.

⚠ IDENTITY IS `repo_key`, FALLING BACK TO `name|source`. It has to survive dedupe
picking a different survivor next week, and repo_key is the join key dedupe itself
uses. An entry whose repo URL changes upstream will look new again — accepted:
the alternative is matching on name, which this repo refuses everywhere else for
good reason (Angular vs AngularJS).

⚠ THE BACKFILL IS A ONE-OFF AND ITS LIMIT IS REAL. Entries present at the FIRST
weekly run get a date of None — they existed before the record starts, and dating
them to the day the backfill happened to run would assert an arrival nobody
observed. They are known, and never "new". Measured: **3,070 undated baseline,
119 dated across 9 weekly runs.** None means unknown, not old, and not absent.
"""
import json
import os
import subprocess
import sys
import time

OUT = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(OUT, "cache")
PATH = os.path.join(CACHE, "_first_seen.json")
TODAY = time.strftime("%Y-%m-%d", time.gmtime())


def ident(r):
    """Stable identity across runs. See the module docstring."""
    return r.get("repo_key") or "%s|%s" % (r.get("name"), r.get("source"))


def load():
    try:
        with open(PATH) as fh:
            return json.load(fh)
    except Exception:
        return {}


def save(d):
    os.makedirs(CACHE, exist_ok=True)
    with open(PATH, "w") as fh:
        json.dump(d, fh, indent=0, sort_keys=True)
        fh.write("\n")


def revisions():
    """The weekly RUN commits of catalog.json, oldest first.

    ⚠ Only commits whose subject begins "Data:" count, and that is the whole
    trick. git holds 27 revisions of catalog.json but 16 of them are dated
    2026-08-11 — the project being BUILT, not entries arriving. Treating those as
    observations dated 1,185 entries to a day on which nothing was harvested and
    the dates meant nothing.

    A "Data:" commit is written by run.sh's `record` step at the end of a weekly
    run, so it is the only revision that represents the catalogue actually
    changing. Everything else is the code changing underneath it.
    """
    out = subprocess.run(
        ["git", "-C", OUT, "log", "--reverse", "--format=%H\t%ad\t%s",
         "--date=short", "--", "catalog.json"],
        capture_output=True, text=True).stdout.strip()
    revs = []
    for line in out.split("\n"):
        parts = line.split("\t")
        if len(parts) == 3 and parts[2].startswith("Data:"):
            revs.append((parts[0], parts[1]))
    return revs


def catalog_at(sha):
    out = subprocess.run(["git", "-C", OUT, "show", "%s:catalog.json" % sha],
                         capture_output=True, text=True).stdout
    try:
        return json.loads(out)
    except Exception:
        return None                       # a revision that predates the file


def backfill(seen):
    """Recover real first-seen dates from git. Only fills ids with no date yet.

    The oldest run commit is the BASELINE: its entries are recorded with a date of
    None, meaning "present before the record began". That is deliberately not the
    same as absent — an id carrying None is known and will never be reported as
    new, whereas an id missing from the file entirely is genuinely unseen and gets
    stamped. Conflating the two dated the whole 3,070-entry baseline to the day
    the backfill ran.
    """
    revs = revisions()
    if not revs:
        print("  no weekly run commits found — nothing to backfill")
        return seen, 0
    known, added, baseline = set(), 0, 0
    for sha, date in revs:
        c = catalog_at(sha)
        if c is None:
            continue
        ids = {ident(r) for r in c if not r.get("excluded")}
        fresh = ids - known
        for k in fresh:
            if k in seen:
                continue
            seen[k] = date if known else None
        if not known:
            baseline = len(fresh)
        else:
            added += len(fresh)
        known |= ids
    print("  walked %d weekly run commits; dated %d entries; "
          "%d were present at the first run and stay undated"
          % (len(revs), added, baseline))
    return seen, added


def main():
    seen = load()
    before = len(seen)

    if "--backfill" in sys.argv or not seen:
        print("[first_seen] backfilling from git history")
        seen, _ = backfill(seen)

    try:
        catalog = json.load(open(os.path.join(OUT, "catalog.json")))
    except Exception as e:
        print("  cannot read catalog.json: %s" % e, file=sys.stderr)
        return 0                          # never fail the pipeline over this

    # `not in seen` — NOT `not seen.get(...)`. A baseline entry carries None, and
    # a falsy test would restamp all 3,070 of them every run.
    active = [r for r in catalog if not r.get("excluded")]
    new = [ident(r) for r in active if ident(r) not in seen]
    for k in new:
        seen[k] = TODAY
    save(seen)

    dated = sum(1 for v in seen.values() if v)
    print("[first_seen] %d ids known, %d carrying a date, %d baseline; "
          "%d stamped %s today"
          % (len(seen), dated, len(seen) - dated, len(new), TODAY))
    if new and before:
        names = {ident(r): r.get("name") for r in active}
        shown = [names.get(k) or k for k in new[:6]]
        print("   new: %s%s" % (", ".join(shown), " …" if len(new) > 6 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
