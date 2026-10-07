"""Build site/ospos.html (served at /ospos) + site/ospos.json.

Open source program offices, government and academic, from two published
lists that fetch_ospos.py reads into cache/ospos.json: the FLOSS-PSO Network's
public-sector OSPO list (CC0) and the SustainOSS academic map (MIT). Records
stay English on every language copy; only the chrome is translated.

Two views of one list, like /catalogs: cards (the default, and all a reader
without JavaScript gets) and a map. The map is inline SVG from the committed
geo/ospo_frames.json (North America + Europe, written by geo/build_geo.py);
each office is placed from ospos/locations.json, hand-placed. Offices sharing a
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

import i18n
import sources as S

OUT = os.path.dirname(os.path.abspath(__file__))
SITE = f"{OUT}/site"
NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

_th = importlib.util.spec_from_file_location("theme", f"{OUT}/theme.py")
theme = importlib.util.module_from_spec(_th); _th.loader.exec_module(theme)
_tp = importlib.util.spec_from_file_location("_ui_template", f"{OUT}/_ui_template.py")
T = importlib.util.module_from_spec(_tp); _tp.loader.exec_module(T)

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


def laea(lon0, lat0):
    """The projection geo/build_geo.py used for these frames (spherical Lambert
    azimuthal equal-area). Pinned against each frame's `probe` by
    test_built_pages.py, so a drift between the two copies fails a check."""
    l0, p0 = math.radians(lon0), math.radians(lat0)
    sp0, cp0 = math.sin(p0), math.cos(p0)

    def f(lon, lat):
        lam, phi = math.radians(lon), math.radians(lat)
        c = math.cos(phi) * math.cos(lam - l0)
        k = math.sqrt(2.0 / max(1e-12, 1.0 + sp0 * math.sin(phi) + cp0 * c))
        return k * math.cos(phi) * math.sin(lam - l0), -k * (cp0 * math.sin(phi) - sp0 * c)
    return f


def place(frames, lon, lat):
    """(frame, x, y) for the first frame whose rectangle holds the point, else None."""
    for k, fr in frames.items():
        x, y = laea(*fr["centre"])(lon, lat)
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
    cname = lambda c: i18n.country(lang, c, S.COUNTRY_NAME.get(c, c)) if c else ""
    rcount = collections.Counter(r["case"] for r in res["resources"])
    os_ = sorted(data["ospos"], key=lambda r: (r["type"] != "government", r["name"].lower()))
    for r in os_:
        loc = locs.get(r["id"]) or {}
        r["_cc"] = r.get("country") or loc.get("country")
        r["_loc"] = loc
        case = RESOURCE_CASE.get(r["url"])
        r["_case"] = case if case and rcount.get(case) else None
    n_gov = sum(r["type"] == "government" for r in os_)
    n_aca = len(os_) - n_gov
    by_cc = collections.Counter(r["_cc"] for r in os_ if r["_cc"])

    cards = []
    for r in os_:
        links = ['<a href="%s" target="_blank" rel="noopener">%s</a>'
                 % (esc(r["url"]), esc(_("Website")))]
        for c in r.get("code") or []:
            links.append('<a href="%s" target="_blank" rel="noopener">%s</a>' % (esc(c), esc(_("Code"))))
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
        typ = _("Government") if r["type"] == "government" else _("Academic")
        meta = [esc(cname(r["_cc"]))] if r["_cc"] else []
        if r["_loc"].get("place"):
            meta.append(esc(r["_loc"]["place"]))
        if r.get("created"):
            meta.append(esc(_("since {y}", y=str(r["created"])[:4])))
        cards.append(
            '<li class="ocard" id="%s" data-type="%s" data-cc="%s">'
            '<div class="ohead"><span class="otype %s">%s</span><span class="ometa">%s</span></div>'
            '<h3>%s</h3>%s%s'
            '<p class="olinks">%s</p>%s</li>'
            % (esc(r["id"]), esc(r["type"]), esc(r["_cc"] or ""), esc(r["type"]), esc(typ),
               " &middot; ".join(meta), esc(r["name"]),
               ('<p class="odesc">%s</p>' % esc(r["description"])) if r.get("description") else "",
               ('<p class="onote"><b>%s</b> %s</p>' % (esc(_("OSPO:")), esc(r["ospo_note"])))
               if r.get("ospo_note") else "",
               " &middot; ".join(links), res_link))

    # ---- the map: one dot per spot; offices sharing a spot share a dot
    spots = collections.OrderedDict()
    unplaced = []
    for r in os_:
        loc = r["_loc"]
        p = place(geo["frames"], loc["lon"], loc["lat"]) if loc.get("lat") is not None else None
        if not p:
            unplaced.append(r)
            continue
        spots.setdefault(p, []).append(r)
    vx, vy, vw, vh = geo["viewbox"]
    svg = ['<svg class="omap-svg" viewBox="%s %s %s %s" role="group" aria-label="%s">'
           % (vx, vy, vw, vh, esc(_("Map of open source program offices")))]
    for k, fr in geo["frames"].items():
        rx, ry, rw, rh = fr["rect"]
        svg.append('<g class="oframe"><rect x="%s" y="%s" width="%s" height="%s" rx="8"/>'
                   '<path d="%s" aria-hidden="true"/></g>' % (rx, ry, rw, rh, fr["land"]))
    for (k, x, y), rs in sorted(spots.items(), key=lambda kv: -len(kv[1])):
        label = "; ".join("%s (%s)" % (r["name"], _("Government") if r["type"] == "government"
                                       else _("Academic")) for r in rs)
        types = sorted({r["type"] for r in rs})
        cls = types[0] if len(types) == 1 else "mixed"
        svg.append('<a class="odot %s" href="#%s" data-ids="%s" aria-label="%s"><title>%s</title>'
                   '<circle cx="%s" cy="%s" r="%s"/>%s</a>'
                   % (cls, esc(rs[0]["id"]), esc(" ".join(r["id"] for r in rs)), esc(label), esc(label),
                      x, y, 5.5 if len(rs) == 1 else 7.5,
                      ('<text x="%s" y="%s">%d</text>' % (x, y + 3.2, len(rs))) if len(rs) > 1 else ""))
    svg.append("</svg>")
    note = ""
    if unplaced:
        note = ('<p class="onote-map">%s</p>'
                % esc(_("{n} not on the map yet (no location recorded): {names}",
                        n=len(unplaced), names="; ".join(r["name"] for r in unplaced))))

    copts = "".join('<option value="%s">%s (%s)</option>' % (esc(c), esc(cname(c)), N(n))
                    for c, n in sorted(by_cc.items(), key=lambda kv: cname(kv[0])))
    src = data.get("sources") or {}
    def fetched(key):
        st = src.get(key) or {}
        when = (st.get("fetched_at") or "")[:10] or _("never")
        return when + ("" if st.get("ok", True) else " &middot; " + esc(_("last fetch failed, showing the previous list")))

    subs = {
        "__N__": N(len(os_)), "__NGOV__": N(n_gov), "__NACA__": N(n_aca),
        "__CARDS__": "".join(cards), "__MAP__": "".join(svg), "__MAPNOTE__": note,
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
    print("ospos page [%s]: %d OSPOs (%d government, %d academic), %d map spots, %d unplaced (%.0f KB)"
          % (lang, len(os_), n_gov, n_aca, len(spots), len(unplaced), len(page) / 1024))
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
.ometa{font-size:12px;color:var(--ink-faint);}
.ocard h3{font-family:var(--font-display);font-size:16px;margin:2px 0 0;line-height:1.3;}
.odesc{margin:0;font-size:13.5px;color:var(--ink);line-height:1.5;text-wrap:pretty;}
.onote{margin:0;font-size:13px;color:var(--ink-600);line-height:1.5;}
.olinks{margin:4px 0 0;font-size:12.5px;word-break:break-word;}
.ores{align-self:flex-start;margin-top:4px;font-size:12.5px;font-weight:600;}
.omap{background:var(--surface);border:1px solid var(--border);border-radius:var(--r-card);
  padding:14px;margin-top:14px;}
.omap-svg{display:block;width:100%;height:auto;}
.oframe rect{fill:var(--surface);stroke:var(--border);stroke-width:1;}
.oframe path{fill:var(--bg-alt);stroke:var(--surface);stroke-width:.6;}
.odot circle{stroke:var(--surface);stroke-width:1.5;}
.odot.government circle{fill:var(--primary);}
.odot.academic circle{fill:var(--green);}
.odot.mixed circle{fill:var(--ink-600);}
.odot text{font-family:var(--font-ui);font-size:8px;font-weight:700;fill:var(--white);
  text-anchor:middle;pointer-events:none;}
.odot:hover circle,.odot:focus-visible circle{stroke:var(--ink);stroke-width:2;}
.odot:focus{outline:none;}
.okey{display:flex;flex-wrap:wrap;gap:16px;margin-top:10px;font-size:12px;color:var(--ink-600);}
.okey i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:-1px;}
.onote-map{margin:8px 0 0;font-size:12px;color:var(--ink-faint);}
.ocred{margin-top:18px;font-size:12px;color:var(--ink-faint);line-height:1.6;}
"""

