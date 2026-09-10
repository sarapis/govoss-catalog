#!/usr/bin/env python3
"""Adversarial test for stage_guard.assert_pre_dedupe().

    python3 test_stage_guard.py

A guard is worth exactly what its failing case is worth. This repo has shipped a
guard that could only ever pass — `theme.assert_variant_live()` substring-searched
the whole page, and the vendored CSS's own comment contains the literal it looked
for — so the rule here is that every guard gets tested by BREAKING the thing it
checks, not by watching it not complain.

So this file asserts both directions, and includes the two implementation
mistakes that would leave the guard silently useless:

  * `all()` instead of `any()` — would not fire on a catalogue where only some
    active rows are merged, which is every real catalogue.
  * not skipping `excluded` rows — the 484 set-aside rows never receive a
    `catalogue_count`, so a guard that required it on every row could never fire.

The final case is the one that matters: it runs `taxonomy.py` and `dedupe.py` as
subprocesses against the REAL merged catalog.json and asserts the file is
byte-identical afterwards. That is the destruction the guard exists to prevent,
and checking the exit code alone would not prove it was prevented — this repo's
own rule is to verify the built output, not that a patch reported success.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

import stage_guard

HERE = os.path.dirname(os.path.abspath(__file__))


def active(**kw):
    return dict({"name": "x", "source": "IT/it"}, **kw)


# (label, catalog, should_fire)
CASES = [
    ("empty catalogue",
     [], False),

    ("raw checkpoint shape — what harvest.py assembles, no catalogue_count",
     [active(), active(name="y")], False),

    ("post-dedupe — every active row stamped",
     [active(catalogue_count=1), active(name="y", catalogue_count=3)], True),

    # Kills an all()-based implementation.
    ("post-dedupe — only ONE active row stamped",
     [active(), active(name="y", catalogue_count=2)], True),

    # Kills an implementation that forgets to skip excluded rows: these rows
    # never carry a catalogue_count, so requiring it everywhere never fires.
    ("pre-dedupe with set-aside rows present",
     [active(), active(name="y", excluded=True, exclude_reason="no-description")],
     False),

    ("post-dedupe with set-aside rows present",
     [active(catalogue_count=1),
      active(name="y", excluded=True, exclude_reason="no-description")],
     True),

    # catalogue_count of 1 is still the marker: dedupe stamps it on singletons
    # too, so its presence — not its value — is what says the merge has run.
    ("post-dedupe, no multi-catalogue entries at all",
     [active(catalogue_count=1), active(name="y", catalogue_count=1)], True),
]


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main():
    failed = []

    for label, catalog, want in CASES:
        got = stage_guard.is_post_dedupe(catalog)
        if got != want:
            failed.append(f"is_post_dedupe: {label}: expected {want}, got {got}")

    # ---- the real files, both directions
    raw = json.load(open(f"{HERE}/cache/src_tw.json"))
    if stage_guard.is_post_dedupe(raw):
        failed.append("a real raw checkpoint (cache/src_tw.json) read as post-dedupe")

    real = json.load(open(f"{HERE}/catalog.json"))
    # ⚠ Decided INDEPENDENTLY of the function under test. Keying this on
    # stage_guard.is_post_dedupe() is circular, and it was: a sabotaged no-op
    # guard reported "not merged", which SKIPPED the subprocess cases — the ones
    # that prove destruction is prevented — exactly when the guard was broken.
    # The test must never ask the thing it is testing whether to run its hardest
    # case.
    real_is_merged = any("catalogue_count" in r for r in real if not r.get("excluded"))
    if not real_is_merged:
        # Not a guard failure — catalog.json is only merged between the dedupe
        # step and the next harvest. Say so rather than reporting a false pass.
        print("SKIP  catalog.json is not currently merged, so the subprocess\n"
              "      cases cannot run. Re-run after `bash run.sh`.")
    else:
        # ---- THE case: run the two stages for real and prove nothing changed.
        before = sha(f"{HERE}/catalog.json")
        backup = os.path.join(tempfile.mkdtemp(), "catalog.json")
        shutil.copy2(f"{HERE}/catalog.json", backup)
        try:
            for stage in ("taxonomy.py", "dedupe.py"):
                p = subprocess.run([sys.executable, stage], cwd=HERE,
                                   capture_output=True, text=True)
                if p.returncode != 2:
                    failed.append(f"{stage} on merged catalog.json: expected exit 2, "
                                  f"got {p.returncode}")
                if "REFUSING" not in (p.stderr or ""):
                    failed.append(f"{stage}: refusal message missing from stderr")
                if sha(f"{HERE}/catalog.json") != before:
                    failed.append(f"{stage} MODIFIED catalog.json despite refusing — "
                                  f"the guard ran too late to protect anything")
        finally:
            # Restore unconditionally: a broken guard means this test is the
            # thing that destroyed the data it was checking.
            if sha(f"{HERE}/catalog.json") != before:
                shutil.copy2(backup, f"{HERE}/catalog.json")
                print("NOTE  catalog.json was modified and has been restored.")

    for f in failed:
        print(f"FAIL  {f}")

    n = len(CASES) + 2 + (6 if real_is_merged else 0)
    print(f"\n{n - len(failed)}/{n} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
