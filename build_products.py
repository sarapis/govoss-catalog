#!/usr/bin/env python3
"""Build site/products.html + site/products.json - the proprietary-software side.

The catalogue answers "what open source exists". This page answers the question a
buyer actually starts from: "we pay for X - what could replace it?". It is the
browsable form of by-product.json, which existed as a file nobody could read.

ONE table, not two. Products with and without an alternative are the same kind of
object and belong in the same list; "has a govoss alternative" is a filter over
it, on by default. Splitting them into two tables made the gap list look like a
separate artefact rather than the other end of the same shelf.

Deliberately NOT in the top nav. Proprietary software is a way INTO the open
source, not a peer of it, so the entry point is a facet in the catalog sidebar
whose "Show all" lands here. See DEMAND-SIDE-CATALOGUE.md.

Rows are STATIC HTML, not client-side like catalogue.html. 372 products is small
enough, and it means deep links (#p-dropbox) work natively and an agent reading
raw HTML gets the content without running the filter script.

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
_tx = importlib.util.spec_from_file_location("taxonomy", f"{OUT}/taxonomy.py")
TAX = importlib.util.module_from_spec(_tx); _tx.loader.exec_module(TAX)


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

    pmeta = {p["name"]: p for p in prop["products"] if p.get("name")}

    # Every product in the index needs metadata, or its row renders with empty
    # cells and drops out of the function filter. Same class of check as
    # export_json.py's orphan warning: both files are hand-maintained.
    missing = sorted(set(bp) - set(pmeta))
    if missing:
        raise SystemExit("build_products: %d products in by-product.json have no "
                         "entry in proprietary.json (add name/description/function): %s"
                         % (len(missing), ", ".join(missing[:12])))
    bad = [p for p in pmeta.values() if p.get("function") not in TAX.FUNCTIONS]
    if bad:
        raise SystemExit("build_products: bad function key: %s"
                         % [(p["name"], p.get("function")) for p in bad[:8]])

    # Most replaceable first, then products with no alternative, name breaking
    # ties so the output is deterministic (most products have one alternative).
    def order(name):
        return (-len(bp.get(name, [])), name.lower())

    names = sorted(pmeta, key=order)

    slugs = {}
    for n in names:
        slugs.setdefault(pslug(n), []).append(n)
    clash = {k: v for k, v in slugs.items() if len(v) > 1}
    if clash:
        raise SystemExit("build_products: anchor id collision %s" % clash)

    rows, n_alt = [], 0
    for name in names:
        p = pmeta[name]
        alts = bp.get(name) or []
        if alts:
            n_alt += 1
        links = []
        for a in alts:
            q = qual(a)
            url = a.get("repo_url") or ""
            nm = ('<a href="%s">%s</a>' % (esc(url), esc(a["name"]))) if url \
                else '<span class="a-x">' + esc(a["name"]) + '</span>'
            links.append(nm + (' <span class="a-q">(' + esc(q) + ')</span>' if q else ""))
        cell = ", ".join(links) if links else (
            '<span class="a-none">' + ("content or data subscription"
                                       if p.get("kind") == "data-service"
                                       else "none mapped") + '</span>')
        act = ('<a href="/?rp=' + quote(name, safe="") + '">See alternatives &rarr;</a>'
               if alts else "")
        rows.append(
            '<tr id="p-' + pslug(name) + '" data-n="'
            + esc((name + " " + (p.get("description") or "")).lower())
            + '" data-f="' + esc(p["function"]) + '" data-a="' + ("1" if alts else "0") + '">'
            + '<th scope="row">' + esc(name) + '</th>'
            + '<td class="c-desc">' + esc(p.get("description") or "") + '</td>'
            + '<td class="c-fn">' + esc(TAX.FUNCTIONS[p["function"]]) + '</td>'
            + '<td class="c-alt">' + cell + '</td>'
            + '<td class="c-act">' + act + '</td></tr>')

    fopts = "".join(
        '<option value="%s">%s</option>' % (esc(k), esc(v))
        for k, v in sorted(TAX.FUNCTIONS.items(), key=lambda kv: kv[1])
        if any(p["function"] == k for p in pmeta.values()))

    n_links = sum(len(v) for v in bp.values())
    n_gap = len(names) - n_alt
    n_data = sum(1 for p in pmeta.values() if p.get("kind") == "data-service")

    subs = {
        "__NPROD__": "{:,}".format(len(names)),
        "__NALT__": "{:,}".format(n_alt),
        "__NLINKS__": "{:,}".format(n_links),
        "__NGAP__": str(n_gap),
        "__NDATA__": str(n_data),
        "__NCURATED__": str(sum(1 for p in pmeta.values() if p.get("desc_src") == "curated")),
        "__FOPTS__": fopts,
        "__ROWS__": "".join(rows),
        "__GEN__": esc(meta.get("generated_at") or NOW),
    }

    page = (theme.head(
        "Proprietary software and open source alternatives | govoss",
        "%s proprietary products governments buy, %s of them with a government "
        "open source alternative, filterable by function." % (len(names), n_alt))
        + "<style>\n" + theme.FONT_FACE_CSS + theme.CSS + T.PAGE_CSS + PAGE_CSS + "</style>\n"
        + theme.utility_bar() + theme.topbar("") + BODY + theme.footer())

    for k, v in subs.items():
        page = page.replace(k, v)
    left = sorted(set(re.findall(r"__[A-Z_]{3,}__", page)))
    if left:
        raise SystemExit("build_products: unsubstituted placeholders %s" % left)

    theme.assert_variant_live(page)

    page = page.encode("ascii", "xmlcharrefreplace").decode()
    open(f"{SITE}/products.html", "w").write(page)

    json.dump({
        "generated_at": meta.get("generated_at") or NOW,
        "human_page": "https://govoss-catalog.vercel.app/products.html",
        "disclaimer": prop["_README"]["status"],
        "counts": {"products": len(names), "with_alternatives": n_alt,
                   "no_alternative": n_gap, "alternatives": n_links,
                   "aliases": len(aliases)},
        "functions": {k: v for k, v in TAX.FUNCTIONS.items()},
        "products": [
            {"product": n, "slug": pslug(n),
             "description": pmeta[n].get("description"),
             "description_source": pmeta[n].get("desc_src"),
             "function": pmeta[n]["function"],
             "function_label": TAX.FUNCTIONS[pmeta[n]["function"]],
             "kind": pmeta[n].get("kind"),
             "seen_in": pmeta[n].get("seen_in") or [],
             "has_alternative": bool(bp.get(n)),
             "alternatives": [{"name": a["name"], "id": a["id"],
                               "confidence": a["confidence"], "kind": a["kind"],
                               "country": a["country"], "adopters": a["adopters"],
                               "licence_spdx": a["licence_spdx"],
                               "repo_url": a["repo_url"]} for a in (bp.get(n) or [])]}
            for n in names],
        "aliases": aliases,
    }, open(f"{SITE}/products.json", "w"), indent=1, sort_keys=True)

    print("products page: %d products, %d with an alternative (%d links), %d without "
          "(%d data) (%.0f KB) + products.json"
          % (len(names), n_alt, n_links, n_gap, n_data, len(page) / 1024))


PAGE_CSS = """
.sec{margin-top:40px;}
.sechead{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;
  gap:8px 20px;padding-bottom:10px;}
