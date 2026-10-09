"""Fetch the public-sector, academic and corporate OSPO lists into cache/ospos.json.

    python3 fetch_ospos.py

Three published lists, read from the route each one's own site is built from -
never a list govoss curates (the scope rule for sources applies here too):

  FLOSS-PSO Network (OSPO Alliance), https://floss-pso.network/public-sector-ospos/
      ONE YAML file merging each office's own YAML: all_public_sector_ospos.yaml.
      The OSPO list is CC0 (their footer). Every entry is "public sector", so
      it is GOVERNMENT unless named in ACADEMIC_FLOSS below.
  SustainOSS academic map, github.com/sustainers/academic-map (MIT)
      A Jupyter Book: one markdown page per institution, no data file. Its own
      index pages sort universities and research institutions under "## OSPOs"
      and other headings ("Labs", "Universities without OSPOs"); ONLY the "## OSPOs"
      sections are read - the map's classification, not ours (owner, 2026-10-07).
      Every academic-map entry is ACADEMIC, research institutions included.
  TODO Group OSPO landscape, github.com/todogroup/ospolandscape (Apache-2.0)
      landscape.yml, which landscape.todogroup.org (and todogroup.org's members
      page, an embed of it) is generated from. ONLY its "OSPO Adopter" category,
      minus the "Associate" subcategory (foundations and projects, not offices);
      every TODO Group member but one is also listed there. CORPORATE unless named
      in TODO_TYPES (owner, 2026-10-09); rows that are an office already listed
      from the other two are dropped by name in TODO_SAME_AS. Rows carry a name,
      a homepage and a Crunchbase link only - no country, no description.
      ⚠ The adopter subcategory is spelt with a CYRILLIC о ("OSPO Adоpter"): the
      category is matched by its ASCII name and the subcategory never by name.

Like a harvest source: a source that fails, or comes back under half its last
size, or (FLOSS-PSO) breaks the /ospos.json consumer contract in ospo_contract.py,
keeps its previous records and records the error; this script always
exits 0 (one flaky list must not block the weekly publish). /ospos shows each
list's fetch date, so a stale list is visible where people look.

Locations are not in any of the lists: ospos/locations.json (hand-placed, committed)
places each office for the map. An office with no location is still listed;
the page says how many are not on the map.
"""
import json
import os
import re
import sys
import time
import urllib.parse

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from harvest import get  # noqa: E402  (the tested fetcher: raises, never None)
import ospo_contract as C  # noqa: E402

OUT = os.path.join(HERE, "cache", "ospos.json")
LOCATIONS = os.path.join(HERE, "ospos", "locations.json")
NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

FLOSS_URL = "https://floss-pso.network/all_public_sector_ospos.yaml"
FLOSS_PAGE = "https://floss-pso.network/public-sector-ospos/"
AMAP_RAW = "https://raw.githubusercontent.com/sustainers/academic-map/HEAD/"
AMAP_REPO = "https://github.com/sustainers/academic-map/blob/main/"
AMAP_SITE = "https://sustainoss.org/academic-map/"
AMAP_INDEXES = ("universities/index.md", "research-institutions/index.md")

# FLOSS-PSO entries that are universities, by their key (the office's URL).
# Named, never guessed from a name - the same discipline as filters.py.
ACADEMIC_FLOSS = {
    "https://opentech.auth.gr/",   # Aristotle University of Thessaloniki
    "https://scienceouverte.univ-grenoble-alpes.fr/a-propos/cellule-data-grenoble-alpes",
}

TODO_RAW = "https://raw.githubusercontent.com/todogroup/ospolandscape/main/landscape.yml"
TODO_REPO = "https://github.com/todogroup/ospolandscape/blob/main/landscape.yml"
TODO_SITE = "https://landscape.todogroup.org/"

