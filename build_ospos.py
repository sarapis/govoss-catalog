"""Build site/ospos.html (served at /ospos) + site/ospos.json.

Open source program offices - government, academic and corporate - from three
published lists that fetch_ospos.py reads into cache/ospos.json: the FLOSS-PSO
Network's public-sector OSPO list (CC0), the SustainOSS academic map (MIT) and
the TODO Group's OSPO landscape (Apache-2.0; corporate since 2026-10-09). Records
stay English on every language copy; only the chrome is translated.

Two views of one list, like /catalogs: cards (the default, and all a reader
without JavaScript gets) and a map. The map is inline SVG from the committed
geo/ospo_frames.json (one world map, Equal Earth; written by geo/build_geo.py);
each office is placed from ospos/locations.json - hand-placed, or for TODO's
companies their Wikidata headquarters (ospos/place_from_wikidata.py, `via`). Offices sharing a
spot (three in Paris, two in The Hague) share one dot that names them all.

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
import time

import fetch_ospos
import i18n
import ospo_contract as C
import sources as S

OUT = os.path.dirname(os.path.abspath(__file__))
SITE = f"{OUT}/site"
NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

_th = importlib.util.spec_from_file_location("theme", f"{OUT}/theme.py")
theme = importlib.util.module_from_spec(_th); _th.loader.exec_module(theme)
_tp = importlib.util.spec_from_file_location("_ui_template", f"{OUT}/_ui_template.py")
T = importlib.util.module_from_spec(_tp); _tp.loader.exec_module(T)

# A map pin, tip at (0,0) on the office's place, head a circle of radius 6 at (0,-10).
PIN = "M0,0C-1.6,-3.4 -6,-6.2 -6,-10A6,6 0 1 1 6,-10C6,-6.2 1.6,-3.4 0,0Z"

# Pins nearer than this (map units, before scaling) merge into one numbered pin.
MERGE_WITHIN = 9

# Card and filter order: government first, as the site is about government.
TYPE_ORDER = ("government", "academic", "corporate")

# Code links shown on a card before the rest fold behind "+N more code links".
CODE_SHOWN = 3

# An office's URL (its key in FLOSS-PSO) -> its case in resources/ospo-resources.json.
# Named, never guessed: UNDP is NOT the "un" case (that is the UN's OICT and the
# Open Source United community, a different office).
RESOURCE_CASE = {
    "https://opensource.muenchen.de/ospo.html": "munich",
    "https://opensource.paris.fr": "paris",
    "https://cms.gov/digital-service/open-source-program-office": "cms",
}


def esc(s):
    return ("" if s is None else str(s)).replace("&", "&amp;").replace(
        "<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def flag(cc):
    """Flag emoji for a country code, as /software shows them. Built from the
    code (regional-indicator letters), not sources.py's per-catalogue flags:
    most OSPO countries have no catalogue. EL is the EU's code for Greece (its
    flag is GR); INT, an intergovernmental office, gets /software's Global sign."""
    cc = {"EL": "GR"}.get(cc or "", cc or "")
    if cc == "INT":
        return "\U0001F310"
    if len(cc) == 2 and cc.isalpha():
        return "".join(chr(0x1F1E6 + ord(ch) - ord("A")) for ch in cc.upper())
    return ""


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


def load():
    data = json.load(open(f"{OUT}/cache/ospos.json"))
    locs = json.load(open(f"{OUT}/ospos/locations.json"))["locations"]
    geo = json.load(open(f"{OUT}/geo/ospo_frames.json"))
    res = json.load(open(f"{OUT}/resources/ospo-resources.json"))
    if not data.get("ospos"):
        raise SystemExit("build_ospos: cache/ospos.json has no ospos - run fetch_ospos.py")
    return data, locs, geo, res