.lede{font-size:15px;line-height:1.6;color:var(--ink-600);}
.note{font-size:13px;line-height:1.6;color:var(--ink-faint);margin-top:10px;}
.pctl{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:18px;}
#pq{flex:1 1 260px;max-width:360px;}
.pcount{font-size:13px;color:var(--ink-600);margin-top:12px;}
.pcount b{font-family:var(--font-display);font-size:16px;color:var(--ink);
  font-variant-numeric:tabular-nums;}

/* Dense table. A flex/grid child defaults to min-width:auto, which defeats
   overflow-x on a wide table - the wrapper needs min-width:0 explicitly. That
   trap is already documented in DESIGN-BRIEF.md; it applies here too. */
.twrap{margin-top:12px;min-width:0;overflow-x:auto;border:1px solid var(--border);
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
.c-desc{min-width:200px;}
.c-fn{white-space:nowrap;color:var(--ink-faint);font-size:12px;}
.c-alt{min-width:220px;}
.c-alt a{color:var(--primary);text-decoration:none;}
.c-alt a:hover{text-decoration:underline;}
.a-x{color:var(--ink-600);}          /* no repo url upstream - nothing to link to */
.a-q{color:var(--ink-faint);font-size:12px;}
.a-none{color:var(--ink-faint);font-style:italic;}
.c-act{white-space:nowrap;text-align:right;}
.c-act a{color:var(--primary);text-decoration:none;font-size:12px;}
.c-act a:hover{text-decoration:underline;}
.nores{font-size:14px;color:var(--ink-faint);margin-top:16px;}
/* An empty <th> leaves a screen reader announcing an unnamed column. The label
   is hidden rather than dropped. */
.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);
  white-space:nowrap;}
