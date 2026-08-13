#!/usr/bin/env python3
"""Generate a self-contained browsable page from catalog.json."""
import json, os, collections, html, importlib.util

OUT = os.path.dirname(os.path.abspath(__file__))
c = json.load(open(f"{OUT}/catalog.json"))
_spec = importlib.util.spec_from_file_location("taxonomy", f"{OUT}/taxonomy.py")
_tax = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_tax)
FUNCTIONS = _tax.FUNCTIONS
_ss = importlib.util.spec_from_file_location("sources", f"{OUT}/sources.py")
_S = importlib.util.module_from_spec(_ss); _ss.loader.exec_module(_S)
SRC_SITE = {k: v["site"] for k, v in _S.SOURCES.items()}

# Liveness is surfaced ON THE PAGE, not just in liveness.json — a monitor whose
# output lives only in a file nobody opens is the same failure as no monitor.
LIVE = {}
if os.path.exists(f"{OUT}/liveness.json"):
    LIVE = json.load(open(f"{OUT}/liveness.json")).get("repos", {})

# replaces.json -> "what can we stop paying for?". Matching UNIONS every key
# that matches the survivor name or any also_known_as, exactly as export_json.py
# does: dedupe can pick a different survivor name than a mapping was keyed on,
# and first-match-wins silently dropped what the other keys mapped. Keep these
# two in step - if this rule changes, change it in both.
_RAW = json.load(open(f"{OUT}/replaces.json"))
RMAP = {k.lower(): v for k, v in _RAW.items() if not k.startswith("_")}


def _replaces(r):
    out, seen = [], set()
    for cand in [r.get("name")] + list(r.get("also_known_as") or []):
        k = (cand or "").strip().lower()
        if not k or k not in RMAP:
            continue
        for m in RMAP[k]:
            pk = (m.get("product") or "").lower()
            if pk and pk not in seen:
                seen.add(pk)
                out.append(m)
    for m in (r.get("replaces") or []):
        if isinstance(m, dict):
            pk = (m.get("product") or "").lower()
            if pk and pk not in seen:
                seen.add(pk)
                out.append(m)
    return out


# 62% of mappings are NOT a like-for-like software swap - 21% are a paid tier or a
# hosted service, 53% are partial or adjacent. The page used to print all of them
# as a flat "Replaces X, Y, Z", which asserts exactly the category error the
# _README in replaces.json exists to prevent: Drupal does not replace Contentful's
# hosting, and ClamAV is not an endpoint-protection suite. Qualify anything that
# is not strong+software. The qualifier is display only - `rp` stays the clean
# product names so the search haystack and the "has replaces" filter are unchanged.
def _rp_qual(m):
    q = []
    k, conf = m.get("kind"), m.get("confidence")
    if k == "paid-tier":
        q.append("paid tier")
    elif k == "service":
        q.append("hosted service")
    if conf in ("partial", "adjacent"):
        q.append(conf)
    return ", ".join(q)

# Labels come from sources.py, which CLAUDE.md makes the single source of truth
# for them. The hand-written dict this replaces held 8 entries byte-identical to
# sources.py and covered none of the other 9, so those rendered in the sidebar
# and on entry cards as raw keys - "DK/os2" rather than "OS2 Denmark".
SRC_LABEL = {k: v["label"] for k, v in _S.SOURCES.items()}
CLAIM = {
    "IT/developers-italia": "built for public administration",
    "DE/openCode": "built for public administration",
    "EU/code.europa.eu": "built by EU institutions",
    "BE/iMio": "built by Walloon municipalities",
    "SE/offentligkod": "in use by Swedish public bodies",
    "FI/avoinkoodi": "Finnish public-sector project",
    "FR/awesome-codegouvfr": "curated French public-sector",
    "FR/sill": "recommended to public agents",
}

