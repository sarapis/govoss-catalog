"""Build site/ospos.html (served at /ospos) + site/ospos.json.

Open source program offices - government, academic and corporate - from three
published lists that fetch_ospos.py reads into cache/ospos.json: the FLOSS-PSO
Network's public-sector OSPO list (CC0), the SustainOSS academic map (MIT) and
the TODO Group's OSPO landscape (Apache-2.0; corporate since 2026-10-09). Records
stay English on every language copy; only the chrome is translated.

The page is the "OSPO Atlas" (design handoff, 2026-10-13): under the shared page
header, three columns - a sidebar (search, then Type, which opens on Government, and the
other facets), the offices - one list sorted by software or A-Z, or, with "Group by
country" (off by default, owner 2026-10-13), in country sections - and a
world map of every office the filters show. The map never follows the list to a
country (owner, 2026-10-13): it stays where the reader puts it.
Everything is rendered here, so a reader without JavaScript gets every office,
grouped and sorted, with its details open; the script filters, sorts, expands
and drives the map. The map is inline SVG from the committed geo/ospo_frames.json
(one world map, Equal Earth; written by geo/build_geo.py); each office is placed
from ospos/locations.json - hand-placed, or for TODO's companies their Wikidata
headquarters (ospos/place_from_wikidata.py, `via`).

What the page derives, all from committed inputs, never fetched here:
  products  catalogue entries (catalog.json, set-aside rows skipped) whose repo
            sits under one of the office's code organisations - a URL fact
  fns       those products' functions (taxonomy.py's 19), most frequent first
  focus     FOCUS_RULES matched on the office's own name, description and note
  score     how many of its software entries govoss lists (len(products)). It SORTS
            the list (Most software, or A-Z) and shows on the card; there are no
            ranks (owner, 2026-10-13)
Logos and flags are local files in ospos/img/ (fetched by the MANUAL
ospos/fetch_images.py), copied to site/ospo-img/; a missing one falls back to
initials or the flag emoji. Icons are vendored Lucide (vendor/lucide/).

An office with Resources links to them: RESOURCE_CASE maps an office's URL to
its case in resources/ospo-resources.json, checked against that file.

No f-strings for markup: plain strings with __PLACEHOLDER__ tokens.
"""
import collections
import importlib.util
import json
import math
import os
import re
import shutil
import time

import fetch_ospos
import i18n
import ospo_contract as C
import sources as S
import taxonomy

OUT = os.path.dirname(os.path.abspath(__file__))
SITE = f"{OUT}/site"
NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

_th = importlib.util.spec_from_file_location("theme", f"{OUT}/theme.py")
theme = importlib.util.module_from_spec(_th); _th.loader.exec_module(theme)
_tp = importlib.util.spec_from_file_location("_ui_template", f"{OUT}/_ui_template.py")
T = importlib.util.module_from_spec(_tp); _tp.loader.exec_module(T)

# Type order (filters, the country bars): government first, as the site is about government.
TYPE_ORDER = ("government", "academic", "corporate")
# fill / tint / text and Lucide icon per type (the handoff's type colours)
TYPE_ICON = {"government": "landmark", "academic": "graduation-cap", "corporate": "building-2"}

# Lucide icon per function (taxonomy.FUNCTIONS) and per focus tag
FN_ICON = {
    "case-workflow": "workflow", "documents": "file-text", "web-content": "globe",
    "collaboration": "messages-square", "data-analytics": "bar-chart-3", "geospatial": "map",
    "identity-security": "shield-check", "citizen-services": "users",
    "finance-procurement": "receipt", "hr-workforce": "contact", "crm-service": "headset",
    "dev-tools": "terminal-square", "infrastructure": "server", "integration": "plug",
    "learning-knowledge": "book-open", "health-social": "heart-pulse",
    "environment-transport": "leaf", "office": "briefcase", "registers": "list",
}

# Focus tags: matched on the office's OWN words (name, description, note), English,
# whole-word starts. Government offices are public services by definition.
# ENGLISH keywords only: an office described in French, German or Dutch gets FEWER
# tags, never a wrong one. Add another language's words to a rule, never loosen one.
FOCUS = (
    ("research", "Research software", "flask-conical",
     r"\bresearch|\bscien|\breproducib"),
    ("education", "Education", "graduation-cap",
     r"\beducat|\bteach|\bstudent|\bcurricul|\bcourses?\b|\btraining\b"),
    ("policy", "Policy & guidance", "scroll-text",
     r"\bpolic(y|ies)\b|\bguidance\b|\bgovernance\b|\bcompliance\b|\bbest practices?\b"),
    ("sovereignty", "Digital sovereignty", "flag", r"\bsovereign"),
    ("community", "Community & commons", "handshake",
     r"\bcommunit|\bcommons\b|\becosystems?\b"),
    ("health", "Health", "heart-pulse", r"\bhealth|\bmedic|\bclinic|\bhospital"),
    ("publicsector", "Public services", "landmark",
     r"\bpublic (sector|services?|administrations?|bod(y|ies)|interest)\b|\bgovernments?\b|"
     r"\bmunicipal|\bcivic\b"),
)
FOCUS_KEYS = [k for k, *_ in FOCUS]

# An office's URL (its key in FLOSS-PSO) -> its case in resources/ospo-resources.json.
# Named, never guessed: UNDP is NOT the "un" case (that is the UN's OICT and the
# Open Source United community, a different office).
RESOURCE_CASE = {
    "https://opensource.muenchen.de/ospo.html": "munich",
    "https://opensource.paris.fr": "paris",
    "https://cms.gov/digital-service/open-source-program-office": "cms",
}

IMG = f"{OUT}/ospos/img"            # logo/<host>.png, flag/<code>.svg (ospos/fetch_images.py)
ICONS = json.load(open(f"{OUT}/vendor/lucide/icons.json", encoding="utf-8"))["icons"]


