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
    and main() never raises.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fetch_ospos as F  # noqa: E402

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

    # ---- main(): fallback, error recorded, never raises
    tmp = tempfile.mkdtemp()
    real_out, real_get = F.OUT, F.get
    F.OUT = os.path.join(tmp, "ospos.json")
    pages = {F.AMAP_RAW + "universities/index.md": INDEX,
             F.AMAP_RAW + "research-institutions/index.md": "## OSPOs\n\n- [Beta](./beta.md)\n",
             F.AMAP_RAW + "universities/alpha.md": ALPHA, F.AMAP_RAW + "universities/beta.md": BETA,
             F.AMAP_RAW + "research-institutions/beta.md": BETA}
    import yaml as _y

    def ok_get(url, raw=False, **kw):
        if url == F.FLOSS_URL:
            return _y.safe_dump(FLOSS).encode()
        if url in pages:
            return pages[url].encode()
        raise OSError("no fixture for " + url)
    try:
        F.get = ok_get
        F.main()
        d = json.load(open(F.OUT))
        check("a clean fetch writes both lists", (d["sources"]["floss-pso"]["ok"],
              d["sources"]["academic-map"]["ok"], len(d["ospos"])), (True, True, 5))

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
        F.OUT, F.get = real_out, real_get

    for f in failed:
        print("FAIL  " + f)
    n = len(ran)
    print("\n%d/%d checks passed" % (n - len(failed), n))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