rows = []
for r in c:
    _rp = _replaces(r)
    rows.append({
        "n": r.get("name") or "(unnamed)",
        "c": (r.get("countries") or [r.get("country")])[0] if (r.get("countries") or r.get("country")) else "",
        "cs": r.get("countries") or ([r["country"]] if r.get("country") else []),
        "mc": r.get("merged_count", 1),
        "cc2": r.get("catalogue_count", 1),
        "ce": [{"l": (_S.SOURCES.get(x.get("source")) or {}).get("label", x.get("source")),
                "u": x.get("entry_url") or (_S.SOURCES.get(x.get("source")) or {}).get("site")}
               for x in (r.get("catalogue_entries") or [])],
        "aka": r.get("also_known_as") or [],
        "s": SRC_LABEL.get(r.get("source"), r.get("source")),
        "ss": [SRC_LABEL.get(x, x) for x in (r.get("sources") or [r.get("source")]) if x],
        "su": [SRC_SITE.get(x) for x in (r.get("sources") or [r.get("source")]) if x and SRC_SITE.get(x)],
        "t": r.get("tier"),
        "l": r.get("license") or "",
        "d": (r.get("short_desc") or "")[:230],
        "u": r.get("repo") or "",
        "h": r.get("landing") or "",
        "st": r.get("dev_status") or "",
        "o": r.get("repo_owner") or "",
        "g": (r.get("categories") or [])[:4],
        "ub": len(r.get("used_by") or []),
        "rec": 1 if r.get("recommended_for_gov") else 0,
        "fx": r.get("functions") or [],
        "tr": 1 if r.get("translated") else 0,
        "sl": r.get("desc_src_lang") or "",
        "qid": r.get("wikidata") or "",
        "ex": r.get("exclude_reason") or "",
        # rp and rpq are built from one pass so they cannot fall out of alignment
        "rp": [m.get("product") for m in _rp if m.get("product")],
        "rpq": [_rp_qual(m) for m in _rp if m.get("product")],
        # dead_since is only set after 2 consecutive dead observations, so the
        # page never shows a one-off 404 as "repo gone"
        "lv": (lambda v: "dead" if v.get("dead_since")
                    else ("archived" if v.get("archived") else ""))(
                    LIVE.get(r.get("repo_key") or "", {})),
    })
rows.sort(key=lambda x: (x["n"] or "").lower())
n_ex = sum(1 for r in rows if r["ex"])

# facet counts describe the DEFAULT view (excluded hidden), or the chips would
# advertise entries the list will not show
_inc = [r for r in rows if not r["ex"]]
countries = collections.Counter(cc for r in _inc for cc in (r["cs"] or [r["c"]]) if cc)
sources = collections.Counter(x for r in _inc for x in (r["ss"] or [r["s"]]) if x)
licenses = collections.Counter(r["l"] for r in _inc if r["l"])
n_pc = sum(1 for r in _inc if r["t"] == "publiccode")
n_repos = len({r["u"] for r in _inc if r["u"]})
n_tr = sum(1 for r in _inc if r["tr"])
n_en = sum(1 for r in _inc if r["d"] and not r["tr"])
funcs = collections.Counter(f for r in _inc for f in r["fx"])
n_dead = sum(1 for r in _inc if r["lv"] == "dead")
n_multi_cat = sum(1 for r in _inc if (r.get("cc2") or 1) > 1)
FFACETS = json.dumps([[k, FUNCTIONS[k], n] for k, n in funcs.most_common()])

# Proprietary products as a FACET, not a nav item: they are a way into the open
# source, not a peer of it. Clicking one filters the catalogue to the entries
# that replace it, which is the whole "what could replace Dropbox?" question
# answered in place. "Show all" leaves for /products.html, which is also the
# only place products with NO alternative can live - a facet yielding zero rows
# would just be broken. Ordered most-replaceable first, name breaking ties so
# the list is deterministic (most products have exactly one alternative).
prods = collections.Counter(p for r in _inc for p in (r["rp"] or []))
PFACETS = json.dumps([[k, k, n] for k, n in
                      sorted(prods.items(), key=lambda kv: (-kv[1], kv[0].lower()))])

DATA = json.dumps(rows, separators=(",", ":"))

# The Country facet is GONE — it was largely redundant with Source catalog (a
# catalogue belongs to one country) and the sidebar had grown taller than the
# viewport, which stopped it pinning. The country now rides on the source label
# instead, so nothing is lost from view.
#
# The facet VALUE stays the bare label because it is matched against r.ss; only
# the display label carries the country. Entry cards keep the plain label.
#
# What this does cost: an entry listed by catalogues in two countries can no
# longer be found by country alone, and "everything from Germany" now means
# selecting openCode and Munich separately. GLOBAL/EU are shown as-is.
_SRC_CC = {lbl: (_S.SOURCES.get(k) or {}).get("country")
           for k, lbl in SRC_LABEL.items() if (_S.SOURCES.get(k) or {}).get("country")}