# TODO "OSPO Adopter" rows that are not companies, by their homepage URL (named,
# never inferred). Two state bodies are shown as government (owner, 2026-10-09);
# the six that are offices /ospos already lists from FLOSS-PSO or the academic map
# are dropped, mapped to the id they would duplicate.
TODO_TYPES = {
    "http://www.caict.ac.cn/": "government",          # China Academy for ICT (state)
    "https://www.ipa.go.jp/en/": "government",        # Innovation Platform Agency, Japan - the IPA's English name
                                                      # since 2026-06-05; before, Information-technology Promotion Agency
}
TODO_SAME_AS = {
    "https://opensource.muenchen.de/": "floss-opensource-muenchen-de-ospo-html",
    "https://ospo.gwu.edu/": "amap-george-washington",
    "https://drcc.library.jhu.edu/open-source-programs-office/": "amap-johns-hopkins-university",
    "https://www.rit.edu/about-rit": "amap-rit",
    "https://www.tcd.ie/innovation/OSPO/": "amap-trinity-college-dublin",
    "https://cross.ucsc.edu": "amap-university-of-california-santa-cruz",
}
# TODO Group's own OSPO case studies (todogroup.org, CC BY 4.0), by the cleaned
# landscape name - linked from the card, never copied. Index:
# https://todogroup.org/resources/case-studies/ (RIT's is the academic map's office).
TODO_CASE_STUDIES = {
    name: "https://todogroup.org/resources/case-studies/%s/" % slug for name, slug in (
        ("Autodesk", "autodesk"), ("Capital One", "capital-one"), ("Comcast", "comcast"),
        ("Dropbox", "dropbox"), ("Meta", "meta"), ("Microsoft", "microsoft"),
        ("National Instruments", "national-instruments"), ("Verizon Media", "oath"),
        ("Porsche", "porsche"), ("Red Hat", "red-hat"), ("Salesforce", "salesforce"),
        ("SAP", "sap"), ("Uber", "uber"),
    )
}

LICENCES = {"floss-pso": C.FLOSS_LICENCE,
            "academic-map": "MIT (github.com/sustainers/academic-map)",
            "todo-landscape": "Apache-2.0 (github.com/todogroup/ospolandscape)"}
PAGES = {"floss-pso": FLOSS_PAGE, "academic-map": AMAP_SITE, "todo-landscape": TODO_SITE}


def host_of(url):
    h = urllib.parse.urlparse(url or "").netloc.lower()
    return h[4:] if h.startswith("www.") else h


def slug(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", (s or "").lower())).strip("-")


def md_text(s):
    """Markdown inline -> plain text: [label](url) -> label, <url> -> url, *x* -> x."""
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s or "")
    s = re.sub(r"<(https?://[^>]+)>", r"\1", s)
    s = re.sub(r"[*_`]+", "", s)
    return re.sub(r"\s+", " ", s).strip()


def first_url(s):
    m = re.search(r"\]\((https?://[^)\s]+)\)", s or "") or re.search(r"<(https?://[^>\s]+)>", s or "") \
        or re.search(r"(https?://\S+)", s or "")
    return m.group(1).rstrip(").,") if m else None


# ------------------------------------------------------------ FLOSS-PSO
def parse_floss(doc):
    """{yaml path: {office url: record}} -> normalised records."""
    out = []
    for origin, block in (doc or {}).items():
        if not isinstance(block, dict):
            continue
        for url, r in block.items():
            if not isinstance(r, dict) or not r.get("name"):
                continue
            desc = r.get("description") or {}
            en = desc.get("en") if isinstance(desc, dict) else desc
            orig = next((v for k, v in desc.items() if k != "en"), None) if isinstance(desc, dict) else None
            code = r.get("code") or []
            out.append({
                "id": "floss-" + slug(host_of(url) + urllib.parse.urlparse(url).path),
                "name": str(r["name"]).strip(),
                "type": "academic" if url in ACADEMIC_FLOSS else "government",
                "country": str(r.get("country") or "").upper() or None,
                "url": url,
                "description": str(en or orig or "").strip(),
                "code": [c for c in (code if isinstance(code, list) else [code]) if isinstance(c, str)],
                "policy": r.get("floss_policy"),
                "email": r.get("email"),
                "created": str(r["created"]) if r.get("created") else None,
                "source": "floss-pso",
                "source_url": urllib.parse.urljoin(FLOSS_PAGE, origin) if not str(origin).startswith("http") else origin,
            })
    return out


# ------------------------------------------------------------ academic map
def ospo_section(index_md):
    """Relative .md links under the index's '## OSPOs' heading, in order."""
    m = re.search(r"^## OSPOs\s*$(.*?)(?=^## |\Z)", index_md, re.M | re.S)
    if not m:
        return []
    return re.findall(r"^\s*-\s*\[[^\]]+\]\(\./([^)]+\.md)\)", m.group(1), re.M)


