#!/usr/bin/env python3
"""Refuse to re-run a pipeline stage on already-merged catalog.json.

`run.sh`'s ordering is load-bearing, and two stages are DESTRUCTIVE when run out
of order — not wrong-looking, destructive, and silently so. Both compute a field
from scratch, and both fields can also carry information that only `dedupe.py`
produced, which the survivor's own record cannot reconstruct:

  * `dedupe.py` — a second pass sees each merge survivor as a group of ONE, takes
    the `len(g) == 1` branch, and overwrites `catalogue_entries` with a
    single-element list built from the survivor's own fields plus
    `catalogue_count = 1`. The "In N catalogues" pill — 98 entries, and the whole
    point of a union catalogue — is gone, with no error. (Review finding F5.)

  * `taxonomy.py` — `functions` is in `dedupe.py:UNION_LIST`, so a survivor
    carries functions contributed by its merge partners. `classify()` recomputes
    from the survivor alone and returns at most one function from the inference
    branch, and never consults inference at all once a source category maps. On
    the 2026-09-10 catalogue that narrows **45 entries** (7-Zip loses
    `data-analytics`, Apache HTTP Server loses `infrastructure`, Decidim loses
    `citizen-services`). Found while verifying an unrelated one-line taxonomy
    change, by dry-running `classify()` and wondering why 45 rows moved.

⚠ THE FIX IS TO REFUSE, NOT TO UNION WITH WHAT IS ALREADY THERE.

Making these stages merge-aware — union the recomputed value with the stored one
— is the obvious idea and it is wrong. It would make a CORRECTION impossible: a
bad mapping removed from `taxonomy.py:M`, or a record that legitimately stopped
being listed by three catalogues, would keep its stale value forever, and nothing
would ever say so. That trades a loud bug for a silent permanent one, in the
reassuring direction, which is the failure this repo keeps re-learning (an API
404 read as a dead repo; a green pipeline log over a dead harvest).

There is deliberately NO --force. The way forward is to rebuild from the
checkpoints, which is offline, cheap and polite:

    python3 harvest.py --from-cache && bash run.sh   # or just: bash run.sh

`--from-cache` reassembles catalog.json from `cache/src_*.json`, which are raw
per-source records and carry no `catalogue_count` — so the guard passes again and
the stages run on the input shape they were written for.

The marker is `catalogue_count` on an ACTIVE row. `dedupe.py` stamps it on every
active record in both branches and leaves `excluded` rows untouched, so "any
active row has it" is the test; "every row has it" would be wrong, since the 484
set-aside rows never get one.
"""
import sys

MARKER = "catalogue_count"


def is_post_dedupe(catalog):
    """True if catalog.json has already been through dedupe.py this cycle."""
    return any(MARKER in r for r in catalog if not r.get("excluded"))


def assert_pre_dedupe(catalog, stage):
    """Exit 2 if `catalog` has already been merged. Call before mutating it.

    Exits rather than raises so the message is the whole output: this fires when
    someone runs a stage by hand, and a traceback would bury the one line that
    says what to do instead. `run.sh` records the non-zero code in out/steps.tsv,
    which gates the deploy — right, because the only way this fires inside a real
    run is that the documented ordering has broken.
    """
    if not is_post_dedupe(catalog):
        return
    n = sum(1 for r in catalog
            if not r.get("excluded") and (r.get(MARKER) or 1) > 1)
    print(
        f"REFUSING to run {stage} on already-merged catalog.json.\n"
        f"\n"
        f"  Every active row carries `{MARKER}`, so dedupe.py has already run.\n"
        f"  Re-running {stage} now would silently destroy data only the merge\n"
        f"  has: {stage} recomputes a field from each survivor alone, and cannot\n"
        f"  see what its merge partners contributed"
        + (f" ({n} entries are listed by\n  2+ catalogues right now).\n" if n else ".\n")
        + f"\n"
        f"  Rebuild from the checkpoints instead — offline, no network:\n"
        f"\n"
        f"      python3 harvest.py --from-cache && bash run.sh\n"
        f"\n"
        f"  See stage_guard.py for why there is no --force.\n",
        file=sys.stderr)
    sys.exit(2)
