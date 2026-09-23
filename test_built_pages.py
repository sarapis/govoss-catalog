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
import html
import json
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "site")

PAGES = {
    "index.html": os.path.join(SITE, "index.html"),
    "sources.html": os.path.join(SITE, "sources.html"),
    "api.html": os.path.join(SITE, "api.html"),
    "products.html": os.path.join(SITE, "products.html"),
    "catalogue.html": os.path.join(HERE, "catalogue.html"),
    # Catalan copies (i18n.py). Every check that loops over PAGES covers them.
    "ca/index.html": os.path.join(SITE, "ca", "index.html"),
    "ca/sources.html": os.path.join(SITE, "ca", "sources.html"),
    "ca/api.html": os.path.join(SITE, "ca", "api.html"),
    "ca/products.html": os.path.join(SITE, "ca", "products.html"),
    "catalogue.ca.html": os.path.join(HERE, "catalogue.ca.html"),
}


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
    failed = []

    def check(label, got, want):
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
    for name in ("index.html", "products.html"):
        page = pages[name]
        if ".hidden" in page or "hidden>" in page:
            check("%s carries [hidden]{display:none!important}" % name,
                  bool(re.search(r"\[hidden\]\s*\{[^}]*display\s*:\s*none\s*!important", page)),
                  True)

    # ---- 4. CROSS-PAGE: every ?src= link resolves to a real <option>.
    src_links = [urllib.parse.unquote(m)
                 for m in re.findall(r'href="/\?src=([^"]*)"', pages["sources.html"])]
    options = set(html.unescape(m)
                  for m in re.findall(r'<option value="([^"]*)">', pages["index.html"]))
    check("sources.html emits a ?src= link per harvested catalogue",
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
    data = extract_js_array(pages["index.html"], "DATA")
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
    # are masked because each page passes its own catalogue count. The topbar's
    # "Submit a catalog" button on every page links to /#submit, so the catalog
    # page must carry exactly one target for it.
    def submit(page):
        m = re.search(r'<div class="submit" id="submit">.*?</div>', page, re.S)
        return re.sub(r"\d+", "N", m.group(0)) if m else None
    check("index.html carries exactly one #submit target",
          pages["index.html"].count('id="submit"'), 1)
    check("the Get involved block is identical on / and /sources.html",
          submit(pages["sources.html"]) is not None
          and submit(pages["index.html"]) == submit(pages["sources.html"]), True)

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
    ENG = {"index.html": "/", "sources.html": "/sources.html", "api.html": "/api.html",
           "products.html": "/products.html"}
    n12 = 0
    for en_name, route in ENG.items():
        for lang in i18n.LANGS:
            name = en_name if lang == "en" else "%s/%s" % (lang, en_name)
            page = pages[name]
            n12 += 4
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
    # the Catalan catalog's ?src= links (from /ca/sources.html) must resolve too
    ca_src = [urllib.parse.unquote(m) for m in
              re.findall(r'href="/ca/\?src=([^"]*)"', pages["ca/sources.html"])]
    ca_opts = set(html.unescape(m) for m in
                  re.findall(r'<option value="([^"]*)">', pages["ca/index.html"]))
    check("every /ca/?src= value matches a Catalan catalog <option>",
          (len(ca_src) > 0, sorted(l for l in ca_src if l not in ca_opts)), (True, []))
    # The catalog's inline script must PARSE in every language. A Catalan
    # apostrophe unescaped inside a single-quoted JS string would break the whole
    # page while every static check above still passed.
    for name in ("index.html", "ca/index.html"):
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
    n12 += 5

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
                "/data.json": "/entries.json", "/status.html": "/sources.html"}
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
    total = 9 + len(pages) + 7 + 1 + n12 + 5
    print("\n%d checks run, %d failed" % (total, len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
