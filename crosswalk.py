#!/usr/bin/env python3
"""Enrich entry IDENTITY from Comptoir du Libre and Wikidata, so dedupe can merge more.

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

Wikidata itself is the second source, reached over SPARQL by URL, never by name:

  P1324 source code repository  -> our repo_key
  P856  official website        -> our landing

WHY NOT BY NAME. Tried and rejected, with the evidence:
  * Q936 (OpenStreetMap) has NO English label at all, so a label lookup misses
    the very case that prompted this.
  * "Audacity" resolves to three different QIDs and "Caddy" to two. An ambiguous
    identity is worse than none.
  * "about" matches a real software item called `about`. Generic repo names are
    everywhere in this catalogue (`docs`, `api`, `about`) and every one of them
    is a live false positive.

MEASURED YIELD, so nobody re-litigates this expecting more:
  * repo route:    ~51 QIDs stamped, but only ONE extra merge. By construction —
    entries sharing a repo URL ALREADY merge on repo URL, so a QID derived from
    that same URL tells dedupe nothing it did not know. The QIDs are still worth
    having as identity for consumers.
  * website route: ~27 QIDs, ~0 extra merges after the guard below.
The routes are worth running for identity coverage. They are NOT the fix for
duplicate entries — see the note at the end of this file.

URL PROPERTIES ARE IRIs, NOT STRINGS. `VALUES ?s { "https://..." }` silently
matches nothing; it has to be `VALUES ?s { <https://...> }`. And Wikidata stores
one exact spelling, so each candidate is expanded over scheme x www x trailing
slash before being sent.

Every stamped QID records `wikidata_via: comptoir:<how>` or `wikidata:<how>` so an
inferred identity is never mistaken for one the publisher asserted — the same rule
as translated vs desc_en, and inferred vs source categories.

Wikidata is BEST EFFORT: any failure warns and leaves the Comptoir result in
place. This is a gated step in run.sh, and a third-party SPARQL endpoint being
slow must never block the deploy.
"""
import json, os, re, collections

OUT = os.path.dirname(os.path.abspath(__file__))
SRC = f"{OUT}/out/comptoir.json"
API = "https://comptoir-du-libre.org/api/v1/softwares.json"
WD_REPO_CACHE = f"{OUT}/out/wikidata_repo.json"
WD_SITE_CACHE = f"{OUT}/out/wikidata_site.json"
WDQS = "https://query.wikidata.org/sparql"
UA = "govoss-catalog/0.2 (https://github.com/sarapis/govoss-catalog)"


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