def esc(s):
    return ("" if s is None else str(s)).replace("&", "&amp;").replace(
        "<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def flag(cc):
    """Flag emoji for a country code, as /software shows them - the fallback when
    ospos/img/flag/ has no image. EL is the EU's code for Greece (its flag is GR);
    INT, an intergovernmental office, gets /software's Global sign."""
    cc = {"EL": "GR"}.get(cc or "", cc or "")
    if cc == "INT":
        return "\U0001F310"
    if len(cc) == 2 and cc.isalpha():
        return "".join(chr(0x1F1E6 + ord(ch) - ord("A")) for ch in cc.upper())
    return ""


def flag_file(cc):
    """ospos/img/flag/<code>.svg, by the flag's code (Greece's EL is gr)."""
    if not cc or cc in ("INT", "ZZ"):
        return None
    return "%s.svg" % {"EL": "gr"}.get(cc, cc.lower())


def equal_earth(lon, lat):
    """The projection geo/build_geo.py draws the world map in (Equal Earth). Pinned
    against the frame's `probe` by test_built_pages.py, so a drift between the two
    copies fails a check."""
    A1, A2, A3, A4, M = 1.340264, -0.081106, 0.000893, 0.003796, math.sqrt(3) / 2
    lam, phi = math.radians(lon), math.radians(lat)
    t = math.asin(M * math.sin(phi))
    t2, t6 = t * t, t ** 6
    x = 2 * math.sqrt(3) * lam * math.cos(t) / (3 * (A1 + 3 * A2 * t2 + t6 * (7 * A3 + 9 * A4 * t2)))
    return x, -t * (A1 + A2 * t2 + t6 * (A3 + A4 * t2))


def place(frames, lon, lat):
    """(frame, x, y) for the first frame whose rectangle holds the point, else None."""
    for k, fr in frames.items():
        x, y = equal_earth(lon, lat)
        x, y = x * fr["s"] + fr["ox"], y * fr["s"] + fr["oy"]
        rx, ry, rw, rh = fr["rect"]
        if rx <= x <= rx + rw and ry <= y <= ry + rh:
            return k, round(x, 1), round(y, 1)
    return None


def norm_url(u):
    """A forge URL compared by host and path: no scheme, www, case, trailing
    slash, or GitLab's /groups/ segment."""
    u = (u or "").split("://", 1)[-1].lower().rstrip("/")
    u = u[4:] if u.startswith("www.") else u
    return u.replace("/groups/", "/")


def host_of(u):
    h = (u or "").split("://", 1)[-1].split("/", 1)[0].lower()
    return h[4:] if h.startswith("www.") else h


def code_org(c):
    """A code link named by its account or group (ANSSI lists 13; "Code" x13 said nothing)."""
    seg = [x for x in c.split("://", 1)[-1].split("/")[1:] if x and x != "groups"]
    return seg[-1] if seg else c.split("://", 1)[-1]


def office_indices(r, catalog):
    """Positions in catalog.json of the entries whose repository sits under one of
    the office's code organisations. A URL fact, never a name guess; set-aside rows
    are skipped. build_ui.py maps the SAME positions onto its own (name-sorted) rows
    for /software?ospo=<id>, so the card's count is that view's."""
    orgs = [norm_url(c) for c in r.get("code") or []]
    orgs = [o for o in orgs if "/" in o]          # a bare host would claim a whole forge
    if not orgs:
        return []
    out = []
    for i, e in enumerate(catalog):
        if e.get("excluded"):
            continue
        repos = [e.get("repo")] + [x.get("repo_url") for x in e.get("catalogue_entries") or []]
        if any(norm_url(u).startswith(o + "/") for u in repos if u for o in orgs):
            out.append(i)
    return out


def office_products(r, catalog):
    return [catalog[i] for i in office_indices(r, catalog)]


def focus_of(r):
    text = " ".join(x for x in (r["name"], r.get("description"), r.get("ospo_note")) if x).lower()
    tags = [k for k, _l, _i, rx in FOCUS if re.search(rx, text)]
    if r["type"] == "government" and "publicsector" not in tags:
        tags.append("publicsector")
    if r.get("kind") == "research" and "research" not in tags:
        tags.insert(0, "research")
    return tags


def initials(name):
    """1-2 letters for a logo that is missing (the handoff's mono())."""
    n = re.sub(r"^(The|OSPO( de| at| of)?( la| l')?|Open Source Program(me)? Office( of| at)?( the)?)\s+",
               "", name, flags=re.I)
    words = re.sub(r"[^A-Za-z0-9À-ž ]", "", n).split()
    return "".join(w[0] for w in words[:2]).upper() or "?"


def icon(name, size=14, cls="at-i"):
    return ('<svg class="%s" width="%d" height="%d" aria-hidden="true" focusable="false">'
            '<use href="#li-%s"/></svg>' % (cls, size, size, name))


def sprite(names):
    return ('<svg class="at-sprite" aria-hidden="true" focusable="false" width="0" height="0">%s</svg>'
            % "".join('<symbol id="li-%s" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                      'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">%s</symbol>'
                      % (n, ICONS[n]) for n in sorted(names)))


def load():
    data = json.load(open(f"{OUT}/cache/ospos.json", encoding="utf-8"))
    locs = json.load(open(f"{OUT}/ospos/locations.json", encoding="utf-8"))["locations"]
    geo = json.load(open(f"{OUT}/geo/ospo_frames.json", encoding="utf-8"))
    res = json.load(open(f"{OUT}/resources/ospo-resources.json", encoding="utf-8"))
    catalog = json.load(open(f"{OUT}/catalog.json", encoding="utf-8"))
    if not data.get("ospos"):
        raise SystemExit("build_ospos: cache/ospos.json has no ospos - run fetch_ospos.py")
    return data, locs, geo, res, catalog


def derive(data, locs, geo, res, catalog):
    """Every office with its place, products, tags and score (its software in govoss)."""
    rcount = collections.Counter(r["case"] for r in res["resources"])
    fr = geo["frames"]["world"]
    os_ = [dict(r) for r in data["ospos"]]
    for r in os_:
        loc = locs.get(r["id"]) or {}
        r["_cc"] = r.get("country") or loc.get("country")
        r["_loc"] = loc
        case = RESOURCE_CASE.get(r["url"])
        r["_case"] = case if case and rcount.get(case) else None
        r["_ncase"] = rcount.get(case or "", 0)
        p = place(geo["frames"], loc["lon"], loc["lat"]) if loc.get("lat") is not None else None
        r["_xy"] = (p[1], p[2]) if p and p[0] == "world" else None
        r["_prod"] = office_products(r, catalog)
        fc = collections.Counter(f for e in r["_prod"] for f in e.get("functions") or []
                                 if f in taxonomy.FUNCTIONS)
        r["_fns"] = [f for f, _n in sorted(fc.items(), key=lambda kv: (-kv[1], kv[0]))]
        r["_focus"] = focus_of(r)
        y = str(r.get("created") or "")[:4]
        r["_year"] = int(y) if y.isdigit() else None
        r["_score"] = len(r["_prod"])     # what "Most software" sorts by (owner, 2026-10-13)
        h = host_of(r["url"])
        r["_logo"] = (h if h not in ("github.com", "gitlab.com") and h
                      and os.path.exists(f"{IMG}/logo/{h}.png") else None)
    return os_


def build(lang, data, os_, geo):
    _ = lambda msg, **kw: i18n.t(lang, msg, **kw)
    N = lambda n: i18n.num(lang, n)
    cname = lambda c: (i18n.country(lang, c, S.COUNTRY_NAME.get(c) or C.COUNTRY_NAMES.get(c, c))
                       if c and c != "ZZ" else _("Not yet placed"))
    fnlabel = lambda k: i18n.function(lang, k, taxonomy.FUNCTIONS[k])
    flabel = {k: _(lbl) for k, lbl, _i, _r in FOCUS}
    ficon = {k: ic for k, _l, ic, _r in FOCUS}
    tlabel = {"government": _("Government"), "academic": _("Academic"), "corporate": _("Corporate")}
    used = {"search", "layers", "plus", "minus", "rotate-ccw", "globe", "mail", "scroll-text",
            "file-check", "book-marked", "package", "sliders-horizontal", "x", "flask-conical"}
    used |= set(TYPE_ICON.values()) | set(FN_ICON.values()) | set(ficon.values())
    used |= {"github", "gitlab", "git-branch"}

    def flag_html(cc, cls):
        if cc == "ZZ":
            return ""
        f = flag_file(cc)
        if f and os.path.exists(f"{IMG}/flag/{f}"):
            return '<img class="%s" src="/ospo-img/flag/%s" alt="" width="26" height="18">' % (cls, f)
        e = flag(cc)
        return ('<span class="%s at-femoji" aria-hidden="true">%s</span>' % (cls, e)) if e else ""

    # ---- the cards, grouped by country (ZZ: not yet placed, always last)
    def card(r):
        t = r["type"]
        tl = _("Research") if r.get("kind") == "research" else tlabel[t]
        ti = "flask-conical" if r.get("kind") == "research" else TYPE_ICON[t]
        logo = ('<img src="/ospo-img/logo/%s.png" alt="" width="40" height="40" loading="lazy">'
                % esc(r["_logo"])) if r["_logo"] else ""
        meta = ['%s%s' % (icon(ti, 13, "at-i at-ti"), esc(tl)),
                esc(r["_loc"].get("place") or _("Location unknown"))]
        # its country beside the city, with the flag emoji, on every card (owner, 2026-10-13)
        if r["_cc"] and r["_cc"] != "ZZ":
            meta.append('<span class="at-ccm"><span class="at-cflag" aria-hidden="true">%s</span> %s</span>'
                        % (flag(r["_cc"]), esc(cname(r["_cc"]))))
        if r["_year"]:     # most lists give no year: say nothing then (owner, 2026-10-13)
            meta.append(esc(_("Since {y}", y=r["_year"])))
        tags = (['<span class="at-tag at-tfn">%s%s</span>' % (icon(FN_ICON[f], 12), esc(fnlabel(f)))
                 for f in r["_fns"]] +
                ['<span class="at-tag at-tfo">%s%s</span>' % (icon(ficon[f], 12), esc(flabel[f]))
                 for f in r["_focus"]])
        more = []
        if r.get("description"):
            more.append('<p class="at-desc">%s</p>' % esc(r["description"]))
        if r.get("ospo_note"):
            more.append('<p class="at-note">%s</p>' % esc(r["ospo_note"]))
        np_ = len(r["_prod"])
        # its software as ONE link to /software?ospo=<id>, never a list of repos
        if np_:
            more.append('<p class="at-swp"><a class="at-sw" href="/software?ospo=%s">%s%s</a></p>'
                        % (esc(r["id"]), icon("package", 15),
                           esc(_("{n} software entries in govoss", n=N(np_)) if np_ > 1
                               else _("1 software entry in govoss"))))
        links = ['<a class="at-web" href="%s" target="_blank" rel="noopener">%s%s</a>'
                 % (esc(r["url"]), icon("globe", 13), esc(_("Website")))]
        # one code profile on the card; the rest behind "+N", opened in the dialog.
        # The full list is in the card (hidden), so the page without JS still has it.
        code = r.get("code") or []
        def code_link(c, cls="at-code"):
            h = host_of(c)
            ic = "github" if "github" in h else "gitlab" if ("gitlab" in h or "opencode" in h) else "git-branch"
            return ('<a class="%s" href="%s" target="_blank" rel="noopener">%s<span>%s</span>'
                    '<small>%s</small></a>' % (cls, esc(c), icon(ic, 13), esc(code_org(c)), esc(h)))
        if code:
            links.append(code_link(code[0]))
        if len(code) > 1:
            links.append('<button type="button" class="at-codes-more" aria-haspopup="dialog" '
                         'data-n="%d" title="%s">%s</button>'
                         % (len(code), esc(_("All {n} code profiles", n=N(len(code)))),
                            esc(_("+{n} more", n=N(len(code) - 1)))))
        if r.get("policy"):
            links.append('<a href="%s" target="_blank" rel="noopener">%s%s</a>'
                         % (esc(r["policy"]), icon("scroll-text", 13), esc(_("Open source policy"))))
        if r.get("case_study"):
            links.append('<a href="%s" target="_blank" rel="noopener">%s%s</a>'
                         % (esc(r["case_study"]), icon("file-check", 13), esc(_("TODO Group case study"))))
        if r.get("email"):
            links.append('<a href="mailto:%s">%s%s</a>' % (esc(r["email"]), icon("mail", 13), esc(r["email"])))
        if r["_case"]:
            links.append('<a class="at-res" href="/resources?case=%s">%s%s</a>'
                         % (esc(r["_case"]), icon("book-marked", 13),
                            esc(_("{n} resources on how this office was built", n=N(r["_ncase"])))))
        more.append('<p class="at-links">%s</p>' % "".join(links))
        if len(code) > 1:
            more.append('<ul class="at-codes" hidden>%s</ul>'
                        % "".join('<li>%s</li>' % code_link(c, "at-codel") for c in code))
        return (
            '<article class="at-card %s" id="%s" data-type="%s" data-cc="%s" data-fns="%s" data-focus="%s"'
            ' data-code="%d" data-score="%d" data-name="%s">'
            '<div class="at-ch"><div class="at-logo" aria-hidden="true">%s%s</div>'
            '<div class="at-mid"><h3><button type="button" class="at-tgl" aria-expanded="false" '
            'aria-controls="%s-x">%s</button></h3><p class="at-meta">%s</p>%s</div>'
            '%s</div>'
            '<div class="at-more" id="%s-x" hidden>%s</div></article>'
            % (esc(t), esc(r["id"]), esc(t), esc(r["_cc"] or "ZZ"), " ".join(r["_fns"]),
               " ".join(r["_focus"]), 1 if r.get("code") else 0, r["_score"], esc(r["name"]),
               esc(initials(r["name"])), logo, esc(r["id"]), esc(r["name"]),
               '<span class="at-dot">&middot;</span>'.join(meta),
               ('<p class="at-tags">%s</p>' % "".join(tags)) if tags else "",
               # its software count, what "Most software" sorts by; nothing when none
               ('<div class="at-sc" title="%s"><span class="at-sn">%s</span><span class="at-sl">%s</span></div>'
                % (esc(_("{n} software entries in govoss", n=N(r["_score"])) if r["_score"] > 1
                       else _("1 software entry in govoss")), N(r["_score"]), esc(_("software"))))
               if r["_score"] else "",
               esc(r["id"]), "".join(more)))

    groups = collections.defaultdict(list)
    for r in os_:
        groups[r["_cc"] or "ZZ"].append(r)
    keys = sorted(groups, key=lambda c: (c == "ZZ", -len(groups[c]), cname(c)))
    secs = []
    for cc in keys:
        rs = sorted(groups[cc], key=lambda r: (-r["_score"], r["name"].lower()))
        tc = collections.Counter(r["type"] for r in rs)
        bar = "".join('<i class="%s" style="width:%.1f%%" title="%s"></i>'
                      % (t, tc[t] * 100 / len(rs), esc("%s %s" % (N(tc[t]), tlabel[t])))
                      for t in TYPE_ORDER if tc[t])
        secs.append('<section class="at-grp" data-cc="%s" data-name="%s" aria-labelledby="g-%s">'
                    '<div class="at-gh">%s<h2 id="g-%s">%s</h2><span class="at-gn">%s</span>'
                    '<span class="at-gbar" aria-hidden="true">%s</span></div>%s</section>'
                    % (cc, esc(cname(cc)), cc, flag_html(cc, "at-flag"), cc, esc(cname(cc)),
                       esc(_("{n} offices", n=N(len(rs))) if len(rs) > 1 else _("1 office")),
                       bar, "".join(card(r) for r in rs)))

    # ---- the sidebar: Type, Product category, Focus
    nt = collections.Counter(r["type"] for r in os_)
    fbtn = lambda f, v, ic, cls, label, n: (
        '<button type="button" class="at-fb" data-f="%s" data-v="%s" aria-pressed="false">%s'
        '<span class="at-fl">%s</span><span class="at-fn" data-n>%s</span></button>'
        % (f, v, icon(ic, 15, "at-i " + cls), esc(label), N(n)))
    types = (fbtn("type", "", "layers", "at-iall", _("All offices"), len(os_)) +
             "".join(fbtn("type", t, TYPE_ICON[t], "at-i" + t[:3], tlabel[t], nt[t]) for t in TYPE_ORDER))
    nf = collections.Counter(f for r in os_ for f in r["_fns"])
    fns = "".join(fbtn("fn", f, FN_ICON[f], "at-ifn", fnlabel(f), n)
                  for f, n in sorted(nf.items(), key=lambda kv: (-kv[1], fnlabel(kv[0]))))
    nfo = collections.Counter(f for r in os_ for f in r["_focus"])
    foc = "".join(fbtn("focus", f, ficon[f], "at-ifo", flabel[f], n)
                  for f, n in sorted(nfo.items(), key=lambda kv: (-kv[1], flabel[kv[0]])))

    vb = geo["viewbox"]
    fr = geo["frames"]["world"]
    nctry = len([c for c in keys if c not in ("ZZ", "INT")])
    cfg = {
        "vb": vb, "listw_key": "ospo-atlas2-listw",
        "pts": {r["id"]: r["_xy"] for r in os_ if r["_xy"]},
        "fns": sorted(nf), "focus": sorted(nfo),
        "L": {"all": _("{n} offices in {c} countries"), "some": _("{n} of {t} offices in {c} countries"),
              "all1": _("{n} offices in 1 country"), "some1": _("{n} of {t} offices in 1 country"),
              "offices": _("{n} offices"), "office": _("1 office"),
              "codes": _("{name}: code profiles"),
              "cluster": _("{n} offices here"), "moretags": _("{n} more tags - open the office to see them"),
              "thou": "." if lang == "ca" else ","},
    }
    subs = {
        "__SPRITE__": sprite(used), "__SEARCHI__": icon("search", 15), "__TYPES__": types, "__FNS__": fns, "__FOCUS__": foc,
        "__COUNT__": esc(_("{n} offices in 1 country", n=N(len(os_))) if nctry == 1
                         else _("{n} offices in {c} countries", n=N(len(os_)), c=N(nctry))),
        "__GROUPS__": "".join(secs), "__LAND__": fr["land"], "__VB__": " ".join(str(v) for v in vb),
        "__IPLUS__": icon("plus", 16), "__IMINUS__": icon("minus", 16), "__IRESET__": icon("rotate-ccw", 15),
        "__IFILT__": icon("sliders-horizontal", 14), "__IGROUP__": icon("globe", 14),
        "__CFG__": json.dumps(cfg, sort_keys=True).replace("</", "<\\/"),
        "__TODO_AT__": fetched(data, "todo-landscape", _), "__FLOSS_AT__": fetched(data, "floss-pso", _),
        "__AMAP_AT__": fetched(data, "academic-map", _),
        "__LANG__": lang,
    }
    page = (theme.head(
        _("OSPOs | govoss"),
        _("{n} open source program offices - {g} in government, {a} in universities and "
          "research institutes - with a map.", n=N(len(os_)), g=N(nt["government"]), a=N(nt["academic"])),
        lang=lang, route="/ospos")
        + "<style>\n" + theme.FONT_FACE_CSS + theme.CSS + T.PAGE_CSS + PAGE_CSS + "</style>\n"
        + theme.utility_bar(lang=lang) + theme.topbar("ospos", lang, "/ospos")
        + BODY + theme.footer(lang=lang) + SCRIPT)
    page = i18n.markers(page, lang)
    for k, v in subs.items():
        page = page.replace(k, v)
    left = sorted(set(re.findall(r"__[A-Z_]{3,}__", page)))
    if left:
        raise SystemExit("build_ospos: unsubstituted placeholders %s" % left)
    page = i18n.links(page, lang)
    theme.assert_variant_live(page)
    page = page.encode("ascii", "xmlcharrefreplace").decode()
    out = f"{SITE}/ospos.html" if lang == "en" else f"{SITE}/{lang}/ospos.html"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="ascii").write(page)
    print("ospos page [%s]: %d OSPOs (%d government, %d academic, %d corporate), %d on the map, "
          "%d with catalogue products (%.0f KB)"
          % (lang, len(os_), nt["government"], nt["academic"], nt["corporate"],
             sum(1 for r in os_ if r["_xy"]), sum(1 for r in os_ if r["_prod"]), len(page) / 1024))


