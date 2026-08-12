#!/usr/bin/env python3
"""Enrich entry IDENTITY from Comptoir du Libre, so dedupe can merge more.

Runs BEFORE dedupe.py and adds nothing to coverage — it only fills in Wikidata
QIDs that entries were missing. dedupe unions on QID first and repo URL second,
so an entry with no QID can only merge with something sharing its exact repo URL.
That is why the same upstream tool listed by two catalogues with slightly
different repo URLs (angular.io vs angular.dev, a mirror vs the canonical) stays
split.

Comptoir du Libre (comptoir-du-libre.org, run by ADULLACT) is the one open source
that carries several identifiers on the SAME row: 780 entries, all with a
repository URL and a website, 270 with a Wikidata QID and 349 with a SILL id. So
it can bridge repo URL -> QID and SILL id -> QID.

Every stamped QID records `wikidata_via: comptoir` so an inferred identity is
never mistaken for one the publisher asserted — the same rule as translated vs
desc_en, and inferred vs source categories.
"""
import json, os, re, collections

OUT = os.path.dirname(os.path.abspath(__file__))
SRC = f"{OUT}/out/comptoir.json"
API = "https://comptoir-du-libre.org/api/v1/softwares.json"


def norm(url):
    """Same normalisation as harvest.norm_repo, kept local so this step has no
    import-time dependency on the harvester."""
    if not url or not isinstance(url, str):
        return None
    u = re.sub(r"^https?://", "", url.strip().rstrip("/"))
    u = re.sub(r"^www\.", "", u)
    u = re.sub(r"\.git$", "", u)
    u = re.sub(r"/-/(tree|blob)/.*$", "", u)
    u = re.sub(r"/(tree|blob)/.*$", "", u)
    return u.lower() or None


def load_comptoir():
    if os.path.exists(SRC):
        d = json.load(open(SRC))
    else:
        import ssl, urllib.request, certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
        req = urllib.request.Request(API, headers={"User-Agent": "govoss-catalog/0.2"})
        with urllib.request.urlopen(req, timeout=90, context=ctx) as r:
            d = json.load(r)
        os.makedirs(f"{OUT}/out", exist_ok=True)
        json.dump(d, open(SRC, "w"))
    rows = d if isinstance(d, list) else (d.get("softwares") or list(d.values())[0])
    if rows and isinstance(rows[0], dict) and "software" in rows[0]:
        rows = [r["software"] for r in rows]
    return rows


if __name__ == "__main__":
    rows = load_comptoir()
    catalog = json.load(open(f"{OUT}/catalog.json"))

    by_repo, by_sill, by_site, by_name = {}, {}, {}, {}
    for r in rows:
        qid = (r.get("wikidata") or "").strip() or None
        if not qid:
            continue
        for k, idx in ((norm(r.get("url_repository")), by_repo),
                       (norm(r.get("url_website")), by_site)):
            if k and k not in idx:
                idx[k] = qid
        if r.get("sill"):
            by_sill.setdefault(str(r["sill"]), qid)
        nm = (r.get("softwarename") or "").strip().lower()
        if nm:
            by_name.setdefault(nm, qid)

    print(f"comptoir: {len(rows)} rows -> {len(by_repo)} repo, {len(by_sill)} sill, "
          f"{len(by_site)} website, {len(by_name)} name keys carrying a QID")

    hits = collections.Counter()
    for e in catalog:
        if e.get("wikidata"):
            continue
        qid = None
        if e.get("repo_key") and e["repo_key"] in by_repo:
            qid, how = by_repo[e["repo_key"]], "repo"
        elif e.get("sill_id") is not None and str(e["sill_id"]) in by_sill:
            qid, how = by_sill[str(e["sill_id"])], "sill_id"
        elif norm(e.get("landing")) and norm(e["landing"]) in by_site:
            qid, how = by_site[norm(e["landing"])], "website"
        else:
            # Name matching is the LAST resort and only for an exact, full,
            # case-insensitive match against a Comptoir entry. Never fuzzy: the
            # Angular / AngularJS pair is exactly what fuzzy matching gets wrong,
            # and one is a substring of the other.
            nm = (e.get("name") or "").strip().lower()
            if nm and nm in by_name:
                qid, how = by_name[nm], "exact_name"
        if qid:
            e["wikidata"] = qid
            e["wikidata_via"] = f"comptoir:{how}"
            hits[how] += 1

    json.dump(catalog, open(f"{OUT}/catalog.json", "w"), indent=1, default=str)
    total = sum(hits.values())
    have = sum(1 for e in catalog if e.get("wikidata"))
    print(f"stamped {total} QIDs: {dict(hits)}")
    print(f"entries with a QID: {have}/{len(catalog)} "
          f"({100*have/len(catalog):.1f}%), {total} of them via comptoir")