def build(lang, data, locs, geo, res):
    _ = lambda msg, **kw: i18n.t(lang, msg, **kw)
    N = lambda n: i18n.num(lang, n)
    cname = lambda c: (i18n.country(lang, c, S.COUNTRY_NAME.get(c) or C.COUNTRY_NAMES.get(c, c))
                       if c else "")
    rcount = collections.Counter(r["case"] for r in res["resources"])
    os_ = sorted(data["ospos"], key=lambda r: (TYPE_ORDER.index(r["type"]), r["name"].lower()))
    for r in os_:
        loc = locs.get(r["id"]) or {}
        r["_cc"] = r.get("country") or loc.get("country")
        r["_loc"] = loc
        case = RESOURCE_CASE.get(r["url"])
        r["_case"] = case if case and rcount.get(case) else None
    n_gov = sum(r["type"] == "government" for r in os_)
    n_aca = sum(r["type"] == "academic" for r in os_)
    n_corp = sum(r["type"] == "corporate" for r in os_)
    tlabel = lambda t: {"government": _("Government"), "academic": _("Academic"),
                        "corporate": _("Corporate")}[t]
    by_cc = collections.Counter(r["_cc"] for r in os_ if r["_cc"])

    cards = []
    for r in os_:
        links = ['<a href="%s" target="_blank" rel="noopener">%s</a>'
                 % (esc(r["url"]), esc(_("Website")))]
        # each code link named by its account or group (ANSSI lists 13; "Code" x13 said nothing)
        code = []
        for c in r.get("code") or []:
            seg = [x for x in c.split("://", 1)[-1].split("/")[1:] if x and x != "groups"]
            code.append('<a href="%s" target="_blank" rel="noopener">%s %s</a>'
                        % (esc(c), esc(_("Code:")), esc(seg[-1] if seg else c.split("://", 1)[-1])))
        # past CODE_SHOWN, the rest fold behind a native <details> (OS2 lists 19): policy
        # and email stay in the visible row, after the shown code links
        links += code[:CODE_SHOWN]
        more = ""
        if len(code) > CODE_SHOWN:
            more = ('<details class="omore"><summary>%s</summary><p class="olinks">%s</p></details>'
                    % (esc(_("+{n} more code links", n=N(len(code) - CODE_SHOWN))),
                       " &middot; ".join(code[CODE_SHOWN:])))
        if r.get("case_study"):
            links.append('<a href="%s" target="_blank" rel="noopener">%s</a>'
                         % (esc(r["case_study"]), esc(_("TODO Group case study"))))
        if r.get("policy"):
            links.append('<a href="%s" target="_blank" rel="noopener">%s</a>'
                         % (esc(r["policy"]), esc(_("Open source policy"))))
        if r.get("email"):
            links.append('<a href="mailto:%s">%s</a>' % (esc(r["email"]), esc(r["email"])))
        res_link = ""
        if r["_case"]:
            res_link = ('<a class="ores" href="/resources?case=%s">%s</a>'
                        % (esc(r["_case"]), _("{n} resources on how this office was built &rarr;",
                                              n=N(rcount[r["_case"]]))))   # own chrome: not escaped again
        typ = tlabel(r["type"])
        meta = (['<span class="oflag" aria-hidden="true">%s</span> %s' % (flag(r["_cc"]), esc(cname(r["_cc"])))]
                if r["_cc"] else [])
        if r["_loc"].get("place"):
            meta.append(esc(r["_loc"]["place"]))
        if r.get("created"):
            meta.append(esc(_("since {y}", y=str(r["created"])[:4])))
        cards.append(
            '<li class="ocard" id="%s" data-type="%s" data-cc="%s">'
            '<div class="ohead"><span class="otype %s">%s</span><span class="ometa">%s</span></div>'
            '<h3>%s</h3>%s%s'
            '<p class="olinks">%s</p>%s%s</li>'
            % (esc(r["id"]), esc(r["type"]), esc(r["_cc"] or ""), esc(r["type"]), esc(typ),
               " &middot; ".join(meta), esc(r["name"]),
               ('<p class="odesc">%s</p>' % esc(r["description"])) if r.get("description") else "",
               ('<p class="onote"><b>%s</b> %s</p>' % (esc(_("OSPO:")), esc(r["ospo_note"])))
               if r.get("ospo_note") else "",
               " &middot; ".join(links), more, res_link))

    # ---- the map: one pin per spot; offices sharing a spot share a pin
    spots = collections.OrderedDict()
    unplaced = []
    for r in os_:
        loc = r["_loc"]
        p = place(geo["frames"], loc["lon"], loc["lat"]) if loc.get("lat") is not None else None
        if not p:
            unplaced.append(r)
            continue
        spots.setdefault(p, []).append(r)
    # pins closer than MERGE_WITHIN share one (a teardrop hides its neighbour: Saint-Mande
    # covered Paris's three); greedy, largest spot first, measured from each pin's anchor
    order = sorted(spots.items(), key=lambda kv: -len(kv[1]))
    # the same spots, in the same order, for the page's zoom: ospoCluster() in SCRIPT
    # re-merges them at each zoom by this rule, MERGE_WITHIN measured on SCREEN
    spot_json = json.dumps({"within": MERGE_WITHIN, "pin": PIN, "spots": [
        [k, x, y, [r["id"] for r in rs],
         list(dict.fromkeys(r["_loc"].get("place") for r in rs if r["_loc"].get("place")))]
        for (k, x, y), rs in order]}, sort_keys=True).replace("</", "<\\/")
    merged = []
    for (k, x, y), rs in order:
        for m in merged:
            if m[0] == k and math.hypot(m[1] - x, m[2] - y) < MERGE_WITHIN:
                m[3].extend(rs)
                break
        else:
            merged.append((k, x, y, list(rs)))
    # drawn smallest first, so a numbered pin is never covered by a single one
    pins = collections.defaultdict(list)
    for k, x, y, rs in reversed(merged):
        places = list(dict.fromkeys(r["_loc"].get("place") for r in rs if r["_loc"].get("place")))
        label = "; ".join("%s (%s)" % (r["name"], tlabel(r["type"])) for r in rs)
        types = sorted({r["type"] for r in rs})
        cls = types[0] if len(types) == 1 else "mixed"
        pins[k].append('<a class="odot %s" href="#%s" data-ids="%s" data-place="%s" aria-label="%s" '
                       'aria-haspopup="dialog"><title>%s</title><g transform="translate(%s %s)">'
                       '<g class="opin"%s><path d="%s"/>%s</g></g></a>'
                       % (cls, esc(rs[0]["id"]), esc(" ".join(r["id"] for r in rs)),
                          esc("; ".join(places)), esc(label), esc(label),
                          x, y, ' style="--k:1.3"' if len(rs) > 1 else "", PIN,
                          '<text x="0" y="-7">%d</text>' % len(rs) if len(rs) > 1
                          else '<circle class="ohole" cx="0" cy="-10" r="2.2"/>'))

    def draw(cls, viewbox, shift):
        """One layout of the map: each frame's land and pins, moved by shift[frame]."""
        out = ['<svg class="omap-svg %s" viewBox="%s %s %s %s" role="group" aria-label="%s">'
               % ((cls,) + tuple(viewbox) + (esc(_("Map of open source program offices")),))]
        for k, fr in geo["frames"].items():
            rx, ry, rw, rh = fr["rect"]
            dx, dy = shift[k]
            out.append('<g transform="translate(%s %s)"><g class="oframe">'
                       '<rect x="%s" y="%s" width="%s" height="%s" rx="8"/>'
                       '<path d="%s" aria-hidden="true"/></g><g class="opins" data-frame="%s">%s</g></g>'
                       % (round(dx, 1), round(dy, 1), rx, ry, rw, rh, fr["land"], esc(k), "".join(pins[k])))
        out.append("</svg>")
        return "".join(out)

    # one world map (owner, 2026-10-09; it was three regional frames, and a second,
    # stacked layout for phones)
    svg = [draw("omap-world", geo["viewbox"], {k: (0, 0) for k in geo["frames"]})]
    note = ""
    if unplaced:
        note = ('<p class="onote-map">%s</p>'
                % esc(_("{n} not on the map: {names}",
                        n=len(unplaced), names="; ".join(r["name"] for r in unplaced))))

    copts = "".join('<option value="%s">%s %s (%s)</option>' % (esc(c), flag(c), esc(cname(c)), N(n))
                    for c, n in sorted(by_cc.items(), key=lambda kv: cname(kv[0])))
    src = data.get("sources") or {}
    def fetched(key):
        st = src.get(key) or {}
        when = (st.get("fetched_at") or "")[:10] or _("never")
        return when + ("" if st.get("ok", True) else " &middot; " + esc(_("last fetch failed, showing the previous list")))

    subs = {
        "__N__": N(len(os_)), "__NGOV__": N(n_gov), "__NACA__": N(n_aca), "__NCORP__": N(n_corp),
        "__TODO_AT__": fetched("todo-landscape"),
        "__CARDS__": "".join(cards), "__MAP__": "".join(svg), "__MAPNOTE__": note, "__SPOTS__": spot_json,
        "__COPTS__": copts,
        "__FLOSS_AT__": fetched("floss-pso"), "__AMAP_AT__": fetched("academic-map"),
        "__LANG__": lang,
    }
    page = (theme.head(
        _("OSPOs | govoss"),
        _("{n} open source program offices - {g} in government, {a} in universities and "
          "research institutes - with a map.", n=N(len(os_)), g=N(n_gov), a=N(n_aca)),
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
    open(out, "w").write(page)
    print("ospos page [%s]: %d OSPOs (%d government, %d academic, %d corporate), %d map pins, "
          "%d unplaced (%.0f KB)" % (lang, len(os_), n_gov, n_aca, n_corp, len(merged), len(unplaced),
                                    len(page) / 1024))
    return os_


PAGE_CSS = """
.obar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-top:28px;}
.obar input[type=search]{flex:1 1 240px;min-width:0;font:inherit;font-size:15px;padding:10px 14px;
  border:1px solid var(--border);border-radius:var(--r-chip);background:var(--surface);color:var(--ink);}
.obar select{font:inherit;font-size:13px;padding:9px 10px;border:1px solid var(--border);
  border-radius:var(--r-chip);background:var(--surface);color:var(--ink);max-width:100%;}
.oseg{display:inline-flex;border:1px solid var(--border);border-radius:var(--r-chip);overflow:hidden;
  background:var(--surface);}
.oseg button{font:inherit;font-size:12px;font-weight:600;border:0;background:none;padding:8px 13px;
  color:var(--ink-600);cursor:pointer;}
.oseg button + button{border-left:1px solid var(--border);}
.oseg button[aria-pressed="true"]{background:var(--primary-tint);color:var(--ink);}
.oseg button:focus-visible{outline:2px solid var(--primary);outline-offset:-2px;}
.ocount{margin:14px 0 10px;font-size:13px;color:var(--ink-600);}
.olist{list-style:none;margin:0;padding:0;display:grid;
  grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px;}
@media (max-width:520px){.olist{grid-template-columns:minmax(0,1fr);}}
.ocard{background:var(--surface);border:1px solid var(--border);border-radius:var(--r-card);
  padding:16px 18px;display:flex;flex-direction:column;gap:6px;scroll-margin-top:16px;}
.ocard:target{outline:2px solid var(--primary);}
.ohead{display:flex;flex-wrap:wrap;gap:8px;align-items:center;}
.otype{font-family:var(--font-ui);font-size:10px;font-weight:600;letter-spacing:.1em;
  text-transform:uppercase;padding:3px 8px;border-radius:var(--r-chip);}
.otype.government{background:var(--primary-tint);color:var(--primary-deep);}
.otype.academic{background:var(--mint-100);color:var(--green-text);}
.otype.corporate{background:var(--corp-tint);color:var(--corp-text);}
.ometa{font-size:12px;color:var(--ink-faint);}
.ocard h3{font-family:var(--font-display);font-size:16px;margin:2px 0 0;line-height:1.3;}
.odesc{margin:0;font-size:13.5px;color:var(--ink);line-height:1.5;text-wrap:pretty;}
.onote{margin:0;font-size:13px;color:var(--ink-600);line-height:1.5;}
.olinks{margin:4px 0 0;font-size:12.5px;word-break:break-word;}
.omore{font-size:12.5px;}
.omore summary{cursor:pointer;color:var(--ink-600);width:max-content;}
.omore .olinks{margin-top:2px;}
.ores{align-self:flex-start;margin-top:4px;font-size:12.5px;font-weight:600;}
.omap{background:var(--surface);border:1px solid var(--border);border-radius:var(--r-card);
  padding:14px;margin-top:14px;}
.omap-svg{display:block;width:100%;height:auto;}
.oframe rect{fill:var(--surface);stroke:var(--border);stroke-width:1;vector-effect:non-scaling-stroke;}
.oframe path{fill:var(--bg-alt);stroke:var(--surface);stroke-width:.6;vector-effect:non-scaling-stroke;}
/* zoom moves the viewBox; --z (set by the script) divides the pins' scale back out,
   so a pin keeps its size on screen at every zoom */
.omap-svg{touch-action:pan-y;}
.omap-svg.zoomed{cursor:grab;touch-action:none;}
.omap-svg.zoomed:active{cursor:grabbing;}
.ozoom{position:absolute;top:22px;left:22px;z-index:4;display:flex;flex-direction:column;
  border:1px solid var(--border);border-radius:var(--r-chip);overflow:hidden;background:var(--surface);
  box-shadow:var(--shadow-soft);}
.ozoom button{font:inherit;font-size:18px;font-weight:600;line-height:1;width:34px;height:34px;border:0;
  background:none;color:var(--ink);cursor:pointer;padding:0;}
.ozoom button + button{border-top:1px solid var(--border);}
.ozoom button.oreset{font-size:15px;}
.ozoom button:hover:not(:disabled),.ozoom button:focus-visible{background:var(--bg-alt);}
.ozoom button:focus-visible{outline:2px solid var(--primary);outline-offset:-2px;}
.ozoom button:disabled{color:var(--ink-faint);cursor:default;}
/* a phone's map is ~124px tall: the column would cover the Americas, so the
   buttons sit in a row under the map instead */
@media (max-width:600px){.ozoom{position:static;flex-direction:row;width:max-content;margin-top:10px;
  box-shadow:none;}.ozoom button + button{border-top:0;border-left:1px solid var(--border);}
  .ozoom button{width:44px;height:40px;}}
.odot{cursor:pointer;}
/* the map shrinks with the page and the pins with it: --pin scales them back up on
   narrow screens, about the tip (the place), so a pin stays a usable tap target */
.opin{transform:scale(calc(var(--pin,1) * var(--k,1) / var(--z,1)));transform-origin:0 0;}
@media (max-width:800px){.omap-svg{--pin:1.5;}}
@media (max-width:520px){.omap-svg{--pin:2.2;}}
.odot path{stroke:var(--surface);stroke-width:1.2;stroke-linejoin:round;}
.odot.government path{fill:var(--primary);}
.odot.academic path{fill:var(--green);}
.odot.corporate path{fill:var(--corp);}
.odot.mixed path{fill:var(--ink-600);}
.odot .ohole{fill:var(--surface);pointer-events:none;}
.odot text{font-family:var(--font-ui);font-size:7.5px;font-weight:700;fill:var(--white);
  text-anchor:middle;pointer-events:none;}
.odot:hover path,.odot:focus-visible path,.odot[aria-expanded="true"] path{stroke:var(--ink);stroke-width:1.8;}
.odot:focus{outline:none;}
.omap{position:relative;}
.opop{position:absolute;z-index:5;width:min(360px,calc(100% - 28px));max-height:min(70vh,480px);
  overflow:auto;background:var(--surface);border:1px solid var(--border);border-radius:var(--r-card);
  box-shadow:var(--shadow-soft);padding:8px;}
.opop-head{display:flex;justify-content:space-between;align-items:center;gap:8px;
  padding:2px 4px 6px 10px;font-size:12px;color:var(--ink-600);}
.opop-x{border:0;background:none;font-size:20px;line-height:1;padding:2px 8px;cursor:pointer;
  color:var(--ink-600);border-radius:var(--r-chip);}
.opop-x:hover,.opop-x:focus-visible{color:var(--ink);background:var(--bg-alt);}
.opop .olist{grid-template-columns:minmax(0,1fr);gap:8px;}
.opop .ocard{border:0;padding:8px 10px;}
.opop .ocard + .ocard{border-top:1px solid var(--border);border-radius:0;}
.okey{display:flex;flex-wrap:wrap;gap:16px;margin-top:10px;font-size:12px;color:var(--ink-600);}
.okey i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:-1px;}
.onote-map{margin:8px 0 0;font-size:12px;color:var(--ink-faint);}
.ohint{margin:8px 0 0;font-size:12px;color:var(--ink-faint);}
.ocred{margin-top:18px;font-size:12px;color:var(--ink-faint);line-height:1.6;}
"""

BODY = theme.page_header(
    '⟪OSPOs⟫',
    '⟪Open source program offices in government, universities and research institutes.⟫',
    [theme.data_links('/ospos.json')]) + """
<div class="wrap">
  <main id="main">
    <div class="obar">
      <input type="search" id="oq" autocomplete="off" placeholder="⟪Search offices&hellip;⟫"
             aria-label="⟪Search offices⟫">
      <div class="oseg" role="group" aria-label="⟪Type⟫">
        <button type="button" data-type="" aria-pressed="true">⟪All⟫</button>
        <button type="button" data-type="government" aria-pressed="false">⟪Government⟫</button>
        <button type="button" data-type="academic" aria-pressed="false">⟪Academic⟫</button>
        <button type="button" data-type="corporate" aria-pressed="false">⟪Corporate⟫</button>
      </div>
      <select id="occ" aria-label="⟪Filter by country⟫">
        <option value="">⟪Any country⟫</option>__COPTS__
      </select>
      <div class="oseg" id="oview" role="group" aria-label="⟪View⟫" hidden>
        <button type="button" data-view="cards" aria-pressed="true">⟪Cards⟫</button>
        <button type="button" data-view="map" aria-pressed="false">⟪Map⟫</button>
      </div>
    </div>
    <p class="ocount" id="ocount" aria-live="polite">⟪__N__ offices⟫</p>
    <ul class="olist" id="olist">__CARDS__</ul>
    <div class="omap" id="omap" hidden>__MAP__
      <div class="ozoom" id="ozoom" role="group" aria-label="⟪Zoom⟫">
        <button type="button" data-zoom="in" aria-label="⟪Zoom in⟫" title="⟪Zoom in⟫">+</button>
        <button type="button" data-zoom="out" aria-label="⟪Zoom out⟫" title="⟪Zoom out⟫">&minus;</button>
        <button type="button" class="oreset" data-zoom="reset" aria-label="⟪Show the whole world⟫"
          title="⟪Show the whole world⟫">&#8634;</button></div>
      <script type="application/json" id="ospots">__SPOTS__</script>
      <div class="opop" id="opop" role="dialog" aria-labelledby="opop-h" hidden>
        <div class="opop-head"><span id="opop-h"></span>
          <button type="button" class="opop-x" id="opop-x" aria-label="⟪Close⟫">&times;</button></div>
        <ul class="olist" id="opop-list"></ul>
      </div>
      <div class="okey"><span><i style="background:var(--primary)"></i>⟪Government⟫</span>
        <span><i style="background:var(--green)"></i>⟪Academic⟫</span>
        <span><i style="background:var(--corp)"></i>⟪Corporate⟫</span>
        <span><i style="background:var(--ink-600)"></i>⟪Several types, at one place⟫</span></div>
      <p class="ohint">⟪Zoom with the buttons, a pinch, Ctrl + scroll or a double-click; drag to move. Nearby offices share a numbered pin until you zoom in.⟫</p>
      __MAPNOTE__
    </div>
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
  </main>
</div>
"""

# View in the address bar (q, type, cc, view), validated like /software and
# /resources: an unknown value is IGNORED. el.hidden throughout.
SCRIPT = """
<script>
// build_ospos.py's merge, re-run at zoom z: greedy over spots already in merge order
// (largest first); a spot joins the first pin in its frame nearer than `within`
// SCREEN units, i.e. within / z map units. At z = 1 it is the build's own merge.
function ospoCluster(spots, within, z) {
  var out = [];
  spots.forEach(function (s) {
    for (var i = 0; i < out.length; i++) {
      var m = out[i];
      if (m.k === s[0] && Math.hypot(m.x - s[1], m.y - s[2]) * z < within) {
        m.ids = m.ids.concat(s[3]); m.places = m.places.concat(s[4]); return;
      }
    }
    out.push({k: s[0], x: s[1], y: s[2], ids: s[3].slice(), places: s[4].slice()});
  });
  out.forEach(function (m) { m.places = m.places.filter(function (p, i, a) { return a.indexOf(p) === i; }); });
  return out;
}
(function () {
  var el = function (id) { return document.getElementById(id); };
  var list = el('olist'), cards = [].slice.call(list.children), total = cards.length;
  var text = new Map(cards.map(function (c) { return [c, c.textContent.toLowerCase()]; }));
  var segT = [].slice.call(document.querySelectorAll('.oseg button[data-type]'));
  var segV = [].slice.call(document.querySelectorAll('#oview button'));
  var svg = document.querySelector('.omap-svg'), shown = null;
  var dots = function () { return [].slice.call(svg.querySelectorAll('.odot')); };
  var type = '', view = 'cards', timer = null;
  function apply(write) {
    closePop(false);
    var q = (el('oq').value || '').trim().toLowerCase(), cc = el('occ').value, n = 0;
    shown = {};
    cards.forEach(function (c) {
      var ok = (!q || text.get(c).indexOf(q) >= 0) && (!type || c.dataset.type === type) &&
        (!cc || c.dataset.cc === cc);
      c.hidden = !ok;
      if (ok) { n++; shown[c.id] = 1; }
    });
    hideDots();
    el('ocount').textContent = n === total ? '⟪js:{n} offices⟫'.replace('{n}', total)
      : '⟪js:{n} of {t} offices⟫'.replace('{n}', n).replace('{t}', total);
    segT.forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.type === type ? 'true' : 'false'); });
    segV.forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.view === view ? 'true' : 'false'); });
    list.hidden = view === 'map'; el('omap').hidden = view !== 'map';
    if (write) {
      var P = new URLSearchParams();
      if (q) P.set('q', el('oq').value.trim());
      if (type) P.set('type', type);
      if (cc) P.set('cc', cc);
      if (view === 'map') P.set('view', 'map');
      var qs = P.toString();
      clearTimeout(timer);
      // the hash is read when the write HAPPENS: a dot click sets #<office> after
      // calling apply(), and an earlier copy here dropped it
      timer = setTimeout(function () {
        try { history.replaceState(null, '', location.pathname + (qs ? '?' + qs : '') + location.hash); } catch (e) {}
      }, 250);
    }
  }
  try {
    var P = new URLSearchParams(location.search);
    if (P.get('q')) el('oq').value = P.get('q');
    if (['government', 'academic', 'corporate'].indexOf(P.get('type')) >= 0) type = P.get('type');
    var cc = P.get('cc');
    if (cc && [].some.call(el('occ').options, function (o) { return o.value === cc; })) el('occ').value = cc;
    if (P.get('view') === 'map' || location.hash === '#map') view = 'map';
  } catch (e) {}
  // SVG elements have no .hidden property: set the ATTRIBUTE, which theme.py's
  // [hidden]{display:none!important} matches on SVG as on HTML
  function hideDots() {
    dots().forEach(function (d) {
      if (d.dataset.ids.split(' ').some(function (i) { return shown[i]; })) d.removeAttribute('hidden');
      else d.setAttribute('hidden', '');
    });
  }
  segT.forEach(function (b) { b.onclick = function () { type = b.dataset.type; apply(true); }; });
  segV.forEach(function (b) { b.onclick = function () { view = b.dataset.view; apply(true); }; });
  el('oq').oninput = function () { apply(true); };
  el('occ').onchange = function () { apply(true); };
  // a pin opens a popup holding COPIES of its place's cards, so the content is
  // the cards' own; offices hidden by the current filters stay out of it
  var pop = el('opop'), popList = el('opop-list'), mapBox = el('omap'), openDot = null;
  function closePop(refocus) {
    if (!openDot) return;
    pop.hidden = true; popList.textContent = '';
    openDot.setAttribute('aria-expanded', 'false');
    if (refocus) openDot.focus();
    openDot = null;
  }
  function openPop(d) {
    closePop(false);
    var ids = d.dataset.ids.split(' ').filter(function (i) { var c = el(i); return c && !c.hidden; });
    if (!ids.length) return;
    ids.forEach(function (i) {
      var c = el(i).cloneNode(true);
      c.removeAttribute('id');
      popList.appendChild(c);
    });
    // the cards carry the names; the header says where (and how many, when shared)
    el('opop-h').textContent = [d.dataset.place,
      ids.length > 1 ? '⟪js:{n} offices⟫'.replace('{n}', ids.length) : ''].filter(Boolean).join(' \\u00b7 ');
    pop.hidden = false; openDot = d; d.setAttribute('aria-expanded', 'true');
    // beside the pin, kept inside the map box: right of it when there is room, else left
    var mb = mapBox.getBoundingClientRect(), pb = d.getBoundingClientRect();
    var w = pop.offsetWidth, x = pb.right - mb.left + 8;
    if (x + w > mb.width - 8) x = pb.left - mb.left - w - 8;
    x = Math.max(8, Math.min(x, mb.width - w - 8));
    pop.style.left = x + 'px';
    pop.style.top = Math.max(8, pb.top - mb.top - 12) + 'px';
    el('opop-x').focus();
  }
  // ---- zoom (owner, 2026-10-09). The viewBox moves; the pins are redrawn from
  // #ospots at each zoom, merged by ospoCluster(), and --z keeps them one size.
  var SP = JSON.parse(el('ospots').textContent), NS = 'http://www.w3.org/2000/svg';
  var VB0 = svg.getAttribute('viewBox').split(' ').map(Number), vb = VB0.slice();
  var ZMAX = 24, drawnAt = null, redraw = 0, moved = false;
  var zb = {};
  [].forEach.call(document.querySelectorAll('#ozoom button'), function (b) { zb[b.dataset.zoom] = b; });
  function mk(tag, at) {
    var e = document.createElementNS(NS, tag);
    for (var a in at) e.setAttribute(a, at[a]);
    return e;
  }
  function drawPins(z) {
    var groups = {};
    [].forEach.call(svg.querySelectorAll('.opins'), function (g) { groups[g.dataset.frame] = g; g.textContent = ''; });
    // drawn smallest first, so a numbered pin is never covered by a single one
    ospoCluster(SP.spots, SP.within, z).reverse().forEach(function (m) {
      var cs = m.ids.map(el).filter(Boolean), types = {};
      cs.forEach(function (c) { types[c.dataset.type] = 1; });
      var tk = Object.keys(types).sort(), one = m.ids.length === 1;
      var label = cs.map(function (c) {
        return c.querySelector('h3').textContent + ' (' + c.querySelector('.otype').textContent + ')';
      }).join('; ');
      var a = mk('a', {'class': 'odot ' + (tk.length === 1 ? tk[0] : 'mixed'), href: '#' + m.ids[0],
        'data-ids': m.ids.join(' '), 'data-place': m.places.join('; '), 'aria-label': label,
        'aria-haspopup': 'dialog', 'aria-expanded': 'false'});
      var t = mk('title', {}); t.textContent = label; a.appendChild(t);
      var g = mk('g', {transform: 'translate(' + m.x + ' ' + m.y + ')'});
      var p = mk('g', one ? {'class': 'opin'} : {'class': 'opin', style: '--k:1.3'});
      p.appendChild(mk('path', {d: SP.pin}));
      if (one) p.appendChild(mk('circle', {'class': 'ohole', cx: 0, cy: -10, r: 2.2}));
      else { var tx = mk('text', {x: 0, y: -7}); tx.textContent = m.ids.length; p.appendChild(tx); }
      g.appendChild(p); a.appendChild(g); groups[m.k].appendChild(a);
    });
    drawnAt = z;
    if (shown) hideDots();
  }
  function zoom() { return VB0[2] / vb[2]; }
  function setVB(x, y, w) {
    var z = Math.min(ZMAX, Math.max(1, VB0[2] / w));
    w = VB0[2] / z;
    var h = VB0[3] / z;
    x = Math.min(Math.max(x, VB0[0]), VB0[0] + VB0[2] - w);
    y = Math.min(Math.max(y, VB0[1]), VB0[1] + VB0[3] - h);
    vb = [x, y, w, h];
    closePop(false);
    svg.setAttribute('viewBox', vb.map(function (v) { return Math.round(v * 100) / 100; }).join(' '));
    svg.style.setProperty('--z', z);
    svg.classList.toggle('zoomed', z > 1.001);
    zb['in'].disabled = z >= ZMAX - 0.001;
    zb.out.disabled = zb.reset.disabled = z <= 1.001;
    // re-merge once per frame, not once per pointer event
    if (z !== drawnAt && !redraw) {
      redraw = requestAnimationFrame(function () { redraw = 0; if (zoom() !== drawnAt) drawPins(zoom()); });
    }
  }
  // zoom by f, keeping the map point (px, py) where it is on screen
  function zoomAt(f, px, py) {
    var z = Math.min(ZMAX, Math.max(1, zoom() * f));
    f = z / zoom();
    setVB(px - (px - vb[0]) / f, py - (py - vb[1]) / f, vb[2] / f);
  }
  function toMap(cx, cy) {
    var r = svg.getBoundingClientRect();
    return [vb[0] + (cx - r.left) / r.width * vb[2], vb[1] + (cy - r.top) / r.height * vb[3]];
  }
  function centre() { return [vb[0] + vb[2] / 2, vb[1] + vb[3] / 2]; }
  zb['in'].onclick = function () { var c = centre(); zoomAt(2, c[0], c[1]); };
  zb.out.onclick = function () { var c = centre(); zoomAt(0.5, c[0], c[1]); };
  zb.reset.onclick = function () { setVB(VB0[0], VB0[1], VB0[2]); };
  svg.addEventListener('wheel', function (e) {
    // Ctrl (or Cmd) + scroll, which is also what a trackpad pinch sends; a plain
    // scroll keeps scrolling the page
    if (!e.ctrlKey && !e.metaKey) return;
    e.preventDefault();
    var p = toMap(e.clientX, e.clientY);
    zoomAt(Math.exp(-Math.max(-60, Math.min(60, e.deltaY)) * 0.01), p[0], p[1]);
  }, {passive: false});
  svg.addEventListener('dblclick', function (e) {
    if (e.target.closest('.odot')) return;
    e.preventDefault();
    var p = toMap(e.clientX, e.clientY);
    zoomAt(e.shiftKey ? 0.5 : 2, p[0], p[1]);
  });
  // drag pans (when zoomed in); two pointers pinch. A drag is never a click.
  var ptrs = {}, gest = null;
  function startGesture() {
    var ids = Object.keys(ptrs), r = svg.getBoundingClientRect();
    gest = {vb: vb.slice(), r: r, p: ids.map(function (i) { return [ptrs[i][0], ptrs[i][1]]; })};
  }
  svg.addEventListener('pointerdown', function (e) {
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    if (!Object.keys(ptrs).length) moved = false;
    ptrs[e.pointerId] = [e.clientX, e.clientY];
    startGesture();
  });
  svg.addEventListener('pointermove', function (e) {
    if (!ptrs[e.pointerId]) return;
    ptrs[e.pointerId] = [e.clientX, e.clientY];
    var ids = Object.keys(ptrs), g = gest, u = g.vb[2] / g.r.width;
    if (ids.length === 1) {
      var dx = e.clientX - g.p[0][0], dy = e.clientY - g.p[0][1];
      if (!moved && Math.hypot(dx, dy) < 5) return;
      if (!moved) { moved = true; try { svg.setPointerCapture(e.pointerId); } catch (x) {} }
      if (zoom() > 1.001) setVB(g.vb[0] - dx * u, g.vb[1] - dy * u, g.vb[2]);
    } else if (ids.length === 2 && g.p.length === 2) {
      moved = true;
      var a = ptrs[ids[0]], b = ptrs[ids[1]];
      var d0 = Math.hypot(g.p[0][0] - g.p[1][0], g.p[0][1] - g.p[1][1]) || 1;
      var f = Math.hypot(a[0] - b[0], a[1] - b[1]) / d0;
      // the map point under the starting midpoint stays under the current one
      var m0x = g.vb[0] + ((g.p[0][0] + g.p[1][0]) / 2 - g.r.left) * u;
      var m0y = g.vb[1] + ((g.p[0][1] + g.p[1][1]) / 2 - g.r.top) * u;
      var w = g.vb[2] / f, u1 = w / g.r.width;
      setVB(m0x - ((a[0] + b[0]) / 2 - g.r.left) * u1, m0y - ((a[1] + b[1]) / 2 - g.r.top) * u1, w);
    }
  });
  function lift(e) {
    if (!ptrs[e.pointerId]) return;
    delete ptrs[e.pointerId];
    if (Object.keys(ptrs).length) startGesture();
  }
  svg.addEventListener('pointerup', lift);
  svg.addEventListener('pointercancel', lift);
  // one listener for every pin, the redrawn ones included
  svg.addEventListener('click', function (e) {
    var d = e.target.closest('.odot');
    if (moved) { moved = false; e.preventDefault(); e.stopPropagation(); return; }
    if (!d) return;
    e.preventDefault();
    if (openDot === d) closePop(false); else openPop(d);
  }, true);
  drawPins(1);
  setVB(VB0[0], VB0[1], VB0[2]);
  el('opop-x').onclick = function () { closePop(true); };
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && openDot) closePop(true); });
  document.addEventListener('click', function (e) {
    if (openDot && !pop.contains(e.target) && !openDot.contains(e.target)) closePop(false);
  });
  el('oview').hidden = false;
  apply(false);
})();
</script>
"""


if __name__ == "__main__":
    data, locs, geo, res = load()
    for _lang in i18n.LANGS:
        rows = build(_lang, data, locs, geo, res)
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
