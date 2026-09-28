"""The map on /sources.html, and /catalogues.geo.json beside it.

Reads geo/catalogue_shapes.json (committed; written by geo/build_geo.py, which
is manual and never part of run.sh) and joins THIS run's per-catalogue counts
onto it. No map library, no tile server, no request to anyone at page load: the
shapes are inline SVG. See geo/build_geo.py for why.

Rules this file keeps:
  * Every catalogue in sources.py is on the map or named beside it: a shaded
    country, a city dot (`map_point`), the dashed EU outline, or the Global chip.
    test_built_pages.py pins that, so a 21st catalogue cannot silently vanish.
  * NEVER render a sum of counts per country. An entry listed by two catalogues
    counts under each, and the Global/EU entries count nowhere, so a sum matches
    no real total. Each catalogue's own count is shown, never their total.
  * A shaded country means one of its governments' catalogues is harvested - not
    that the catalogue covers the country. The caveat ships under the map, and in
    the GeoJSON.
  * No f-strings for markup (plain strings, % and join), like every page builder.
"""
import json
import os
from urllib.parse import quote

import i18n
import sources as S

HERE = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT = os.path.join(HERE, "geo", "catalogue_shapes.json")


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _groups():
    """sources.py -> {country code: [source keys]} for shaded countries, the city
    catalogues, and the ones with no shape (EU, GLOBAL)."""
    by_cc, cities, off = {}, [], []
    for key, meta in S.SOURCES.items():
        if "map_point" in meta:
            cities.append(key)
        if meta["country"] in ("EU", "GLOBAL"):
            off.append(key)
        else:
            by_cc.setdefault(meta["country"], []).append(key)
    return by_cc, cities, off