def fetched(data, key, _):
    st = (data.get("sources") or {}).get(key) or {}
    when = (st.get("fetched_at") or "")[:10] or _("never")
    return when + ("" if st.get("ok", True) else " &middot; " + esc(_("last fetch failed, showing the previous list")))


def copy_images():
    """ospos/img/ -> site/ospo-img/ (logos by host, flags by code)."""
    dst = f"{SITE}/ospo-img"
    shutil.rmtree(dst, ignore_errors=True)
    if os.path.isdir(IMG):
        shutil.copytree(IMG, dst, ignore=shutil.ignore_patterns("*.json", "*.md"))


# Colours are the theme's roles where the handoff's value is one (ink #162e51,
# #2c4a73, #5A6A82, link #2E6EAE, page #FBFBFB, wells #f3f6fa, the type fills);
# the handoff's own surfaces are the --at-* below.
PAGE_CSS = """
.atlas{--at-sel:#E7EEF7;--at-track:#e7ecf3;--at-water:#EEF2F8;--at-land:#D5DDE8;--at-off:#9aa6b8;
  --at-line:rgba(22,46,81,.1);--at-line2:rgba(22,46,81,.16);--at-hover:rgba(22,46,81,.25);
  --at-sh:0 4px 16px rgba(27,42,74,.1);--at-sh2:0 12px 40px rgba(27,42,74,.12);
  --at-gov:var(--primary);--at-aca:var(--green);--at-cor:var(--corp);
  display:grid;grid-template-columns:272px minmax(380px,1fr) minmax(0,1.1fr);
  height:calc(100vh - 32px);height:calc(100dvh - 32px);min-height:600px;overflow:hidden;background:var(--bg);
  color:var(--ink);border:1px solid var(--at-line);border-radius:var(--r-card);font-family:var(--font-body);
  letter-spacing:0;}
/* inside the shared page container (theme), so its gutters are every page's: 40px, 20px on phones */
.at-wrap{margin-top:16px;}
.at-sprite{position:absolute;width:0;height:0;overflow:hidden;}
.at-i{flex:none;vertical-align:middle;}
:where(.atlas button){font:inherit;color:inherit;}
/* sidebar */
.at-side{display:flex;flex-direction:column;min-height:0;background:var(--surface);
  border-right:1px solid var(--at-line);}
.at-shead{padding:16px 20px 12px;}
.at-q{position:relative;}
.at-q .at-i{position:absolute;left:11px;top:50%;transform:translateY(-50%);color:var(--ink-faint);}
.at-q input{width:100%;font:inherit;font-size:13.5px;padding:8px 10px 8px 32px;border:1px solid var(--at-line2);
  border-radius:8px;background:var(--primary-tint);color:var(--ink);}
.at-sbody{flex:1;overflow-y:auto;overflow-x:hidden;padding:0 12px 16px;display:flex;flex-direction:column;
  gap:18px;font-family:var(--font-ui);}
.at-blk{display:flex;flex-direction:column;gap:2px;}
.at-lbl{padding:0 8px 4px;display:flex;justify-content:space-between;align-items:center;font-size:11px;
  font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-faint);margin:0;}
.at-lbl small{font-size:11px;font-weight:400;letter-spacing:0;text-transform:none;}
.at-link{font-size:12px;font-weight:600;padding:6px 8px;border:0;background:none;color:var(--primary);
  cursor:pointer;text-align:left;}
.at-link:hover{color:var(--primary-deep);}
.at-fb{display:flex;align-items:center;gap:9px;font-size:13px;padding:6px 8px;border:0;border-radius:8px;
  cursor:pointer;text-align:left;background:none;font-weight:500;}
.at-fb[data-f="type"]{padding:7px 8px;}
.at-fb:hover{background:var(--primary-tint);}
.at-fb.at-none{color:var(--ink-faint);} .at-fb.at-none .at-i{opacity:.45;}
.at-fb[aria-pressed="true"]{background:var(--at-sel);font-weight:700;}
.at-fl{flex:1;}
.at-fn{color:var(--ink-faint);font-size:12px;font-weight:500;}
.at-iall{color:var(--ink);} .at-igov{color:var(--at-gov);} .at-iaca{color:var(--at-aca);}
.at-icor{color:var(--at-cor);} .at-ifn{color:var(--primary);} .at-ifo{color:var(--ink-600);}
.at-chk{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--ink-600);cursor:pointer;padding:0 8px;}
/* list */
.at-list{display:flex;flex-direction:column;min-width:0;min-height:0;border-right:1px solid var(--at-line);}
.at-tool{display:flex;align-items:center;gap:12px;padding:14px 20px;border-bottom:1px solid var(--at-line);
  background:var(--surface);flex-wrap:wrap;font-family:var(--font-ui);}
.at-count{font-size:13px;color:var(--ink-600);}
.at-clear{font-size:13px;border:0;background:none;color:var(--primary);cursor:pointer;padding:0;}
.at-sp{flex:1;}
.at-ftog{display:none;align-items:center;gap:6px;font-size:12px;font-weight:600;padding:6px 10px;
  border:1px solid var(--at-line2);border-radius:8px;background:var(--surface);cursor:pointer;}
.at-seg{display:flex;border:1px solid rgba(22,46,81,.14);border-radius:8px;overflow:hidden;}
/* the sort and Group by country wrap TOGETHER, never one without the other */
.at-ctl{display:flex;align-items:center;gap:8px;margin-left:auto;}
.at-gtog{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;padding:6px 10px;
  border:1px solid rgba(22,46,81,.14);border-radius:8px;background:var(--surface);color:var(--ink);cursor:pointer;}
.at-gtog .at-i{color:var(--ink-600);}
.at-gtog[aria-pressed="true"]{background:var(--ink);border-color:var(--ink);color:var(--white);}
.at-gtog[aria-pressed="true"] .at-i{color:var(--white);}
.at-gtog:focus-visible{outline:2px solid var(--primary);outline-offset:2px;}
.at-flat{display:flex;flex-direction:column;gap:10px;padding:16px 0 12px;}
.at-ccm{white-space:nowrap;}
.at-seg button{font-size:12px;font-weight:600;padding:6px 10px;border:0;cursor:pointer;
  background:var(--surface);}
.at-seg button[aria-pressed="true"]{background:var(--ink);color:var(--white);}
.at-scroll{flex:1;overflow-y:auto;overflow-x:hidden;padding:0 20px 48px;}
.at-grp{display:flex;flex-direction:column;gap:10px;padding-bottom:12px;}
.at-gh{position:sticky;top:0;z-index:3;background:var(--bg);padding:16px 0 8px;display:flex;align-items:center;
  gap:10px;border-bottom:1px solid rgba(22,46,81,.08);}
.at-gh h2{font-size:19px;letter-spacing:-0.01em;}
.at-gn{font-family:var(--font-ui);font-size:12.5px;color:var(--ink-faint);flex:1;}
.at-gbar{width:80px;height:6px;border-radius:3px;overflow:hidden;display:flex;background:var(--at-track);flex:none;}
.at-gbar i{height:100%;}
.at-gbar .government{background:var(--at-gov);} .at-gbar .academic{background:var(--at-aca);}
.at-gbar .corporate{background:var(--at-cor);}
.at-flag{width:26px;height:18px;border-radius:3px;object-fit:cover;box-shadow:0 0 0 1px rgba(22,46,81,.12);flex:none;}
.at-femoji{box-shadow:none;width:auto;height:auto;font-size:18px;line-height:1;}
.at-card{background:var(--surface);border:1px solid var(--at-line);border-left:4px solid var(--at-gov);
  border-radius:12px;cursor:pointer;display:flex;flex-direction:column;transition:box-shadow .15s,border-color .15s;
  scroll-margin-top:64px;}
.at-card.academic{border-left-color:var(--at-aca);} .at-card.corporate{border-left-color:var(--at-cor);}
.at-card:hover,.at-card.hov{border-color:var(--at-hover);box-shadow:var(--at-sh);}
.at-card.government:hover,.at-card.government.hov{border-left-color:var(--at-gov);}
.at-card.academic:hover,.at-card.academic.hov{border-left-color:var(--at-aca);}
.at-card.corporate:hover,.at-card.corporate.hov{border-left-color:var(--at-cor);}
.at-card.at-open{border-color:var(--at-gov);box-shadow:var(--at-sh2);}
.at-card.academic.at-open{border-color:var(--at-aca);} .at-card.corporate.at-open{border-color:var(--at-cor);}
.at-ch{padding:12px 14px;display:grid;grid-template-columns:40px minmax(0,1fr) auto;gap:12px;align-items:start;}
.at-logo{position:relative;width:40px;height:40px;border-radius:10px;background:var(--at-sel);color:var(--ink);
  display:flex;align-items:center;justify-content:center;font-family:var(--font-display);font-weight:700;
  font-size:14px;overflow:hidden;}
.academic .at-logo{background:var(--mint-100);color:var(--green-text);}
.corporate .at-logo{background:var(--corp-tint);color:var(--corp-text);}
.at-logo img{position:absolute;inset:0;width:40px;height:40px;object-fit:contain;background:var(--surface);}
.at-mid{display:flex;flex-direction:column;gap:6px;min-width:0;}
.at-mid h3{font-size:15px;font-weight:600;line-height:1.25;letter-spacing:-0.01em;text-wrap:pretty;}
.at-tgl{all:unset;cursor:pointer;color:var(--ink);}
.at-tgl:focus-visible{outline:2px solid var(--primary);outline-offset:2px;border-radius:3px;}
.at-meta{display:flex;align-items:center;gap:5px;flex-wrap:wrap;font-size:12px;color:var(--ink-faint);margin-top:-4px;}
.at-ti{color:var(--at-gov);} .academic .at-ti{color:var(--at-aca);} .corporate .at-ti{color:var(--at-cor);}
.at-dot{opacity:.5;}
.at-tags{display:flex;gap:5px;flex-wrap:wrap;}
.at-tag{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;padding:3px 8px;border-radius:6px;color:var(--ink);}
.at-tag.at-tmore{font-weight:600;color:var(--ink-600);background:var(--bg-alt);}
.at-tfn{background:var(--at-sel);} .at-tfn .at-i{color:var(--primary);}
.at-tfo{background:var(--primary-tint);} .at-tfo .at-i{color:var(--ink-600);}
.at-sc{display:flex;flex-direction:column;align-items:flex-end;gap:3px;min-width:64px;}
.at-sn{font-family:var(--font-display);font-weight:700;font-size:20px;line-height:1;}
.at-sl{font-family:var(--font-ui);font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
  color:var(--ink-faint);}
.at-more{padding:12px 14px 14px 66px;display:flex;flex-direction:column;gap:12px;border-top:1px solid rgba(22,46,81,.08);
  cursor:auto;}
.at-desc{font-size:13.5px;line-height:1.6;text-wrap:pretty;}
.at-note{font-size:12.5px;line-height:1.5;color:var(--ink-faint);}
 .at-nums b.at-zero{color:var(--at-off);}
.at-pmore{font-size:12px;color:var(--ink-faint);}
.at-links{display:flex;gap:6px;flex-wrap:wrap;}
.at-swp{margin:0;}
.at-sw{display:inline-flex;align-items:center;gap:8px;font-family:var(--font-ui);font-size:13.5px;font-weight:700;
  padding:9px 14px;border-radius:999px;background:var(--primary-tint);color:var(--primary-deep);text-decoration:none;
  border:1px solid var(--at-line2);}
.at-sw:hover,.at-sw:focus-visible{background:var(--at-sel);color:var(--ink);}
.at-sw::after{content:"\\2192";}
.at-links a small,.at-codel small{font-size:11px;color:var(--ink-faint);}
.at-codes-more{font:inherit;font-size:12.5px;font-weight:600;padding:6px 10px;border-radius:999px;cursor:pointer;
  border:1px solid var(--at-line2);background:var(--surface);color:var(--primary);}
.at-codes-more:hover,.at-codes-more:focus-visible{background:var(--at-sel);color:var(--ink);}
.at-codes{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:4px;}
.at-dlg{border:0;border-radius:14px;padding:0;width:min(440px,calc(100vw - 32px));max-height:min(80vh,620px);
  box-shadow:var(--at-sh);color:var(--ink);background:var(--surface);}
.at-dlg::backdrop{background:rgba(22,46,81,.45);}
.at-dlg-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 16px 10px 18px;
  border-bottom:1px solid var(--at-line);position:sticky;top:0;background:var(--surface);}
.at-dlg-head h2{margin:0;font-family:var(--font-display);font-size:17px;line-height:1.3;}
.at-dlg-x{border:0;background:none;font-size:24px;line-height:1;padding:2px 8px;cursor:pointer;color:var(--ink-600);
  border-radius:8px;}
.at-dlg-x:hover,.at-dlg-x:focus-visible{background:var(--primary-tint);color:var(--ink);}
.at-dlg-list{list-style:none;margin:0;padding:8px;display:flex;flex-direction:column;gap:2px;}
.at-codel{display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:8px;text-decoration:none;
  color:var(--ink);font-size:14px;font-weight:600;}
.at-codel span{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;}
.at-codel .at-i{color:var(--primary);}
.at-codel:hover,.at-codel:focus-visible{background:var(--at-sel);}
.at-links a{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;padding:6px 10px;
  border-radius:999px;border:1px solid var(--at-line2);text-decoration:none;color:var(--ink);word-break:break-all;}
.at-links a .at-i{color:var(--primary);}
.at-links a:hover{border-color:var(--at-hover);color:var(--ink);}
.at-links a.at-web{border-color:var(--ink);background:var(--ink);color:var(--white);}
.at-links a.at-web .at-i{color:var(--white);}
.at-links a.at-web:hover{border-color:var(--primary-deep);background:var(--primary-deep);color:var(--white);}
.at-empty{padding:60px 20px;text-align:center;color:var(--ink-faint);}
/* map */
.at-map{position:relative;min-width:0;min-height:0;background:var(--at-water);overflow:hidden;}
.at-svg{position:absolute;inset:0;width:100%;height:100%;display:block;cursor:grab;touch-action:none;}
.at-svg:active{cursor:grabbing;}
.at-svg path{fill:var(--at-land);stroke:var(--at-water);stroke-width:.5;vector-effect:non-scaling-stroke;}
.at-pins{position:absolute;inset:0;pointer-events:none;}
.at-pin{position:absolute;transform:translate(-50%,-50%);border-radius:50%;border:0;padding:0;cursor:pointer;
  pointer-events:auto;display:flex;align-items:center;justify-content:center;background:var(--at-gov);
  box-shadow:0 0 0 2px var(--white),0 1px 3px rgba(22,46,81,.3);opacity:.35;
  transition:opacity .25s,width .15s,height .15s;}
.at-pin.academic{background:var(--at-aca);} .at-pin.corporate{background:var(--at-cor);}
.at-pin.in{opacity:1;}
.at-pin.hot{opacity:1;box-shadow:0 0 0 3px var(--white),0 0 0 5px var(--ink);}
.at-pin span{width:calc(100% - 7px);height:calc(100% - 7px);border-radius:50%;background:var(--white);display:flex;
  align-items:center;justify-content:center;font-family:var(--font-ui);font-weight:700;font-size:11px;color:var(--ink);}
.at-pin:focus-visible{outline:2px solid var(--ink);outline-offset:3px;}
.at-pop{position:absolute;z-index:7;display:flex;flex-direction:column;gap:2px;width:240px;max-height:60%;
  overflow-y:auto;padding:6px;background:var(--surface);border-radius:12px;box-shadow:var(--at-sh);}
.at-popi{display:block;text-align:left;font-size:13px;font-weight:600;padding:6px 8px 6px 10px;border:0;
  border-left:3px solid var(--at-gov);border-radius:6px;background:none;cursor:pointer;}
.at-popi.academic{border-left-color:var(--at-aca);} .at-popi.corporate{border-left-color:var(--at-cor);}
.at-popi:hover,.at-popi:focus-visible{background:var(--at-sel);}
.at-zoom{position:absolute;right:16px;top:16px;display:flex;flex-direction:column;background:var(--surface);
  border-radius:10px;box-shadow:var(--at-sh);overflow:hidden;z-index:6;}
.at-zoom button{width:34px;height:34px;border:0;background:none;cursor:pointer;display:flex;align-items:center;
  justify-content:center;}
.at-zoom button + button{border-top:1px solid var(--at-line);}
.at-zoom button:hover{background:var(--primary-tint);}
.at-grip{position:absolute;left:0;top:0;bottom:0;width:12px;z-index:8;cursor:col-resize;display:flex;
  align-items:center;touch-action:none;}
.at-grip:hover,.at-grip:focus-visible{background:rgba(46,110,174,.08);outline:none;}
.at-grip i{width:4px;height:44px;margin-left:3px;border-radius:2px;background:var(--at-hover);}
.at-grip.drag i,.at-grip:focus-visible i{background:var(--primary);}
.ocred{margin:18px 0 0;font-size:12px;color:var(--ink-faint);line-height:1.6;}
/* narrow: one column - the map pinned on top, then the list in the page's own
   scroll; the sidebar folds behind the Filters button */
@media (max-width:900px){
  .atlas{display:flex;flex-direction:column;height:auto;min-height:0;overflow:visible;}
  .at-map{order:-1;position:sticky;top:0;z-index:20;height:38vh;min-height:220px;flex:none;}
  .at-side{display:none;border-right:0;border-bottom:1px solid var(--at-line);}
  .atlas.fopen .at-side{display:flex;}
  .at-sbody{overflow:visible;}
  .at-list{border-right:0;}
  .at-ftog{display:inline-flex;}
  .at-scroll{overflow:visible;padding:0 16px 32px;}
  .at-gh{top:38vh;}
  .at-grip{display:none;}
  .at-zoom{right:10px;top:10px;}
  .at-more{padding-left:14px;}
}
@media (max-width:900px) and (max-height:520px){.at-map{height:52vh;}.at-gh{top:52vh;}}
"""

