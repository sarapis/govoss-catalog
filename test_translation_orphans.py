#!/usr/bin/env python3
"""Regression test for translation-key rot detection (review finding F6).

    python3 test_translation_orphans.py

`merge_translations.py` reports tr_*.json keys whose source text is no longer in
the catalogue. The entry then falls back to its foreign original, which is
documented and accepted — what was missing was any report that it happened.

The whole difficulty is deciding what "no longer in the catalogue" means, and the
obvious answer is wrong in a way that would make the sensor useless:

  * NAIVE: "keys this merge pass actually looked up". A merged row carries
    translated=True and short-circuits before the lookup, so on already-merged
    input almost nothing is looked up. Measured against the real catalogue: the
    naive rule reports **1,762 of 1,762 keys orphaned** where the truth is 59.
    A sensor that screams on a re-run trains you to ignore it, which is the same
    end state as having no sensor — the failure F1-F6 all exist to fix.

  * CORRECT: hash the SOURCE TEXT still present in the catalogue, from both
    short_desc (the original on a raw row) and desc_src (the original on an
    already-merged one). Stable across re-runs by construction.

`live_keys_of` and `orphans_of` were extracted from the script so both rules can
be exercised side by side, which is the only way to keep the naive one from
looking reasonable to the next reader.
"""
import os
import sys

# merge_translations.py does its work at MODULE level — importing it would run
# the whole step and rewrite catalog.json. So compile only the part above the
# first statement that touches disk, and take the pure helpers from that.
_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "merge_translations.py")
_HEAD = open(_PATH).read().split("tr, per_file = {}, {}")[0]
assert "def live_keys_of" in _HEAD and "def orphans_of" in _HEAD, (
    "merge_translations.py was restructured: the helpers no longer sit above "
    "`tr, per_file = {}, {}`, so this test is reading the wrong slice of it.")
_ns = {"__file__": _PATH, "__name__": "merge_translations_head"}
exec(compile(_HEAD, _PATH, "exec"), _ns)
key_of, live_keys_of, orphans_of = _ns["key_of"], _ns["live_keys_of"], _ns["orphans_of"]

# A catalogue mid-pipeline: one raw row, one already-merged row, one row whose
# upstream text was reworded since its translation was made.
RAW = {"name": "raw", "short_desc": "Ein Werkzeug für Verwaltungen"}
MERGED = {"name": "merged", "translated": True, "desc_lang": "en",
          "short_desc": "A tool for public administrations",
          "desc_src": "Uno strumento per le amministrazioni"}
REWORDED = {"name": "reworded", "short_desc": "Nieuwe formulering van de tekst"}
# 12 Bulgarian descriptions carry surrounding whitespace and the key hashes the
# RAW string; a .strip() anywhere in this chain silently matches nothing.
PADDED = {"name": "padded", "short_desc": "  Договор № 98-00-101  "}
NO_DESC = {"name": "nodesc", "short_desc": None}

CATALOG = [RAW, MERGED, REWORDED, PADDED, NO_DESC]

PER_FILE = {
    "tr_de.json": {key_of(RAW["short_desc"]): "A tool for administrations"},
    "tr_it.json": {key_of(MERGED["desc_src"]): "A tool for public administrations"},
    "tr_bg.json": {key_of(PADDED["short_desc"]): "Contract No 98-00-101"},
    # the rot: a key for wording that no longer appears anywhere
    "tr_nl.json": {"deadbeef00": "translation of text nobody publishes now"},
}


def naive_looked_up(catalog):
    """The rejected rule, kept so the test can prove it is rejected for cause."""
    out = set()
    for r in catalog:
        d = r.get("short_desc")
        if not d or r.get("translated") or r.get("desc_lang") == "en":
            continue
        out.add(key_of(d))
    return out


def main():
    failed, ran = [], []

    def check(label, got, want):
        ran.append(label)          # counted, never hard-coded: a stale n reports a phantom pass
        if got != want:
            failed.append(f"{label}: expected {want}, got {got}")

    live = live_keys_of(CATALOG)
    orph = orphans_of(PER_FILE, live)
    flat = {k for v in orph.values() for k in v}

    check("raw row's text is live", key_of(RAW["short_desc"]) in live, True)
    # The re-run stability mechanism, stated as its own assertion rather than
    # inferred from a total: a merged row's ORIGINAL survives only in desc_src.
    check("merged row's desc_src is live", key_of(MERGED["desc_src"]) in live, True)
    check("merged row's English is also live", key_of(MERGED["short_desc"]) in live, True)
    check("padded text hashes raw, unstripped", key_of(PADDED["short_desc"]) in live, True)
    check("stripped text is NOT the key", key_of(PADDED["short_desc"].strip()) in live, False)

    check("the reworded key is orphaned", "deadbeef00" in flat, True)
    check("orphan total", sum(len(v) for v in orph.values()), 1)
    check("orphan attributed to its own file", orph["tr_nl.json"], ["deadbeef00"])
    check("the merged row's key is NOT orphaned",
          key_of(MERGED["desc_src"]) in flat, False)
    check("every file reported, healthy ones as empty", sorted(orph), sorted(PER_FILE))

    # ---- the trap, asserted directly.
    naive = naive_looked_up(CATALOG)
    naive_orph = {k for part in PER_FILE.values() for k in part if k not in naive}
    check("naive rule would report the merged row's key as rot",
          key_of(MERGED["desc_src"]) in naive_orph, True)
    check("naive rule is strictly worse here", len(naive_orph) > len(flat), True)

    # A catalogue with nothing left to translate: every row merged. This is the
    # shape that produced 100% false rot.
    all_merged = [MERGED]
    check("correct rule survives an all-merged catalogue",
          orphans_of({"tr_it.json": PER_FILE["tr_it.json"]}, live_keys_of(all_merged)),
          {"tr_it.json": []})
    check("naive rule collapses on an all-merged catalogue",
          naive_looked_up(all_merged), set())

    for f in failed:
        print(f"FAIL  {f}")
    n = len(ran)
    print(f"\n{n - len(failed)}/{n} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
