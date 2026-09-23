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

# When each entry first appeared, from cache/_first_seen.json (first_seen.py).
# ⚠ A value of None is BASELINE — present before the record began — and is not
# the same as a missing key. Both render as "no date" here, but the distinction
# is what stops first_seen.py restamping 3,070 entries every run; see its
# docstring. Absent file degrades to no dates at all, which costs the "recently
# added" ordering and nothing else.
try:
    with open(f"{OUT}/cache/_first_seen.json") as _fh:
        _FIRST_SEEN = json.load(_fh)
except Exception:
    _FIRST_SEEN = {}


def _fs_ident(r):
    """Must match first_seen.ident() exactly, or every entry reads as undated."""
    return r.get("repo_key") or "%s|%s" % (r.get("name"), r.get("source"))
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
        "fs": _FIRST_SEEN.get(_fs_ident(r)),
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
        # No "rec" key: the Recommended stamp is retired (2026-08-14). It read
        # as one claim but was fed by two sources making DIFFERENT ones:
        #   FR/sill (668) - a real publisher assertion. SILL *is* France's
        #     interministerial list of software recommended to public agents,
        #     so harvest.py sets the flag on every row and says so in `note`.
        #   DE/opensource.muenchen.de (85) - OUR inference, not Munich's claim:
        #     `recommended_for_gov = not built`. Munich asserts "in production
        #     use at the City of Munich", which is ADOPTION; the stamp turned
        #     that into an ENDORSEMENT, and inverted it on the way, since
        #     software Munich actually BUILT got no stamp at all.
        # This is the case `wikidata_via` exists to prevent - an inferred claim
        # indistinguishable from a publisher-asserted one - and there is no
        # `recommended_via` to separate them. Dedupe also dropped 70 of the 753
        # flags, because recommended_for_gov rides the survivor and is not in
        # UNION_LIST, so the pill was inconsistent as well as ambiguous.
        # The data is untouched: catalog.json keeps recommended_for_gov and
        # export_json.py still emits recommended_for_government.
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

# The "in English or translated" tile counts entries whose DISPLAYED description
# is English — publisher-supplied or machine-translated, both count.
#
# It used to be `n_en + n_tr` where n_en was "has a description and is not
# translated", i.e. it counted HAVING A DESCRIPTION and called that English. That
# overstated by 176: 175 Bulgarian descriptions (a deliberate call - they are
# mostly EU-funding grant references, not software summaries) and one German
# stray were all counted as English.
#
# Read desc_lang, NOT desc_src_lang: desc_src_lang is the language of the
# ORIGINAL, and openCode/NL entries carry a German or Dutch original alongside
# publisher-supplied English. Counting those as un-English is the same
# read-the-wrong-language-field mistake in the other direction.
_src = [r for r in c if not r.get("excluded")]          # 1:1 with _inc, same order
n_en = sum(1 for r in _src if (r.get("desc_lang") or "") == "en")
n_nodesc = sum(1 for r in _src if not (r.get("short_desc") or "").strip())
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

# ---- Recently added: the 10 newest ACTIVE entries, newest first.
#
# Ten, not the whole 119: a strip you can read is worth more than one you have to
# work through, and the full list is reachable by sorting the table on "Recently
# added" — which is why that sort option exists rather than a longer strip.
#
# Ties inside a date are broken by name so the order is deterministic; a run that
# adds 20 entries on one day would otherwise reshuffle the strip on every build
# for no reason, the same churn rule the committed JSON follows.
# ⚠ Tie-break must match the page's `recent` sort EXACTLY, or "See all, newest
# first" lands the reader somewhere the strip did not start. `reverse=True` on a
# (date, name) tuple reverses BOTH keys, so the strip led with VC Solar while the
# table led with bytype — same date, opposite name order. Sort by name ascending
# first, then stable-sort by date descending, which is what the JS does.
_dated = sorted((r for r in _inc if r.get("fs")), key=lambda r: r["n"].lower())
_dated.sort(key=lambda r: r["fs"], reverse=True)
NEWEST = json.dumps([
    {"n": r["n"], "c": r["c"], "s": r["s"], "fs": r["fs"],
     "u": r.get("u"), "d": (r.get("d") or "")[:110]}
    for r in _dated[:10]
])

