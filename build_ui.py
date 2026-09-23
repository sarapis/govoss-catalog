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
_KNOWN = {p["name"] for p in json.load(open(f"{OUT}/proprietary.json"))["products"]}


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
        # A publisher-declared product with no proprietary.json record has no
        # anchor on /products.html to link to; export_json.py keeps it out of
        # by-product.json for the same reason. It stays in /entries.json.
        if isinstance(m, dict) and m.get("via") == "publiccode" and m.get("product") not in _KNOWN:
            continue
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
    """Qualifier PARTS, joined per language at render time (see _rpq_text)."""
    q = []
    k, conf = m.get("kind"), m.get("confidence")
    if k == "paid-tier":
        q.append("paid tier")
    elif k == "service":
        q.append("hosted service")
    if conf in ("partial", "adjacent"):
        q.append(conf)
    return q

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

# Variants (variants.py): an entry that is a version of another carries
# variant_of.ident. A variant with no mapping of its own INHERITS its core's,
# qualified "via <core>" - the same rule export_json.py applies, so the page and
# /entries.json agree. Keep the two in step.
_BY_IDENT = {}
for r in c:
    if not r.get("excluded"):
        _BY_IDENT.setdefault(_fs_ident(r), r)


def _core(r):
    vo = r.get("variant_of") if not r.get("excluded") else None
    return _BY_IDENT.get(vo["ident"]) if vo else None


rows = []
for r in c:
    _rp = _replaces(r)
    _cr = _core(r)
    _inh = bool(_cr is not None and not _rp)
    if _inh:
        _rp = _replaces(_cr)
    rows.append({
        "n": r.get("name") or "(unnamed)",
        "fs": _FIRST_SEEN.get(_fs_ident(r)),
        "dl": r.get("desc_lang"),
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
        # PARTS, not text: ["paid tier", ["via", "Consul Democracy"]]. Joined per
        # language in the render loop, so the qualifier is translated with the page.
        "rpq": [_rp_qual(m) + ([["via", _cr["name"]]] if _inh else [])
                for m in _rp if m.get("product")],
        "_id": _fs_ident(r), "_core": _fs_ident(_cr) if _cr is not None else None,
        "_rep": _BY_IDENT.get(_fs_ident(r)) is r,     # the row a core ident means
        # dead_since is only set after 2 consecutive dead observations, so the
        # page never shows a one-off 404 as "repo gone"
        "lv": (lambda v: "dead" if v.get("dead_since")
                    else ("archived" if v.get("archived") else ""))(
                    LIVE.get(r.get("repo_key") or "", {})),
    })
for x, r in zip(rows, c):
    if x["_core"] is not None and not _replaces(r):
        x["rpi"] = 1          # inherited rows; absent otherwise, ~27 KB saved
rows.sort(key=lambda x: (x["n"] or "").lower())

# Positions are only final after the sort. vo = index of the core row (or absent),
# vs = indices of a core's variants. The page folds a variant under its core
# whenever both are in the result set; see fold() in _ui_template.py.
_pos = {x["_id"]: i for i, x in enumerate(rows) if x["_rep"]}
for i, x in enumerate(rows):
    core = x.pop("_core")
    if core is not None and core in _pos:
        x["vo"] = _pos[core]
        rows[_pos[core]].setdefault("vs", []).append(i)
for x in rows:
    x.pop("_id"); x.pop("_rep")
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
# FFACETS (function facet labels) is built per language in render().

# Proprietary products as a FACET, not a nav item: they are a way into the open
# source, not a peer of it. Clicking one filters the catalogue to the entries
# that replace it, which is the whole "what could replace Dropbox?" question
# answered in place. "Show all" leaves for /products.html, which is also the
# only place products with NO alternative can live - a facet yielding zero rows
# would just be broken. Ordered most-replaceable first, name breaking ties so
# the list is deterministic (most products have exactly one alternative).
# Direct mappings only: an inherited row folds under its core on the page, so
# counting it would advertise more results than the facet returns.
prods = collections.Counter(p for r in _inc if not r.get("rpi") for p in (r["rp"] or []))
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
# Source label -> flag, for the entry cards. Keyed on the LABEL because that is
# what the card renders (r.ce[].l and r.ss), the same string /sources.html links
# on. Falls back to nothing rather than a placeholder: a wrong flag on a country
# claim is worse than no flag.
SRCFLAG = json.dumps({lbl: (_S.SOURCES.get(k) or {}).get("flag") or ""
                      for k, lbl in SRC_LABEL.items()})

_dated = sorted((r for r in _inc if r.get("fs")), key=lambda r: r["n"].lower())
_dated.sort(key=lambda r: r["fs"], reverse=True)
# ⚠ The description is carried ONLY when it is English. A card is 232px of prime
# space on the home page, and this strip is the one place a reader meets an entry
# with no context — showing them German there is worse than showing them nothing.
# The name, country, catalogue and date still identify it, and the full entry is
# one click away. Translations land on the next run, so a card can gain its
# description without any change here.
NEWEST = json.dumps([
    {"n": r["n"], "c": r["c"], "s": r["s"], "fs": r["fs"], "u": r.get("u"),
     "d": (r.get("d") or "")[:110] if r.get("dl") == "en" else ""}
    for r in _dated[:10]
])

