"""The /ospos.json consumer contract: what an outside reader may rely on.

un.opensource.nyc (repo sarapis/unnyc) snapshots /ospos.json, reads the
FLOSS-PSO offices (source == "floss-pso") and THROWS on anything unexpected.
What it relies on is written down here, once, and checked in three places:

  fetch_ospos.py   a new FLOSS-PSO list that breaks it is a FAILED fetch: the
                   last good copy is kept, sources["floss-pso"].ok goes false and
                   `error` names the rule. Upstream change never reaches them.
  build_ospos.py   refuses to write an /ospos.json that breaks it. Only our own
                   code or committed data (ospos/locations.json) can get here,
                   and the failed step stops the publish.
  test_ospos.py, test_built_pages.py   pin it, by sabotage.

Free to change, because they do not read them: human_page, about, created,
resources_case, kind, ospo_note, source_url, and any NEW key. A change to
anything checked below is a contract change: tell UNNYC first, then change
this file and the tests together.
"""
import re

# Exact strings. A licence is read by the consumer and checked verbatim.
FLOSS_LICENCE = "CC0 1.0 (the FLOSS-PSO Network's OSPO list)"
# govoss's OWN fields - id, type, location, resources_case, and country where
# the list gives none. CC0 because most FLOSS-PSO placements are un.opensource.nyc's,
# published CC0, and placing an office at a city is a fact we want reused freely
# (the rest of the site's data is CC BY 4.0; this file says which applies).
LICENCE = {"govoss_fields": "CC0 1.0, govoss (https://govoss.cat)",
           "lists": "each list's own: sources[*].licence"}

# The country codes in use. ISO 3166-1 alpha-2 except EL (Greece, the EU's code,
# as FLOSS-PSO writes it) and INT (an international or intergovernmental body).
# A new code is a contract change - add it here, deliberately.
COUNTRIES = {
    "DE": "Germany", "DK": "Denmark", "EL": "Greece (the EU's code; ISO is GR)",
    "ES": "Spain", "FR": "France", "GB": "United Kingdom", "IE": "Ireland",
    "INT": "an international or intergovernmental body", "LU": "Luxembourg",
    "NL": "Netherlands", "US": "United States",
}
TYPES = ("government", "academic")
BASES = {"seat": "the office's own city",
         "hq": "its parent organisation's headquarters - the point is approximate"}
ISO_UTC = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")


def _str(v):
    return isinstance(v, str) and v.strip() != ""


def _num(v, lo, hi):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and lo <= v <= hi


def location_problems(loc):
    if not isinstance(loc, dict):
        return ["location is not an object"]
    p = []
    if not _num(loc.get("lat"), -90, 90):
        p.append("location.lat is not a latitude")
    if not _num(loc.get("lon"), -180, 180):
        p.append("location.lon is not a longitude")
    if not _str(loc.get("place")):
        p.append("location.place is empty")
    if loc.get("basis") not in BASES:
        p.append("location.basis %r is not seat/hq" % loc.get("basis"))
    if loc.get("country") not in COUNTRIES:
        p.append("location.country %r is not a documented code" % loc.get("country"))
    return p


def row_problems(r):
    """One row's problems, as '<id>: <rule>'. A FLOSS-PSO row gets every rule;
    other rows the shape rules only (the academic map can lack a description,
    and an office not yet placed has no location - both designed states)."""
    rid = r.get("id") if _str(r.get("id")) else "<no id>"
    p = []
    if not _str(r.get("id")):
        p.append("id is empty")
    if not _str(r.get("source")):
        p.append("source is empty")
    if r.get("type") not in TYPES:
        p.append("type %r is not government/academic" % r.get("type"))
    for k in ("name", "url"):
        if not _str(r.get(k)):
            p.append("%s is empty" % k)
    for k in ("email", "policy"):
        if r.get(k) is not None and not isinstance(r.get(k), str):
            p.append("%s is neither a string nor null" % k)
    code = r.get("code")
    if not isinstance(code, list) or not all(isinstance(c, str) and re.match(r"^https?://\S+$", c)
                                             for c in code):
        p.append("code is not a list of URLs")
    if r.get("source") == "floss-pso":
        if not _str(r.get("description")):
            p.append("description is empty")
        if r.get("country") not in COUNTRIES:
            p.append("country %r is not a documented code" % r.get("country"))
        p += location_problems(r.get("location"))
    else:
        if r.get("country") is not None and r.get("country") not in COUNTRIES:
            p.append("country %r is not a documented code" % r.get("country"))
        if r.get("location") is not None:
            p += location_problems(r.get("location"))
    return ["%s: %s" % (rid, x) for x in p]


def doc_problems(doc):
    """Every way an exported /ospos.json breaks the contract; [] when it holds."""
    if not isinstance(doc, dict):
        return ["the document is not an object"]
    p = []
    if not (isinstance(doc.get("generated_at"), str) and ISO_UTC.match(doc["generated_at"])):
        p.append("generated_at is not an ISO 8601 UTC time")
    if doc.get("licence") != LICENCE:
        p.append("licence is not %r" % (LICENCE,))
    rows = doc.get("ospos")
    if not isinstance(rows, list):
        return p + ["ospos is not an array"]
    src = doc.get("sources")
    if not isinstance(src, dict):
        return p + ["sources is not an object"]
    f = src.get("floss-pso")
    if not isinstance(f, dict):
        p.append('sources["floss-pso"] is missing')
    else:
        if f.get("licence") != FLOSS_LICENCE:
            p.append('sources["floss-pso"].licence is %r' % f.get("licence"))
        if not _str(f.get("url")):
            p.append('sources["floss-pso"].url is empty')
        if not (isinstance(f.get("fetched_at"), str) and ISO_UTC.match(f["fetched_at"])):
            p.append('sources["floss-pso"].fetched_at is not an ISO time')
        n = sum(1 for r in rows if isinstance(r, dict) and r.get("source") == "floss-pso")
        if not (isinstance(f.get("count"), int) and not isinstance(f.get("count"), bool)
                and f["count"] == n):
            p.append('sources["floss-pso"].count %r is not the %d floss-pso rows' % (f.get("count"), n))
        if not isinstance(f.get("ok"), bool):
            p.append('sources["floss-pso"].ok is not a boolean')
    seen = set()
    for r in rows:
        if not isinstance(r, dict):
            p.append("a row is not an object")
            continue
        p += row_problems(r)
        if r.get("id") in seen:
            p.append("%s: id is not unique" % r.get("id"))
        seen.add(r.get("id"))
    return p