def bullet(md, *labels):
    """The value of a header bullet in either style the map uses:
    `- *OSPO*: x`, `- **Website:** x`, `- **Open Source Program Office (OSPO):** x`."""
    for lab in labels:
        # [ \t]*, never \s*: \s spans the newline, so an EMPTY "- *Link*:" took the
        # next line's link (UC Santa Barbara got CURIOSS's site, 2026-10-07)
        m = re.search(r"^-[ \t]*\*{1,2}%s\*{0,2}[ \t]*:?\*{0,2}[ \t]*:?[ \t]*(\S.*)$" % re.escape(lab),
                      md, re.M | re.I)
        if m:
            return m.group(1).strip()
    return None


def parse_amap_entry(md, path):
    name = re.search(r"^#\s+(.+?)\s*$", md, re.M)
    name = re.sub(r"\s+Overview$", "", name.group(1)).strip() if name else path
    ospo_line = bullet(md, "OSPO", "Open Source Program Office (OSPO)")
    link = bullet(md, "Link", "Website")
    # CERN's page names its OSPO's own site in the OSPO bullet; prefer that
    url = first_url(ospo_line) or first_url(link)
    desc = ""
    sec = re.search(r"^## (?:General Description|Overview)\s*$(.*?)(?=^## |\Z)", md, re.M | re.S)
    if sec:
        paras = [p for p in re.split(r"\n\s*\n", sec.group(1)) if p.strip() and not p.strip().startswith("-")]
        if paras:
            desc = md_text(paras[0])
    note = md_text(ospo_line or "")
    if not re.sub(r"\[[^\]]*\]\([^)]*\)|<[^>]+>|[\s.,;]", "", ospo_line or ""):
        note = ""                     # the line is only a link ("[Website](...)"), not a note
    note = re.sub(r"^yes[.,]?\s*", "", note, flags=re.I)
    note = note[:1].upper() + note[1:]
    kind = "research" if path.startswith("research-institutions/") else "university"
    return {
        "id": "amap-" + slug(path.rsplit("/", 1)[-1][:-3]),
        "name": name,
        "type": "academic",
        "kind": kind,
        "country": None,            # the map gives none; ospos/locations.json does
        "url": url or AMAP_REPO + path,
        "description": desc[:600],
        "ospo_note": note[:300],
        "code": [], "policy": None, "email": None, "created": None,
        "source": "academic-map",
        "source_url": AMAP_REPO + path,
    }


def fetch_amap():
    out = []
    for idx in AMAP_INDEXES:
        index = get(AMAP_RAW + idx, raw=True).decode("utf-8")
        folder = idx.rsplit("/", 1)[0] + "/"
        paths = ospo_section(index)
        if not paths:
            raise RuntimeError("%s has no '## OSPOs' list - the page changed shape" % idx)
        for p in paths:
            md = get(AMAP_RAW + urllib.parse.quote(folder + p), raw=True).decode("utf-8")
            out.append(parse_amap_entry(md, folder + p))
    return out


def floss_contract(recs):
    """A new FLOSS-PSO list must keep the /ospos.json contract (ospo_contract.py)
    as it will be exported - each office placed from ospos/locations.json - or it
    is refused like a failed fetch: un.opensource.nyc reads these rows and throws
    on anything unexpected, so the last good copy is what they should keep seeing.
    A new office with no placement lands here: place it, and the next run takes it."""
    locs = json.load(open(LOCATIONS))["locations"]
    probs = []
    for r in recs:
        loc = locs.get(r["id"])
        if loc is None:
            probs.append("%s: not placed - add it to ospos/locations.json" % r["id"])
            loc = {"lat": 0, "lon": 0, "place": "-", "basis": "seat", "country": r.get("country")}
        probs += C.row_problems(dict(r, location=loc))
    ids = [r["id"] for r in recs]
    probs += ["%s: id is not unique" % i for i in sorted({i for i in ids if ids.count(i) > 1})]
    if probs:
        raise ValueError("contract: " + "; ".join(probs[:5]) + (" (+%d more)" % (len(probs) - 5)
                                                                    if len(probs) > 5 else ""))