# DATA is serialised per language in render(): only rpq differs between them.

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
# CCFACETS is built per language in render(), from these names or i18n/ca.json's.

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
import i18n
import re as _re

n_entries = len(_inc)
n_srcs = len(sources)
n_funcs = len(funcs)
_OUTFILE = {"en": "catalogue.html", "ca": "catalogue.ca.html"}


def _rpq_text(lang, parts):
    return ", ".join(i18n.t(lang, "via {name}", name=p[1]) if isinstance(p, list)
                     else i18n.t(lang, p) for p in parts)


def render(lang):
    """One language's page. Everything above is language-neutral and computed once;
    only labels, qualifiers and number formats change here. Order is load-bearing:
    markers resolve while __PLACEHOLDERS__ are intact, then values go in, then
    page links are pointed at this language's copies (i18n.py)."""
    N = lambda n: i18n.num(lang, n)
    data = json.dumps([dict(r, rpq=[_rpq_text(lang, q) for q in r["rpq"]]) for r in rows],
                      separators=(",", ":"))
    ffacets = json.dumps([[k, i18n.function(lang, k, FUNCTIONS[k]), n]
                          for k, n in funcs.most_common()])
    ccfacets = json.dumps([[k, ("%s %s" % (_CC_FLAG.get(k, ""),
                                           i18n.country(lang, k, _S.COUNTRY_NAME.get(k, k)))).strip(), v]
                           for k, v in sorted(countries.items(), key=lambda x: -x[1])])
    subs = {
        "__DATA__": data,
        "__FFACETS__": ffacets,
        "__SFACETS__": SFACETS,
        "__CCFACETS__": ccfacets,
        "__NEWEST__": NEWEST,
        "__SRCFLAG__": SRCFLAG,
        "__SOPTS__": SOPTS,
        "__N_EX_NODESC__": N(n_ex_nodesc),
        "__N_EX_NOTSOFT__": N(n_ex_notsoft),
        "__PFACETS__": PFACETS,
        "__LOPTS__": LOPTS,
        "__NENTRIES__": N(n_entries),
        "__N_ENTRIES__": N(n_entries),
        "__SUBMIT__": theme.submit_block(n_srcs, lang),
        "__N_SOURCES__": str(n_srcs),
        "__N_PC__": N(n_pc),
        "__N_EN__": N(n_en),
        "__N_NODESC__": N(n_nodesc),
        "__N_FUNCS__": str(n_funcs),
        "__N_MULTI__": str(n_multi_cat),
        "__N_EX__": str(n_ex),
        "__LANG__": lang,
        "__ICON_CODE__": T.ICONS["code"],
        # no __ICON_SEAL__: its only use on this page was the retired Recommended
        # stamp. T.ICONS["seal"] stays - build_sources.py still stamps it.
        "__ICON_ALERT__": T.ICONS["alert"],
    }
    page = (
        theme.head(
            i18n.t(lang, "Government open source software catalog | govoss"),
            i18n.t(lang, "{n} open source entries harvested first-hand from {k} government "
                         "catalogues worldwide, normalised onto one schema. Free JSON API at "
                         "/entries.json - no key, no pagination.", n=N(n_entries), k=n_srcs),
            lang=lang, route="/")
        + "<style>\n" + theme.FONT_FACE_CSS + theme.CSS + T.PAGE_CSS + "</style>\n"
        + theme.utility_bar(lang=lang) + theme.topbar("catalog", lang, "/")
        + T.BODY + theme.footer(lang=lang) + T.SCRIPT
    )
    page = i18n.markers(page, lang)
    for k, v in subs.items():
        page = page.replace(k, v)
    # A missed placeholder is a silent visual bug - the page would render the raw
    # token. Fail the build instead.
    left = sorted(set(_re.findall(r"__[A-Z_]{3,}__", page)))
    if left:
        raise SystemExit(f"build_ui: unsubstituted placeholders {left} ({lang})")
    page = i18n.links(page, lang)
    theme.assert_variant_live(page)
    page = page.encode("ascii", "xmlcharrefreplace").decode()
    path = f"{OUT}/{_OUTFILE[lang]}"
    open(path, "w").write(page)
    print(f"wrote {path}  ({len(page)/1024:.0f} KB, {len(rows)} rows, "
          f"{sum(1 for r in rows if r['rp'])} with replaces)")


for _lang in i18n.LANGS:
    render(_lang)
i18n.report("build_ui")
print(f"   design tokens: @wegovnyc/design-tokens v{theme.TOKENS_VERSION} (vendor/wegovnyc, brand=govoss)")