def render(lang, counts, country_name):
    """(section html, geojson dict). `counts` is entries per ORIGINAL source key,
    the same Counter the catalogue rows use. `country_name(lang, code)` is the
    page's localised namer."""
    _ = lambda msg, **kw: i18n.t(lang, msg, **kw)
    N = lambda n: i18n.num(lang, n)
    geo = json.load(open(SNAPSHOT))
    by_cc, cities, off = _groups()

    def item(key):
        return _("{label}, {n} entries", label=S.SOURCES[key]["label"], n=N(counts.get(key, 0)))

    def src_href(key):
        return "/?src=" + quote(S.SOURCES[key]["label"], safe="")

    vx, vy, vw, vh = geo["viewbox"]
    parts = ['<svg class="cmap-svg" viewBox="%s %s %s %s" role="group" aria-label="%s">'
             % (vx, vy, vw, vh, esc(_("Map of the countries whose government catalogues "
                                       "govoss harvests")))]
    parts.append('<g class="bg" aria-hidden="true"><path d="%s"/></g>' % geo["background"]["europe"])

    def country_links(frame):
        out = []
        for cc in sorted(by_cc):
            shp = geo["shapes"].get(cc)
            if not shp or shp["frame"] != frame:
                continue
            keys = by_cc[cc]
            label = _("{country}: {items}", country=country_name(lang, cc),
                      items="; ".join(item(k) for k in keys))
            tier = "n%d" % min(3, len(keys))
            out.append('<a href="/?cc=%s" aria-label="%s"><title>%s</title>'
                       '<path class="%s" d="%s"/></a>'
                       % (cc, esc(label), esc(label), tier, shp["d"]))
        return out

    parts.append('<g class="fill">' + "".join(country_links("europe")) + '</g>')
    parts.append('<path class="eu" aria-hidden="true" d="%s"/>' % geo["eu"])
    for key in cities:
        x, y = geo["points"][key]
        label = item(key)
        parts.append('<a class="city" href="%s" aria-label="%s"><title>%s</title>'
                     '<circle cx="%s" cy="%s" r="5.5"/></a>'
                     % (src_href(key), esc(label), esc(label), x, y))
    # insets last, on white cards over the Atlantic
    for frame, cc in (("canada", "CA"), ("taiwan", "TW")):
        rx, ry, rw, rh = geo["frames"][frame]
        parts.append('<g class="inset"><rect x="%s" y="%s" width="%s" height="%s" rx="6"/>'
                     '<g class="bg" aria-hidden="true"><path d="%s"/></g>'
                     '<g class="fill">%s</g>'
                     '<text x="%s" y="%s" aria-hidden="true">%s</text></g>'
                     % (rx, ry, rw, rh, geo["background"][frame],
                        "".join(country_links(frame)), rx + 8, ry + rh - 8,
                        esc(country_name(lang, cc))))
    parts.append("</svg>")
    svg = "".join(parts)

    sw = lambda cls, txt: '<li><i class="sw %s"></i>%s</li>' % (cls, txt)
    legend = ('<ul class="cmap-key">'
              + sw("n1", _("1 catalogue")) + sw("n2", _("{n} catalogues", n=2))
              + sw("n3", _("{n} catalogues", n=3))
              + sw("city", _("a city's catalogue"))
              + sw("eu", _("the European Union"))
              + "</ul>")
    beside = "".join(
        '<li><a href="%s">%s</a> <span>%s</span></li>'
        % (src_href(k), esc(S.SOURCES[k]["label"]),
           esc(_("{n} entries", n=N(counts.get(k, 0)))) + " &middot; " +
           esc(_("the European Union") if S.SOURCES[k]["country"] == "EU" else _("global")))
        for k in off)
    # The MAP VIEW of "Harvested catalogues" (the cards are the default view);
    # build_sources.py places it and owns the switch between the two.
    html = ('<div class="cmap">%s<div class="cmap-side"><p class="cmap-hint">%s</p>%s'
            '<p class="cmap-h">%s</p><ul class="cmap-off">%s</ul>'
            '<p class="cmap-note">%s</p><p class="cmap-cred">%s</p></div></div>'
            % (svg, esc(_("Select a country to see its entries in the catalog.")), legend,
               esc(_("Not drawn as a country")), beside,
               esc(_("A shaded country has at least one catalogue from its national, regional "
                     "or city government. It does not mean that catalogue covers the whole "
                     "country.")),
               _("Boundaries: Natural Earth (public domain). The same shapes with these "
                 "counts: {link}", link='<a href="/catalogues.geo.json">/catalogues.geo.json</a>')))

    # ---- /catalogues.geo.json: lon/lat, one feature per shaded country, the EU
    # outline, a point per city catalogue. Language-neutral (English names), like
    # every JSON here. Deliberately NO per-country total - see the module doc.
    def cat(key):
        m = S.SOURCES[key]
        return {"key": key, "label": m["label"], "entries": counts.get(key, 0),
                "catalog_url": "https://govoss.cat" + src_href(key)}
    feats = []
    for cc in sorted(by_cc):
        feats.append({"type": "Feature", "geometry": geo["lonlat"][cc],
                      "properties": {"kind": "country", "code": cc,
                                     "name": S.country_label(cc),
                                     "catalogues": [cat(k) for k in by_cc[cc]]}})
    eu_keys = [k for k in off if S.SOURCES[k]["country"] == "EU"]
    feats.append({"type": "Feature", "geometry": geo["lonlat"]["EU"],
                  "properties": {"kind": "union", "code": "EU", "name": "European Union",
                                 "members": geo["eu27"],
                                 "catalogues": [cat(k) for k in eu_keys]}})
    for key in cities:
        lon, lat = S.SOURCES[key]["map_point"]
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
                      "properties": {"kind": "city", "code": S.SOURCES[key]["country"],
                                     "catalogues": [cat(key)]}})
    gj = {"type": "FeatureCollection",
          "about": "Where govoss's harvested catalogues are. A country feature means at "
                   "least one of its governments' catalogues is harvested - national, "
                   "regional or city - NOT that the catalogue covers the country. Counts are "
                   "per catalogue and must not be summed: an entry in two catalogues counts "
                   "under each, and global catalogues have no shape.",
          "not_drawn": [cat(k) for k in off if S.SOURCES[k]["country"] != "EU"],
          "trimmed": geo["trimmed"],
          "licence": {"geometry": "Natural Earth, public domain",
                      "properties": "CC BY 4.0, govoss (https://govoss.cat)"},
          "source": {"geometry": geo["source"], "geometry_sha256": geo["source_sha256"]},
          "features": feats}
    return html, gj


