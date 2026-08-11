#!/usr/bin/env python3
"""Merge tr_*.json translation files into catalog.json.

Keys are sha1(short_desc)[:10] so a translation survives re-harvests as long as
the upstream wording is unchanged. desc_src / desc_src_lang keep the original,
and translated=True marks machine-translated text so it is never mistaken for
source-provided English (desc_en).
"""
import json, os, glob, hashlib, collections

OUT = os.path.dirname(os.path.abspath(__file__))
tr = {}
for f in sorted(glob.glob(f"{OUT}/translations/tr_*.json")):
    part = json.load(open(f))
    tr.update(part)
    print(f"  {os.path.basename(f)}: {len(part)}")

c = json.load(open(f"{OUT}/catalog.json"))
n = collections.Counter()
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
    k = hashlib.sha1(d.encode()).hexdigest()[:10]
    if k in tr:
        r["desc_src"] = r.get("desc_src") or d
        r["desc_src_lang"] = r.get("desc_src_lang") or r.get("desc_lang")
        r["short_desc"] = tr[k]
        r["desc_lang"] = "en"
        r["translated"] = True
        n["translated"] += 1
    else:
        n["still_untranslated"] += 1

json.dump(c, open(f"{OUT}/catalog.json", "w"), indent=1, default=str)
tot = len(c)
print(f"\n{tot} entries")
for k, v in n.most_common():
    print(f"   {k:20} {v:>5}  ({100*v/tot:.0f}%)")
eng = n['source_english'] + n['translated']
print(f"\n   ENGLISH COVERAGE: {eng}/{tot - n['no_description']} of described entries "
      f"({100*eng/max(1,tot-n['no_description']):.0f}%)")