DATA = json.dumps(rows, separators=(",", ":"))

# The Source country facet is BACK (2026-09-21), after being removed for two
# reasons that are worth recording because only one of them was ever true.
#
# 1. "Largely redundant with Source catalog (a catalogue belongs to one
#    country)." Half true. A catalogue belongs to one country, but a COUNTRY has
#    several catalogues: DE is openCode + Munich, FR is SILL +
#    awesome-codegouvfr. The removal comment named the cost itself —
#    "everything from Germany now means selecting openCode and Munich
#    separately" — and that is precisely the query a policy researcher asked for
#    in September, which is also why /by-country/ now exists. A facet that
#    unions the catalogues of one country is not redundant with picking them
#    one by one.
# 2. "The sidebar had grown taller than the viewport, which stopped it pinning."
#    True, and NOT fixed by removing the group: measured 2026-09-21 on the live
#    page at 1280x860, the sidebar was 887px against an 860px viewport — still
#    27px unreachable while pinned, with the facet already gone. The cause was
#    an unbounded `position:sticky` element, not the number of groups. `.side`
#    now carries max-height + overflow-y:auto so it scrolls internally, which
#    fixes the pre-existing overhang and makes the group count irrelevant.
#
# ⚠ The facet VALUE is the country CODE and is matched against r.cs, the full
# countries list, so an entry listed by catalogues in two countries is found
# under both. That is the case the old single-country `r.c` could not serve.
#
# ⚠ It is called SOURCE COUNTRY, not Country, and that wording is load-bearing:
# it is the country of the CATALOGUE that listed the software, not the tier of
# government that published it. Same caveat as /by-country/ and /sources.html.
_CC_FLAG = {(m.get("country") or ""): m.get("flag") or ""
            for m in _S.SOURCES.values() if m.get("country")}
# Label is the country NAME, not the code: "France", not "FR". The code is what
# the data joins on and stays the facet VALUE (matched against r.cs) — only the
# display changes. sources.py:COUNTRY_NAME owns the mapping so the page and any
# other consumer cannot disagree; a code with no name falls back to itself rather
# than rendering blank.
CCFACETS = json.dumps([[k, ("%s %s" % (_CC_FLAG.get(k, ""),
                                       _S.COUNTRY_NAME.get(k, k))).strip(), v]
                       for k, v in sorted(countries.items(), key=lambda x: -x[1])])

# The facet VALUE stays the bare label because it is matched against r.ss; only
# the display label carries the country. Entry cards keep the plain label.
_SRC_CC = {lbl: (_S.SOURCES.get(k) or {}).get("country")
           for k, lbl in SRC_LABEL.items() if (_S.SOURCES.get(k) or {}).get("country")}
SFACETS = json.dumps([[k, ("%s (%s)" % (k, _SRC_CC[k])) if k in _SRC_CC else k, v]
                      for k, v in sorted(sources.items(), key=lambda x: -x[1])])
LOPTS = "".join(f'<option value="{html.escape(k)}">{html.escape(k)} ({v})</option>'
                for k, v in licenses.most_common()
                ).encode("ascii", "xmlcharrefreplace").decode()

