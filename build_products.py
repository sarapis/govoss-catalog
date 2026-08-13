#!/usr/bin/env python3
"""Build site/products.html + site/products.json - the proprietary-software side.

The catalogue answers "what open source exists". This page answers the question a
buyer actually starts from: "we pay for X - what could replace it?". It is the
browsable form of by-product.json, which existed as a file nobody could read.

Deliberately NOT in the top nav. Proprietary software is a way INTO the open
source, not a peer of it, so the entry point is a facet in the catalog sidebar
whose "Show all" lands here. See DEMAND-SIDE-CATALOGUE.md.

Cards are rendered as STATIC HTML, not client-side like catalogue.html. 391
products is small enough, and it means deep links (#p-dropbox) work natively and
an agent reading raw HTML gets the content without running the filter script.

Runs AFTER export_json.py - it reads by-product.json.

No f-strings for markup: plain strings with __PLACEHOLDER__ tokens.
"""
import json, os, re, importlib.util, time
from urllib.parse import quote

OUT = os.path.dirname(os.path.abspath(__file__))
SITE = f"{OUT}/site"
NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

_th = importlib.util.spec_from_file_location("theme", f"{OUT}/theme.py")
theme = importlib.util.module_from_spec(_th); _th.loader.exec_module(theme)
_tp = importlib.util.spec_from_file_location("_ui_template", f"{OUT}/_ui_template.py")
T = importlib.util.module_from_spec(_tp); _tp.loader.exec_module(T)
_cn = importlib.util.spec_from_file_location("ctfg_nav", f"{OUT}/ctfg_nav.py")
ctfg_nav = importlib.util.module_from_spec(_cn); _cn.loader.exec_module(ctfg_nav)
NAV = ctfg_nav.load()