def _sparql(query, timeout=300):
    """POST, not GET: the VALUES blocks below run to tens of kilobytes and a GET
    returns 414 URI Too Long."""
    import ssl, urllib.request, urllib.parse, certifi
    ctx = ssl.create_default_context(cafile=certifi.where())
    data = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
    req = urllib.request.Request(WDQS, data=data, headers={
        "User-Agent": UA,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return json.load(r)["results"]["bindings"]


def _qid(binding):
    return binding["value"].rsplit("/", 1)[-1]


def _variants(bare):
    """Wikidata records one exact spelling of a URL; we hold a normalised one.
    Expand ours over the axes norm() collapsed so an exact IRI match can hit."""
    return {f"{s}{w}{bare}{t}"
            for s in ("https://", "http://") for w in ("", "www.") for t in ("", "/")}


def _iri_safe(u):
    """A URL with a space, quote or angle bracket breaks SPARQL IRI syntax and
    fails the WHOLE chunk with a 400. Drop those rather than lose 200 good ones."""
    return u and not re.search(r'[\s<>"{}|\\^`]', u)


def software_qids(qids, chunk=300):
    """Keep only the QIDs that are software.

    LOAD-BEARING, not tidiness. A URL match says "this page belongs to that
    item", not "that item is the software". Of 92 homepages matched by P856, 17
    resolved to something that is not software at all: Q1199 is the German state
    of Hesse (an entry's landing was hessen.de), plus an Italian municipality, a
    Taiwanese ministry, an elementary school and an academic publisher. Each was
    a wrong identity, and a wrong identity is what makes dedupe merge unrelated
    entries later.

    Asked only about the handful of items a URL actually matched — the same
    constraint asked over all of Wikidata times out (504)."""
    if not qids:
        return set()
    out = set()
    qids = sorted(qids)
    for i in range(0, len(qids), chunk):
        vals = " ".join("wd:%s" % q for q in qids[i:i + chunk])
        rows = _sparql("SELECT DISTINCT ?item WHERE { VALUES ?item { %s } "
                       "?item wdt:P31/wdt:P279* wd:Q7397 . }" % vals)
        out |= {_qid(b["item"]) for b in rows}
    return out


def wikidata_by_repo(repo_keys):
    """P1324 source code repository -> QID, for repo urls we actually hold."""
    if os.path.exists(WD_REPO_CACHE):
        raw = json.load(open(WD_REPO_CACHE))
    else:
        rows = _sparql("SELECT ?item ?r WHERE { ?item wdt:P1324 ?r . }")
        raw = [[_qid(b["item"]), b["r"]["value"]] for b in rows]
        os.makedirs(f"{OUT}/out", exist_ok=True)
        json.dump(raw, open(WD_REPO_CACHE, "w"))
    idx = collections.defaultdict(set)
    for qid, url in raw:
        k = norm(url)
        if k:
            idx[k].add(qid)
    # One repo url claimed by two items is not an identity. Drop it.
    return {k: next(iter(v)) for k, v in idx.items() if len(v) == 1 and k in repo_keys}


def wikidata_by_site(sites, chunk=200):
    """P856 official website -> QID, asked only about homepages we hold."""
    if os.path.exists(WD_SITE_CACHE):
        found = {k: set(v) for k, v in json.load(open(WD_SITE_CACHE)).items()}
    else:
        found = collections.defaultdict(set)
        cands = sorted(s for s in sites if s)
        for i in range(0, len(cands), chunk):
            vals = " ".join("<%s>" % v for b in cands[i:i + chunk]
                            for v in _variants(b) if _iri_safe(v))
            if not vals:
                continue
            try:
                rows = _sparql("SELECT ?item ?s WHERE { VALUES ?s { %s } "
                               "?item wdt:P856 ?s . }" % vals)
            except Exception as ex:                       # one bad chunk, not the run
                print(f"   wikidata: website chunk {i // chunk} failed ({ex})")
                continue
            for b in rows:
                found[norm(b["s"]["value"])].add(_qid(b["item"]))
        os.makedirs(f"{OUT}/out", exist_ok=True)
        json.dump({k: sorted(v) for k, v in found.items()}, open(WD_SITE_CACHE, "w"))
    return {k: next(iter(v)) for k, v in found.items() if len(v) == 1}


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

    # ---- second source: Wikidata, by URL only. Best effort.
    active = [e for e in catalog if not e.get("excluded")]
    todo = [e for e in active if not e.get("wikidata")]
    try:
        repo_keys = {e["repo_key"] for e in todo if e.get("repo_key")}
        by_wd_repo = wikidata_by_repo(repo_keys)

        # A homepage shared by entries with DIFFERENT names is an ORGANISATION
        # site, not a product identity. Measured: umwelt.info is the official
        # website of one Wikidata item and the landing page of four unrelated
        # German repos (data-stories, journal-web-ui, metadaten, usage-stats-api),
        # so without this the four collapse into a single entry. A wrong merge is
        # worse than the missed merge it was meant to fix.
        site_names = collections.defaultdict(set)
        for e in active:
            s = norm(e.get("landing"))
            if s:
                site_names[s].add((e.get("name") or "").strip().lower())
        org_sites = {s for s, n in site_names.items() if len(n) > 1}

        want = {norm(e.get("landing")) for e in todo if norm(e.get("landing"))} - org_sites
        by_wd_site = wikidata_by_site(want)

        # A URL match says the page belongs to the item, not that the item is
        # software. Verify before stamping — see software_qids().
        ok = software_qids(set(by_wd_repo.values()) | set(by_wd_site.values()))
        dropped = len(set(by_wd_repo.values()) | set(by_wd_site.values())) - len(ok)
        by_wd_repo = {k: v for k, v in by_wd_repo.items() if v in ok}
        by_wd_site = {k: v for k, v in by_wd_site.items() if v in ok}

        for e in todo:
            if e.get("wikidata"):
                continue
            qid = how = None
            if e.get("repo_key") and e["repo_key"] in by_wd_repo:
                qid, how = by_wd_repo[e["repo_key"]], "repo"
            else:
                s = norm(e.get("landing"))
                if s and s not in org_sites and s in by_wd_site:
                    qid, how = by_wd_site[s], "website"
            if qid:
                e["wikidata"] = qid
                e["wikidata_via"] = f"wikidata:{how}"
                hits[f"wd_{how}"] += 1
        print(f"wikidata: {len(by_wd_repo)} repo urls, {len(by_wd_site)} websites resolved to "
              f"exactly one SOFTWARE item ({len(org_sites)} org-shared homepages skipped, "
              f"{dropped} matched items rejected as not software)")
    except Exception as ex:
        # A gated step must not fail the run because a third-party endpoint is
        # slow. Comptoir's stamps are already applied and stand on their own.
        print(f"wikidata: SKIPPED ({type(ex).__name__}: {ex})")

    json.dump(catalog, open(f"{OUT}/catalog.json", "w"), indent=1, default=str)
    total = sum(hits.values())
    have = sum(1 for e in catalog if e.get("wikidata"))
    print(f"stamped {total} QIDs: {dict(hits)}")
    print(f"entries with a QID: {have}/{len(catalog)} ({100*have/len(catalog):.1f}%)")
