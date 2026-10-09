#!/usr/bin/env python3
"""Smoke test for the BUILT pages, and the contracts that span two of them.

    bash run.sh          # or at least build_ui + build_site + the page builders
    python3 test_built_pages.py

Why this file exists: on 2026-09-21 a More filters drawer shipped rendering 253px
tall with its `hidden` attribute correctly set, because `.drawer{display:flex}`
outranks the UA stylesheet's `[hidden]{display:none}`. The verification that
passed had asserted `el.hidden === true` — the property, not the rendering. At
that point the repo had 163 tests and **not one of them touched built output**,
which is precisely where the bug was.

The checks below are the ones that were run by hand that day. A check that exists
only in someone's session is a check that does not exist.

⚠ Four of these are CROSS-PAGE contracts, and all fail silently and invisibly:

  * `/sources.html` links to `/?src=<label>`, and the catalog validates that value
    against its own <option> list and IGNORES an unknown one. So renaming a label
    in sources.py does not error — all 17 "See catalog entries" links just stop
    filtering, which reads as "this catalogue contributed no entries", the one
    claim that page exists to disprove.
  * `pslug()` exists TWICE — Python in build_products.py, JavaScript in
    _ui_template.py — because importing across those modules would execute a
    module body. The catalog computes product anchors client-side, so if the two
    drift, every "Replaces X" link lands on an anchor that is not there. Checked
    at the OUTCOME level (do the links land?) rather than by comparing the two
    functions — see the note on check 5 for why the direct comparison was written
    and then deleted.
  * The "Get involved" block on / and /sources.html comes from one function,
    theme.submit_block(). It used to be two copies, and a fix to one left the
    other stale; check 10 fails if the two renderings differ again.
  * Variants are linked in two builders - by DATA index on the page, by id in
    entries.json - and inherited mappings must stay out of by-product.json.
    Check 11.

Not wired into run.sh, same as the other five suites: a test that can fail the
weekly publish is a test someone switches off, and run.sh already gates its deploy
on every build step exiting 0.
"""
import collections
import html
import json
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "site")

# Since 2026-10-07: index.html is the HOME page (/), software.html the catalog
# (/software); catalogs = the old sources page, docs = the old api page. The
# keys are site/ file names; site-worker.js serves each at its clean path.
ROUTE_OF = {"index.html": "/", "software.html": "/software", "catalogs.html": "/catalogs",
            "ospos.html": "/ospos", "docs.html": "/docs", "products.html": "/products",
            "resources.html": "/resources"}
PAGES = {n: os.path.join(SITE, n) for n in ROUTE_OF}
# Catalan copies (i18n.py). Every check that loops over PAGES covers them.
PAGES.update({"ca/" + n: os.path.join(SITE, "ca", n) for n in ROUTE_OF})
PAGES["catalogue.html"] = os.path.join(HERE, "catalogue.html")
PAGES["catalogue.ca.html"] = os.path.join(HERE, "catalogue.ca.html")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def py_pslug(s):
    """The PYTHON pslug, copied from build_products.py."""
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", (s or "").lower())).strip("-")


def extract_js_array(page, var):
    m = re.search(r"var %s = (\[.*?\]);" % re.escape(var), page, re.S)
    return json.loads(m.group(1)) if m else None