def esc(s):
    return ("" if s is None else str(s)).replace("&", "&amp;").replace(
        "<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def pslug(name):
    """Anchor id for a product. DUPLICATED in build_ui.py so the catalog page can
    link here without importing this module (importing would execute its body,
    the same reason stable_order() is duplicated in harvest.py and dedupe.py).
    If this changes, change it there too."""
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", (name or "").lower())).strip("-")


QUAL = {"paid-tier": "paid tier", "service": "hosted service"}


def qual(m):
    """Same rule as the catalog page: qualify anything that is not a
    like-for-like software swap, so 'Replaces X' is never asserted flatly."""
    q = []
    if m.get("kind") in QUAL:
        q.append(QUAL[m["kind"]])
    if m.get("confidence") in ("partial", "adjacent"):
        q.append(m["confidence"])
    return ", ".join(q)


def build():
    bp = json.load(open(f"{SITE}/by-product.json"))
    meta = json.load(open(f"{SITE}/meta.json"))
    prop = json.load(open(f"{OUT}/proprietary.json"))
    aliases = json.load(open(f"{OUT}/product_aliases.json"))["aliases"]

    gaps = [p for p in prop["products"] if p.get("name")]

    # A product cannot both have an alternative and be an unfilled gap. This is
    # the same class of check as export_json.py's orphan warning: the two files
    # are hand-maintained and drift silently otherwise.
    both = sorted({p["name"] for p in gaps} & set(bp))
    if both:
        raise SystemExit("build_products: in BOTH by-product.json and proprietary.json "
                         "(remove from proprietary.json): " + ", ".join(both))

    # Most replaceable first - the count of alternatives IS the facet count on
    # the catalog page, so the two orderings agree. Name breaks ties so the
    # output is deterministic (242 products have exactly one alternative).
    products = sorted(bp.items(), key=lambda kv: (-len(kv[1]), kv[0].lower()))

    slugs = {}
    for name, _ in products:
        slugs.setdefault(pslug(name), []).append(name)
    for p in gaps:
        slugs.setdefault(pslug(p["name"]), []).append(p["name"])
    clash = {k: v for k, v in slugs.items() if len(v) > 1}
    if clash:
        raise SystemExit("build_products: anchor id collision %s" % clash)

    # ---- rows for products WITH alternatives.
    # A dense table, not cards: the question is "is our product here, and what
    # replaces it", which is a scan down one column. Inter is the design system's
    # face for dense data.
    cards = []
    for name, alts in products:
        links = []
        for a in alts:
            q = qual(a)
            url = a.get("repo_url") or ""
            nm = ('<a href="%s">%s</a>' % (esc(url), esc(a["name"]))) if url \
                else '<span class="a-x">' + esc(a["name"]) + '</span>'
            links.append(nm + (' <span class="a-q">(' + esc(q) + ')</span>' if q else ""))
        cards.append(
            '<tr id="p-' + pslug(name) + '" data-n="' + esc(name.lower()) + '">'
            + '<th scope="row">' + esc(name) + '</th>'
            + '<td class="c-alt">' + ", ".join(links) + '</td>'
            # quote(), not a space-swap: "Veeam Backup & Replication" would put a
            # bare & in the query string and the catalog would receive
            # rp="Veeam Backup " plus a stray parameter.
            + '<td class="c-act"><a href="/?rp=' + quote(name, safe="")
            + '">See alternatives &rarr;</a></td></tr>')

    # ---- rows for products with NO alternative
    gcards = []
    for p in sorted(gaps, key=lambda x: x["name"].lower()):
        tag = ("content or data" if p.get("kind") == "data-service" else "software")
        gcards.append(
            '<tr id="p-' + pslug(p["name"]) + '" data-n="' + esc(p["name"].lower()) + '">'
            + '<th scope="row">' + esc(p["name"]) + '</th>'
            + '<td class="c-alt">' + esc(p.get("purpose") or "") + '</td>'
            + '<td class="c-act"><span class="g-t">' + tag + '</span></td></tr>')

    n_alts = sum(len(v) for v in bp.values())
    n_data = sum(1 for p in gaps if p.get("kind") == "data-service")

    subs = {
        "__NPROD__": "{:,}".format(len(products)),
        "__NALTS__": "{:,}".format(n_alts),
        "__NGAP__": str(len(gaps)),
        "__NGAPSW__": str(len(gaps) - n_data),
        "__NDATA__": str(n_data),
        "__NALIAS__": str(len(aliases)),
        "__CARDS__": "".join(cards),
        "__GAPS__": "".join(gcards),
        "__GEN__": esc(meta.get("generated_at") or NOW),
    }

    page = (theme.head(
        "Proprietary software and open source alternatives | govoss",
        "%s proprietary products mapped to government open source alternatives, plus %s "
        "products governments buy for which this catalogue has no answer."
        % (len(products), len(gaps)))
        + "<style>\n" + theme.FONT_FACE_CSS + theme.CSS + T.PAGE_CSS + PAGE_CSS + "</style>\n"
        + theme.utility_bar(NAV) + theme.topbar("") + BODY + theme.footer(NAV))

    for k, v in subs.items():
        page = page.replace(k, v)
    left = sorted(set(re.findall(r"__[A-Z_]{3,}__", page)))
    if left:
        raise SystemExit("build_products: unsubstituted placeholders %s" % left)

    page = page.encode("ascii", "xmlcharrefreplace").decode()
    open(f"{SITE}/products.html", "w").write(page)

    json.dump({
        "generated_at": meta.get("generated_at") or NOW,
        "human_page": "https://govoss-catalog.vercel.app/products.html",
        "disclaimer": prop["_README"]["status"],
        "counts": {"with_alternatives": len(products), "alternatives": n_alts,
                   "no_alternative": len(gaps), "aliases": len(aliases)},
        "with_alternatives": [
            {"product": k, "slug": pslug(k),
             "alternatives": [{"name": a["name"], "id": a["id"],
                               "confidence": a["confidence"], "kind": a["kind"],
                               "country": a["country"], "adopters": a["adopters"],
                               "licence_spdx": a["licence_spdx"],
                               "repo_url": a["repo_url"]} for a in v]}
            for k, v in products],
        "no_alternative": [
            {"product": p["name"], "slug": pslug(p["name"]), "kind": p.get("kind"),
             "purpose": p.get("purpose"), "seen_in": p.get("seen_in") or []}
            for p in sorted(gaps, key=lambda x: x["name"].lower())],
        "aliases": aliases,
    }, open(f"{SITE}/products.json", "w"), indent=1, sort_keys=True)

    print("products page: %d products -> %d alternatives, %d with none "
          "(%d software, %d data) (%.0f KB) + products.json"
          % (len(products), n_alts, len(gaps), len(gaps) - n_data, n_data, len(page) / 1024))


PAGE_CSS = """
.sec{margin-top:40px;}
.sechead{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;
  gap:8px 20px;padding-bottom:10px;}
.lede{font-size:15px;line-height:1.6;color:var(--ink-600);max-width:72ch;}
.note{font-size:13px;line-height:1.6;color:var(--ink-faint);max-width:72ch;margin-top:10px;}
#pq{width:100%;max-width:420px;margin-top:18px;}

/* Dense table. A flex/grid child defaults to min-width:auto, which defeats
   overflow-x on a wide table - the wrapper needs min-width:0 explicitly. That
   trap is already documented in DESIGN-BRIEF.md; it applies here too. */
.twrap{margin-top:16px;min-width:0;overflow-x:auto;border:1px solid var(--border);
  border-radius:var(--r-table);background:var(--surface);}
table.ptab{width:100%;border-collapse:collapse;font-size:13px;line-height:1.5;}
table.ptab thead th{font-family:var(--font-ui);font-size:10px;font-weight:600;
  letter-spacing:.1em;text-transform:uppercase;color:var(--ink-faint);text-align:left;
  padding:10px 14px;border-bottom:1px solid var(--border);white-space:nowrap;}
/* --border-soft is the semantic alias for the faint-divider ramp step; use the
   purpose token, not --line-200 directly. */
table.ptab tbody tr{border-top:1px solid var(--border-soft);scroll-margin-top:90px;}
table.ptab tbody tr:first-child{border-top:0;}
table.ptab tbody tr:target{background:var(--primary-tint);}
/* [hidden] is display:none in the UA sheet, but any `tr{display:table-row}` in a
   reset would outrank it and the filter would silently do nothing. */
table.ptab tbody tr[hidden]{display:none;}
table.ptab th[scope=row]{font-weight:600;color:var(--ink);text-align:left;
  padding:9px 14px;vertical-align:top;white-space:nowrap;}
table.ptab td{padding:9px 14px;vertical-align:top;color:var(--ink-600);}
.c-alt a{color:var(--primary);text-decoration:none;}
.c-alt a:hover{text-decoration:underline;}
.a-x{color:var(--ink-600);}          /* no repo url upstream - nothing to link to */
.a-q{color:var(--ink-faint);font-size:12px;}
.c-act{white-space:nowrap;text-align:right;}
.c-act a{color:var(--primary);text-decoration:none;font-size:12px;}
.c-act a:hover{text-decoration:underline;}
.g-t{font-family:var(--font-ui);font-size:10px;font-weight:600;letter-spacing:.06em;
  text-transform:uppercase;color:var(--ink-faint);}
.nores{font-size:14px;color:var(--ink-faint);margin-top:16px;}
/* An empty <th> leaves a screen reader announcing an unnamed column. The label
   is hidden rather than dropped. */
.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);
  white-space:nowrap;}
"""

BODY = """
<a class="skip" href="#main">Skip to content</a>
<div class="wrap">
  <main id="main">

  <section class="sec" style="margin-top:28px">
    <h1 style="font-size:30px;margin:0 0 12px">Proprietary software, and what could replace it</h1>
    <p class="lede">The catalogue lists government open source. This is the other side of it:
      <b>__NPROD__ proprietary products</b> mapped to <b>__NALTS__</b> open source
      alternatives that a government somewhere already publishes &mdash; plus
      <b>__NGAP__ products governments buy for which this catalogue has no answer</b>,
      listed so a gap reads as a gap rather than as an oversight.</p>
    <p class="note">These mappings are <b>hand-curated and unverified</b>. Absence of a
      mapping is not evidence that no alternative exists. Anything that is not a
      like-for-like swap is qualified &mdash; a <i>paid tier</i> is usually a licence you
      stop renewing, a <i>hosted service</i> means you still need somewhere to run it, and
      <i>partial</i> or <i>adjacent</i> means real gaps or a changed workflow. Machine
      readable at <a href="/products.json">/products.json</a>; the raw index is
      <a href="/by-product.json">/by-product.json</a>.</p>
    <input id="pq" type="search" placeholder="Filter products, e.g. Dropbox"
      aria-label="Filter products">
  </section>

  <section class="sec" id="mapped">
    <div class="sechead"><h3>Has an open source alternative</h3>
      <span class="r" style="font-size:12px;color:var(--ink-faint)">__NPROD__ products,
        most replaceable first</span></div>
    <hr class="dashed">
    <div class="twrap">
      <table class="ptab">
        <thead><tr><th scope="col">Proprietary product</th>
          <th scope="col">Open source alternatives</th>
          <th scope="col"><span class="vh">See them in the catalog</span></th></tr></thead>
        <tbody id="g-mapped">__CARDS__</tbody>
      </table>
    </div>
    <p class="nores" id="none-mapped" hidden>No product matches that filter.</p>
  </section>

  <section class="sec" id="gaps">
    <div class="sechead"><h3>No alternative in this catalogue</h3>
      <span class="r" style="font-size:12px;color:var(--ink-faint)">__NGAPSW__ software,
        __NDATA__ content or data</span></div>
    <hr class="dashed">
    <p class="note" style="margin-top:12px">Seeded from one jurisdiction's licence data
      (New York City), so this list is NYC-shaped &mdash; US municipal and public-safety
      software is over-represented relative to what other governments buy. The
      <i>content or data</i> entries are a different case: open source cannot substitute a
      legal-research corpus or a traffic feed, so the absence is a category fact rather
      than a gap to fill.</p>
    <div class="twrap">
      <table class="ptab">
        <thead><tr><th scope="col">Proprietary product</th>
          <th scope="col">What it is used for</th><th scope="col">Type</th></tr></thead>
        <tbody id="g-gaps">__GAPS__</tbody>
      </table>
    </div>
    <p class="nores" id="none-gaps" hidden>No product matches that filter.</p>
  </section>

  </main>
</div>
<script>
(function () {
  var q = document.getElementById('pq');
  var groups = [['g-mapped', 'none-mapped'], ['g-gaps', 'none-gaps']];
  function apply() {
    var v = (q.value || '').trim().toLowerCase();
    groups.forEach(function (g) {
      var n = 0;
      var body = document.getElementById(g[0]);
      var rows = body.children;
      for (var i = 0; i < rows.length; i++) {
        var hit = !v || rows[i].getAttribute('data-n').indexOf(v) >= 0;
        rows[i].hidden = !hit;
        if (hit) n++;
      }
      // Hide the whole table when nothing matches - a bare header row over an
      // empty body reads as a broken table rather than as an empty result.
      var wrap = body.parentNode.parentNode;
      wrap.hidden = n === 0;
      document.getElementById(g[1]).hidden = n > 0;
    });
  }
  q.addEventListener('input', apply);
  // A deep link must win over a stale filter value the browser restored on reload.
  if (location.hash) { q.value = ''; }
  apply();
})();
</script>
"""

if __name__ == "__main__":
    build()