"""

BODY = """
<!-- No skip link here: theme.utility_bar() emits it, and it is prepended ahead
     of the topbar so it stays the FIRST focusable element. This page carried
     its own as well, which put two identical "Skip to content" links in the tab
     order and read the target out twice to a screen reader. Left over from the
     2026-08-13 chrome removal, when utility_bar() shrank to just the skip link
     and this page's copy stopped being the only one. -->
<div class="wrap">
  <main id="main">

  <section class="sec" style="margin-top:28px">
    <h1 style="font-size:30px;margin:0 0 12px">Proprietary software, and what could replace it</h1>
    <p class="lede">The catalogue lists government open source. This is the other side of it:
      <b>__NPROD__ proprietary products</b> governments buy, of which <b>__NALT__</b> have an
      open source alternative a government somewhere already publishes &mdash; <b>__NLINKS__</b>
      alternatives in all. The other <b>__NGAP__</b> are listed too, so a gap reads as a gap
      rather than as an oversight.</p>
    <p class="note">These mappings are <b>hand-curated and unverified</b>, and __NCURATED__ of
      the descriptions are written for this catalogue rather than taken from a source. Absence
      of a mapping is not evidence that no alternative exists. Anything that is not a
      like-for-like swap is qualified &mdash; a <i>paid tier</i> is usually a licence you stop
      renewing, a <i>hosted service</i> means you still need somewhere to run it, and
      <i>partial</i> or <i>adjacent</i> means real gaps or a changed workflow. __NDATA__ entries
      are content or data subscriptions, where open source cannot substitute the content at all.
      Machine readable at <a href="/products.json">/products.json</a>.</p>

    <div class="pctl">
      <input id="pq" class="fq" type="search" placeholder="Filter products, e.g. Dropbox"
        aria-label="Filter products">
      <select id="pf" class="sel" aria-label="Filter by function">
        <option value="">Any function</option>__FOPTS__
      </select>
      <button type="button" id="pa" class="tog" aria-pressed="true">Has a govoss alternative</button>
    </div>
    <p class="pcount"><b id="pn">__NALT__</b> of __NPROD__ products</p>

    <div class="twrap" id="twrap">
      <table class="ptab">
        <thead><tr>
          <th scope="col">Proprietary product</th>
          <th scope="col">Description</th>
          <th scope="col">Function</th>
          <th scope="col">Open source alternatives</th>
          <th scope="col"><span class="vh">See them in the catalog</span></th>
        </tr></thead>
        <tbody id="prows">__ROWS__</tbody>
      </table>
    </div>
    <p class="nores" id="nores" hidden>No product matches those filters.</p>
  </section>

  </main>
</div>
<script>
(function () {
  var q = document.getElementById('pq'), f = document.getElementById('pf'),
      a = document.getElementById('pa'), rows = document.getElementById('prows').children,
      wrap = document.getElementById('twrap'), none = document.getElementById('nores'),
      out = document.getElementById('pn');
  var onlyAlt = true;
  function apply() {
    var v = (q.value || '').trim().toLowerCase(), fn = f.value, n = 0;
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      var hit = (!v || r.getAttribute('data-n').indexOf(v) >= 0)
             && (!fn || r.getAttribute('data-f') === fn)
             && (!onlyAlt || r.getAttribute('data-a') === '1');
      r.hidden = !hit;
      if (hit) n++;
    }
    out.textContent = n.toLocaleString();
    // Hide the whole table when nothing matches - a bare header row over an
    // empty body reads as a broken table rather than as an empty result.
    wrap.hidden = n === 0;
    none.hidden = n > 0;
  }
  q.addEventListener('input', apply);
  f.addEventListener('change', apply);
  a.addEventListener('click', function () {
    onlyAlt = !onlyAlt;
    this.setAttribute('aria-pressed', onlyAlt ? 'true' : 'false');
    apply();
  });
  // A deep link must win over the default filters, or following #p-axon from
  // elsewhere lands on a row the "has an alternative" filter has just hidden.
  if (location.hash) {
    var t = document.getElementById(location.hash.slice(1));
    if (t && t.getAttribute('data-a') === '0') {
      onlyAlt = false;
      a.setAttribute('aria-pressed', 'false');
    }
    q.value = '';
  }
  apply();
  if (location.hash) {
    var el = document.getElementById(location.hash.slice(1));
    if (el) el.scrollIntoView();
  }
})();
</script>
"""

if __name__ == "__main__":
    build()
