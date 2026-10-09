#!/usr/bin/env python3
"""Regression test for fetch_ospos.py - the /ospos lists.

    python3 test_ospos.py

Offline: the fetcher's parsers run on small fixtures written in the shapes the
two real sources use, and main() runs against a stubbed get(). What it pins:

  * only the "## OSPOs" section of an academic-map index is read - "Labs" and
    "Universities without OSPOs" are the map's own NO (owner, 2026-10-07);
  * both header-bullet styles parse (`- *OSPO*:` and `- **Website:**`), and an
    EMPTY "- *Link*:" never borrows the next line's URL (UC Santa Barbara got
    CURIOSS's site that way);
  * notes: "Yes, in the Library." -> "In the Library."; a link-only line -> none;
  * FLOSS-PSO entries are government unless named in ACADEMIC_FLOSS;
  * a duplicate across the lists (same host) keeps the FLOSS-PSO record;
  * a failed or halved source keeps its previous records and records the error,
    and main() never raises;
  * THE /ospos.json CONSUMER CONTRACT (ospo_contract.py; un.opensource.nyc reads
    it and throws on anything unexpected): its exact licence strings and code
    sets, every rule failing when broken, ids stable for unchanged upstream
    entries, ok:false keeping fetched_at and count of the copy kept, and a
    FLOSS-PSO list that breaks the contract refused like a failed fetch.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fetch_ospos as F  # noqa: E402
import ospo_contract as C  # noqa: E402

# The FLOSS-PSO offices as of 2026-10-07: key URL in their YAML -> our id. A
# change to how ids are derived changes one of these, and breaks every reader
# that keys on them.
IDS_2026_10_07 = {
    'https://opensource.muenchen.de/ospo.html': 'floss-opensource-muenchen-de-ospo-html',
    'https://schleswig-holstein.de/open-source': 'floss-schleswig-holstein-de-open-source',
    'https://os2.eu': 'floss-os2-eu',
    'https://opentech.auth.gr/': 'floss-opentech-auth-gr',
    'https://code.gouv.fr': 'floss-code-gouv-fr',
    'https://cyber.gouv.fr/enjeux-technologiques/open-source/': 'floss-cyber-gouv-fr-enjeux-technologiques-open-source',
    'https://francetravail.io/opportunites-innovation/participer-initiatives-open-source': 'floss-francetravail-io-opportunites-innovation-participer-initiatives-open-source',
    'https://opensource.paris.fr': 'floss-opensource-paris-fr',
    'https://pcll.ac-dijon.fr': 'floss-pcll-ac-dijon-fr',
    'https://scienceouverte.univ-grenoble-alpes.fr/a-propos/cellule-data-grenoble-alpes': 'floss-scienceouverte-univ-grenoble-alpes-fr-a-propos-cellule-data-grenoble-alpes',
    'https://www.echirolles.fr/territoire-numerique': 'floss-echirolles-fr-territoire-numerique',
    'https://www.ign.fr/institut/des-donnees-et-logiciels-ouverts-au-service-de-la-nation': 'floss-ign-fr-institut-des-donnees-et-logiciels-ouverts-au-service-de-la-nation',
    'https://www.recia.fr': 'floss-recia-fr',
    'https://www.strasbourg.eu/strategie-logiciels-libres': 'floss-strasbourg-eu-strategie-logiciels-libres',
    'https://opensourcewerken.nl/': 'floss-opensourcewerken-nl',
    'https://developer.overheid.nl': 'floss-developer-overheid-nl',
    'https://undp.org/digital': 'floss-undp-org-digital',
    'https://cms.gov/digital-service/open-source-program-office': 'floss-cms-gov-digital-service-open-source-program-office',
}

INDEX = """# Universities

## OSPOs

The following universities have an office:

- [Alpha University](./alpha.md)
- [Beta Institute](./beta.md)

## Labs

- [Gamma State](./gamma.md)

## Universities without OSPOs

- [Delta University](./delta.md)
"""
ALPHA = """# Alpha University

