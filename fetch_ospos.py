"""Fetch the public-sector and academic OSPO lists into cache/ospos.json.

    python3 fetch_ospos.py

Two published lists, read from the route each one's own site is built from -
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

Like a harvest source: a source that fails, or comes back under half its last
size, keeps its previous records and records the error; this script always
exits 0 (one flaky list must not block the weekly publish). /ospos shows each
list's fetch date, so a stale list is visible where people look.

Locations are not in either list: ospos/locations.json (hand-placed, committed)
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

OUT = os.path.join(HERE, "cache", "ospos.json")
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

LICENCES = {"floss-pso": "CC0 1.0 (the FLOSS-PSO Network's OSPO list)",
            "academic-map": "MIT (github.com/sustainers/academic-map)"}


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


def merge(floss, amap):
    """FLOSS-PSO wins a duplicate: same host is the same office."""
    hosts = {host_of(r["url"]) for r in floss}
    return floss + [r for r in amap if host_of(r["url"]) not in hosts]


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
                    ("academic-map", fetch_amap)):
        old = prev_by.get(key, [])
        try:
            recs = fn()
            if len(recs) < max(1, len(old) // 2):
                raise RuntimeError("%d records against %d last time" % (len(recs), len(old)))
            got[key] = recs
            state[key] = {"ok": True, "fetched_at": NOW, "count": len(recs), "licence": LICENCES[key],
                          "url": FLOSS_PAGE if key == "floss-pso" else AMAP_SITE}
            print("    %s: %d OSPOs" % (key, len(recs)))
        except Exception as e:
            got[key] = old
            st = dict(state.get(key) or {"licence": LICENCES[key]})
            st.update({"ok": False, "error": "%s: %s" % (type(e).__name__, str(e)[:200]),
                       "failed_at": NOW})
            state[key] = st
            print("    %s: FAILED %s - keeping %d from the last good fetch" % (key, st["error"], len(old)))
    ospos = merge(got.get("floss-pso", []), got.get("academic-map", []))
    with open(OUT, "w") as fh:
        json.dump({"sources": state, "ospos": ospos}, fh, indent=1, sort_keys=True, ensure_ascii=False)
    print("    %d OSPOs written (%d government, %d academic)"
          % (len(ospos), sum(r["type"] == "government" for r in ospos),
             sum(r["type"] == "academic" for r in ospos)))


if __name__ == "__main__":
    main()