def failed_state(prev, key, error, kept, now):
    """A source's state after a failed fetch. ok:false means "these rows are the last
    good copy, fetched at fetched_at": fetched_at and count stay those of the copy
    kept, never this attempt's. build_ospos.py publishes an example built by this
    same function (/ospos.example-failed.json), so the example cannot drift."""
    st = dict(prev or {})
    st.update({"ok": False, "error": error,
               "failed_at": now, "count": kept, "licence": LICENCES[key],
               "url": PAGES[key]})
    return st


# ------------------------------------------------------------ TODO landscape
def parse_todo(doc):
    """landscape.yml -> the OSPO Adopter rows, normalised. The subcategory is
    never matched by name (its "о" is Cyrillic): every subcategory of the
    "OSPO Adopter" category but "Associate" is read."""
    out = []
    for cat in (doc or {}).get("landscape") or []:
        if cat.get("name") != "OSPO Adopter":
            continue
        for sub in cat.get("subcategories") or []:
            if sub.get("name") == "Associate":
                continue
            for it in sub.get("items") or []:
                url = (it.get("homepage_url") or "").strip()
                if not it.get("name") or not url or url in TODO_SAME_AS:
                    continue
                name = re.sub(r"\s*\(Adopter\)\s*$", "", re.sub(r"\s+", " ", str(it["name"]))).strip()
                out.append({
                    "id": "todo-" + slug(name),
                    "name": name,
                    "type": TODO_TYPES.get(url, "corporate"),
                    "country": None,           # the landscape gives none; ospos/locations.json does
                    "url": url,
                    "description": "",
                    "case_study": TODO_CASE_STUDIES.get(name),
                    "crunchbase": it.get("crunchbase"),
                    "code": [], "policy": None, "email": None, "created": None,
                    "source": "todo-landscape",
                    "source_url": TODO_REPO,
                })
    return out


def merge(floss, amap, todo=()):
    """FLOSS-PSO wins a duplicate: same host is the same office. TODO rows that
    duplicate one were already dropped by TODO_SAME_AS (their hosts differ - the
    landscape often links a university or a company, not its office)."""
    hosts = {host_of(r["url"]) for r in floss}
    return floss + [r for r in amap if host_of(r["url"]) not in hosts] + list(todo)


def main():
    prev = {}
    try:
        prev = json.load(open(OUT))
    except Exception:
        pass
    prev_by = {}
    for r in prev.get("ospos") or []:
        prev_by.setdefault(r["source"], []).append(r)
    state = dict(prev.get("sources") or {})
    got = {}
    for key, fn in (("floss-pso", lambda: parse_floss(yaml.safe_load(get(FLOSS_URL, raw=True)))),
                    ("academic-map", fetch_amap),
                    ("todo-landscape", lambda: parse_todo(yaml.safe_load(get(TODO_RAW, raw=True))))):
        old = prev_by.get(key, [])
        try:
            recs = fn()
            if len(recs) < max(1, len(old) // 2):
                raise RuntimeError("%d records against %d last time" % (len(recs), len(old)))
            if key == "floss-pso":
                floss_contract(recs)
            got[key] = recs
            state[key] = {"ok": True, "fetched_at": NOW, "count": len(recs), "licence": LICENCES[key],
                          "url": PAGES[key]}
            print("    %s: %d OSPOs" % (key, len(recs)))
        except Exception as e:
            got[key] = old
            st = failed_state(state.get(key), key, "%s: %s" % (type(e).__name__, str(e)[:400]),
                              len(old), NOW)
            state[key] = st
            print("    %s: FAILED %s - keeping %d from the last good fetch" % (key, st["error"], len(old)))
    ospos = merge(got.get("floss-pso", []), got.get("academic-map", []), got.get("todo-landscape", []))
    with open(OUT, "w") as fh:
        json.dump({"sources": state, "ospos": ospos}, fh, indent=1, sort_keys=True, ensure_ascii=False)
    print("    %d OSPOs written (%d government, %d academic, %d corporate)"
          % (len(ospos), sum(r["type"] == "government" for r in ospos),
             sum(r["type"] == "academic" for r in ospos), sum(r["type"] == "corporate" for r in ospos)))


if __name__ == "__main__":
    main()