- *OSPO*: Yes, in the Library.
- *Personnel*: A. Person
- *Link*:
- *Member of*: [CURIOSS](https://curioss.org/)

## General Description

Alpha's OSPO [supports](https://alpha.edu/x) *research* software.

## Core Objectives

- one
"""
BETA = """# Beta Institute Overview

- **Website:** [Beta](https://beta.org/)
- **Open Source Program Office (OSPO):** [Website](https://ospo.beta.org/)

## Overview

Beta runs an OSPO.
"""
FLOSS = {
    "yamls/a.yml": {"https://ospo.gov.example/": {
        "name": "Gov OSPO", "country": "fr", "email": "x@gov.example",
        "description": {"fr": "Bureau", "en": "Office"}, "code": ["https://code.example"],
        "created": "2024-01-01"}},
    "yamls/b.yml": {"https://opentech.auth.gr/": {
        "name": "AUTH OSPO", "country": "EL", "description": {"en": "Open tech"}, "email": "y"}},
}


# The TODO landscape's landscape.yml, in its real shape: the adopter subcategory
# is spelt "OSPO Ad\u043epter" (a Cyrillic о), exactly as upstream.
TODO = {"landscape": [
    {"name": "TODO Group Member", "subcategories": [
        {"name": "General", "items": [{"name": "Snowflake (Member)", "homepage_url": "https://snowflake.example/"}]}]},
    {"name": "OSPO Adopter", "subcategories": [
        {"name": "Associate", "items": [{"name": "CHAOSS (Associate)", "homepage_url": "https://chaoss.example/"}]},
        {"name": "OSPO Ad\u043epter", "items": [
            {"name": "Acme (Adopter)", "homepage_url": "https://acme.example/", "crunchbase": "https://www.crunchbase.com/organization/acme"},
            {"name": "China  Mobile (Adopter)", "homepage_url": "https://chinamobile.example/"},
            {"name": "City of Munich (Adopter)", "homepage_url": "https://opensource.muenchen.de/"},
            {"name": "Innovation Platform Agency Japan (Adopter)", "homepage_url": "https://www.ipa.go.jp/en/"},
            {"name": "Microsoft (Adopter)", "homepage_url": "https://opensource.microsoft.example/"},
        ]}]},
    {"name": "OSPO Tools", "subcategories": [
        {"name": "SCA", "items": [{"name": "SomeTool", "homepage_url": "https://tool.example/"}]}]},
]}


def main():
    failed, ran = [], []

    def check(label, got, want):
        ran.append(label)          # counted, never hard-coded: a stale n reports a phantom pass
        if got != want:
            failed.append("%s: expected %r, got %r" % (label, want, got))

    # ---- index: the "## OSPOs" section only
    check("only the ## OSPOs section is read", F.ospo_section(INDEX), ["alpha.md", "beta.md"])
    check("an index with no ## OSPOs section reads nothing", F.ospo_section("# X\n## Labs\n- [a](./a.md)\n"), [])

    # ---- entries
    a = F.parse_amap_entry(ALPHA, "universities/alpha.md")
    check("an empty Link does not borrow the next line's URL",
          a["url"], F.AMAP_REPO + "universities/alpha.md")
    check("'Yes, in the Library.' becomes 'In the Library.'", a["ospo_note"], "In the Library.")
    check("description is the first General Description paragraph, as text",
          a["description"], "Alpha's OSPO supports research software.")
    check("academic-map entries are academic", (a["type"], a["kind"]), ("academic", "university"))
    b = F.parse_amap_entry(BETA, "research-institutions/beta.md")
    check("the **Label:** style parses, and the OSPO's own link wins",
          b["url"], "https://ospo.beta.org/")
    check("a link-only OSPO line is not a note", b["ospo_note"], "")
    check("' Overview' is trimmed from a name", b["name"], "Beta Institute")
    check("research institutions are kind research", b["kind"], "research")

    # ---- FLOSS-PSO
    fl = F.parse_floss(FLOSS)
    by = {r["url"]: r for r in fl}
    check("FLOSS-PSO is government by default", by["https://ospo.gov.example/"]["type"], "government")
    check("an ACADEMIC_FLOSS office is academic", by["https://opentech.auth.gr/"]["type"], "academic")
    check("English description preferred", by["https://ospo.gov.example/"]["description"], "Office")
    check("country upper-cased", by["https://ospo.gov.example/"]["country"], "FR")

    # ---- merge: same host -> keep FLOSS-PSO
    dup = dict(a, url="https://www.opentech.auth.gr/about", id="amap-dup")
    merged = F.merge(fl, [dup, b])
    check("a duplicate (same host, www ignored) keeps the FLOSS-PSO record",
          sorted(r["id"] for r in merged), sorted([r["id"] for r in fl] + [b["id"]]))

    # ---- the contract's fixed values, written HERE as literals: the test must not
    # ask ospo_contract.py what they are, or a changed string would pass itself
    check("contract: the FLOSS-PSO licence string", C.FLOSS_LICENCE,
          "CC0 1.0 (the FLOSS-PSO Network's OSPO list)")
    check("contract: fetch_ospos stamps that licence", F.LICENCES["floss-pso"],
          "CC0 1.0 (the FLOSS-PSO Network's OSPO list)")
    check("contract: govoss's own licence object", C.LICENCE,
          {"govoss_fields": "CC0 1.0, govoss (https://govoss.cat)",
           "lists": "each list's own: sources[*].licence"})
    # nine codes and "corporate" added 2026-10-09 with TODO's corporate OSPOs; UY the
    # same day (Mercado Libre's principal office)
    check("contract: the documented country codes", sorted(C.COUNTRIES),
          ["AR", "BR", "CN", "DE", "DK", "EL", "ES", "FI", "FR", "GB", "IE", "IN", "INT", "JP",
           "KR", "LU", "NL", "SE", "TW", "US", "UY"])
    check("contract: the display name per code (UNNYC's headings)", C.COUNTRY_NAMES,
          {"DE": "Germany", "DK": "Denmark", "EL": "Greece", "ES": "Spain", "FR": "France",
                     "GB": "United Kingdom", "IE": "Ireland", "INT": "International",
                     "LU": "Luxembourg", "NL": "Netherlands", "US": "United States",
                     "AR": "Argentina", "BR": "Brazil", "CN": "China", "FI": "Finland",
                     "IN": "India", "JP": "Japan", "KR": "South Korea", "SE": "Sweden",
                     "TW": "Taiwan", "UY": "Uruguay"})
    check("contract: types", sorted(C.TYPES), ["academic", "corporate", "government"])
    check("contract: a corporate row with no description and no location is valid",
          C.row_problems({"id": "todo-x", "source": "todo-landscape", "type": "corporate",
                          "name": "X", "url": "https://x.example/", "description": "",
                          "email": None, "policy": None, "code": [], "country": None,
                          "location": None}), [])
    UNPLACED = {"id": "todo-x", "source": "todo-landscape", "type": "corporate", "name": "X",
                "url": "https://x.example/", "description": "", "email": None, "policy": None,
                "code": [], "country": None, "location": None}
    check("contract: placement is all or nothing outside FLOSS-PSO - a country with no "
          "location, or a location with no country, is a problem",
          [len(C.row_problems(dict(UNPLACED, **kw))) > 0 for kw in (
              {"country": "US"},
              {"location": {"lat": 1, "lon": 1, "place": "P", "basis": "hq", "country": "US"}},
              {"country": "US", "location": {"lat": 1, "lon": 1, "place": "P", "basis": "hq",
                                             "country": "US"}})],
          [True, True, False])
    check("contract: the about text states the per-source placement rule",
          all(x in open(os.path.join(HERE, "build_ospos.py")).read() for x in (
              "every FLOSS-PSO row (source 'floss-pso') has a ",
              "'academic-map' and 'todo-landscape' MAY have country null and location null")),
          True)
    check("contract: location bases", sorted(C.BASES), ["hq", "seat"])

    # ---- every rule fails when broken, on a document that holds
    LOC = {"lat": 48.1351, "lon": 11.582, "place": "Munich", "basis": "seat", "country": "DE"}
    ROW = {"id": "floss-a", "source": "floss-pso", "type": "government", "name": "A",
           "url": "https://a.example/", "description": "An office.", "email": None,
           "policy": "https://a.example/p", "code": ["https://github.com/a"], "country": "DE",
           "location": LOC}
    AROW = {"id": "amap-b", "source": "academic-map", "type": "academic", "name": "B",
            "url": "https://b.example/", "description": "", "email": None, "policy": None,
            "code": [], "country": None, "location": None}
    DOC = {"generated_at": "2026-10-07T20:54:31Z", "licence": dict(C.LICENCE),
           "country_codes": dict(C.COUNTRIES), "country_names": dict(C.COUNTRY_NAMES),
           "sources": {"floss-pso": {"licence": "CC0 1.0 (the FLOSS-PSO Network's OSPO list)",
                                     "url": "https://floss-pso.network/public-sector-ospos/",
                                     "fetched_at": "2026-10-07T20:10:41Z", "count": 1, "ok": True}},
           "ospos": [ROW, AROW]}
    check("contract: a valid document has no problems (an academic row may lack a "
          "description and, unplaced, a location)", C.doc_problems(DOC), [])

    def broken(path, value):
        d = json.loads(json.dumps(DOC))
        o = d
        for k in path[:-1]:
            o = o[k]
        if value is KeyError:
            del o[path[-1]]
        else:
            o[path[-1]] = value
        return C.doc_problems(d)
    for path, value in [
        (("generated_at",), "2026-10-07 20:54"), (("generated_at",), KeyError),
        (("licence",), {"govoss_fields": "CC BY 4.0"}), (("licence",), KeyError),
        (("sources",), []), (("ospos",), {}),
        (("country_codes",), KeyError), (("country_codes", "EL"), {"name": "Greece"}),
        (("country_codes", "IT"), "Italy"),
        (("country_names",), KeyError), (("country_names", "EL"), "Hellas"),
        (("country_names", "INT"), KeyError),
        (("sources", "floss-pso"), KeyError),
        (("sources", "floss-pso", "licence"), "CC0 1.0"),
        (("sources", "floss-pso", "url"), ""),
        (("sources", "floss-pso", "fetched_at"), None),
        (("sources", "floss-pso", "count"), 2), (("sources", "floss-pso", "count"), True),
        (("sources", "floss-pso", "ok"), "true"),
        (("ospos", 0, "id"), ""), (("ospos", 1, "id"), "floss-a"),
        (("ospos", 0, "source"), None), (("ospos", 0, "type"), "public"),
        (("ospos", 0, "name"), " "), (("ospos", 0, "url"), None),
        (("ospos", 0, "description"), ""), (("ospos", 0, "email"), 7),
        (("ospos", 0, "policy"), ["x"]), (("ospos", 0, "code"), "https://github.com/a"),
        (("ospos", 0, "code"), ["github.com/a"]),
        (("ospos", 0, "country"), "GR"), (("ospos", 0, "country"), None),
        (("ospos", 1, "country"), "XX"),
        (("ospos", 0, "location"), None), (("ospos", 0, "location", "lat"), "48.1"),
        (("ospos", 0, "location", "lat"), 91), (("ospos", 0, "location", "lon"), KeyError),
        (("ospos", 0, "location", "lon"), -181), (("ospos", 0, "location", "place"), ""),
        (("ospos", 0, "location", "basis"), "city"), (("ospos", 0, "location", "country"), "Germany"),
        (("ospos", 1, "location"), {"lat": 1}),
    ]:
        check("contract: %s = %r is a problem" % ("/".join(map(str, path)), value),
              len(broken(path, value)) > 0, True)

    # ---- failed_state(): the one writer of a failed source's state, also used for
    # the published /ospos.example-failed.json
    prev = {"ok": True, "fetched_at": "2026-10-07T20:10:41Z", "count": 18,
            "licence": "CC0 1.0 (the FLOSS-PSO Network's OSPO list)",
            "url": "https://floss-pso.network/public-sector-ospos/"}
    st = F.failed_state(prev, "floss-pso", "OSError: down", 18, "2026-10-14T07:01:00Z")
    check("failed_state: ok false, the copy kept's fetched_at and count, this attempt's "
          "failed_at, the error as given",
          st, dict(prev, ok=False, error="OSError: down", failed_at="2026-10-14T07:01:00Z"))
    check("failed_state: a source never fetched still gets licence, url and count",
          sorted(F.failed_state(None, "floss-pso", "OSError: down", 0, "2026-10-14T07:01:00Z")),
          ["count", "error", "failed_at", "licence", "ok", "url"])

    # ---- ids: derived from the office's URL alone, so stable for an unchanged
    # upstream entry whatever else about it, or its file, or the order, changes
    def floss_doc(urls, origin="yamls/x.yml", **extra):
        return {origin: {u: dict({"name": "N", "description": {"en": "D"}, "country": "fr"}, **extra)
                         for u in urls}}
    urls = list(IDS_2026_10_07)
    got = {r["url"]: r["id"] for r in F.parse_floss(floss_doc(urls))}
    check("ids: the 18 offices of 2026-10-07 keep their ids", got, IDS_2026_10_07)
    got2 = {r["url"]: r["id"] for r in F.parse_floss(floss_doc(
        list(reversed(urls)), origin="yamls/moved.yml", email="new@x", code=["https://c.example"],
        floss_policy="https://p.example", created="2030-01-01"))}
    check("ids: unchanged by order, the YAML file, or any other field", got2, got)
    check("ids: unique", len(set(got.values())), len(got))

    # ---- TODO landscape: only "OSPO Adopter", never "Associate"; the adopter
    # subcategory is spelt with a CYRILLIC о and must still be read
    T = F.parse_todo(TODO)
    tby = {r["name"]: r for r in T}
    g = lambda n, k: (tby.get(n) or {}).get(k, "<missing row>")   # a lost row FAILS, never crashes
    check("todo: only the OSPO Adopter rows, Associates and other categories skipped, "
          "the Cyrillic-named subcategory read",
          sorted(tby), ["Acme", "China Mobile", "Information-technology Promotion Agency, Japan (IPA)", "Microsoft"])
    check("todo: ' (Adopter)' trimmed and doubled spaces collapsed", "China Mobile" in tby, True)
    check("todo: an office already listed (TODO_SAME_AS) is dropped", "City of Munich" not in tby, True)
    check("todo: companies are corporate, a named state body government",
          (g("Acme", "type"), g("Information-technology Promotion Agency, Japan (IPA)", "type")),
          ("corporate", "government"))
    check("todo: a misnamed row (TODO_NAMES) gets the right name, keeps the id its listed "
          "name gives, and records that name; other rows carry no name_in_list",
          (g("Information-technology Promotion Agency, Japan (IPA)", "id"), g("Information-technology Promotion Agency, Japan (IPA)", "name_in_list"), "name_in_list" in tby.get("Acme", {"name_in_list": 1})),
          ("todo-innovation-platform-agency-japan", "Innovation Platform Agency Japan", False))
    fixed = F.parse_todo({"landscape": [{"name": "OSPO Adopter", "subcategories": [{"name": "x",
              "items": [{"name": "IPA Japan (Adopter)", "homepage_url": "https://www.ipa.go.jp/en/"}]}]}]})
    check("todo: once the landscape changes the name, the override no longer applies",
          [(r["name"], "name_in_list" in r) for r in fixed], [("IPA Japan", False)])
    check("todo: every TODO_NAMES row really renames (listed != right)",
          [u for u, (a, b) in F.TODO_NAMES.items() if a == b or not a or not b], [])
    check("todo: a TODO case study is joined by name, others have none",
          (g("Microsoft", "case_study"), g("Acme", "case_study")),
          ("https://todogroup.org/resources/case-studies/microsoft/", None))
    check("todo: row shape - id from the name, homepage as url, no description, its source",
          (g("Acme", "id"), g("Acme", "url"), g("Acme", "description"), g("Acme", "source"),
           g("Acme", "country")),
          ("todo-acme", "https://acme.example/", "", "todo-landscape", None))
    check("todo: its licence, read by consumers", F.LICENCES["todo-landscape"],
          "Apache-2.0 (github.com/todogroup/ospolandscape)")
    check("todo: every TODO_SAME_AS target is an id the other lists produce",
          sorted(v for v in F.TODO_SAME_AS.values() if not v.startswith(("floss-", "amap-"))), [])

    # ---- main(): fallback, error recorded, never raises
    tmp = tempfile.mkdtemp()
    real_out, real_get, real_locs, real_now = F.OUT, F.get, F.LOCATIONS, F.NOW
    F.OUT = os.path.join(tmp, "ospos.json")
    F.LOCATIONS = os.path.join(tmp, "locations.json")
    placed = {"floss-ospo-gov-example": {"lat": 48.85, "lon": 2.35, "place": "Paris", "basis": "seat",
                                         "country": "FR"},
              "floss-opentech-auth-gr": {"lat": 40.63, "lon": 22.94, "place": "Thessaloniki",
                                         "basis": "seat", "country": "EL"}}
    json.dump({"locations": placed}, open(F.LOCATIONS, "w"))
    pages = {F.AMAP_RAW + "universities/index.md": INDEX,
             F.AMAP_RAW + "research-institutions/index.md": "## OSPOs\n\n- [Beta](./beta.md)\n",
             F.AMAP_RAW + "universities/alpha.md": ALPHA, F.AMAP_RAW + "universities/beta.md": BETA,
             F.AMAP_RAW + "research-institutions/beta.md": BETA}
    import yaml as _y

    def ok_get(url, raw=False, **kw):
        if url == F.FLOSS_URL:
            return _y.safe_dump(FLOSS).encode()
        if url == F.TODO_RAW:
            return _y.safe_dump(TODO, allow_unicode=True).encode()
        if url in pages:
            return pages[url].encode()
        raise OSError("no fixture for " + url)
    try:
        F.get = ok_get
        F.main()
        d = json.load(open(F.OUT))
        check("a clean fetch writes all three lists", (d["sources"]["floss-pso"]["ok"],
              d["sources"]["academic-map"]["ok"], d["sources"]["todo-landscape"]["ok"],
              len(d["ospos"])), (True, True, True, 9))
        # the landscape fails like the other two: its last good rows are kept
        F.get = lambda url, raw=False, **kw: ((_ for _ in ()).throw(OSError("todo down"))
                                              if url == F.TODO_RAW else ok_get(url, raw=raw))
        F.main()
        dt = json.load(open(F.OUT))
        check("a failed TODO fetch keeps its last good rows, ok false, fetched_at unmoved",
              (sum(r["source"] == "todo-landscape" for r in dt["ospos"]),
               dt["sources"]["todo-landscape"]["ok"],
               dt["sources"]["todo-landscape"].get("fetched_at", "a") ==
               d["sources"]["todo-landscape"].get("fetched_at", "b")),
              (4, False, True))
        F.get = ok_get
        F.main()
        d = json.load(open(F.OUT))
        good = dict(d["sources"]["floss-pso"])
        # a later attempt has a later clock: what ok:false must NOT copy
        F.NOW = "2099-01-01T00:00:00Z"

        def broken(url, raw=False, **kw):
            if url == F.FLOSS_URL:
                raise OSError("down")
            return ok_get(url, raw=raw)
        F.get = broken
        F.main()
        d = json.load(open(F.OUT))
        check("a failed source keeps its previous records",
              sum(r["source"] == "floss-pso" for r in d["ospos"]), 2)
        check("...and records the failure where /ospos reads it",
              (d["sources"]["floss-pso"]["ok"], "down" in d["sources"]["floss-pso"]["error"]), (False, True))
        st = d["sources"]["floss-pso"]
        check("ok:false keeps fetched_at, count, licence and url of the copy kept; "
              "failed_at is the attempt",
              (st["fetched_at"], st["count"], st["licence"], st["url"], st["failed_at"]),
              (good["fetched_at"], 2, good["licence"], good["url"], "2099-01-01T00:00:00Z"))

        # a list that breaks the contract is refused like a failed fetch - here a
        # new office nobody has placed, and one in an undocumented country
        F.get = ok_get
        F.main()
        good = dict(json.load(open(F.OUT))["sources"]["floss-pso"])
        for label, extra in [("an unplaced new office", {"https://new.example/": {
                                 "name": "New", "country": "FR", "description": {"en": "x"}}}),
                             ("an undocumented country", None)]:
            doc = json.loads(json.dumps(FLOSS))
            if extra:
                doc["yamls/c.yml"] = extra
            else:
                doc["yamls/a.yml"]["https://ospo.gov.example/"]["country"] = "IT"
            F.get = lambda url, raw=False, _d=doc, **kw: (_y.safe_dump(_d).encode()
                                                          if url == F.FLOSS_URL else ok_get(url, raw=raw))
            F.main()
            d = json.load(open(F.OUT))
            st = d["sources"]["floss-pso"]
            check("contract break (%s) is refused: last good copy kept, ok false, "
                  "fetched_at unmoved, error names the contract" % label,
                  (sorted(r["id"] for r in d["ospos"] if r["source"] == "floss-pso"), st["ok"],
                   st["fetched_at"], st["count"], st["error"].startswith("ValueError: contract: ")),
                  (["floss-opentech-auth-gr", "floss-ospo-gov-example"], False,
                   good["fetched_at"], 2, True))
        F.get = ok_get
        F.main()                  # back to a good copy for the size checks below

        F.get = lambda url, raw=False, **kw: (_y.safe_dump({"yamls/a.yml": FLOSS["yamls/a.yml"]}).encode()
                                              if url == F.FLOSS_URL else ok_get(url, raw=raw))
        # one record against two last time is not "under half" - kept
        F.main()
        d = json.load(open(F.OUT))
        check("a list that halves exactly is still accepted",
              sum(r["source"] == "floss-pso" for r in d["ospos"]), 1)
        F.get = lambda url, raw=False, **kw: (_y.safe_dump({}).encode()
                                              if url == F.FLOSS_URL else ok_get(url, raw=raw))
        F.main()
        d = json.load(open(F.OUT))
        check("an emptied list is refused and the previous kept",
              (sum(r["source"] == "floss-pso" for r in d["ospos"]), d["sources"]["floss-pso"]["ok"]),
              (1, False))
    finally:
        F.OUT, F.get, F.LOCATIONS, F.NOW = real_out, real_get, real_locs, real_now

    for f in failed:
        print("FAIL  " + f)
    n = len(ran)
    print("\n%d/%d checks passed" % (n - len(failed), n))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
