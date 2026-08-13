#!/usr/bin/env python3
"""Seed proprietary.json + product_aliases.json from the NYC licence export.

Run once, by hand. The output is CHECKED IN and hand-maintained thereafter -
run.sh must not depend on api.databook.nyc, and the pipeline stays offline and
deterministic. Re-run only to re-seed from a newer export, then review the diff.

The correction tables below are DELIBERATELY explicit rather than heuristic.
A first pass without them put "nothing replaces Atlassian" and "nothing replaces
Elastic Search" on the page - both false, both caused by procurement records
naming a vendor family where the index names a product.
"""
import csv, json, collections, sys, os

# The NYC licence export is NOT vendored - it is NYC's to publish and the URL is
# the durable reference. Pass the CSV path, or set NYC_LICENCES.
#   curl -s https://api.databook.nyc/oce/licenses/export -o nyc.csv
SP = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("NYC_LICENCES", ""))
if not SP or not os.path.exists(SP):
    raise SystemExit(__doc__.strip().splitlines()[0] +
                     "\n\nusage: python3 %s <nyc_licences.csv>\n"
                     "  curl -s https://api.databook.nyc/oce/licenses/export -o nyc.csv"
                     % os.path.basename(__file__))

CUT = 1_000_000  # NYC contract value; selection signal only, never published

# Procurement records name a vendor or a variant spelling; the index names a
# product. Each of these was verified to resolve in by-product.json.
ALIASES = {
    "arcgis": ["ArcGIS Desktop"],
    "esri": ["ArcGIS Desktop"],
    "esri arcgis": ["ArcGIS Desktop"],
    "elastic search": ["Elasticsearch"],
    "socrata": ["Socrata Open Data"],
    "atlassian": ["Jira", "Confluence"],
    "informatica": ["Informatica PowerCenter"],
    "opentext": ["OpenText Documentum"],
    "alfresco": ["Alfresco Content Services Enterprise"],
}

# Not a software licence at all. A support contract, an advisory retainer or a
# payment processor is not something open source replaces, and listing it as an
# unfilled gap would be the same category error `kind` exists to prevent.
NOT_SOFTWARE = {
    "gartner": "IT research and advisory retainer",
    "ibm": "software maintenance and support contract",
    "microsoft": "technical support and maintenance contract",
    "paypal": "payment processing",
    "promise pay": "payment processing",
}

# The paid item is primarily CONTENT or a data feed. Open source software cannot
# substitute a legal-research corpus or a traffic dataset, so absence of an
# alternative here is a category fact, not a catalogue gap.
DATA_SERVICE = {
    "cyclomedia", "dataminr", "dun & bradstreet", "inrix", "leadsonline",
    "lexisnexis", "sanborn maps", "westlaw", "zencity",
}


def n(s):
    return (s or "").strip().lower()


def amt(r):
    try:
        return float(r["current_amount"] or 0)
    except ValueError:
        return 0.0


rows = list(csv.DictReader(open(SRC)))
bp = json.load(open("site/by-product.json"))
idx = {k.lower().strip(): k for k in bp}

spend, purpose = collections.defaultdict(float), {}
for r in rows:
    if (idx.get(n(r["product"])) or idx.get(n(r["family"]))
            or n(r["product"]) in ALIASES or n(r["family"]) in ALIASES):
        continue                                    # has an alternative already
    k = (r["family"] or r["product"]).strip()
    if not k or k == "(unidentified)" or n(k) in NOT_SOFTWARE:
        continue
    spend[k] += amt(r)
    p = (r["purpose"] or "").strip()
    if p and len(p) > len(purpose.get(k, "")):
        purpose[k] = p

picked = sorted((k for k, v in spend.items() if v >= CUT), key=str.lower)

json.dump({
    "_README": {
        "purpose": ("Alternate spellings and vendor-family names seen in procurement "
                    "records, mapped to the product name by-product.json uses."),
        "why": ("Matching is limited by NAMING, not by what the catalogue holds. Four "
                "spellings of Esri hid $13.5M of NYC spend that QGIS answers, and a first "
                "pass reported 'nothing replaces Atlassian'. These are synonyms, verified "
                "to resolve - not judgement calls, and never fuzzy-matched."),
        "shape": "alias (lowercased) -> list of canonical product names in by-product.json",
    },
    "aliases": {k: v for k, v in sorted(ALIASES.items())},
}, open("product_aliases.json", "w"), indent=1, ensure_ascii=True)

out = {
    "_README": {
        "purpose": ("Proprietary software known to be bought by government for which this "
                    "catalogue currently offers NO open source alternative. Published so a "
                    "gap reads as a gap rather than as an oversight."),
        "status": ("SEEDED AND PARTIAL. Absence from this list is not evidence a product is "
                   "unused; presence is not evidence no alternative exists anywhere - only "
                   "that none is mapped in replaces.json."),
        "provenance": ("Seeded 2026-08-13 from NYC's software licence export "
                       "(https://api.databook.nyc/oce/licenses/export), selecting products "
                       "with no replaces.json mapping. One jurisdiction, so the list is "
                       "NYC-shaped: US municipal and public-safety verticals are "
                       "over-represented relative to what other governments buy."),
        "why_no_amounts": ("Selection used NYC contract value as a significance filter "
                           "(>= $1M) but the figures are deliberately NOT stored or "
                           "published. Databook owns that data and publishes it better; "
                           "this catalogue is not a procurement-spend publisher."),
        "kind": {
            "software": ("a software product with no alternative mapped - a genuine "
                         "catalogue gap, and a candidate for replaces.json"),
            "data-service": ("the paid item is primarily CONTENT or a data feed. Open "
                             "source cannot substitute a legal-research corpus or a traffic "
                             "dataset, so 'no alternative' here is a category fact, not a gap"),
        },
        "excluded": ("Support contracts, advisory retainers and payment processing are left "
                     "out entirely - they are not software licences. See NOT_SOFTWARE in "
                     "scratchpad/gen_proprietary.py."),
        "how_to_extend": ("Add products here by hand, or re-seed from a newer export and "
                          "review the diff. A product that gains a replaces.json mapping "
                          "must be REMOVED from here - build_products.py fails if one "
                          "appears in both."),
    },
    "products": [
        {"name": k,
         "purpose": purpose.get(k, ""),
         "kind": "data-service" if n(k) in DATA_SERVICE else "software",
         "seen_in": ["us-nyc"]}
        for k in picked
    ],
}
open("proprietary.json", "w").write(json.dumps(out, indent=1, ensure_ascii=True))

kinds = collections.Counter(p["kind"] for p in out["products"])
print(f"proprietary.json : {len(picked)} products  {dict(kinds)}")
print(f"product_aliases.json: {len(ALIASES)} aliases -> "
      f"{len({x for v in ALIASES.values() for x in v})} canonical products")
