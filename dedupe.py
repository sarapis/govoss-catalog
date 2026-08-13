#!/usr/bin/env python3
"""Collapse records that describe the same piece of software.

Runs AFTER filters.py. Writes the merged catalogue back to catalog.json and
keeps the pre-merge rows in out/dupes.json so every merge is auditable.

Identity, in precedence order (union-find, so identities chain transitively):
  1. Wikidata QID     — authoritative and cross-language. Angular Q28925578 and
                        AngularJS Q2849803 stay separate, which name matching
                        would never manage since one name contains the other.
  2. normalised repo URL
  3. exact name AND exact homepage — BOTH, never either alone.

NEVER name similarity, and never name alone. See the Angular/AngularJS case above.

Rule 3 exists because rules 1 and 2 cannot reach the commonest split: the same
upstream tool listed by two catalogues that recorded DIFFERENT repo urls and
carry no QID. OpenStreetMap was three separate entries — Munich, Sweden and the
DPG registry — each pointing at a different page (one at no repo at all, one at
wiki.openstreetmap.org/wiki/API, one at a wiki how-to on osmfoundation.org).
Nothing joined them, and a reader saw the same software three times.

It is a CONJUNCTION of two independent identifiers, which is what makes it safe
where name alone is not. Angular and AngularJS have different homepages, so the
case the rule above exists to prevent is still prevented. Measured before it
landed: 11 groups qualify — Audacity, ckan, CollectiveAccess, GlobaLeaks, Hugin,
Masterportal, OpenStreetMap, Penpot, TrueNAS, Visual Studio Code, Vue.js — every
one genuinely the same software, and each with two different repo urls, which is
exactly why nothing else caught them.

The homepage is what makes it safe. Four unrelated German repos (data-stories,
journal-web-ui, metadaten, usage-stats-api) share the homepage umwelt.info and do
NOT merge, because their names differ. Requiring both is the whole design.

Why there is so much to merge — two very different causes:

  * Cross-country (15 groups): the same upstream tool recommended or reused by
    several countries. Matomo appears for FR and IT; OpenProject for DE, FR and
    IT. These are genuine, and merging them is the whole point of a union
    catalogue — you want one Matomo row that says "3 countries".

  * Same-country (69 groups), overwhelmingly German: **personal forks on
    gitlab.opencode.de**. 15 separate projects (`tlrz/opendesk`,
    `dschmidt/opendesk`, `wolfgangihloff/opendesk`, …) each carry upstream's
    publiccode.yml, which declares `url: .../bmi/opendesk`. GitLab only exposes
    `forked_from_project` on a single-project GET, not in the list endpoint — but
    we do not need it: a project whose declared publiccode url is NOT itself is
    a fork or a mirror, and the declared url is the canonical identity. So
    deduping on it fixes forks for free.

Choosing the survivor matters: prefer the record whose own forge path matches the
declared URL (i.e. the canonical project, not somebody's fork), then the
publiccode tier over index, then the one with the most populated fields.
"""
import json, os, re, collections

OUT = os.path.dirname(os.path.abspath(__file__))

# fields unioned across the merged group rather than taken from the survivor
UNION_LIST = ["categories", "functions", "platforms", "used_by", "contacts", "keywords"]


def norm_site(url):
    """Normalise a homepage for comparison. Deliberately NOT the repo
    normalisation: no .git or /tree/ handling, because a landing page has
    neither, and no path stripping, because example.org/foo and example.org/bar
    are different products from the same publisher."""
    if not url or not isinstance(url, str):
        return None
    u = re.sub(r"^https?://", "", url.strip().rstrip("/"))
    u = re.sub(r"^www\.", "", u)
    return u.lower() or None


def name_site_key(r):
    """Identity 3: exact name AND exact homepage. Returns None unless BOTH are
    present — a missing homepage must never let the name alone carry a merge."""
    n = (r.get("name") or "").strip().lower()
    s = norm_site(r.get("landing"))
    return (n, s) if n and s else None


class UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def stable_order(r):
    """Total ordering for the committed catalog.json. Kept in sync with the copy
    in harvest.py, which explains why it is duplicated rather than imported."""
    return (str(r.get("name") or "").lower(), str(r.get("repo") or ""),
            str(r.get("source") or ""), str(r.get("entry_url") or ""))


def richness(r):
    """How much do we actually know about this record?"""
    return sum(1 for k, v in r.items() if v not in (None, "", [], {}, False))


def canonical_score(r):
    """Higher is more likely to be the real project rather than a fork/mirror."""
    s = 0
    declared = r.get("repo_key") or ""
    fp = (r.get("forge_path") or "").lower()
    # Namespace containment, NOT exact suffix match. openDesk declares
    # `url: .../bmi/opendesk` while the canonical project actually lives at
    # `bmi/opendesk/deployment/opendesk` — so an endswith() test failed for the
    # real project AND for every personal fork, leaving the survivor to be picked
    # by richness alone. That handed the entry to `tlrz/opendesk`, a fork.
    if fp:
        dpath = declared.split("/", 1)[1] if "/" in declared else declared
        if fp == dpath or fp.startswith(dpath + "/") or dpath.startswith(fp + "/"):
            s += 100
    if r.get("tier") == "publiccode":
        s += 40
    if r.get("wikidata"):
        s += 10
    if r.get("recommended_for_gov"):
        s += 5
    return s + richness(r) / 100.0