SFACETS = json.dumps([[k, ("%s (%s)" % (k, _SRC_CC[k])) if k in _SRC_CC else k, v]
                      for k, v in sorted(sources.items(), key=lambda x: -x[1])])
LOPTS = "".join(f'<option value="{html.escape(k)}">{html.escape(k)} ({v})</option>'
                for k, v in licenses.most_common()
                ).encode("ascii", "xmlcharrefreplace").decode()


# --------------------------------------------------------------------------
# Presentation. The markup, CSS and JS live in _ui_template.py and theme.py as
# PLAIN strings with __PLACEHOLDER__ tokens, not f-strings, so no literal CSS or
# JS brace ever needs doubling. That was the single most common way this file
# broke. Substitution is explicit below and asserted after, so a typo'd token
# fails loudly instead of shipping "__N_ENTRIES__" to production.
# --------------------------------------------------------------------------
_th = importlib.util.spec_from_file_location("theme", f"{OUT}/theme.py")
theme = importlib.util.module_from_spec(_th); _th.loader.exec_module(theme)
_tp = importlib.util.spec_from_file_location("_ui_template", f"{OUT}/_ui_template.py")
T = importlib.util.module_from_spec(_tp); _tp.loader.exec_module(T)
_cn = importlib.util.spec_from_file_location("ctfg_nav", f"{OUT}/ctfg_nav.py")
ctfg_nav = importlib.util.module_from_spec(_cn); _cn.loader.exec_module(ctfg_nav)
NAV = ctfg_nav.load()

n_entries = len(_inc)
n_srcs = len(sources)
n_funcs = len(funcs)

SUBS = {
    "__DATA__": DATA,
    "__FFACETS__": FFACETS,
    "__SFACETS__": SFACETS,
    "__PFACETS__": PFACETS,
    "__LOPTS__": LOPTS,
    "__NENTRIES__": f"{n_entries:,}",
    "__N_ENTRIES__": f"{n_entries:,}",
    "__N_SOURCES__": str(n_srcs),
    "__N_PC__": f"{n_pc:,}",
    "__N_EN__": f"{n_en + n_tr:,}",
    "__N_FUNCS__": str(n_funcs),
    "__N_MULTI__": str(n_multi_cat),
    "__N_EX__": str(n_ex),
    "__ICON_CODE__": T.ICONS["code"],
    "__ICON_SEAL__": T.ICONS["seal"],
    "__ICON_ALERT__": T.ICONS["alert"],
}

PAGE = (
    theme.head(
        "Government open source software catalog | govoss",
        f"{n_entries:,} open source entries harvested first-hand from {n_srcs} government "
        "catalogues worldwide, normalised onto one schema. Free JSON API at /entries.json "
        "- no key, no pagination.")
    + "<style>\n" + theme.FONT_FACE_CSS + theme.CSS + T.PAGE_CSS + "</style>\n"
    + theme.utility_bar(NAV) + theme.topbar("catalog")
    + T.BODY + theme.footer(NAV) + T.SCRIPT
)

for k, v in SUBS.items():
    PAGE = PAGE.replace(k, v)

# A missed placeholder is a silent visual bug - the page would render the raw
# token. Fail the build instead.
import re as _re
_left = sorted(set(_re.findall(r"__[A-Z_]{3,}__", PAGE)))
if _left:
    raise SystemExit(f"build_ui: unsubstituted placeholders {_left}")

PAGE = PAGE.encode("ascii", "xmlcharrefreplace").decode()

path = f"{OUT}/catalogue.html"
open(path, "w").write(PAGE)
print(f"wrote {path}  ({len(PAGE)/1024:.0f} KB, {len(rows)} rows, "
      f"{sum(1 for r in rows if r['rp'])} with replaces)")
print(f"   ctfg tokens: v{theme.TOKENS_VERSION} (vendor/ctfg)")
