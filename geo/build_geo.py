"""Build geo/catalogue_shapes.json - the boundaries /sources.html draws its map from.

    python3 geo/build_geo.py [ne_50m_admin_0_countries.geojson]

ONE-TIME and MANUAL, never part of run.sh. The weekly run reads the committed
snapshot and only joins this week's counts onto it, so the map can never break a
harvest and no reader's page load ever asks a third party for anything. That is
the same reason the fonts are vendored (GDPR), and the lesson un.opensource.nyc
paid for: its CARTO basemap went behind an API key and kept answering HTTP 200
with every tile stamped "API KEY REQUIRED". A snapshot cannot degrade silently.

Re-run it when sources.py gains a country (it REFUSES to write if any catalogue
country has no shape) or a city catalogue (`map_point`), and read the summary.

Geometry: Natural Earth 1:50m admin-0 countries, public domain. 1:50m rather
than the 1:110m UNNYC uses because this is a EUROPE map, where Switzerland,
Belgium, Denmark and Ireland must be legible. Needs shapely (this script only;
build_sources.py does not).

Projection: spherical Lambert azimuthal equal-area, one per frame - the family
EU statistics use (EPSG:3035 is its ellipsoidal form), so areas are honest.
"""
import datetime
import hashlib
import json
import math
import os
import sys
import tempfile
import urllib.request

from shapely.geometry import box, mapping, shape, Polygon, MultiPolygon, Point
from shapely.ops import transform, unary_union
from shapely.validation import make_valid

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import sources as S  # noqa: E402

NE_URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
          "geojson/ne_50m_admin_0_countries.geojson")
OUT = os.path.join(HERE, "geo", "catalogue_shapes.json")

# Codes with no shape of their own. They are shown beside the map instead
# (a dashed EU outline, a "Global" chip) - never silently left off.
OFF_MAP = {"GLOBAL", "EU"}

EU27 = ["AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU",
        "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"]

# Frames: centre (lon, lat) of the projection, the lon/lat box shown, and the
# size in viewBox units. Europe is the map; the others are insets drawn in the
# Atlantic column to its left. A catalogue country outside Europe needs an
# inset named here, or the script refuses.
MAIN_W = 640.0
INSET_W, INSET_H, GAP = 196.0, 132.0, 14.0
FRAMES = {
    "europe": {"centre": (10.0, 52.0), "box": (-11.0, 35.5, 32.5, 70.5)},
    "canada": {"centre": (-96.0, 62.0), "box": (-141.0, 41.5, -52.0, 83.5), "codes": ["CA"]},
    "taiwan": {"centre": (121.0, 23.7), "box": (118.6, 21.6, 123.4, 25.6), "codes": ["TW"]},
}

# Editorial trims, each named with its reason and recorded in the output.
# NEVER generalise into a "drop distant parts" rule: Canada is 30 parts and most
# sit far from the mainland (UNNYC's MAP-LAYERS.md measured it).
TRIM = {
    "FR": {"keep": (-6.0, 41.0, 10.0, 51.5),
           "reason": "Metropolitan France and Corsica only. French Guiana, the Antilles, "
                     "Reunion and Mayotte are France, but outside this map's frame."},
}


def ne_code(p):
    """Natural Earth's ISO_A2 is -99 for France (and Norway, Kosovo...), and
    Taiwan's is CN-TW. Matching on ISO_A2 alone silently drops the largest
    catalogue here. Fall through the fields UNNYC's script settled on."""
    for f in ("ISO_A2_EH", "ISO_A2", "WB_A2"):
        v = p.get(f)
        if v and v != "-99" and "-" not in v:
            return v
    return p.get("ADM0_A3")


def laea(lon0, lat0):
    l0, p0 = math.radians(lon0), math.radians(lat0)
    sp0, cp0 = math.sin(p0), math.cos(p0)

    def f(lon, lat, z=None):
        lam, phi = math.radians(lon), math.radians(lat)
        c = math.cos(phi) * math.cos(lam - l0)
        k = math.sqrt(2.0 / max(1e-12, 1.0 + sp0 * math.sin(phi) + cp0 * c))
        x = k * math.cos(phi) * math.sin(lam - l0)
        y = k * (cp0 * math.sin(phi) - sp0 * c)
        return x, -y          # SVG y grows downward
    return f


def proj_geom(g, f):
    return transform(lambda xs, ys, zs=None: tuple(zip(*[f(x, y) for x, y in zip(xs, ys)])), g)


