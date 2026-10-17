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

    # ---- 12h. "GET PROJECT UPDATES" (owner, 2026-10-14): every page's footer has the
    # signup form, home has a second one in its own section. Each posts to
    # /api/subscribe, labels its email field, says the page's language, keeps the
    # honeypot out of the tab order, announces the answer, and the one script that
    # sends them is on the page once. Ids stay unique with two forms on a page.
    bad = []
    for name, pg in pages.items():
        if name.startswith("catalogue"):
            continue
        lang = "ca" if name.startswith("ca/") else "en"
        forms = re.findall(r'<form class="signup(?: submit)?" action="/api/subscribe" method="post" aria-labelledby="([^"]+)">(.*?)</form>',
                           pg, re.S)
        want = 2 if name in ("index.html", "ca/index.html") else 1
        ok = len(forms) == want and pg.count("form.signup") == 1
        for hid, body in forms:
            em = re.search(r'<input id="([^"]+)" type="email" name="email" required', body)
            ok = ok and bool(em) and ('<label class="vh" for="%s">' % em.group(1)) in body \
                and ('id="%s"' % hid) in body and ('name="lang" value="%s"' % lang) in body \
                and bool(re.search(r'name="website"\s+tabindex="-1"', body)) \
                and '<p class="signup-msg" role="status" aria-live="polite" hidden></p>' in body
        ids = re.findall(r'\sid="([^"]+)"', pg)
        if not ok or len(ids) != len(set(ids)):
            bad.append(name)
    check("every page has the signup form (home twice), labelled, its language, honeypot, live status, unique ids",
          bad, [])
    # on home the signup and Get involved sit side by side as two cards of ONE
    # structure (owner, 2026-10-14): the same card class, an overline, an h3, a
    # primary button
    shape = lambda html_: (bool(re.match(r'\s*<p class="overline">[^<]+</p>\s*<h3[ >]', html_)),
                           'class="btn btn-primary"' in html_)
    bad = []
    for name in ("index.html", "ca/index.html"):
        m = re.search(r'<div class="hm-pair">\s*<form class="signup submit"[^>]*>(.*?)</form>\s*'
                      r'<div class="submit" id="submit">(.*?)</div>\s*</div>', pages[name], re.S)
        if not m or shape(m.group(1)) != (True, True) or shape(m.group(2)) != (True, True):
            bad.append(name)
    check("home: Project updates and Get involved are paired cards of one structure", bad, [])

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

    # ---- 12f. /ospos (build_ospos.py, from cache/ospos.json): the OSPO Atlas
    # (design handoff, 2026-10-13). Every fetched office is a card in its country's
    # group and either a map point or in "Not yet placed"; types are only the three
    # the filter offers; every Resources link lands on a real case with the count it
    # claims; no ranks, a software count; build_ospos's projection agrees with
    # build_geo's probes.
    od = json.load(open(os.path.join(HERE, "cache", "ospos.json")))["ospos"]
    rcases = collections.Counter(r["case"] for r in rfile["resources"])
    sys.path.insert(0, HERE)
    import build_ospos as _bo
    for name in ("ospos.html", "ca/ospos.html"):
        pg = pages[name]
        cards = re.findall(r'<article class="at-card ([a-z]+)" id="([^"]+)" data-type="([a-z]+)" '
                           r'data-cc="([A-Z]+)"(.*?)</article>', pg, re.S)
        check("%s renders every fetched office" % name, sorted(c[1] for c in cards), sorted(r["id"] for r in od))
        check("%s types are only government / academic / corporate, class and data-type agreeing" % name,
              (sorted({c[2] for c in cards} - {"government", "academic", "corporate"}),
               [c[1] for c in cards if c[0] != c[2]]), ([], []))
        # the sidebar restated the page header ("govoss · Atlas / Open source program
        # offices"); the shared header is the page's only title (owner, 2026-10-13)
        check("%s: no second page title in the sidebar (the shared header names the page)" % name,
              ("Atlas" in re.sub(r"<[^>]+>", " ", html.unescape(pg)),
               bool(re.search(r'<aside class="at-side"[^>]*>\s*<div class="at-shead"><div class="at-q">', pg))),
              (False, True))
        # corporate since 2026-10-09 (owner): a filter, a credit naming the TODO
        # landscape, every corporate office a card, and the TODO case studies linked
        # on exactly the cards whose rows carry one
        corp = [c[1] for c in cards if c[2] == "corporate"]
        ncase = sum(1 for r in od if r.get("case_study"))
        check("%s: Corporate is a filter and credited to the TODO landscape" % name,
              ('data-f="type" data-v="corporate"' in pg, 'href="https://landscape.todogroup.org/"' in pg,
               len(corp) == sum(1 for r in od if r["type"] == "corporate"), len(corp) > 0),
              (True, True, True, True))
        # corporate text on its tint is the darker --corp-text (5.9:1), never --corp
        # itself (4.62:1, under the audit's lowest) - the rule, not a substring of it
        lg = re.search(r'\.corporate \.at-logo\{([^}]*)\}', pg)
        check("%s: corporate initials are --corp-text on --corp-tint" % name,
              lg and sorted(re.findall(r'(?:^|;)((?:background|color):[^;]+)', lg.group(1))),
              ["background:var(--corp-tint)", "color:var(--corp-text)"])
        check("%s: a TODO case-study link on each card that has one, and only those" % name,
              len(re.findall(r'<a href="https://todogroup\.org/resources/case-studies/[a-z-]+/"', pg)), ncase)
        # every country group shows its flag (an image, or the emoji where none is
        # fetched); "Not yet placed" (ZZ) has none
        grp = re.findall(r'<section class="at-grp" data-cc="([A-Z]+)"[^>]*><div class="at-gh">(<img class="at-flag"|'
                         r'<span class="at-flag at-femoji")?', pg)
        check("%s: every country group shows a flag, Not yet placed none" % name,
              (len(grp) > 1, sorted(cc for cc, f in grp if bool(f) == (cc == "ZZ"))), (True, []))
        check("%s: every flag and logo image the page names was copied to site/" % name,
              sorted(u for u in re.findall(r'src="(/ospo-img/[^"]+)"', pg)
                     if not os.path.exists(os.path.join(SITE, u.lstrip("/")))), [])
        # code profiles (owner, 2026-10-13): the card links the FIRST; with more, a
        # "+N more" button (data-n = all of them) opens the dialog, which copies the
        # card's own hidden list - every profile, in the list's order
        bad = []
        for c in cards:
            code = next((r.get("code") or [] for r in od if r["id"] == c[1]), [])
            first = re.findall(r'<a class="at-code" href="([^"]+)"', c[4])
            more = re.search(r'<button type="button" class="at-codes-more"[^>]*data-n="(\d+)"', c[4])
            lst = re.search(r'<ul class="at-codes" hidden>(.*?)</ul>', c[4])
            got = (first, int(more.group(1)) if more else None,
                   re.findall(r'<a class="at-codel" href="([^"]+)"', lst.group(1)) if lst else None)
            want = (code[:1], len(code) if len(code) > 1 else None, code if len(code) > 1 else None)
            if [html.unescape(x) if isinstance(x, str) else x for x in got[0]] != want[0] or got[1] != want[1] or \
                    (got[2] and [html.unescape(x) for x in got[2]]) != want[2]:
                bad.append(c[1])
        check("%s: one code profile on the card, the rest behind +N, all in its dialog list" % name,
              (sum(1 for r in od if len(r.get("code") or []) > 1) > 0, bad), (True, []))
        check("%s has the code-profiles dialog with a labelled close button" % name,
              bool(re.search(r'<dialog class="at-dlg" id="at-dlg" aria-labelledby="at-dlg-h">.*?'
                             r'<button type="button" class="at-dlg-x" id="at-dlg-x" aria-label="[^"]+">', pg, re.S)), True)
        links = re.findall(r'class="at-res" href="(?:/ca)?/resources\?case=([a-z]+)">.*?</svg>(\d+)', pg)
        check("%s Resources links land on real cases with the right counts" % name,
              [(c, n) for c, n in links if rcases.get(c) != int(n)], [])
        check("%s links to Resources for at least one office" % name, len(links) > 0, True)
        cred = re.search(r'<p class="ocred">(.*?)</p>', pg, re.S)
        check("%s credits the FLOSS-PSO Network and the OSPO Alliance, its umbrella" % name,
              bool(cred and 'href="https://floss-pso.network/public-sector-ospos/"' in cred.group(1)
                   and 'href="https://ospo-alliance.org/">OSPO Alliance</a>' in cred.group(1)), True)
        # the score is the office's software in govoss (owner, 2026-10-13):
        # office_indices()'s count; the card's button says it and opens
        # /software?ospo=<id>, whose list is those SAME entries
        catj = json.load(open(os.path.join(HERE, "catalog.json")))
        want_ix = {r["id"]: _bo.office_indices(r, catj) for r in od}
        swm = re.search(r"var OSPOSW = (\{.*?\});\n", pages["ca/software.html" if name.startswith("ca/") else "software.html"])
        osw = json.loads(swm.group(1)) if swm else {}
        dm = re.search(r"var DATA = (\[.*?\]);\n", pages["ca/software.html" if name.startswith("ca/") else "software.html"])
        D = json.loads(dm.group(1)) if dm else []
        bad, scores = [], {}
        for c in cards:
            sc = int(re.search(r'data-score="(\d+)"', c[4]).group(1))
            scores[c[1]] = sc
            btn = re.search(r'<a class="at-sw" href="(?:/ca)?/software\?ospo=([^"]+)">.*?</svg>([\d.,]+) ', c[4])
            n_btn = int(re.sub(r"[.,]", "", btn.group(2))) if btn else 0
            # the SAME entries, by what they are - positions differ (DATA is name-sorted)
            got = sorted((D[i]["n"], D[i]["u"], D[i]["ex"]) for i in osw.get(c[1], [None, []])[1])
            want = sorted(((catj[i].get("name") or "(unnamed)"), catj[i].get("repo") or "", "")
                          for i in want_ix[c[1]])
            if not (sc == len(want_ix[c[1]]) == n_btn and (btn is None or btn.group(1) == c[1])
                    and got == want):
                bad.append((c[1], sc, n_btn, len(want_ix[c[1]])))
        check("%s: score = software in govoss = its button = /software?ospo= (same entries)" % name,
              (sum(1 for v in scores.values() if v) > 0, bad,
               sorted(osw) == sorted(i for i, v in want_ix.items() if v)), (True, [], True))
        # no ranks (owner, 2026-10-13): a card shows its software count when it has any,
        # and the list sorts by it or A-Z - two buttons, nothing else
        badc = []
        for c in cards:
            m = re.search(r'<div class="at-sc"[^>]*><span class="at-sn">([\d.,]+)</span>', c[4])
            if (int(re.sub(r"[.,]", "", m.group(1))) if m else 0) != scores[c[1]]:
                badc.append(c[1])
        check("%s: each card shows its software count (none at 0), no rank" % name,
              (badc, [x for x in ('class="at-rk', 'Unranked', 'class="at-bar"') if x in pg]), ([], []))
        srt = re.search(r'<div class="at-seg"[^>]*id="at-sort"[^>]*>(.*?)</div>', pg, re.S)
        # Group by country (owner, 2026-10-13): a toggle beside the sort, OFF by default
        # (one flat list), written to the hash as group=country and read back
        scr = "".join(re.findall(r'<script>(.*?)</script>', pg, re.S))
        tool = re.search(r'id="at-sort"[^>]*>.*?</div>\s*(<button[^>]*id="at-group"[^>]*>)', pg, re.S)
        check("%s: Group by country sits beside the sort, off by default, kept in the hash" % name,
              (bool(tool) and 'aria-pressed="false"' in tool.group(1), "group: false" in scr,
               "P.get('group') === 'country'" in scr and "P.set('group', 'country')" in scr,
               '<div class="at-flat" id="at-flat" hidden></div>' in pg),
              (True, True, True, True))
        # every placed card names its country beside its city, with the flag emoji
        noflag = [c[1] for c in cards if c[3] != "ZZ" and not re.search(
            r'<span class="at-ccm"><span class="at-cflag" aria-hidden="true">(&#\d+;)+</span> [^<]+</span>', c[4])]
        check("%s: each card shows its country's flag emoji and name beside the city" % name,
              (len(cards) > 0, noflag), (True, []))
        # the same side margins as every page (owner, 2026-10-13): the atlas and its
        # credits sit in theme.py's .wrap, and nothing sets its own gutter
        check("%s: the atlas and credits sit in the shared .wrap gutters" % name,
              (bool(re.search(r'<main id="main">\s*<div class="wrap at-wrap">\s*<div class="atlas" id="atlas">', pg)),
               'class="wrap at-wrap"' in pg and '<p class="ocred"' in pg
               and pg.index('class="wrap at-wrap"') < pg.index('<p class="ocred"'),
               re.findall(r'\.(?:atlas|ocred|at-wrap)\{[^}]*padding:0 \d+px', pg)),
              (True, True, []))
        # owner, 2026-10-14: no type colour down the cards' left edge; Product category
        # shows FN_SHOWN, the rest behind "Show all N" (folded by the
        # script, a pressed one never folded away), so the sidebar fits the atlas
        card_css = "".join(re.findall(r'\.at-card[^{]*\{[^}]*\}', pg))
        nfn = len(re.findall(r'class="at-fb" data-f="fn"', pg))
        check("%s: cards carry no type colour; Product category folds to its top FN_SHOWN" % name,
              ("border-left" in card_css, "--at-gov" in card_css or "--at-aca" in card_css or "--at-cor" in card_css,
               nfn > _bo.FN_SHOWN, bool(re.search(r'<button type="button" class="at-link at-fnmore" id="at-fnmore" '
                                                  r'aria-expanded="false" hidden>[^<]+ %d [^<]*</button>' % nfn, pg)),
               # the six are the first WITH offices (not .at-none), topped up with greyed
               # ones; a pressed one is never folded (Government + Community, 2026-10-14)
               all(t in scr for t in ("classList.contains('at-none')",
                                      "bs.filter(live).concat(bs.filter(function (b) { return !live(b); })).slice(0, L.fnshown)",
                                      "keep.indexOf(b) < 0 && b.getAttribute('aria-pressed') !== 'true'")),
               ((json.loads(re.search(r'<script type="application/json" id="at-data">(.*?)</script>', pg, re.S).group(1))
                 .get("L") or {}).get("fnshown")) == _bo.FN_SHOWN == 6),
              (False, False, True, True, True, True))
        # credits (owner, 2026-10-14): ONE visible line with what the licences and
        # trademarks require - each source linked with its licence, icons and flags,
        # the logo notice and its removal route - the rest behind a closed "More info"
        line = re.search(r'<p class="ocred" id="logo-notice">(.*?)</p>\s*<details class="ocred-more"><summary>[^<]+</summary>(.*?)</details>',
                         pg, re.S)
        need = ["https://floss-pso.network/public-sector-ospos/", "https://sustainoss.org/academic-map/",
                "https://landscape.todogroup.org/", "https://www.wikidata.org/", "https://lucide.dev/",
                "https://github.com/lipis/flag-icons", "https://github.com/sarapis/govoss-catalog/issues"]
        check("%s: credits: one line with every source, licence and the logo notice; details behind More info" % name,
              (bool(line), [u for u in need if not line or ('href="%s"' % u) not in line.group(1)],
               [lic for lic in ("CC0", "(MIT)", "(Apache-2.0)", "(ISC)") if not line or lic not in line.group(1)],
               bool(line) and line.group(2).count('<p class="ocred">') >= 4,
               pg.count('<p class="ocred"') - (line.group(2).count('<p class="ocred">') if line else 0)),
              (True, [], [], True, 1))
        check("%s: the list sorts by software or A-Z" % name,
              re.findall(r'data-sort="(\w+)"', srt.group(1)) if srt else None, ["software", "name"])
        check("%s: no sidebar ranking, no score signals, no per-product links" % name,
              [x for x in ('class="at-trow"', 'id="at-top"', 'class="at-sigs"', 'class="at-prod"', 'at-how')
               if x in pg], [])
        # each card toggles its own details panel, closed in the HTML (open without JS)
        check("%s: every card has a toggle controlling its own closed details panel" % name,
              [c[1] for c in cards if 'aria-controls="%s-x"' % c[1] not in c[4]
               or '<div class="at-more" id="%s-x" hidden>' % c[1] not in c[4]], [])
        check("%s: without JavaScript the details show" % name,
              bool(re.search(r'<noscript><style>\.at-card \.at-more\[hidden\]\{display:flex!important;\}'
                             r'\.at-card \.at-codes\[hidden\]\{display:flex!important;\}', pg)), True)
        # no character entity inside a script, JSON ones included (entities are not
        # decoded there: a "·" once showed as &#183;)
        # a CSS escape written into a Python string ("\2192") once shipped as a control
        # character + "92" - no built page may carry one
        check("%s: no control character in the page" % name,
              sorted({hex(ord(ch)) for ch in pg if ord(ch) < 32 and ch not in "\n\r\t"}), [])
        check("%s: no character entity inside a script" % name,
              [m for s_ in re.findall(r'<script[^>]*>(.*?)</script>', pg, re.S) for m in re.findall(r'&#\d+;', s_)], [])
        try:
            cfg = json.loads(re.search(r'<script type="application/json" id="at-data">(.*?)</script>', pg, re.S).group(1))
        except Exception:
            cfg = {}
        # ONE world map (owner, 2026-10-09): a single SVG of the Equal Earth frame
        gfw = json.load(open(os.path.join(HERE, "geo", "ospo_frames.json")))
        check("%s: one world map - a single SVG, the single Equal Earth frame's land" % name,
              (pg.count('<svg class="at-svg"'), sorted(gfw["frames"]),
               [f.get("projection") for f in gfw["frames"].values()],
               '<path d="%s"/>' % gfw["frames"]["world"]["land"] in pg, cfg.get("vb")),
              (1, ["world"], ["equal-earth"], True, gfw["viewbox"]))
        zb = re.search(r'<div class="at-zoom" role="group" aria-label="[^"]+">(.*?)</div>', pg, re.S)
        check("%s: zoom in / out / whole world, each a labelled button" % name,
              zb and re.findall(r'<button type="button" data-zoom="(\w+)" aria-label="[^"]+"', zb.group(1)),
              ["in", "out", "reset"])
        # owner, 2026-10-13: Type is the sidebar's FIRST block and the page opens on
        # Government (All is type=all, read back); no "Now reading" box, no country
        # chips, the map never flies to a country; no "Founded n/a"; one country singular
        first = re.search(r'<div class="at-sbody">\s*<div class="at-blk"[^>]*>\s*<h2 class="at-lbl" id="([^"]+)"', pg)
        sc = "".join(re.findall(r'<script>(.*?)</script>', pg, re.S))
        check("%s: Type is the first sidebar block, and the page opens on Government" % name,
              (first and first.group(1), "var TYPE0 = 'government';" in sc,
               "P.get('type') === 'all'" in sc and "P.set('type', st.type || 'all')" in sc),
              ("at-l-type", True, True))
        check("%s: the map does not follow countries, and no card says Founded n/a" % name,
              [x for x in ('class="at-now"', 'id="at-chips"', 'fitGroup', 'onScroll', 'Founded', 'Fundaci')
               if x in pg], [])
        # logos stay, with a notice (owner, 2026-10-13): their owners' trademarks, outside
        # govoss's licences, no endorsement, removed on request - and never in the data
        ln = re.search(r'<p class="ocred" id="logo-notice">(.*?)</p>', pg, re.S)
        oj_raw = open(os.path.join(SITE, "ospos.json")).read()
        check("%s: the logo notice is on the page, and no logo is in /ospos.json" % name,
              (bool(ln) and 'href="https://github.com/sarapis/govoss-catalog/issues"' in ln.group(1),
               "/ospo-img/logo/" in pg, "ospo-img" in oj_raw or '"logo"' in oj_raw),
              (True, True, False))
        # a closed card shows at most two rows of tags, then "+N"; an open one all
        # (owner, 2026-10-13). Measured in the browser - the static part pinned here
        check("%s: closed cards clamp their tags to two rows, open ones show all" % name,
              ("var TAGROWS = 2;" in sc, "c.classList.contains('at-open')) return;" in sc,
               "clampTags(c);" in sc and "clampTags(d);" in sc, ".at-tag.at-tmore{" in pg,
               bool((cfg.get("L") or {}).get("moretags"))),
              (True, True, True, True, True))
        check("%s: one country is singular" % name,
              (bool((cfg.get("L") or {}).get("all1")), bool((cfg.get("L") or {}).get("some1")), "nc === 1" in sc),
              (True, True, True))
        # every office is a map point or in Not yet placed, and each point is the
        # build's own projection of its location
        locs = json.load(open(os.path.join(HERE, "ospos", "locations.json")))["locations"]
        pts = cfg.get("pts") or {}
        zz = {c[1] for c in cards if c[3] == "ZZ"}
        check("%s: every office is a map point or in Not yet placed" % name,
              (len(pts) > 0, sorted(r["id"] for r in od if r["id"] not in pts and r["id"] not in zz)), (True, []))
        fr = gfw["frames"]["world"]
        off = []
        for i, (x, y) in pts.items():
            l = locs.get(i) or {}
            ex, ey = _bo.equal_earth(l["lon"], l["lat"])
            if abs(ex * fr["s"] + fr["ox"] - x) > 0.06 or abs(ey * fr["s"] + fr["oy"] - y) > 0.06:
                off.append(i)
        check("%s: each map point is its office's projected location" % name, off, [])
        check("%s: the script's strings are all there" % name,
              sorted({"all", "some", "all1", "some1", "offices", "office", "cluster", "moretags", "codes", "thou"}
                     - set((cfg.get("L") or {}))), [])
    gf = json.load(open(os.path.join(HERE, "geo", "ospo_frames.json")))
    drift = []
    for k, fr in gf["frames"].items():
        x, y = _bo.equal_earth(fr["probe"]["lon"], fr["probe"]["lat"])
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
    # ownership (2026-10-16): the built rows carry EXACTLY the hand-checked facts -
    # compared fact by fact, not by count - and every academic office has one
    own = json.load(open(os.path.join(HERE, "ospos", "ownership.json")))["ownership"]
    built_own = {r["id"]: r["ownership"] for r in oj["ospos"] if r.get("ownership") is not None}
    check("/ospos.json ownership = ospos/ownership.json, office by office",
          built_own, {k: {"value": v["value"], "via": v["via"], "note": v.get("note")}
                      for k, v in own.items()})
    check("/ospos.json: every academic office's ownership has been checked",
          sorted(r["id"] for r in oj["ospos"] if r["type"] == "academic" and r["ownership"] is None), [])
    check("/ospos.json: govoss's own licence, exactly", oj.get("licence"),
          {"govoss_fields": "CC0 1.0, govoss (https://govoss.cat)",
           "lists": "each list's own: sources[*].licence"})
    check("/ospos.json: the FLOSS-PSO licence, exactly",
          ((oj.get("sources") or {}).get("floss-pso") or {}).get("licence"),
          "CC0 1.0 (the FLOSS-PSO Network's OSPO list)")
    check("/ospos.json documents its country codes",
          sorted(oj.get("country_codes") or {}),
          ["AR", "BR", "CN", "DE", "DK", "EL", "ES", "FI", "FR", "GB", "IE", "IN", "INT", "JP",
           "KR", "LU", "NL", "SE", "SG", "TW", "US", "UY"])
    check("/ospos.json names every country code, exactly (UNNYC's headings)",
          (oj.get("country_names"), sorted(oj.get("country_names") or {}) == sorted(oj.get("country_codes") or {})),
          ({"DE": "Germany", "DK": "Denmark", "EL": "Greece", "ES": "Spain", "FR": "France",
            "GB": "United Kingdom", "IE": "Ireland", "INT": "International", "LU": "Luxembourg",
            "NL": "Netherlands", "US": "United States", "AR": "Argentina", "BR": "Brazil",
            "CN": "China", "FI": "Finland", "IN": "India", "JP": "Japan", "KR": "South Korea",
            "SE": "Sweden", "TW": "Taiwan", "SG": "Singapore", "UY": "Uruguay"}, True))
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

    # ---- 14. /status.json REPORTS A FAILED HARVEST FROM THE FILES (2026-10-14).
    # `last_run` is whatever ran last, so a --no-harvest publish after a failed
    # Monday said `ok, []` through six publishes while 12 sources and all three
    # OSPO lists had failed. build_sources.harvest_problems() reads
    # cache/_fetched.json and cache/ospos.json instead. Synthetic cases first (the
    # live files may hold no failure at all), then the built file against the real ones.
    import importlib.util, time as _t
    _bs = importlib.util.spec_from_file_location("build_sources", os.path.join(HERE, "build_sources.py"))
    BS = importlib.util.module_from_spec(_bs); _bs.loader.exec_module(BS)
    now = _t.mktime(_t.gmtime())
    def stamp(days):
        return _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime(_t.time() - days * 86400))
    srcs = {"XX/demo": {"label": "Demo", "checkpoint": "demo"}}
    def hp(rec=None, ospo=None):
        return BS.harvest_problems({"demo": rec} if rec else {}, ospo or {}, srcs, now)
    def levels(ps):
        return [a for a, _ in ps]
    got = hp({"ok": False, "fetched_at": stamp(2), "last_error_at": stamp(0), "error": "URLError x"})
    check("14 a failed last attempt warns at once, even on a 2-day-old copy", levels(got), ["warn"])
    check("14 ...naming the catalogue, the failure and its reason",
          bool(got) and all(w in got[0][1] for w in ("'Demo'", "attempt failed", "URLError x")), True)
    check("14 a failed attempt on a copy >29 days old is critical",
          levels(hp({"ok": False, "fetched_at": stamp(40)})), ["critical"])
    check("14 a fresh success reports nothing", hp({"ok": True, "fetched_at": stamp(3)}), [])
    check("14 a record with no `ok` is read as a success", hp({"fetched_at": stamp(3)}), [])
    check("14 a success aged >15 days warns, >29 is critical",
          (levels(hp({"ok": True, "fetched_at": stamp(20)})),
           levels(hp({"ok": True, "fetched_at": stamp(40)}))), (["warn"], ["critical"]))
    check("14 looked up by CHECKPOINT key, never the sources.py key",
          BS.harvest_problems({"XX/demo": {"ok": False, "fetched_at": stamp(2)}}, {}, srcs, now), [])
    ok_l = {"ok": True, "fetched_at": stamp(1)}
    got = hp(ospo={"floss-pso": {"ok": False, "fetched_at": stamp(5), "failed_at": stamp(2),
                                 "error": "URLError y"}, "academic-map": ok_l})
    check("14 a failed OSPO list warns, naming the list; an ok one says nothing",
          (levels(got), bool(got) and "'floss-pso'" in got[0][1] and "URLError y" in got[0][1]),
          (["warn"], True))
    check("14 a failed OSPO list whose copy is >29 days old is critical",
          levels(hp(ospo={"todo-landscape": {"ok": False, "fetched_at": stamp(40)}})), ["critical"])
    # the built file vs the real cache files: one problem per failed source, by name
    st = json.load(open(os.path.join(SITE, "status.json")))
    msgs = [p["message"] for p in st.get("problems") or []]
    fetched = json.load(open(os.path.join(HERE, "cache", "_fetched.json")))
    ospo_src = json.load(open(os.path.join(HERE, "cache", "ospos.json"))).get("sources") or {}
    label_of = {m.get("checkpoint"): m["label"] for m in BS.S.SOURCES.values()}
    want = sorted(["catalogue '%s': the last harvest attempt" % label_of[k]
                   for k, r in fetched.items() if r.get("ok") is False and k in label_of]
                  + ["OSPO list '%s': the last fetch failed" % k
                     for k, r in ospo_src.items() if r.get("ok") is False])
    have = sorted(w for w in want if any(m.startswith(w) for m in msgs))
    check("14 built status.json names every source whose last attempt failed (%d)" % len(want),
          have, want)

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