# Source catalog moved from a sidebar facet to a toolbar <select>, which is
# SINGLE-select — you can no longer union two catalogues. That was a deliberate
# trade: the Source country facet now answers the case it existed for ("all of
# Germany" rather than openCode + Munich ticked separately), and a 17-value list
# is a better dropdown than a 6-of-17 facet with a "Show all" expander.
#
# The option VALUE is the bare label, because it is matched against r.ss, and
# /sources.html links here as ?src=<label>. Those two must agree: both read
# sources.py SOURCES[key]["label"].
SOPTS = "".join(
    f'<option value="{html.escape(lbl)}">{html.escape(lbl)}'
    f'{" (" + _SRC_CC[lbl] + ")" if lbl in _SRC_CC else ""} ({n})</option>'
    for lbl, n in sorted(sources.items(), key=lambda kv: -kv[1])
).encode("ascii", "xmlcharrefreplace").decode()

# The set-aside toggle is SPLIT, because one label covered two unrelated claims
# and the project's own owner could not say what it meant. 384 entries have no
# description the publisher or GitHub could supply; 104 are judged not adoptable
# (forks, deployment recipes, CI plumbing, locale bundles, org meta). "Set aside"
# said neither. Counts are computed here so the labels cannot drift from the data.
n_ex_nodesc = sum(1 for r in rows if r["ex"] == "no-description")
n_ex_notsoft = sum(1 for r in rows if r["ex"] and r["ex"] != "no-description")


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

n_entries = len(_inc)
n_srcs = len(sources)
n_funcs = len(funcs)

SUBS = {
    "__DATA__": DATA,
    "__FFACETS__": FFACETS,
    "__SFACETS__": SFACETS,
    "__CCFACETS__": CCFACETS,
    "__NEWEST__": NEWEST,
    "__SOPTS__": SOPTS,
    "__N_EX_NODESC__": "{:,}".format(n_ex_nodesc),
    "__N_EX_NOTSOFT__": "{:,}".format(n_ex_notsoft),
    "__PFACETS__": PFACETS,
    "__LOPTS__": LOPTS,
    "__NENTRIES__": f"{n_entries:,}",
    "__N_ENTRIES__": f"{n_entries:,}",
    "__N_SOURCES__": str(n_srcs),
    "__N_PC__": f"{n_pc:,}",
    "__N_EN__": f"{n_en:,}",
    "__N_NODESC__": f"{n_nodesc:,}",
    "__N_FUNCS__": str(n_funcs),
    "__N_MULTI__": str(n_multi_cat),
    "__N_EX__": str(n_ex),
    "__ICON_CODE__": T.ICONS["code"],
    # no __ICON_SEAL__: its only use on this page was the retired Recommended
    # stamp. T.ICONS["seal"] stays - build_sources.py still stamps it.
    "__ICON_ALERT__": T.ICONS["alert"],
}

PAGE = (
    theme.head(
        "Government open source software catalog | govoss",
        f"{n_entries:,} open source entries harvested first-hand from {n_srcs} government "
        "catalogues worldwide, normalised onto one schema. Free JSON API at /entries.json "
        "- no key, no pagination.")
    + "<style>\n" + theme.FONT_FACE_CSS + theme.CSS + T.PAGE_CSS + "</style>\n"
    + theme.utility_bar() + theme.topbar("catalog")
    + T.BODY + theme.footer() + T.SCRIPT
)

for k, v in SUBS.items():
    PAGE = PAGE.replace(k, v)

# A missed placeholder is a silent visual bug - the page would render the raw
# token. Fail the build instead.
import re as _re
_left = sorted(set(_re.findall(r"__[A-Z_]{3,}__", PAGE)))
if _left:
    raise SystemExit(f"build_ui: unsubstituted placeholders {_left}")

theme.assert_variant_live(PAGE)
PAGE = PAGE.encode("ascii", "xmlcharrefreplace").decode()

path = f"{OUT}/catalogue.html"
open(path, "w").write(PAGE)
print(f"wrote {path}  ({len(PAGE)/1024:.0f} KB, {len(rows)} rows, "
      f"{sum(1 for r in rows if r['rp'])} with replaces)")
print(f"   design tokens: @wegovnyc/design-tokens v{theme.TOKENS_VERSION} (vendor/wegovnyc, brand=govoss)")