BODY = theme.page_header(
    '⟪OSPOs⟫',
    '⟪Open source program offices in government, universities and research institutes.⟫',
    [theme.data_links('/ospos.json')]) + """
__SPRITE__
<main id="main">
<div class="wrap at-wrap">
<div class="atlas" id="atlas">
  <aside class="at-side" id="at-side" aria-label="⟪Search and filters⟫">
    <div class="at-shead"><div class="at-q">__SEARCHI__<input type="search" id="at-q" autocomplete="off"
      placeholder="⟪Search⟫" aria-label="⟪Search offices⟫"></div></div>
    <div class="at-sbody">
      <div class="at-blk" role="group" aria-labelledby="at-l-type"><h2 class="at-lbl" id="at-l-type">⟪Type⟫</h2>__TYPES__</div>
      <div class="at-blk" role="group" aria-labelledby="at-l-fn"><h2 class="at-lbl" id="at-l-fn">⟪Product category⟫</h2>__FNS__</div>
      <div class="at-blk" role="group" aria-labelledby="at-l-fo"><h2 class="at-lbl" id="at-l-fo">⟪Focus⟫</h2>__FOCUS__</div>
      <label class="at-chk"><input type="checkbox" id="at-code">⟪Publishes code⟫</label>
    </div>
  </aside>
  <section class="at-list" aria-label="⟪Offices⟫">
    <div class="at-tool">
      <span class="at-count" id="at-count" aria-live="polite">__COUNT__</span>
      <button type="button" class="at-clear" id="at-clear" hidden>⟪Clear filters⟫</button>
      <span class="at-sp"></span>
      <button type="button" class="at-ftog" id="at-ftog" aria-expanded="false" aria-controls="at-side" hidden>__IFILT__⟪Filters⟫</button>
      <div class="at-ctl">
      <div class="at-seg" role="group" aria-label="⟪Sort⟫" id="at-sort" hidden>
        <button type="button" data-sort="software" aria-pressed="true">⟪Most software⟫</button>
        <button type="button" data-sort="name" aria-pressed="false">⟪A&ndash;Z⟫</button></div>
      <button type="button" class="at-gtog" id="at-group" aria-pressed="false" hidden>__IGROUP__⟪Group by country⟫</button>
      </div>
    </div>
    <div class="at-scroll" id="at-scroll">__GROUPS__
      <div class="at-flat" id="at-flat" hidden></div>
      <p class="at-empty" id="at-empty" hidden>⟪No offices match these filters.⟫</p></div>
  </section>
  <div class="at-map" id="at-map" hidden>
    <svg class="at-svg" id="at-svg" viewBox="__VB__" role="img" aria-label="⟪Map of open source program offices⟫"><path d="__LAND__"/></svg>
    <div class="at-pins" id="at-pins"></div>
    <div class="at-pop" id="at-pop" role="group" aria-label="⟪Offices at this place⟫" hidden></div>
    <div class="at-grip" id="at-grip" role="separator" aria-orientation="vertical" tabindex="0"
      aria-label="⟪Resize the list and the map⟫" title="⟪Drag to resize, double-click to reset⟫"><i></i></div>
    <div class="at-zoom" role="group" aria-label="⟪Zoom⟫">
      <button type="button" data-zoom="in" aria-label="⟪Zoom in⟫" title="⟪Zoom in⟫">__IPLUS__</button>
      <button type="button" data-zoom="out" aria-label="⟪Zoom out⟫" title="⟪Zoom out⟫">__IMINUS__</button>
      <button type="button" data-zoom="reset" aria-label="⟪Show the whole world⟫" title="⟪Show the whole world⟫">__IRESET__</button></div>
  </div>
</div>
<dialog class="at-dlg" id="at-dlg" aria-labelledby="at-dlg-h">
  <div class="at-dlg-head"><h2 id="at-dlg-h"></h2>
    <button type="button" class="at-dlg-x" id="at-dlg-x" aria-label="⟪Close⟫">&times;</button></div>
  <ul class="at-dlg-list" id="at-dlg-list"></ul>
</dialog>
<noscript><style>.at-card .at-more[hidden]{display:flex!important;}.at-card .at-codes[hidden]{display:flex!important;}
.at-codes-more{display:none;}</style></noscript>
<p class="ocred">⟪Government offices: the public-sector OSPO list (CC0) of the
  <a href="https://floss-pso.network/public-sector-ospos/">FLOSS-PSO Network</a>, a volunteer
  project under the <a href="https://ospo-alliance.org/">OSPO Alliance</a>&rsquo;s umbrella,
  fetched __FLOSS_AT__. Academic offices: the
  <a href="https://sustainoss.org/academic-map/">SustainOSS academic map</a> (MIT), the
  universities and research institutes it lists under &ldquo;OSPOs&rdquo;, fetched __AMAP_AT__.
  Two FLOSS-PSO offices are universities and are shown as academic.⟫</p>
<p class="ocred">⟪Corporate offices: the &ldquo;OSPO adopters&rdquo; of the
  <a href="https://landscape.todogroup.org/">TODO Group&rsquo;s OSPO landscape</a> (Apache-2.0),
  fetched __TODO_AT__, as the landscape names them; two state bodies it lists are shown as
  government, and offices already listed above are not repeated. Case studies are the TODO
  Group&rsquo;s own.⟫</p>
<p class="ocred">⟪Locations are placed by govoss at each office&rsquo;s city or its
  organisation&rsquo;s headquarters; companies&rsquo; headquarters come from
  <a href="https://www.wikidata.org/">Wikidata</a> where it has them. The same data:
  <a href="/ospos.json">/ospos.json</a>.⟫</p>
<p class="ocred">⟪Product categories come from each office&rsquo;s software in the govoss catalogue
  (entries whose repository sits under one of its code organisations); focus tags are matched on the
  office&rsquo;s own name and description. &ldquo;Most software&rdquo; sorts offices by how many of their
  software entries govoss lists. Icons: <a href="https://lucide.dev/">Lucide</a> (ISC).⟫</p>
<p class="ocred" id="logo-notice">⟪Logos are the trademarks of their owners, shown only to identify each office.
  They are not covered by govoss&rsquo;s licences and no endorsement is implied. To have one removed,
  <a href="https://github.com/sarapis/govoss-catalog/issues">report it</a>. Flags:
  <a href="https://github.com/lipis/flag-icons">flag-icons</a> (MIT).⟫</p>
</div>
</main>
<script type="application/json" id="at-data">__CFG__</script>
"""