CSS = """
/* catalogue map (sources_map.py) */
.cmap{display:grid;grid-template-columns:minmax(0,1.9fr) minmax(220px,1fr);gap:20px 28px;
  align-items:start;background:var(--surface);border:1px solid var(--border);
  border-radius:var(--r-card);padding:16px 20px;margin-top:14px;}
@media (max-width:820px){.cmap{grid-template-columns:minmax(0,1fr);}}
.cmap-svg{display:block;width:100%;height:auto;}
.cmap-svg .bg path{fill:var(--bg-alt);stroke:var(--surface);stroke-width:.6;}
.cmap-svg .fill path{stroke:var(--surface);stroke-width:.7;}
.cmap-svg .n1,.cmap-key .n1{fill:var(--primary-lter);background:var(--primary-lter);}
.cmap-svg .n2,.cmap-key .n2{fill:var(--primary-lt);background:var(--primary-lt);}
.cmap-svg .n3,.cmap-key .n3{fill:var(--primary);background:var(--primary);}
.cmap-svg a:hover path,.cmap-svg a:focus-visible path{fill:var(--primary-deep);}
.cmap-svg a:focus{outline:none;}
.cmap-svg a:focus-visible path,.cmap-svg a:focus-visible circle{stroke:var(--ink);stroke-width:2;}
.cmap-svg .eu{fill:none;stroke:var(--ink-600);stroke-width:1.1;stroke-dasharray:4 3;
  pointer-events:none;}
.cmap-svg .city circle{fill:var(--ink);stroke:var(--surface);stroke-width:2;}
.cmap-svg .city:hover circle{fill:var(--primary-deep);}
.cmap-svg .inset rect{fill:var(--surface);stroke:var(--border);stroke-width:1;}
.cmap-svg .inset text{font-family:var(--font-ui);font-size:11px;fill:var(--ink-600);}
.cmap-side{font-size:13px;color:var(--ink-600);}
.cmap-hint{margin:0 0 12px;color:var(--ink);}
/* the Cards / Map switch in the "Harvested catalogues" header */
.vtog{display:inline-flex;border:1px solid var(--border);border-radius:var(--r-chip);
  overflow:hidden;background:var(--surface);}
.vtog button{font:inherit;font-size:12px;font-weight:600;border:0;background:none;
  padding:6px 14px;color:var(--ink-600);cursor:pointer;}
.vtog button + button{border-left:1px solid var(--border);}
.vtog button[aria-pressed="true"]{background:var(--primary-tint);color:var(--ink);}
.vtog button:focus-visible{outline:2px solid var(--primary);outline-offset:-2px;}
.sechead .hl{display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
.cmap-key,.cmap-off{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:6px;}
.cmap-key li{display:flex;align-items:center;gap:8px;}
.cmap-key .sw{display:inline-block;width:14px;height:14px;border-radius:3px;flex:0 0 14px;}
.cmap-key .sw.city{border-radius:50%;background:var(--ink);transform:scale(.8);}
.cmap-key .sw.eu{background:none;border:1.5px dashed var(--ink-600);}
.cmap-h{font-family:var(--font-ui);font-size:10px;font-weight:600;letter-spacing:.12em;
  text-transform:uppercase;color:var(--ink-faint);margin:18px 0 6px;}
.cmap-off a{font-weight:600;}
.cmap-off span{color:var(--ink-faint);font-size:12px;}
.cmap-note{margin:16px 0 0;line-height:1.5;text-wrap:pretty;}
.cmap-cred{margin:8px 0 0;font-size:12px;color:var(--ink-faint);}
"""
