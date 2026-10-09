#!/usr/bin/env python3
"""Place the TODO landscape's OSPOs on the /ospos map, from Wikidata (CC0).

    python3 ospos/place_from_wikidata.py            # report only
    python3 ospos/place_from_wikidata.py --write    # add the found placements

MANUAL, like geo/build_geo.py - never in run.sh. The landscape gives each company
a Crunchbase link and no location; Crunchbase's own data comes with restrictive
reuse terms, so it is never copied. Instead the Crunchbase id is looked up as
Wikidata's "Crunchbase organization ID" (P2088), and the company's headquarters
(P159) gives the place, its coordinates (P625) and its country (P17 -> P297).
A row with no Crunchbase link, or no match, is tried by official website (P856).

ospos/locations.json stays the hand-placed source of truth: this script only
ADDS ids that have no entry (basis "hq", with `via` naming the Wikidata item),
never changes one, and prints what it could not place - place those by hand.
Re-run it when the landscape gains companies (the page names unplaced ones).
"""
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import certifi
import yaml

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import fetch_ospos as F  # noqa: E402

LOC = os.path.join(HERE, "ospos", "locations.json")
CTX = ssl.create_default_context(cafile=certifi.where())
UA = {"User-Agent": "govoss-catalog/ospos placement (https://govoss.cat; devin@sarapis.org)"}


def sparql(q, tries=4):
    """POST, and back off on 429/503 - the service answers those after heavy use
    (CLAUDE.md, crosswalk). Honours Retry-After; gives up loudly after `tries`."""
    data = urllib.parse.urlencode({"query": q, "format": "json"}).encode()
    for n in range(tries):
        try:
            req = urllib.request.Request("https://query.wikidata.org/sparql", data=data, headers=UA)
            with urllib.request.urlopen(req, timeout=120, context=CTX) as r:
                return json.load(r)["results"]["bindings"]
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503) or n == tries - 1:
                raise
            wait = int(e.headers.get("Retry-After") or 0) or 30 * (n + 1)
            print("   wikidata %d - waiting %ds" % (e.code, wait))
            time.sleep(min(wait, 180))


# Every CURRENT headquarters statement with its rank: not deprecated, no end time
# (P582). point() keeps the PREFERRED one when there are several - the first one
# returned put Google in Milan, Nokia in Mississauga, Tencent in the Caymans.
HQ = """
  ?item p:P159 ?st . ?st ps:P159 ?hq ; wikibase:rank ?rank .
  FILTER(?rank != wikibase:DeprecatedRank) FILTER NOT EXISTS { ?st pq:P582 ?end }
  ?hq wdt:P625 ?coord .
  OPTIONAL { ?hq wdt:P17 ?hc . ?hc wdt:P297 ?hcc . }
  OPTIONAL { ?item wdt:P17 ?ic . ?ic wdt:P297 ?icc . }
  ?hq rdfs:label ?hqLabel . FILTER(LANG(?hqLabel) = "en")
"""


def by_crunchbase(ids):
    vals = " ".join('"%s"' % i.replace('"', "") for i in ids)
    return sparql("SELECT ?cb ?item ?hqLabel ?coord ?hcc ?icc ?rank WHERE { VALUES ?cb { %s } "
                  "?item wdt:P2088 ?cb . %s }" % (vals, HQ))


def by_website(hosts):
    """Exact official-website IRIs (P856), in the spellings sites use - an indexed
    lookup. Comparing a computed host against every P856 timed out (HTTP 502)."""
    iri = {}
    for h in hosts:
        for pre in ("https://", "https://www.", "http://", "http://www."):
            for end in ("/", ""):
                iri[pre + h + end] = h
    vals = " ".join("<%s>" % u for u in iri)
    out = []
    for b in sparql("SELECT ?w ?item ?hqLabel ?coord ?hcc ?icc ?rank WHERE { VALUES ?w { %s } "
                    "?item wdt:P856 ?w . %s }" % (vals, HQ)):
        b["h"] = {"value": iri[b["w"]["value"]]}
        out.append(b)
    return out


def pref(b):
    return 0 if b.get("rank", {}).get("value", "").endswith("PreferredRank") else 1


def point(b):
    lon, lat = b["coord"]["value"].replace("Point(", "").rstrip(")").split()
    cc = (b.get("hcc") or b.get("icc") or {}).get("value")
    return {"lat": round(float(lat), 4), "lon": round(float(lon), 4), "place": b["hqLabel"]["value"],
            "basis": "hq", "country": cc, "via": "wikidata " + b["item"]["value"].rsplit("/", 1)[1]}


def main(write):
    rows = F.parse_todo(yaml.safe_load(F.get(F.TODO_RAW, raw=True)))
    locs = json.load(open(LOC))
    todo = [r for r in rows if r["id"] not in locs["locations"]]
    found = {}
    cb = {r["id"]: r["crunchbase"].rstrip("/").rsplit("/", 1)[1] for r in todo if r.get("crunchbase")}
    for i in range(0, len(cb), 200):                  # one query: be gentle
        chunk = dict(list(cb.items())[i:i + 200])
        hits = {}
        for b in sorted(by_crunchbase(chunk.values()), key=pref):
            hits.setdefault(b["cb"]["value"], b)        # the preferred HQ when there are several
        for rid, c in chunk.items():
            if c in hits:
                found[rid] = point(hits[c])
    rest = {r["id"]: F.host_of(r["url"]) for r in todo
            if r["id"] not in found and F.host_of(r["url"]) not in ("github.com", "")}
    if rest:
        hits = {}
        for b in sorted(by_website(sorted(set(rest.values()))), key=pref):
            hits.setdefault(b["h"]["value"], b)
        for rid, h in rest.items():
            if h in hits:
                found[rid] = point(hits[h])
    missing = sorted(r["id"] for r in todo if r["id"] not in found)
    nocc = sorted(k for k, v in found.items() if not v["country"])
    print("%d TODO rows, %d already placed, %d found on Wikidata, %d not found, %d with no country"
          % (len(rows), len(rows) - len(todo), len(found), len(missing), len(nocc)))
    for k in sorted(found):
        print("   %-45s %s, %s (%s)" % (k, found[k]["place"], found[k]["country"], found[k]["via"]))
    print("NOT FOUND - place by hand:", missing)
    print("NO COUNTRY - fill by hand:", nocc)
    if write:
        locs["locations"].update({k: v for k, v in found.items() if v["country"]})
        with open(LOC, "w") as fh:
            json.dump(locs, fh, indent=1, sort_keys=True, ensure_ascii=False)
            fh.write("\n")
        print("wrote %s" % LOC)


if __name__ == "__main__":
    main("--write" in sys.argv[1:])