def densified_box(b, n=60):
    x0, y0, x1, y1 = b
    pts = ([(x0 + (x1 - x0) * i / n, y0) for i in range(n)] +
           [(x1, y0 + (y1 - y0) * i / n) for i in range(n)] +
           [(x1 - (x1 - x0) * i / n, y1) for i in range(n)] +
           [(x0, y1 - (y1 - y0) * i / n) for i in range(n)])
    return Polygon(pts)


def fit(frame, w, h=None):
    """Scale + offset putting the frame's projected lon/lat box into w (x h)."""
    f = laea(*frame["centre"])
    bx = proj_geom(densified_box(frame["box"]), f).bounds
    sx = w / (bx[2] - bx[0])
    s = sx if h is None else min(sx, h / (bx[3] - bx[1]))
    return f, bx, s


def to_d(g, nd=1):
    """Polygon/MultiPolygon -> SVG path data, coordinates rounded to nd decimals."""
    polys = [g] if isinstance(g, Polygon) else list(getattr(g, "geoms", []))
    out = []
    for p in polys:
        if not isinstance(p, Polygon) or p.is_empty:
            continue
        for ring in [p.exterior] + list(p.interiors):
            c = list(ring.coords)[:-1]
            if len(c) < 3:
                continue
            out.append("M" + "L".join("%s,%s" % (round(x, nd), round(y, nd)) for x, y in c) + "Z")
    return "".join(out).replace(".0,", ",").replace(".0L", "L").replace(".0Z", "Z")