def main():
    missing = [n for n, p in PAGES.items() if not os.path.exists(p)]
    if missing:
        print("SKIP  not built: %s\n      run `bash run.sh` (or the page builders) first."
              % ", ".join(missing))
        return 0

    pages = {n: read(p) for n, p in PAGES.items()}
    failed, ran = [], []

    def check(label, got, want):
        ran.append(label)          # counted, never hard-coded: a stale total reports a phantom pass
        if got != want:
            failed.append("%s: expected %r, got %r" % (label, want, got))

    # ---- 1. no unsubstituted placeholders.
    # theme.py and _ui_template.py hold markup as PLAIN strings with
    # __TOKEN__ substituted at the end. The builders assert none survive, but only
    # for the pages they write; this covers every page at once.
    for name, page in pages.items():
        left = sorted(set(re.findall(r"__[A-Z][A-Z0-9_]*__", page)))
        check("%s has no unsubstituted placeholder" % name, left, [])

    # ---- 2. catalogue.html is pure ASCII.
    # Artifacts cannot set <meta charset>, so depending on the host to declare
    # UTF-8 once rendered "open source â€” aggregated".
    for name in ("catalogue.html", "catalogue.ca.html"):
        raw = open(PAGES[name], "rb").read()
        check("%s non-ASCII byte count" % name, sum(1 for b in raw if b > 127), 0)

    # ---- 3. the [hidden] reset, on every page whose JS toggles el.hidden.
    # This is the drawer bug. `hidden` hides via the UA stylesheet, which any
    # author `display:` rule outranks; the reset is what makes el.hidden mean
    # hidden. Asserted as PRESENT because its absence is invisible — the attribute
    # is set, the property reads true, and the element renders anyway.
    for name in ("software.html", "products.html", "resources.html", "catalogs.html", "ospos.html"):
        page = pages[name]
        if ".hidden" in page or "hidden>" in page:
            check("%s carries [hidden]{display:none!important}" % name,
                  bool(re.search(r"\[hidden\]\s*\{[^}]*display\s*:\s*none\s*!important", page)),
                  True)

    # ---- 4. CROSS-PAGE: every ?src= link resolves to a real <option>.
    src_links = [urllib.parse.unquote(m)
                 for m in re.findall(r'href="/software\?src=([^"]*)"', pages["catalogs.html"])]
    options = set(html.unescape(m)
                  for m in re.findall(r'<option value="([^"]*)">', pages["software.html"]))
    check("catalogs.html emits a /software?src= link per harvested catalogue",
          len(src_links) > 0, True)
    check("every ?src= value matches a catalog <option>",
          sorted(l for l in src_links if l not in options), [])

    # ---- 5. CROSS-PAGE: every product the catalog links to has an anchor.
    #
    # ⚠ This replaced a direct "do the two pslug implementations agree?" check,
    # which was written, tested by sabotage, and DELETED because it could only
    # ever pass. Both implementations run `[^a-z0-9]+ -> -` and then collapse
    # `-+ -> -`, and that pipeline absorbs every plausible one-sided edit: dropping
    # the `+` from one character class, or the difference between Python's
    # `.strip("-")` and the JS single-hyphen strip, produce identical output for
    # every input tried (`--Foo--`, `C++ / C#`, `.NET`, `a---b`, `Ärger`, `...`).
    # No input distinguishes them, so the comparison was untestable decoration.
    #
    # This check tests the OUTCOME instead: the links have to land. It does not
    # care why two slugs might diverge, which is what makes it robust to causes
    # nobody thought of. It fails on a sabotaged anchor (verified).
    # The catalog builds `products.html#p-<pslug(name)>` in JS at render time, so
    # this cannot be checked by grepping the static HTML — it has to be recomputed
    # from the data the page ships.
    anchors = set(re.findall(r'id="(p-[a-z0-9-]+)"', pages["products.html"]))
    data = extract_js_array(pages["software.html"], "DATA")
    check("catalog page ships its DATA array", data is not None, True)
    if data:
        linked = sorted({p for r in data for p in (r.get("rp") or []) if p})
        check("catalog links to products", len(linked) > 0, True)
        orphans = sorted(p for p in linked if "p-" + py_pslug(p) not in anchors)
        check("every product the catalog links to has an anchor on products.html",
              orphans, [])

    # ---- 7. by-country files exist and agree with meta.json.
    meta = json.load(open(os.path.join(SITE, "meta.json")))
    codes = [c["code"] for c in meta["countries"]]
    check("meta.json lists countries", len(codes) > 0, True)
    absent, mismatched = [], []
    for c in codes:
        p = os.path.join(SITE, "by-country", "%s.json" % c)
        if not os.path.exists(p):
            absent.append(c)
            continue
        d = json.load(open(p))
        declared = next(x["count"] for x in meta["countries"] if x["code"] == c)
        if d.get("count") != declared or len(d.get("entries") or []) != declared:
            mismatched.append("%s: meta %s, file count %s, entries %s"
                              % (c, declared, d.get("count"), len(d.get("entries") or [])))
    check("every country in meta.json has a by-country file", absent, [])
    check("every by-country file agrees with meta.json", mismatched, [])

    # ---- 8. the caveat that must travel WITH the data, not just in the docs.
    # /by-country/<CC>.json is the figure most likely to be misread by the audience
    # most likely to want it, so the note ships in the file itself.
    de = json.load(open(os.path.join(SITE, "by-country", "DE.json")))
    check("by-country files carry the catalogue-vs-tier-of-government caveat",
          "not the tier of government" in (de.get("note") or ""), True)

    # ---- 9. meta.json's literal file paths resolve on disk.
    for key, path in (meta.get("files") or {}).items():
        if "<" in path:
            continue                      # a template, e.g. /by-country/<CC>.json
        check("meta.json files[%s] -> %s exists" % (key, path),
              os.path.exists(os.path.join(SITE, path.lstrip("/"))), True)

    # ---- 10. CROSS-PAGE: one "Get involved" block, rendered the same on both pages.
    # It was written out twice, in _ui_template.py and build_sources.py, and a fix
    # to one left the other stale; it now comes from theme.submit_block(). Digits
    # are masked because each page passes its own catalogue count. The home page
    # must carry exactly one #submit target (its lede's "Submit it here" links
    # to it; the top bar's "Submit a catalog" button became Docs on 2026-10-07).
    def submit(page):
        m = re.search(r'<div class="submit" id="submit">.*?</div>', page, re.S)
        return re.sub(r"\d+", "N", m.group(0)) if m else None
    check("index.html carries exactly one #submit target",
          pages["index.html"].count('id="submit"'), 1)
    check("the Get involved block is identical on / and /catalogs",
          submit(pages["catalogs.html"]) is not None
          and submit(pages["index.html"]) == submit(pages["catalogs.html"]), True)

    # ---- 11. CROSS-PAGE: variants agree between the page and /entries.json.
    # The page folds a variant under its core by DATA index (vo/vs); entries.json
    # links them by id. Both derive from variant_of in catalog.json, in two
    # builders, so they can drift. And an inherited replaces row must never reach
    # by-product.json - the buyer should see the core once, not every deployment.
    back = all(i in (data[r["vo"]].get("vs") or []) and not data[r["vo"]].get("ex")
               for i, r in enumerate(data) if r.get("vo") is not None) if data else False
    check("every page variant points at a core that lists it back", back, True)
    ents = json.load(open(os.path.join(SITE, "entries.json")))
    page_pairs = sorted((r["n"], data[r["vo"]]["n"]) for r in data if r.get("vo") is not None)
    json_pairs = sorted((e["name"], e["variant_of"]["name"]) for e in ents
                        if e.get("variant_of") and not e.get("excluded"))
    check("page and entries.json agree on variant links", page_pairs, json_pairs)
    bp = json.load(open(os.path.join(SITE, "by-product.json")))
    inh = {(m["product"], e["name"]) for e in ents for m in (e.get("replaces") or [])
           if m.get("inherited_from")}
    leaked = sorted(p + " <- " + x["name"] for p, rows in bp.items() for x in rows
                    if (p, x["name"]) in inh)
    check("no inherited replaces row reaches by-product.json", leaked, [])

    # ---- 12. LANGUAGE COPIES (i18n.py). Each failure here is silent in a browser
    # check of the English site, which is where anyone would look first.
    import subprocess
    sys.path.insert(0, HERE)
    import i18n
    for en_name, route in ROUTE_OF.items():
        for lang in i18n.LANGS:
            name = en_name if lang == "en" else "%s/%s" % (lang, en_name)
            page = pages[name]
            check("%s declares lang=%s" % (name, lang),
                  bool(re.search(r'<html lang="%s"' % lang, page)), True)
            check("%s has no unresolved translation marker" % name,
                  "\u27ea" in page or "\u27eb" in page, False)
            want = sorted('hreflang="%s" href="%s%s"' % (l, i18n.BASE, i18n.path_for(l, route))
                          for l in i18n.LANGS)
            got = sorted(set(re.findall(r'hreflang="(?!x-default)[a-z]+" href="[^"]+"', page)))
            check("%s carries reciprocal hreflang links" % name, got, want)
            # every page link outside the switcher/alternates stays in this language
            stray = []
            for tag in re.findall(r"<(?:a|link)\b[^>]*>", page):
                if "hreflang=" in tag:
                    continue
                for href in re.findall(r'\shref="(/[^"]*)"', tag):
                    cut = min([i for i in (href.find("?"), href.find("#")) if i >= 0] or [len(href)])
                    if (href[:cut] or "/") in i18n.ROUTES and lang != "en":
                        stray.append(href)
                    if lang == "en" and href.startswith("/ca/"):
                        stray.append(href)
            check("%s page links stay in %s" % (name, lang), stray[:3], [])
    # the Catalan catalog's ?src= links (from /ca/catalogs) must resolve too
    ca_src = [urllib.parse.unquote(m) for m in
              re.findall(r'href="/ca/software\?src=([^"]*)"', pages["ca/catalogs.html"])]
    ca_opts = set(html.unescape(m) for m in
                  re.findall(r'<option value="([^"]*)">', pages["ca/software.html"]))
    check("every /ca/software?src= value matches a Catalan catalog <option>",
          (len(ca_src) > 0, sorted(l for l in ca_src if l not in ca_opts)), (True, []))
    # The catalog's inline script must PARSE in every language. A Catalan
    # apostrophe unescaped inside a single-quoted JS string would break the whole
    # page while every static check above still passed.
    for name in ("software.html", "ca/software.html", "index.html", "ca/index.html",
                 "resources.html", "ca/resources.html", "ospos.html", "ca/ospos.html"):
        js = "\n".join(re.findall(r"<script>(.*?)</script>", pages[name], re.S))
        tmp = os.path.join(HERE, "out", "_check_%s.js" % name.replace("/", "_"))
        os.makedirs(os.path.dirname(tmp), exist_ok=True)
        open(tmp, "w").write(js)
        p = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
        os.remove(tmp)
        check("%s inline script parses" % name, p.returncode, 0)
    # every translatable string resolved on the last build
    try:
        miss = json.load(open(os.path.join(HERE, "out", "i18n_missing.json")))
    except Exception:
        miss = {}
    check("no page string is missing a translation", sorted(miss), [])
    check("i18n/ca.json loads (placeholders validated)", bool(i18n.table("ca")["strings"]), True)

    # ---- 12b. SHAREABLE URL: every key the catalog WRITES to the address bar is
    # one it READS back at load. A written-but-unread key makes a shared link that
    # silently fails to restore the view it promises.
    idx = pages["software.html"]
    m = re.search(r"function writeURL\(\) \{(.*?)\n\}", idx, re.S)
    written = set()
    if m:
        body = m.group(1)
        written |= set(re.findall(r"P\.(?:set|append)\('(\w+)'", body))
        for grp in re.findall(r"\[((?:'\w+',?\s*)+)\]\.forEach", body):
            written |= set(re.findall(r"'(\w+)'", grp))
    rd = re.search(r"new URLSearchParams\(location\.search\)(.*?)\}\)\(\);", idx, re.S)
    readback = set()
    if rd:
        readback |= set(re.findall(r"P\.get(?:All)?\('(\w+)'\)", rd.group(1)))
        for grp in re.findall(r"\[((?:'\w+',?\s*)+)\]\.forEach", rd.group(1)):
            readback |= set(re.findall(r"'(\w+)'", grp))
    check("catalog writes its view to the URL (writeURL found, keys parsed)",
          len(written) >= 10, True)
    check("every URL key written is read back at load", sorted(written - readback), [])
    check("reset() writes the URL", "render(); writeURL(); }" in idx, True)

    # ---- 12d. STAT ROWS: each carries the class for its tile count. The shared
    # rule never leaves an empty (grey) cell, but only .six / .five hold the
    # measured breakpoints; a changed count without its class wraps 4+1 again.
    WANT = {6: "six", 5: "five"}
    for name in ("software.html", "ca/software.html", "catalogs.html", "ca/catalogs.html"):
        m = re.search(r'<div class="stats([^"]*)">(.*?)\n\s*</div>', pages[name], re.S)
        n = m.group(2).count('class="stat"') if m else 0
        check("%s: stats row class matches its %d tiles" % (name, n),
              WANT.get(n) in (m.group(1).split() if m else []), True)

    # ---- 12c. THE CATALOGUE MAP (sources_map.py). Every catalogue in sources.py
    # is on the map or named beside it; its links resolve; nothing is fetched from
    # a third party; /catalogues.geo.json agrees with the page.
    sys.path.insert(0, HERE)
    import sources as S
    sp = pages["catalogs.html"]
    # ONLY the map panel: the section around it also holds the cards, whose own
    # ?src= links would satisfy every check below with no map at all.
    MAPRE = r'<div id="cview-map" hidden>(.*?)</div>\s*</section>'
    mm = re.search(MAPRE, sp, re.S)
    msec = mm.group(1) if mm else ""
    check("catalogs.html has the map view", bool(mm) and "cmap-svg" in msec, True)
    shaded = set(re.findall(r'<a href="/software\?cc=([A-Z]{2})"', msec))
    src_on_map = set(urllib.parse.unquote(v) for v in re.findall(r'href="/software\?src=([^"]*)"', msec))
    unplaced = sorted(k for k, m in S.SOURCES.items()
                      if m["country"] not in shaded and m["label"] not in src_on_map)
    check("every catalogue is shaded, a city dot, or named beside the map", unplaced, [])
    check("every city catalogue (map_point) has its dot",
          sorted(m["label"] for m in S.SOURCES.values()
                 if "map_point" in m and m["label"] not in src_on_map), [])
    ccf = set(f[0] for f in (extract_js_array(pages["software.html"], "CCFACETS") or []))
    check("every map ?cc= value is a catalog country facet", sorted(shaded - ccf), [])
    check("the map loads nothing from another origin",
          re.findall(r'(?:href|src|xlink:href)="(https?://[^"]*)"',
                     re.search(r"<svg class=\"cmap-svg\".*?</svg>", msec, re.S).group(0)
                     if "cmap-svg" in msec else ""), [])
    cam = re.search(MAPRE, pages["ca/catalogs.html"], re.S)
    check("the Catalan map links to the Catalan catalog",
          bool(cam) and '"/software?cc=' not in cam.group(1) and '"/ca/software?cc=' in cam.group(1), True)
    # the Cards / Map switch: cards are the default (and all a reader without
    # JS gets), the switch is revealed by script, and the script parses.
    for name in ("catalogs.html", "ca/catalogs.html"):
        pg = pages[name]
        check("%s: cards shown and map hidden by default" % name,
              ('<div id="cview-cards">' in pg, '<div id="cview-map" hidden>' in pg), (True, True))
        check("%s: the switch starts hidden, with both buttons" % name,
              (bool(re.search(r'<div class="vtog" id="vtog"[^>]*\bhidden>', pg)),
               'id="vcards"' in pg, 'id="vmap"' in pg), (True, True, True))
        js = "\n".join(re.findall(r"<script>(.*?)</script>", pg, re.S))
        tmp = os.path.join(HERE, "out", "_check_%s.js" % name.replace("/", "_"))
        open(tmp, "w").write(js)
        p = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
        os.remove(tmp)
        check("%s inline script parses (and exists)" % name, (bool(js.strip()), p.returncode), (True, 0))
    gpath = os.path.join(SITE, "catalogues.geo.json")
    try:
        gj = json.load(open(gpath))
    except Exception as e:
        gj = {"features": [], "_error": str(e)}
    gcodes = set(f["properties"]["code"] for f in gj.get("features", [])
                 if f["properties"].get("kind") == "country")
    check("/catalogues.geo.json has a country feature per shaded country",
          sorted(gcodes ^ shaded), [])
    try:
        meta_at = json.load(open(os.path.join(SITE, "meta.json"))).get("generated_at")
    except Exception:
        meta_at = "unreadable"
    check("/catalogues.geo.json is stamped with meta.json's generated_at (UNNYC requires it)",
          gj.get("generated_at"), meta_at)
    check("/catalogues.geo.json never carries a per-country total",
          [f["properties"]["code"] for f in gj.get("features", [])
           if set(f["properties"]) & {"entries", "total", "total_entries"}], [])

    # ---- 12e. THE PAGE SPLIT (2026-10-07). Home is light and hands its search to
    # /software; every page carries the same five nav links; Resources renders
    # every record of its file; the old page files are gone from site/.
    home = pages["index.html"]
    check("home carries no DATA (the entry list lives on /software only)",
          ("var DATA" in home, len(home) < 300 * 1024), (False, True))
    for name, sw in (("index.html", "/software"), ("ca/index.html", "/ca/software")):
        f = re.search(r'<form class="searchbar" action="([^"]+)" method="get"[^>]*>(.*?)</form>',
                      pages[name], re.S)
        check("%s search is a GET form to %s with a q field" % (name, sw),
              (f.group(1) if f else None, bool(f and 'name="q"' in f.group(2))), (sw, True))
    check("home 'See all, newest first' opens /software sorted newest",
          'href="/software?sort=recent"' in home, True)
    # ---- the home page's section cards and catalogue cards (since 2026-10-07).
    # Each figure must equal what its own page publishes - they are read from the
    # same inputs in a different builder, which is how two numbers drift apart.
    _meta = json.load(open(os.path.join(SITE, "meta.json")))
    _srcj = json.load(open(os.path.join(SITE, "sources.json")))
    _osj = json.load(open(os.path.join(SITE, "ospos.json")))
    _rsj = json.load(open(os.path.join(SITE, "resources.json")))
    num = lambda v: int(re.sub(r"[^\d]", "", v))
    for name, lang in (("index.html", "en"), ("ca/index.html", "ca")):
        pg = pages[name]
        doors = [(h, num(n)) for h, n in
                 re.findall(r'<a class="hm-door" href="([^"]+)">.*?<b>([^<]+)</b>', pg, re.S)]
        check("%s: four section cards, each with the figure its page publishes" % name, doors,
              [(i18n.path_for(lang, "/software"), _meta["counts"]["entries"]),
               (i18n.path_for(lang, "/catalogs"), len(_srcj["ingested"])),
               (i18n.path_for(lang, "/ospos"), len(_osj["ospos"])),
               (i18n.path_for(lang, "/resources"),
                len(_rsj["resources"]) + len(_rsj["added_by_govoss"]["resources"]))])
        ct = re.search(r'<ul class="rtrack" id="ctrack">(.*?)</ul>', pg, re.S)
        cards = [(h, lbl or lbl2, n) for h, lbl, lbl2, n in re.findall(
            r'<li class="rcard"><div class="rt">(?:<a href="([^"]+)">([^<]*)</a>|([^<]*))</div>'
            r'.*?<div class="hm-ce"><b>([^<]+)</b>', ct.group(1) if ct else "", re.S)]
        want = {html.unescape(i["label"]): i["entries"] for i in _srcj["ingested"]}
        got = {html.unescape(lbl): num(n) for _h, lbl, n in cards}
        check("%s: one card per catalogue, with the count /catalogs shows" % name, got, want)
        badlink = [lbl for h, lbl, n in cards
                   if (num(n) > 0) != bool(h) or (h and urllib.parse.unquote(h.split("src=", 1)[-1])
                                                    != html.unescape(lbl))]
        check("%s: each catalogue card opens /software filtered to it (none for an empty one)" % name,
              badlink, [])
        # the catalogues scroll like the software strip: own arrows, and no icon
        # without a size of its own (an unsized one filled a whole card)
        check("%s: catalogue strip has its scroll arrows, and the script drives both strips" % name,
              ('id="cprev"' in pg and 'id="cnext"' in pg, "strip('ctrack', 'cprev', 'cnext')" in pg,
               "strip('rtrack', 'rprev', 'rnext')" in pg), (True, True, True))
        check("%s: every inline icon carries its own width and height" % name,
              [m for m in re.findall(r'<svg aria-hidden="true"[^>]*>', pg)
               if not re.search(r'\bwidth="\d+" height="\d+"', m)], [])
        check("%s: the strip says what it is: recently added open source software" % name,
              bool(re.search(r'<section class="recent" id="recent" hidden>\s*<div class="rhead">\s*<h2>(Recently '
                             r'added open source software|Programari de codi obert afegit recentment)</h2>', pg)), True)
    # Docs is the top-right button, not a nav item; Home is the wordmark, not a nav
    # item (owner, 2026-10-07 both)
    NAV = [("/software", "software"), ("/catalogs", "catalogs"),
           ("/ospos", "ospos"), ("/resources", "resources")]
    for name in ROUTE_OF:
        for lang in i18n.LANGS:
            pname = name if lang == "en" else "%s/%s" % (lang, name)
            nav = re.search(r'<nav class="nav">(.*?)</nav>', pages[pname], re.S)
            hrefs = re.findall(r'href="([^"]+)"', nav.group(1)) if nav else []
            check("%s nav: the four links, in order" % pname,
                  hrefs, [i18n.path_for(lang, r) for r, _ in NAV])
            cur = re.findall(r'href="([^"]+)" aria-current="page"', nav.group(1)) if nav else []
            want_cur = ([i18n.path_for(lang, ROUTE_OF[name])]
                        if name not in ("products.html", "docs.html", "index.html") else [])
            check("%s nav marks its own page current" % pname, cur, want_cur)
            brand = re.search(r'<a class="brand" href="([^"]+)"([^>]*)>', pages[pname])
            check("%s wordmark links home, current only on home" % pname,
                  (brand.group(1) if brand else None, bool(brand and "aria-current" in brand.group(2))),
                  (i18n.path_for(lang, "/"), name == "index.html"))
            btn = re.search(r'<div class="t-r">.*?<a class="btn btn-primary" href="([^"]+)"([^>]*)>',
                            pages[pname], re.S)
            check("%s top-right button is Docs (current only on /docs)" % pname,
                  (btn.group(1) if btn else None, bool(btn and "aria-current" in btn.group(2))),
                  (i18n.path_for(lang, "/docs"), name == "docs.html"))
    # ---- 12g. ONE PAGE HEADER (owner, 2026-10-07). Every page but home uses
    # theme.page_header(): one .ph band, the nav name as the ONLY h1, a lede, and
    # a meta line whose Data links resolve. Home keeps its own hero. /catalogs and
    # /docs had an h2 and no h1 at all; four title styles and four heights before.
    _ca = json.load(open(os.path.join(HERE, "i18n", "ca.json")))["strings"]
    TITLE = {"software.html": "Software", "catalogs.html": "Catalogs", "ospos.html": "OSPOs",
             "resources.html": "Resources", "docs.html": "Docs", "products.html": "Products"}
    for name, en in TITLE.items():
        for lang in i18n.LANGS:
            pname = name if lang == "en" else "%s/%s" % (lang, name)
            pg = pages[pname]
            want = en if lang == "en" else _ca.get(en, en)
            hd = re.search(r'<div class="ph tex"><div class="wrap">\s*<h1>(.*?)</h1>\s*'
                           r'<p class="lede">.+?</p>\s*<p class="ph-meta">(.*?)</p>', pg, re.S)
            data = re.findall(r'<a class="mono" href="(/[^"]+\.json)">', hd.group(2)) if hd else []
            check("%s: the shared header, its h1 the nav name, the only h1, no old hero" % pname,
                  (html.unescape(hd.group(1)) if hd else None, len(re.findall(r"<h1\b", pg)),
                   pg.count('<div class="ph tex">'), 'class="hero' in pg),
                  (want, 1, 1, False))
            # no figures in a header lede (owner, 2026-10-07): a number there is one
            # more thing to keep updated; the counts live in cards, tiles and lists
            led = re.search(r'<div class="ph tex">.*?<p class="lede">(.*?)</p>', pg, re.S)
            # ONE line at 1024px and up (owner, 2026-10-08). Measured: ~113 characters
            # of the lede font fit the 929px column at 1024; 100 keeps a margin for the
            # widest words. A static stand-in for a measurement - re-measure in the
            # browser when the font or the header padding changes.
            ltext = html.unescape(re.sub(r"<[^>]+>", "", led.group(1))).strip() if led else ""
            check("%s: the header lede fits one line at 1024px (<= 100 characters)" % pname,
                  len(ltext) <= 100, True)
            check("%s: the header lede carries no numbers" % pname,
                  re.findall(r"\d[\d,.]*", re.sub(r"<[^>]+>|&#?\w+;", "", led.group(1))) if led else ["no lede"],
                  [])
            check("%s: the header's meta line links the page's data, and each file exists" % pname,
                  (len(data) > 0, [d for d in data if not os.path.exists(os.path.join(SITE, d.lstrip("/")))]),
                  (True, []))
    for pname in ("software.html", "ca/software.html"):
        pg = pages[pname]
        ph, tools = pg.find('<div class="ph tex">'), pg.find('<div class="ph-tools">')
        t = re.search(r'<div class="ph-tools">\s*<div class="searchbar">.*?</div>\s*'
                      r'(?:<!--.*?-->\s*)?<p class="apinote">', pg, re.S)
        check("%s: search sits in the tools band right under the header, the agent note directly "
              "under it" % pname, (0 < ph < tools, bool(t)), (True, True))
    for pname in ("index.html", "ca/index.html"):
        check("%s keeps its own hero and one h1" % pname,
              ('<div class="hero tex">' in pages[pname], len(re.findall(r"<h1\b", pages[pname]))), (True, 1))
    rfile = json.load(open(os.path.join(HERE, "resources", "ospo-resources.json")))
    # govoss's own additions sit in their own file, every record marked, and the page
    # says so on each card and under the compilation's credit (never credited to UN+NYC)
    radd = json.load(open(os.path.join(HERE, "resources", "govoss-additions.json")))
    for name in ("resources.html", "ca/resources.html"):
        ids = re.findall(r'<li class="res" id="([^"]+)"', pages[name])
        check("%s renders every resource in the file, plus govoss's additions" % name,
              sorted(ids), sorted(r["id"] for r in rfile["resources"] + radd["resources"]))
        addcards = [body for i, body in re.findall(r'<li class="res" id="([^"]+)"(.*?)</li>', pages[name], re.S)
                    if i in {r["id"] for r in radd["resources"]}]
        check("%s marks each govoss addition on its card, and counts them apart" % name,
              (all("Added by govoss" in b for b in addcards),
               bool(re.search(r'<p class="rcred">%d (more added by govoss|m&#233;s afegits per govoss)'
                              % len(radd["resources"]), pages[name]))), (True, True))
    check("govoss's additions are all marked added_by govoss, with ids the compilation does not use",
          ([r.get("added_by") for r in radd["resources"]].count("govoss") == len(radd["resources"]),
           sorted({r["id"] for r in radd["resources"]} & {r["id"] for r in rfile["resources"]})),
          (True, []))
    # "Check a class name is free before using it": the Resources page's own CSS
    # once reused .rhead (the Recently added header, a space-between flex row) and
    # spread every card's tags across its width.
    import importlib.util as _iu
    def _mod(path, name):
        sp = _iu.spec_from_file_location(name, path); m = _iu.module_from_spec(sp)
        sp.loader.exec_module(m); return m
    _T = _mod(os.path.join(HERE, "_ui_template.py"), "_ui_template_t")
    _th = _mod(os.path.join(HERE, "theme.py"), "theme_t")
    shared_cls = set(re.findall(r"\.([a-zA-Z][\w-]*)", _T.PAGE_CSS + _th.CSS))
    for _b in ("build_resources.py", "build_ospos.py"):
        _rsrc = read(os.path.join(HERE, _b))
        _rcss = _rsrc[_rsrc.index('PAGE_CSS = """'):_rsrc.index('\nBODY = ')]
        check("%s CSS defines no class the shared styles already use" % _b,
              sorted(set(re.findall(r"\.([a-zA-Z][\w-]*)", _rcss)) & shared_cls), [])
    try:
        rj = json.load(open(os.path.join(SITE, "resources.json")))
    except Exception:
        rj = {}
    check("/resources.json publishes every resource, with govoss's additions apart",
          (len(rj.get("resources") or []), rj.get("added_by_govoss")),
          (len(rfile["resources"]), radd))
    check("the pre-2026-10-07 page files are gone from site/",
          [n for n in ("sources.html", "api.html", "ca/sources.html", "ca/api.html")
           if os.path.exists(os.path.join(SITE, n))], [])

    # ---- 12f. /ospos (build_ospos.py, from cache/ospos.json). Every fetched office
    # is a card and either a map dot or named as not placed; types are only the
    # two the filter offers; every Resources link lands on a real case with the
    # count it claims; build_ospos's projection agrees with build_geo's probes.
    od = json.load(open(os.path.join(HERE, "cache", "ospos.json")))["ospos"]
    rcases = collections.Counter(r["case"] for r in rfile["resources"])
    for name in ("ospos.html", "ca/ospos.html"):
        pg = pages[name]
        ids = re.findall(r'<li class="ocard" id="([^"]+)" data-type="([^"]+)"', pg)
        check("%s renders every fetched office" % name, sorted(i for i, _ in ids), sorted(r["id"] for r in od))
        check("%s types are only government / academic / corporate" % name,
              sorted({t for _, t in ids} - {"government", "academic", "corporate"}), [])
        # corporate since 2026-10-09 (owner): a filter, a pin colour in the key, a credit
        # naming the TODO landscape, every corporate card from it, and the TODO case
        # studies linked on exactly the cards whose rows carry one
        corp = [i for i, t in ids if t == "corporate"]
        ncase = sum(1 for r in od if r.get("case_study"))
        check("%s: Corporate is a filter, in the map key, and credited to the TODO landscape" % name,
              # the BUTTON, not the attribute: every corporate card carries data-type too
              ('<button type="button" data-type="corporate"' in pg, pg.count('background:var(--corp)'),
               'href="https://landscape.todogroup.org/"' in pg,
               len(corp) == sum(1 for r in od if r["type"] == "corporate"), len(corp) > 0),
              (True, 1, True, True, True))
        check("%s: a TODO case-study link on each card that has one, and only those" % name,
              len(re.findall(r'<a href="https://todogroup\.org/resources/case-studies/[a-z-]+/"', pg)), ncase)
        # within EACH card: an unbounded search would find the next card's flag
        noflag = [i for i, body in re.findall(r'<li class="ocard" id="([^"]+)"[^>]*data-cc="[^"]+">(.*?)</li>', pg, re.S)
                  if not re.search(r'<span class="oflag" aria-hidden="true">&#\d+;', body)]
        check("%s: every office with a country shows its flag" % name, noflag, [])
        # code links: every listed one is on its card, at most CODE_SHOWN outside the
        # fold, and the fold's "+N" counts what it holds
        ncode = {r["id"]: len(r.get("code") or []) for r in od}
        badcode = []
        for i, body in re.findall(r'<li class="ocard" id="([^"]+)"[^>]*>(.*?)</li>', pg, re.S):
            fold = re.search(r'<details class="omore"><summary>\+(\d+) .*?</summary>(.*?)</details>', body, re.S)
            shown = (body[:fold.start()] + body[fold.end():]) if fold else body
            n_shown = len(re.findall(r'rel="noopener">(?:Code|Codi):', shown))
            n_fold = len(re.findall(r'rel="noopener">(?:Code|Codi):', fold.group(2))) if fold else 0
            if (n_shown + n_fold != ncode.get(i) or n_shown > 3
                    or (fold and int(fold.group(1)) != n_fold) or (n_fold == 0) != (fold is None)):
                badcode.append((i, n_shown, n_fold))
        check("%s: code links all present, at most %d shown, the rest folded and counted"
              % (name, 3), badcode, [])
        links = re.findall(r'class="ores" href="(?:/ca)?/resources\?case=([a-z]+)">(\d+)', pg)
        check("%s Resources links land on real cases with the right counts" % name,
              [(c, n) for c, n in links if rcases.get(c) != int(n)], [])
        check("%s links to Resources for at least one office" % name, len(links) > 0, True)
        cred = re.search(r'<p class="ocred">(.*?)</p>', pg, re.S)
        check("%s credits the FLOSS-PSO Network and the OSPO Alliance, its umbrella" % name,
              bool(cred and 'href="https://floss-pso.network/public-sector-ospos/"' in cred.group(1)
                   and 'href="https://ospo-alliance.org/">OSPO Alliance</a>' in cred.group(1)), True)
        # pins open a popup of their place's cards: each names its place, the
        # popup and its labelled close button exist, and no character entity sits
        # inside a script (entities are not decoded there: a "·" once showed as &#183;)
        pins = re.findall(r'<a class="odot [^"]+" href="#[^"]+" data-ids="[^"]+" data-place="([^"]*)"'
                          r' aria-label="[^"]+" aria-haspopup="dialog">', pg)
        check("%s: every map pin names its place and opens a popup" % name,
              (len(pins), pins.count("")), (pg.count('class="odot '), 0))
        # pins scale back up on narrow screens: each pin's shape sits in a .opin
        # group, and a max-width rule sets --pin above 1 (they were ~5px on a phone)
        check("%s: every pin is scalable, and scaled up on narrow screens" % name,
              (pg.count('<g class="opin"'), bool(re.search(
                  r'@media \(max-width:\d+px\)\{\.omap-svg\{--pin:(?!1;)\d+(\.\d+)?;\}\}', pg))),
              (pg.count('class="odot '), True))
        # two layouts of one map: side by side, and stacked for phones (each frame at
        # the full width). Same pins in both, and a phone is shown the stacked one
        lay = {c: sorted(re.findall(r'data-ids="([^"]+)"', b))
               for c, b in re.findall(r'<svg class="omap-svg (omap-wide|omap-tall)"(.*?)</svg>', pg, re.S)}
        check("%s: the side-by-side and stacked maps carry the same pins" % name,
              (sorted(lay), lay.get("omap-wide") == lay.get("omap-tall"), len(lay.get("omap-wide") or [])),
              (["omap-tall", "omap-wide"], True, pg.count('class="odot ') // 2))
        check("%s: phones get the stacked map" % name,
              bool(re.search(r'\.omap-tall\{display:none;\}\s*@media \(max-width:\d+px\)\{'
                             r'\.omap-wide\{display:none;\}\.omap-tall\{display:block;', pg)), True)
        check("%s has the pin popup with a labelled close button" % name,
              bool(re.search(r'<div class="opop" id="opop" role="dialog" aria-labelledby="opop-h" hidden>'
                             r'.*?<button type="button" class="opop-x" id="opop-x" aria-label="[^"]+">', pg, re.S)), True)
        check("%s: no character entity inside a script" % name,
              [m for s_ in re.findall(r'<script>(.*?)</script>', pg, re.S) for m in re.findall(r'&#\d+;', s_)], [])
        dotted = set(i for grp in re.findall(r'data-ids="([^"]+)"', pg) for i in grp.split())
        unplaced_note = re.search(r'<p class="onote-map">(.*?)</p>', pg, re.S)
        missing = sorted(r["id"] for r in od if r["id"] not in dotted
                         # the page is ASCII: "Itaú" is &#250; there - compare unescaped
                         and not (unplaced_note and r["name"] in html.unescape(unplaced_note.group(1))))
        check("%s: every office is a map dot or named as not placed" % name, missing, [])
    sys.path.insert(0, HERE)
    import build_ospos as _bo
    gf = json.load(open(os.path.join(HERE, "geo", "ospo_frames.json")))
    drift = []
    for k, fr in gf["frames"].items():
        x, y = _bo.laea(*fr["centre"])(fr["probe"]["lon"], fr["probe"]["lat"])
        x, y = x * fr["s"] + fr["ox"], y * fr["s"] + fr["oy"]
        if abs(x - fr["probe"]["x"]) > 0.01 or abs(y - fr["probe"]["y"]) > 0.01:
            drift.append(k)
    check("build_ospos projects exactly as build_geo did (frame probes)", drift, [])
    try:
        oj = json.load(open(os.path.join(SITE, "ospos.json")))
    except Exception:
        oj = {}
    check("/ospos.json publishes every office", len(oj.get("ospos") or []), len(od))
    # /ospos.json's consumer contract (ospo_contract.py): un.opensource.nyc reads the
    # FLOSS-PSO rows and throws on anything unexpected. The built file holds it, and
    # the strings they check verbatim are pinned here as literals, not read back.
    import ospo_contract as _oc
    check("/ospos.json keeps its consumer contract", _oc.doc_problems(oj), [])
    check("/ospos.json: govoss's own licence, exactly", oj.get("licence"),
          {"govoss_fields": "CC0 1.0, govoss (https://govoss.cat)",
           "lists": "each list's own: sources[*].licence"})
    check("/ospos.json: the FLOSS-PSO licence, exactly",
          ((oj.get("sources") or {}).get("floss-pso") or {}).get("licence"),
          "CC0 1.0 (the FLOSS-PSO Network's OSPO list)")
    check("/ospos.json documents its country codes",
          sorted(oj.get("country_codes") or {}),
          ["AR", "BR", "CN", "DE", "DK", "EL", "ES", "FI", "FR", "GB", "IE", "IN", "INT", "JP",
           "KR", "LU", "NL", "SE", "TW", "US"])
    check("/ospos.json names every country code, exactly (UNNYC's headings)",
          (oj.get("country_names"), sorted(oj.get("country_names") or {}) == sorted(oj.get("country_codes") or {})),
          ({"DE": "Germany", "DK": "Denmark", "EL": "Greece", "ES": "Spain", "FR": "France",
            "GB": "United Kingdom", "IE": "Ireland", "INT": "International", "LU": "Luxembourg",
            "NL": "Netherlands", "US": "United States", "AR": "Argentina", "BR": "Brazil",
            "CN": "China", "FI": "Finland", "IN": "India", "JP": "Japan", "KR": "South Korea",
            "SE": "Sweden", "TW": "Taiwan"}, True))
    # the failed-fetch example: the live document with ONLY the floss-pso state
    # changed, the way fetch_ospos.failed_state() writes it, and still in contract
    try:
        ex = json.load(open(os.path.join(SITE, "ospos.example-failed.json")))
    except Exception:
        ex = {}
    exf = (ex.get("sources") or {}).get("floss-pso") or {}
    livef = (oj.get("sources") or {}).get("floss-pso") or {}
    check("/ospos.example-failed.json keeps the contract", _oc.doc_problems(ex) if ex else ["missing"], [])
    check("/ospos.example-failed.json: ok false, the live copy's fetched_at/count/licence/url, "
          "a later failed_at, an error, and nothing else changed",
          (exf.get("ok"), exf.get("fetched_at"), exf.get("count"), exf.get("licence"), exf.get("url"),
           (exf.get("failed_at") or "") > (exf.get("fetched_at") or "~"), bool(exf.get("error")),
           ex.get("ospos") == oj.get("ospos"),
           {k: v for k, v in ex.items() if k not in ("sources", "example")}
           == {k: v for k, v in oj.items() if k != "sources"},
           bool(re.match(r"^NOT LIVE DATA", ex.get("example") or ""))),
          (False, livef.get("fetched_at"), livef.get("count"), livef.get("licence"), livef.get("url"),
           True, True, True, True, True))
    ab = oj.get("about") or ""
    check("/ospos.json's about documents basis (hq approximate) and ok:false (last good copy)",
          (bool(re.search(r"'seat' is the office's own city; 'hq' is its parent organisation's "
                          r"headquarters, so the point is approximate", ab)),
           bool(re.search(r"ok false means .*last good copy, fetched at fetched_at \(which is "
                          r"never moved by a failed attempt", ab))), (True, True))

    # ---- 13. HOSTING (Cloudflare Workers static assets since 2026-09-23). The
    # headers and redirects live in site/_headers and site/_redirects, copied by
    # build_site.sh. Losing either is silent in a browser: pages still render,
    # but agents lose CORS on the JSON and the paths the first agent probed
    # (/api/entries, /data.json, ...) go back to 404.
    hd = os.path.join(SITE, "_headers")
    rd = os.path.join(SITE, "_redirects")
    check("site/_headers and site/_redirects exist", (os.path.exists(hd), os.path.exists(rd)), (True, True))
    if os.path.exists(hd) and os.path.exists(rd):
        hdr = read(hd)
        check("_headers opens CORS on every JSON file",
              bool(re.search(r"^/\*\.json\s*\n(?:[ \t]+.*\n)*?[ \t]+Access-Control-Allow-Origin: \*",
                             hdr, re.M)), True)
        rules = {l.split()[0]: l.split()[1] for l in read(rd).splitlines()
                 if l.strip() and not l.startswith("#")}
        want = {"/api/entries": "/entries.json", "/api/catalog": "/entries.json",
                "/api/meta": "/meta.json", "/catalog.json": "/entries.json",
                "/data.json": "/entries.json", "/status.html": "/catalogs"}
        check("_redirects answers every path agents probe", {k: rules.get(k) for k in want}, want)
    cfg = read(os.path.join(HERE, "wrangler.site.jsonc"))
    check("wrangler.site.jsonc is pinned to the sarapis.org account",
          '"account_id": "a8e2fa072ede7a6389e8db8cad00f774"' in cfg, True)
    # www belongs to the redirect Worker ONLY: two configs claiming one hostname
    # would move it back and forth on every deploy of either.
    wcfg = read(os.path.join(HERE, "wrangler.www.jsonc"))
    check("www.govoss.cat is claimed by govoss-www alone",
          # match the ROUTE, not the text: the site config's own comment names www
          ('"pattern": "www.govoss.cat"' in cfg, '"pattern": "www.govoss.cat"' in wcfg),
          (False, True))

    for f in failed:
        print("FAIL  %s" % f)
    total = len(ran)
    print("\n%d checks run, %d failed" % (total, len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