# State in the address bar's HASH (the handoff's deep links): o q type fn focus code
# sort, each validated and an unknown value IGNORED; the old ?q=&type=&cc= links and
# a bare #<office id> still land. el.hidden throughout.
SCRIPT = """
<script>
(function () {
  var $ = function (id) { return document.getElementById(id); };
  var A = $('atlas'), CFG = JSON.parse($('at-data').textContent), L = CFG.L;
  var SC = $('at-scroll'), MAPBOX = $('at-map'), SVG = $('at-svg'), PINS = $('at-pins');
  var TYPES = ['government', 'academic', 'corporate'];
  var FILL = {};
  var cards = [].slice.call(SC.querySelectorAll('.at-card'));
  var secs = [].slice.call(SC.querySelectorAll('.at-grp'));
  var O = {}, all = cards.map(function (c) {
    var p = CFG.pts[c.id] || null;
    var o = {id: c.id, el: c, type: c.dataset.type, cc: c.dataset.cc, name: c.dataset.name,
      fns: c.dataset.fns ? c.dataset.fns.split(' ') : [], focus: c.dataset.focus ? c.dataset.focus.split(' ') : [],
      code: c.dataset.code === '1', score: +c.dataset.score, x: p ? p[0] : null, y: p ? p[1] : null,
      text: c.textContent.toLowerCase()};
    O[c.id] = o;
    return o;
  });
  var total = all.length;
  // the page opens on Government (owner, 2026-10-13); "All offices" is type '' and
  // is written to the hash as type=all, so every view has an address
  var TYPE0 = 'government';
  var st = {q: '', type: TYPE0, fn: '', focus: '', code: false, sort: 'software', group: false, sel: null, hover: null};
  var shown = all.slice(), order = [];
  var narrow = function () { return window.matchMedia('(max-width:900px)').matches; };
  var fmt = function (s, kw) { return s.replace(/\\{(\\w+)\\}/g, function (m, k) { return k in kw ? kw[k] : m; }); };
  var num = function (n) { return String(n).replace(/\\B(?=(\\d{3})+(?!\\d))/g, L.thou); };
  TYPES.forEach(function (t) { FILL[t] = getComputedStyle(A).getPropertyValue(t === 'government' ? '--primary' : t === 'academic' ? '--green' : '--corp').trim(); });

  // ---- hash state
  function readHash() {
    var h = location.hash.slice(1), P;
    try {
      if (h && h.indexOf('=') < 0) { h = decodeURIComponent(h); if (O[h]) st.sel = h; return; }
      P = new URLSearchParams(h);
    } catch (e) { return; }
    if (P.get('q')) st.q = P.get('q');
    if (TYPES.indexOf(P.get('type')) >= 0) st.type = P.get('type');
    else if (P.get('type') === 'all') st.type = '';
    if (CFG.fns.indexOf(P.get('fn')) >= 0) st.fn = P.get('fn');
    if (CFG.focus.indexOf(P.get('focus')) >= 0) st.focus = P.get('focus');
    if (P.get('code') === '1') st.code = true;
    if (P.get('sort') === 'name') st.sort = 'name';
    if (P.get('group') === 'country') st.group = true;
    if (O[P.get('o')]) st.sel = P.get('o');
  }
  function writeHash() {
    var P = new URLSearchParams();
    if (st.sel) P.set('o', st.sel);
    if (st.q.trim()) P.set('q', st.q.trim());
    if (st.type !== TYPE0) P.set('type', st.type || 'all');
    ['fn', 'focus'].forEach(function (k) { if (st[k]) P.set(k, st[k]); });
    if (st.code) P.set('code', '1');
    if (st.sort === 'name') P.set('sort', 'name');
    if (st.group) P.set('group', 'country');
    var s = P.toString();
    try { history.replaceState(null, '', location.pathname + (s ? '#' + s : '')); } catch (e) {}
  }

  // ---- filter, group, sort (Most software, or A-Z)
  // skip: one facet ('type', 'fn', 'focus') left out - how a facet's own counts are taken
  function pass(o, skip) {
    if (skip !== 'type' && st.type && o.type !== st.type) return false;
    if (skip !== 'fn' && st.fn && o.fns.indexOf(st.fn) < 0) return false;
    if (skip !== 'focus' && st.focus && o.focus.indexOf(st.focus) < 0) return false;
    if (st.code && !o.code) return false;
    var q = st.q.trim().toLowerCase();
    return !q || o.text.indexOf(q) >= 0;
  }
  var cmp = function (a, b) {
    return st.sort === 'name' ? a.name.localeCompare(b.name) : b.score - a.score || a.name.localeCompare(b.name);
  };
  function apply() {
    shown = all.filter(function (o) { return pass(o); });
    var on = {}, gm = {};
    shown.forEach(function (o) { on[o.id] = 1; (gm[o.cc] = gm[o.cc] || []).push(o); });
    all.forEach(function (o) { o.el.hidden = !on[o.id]; });
    order = Object.keys(gm).sort(function (a, b) {
      return (a === 'ZZ') - (b === 'ZZ') || gm[b].length - gm[a].length ||
        secById(a).dataset.name.localeCompare(secById(b).dataset.name);
    });
    var empty = $('at-empty'), flat = $('at-flat');
    // one list (the default) or, grouped, a section per country - same sort either way
    flat.hidden = st.group || !shown.length;
    if (!st.group) shown.slice().sort(cmp).forEach(function (o) { flat.appendChild(o.el); });
    secs.forEach(function (s) { s.hidden = !st.group || !gm[s.dataset.cc]; });
    if (st.group) order.forEach(function (cc) {
      var s = secById(cc), items = gm[cc].slice().sort(cmp), tc = {};
      items.forEach(function (o) { s.appendChild(o.el); tc[o.type] = (tc[o.type] || 0) + 1; });
      s.querySelector('.at-gn').textContent = items.length > 1 ? fmt(L.offices, {n: num(items.length)}) : L.office;
      var bar = s.querySelector('.at-gbar');
      [].forEach.call(bar.children, function (i) { i.style.width = (tc[i.className] || 0) / items.length * 100 + '%'; });
      SC.insertBefore(s, empty);
    });
    empty.hidden = shown.length > 0;
    var nc = order.filter(function (c) { return c !== 'ZZ' && c !== 'INT'; }).length;
    $('at-count').textContent = shown.length === total ? fmt(nc === 1 ? L.all1 : L.all, {n: num(total), c: num(nc)})
      : fmt(nc === 1 ? L.some1 : L.some, {n: num(shown.length), t: num(total), c: num(nc)});
    var any = !!(st.q.trim() || st.type !== TYPE0 || st.fn || st.focus || st.code);
    $('at-clear').hidden = !any;
    // each facet counts the offices every OTHER active filter leaves, so a number is
    // what that choice would show (Corporate picked: every category reads 0)
    var base = {type: [], fn: [], focus: []};
    all.forEach(function (o) { for (var f in base) if (pass(o, f)) base[f].push(o); });
    var has = {
      type: function (o, v) { return !v || o.type === v; },
      fn: function (o, v) { return o.fns.indexOf(v) >= 0; },
      focus: function (o, v) { return o.focus.indexOf(v) >= 0; }
    };
    [].forEach.call(A.querySelectorAll('.at-fb'), function (b) {
      var f = b.dataset.f, v = b.dataset.v, on = st[f] === v;
      var n = base[f].filter(function (o) { return has[f](o, v); }).length;
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      b.querySelector('[data-n]').textContent = num(n);
      b.classList.toggle('at-none', !n && !on);
    });
    [].forEach.call($('at-sort').children, function (b) { b.setAttribute('aria-pressed', b.dataset.sort === st.sort ? 'true' : 'false'); });
    $('at-group').setAttribute('aria-pressed', st.group ? 'true' : 'false');
    $('at-code').checked = st.code;
    if ($('at-q').value !== st.q) $('at-q').value = st.q;
    if (st.sel && !on[st.sel]) setSel(null);
    clampAll();
    pins();
  }
  function secById(cc) { return SC.querySelector('.at-grp[data-cc="' + cc + '"]'); }
  function set(p) { for (var k in p) st[k] = p[k]; apply(); writeHash(); }

  // ---- select / expand: one card open at a time
  function setSel(id) {
    if (st.sel && O[st.sel]) {
      var c = O[st.sel].el; c.classList.remove('at-open'); clampTags(c);
      c.querySelector('.at-more').hidden = true;
      c.querySelector('.at-tgl').setAttribute('aria-expanded', 'false');
    }
    st.sel = id;
    if (id) {
      var d = O[id].el; d.classList.add('at-open'); clampTags(d);
      d.querySelector('.at-more').hidden = false;
      d.querySelector('.at-tgl').setAttribute('aria-expanded', 'true');
    }
  }
  // a CLOSED card shows at most TAGROWS rows of tags, the last ending in "+N"; an
  // open one shows them all (owner, 2026-10-13). Measured: a tag's width is its words.
  var TAGROWS = 2;
  function clampTags(c) {
    var box = c.querySelector('.at-tags');
    if (!box) return;
    var more = box.querySelector('.at-tmore');
    if (more) box.removeChild(more);
    var tags = [].slice.call(box.querySelectorAll('.at-tag'));
    tags.forEach(function (t) { t.hidden = false; });
    if (c.hidden || c.classList.contains('at-open')) return;
    var tops = [];
    tags.forEach(function (t) { if (tops.indexOf(t.offsetTop) < 0) tops.push(t.offsetTop); });
    if (tops.length <= TAGROWS) return;
    var lim = tops[TAGROWS], keep = tags.filter(function (t) { return t.offsetTop < lim; }).length;
    tags.forEach(function (t, i) { t.hidden = i >= keep; });
    more = document.createElement('span');
    more.className = 'at-tag at-tmore';
    box.appendChild(more);
    // the chip itself must fit on the last row: give up one more tag until it does
    do {
      more.textContent = '+' + (tags.length - keep);
      more.title = fmt(L.moretags, {n: tags.length - keep});
      if (more.offsetTop < lim) break;
      tags[--keep].hidden = true;
    } while (keep > 0);
  }
  // debounced on a timer, not a frame: a frame never comes in a background tab, and
  // a card clamped at one width would keep its "+N" at another
  var clampT = 0;
  function clampAll() {
    clearTimeout(clampT);
    clampT = setTimeout(function () { cards.forEach(function (c) { if (!c.hidden) clampTags(c); }); }, 40);
  }
  // the open office, picked again (its pin, its name in a pin's list), closes
  function deselect() { setSel(null); writeHash(); pins(); }
  function select(id, scroll) {
    setSel(st.sel === id ? null : id);
    writeHash(); pins();
    if (scroll && st.sel) setTimeout(function () { scrollToEl(O[id].el, 64); }, 50);
  }
  // pin: hovering FROM a pin restyles that pin in place - redrawing the pins would
  // swap the button under the pointer between press and release, and the click never lands
  function hover(id, pin) {
    st.hover = id;
    all.forEach(function (o) { o.el.classList.toggle('hov', o.id === id); });
    if (!pin) return pins();
    var hot = !!id || (pin.dataset.id === st.sel);
    pin.classList.toggle('hot', hot);
    pin.style.width = pin.style.height = (hot ? 22 : pin.classList.contains('in') ? 14 : 9) + 'px';
    pin.style.zIndex = hot ? 5 : pin.classList.contains('in') ? 3 : 1;
  }

  // ---- the list's scroll: the list column, or the page on a narrow screen
  function topLine() { return narrow() ? MAPBOX.getBoundingClientRect().bottom : SC.getBoundingClientRect().top; }
  function scrollToEl(el, off) {
    var dy = el.getBoundingClientRect().top - topLine() - (off || 0);
    if (narrow()) window.scrollTo({top: window.pageYOffset + dy, behavior: 'smooth'});
    else SC.scrollTo({top: SC.scrollTop + dy, behavior: 'smooth'});
  }
  // ---- the map: viewBox pan/zoom; the vertical extent follows the pane's shape
  var VB0 = CFG.vb.slice(), vb = VB0.slice(), ZMIN = 0.9, ZMAX = 20, anim = 0, raf = 0;
  function asp() { var r = SVG.getBoundingClientRect(); return r.width ? r.height / r.width : VB0[3] / VB0[2]; }
  function zoom() { return VB0[2] / vb[2]; }
  function setVB(x, y, w) {
    var z = Math.min(ZMAX, Math.max(ZMIN, VB0[2] / w)); w = VB0[2] / z;
    var h = w * asp();
    x = Math.min(Math.max(x, VB0[0] - w * 0.3), VB0[0] + VB0[2] - w * 0.7);
    if (h >= VB0[3]) y = VB0[1] + (VB0[3] - h) / 2;
    else y = Math.min(Math.max(y, VB0[1] - h * 0.2), VB0[1] + VB0[3] - h * 0.8);
    vb = [x, y, w, h];
    if (POP && !POP.hidden) closePop();
    SVG.setAttribute('viewBox', vb.map(function (v) { return Math.round(v * 100) / 100; }).join(' '));
    if (!raf) raf = requestAnimationFrame(function () { raf = 0; pins(); });
  }
  function toMap(cx, cy) { var r = SVG.getBoundingClientRect(); return [vb[0] + (cx - r.left) / r.width * vb[2], vb[1] + (cy - r.top) / r.height * vb[3]]; }
  function zoomAt(f, px, py) {
    var z = Math.min(ZMAX, Math.max(ZMIN, zoom() * f)); f = z / zoom();
    setVB(px - (px - vb[0]) / f, py - (py - vb[1]) / f, vb[2] / f);
  }
  function flyTo(x, y, z) {
    cancelAnimationFrame(anim);
    var from = vb.slice(), w1 = VB0[2] / Math.min(ZMAX, Math.max(ZMIN, z)), h1 = w1 * asp();
    var to = [x - w1 / 2, y - h1 / 2, w1], t0 = performance.now();
    if (window.matchMedia('(prefers-reduced-motion:reduce)').matches) return setVB(to[0], to[1], to[2]);
    (function step(now) {
      var t = Math.min(1, (now - t0) / 650), e = 1 - Math.pow(1 - t, 3);
      setVB(from[0] + (to[0] - from[0]) * e, from[1] + (to[1] - from[1]) * e, from[2] + (to[2] - from[2]) * e);
      if (t < 1) anim = requestAnimationFrame(step);
    })(t0);
  }
  function reset() { flyTo(VB0[0] + VB0[2] / 2, VB0[1] + VB0[3] / 2, 1); }
  var drag = null, moved = false;
  SVG.addEventListener('wheel', function (e) {
    e.preventDefault(); var p = toMap(e.clientX, e.clientY);
    zoomAt(Math.exp(-Math.max(-60, Math.min(60, e.deltaY)) * 0.006), p[0], p[1]);
  }, {passive: false});
  SVG.addEventListener('dblclick', function (e) { e.preventDefault(); var p = toMap(e.clientX, e.clientY); zoomAt(e.shiftKey ? 0.5 : 2, p[0], p[1]); });
  // a click on the open map (not a drag, not a pin) closes the open office
  SVG.addEventListener('click', function () { if (!moved && st.sel) deselect(); });
  SVG.addEventListener('pointerdown', function (e) {
    if (e.button !== 0) return; cancelAnimationFrame(anim);
    drag = {x: e.clientX, y: e.clientY, vb: vb.slice(), r: SVG.getBoundingClientRect()}; moved = false;
  });
  window.addEventListener('pointermove', function (e) {
    if (!drag) return; var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    if (!moved && Math.hypot(dx, dy) < 4) return; moved = true;
    var u = drag.vb[2] / drag.r.width; setVB(drag.vb[0] - dx * u, drag.vb[1] - dy * u, drag.vb[2]);
  });
  window.addEventListener('pointerup', function () { drag = null; setTimeout(function () { moved = false; }, 0); });
  [].forEach.call(A.querySelectorAll('.at-zoom button'), function (b) {
    b.onclick = function () {
      if (b.dataset.zoom === 'reset') return reset();
      zoomAt(b.dataset.zoom === 'in' ? 2 : 0.5, vb[0] + vb[2] / 2, vb[1] + vb[3] / 2);
    };
  });
  if (window.ResizeObserver) new ResizeObserver(function () {
    var cx = vb[0] + vb[2] / 2, cy = vb[1] + vb[3] / 2, w = vb[2];
    setVB(cx - w / 2, cy - w * asp() / 2, w);
  }).observe(SVG);

  // pins: greedy screen-space clusters within 18px of the offices shown
  function conic(tc, n) {
    var acc = 0, parts = [];
    TYPES.forEach(function (t) { if (!tc[t]) return; var a = acc + tc[t] / n * 100; parts.push(FILL[t] + ' ' + acc.toFixed(1) + '% ' + a.toFixed(1) + '%'); acc = a; });
    return 'conic-gradient(' + parts.join(',') + ')';
  }
  function pins() {
    var r = SVG.getBoundingClientRect(); if (!r.width) return;
    var k = r.width / vb[2], ky = r.height / vb[3], cl = [];
    shown.forEach(function (o) {
      if (o.x == null) return;
      for (var i = 0; i < cl.length; i++) {
        if (Math.hypot((cl[i].x - o.x) * k, (cl[i].y - o.y) * k) < 18) { cl[i].items.push(o); return; }
      }
      cl.push({x: o.x, y: o.y, items: [o]});
    });
    cl.forEach(function (m) {
      var n = m.items.length; m.n = n;
      if (n > 1) {
        m.x = m.items.reduce(function (a, o) { return a + o.x; }, 0) / n;
        m.y = m.items.reduce(function (a, o) { return a + o.y; }, 0) / n;
      }
    });
    cl.sort(function (a, b) { return a.n - b.n; });
    PINS.textContent = '';
    cl.forEach(function (m) {
      var px = (m.x - vb[0]) * k, py = (m.y - vb[1]) * ky;
      if (px < -40 || py < -40 || px > r.width + 40 || py > r.height + 40) return;
      var one = m.n === 1, o1 = m.items[0];
      var hot = m.items.some(function (o) { return o.id === st.hover || o.id === st.sel; });
      // every pin at full strength: the map shows all offices, not one country's
      var size = one ? (hot ? 22 : 14) : Math.round(Math.min(40, 22 + Math.sqrt(m.n) * 2.2));
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'at-pin in' + (one ? ' ' + o1.type : '') + (hot ? ' hot' : '');
      b.style.left = px + 'px'; b.style.top = py + 'px'; b.style.width = b.style.height = size + 'px';
      b.style.zIndex = hot ? 5 : 3;
      var label = one ? o1.name : fmt(L.cluster, {n: num(m.n)});
      b.title = label; b.setAttribute('aria-label', label);
      if (!one) {
        var tc = {}; m.items.forEach(function (o) { tc[o.type] = (tc[o.type] || 0) + 1; });
        b.style.background = conic(tc, m.n);
        var s = document.createElement('span'); s.textContent = m.n; b.appendChild(s);
      }
      if (one) b.dataset.id = o1.id;
      // a single office opens in the list; a cluster zooms in, unless it cannot split
      // (offices at one address, or already at full zoom) - then its first office opens
      var spread = Math.max.apply(0, m.items.map(function (o) { return Math.hypot(o.x - m.x, o.y - m.y); }));
      var stuck = !one && (spread < 0.05 || zoom() >= ZMAX * 0.99);
      b.onclick = function (e) {
        if (moved) return;
        e.stopPropagation();
        if (one) { closePop(); select(o1.id, true); }
        else if (stuck) openPop(m.items.slice().sort(cmp), b);
        else { closePop(); flyTo(m.x, m.y, Math.min(ZMAX, zoom() * 2.6)); }
      };
      b.onmouseenter = function () { if (one) hover(o1.id, b); };
      b.onmouseleave = function () { if (one) hover(null, b); };
      PINS.appendChild(b);
    });
  }

  // offices at one address never split: their pin lists them to pick from
  var POP = $('at-pop');
  function closePop() { POP.hidden = true; POP.textContent = ''; }
  function openPop(items, pin) {
    POP.textContent = '';
    items.forEach(function (o) {
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'at-popi ' + o.type; b.textContent = o.name;
      b.onclick = function (e) {
        e.stopPropagation(); closePop();
        select(o.id, true);
      };
      POP.appendChild(b);
    });
    POP.hidden = false;
    var mb = MAPBOX.getBoundingClientRect(), pb = pin.getBoundingClientRect();
    var w = POP.offsetWidth, h = POP.offsetHeight, x = pb.right - mb.left + 8;
    if (x + w > mb.width - 8) x = pb.left - mb.left - w - 8;
    POP.style.left = Math.max(8, x) + 'px';
    POP.style.top = Math.max(8, Math.min(pb.top - mb.top - 12, mb.height - h - 8)) + 'px';
    POP.firstChild.focus();
  }
  document.addEventListener('click', function (e) { if (!POP.hidden && !POP.contains(e.target)) closePop(); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closePop(); });

  // ---- the divider between list and map
  var grip = $('at-grip'), listW = null;
  try { listW = +localStorage.getItem(CFG.listw_key) || null; } catch (e) {}
  function cols() {
    A.style.gridTemplateColumns = listW ? '272px ' + listW + 'px minmax(0,1fr)' : '';
  }
  function clampW(w) { var r = A.getBoundingClientRect(); return Math.round(Math.max(320, Math.min(r.width - 272 - 280, w))); }
  function saveW() { try { if (listW) localStorage.setItem(CFG.listw_key, listW); else localStorage.removeItem(CFG.listw_key); } catch (e) {} }
  grip.addEventListener('pointerdown', function (e) {
    e.preventDefault(); grip.classList.add('drag');
    var move = function (ev) { listW = clampW(ev.clientX - A.getBoundingClientRect().left - 272); cols(); };
    var up = function () {
      window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up);
      grip.classList.remove('drag'); saveW();
    };
    window.addEventListener('pointermove', move); window.addEventListener('pointerup', up);
  });
  grip.addEventListener('dblclick', function () { listW = null; cols(); saveW(); });
  grip.addEventListener('keydown', function (e) {
    var d = e.key === 'ArrowLeft' ? -24 : e.key === 'ArrowRight' ? 24 : 0;
    if (!d) return; e.preventDefault();
    listW = clampW((listW || $('at-scroll').getBoundingClientRect().width + 0) + d); cols(); saveW();
  });

  // the atlas is one viewport tall (CSS); the credits are a page scroll below it
  var lastW = 0;
  if (window.ResizeObserver) new ResizeObserver(function () {
    var w = SC.getBoundingClientRect().width;
    if (w !== lastW) { lastW = w; clampAll(); }
  }).observe(SC);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(clampAll);

  // ---- wiring
  var qt = 0;
  $('at-q').addEventListener('input', function () { var v = this.value; clearTimeout(qt); qt = setTimeout(function () { set({q: v}); }, 120); });
  [].forEach.call(A.querySelectorAll('.at-fb'), function (b) {
    b.onclick = function () {
      // Type is one choice of four (All is one of them); the other facets toggle off
      var p = {}; p[b.dataset.f] = b.dataset.f === 'type' || st[b.dataset.f] !== b.dataset.v ? b.dataset.v : ''; set(p);
      if (narrow()) scrollToEl(SC, 0);
    };
  });
  $('at-code').onchange = function () { set({code: this.checked}); };
  $('at-clear').onclick = function () { set({q: '', type: TYPE0, fn: '', focus: '', code: false}); };
  [].forEach.call($('at-sort').children, function (b) { b.onclick = function () { set({sort: b.dataset.sort}); }; });
  $('at-group').onclick = function () { set({group: !st.group}); };
  cards.forEach(function (c) {
    c.querySelector('.at-ch').onclick = function () { select(c.id, false); };
    c.onmouseenter = function () { hover(c.id); };
    c.onmouseleave = function () { hover(null); };
  });
  // the button inside the h3 is the keyboard's way in; its click bubbles to .at-ch
  var ftog = $('at-ftog');
  ftog.onclick = function () {
    var o = !A.classList.contains('fopen'); A.classList.toggle('fopen', o); ftog.setAttribute('aria-expanded', o ? 'true' : 'false');
  };

  // ---- an office's code profiles: one on the card, all of them in a dialog. The
  // dialog holds COPIES of the card's own (hidden) list, so the links are the card's.
  var DLG = $('at-dlg');
  function openCodes(c, btn) {
    var list = $('at-dlg-list'); list.textContent = '';
    [].forEach.call(c.querySelectorAll('.at-codes li'), function (li) { list.appendChild(li.cloneNode(true)); });
    $('at-dlg-h').textContent = fmt(L.codes, {name: c.dataset.name});
    DLG._from = btn;
    if (DLG.showModal) DLG.showModal(); else DLG.setAttribute('open', '');
  }
  function closeCodes() {
    if (DLG.close) DLG.close(); else DLG.removeAttribute('open');
  }
  $('at-dlg-x').onclick = closeCodes;
  // a click on the backdrop lands on the dialog itself, outside its box
  DLG.addEventListener('click', function (e) {
    if (e.target !== DLG) return;
    var r = DLG.getBoundingClientRect();
    if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) closeCodes();
  });
  DLG.addEventListener('close', function () { if (DLG._from) DLG._from.focus(); DLG._from = null; });
  cards.forEach(function (c) {
    var b = c.querySelector('.at-codes-more');
    if (b) b.onclick = function (e) { e.stopPropagation(); openCodes(c, b); };
  });

  // ---- boot: the old ?q= / ?type= / ?cc= links still land
  try {
    var Q = new URLSearchParams(location.search), legacyCc = Q.get('cc');
    if (Q.get('q')) st.q = Q.get('q');
    // an old link was made when the page showed every type: it lands on All
    if (legacyCc) st.group = true;     // an old ?cc= link meant "that country's section"
    if (Q.get('q') || legacyCc || Q.get('type')) st.type = TYPES.indexOf(Q.get('type')) >= 0 ? Q.get('type') : '';
  } catch (e) {}
  readHash();
  MAPBOX.hidden = false; $('at-sort').hidden = false; $('at-group').hidden = false; ftog.hidden = false;
  cols();
  setVB(VB0[0], VB0[1], VB0[2]);
  var sel0 = st.sel; st.sel = null;
  apply();
  // the first clamp now, not on clampAll's timer: no flash of every tag on load
  clearTimeout(clampT); cards.forEach(function (c) { if (!c.hidden) clampTags(c); });
  if (sel0) { setSel(sel0); pins(); setTimeout(function () { scrollToEl(O[sel0].el, 64); }, 300); }
  else if (legacyCc && secById(legacyCc) && !secById(legacyCc).hidden) setTimeout(function () { scrollToEl(secById(legacyCc), 0); }, 300);
  writeHash();
})();
</script>
"""


