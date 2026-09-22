#!/usr/bin/env python3
"""Merge tr_*.json translation files into catalog.json.

Keys are sha1(short_desc)[:10] so a translation survives re-harvests as long as
the upstream wording is unchanged. desc_src / desc_src_lang keep the original,
and translated=True marks machine-translated text so it is never mistaken for
source-provided English (desc_en).
"""
import json, os, glob, hashlib, collections

OUT = os.path.dirname(os.path.abspath(__file__))


def key_of(text):
    """The translation key. Hashes the RAW text — never a .strip()ed one.

    12 Bulgarian descriptions carry surrounding whitespace, and keys built from
    stripped text silently matched nothing. Do not "fix" that by stripping here:
    it would invalidate every key in every tr_*.json at once.
    """
    return hashlib.sha1(text.encode()).hexdigest()[:10]


def live_keys_of(catalog):
    """Every source text in `catalog`, as translation keys.

    Reads BOTH fields, which is what makes the orphan report stable across
    re-runs: short_desc holds the original on a raw row, desc_src holds it on an
    already-merged one (all 1,731 merged rows verified). Pure, so
    test_translation_orphans.py can exercise the trap below directly.
    """
    return {key_of(t) for r in catalog
            for t in (r.get("desc_src"), r.get("short_desc")) if t}


def orphans_of(per_file, live):
    """Per tr file, the keys whose source text is no longer in the catalogue.

    A key present in two files and orphaned counts in both: per-file totals are
    what tell you which file to edit, and tr.update() order is irrelevant to it.
    """
    return {name: sorted(k for k in part if k not in live)
            for name, part in per_file.items()}


tr, per_file = {}, {}
for f in sorted(glob.glob(f"{OUT}/translations/tr_*.json")):
    part = json.load(open(f))
    per_file[os.path.basename(f)] = part
    tr.update(part)
    print(f"  {os.path.basename(f)}: {len(part)}")

c = json.load(open(f"{OUT}/catalog.json"))
n = collections.Counter()

# ---- every source text currently in the catalogue, as translation keys.
#
# Computed BEFORE the merge loop mutates anything, and from BOTH fields, which
# is what makes the orphan report below stable across re-runs: short_desc holds
# the original on a raw row, and desc_src holds it on an already-merged one.
#
# ⚠ The obvious implementation — "keys this pass actually looked up" — is
# unusable. A merged row carries translated=True and short-circuits before the
# lookup, so on already-merged input almost nothing is looked up and the report
# claims ~100% rot (measured: 1,762 of 1,762 keys, against a real 59). A sensor
# that scream-fails on a re-run is worse than none, because it teaches you to
# ignore it.
live_keys = live_keys_of(c)
for r in c:
    d = r.get("short_desc")
    if not d:
        n["no_description"] += 1
        continue
    # check translated BEFORE desc_lang: a merged row already has desc_lang="en",
    # so testing language first would silently recount our own translations as
    # source-provided English and inflate the coverage claim.
    if r.get("translated"):
        n["translated"] += 1
        continue
    if r.get("desc_lang") == "en":
        n["source_english"] += 1
        continue
    # desc_lang is None on index-tier sources (BE/FI/SE adapters never set it),
    # which is why Finnish and Swedish text was originally skipped entirely.
    # Fall through to the hash lookup rather than trusting the language tag.
    k = key_of(d)
    if k in tr:
        r["desc_src"] = r.get("desc_src") or d
        r["desc_src_lang"] = r.get("desc_src_lang") or r.get("desc_lang")
        r["short_desc"] = tr[k]
        # An EMPTY translation means the source text carries no describable
        # content — 8 Bulgarian entries whose whole "description" is a
        # procurement reference like "СОА25-ДГ55-472/04.08.2025 г." The original
        # is kept in desc_src; the entry is treated as having no description
        # rather than counted as English, or the coverage arithmetic
        # double-counts it as both English and undescribed.
        if not tr[k].strip():
            r["desc_lang"] = None
            n["no_description"] += 1
            continue
        r["desc_lang"] = "en"
        r["translated"] = True
        n["translated"] += 1
    else:
        n["still_untranslated"] += 1

json.dump(c, open(f"{OUT}/catalog.json", "w"), indent=1, default=str)

# ---- ORPHANED KEYS: translations whose source text is no longer in the
# catalogue (review finding F6).
#
# Reworded upstream text falls back to the foreign original. That is documented
# and accepted — but nothing reported it, so the only symptom was the English
# coverage tile drifting down by ones, which is the exact rot export_json.py
# already warns about for replaces.json keys. This is the last instance of this
# repo's one idea: every failure sensor was a print.
#
# Written as a file so /sources.html can warn and runlog.py can trend it, and
# rebuilt from scratch every run so it self-clears — same contract as
# out/taxonomy_unmapped.json and cache/_fetched.json.
#
# A key present in two tr files and orphaned counts in both: per-file totals are
# what tell you which file to edit, and tr.update() order is irrelevant to that.
orphans = orphans_of(per_file, live_keys)
n_orph = sum(len(v) for v in orphans.values())

# ⚠ THE ORPHAN COUNT IS POSITION-DEPENDENT, and a by-hand run out of position
# inflates it. run.sh puts this step BEFORE dedupe, which is the number that
# means something. Run it AFTER dedupe and every row dedupe merged away has
# taken its source text out of the catalogue with it, so its translation looks
# rotted when it is nothing of the kind: measured 2026-09-21, a post-dedupe run
# reported 32 orphans of which **29 were dedupe casualties and 3 were real**.
#
# The step itself is safe to re-run — a translated row carries translated=True and
# short-circuits — so this WARNS rather than refusing, unlike taxonomy.py and
# dedupe.py, which destroy data in the same position and use
# stage_guard.assert_pre_dedupe(). Same family, different remedy: there the data
# is at risk, here only the reading is.
if any("catalogue_count" in r for r in c if not r.get("excluded")):
    print(f"\n   !! catalog.json has already been through dedupe, so the {n_orph} "
          f"orphan count above is INFLATED:\n"
          f"      rows dedupe merged away took their source text with them, and "
          f"their translations\n"
          f"      now look rotted. For the number that means something, run this "
          f"before dedupe:\n"
          f"        python3 harvest.py --from-cache && bash run.sh")
os.makedirs(f"{OUT}/out", exist_ok=True)
json.dump({
    "total": n_orph,
    "keys_total": sum(len(p) for p in per_file.values()),
    "by_file": {name: {"keys": len(per_file[name]), "orphans": len(o),
                       # capped: enough to grep for, not a second copy of the file
                       "sample": o[:12]}
                for name, o in sorted(orphans.items())},
}, open(f"{OUT}/out/translation_orphans.json", "w"), indent=1, sort_keys=True)

tot = len(c)
print(f"\n{tot} entries")
for k, v in n.most_common():
    print(f"   {k:20} {v:>5}  ({100*v/tot:.0f}%)")
eng = n['source_english'] + n['translated']
print(f"\n   ENGLISH COVERAGE: {eng}/{tot - n['no_description']} of described entries "
      f"({100*eng/max(1,tot-n['no_description']):.0f}%)")

if n_orph:
    print(f"\n   {n_orph} ORPHANED translation key(s) — source text no longer in the "
          f"catalogue,\n   so those entries fall back to the foreign original:")
    for name, o in sorted(orphans.items(), key=lambda kv: -len(kv[1])):
        if o:
            print(f"      {name:20} {len(o):>4} of {len(per_file[name]):>4}")
    print("   Full list: out/translation_orphans.json")