BODY = """
<div class="hero hero-sw tex">
  <div class="inner">
    <p class="overline">⟪OSPOs⟫</p>
    <h1>⟪Open source program offices⟫</h1>
    <p class="lede">⟪__N__ offices that help their organisations use, publish and contribute to open
      source &mdash; __NGOV__ in government and __NACA__ in universities and research institutes.⟫</p>
  </div>
</div>
<div class="wrap">
  <main id="main">
    <div class="obar">
      <input type="search" id="oq" autocomplete="off" placeholder="⟪Search offices&hellip;⟫"
             aria-label="⟪Search offices⟫">
      <div class="oseg" role="group" aria-label="⟪Type⟫">
        <button type="button" data-type="" aria-pressed="true">⟪All⟫</button>
        <button type="button" data-type="government" aria-pressed="false">⟪Government⟫</button>
        <button type="button" data-type="academic" aria-pressed="false">⟪Academic⟫</button>
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
      <div class="okey"><span><i style="background:var(--primary)"></i>⟪Government⟫</span>
        <span><i style="background:var(--green)"></i>⟪Academic⟫</span>
        <span><i style="background:var(--ink-600)"></i>⟪Both, at one place⟫</span></div>
      __MAPNOTE__
    </div>
    <p class="ocred">⟪Government offices: the <a href="https://floss-pso.network/public-sector-ospos/">FLOSS-PSO
      Network</a>'s public-sector OSPO list (CC0), fetched __FLOSS_AT__. Academic offices: the
      <a href="https://sustainoss.org/academic-map/">SustainOSS academic map</a> (MIT), the
      universities and research institutes it lists under &ldquo;OSPOs&rdquo;, fetched __AMAP_AT__.
      Two FLOSS-PSO offices are universities and are shown as academic. Locations are placed by
      govoss at each office&rsquo;s city or its organisation&rsquo;s headquarters. The same data:
      <a href="/ospos.json">/ospos.json</a>.⟫</p>
  </main>
</div>
"""