if __name__ == "__main__":
    data, locs, geo, res, catalog = load()
    rows = derive(data, locs, geo, res, catalog)
    copy_images()
    for _lang in i18n.LANGS:
        build(_lang, data, rows, geo)
    rows = sorted(rows, key=lambda r: (TYPE_ORDER.index(r["type"]), r["name"].lower()))
    doc = {
        "generated_at": NOW, "human_page": i18n.BASE + "/ospos",
        "about": "Open source program offices. Government: the FLOSS-PSO Network's "
                 "public-sector OSPO list (CC0). Academic: the SustainOSS academic map's "
                 "'OSPOs' lists (MIT). Corporate: the TODO Group OSPO landscape's 'OSPO "
                 "Adopter' rows (Apache-2.0), two state bodies among them typed government and "
                 "offices already listed from the other two not repeated. Two FLOSS-PSO offices "
                 "are universities and are typed academic. "
                 "SOURCES: sources[key].ok false means that list's fetch failed and the rows "
                 "shown are the last good copy, fetched at fetched_at (which is never moved "
                 "by a failed attempt; failed_at and error say when and why it failed); "
                 "count is the number of rows from that list. "
                 "IDS are derived from each office's URL in its list (FLOSS-PSO), its page "
                 "path (academic map) or its name (TODO landscape), and stay the same while "
                 "that does. "
                 "LOCATIONS are govoss's placement, by hand or (companies) from Wikidata's "
                 "headquarters, named in location.via: location.basis 'seat' is the office's "
                 "own city; 'hq' is its parent organisation's headquarters, so the point is "
                 "approximate. lat/lon are WGS84 degrees. "
                 "PLACEMENT differs by source: every FLOSS-PSO row (source 'floss-pso') has a "
                 "location object and a country that is a key of country_codes. Rows from "
                 "'academic-map' and 'todo-landscape' MAY have country null and location null "
                 "together - an office not yet placed; when present, both follow the same "
                 "rules. "
                 "COUNTRY codes are listed in country_codes: ISO 3166-1 alpha-2 except EL "
                 "(Greece, the EU's code) and INT (an international body); country_names "
                 "gives a short display name for each. "
                 "An EXAMPLE of a failed FLOSS-PSO fetch, as this file would then read, is "
                 "published at /ospos.example-failed.json. "
                 "LICENCES: each list's rows are under that list's licence (sources[key].licence); "
                 "govoss's own fields - id, type, location, resources_case, and country where "
                 "the list gives none - are under licence.govoss_fields.",
        "licence": C.LICENCE,
        "country_codes": C.COUNTRIES,
        "country_names": C.COUNTRY_NAMES,
        "sources": data.get("sources"),
        "ospos": [dict({k: v for k, v in r.items() if not k.startswith("_")},
                       country=r["_cc"], location=r["_loc"] or None,
                       resources_case=r["_case"]) for r in rows],
    }
    # un.opensource.nyc reads this file and throws on anything unexpected: a file
    # that breaks the contract (ospo_contract.py) is never written, and the failed
    # step stops the publish. Upstream changes are refused earlier, in fetch_ospos.py.
    probs = C.doc_problems(doc)
    if probs:
        raise SystemExit("build_ospos: /ospos.json would break its consumer contract:\n  "
                         + "\n  ".join(probs))
    with open(f"{SITE}/ospos.json", "w") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    # the same document after a failed FLOSS-PSO fetch, written by the fetcher's own
    # failed_state(), so a reader can test ok:false handling without a real outage
    ex = json.loads(json.dumps(doc))
    ex["example"] = ("NOT LIVE DATA: /ospos.json as it reads after a failed FLOSS-PSO fetch. "
                     "The rows are the last good copy; fetched_at and count are that copy's; "
                     "failed_at and error describe the failed attempt.")
    ex["sources"]["floss-pso"] = fetch_ospos.failed_state(
        doc["sources"]["floss-pso"], "floss-pso",
        "URLError: <urlopen error [Errno 8] nodename nor servname provided, or not known>",
        doc["sources"]["floss-pso"]["count"], NOW)
    probs = C.doc_problems(ex)
    if probs:
        raise SystemExit("build_ospos: the failed-fetch example breaks the contract:\n  "
                         + "\n  ".join(probs))
    with open(f"{SITE}/ospos.example-failed.json", "w") as fh:
        json.dump(ex, fh, ensure_ascii=False, indent=1)
    i18n.report("build_ospos")