def polys_only(g):
    if isinstance(g, (Polygon, MultiPolygon)):
        return g
    parts = [p for p in getattr(g, "geoms", []) if isinstance(p, (Polygon, MultiPolygon))]
    return unary_union(parts) if parts else Polygon()


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if not src:
        src = os.path.join(tempfile.mkdtemp(), "ne_50m.geojson")
        print("fetching", NE_URL)
        urllib.request.urlretrieve(NE_URL, src)
    raw = open(src, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    ne = json.loads(raw)
    by_code = {}
    for feat in ne["features"]:
        c = ne_code(feat["properties"])
        g = shape(feat["geometry"])
        by_code[c] = by_code[c].union(g) if c in by_code else g

    wanted = sorted({meta["country"] for meta in S.SOURCES.values()} - OFF_MAP)
    missing = [c for c in wanted if c not in by_code]
    if missing:
        raise SystemExit("REFUSING: no Natural Earth shape for %s. Fix ne_code() or add "
                         "the code to OFF_MAP with a reason." % missing)
    frame_of = {c: k for k, fr in FRAMES.items() for c in fr.get("codes", [])}

    # ---- trims (named, recorded)
    trimmed = []
    for c, t in TRIM.items():
        if c not in by_code:
            continue
        g = by_code[c]
        parts = list(getattr(g, "geoms", [g]))
        keep = [p for p in parts if p.intersects(box(*t["keep"]))]
        trimmed.append({"code": c, "parts_kept": len(keep),
                        "parts_dropped": len(parts) - len(keep), "reason": t["reason"]})
        by_code[c] = unary_union(keep)

    # ---- layout: europe on the right, insets stacked in a column on its left
    fe, bxe, se = fit(FRAMES["europe"], MAIN_W)
    main_h = (bxe[3] - bxe[1]) * se
    left = INSET_W + GAP
    rects = {"europe": [left, 0.0, MAIN_W, round(main_h, 1)]}
    y = 0.0
    for k in ("canada", "taiwan"):
        rects[k] = [0.0, y, INSET_W, INSET_H]
        y += INSET_H + GAP
    height = max(main_h, y - GAP)

    frames = {}
    for k, fr in FRAMES.items():
        rx, ry, rw, rh = rects[k]
        if k == "europe":
            f, bx, s = fe, bxe, se
        else:
            pad = 8.0
            f, bx, s = fit(fr, rw - 2 * pad, rh - 2 * pad)
        pw, ph = (bx[2] - bx[0]) * s, (bx[3] - bx[1]) * s
        ox = rx + (rw - pw) / 2 - bx[0] * s
        oy = ry + (rh - ph) / 2 - bx[1] * s
        clip = box(rx, ry, rx + rw, ry + rh)
        if k == "europe":
            # Europe fills the WHOLE viewBox: west of its box is open Atlantic,
            # where the insets sit (drawn over it on a white card), so no blank
            # column is left under them.
            rects["europe"] = [0.0, 0.0, round(left + MAIN_W, 1), round(height, 1)]
            clip = box(0, 0, left + MAIN_W, height)

        # Europe's land is cut at 13W (Iceland excepted): Madeira, the Azores and
        # the Canaries are real, but at this scale they are specks that read as
        # stray marks, and two were shaded (Portugal) in the empty Atlantic.
        land = (box(-13.0, 30.0, 60.0, 80.0).union(box(-25.0, 62.0, -13.0, 68.0))
                if k == "europe" else None)

        def place(g, f=f, s=s, ox=ox, oy=oy, clip=clip, land=land):
            if land is not None:
                g = g.intersection(land)
            pg = proj_geom(g, f)
            pg = transform(lambda xs, ys, zs=None: (tuple(x * s + ox for x in xs),
                                                   tuple(y * s + oy for y in ys)), pg)
            # projection can fold a ring (a clipped Russia did); repair before clipping
            return polys_only(make_valid(pg).intersection(clip))
        frames[k] = {"place": place, "f": f, "s": s, "ox": ox, "oy": oy,
                     "lonlat": box(*fr["box"]).buffer(25)}

    # viewBox units; the page renders at ~0.4-1.3 px per unit. Tuned for BYTES: the
    # path data ships inside /sources.html, and 0.35 made it ~140 KB.
    TOL = {"europe": 0.7, "canada": 1.0, "taiwan": 0.5}
    MIN_AREA = 1.5    # drop islands under ~1 px from background and outline

    def drop_specks(g):
        parts = [p for p in getattr(g, "geoms", [g]) if isinstance(p, Polygon) and p.area >= MIN_AREA]
        return MultiPolygon(parts) if parts else Polygon()

    background, shapes = {}, {}
    for k, fr in frames.items():
        near = [g for g in by_code.values() if g.intersects(fr["lonlat"])]
        bg = fr["place"](unary_union(near)).simplify(TOL[k], preserve_topology=True)
        background[k] = to_d(drop_specks(bg))
    for c in wanted:
        k = frame_of.get(c, "europe")
        # specks go from the shaded countries too: Portugal's Azores and Madeira
        # rendered as two stray blue dots in the open Atlantic
        g = drop_specks(frames[k]["place"](by_code[c]).simplify(TOL[k], preserve_topology=True))
        if g.is_empty:
            raise SystemExit("REFUSING: %s falls outside the %s frame - give it an inset "
                             "in FRAMES" % (c, k))
        shapes[c] = {"frame": k, "d": to_d(g)}

    eu = unary_union([by_code[c] for c in EU27 if c in by_code])
    eu_d = to_d(drop_specks(frames["europe"]["place"](eu).simplify(TOL["europe"], preserve_topology=True)))

    points = {}
    for key, meta in S.SOURCES.items():
        if "map_point" not in meta:
            continue
        fr = frames["europe"]
        x, y = fr["f"](*meta["map_point"])
        x, y = x * fr["s"] + fr["ox"], y * fr["s"] + fr["oy"]
        rx, ry, rw, rh = rects["europe"]
        if not (rx <= x <= rx + rw and ry <= y <= ry + rh):
            raise SystemExit("REFUSING: %s's map_point is outside the Europe frame" % key)
        points[key] = [round(x, 1), round(y, 1)]

    # lon/lat copies for the published /catalogues.geo.json - simplified in
    # degrees, 3 decimals (~100 m), enough for any page-scale map.
    def ll(g):
        g = g.simplify(0.03, preserve_topology=True)
        return json.loads(json.dumps(mapping(g)), parse_float=lambda v: round(float(v), 3))
    lonlat = {c: ll(by_code[c]) for c in wanted}
    lonlat["EU"] = ll(eu)

    out = {
        "_about": "Boundaries for the /sources.html map and /catalogues.geo.json. Written "
                  "by geo/build_geo.py (manual, never part of run.sh); the weekly build "
                  "only joins counts onto it. Read `codes`, `trimmed` and `source_sha256` "
                  "in a diff - the path data is not reviewable.",
        "source": "Natural Earth 1:50m Admin 0 - Countries",
        "source_url": NE_URL,
        "source_sha256": sha,
        "licence": "public domain (Natural Earth)",
        "projection": "spherical Lambert azimuthal equal-area, one per frame",
        "generated_by": "geo/build_geo.py",
        "generated": datetime.date.today().isoformat(),
        "codes": wanted,
        "off_map": sorted(OFF_MAP),
        "eu27": EU27,
        "trimmed": trimmed,
        "viewbox": [0, 0, round(left + MAIN_W, 1), round(height, 1)],
        "frames": {k: rects[k] for k in FRAMES},
        "background": background,
        "shapes": shapes,
        "eu": eu_d,
        "points": points,
        "lonlat": lonlat,
    }
    # One line per top-level key: the small reviewable fields (codes, trimmed,
    # sha256, generated) read cleanly in a diff; the geometry stays one line each
    # instead of one line per coordinate.
    with open(OUT, "w") as fh:
        fh.write("{\n" + ",\n".join(
            json.dumps(k) + ": " + json.dumps(out[k], sort_keys=True, separators=(",", ":"))
            for k in sorted(out)) + "\n}\n")
    size = os.path.getsize(OUT)
    print("wrote %s (%.0f KB): %d countries %s, %d city points, trimmed %s"
          % (OUT, size / 1024, len(wanted), wanted, len(points),
             [(t["code"], t["parts_dropped"]) for t in trimmed]))
    print("source sha256", sha)
    ospo_frames(by_code, sha)


# ---- the /ospos map (build_ospos.py): North America and Europe side by side.
# Points are placed at BUILD time from ospos/locations.json, so this file stores
# each frame's projection (centre, scale s, offset ox/oy) beside its land - the
# weekly build then needs no shapely. `probe` pins the projection: build_ospos's
# own copy of laea() must put these lon/lat at these x/y (test_built_pages 12f).
OSPO_OUT = os.path.join(HERE, "geo", "ospo_frames.json")
OSPO_FRAMES = [
    ("northam", {"centre": (-96.0, 39.0), "box": (-125.0, 24.0, -66.5, 50.0)}, 500.0),
    ("europe", {"centre": (10.0, 50.0), "box": (-11.0, 35.5, 25.0, 59.0)}, 440.0),
]


def ospo_frames(by_code, sha):
    gap, x, frames, heights = 18.0, 0.0, {}, []
    for k, fr, w in OSPO_FRAMES:
        f, bx, s = fit(fr, w)
        h = (bx[3] - bx[1]) * s
        frames[k] = {"centre": list(fr["centre"]), "s": s, "ox": x - bx[0] * s, "oy": -bx[1] * s,
                     "rect": [round(x, 1), 0.0, w, round(h, 1)], "_f": f}
        heights.append(h)
        x += w + gap
    H = max(heights)
    for k, fr in frames.items():                      # centre each frame vertically
        dy = (H - fr["rect"][3]) / 2
        fr["oy"] += dy
        fr["rect"][1] = round(dy, 1)
    out = {"_about": "Land outlines and projections for the /ospos map. Written by "
                     "geo/build_geo.py beside catalogue_shapes.json; read by build_ospos.py.",
           "source_sha256": sha, "viewbox": [0, 0, round(x - gap, 1), round(H, 1)], "frames": {}}
    for (k, fr_def, _w), fr in zip(OSPO_FRAMES, frames.values()):
        rx, ry, rw, rh = fr["rect"]
        clip = box(rx, ry, rx + rw, ry + rh)
        lonlat = box(*fr_def["box"]).buffer(20)
        near = unary_union([g for g in by_code.values() if g.intersects(lonlat)])
        f, s_, ox, oy = fr["_f"], fr["s"], fr["ox"], fr["oy"]
        pg = proj_geom(near.intersection(box(fr_def["box"][0] - 15, fr_def["box"][1] - 10,
                                             fr_def["box"][2] + 15, fr_def["box"][3] + 10)), f)
        pg = transform(lambda xs, ys, zs=None: (tuple(v * s_ + ox for v in xs),
                                               tuple(v * s_ + oy for v in ys)), pg)
        land = polys_only(make_valid(pg).intersection(clip)).simplify(0.8, preserve_topology=True)
        parts = [p for p in getattr(land, "geoms", [land]) if isinstance(p, Polygon) and p.area >= 2.0]
        lon0, lat0 = (fr_def["box"][0] + fr_def["box"][2]) / 2, (fr_def["box"][1] + fr_def["box"][3]) / 2
        px, py = f(lon0, lat0)
        out["frames"][k] = {"centre": fr["centre"], "s": s_, "ox": ox, "oy": oy, "rect": fr["rect"],
                            "land": to_d(MultiPolygon(parts)),
                            "probe": {"lon": lon0, "lat": lat0,
                                      "x": round(px * s_ + ox, 3), "y": round(py * s_ + oy, 3)}}
    with open(OSPO_OUT, "w") as fh:
        fh.write("{\n" + ",\n".join(json.dumps(k) + ": " + json.dumps(out[k], sort_keys=True, separators=(",", ":"))
                                     for k in sorted(out)) + "\n}\n")
    print("wrote %s (%.0f KB), frames %s" % (OSPO_OUT, os.path.getsize(OSPO_OUT) / 1024,
                                             {k: v["rect"] for k, v in out["frames"].items()}))


if __name__ == "__main__":
    main()