# View in the address bar (q, type, cc, view), validated like /software and
# /resources: an unknown value is IGNORED. el.hidden throughout.
SCRIPT = """
<script>
(function () {
  var el = function (id) { return document.getElementById(id); };
  var list = el('olist'), cards = [].slice.call(list.children), total = cards.length;
  var text = new Map(cards.map(function (c) { return [c, c.textContent.toLowerCase()]; }));
  var segT = [].slice.call(document.querySelectorAll('.oseg button[data-type]'));
  var segV = [].slice.call(document.querySelectorAll('#oview button'));
  var dots = [].slice.call(document.querySelectorAll('.odot'));
  var type = '', view = 'cards', timer = null;
  function apply(write) {
    var q = (el('oq').value || '').trim().toLowerCase(), cc = el('occ').value, n = 0, shown = {};
    cards.forEach(function (c) {
      var ok = (!q || text.get(c).indexOf(q) >= 0) && (!type || c.dataset.type === type) &&
        (!cc || c.dataset.cc === cc);
      c.hidden = !ok;
      if (ok) { n++; shown[c.id] = 1; }
    });
    // SVG elements have no .hidden property: set the ATTRIBUTE, which theme.py's
    // [hidden]{display:none!important} matches on SVG as on HTML
    dots.forEach(function (d) {
      if (d.dataset.ids.split(' ').some(function (i) { return shown[i]; })) d.removeAttribute('hidden');
      else d.setAttribute('hidden', '');
    });
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
    if (['government', 'academic'].indexOf(P.get('type')) >= 0) type = P.get('type');
    var cc = P.get('cc');
    if (cc && [].some.call(el('occ').options, function (o) { return o.value === cc; })) el('occ').value = cc;
    if (P.get('view') === 'map' || location.hash === '#map') view = 'map';
  } catch (e) {}
  segT.forEach(function (b) { b.onclick = function () { type = b.dataset.type; apply(true); }; });
  segV.forEach(function (b) { b.onclick = function () { view = b.dataset.view; apply(true); }; });
  el('oq').oninput = function () { apply(true); };
  el('occ').onchange = function () { apply(true); };
  // a dot opens its office's card in the card view
  dots.forEach(function (d) {
    d.addEventListener('click', function (e) {
      e.preventDefault(); view = 'cards'; apply(true);
      var c = el(d.dataset.ids.split(' ')[0]);
      if (c) { c.scrollIntoView({ block: 'center' }); history.replaceState(null, '', location.pathname + location.search + '#' + c.id); }
    });
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
    with open(f"{SITE}/ospos.json", "w") as fh:
        json.dump({
            "generated_at": NOW, "human_page": i18n.BASE + "/ospos",
            "about": "Open source program offices. Government: the FLOSS-PSO Network's "
                     "public-sector OSPO list (CC0). Academic: the SustainOSS academic map's "
                     "'OSPOs' lists (MIT). Locations are govoss's hand placement (basis: seat or hq).",
            "sources": data.get("sources"),
            "ospos": [dict({k: v for k, v in r.items() if not k.startswith("_")},
                           country=r["_cc"], location=r["_loc"] or None,
                           resources_case=r["_case"]) for r in rows],
        }, fh, ensure_ascii=False, indent=1)
    i18n.report("build_ospos")