def merge(group):
    group = sorted(group, key=canonical_score, reverse=True)
    primary, rest = group[0], group[1:]
    out = dict(primary)

    for f in UNION_LIST:
        seen, merged = set(), []
        for r in group:
            for v in (r.get(f) or []):
                key = json.dumps(v, sort_keys=True) if not isinstance(v, str) else v
                if key not in seen:
                    seen.add(key)
                    merged.append(v)
        if merged:
            out[f] = merged

    # provenance: which catalogues and countries asserted this, and what each called it.
    # catalogue_entries keeps a DEEP LINK per catalogue so a reader can verify the
    # claim upstream rather than taking the merge on trust. entry_url is null for
    # sources with no per-entry page (Developers Italia is a JS app whose sitemap has
    # no software pages; Offentligkod and Canada have no per-entry route) — a guessed
    # deep link would be worse than none.
    seen_src, cat_entries = set(), []
    for r in group:
        src = r.get("source")
        if src and src not in seen_src:
            seen_src.add(src)
            cat_entries.append({"source": src,
                                "name": r.get("name"),
                                "entry_url": r.get("entry_url"),
                                "repo_url": r.get("repo")})
    out["catalogue_entries"] = cat_entries
    out["catalogue_count"] = len(cat_entries)
    out["sources"] = sorted({r["source"] for r in group})
    out["countries"] = sorted({r["country"] for r in group if r.get("country")})
    out["merged_count"] = len(group)
    alt = sorted({r.get("name") for r in group if r.get("name")
                  and r.get("name") != primary.get("name")})
    if alt:
        out["also_known_as"] = alt
    # keep a description if the survivor lacked one but a sibling had it
    if not out.get("short_desc"):
        for r in rest:
            if r.get("short_desc"):
                out["short_desc"] = r["short_desc"]
                out["desc_lang"] = r.get("desc_lang")
                out["translated"] = r.get("translated")
                break
    if not out.get("wikidata"):
        for r in rest:
            if r.get("wikidata"):
                out["wikidata"] = r["wikidata"]
                break
    return out


if __name__ == "__main__":
    c = json.load(open(f"{OUT}/catalog.json"))
    active = [r for r in c if not r.get("excluded")]
    excluded = [r for r in c if r.get("excluded")]

    uf = UF()
    for i, r in enumerate(active):
        uf.find(("i", i))
        if r.get("repo_key"):
            uf.union(("repo", r["repo_key"]), ("i", i))
        if r.get("wikidata"):
            uf.union(("qid", r["wikidata"]), ("i", i))
        nk = name_site_key(r)
        if nk:
            uf.union(("namesite", nk), ("i", i))

    groups = collections.defaultdict(list)
    for i, r in enumerate(active):
        groups[uf.find(("i", i))].append(r)

    merged, dupes = [], []
    for g in groups.values():
        if len(g) == 1:
            r = dict(g[0])
            r["catalogue_entries"] = [{"source": r.get("source"), "name": r.get("name"),
                                       "entry_url": r.get("entry_url"),
                                       "repo_url": r.get("repo")}]
            r["catalogue_count"] = 1
            merged.append(r)
        else:
            merged.append(merge(g))
            dupes.append(g)

    # Sorting by name alone left ties free to swap between runs, and `excluded`
    # was not sorted at all. catalog.json is committed weekly, so both matter.
    # `merged + excluded` order is kept — the split is meaningful, and consumers
    # filter on the `excluded` flag rather than on position.
    merged.sort(key=stable_order)
    excluded.sort(key=stable_order)
    json.dump(merged + excluded, open(f"{OUT}/catalog.json", "w"),
              indent=1, default=str, sort_keys=True)
    os.makedirs(f"{OUT}/out", exist_ok=True)
    json.dump(dupes, open(f"{OUT}/out/dupes.json", "w"), indent=1, default=str)

    collapsed = sum(len(g) - 1 for g in dupes)
    multi = [r for r in merged if len(r.get("countries") or []) > 1]
    multi_cat = [r for r in merged if r.get("catalogue_count", 1) > 1]
    print(f"{len(active)} active entries -> {len(merged)} after merge "
          f"({collapsed} collapsed across {len(dupes)} groups)")
    print(f"  {len(excluded)} filtered entries left untouched")
    print(f"  {len(multi)} entries now assert more than one country")
    print(f"  {len(multi_cat)} entries appear in more than one CATALOGUE")
    import collections as _c
    print("  catalogue-count distribution:",
          dict(sorted(_c.Counter(r.get("catalogue_count", 1) for r in merged).items())))
    print(f"\n  largest merges:")
    for g in sorted(dupes, key=len, reverse=True)[:8]:
        srcs = "+".join(sorted({r["country"] for r in g if r.get("country")}))
        print(f"    {len(g):>3}x {srcs:10} {g[0].get('name','?')[:38]}")
    print(f"\n  multi-country software (the point of a union catalogue):")
    for r in sorted(multi, key=lambda r: -len(r["countries"]))[:10]:
        print(f"    {'+'.join(r['countries']):14} {(r.get('name') or '')[:34]}")
    print(f"\n  pre-merge rows kept for audit: out/dupes.json")
