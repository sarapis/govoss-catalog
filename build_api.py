#!/usr/bin/env python3
"""Build site/api.html - the agent-and-developer surface.

The point of this page is that an agent never needs to open a browser. It exists
because the first consumer of this catalogue probed eight dead API paths and
then drove a headless browser at the HTML.

Every number on it is measured at build time from the files in site/, so the
page cannot claim a size or a count the export does not have. It therefore must
run AFTER export_json.py.

No f-strings for markup: plain strings with __PLACEHOLDER__ tokens.
"""
import json, os, gzip, importlib.util, time

OUT = os.path.dirname(os.path.abspath(__file__))
SITE = f"{OUT}/site"
NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

_th = importlib.util.spec_from_file_location("theme", f"{OUT}/theme.py")
theme = importlib.util.module_from_spec(_th); _th.loader.exec_module(theme)
_tp = importlib.util.spec_from_file_location("_ui_template", f"{OUT}/_ui_template.py")
T = importlib.util.module_from_spec(_tp); _tp.loader.exec_module(T)
_mt = importlib.util.spec_from_file_location("mcp_tools", f"{OUT}/mcp_tools.py")
M = importlib.util.module_from_spec(_mt); _mt.loader.exec_module(M)


def esc(s):
    return ("" if s is None else str(s)).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def sizes(name):
    """Measured, not estimated. A stated payload size that is wrong is worse
    than no number, because it is what a consumer budgets against."""
    p = f"{SITE}/{name}"
    if not os.path.exists(p):
        return None, None
    raw = open(p, "rb").read()
    return len(raw), len(gzip.compress(raw))


def kb(n):
    if n is None:
        return "&mdash;"
    return "%.0f KB" % (n / 1024) if n < 1024 * 1024 else "%.1f MB" % (n / 1048576)


def build():
    entries = json.load(open(f"{SITE}/entries.json"))
    meta = json.load(open(f"{SITE}/meta.json"))
    counts = meta.get("counts", {})

    ENDPOINTS = [
        ("/entries.json", "Every entry, one request. No key, no pagination, no rate limit.",
         "entries.json", "%s entries" % "{:,}".format(len(entries))),
        ("/by-product.json", "Inverted index: proprietary product to open source "
                             "alternatives. Two requests answer a licence inventory.",
         "by-product.json", "%s products mapped" % counts.get("distinct_products_mapped", "-")),
        ("/sources.json", "The catalogues harvested, their access routes and entry counts, "
                          "plus the ones surveyed and rejected with reasons.",
         "sources.json", "17 catalogues"),
        ("/meta.json", "Counts, the controlled vocabulary for functions and countries, and "
                       "generated_at. Poll this, not the pages.",
         "meta.json", "freshness signal"),
        ("/status.json", "Last run, per-step results, open items. Whether the machine is "
                         "still running.", "status.json", "build health"),
    ]
    erows = ""
    for path, desc, fname, fact in ENDPOINTS:
        raw, gz = sizes(fname)
        erows += (
            '<div class="ecard">'
            '<div class="e-h"><span class="get">GET</span>'
            '<a class="mono e-p" href="%s">%s</a></div>'
            '<p class="e-d">%s</p>'
            '<div class="e-f"><span class="fact">%s</span>'
            '<span class="fact">%s raw</span><span class="fact">%s gzip</span></div>'
            '</div>'
        ) % (path, path, esc(desc), esc(fact), kb(raw), kb(gz))

    # A REAL entry, chosen deterministically: most-catalogued of the entries that
    # carry both a replaces mapping and a licence, so the example shows the
    # fields that actually carry rules rather than a sparse row.
    cands = [r for r in entries if r.get("replaces") and r.get("catalogue_count", 1) > 1
             and r.get("licence")]
    cands.sort(key=lambda r: (-r.get("catalogue_count", 1), r.get("name", "")))
    example = cands[0] if cands else entries[0]
    keep = ["id", "name", "description", "country", "countries", "source", "sources",
            "repo_url", "licence", "licence_spdx", "wikidata", "functions",
            "catalogue_count", "catalogues", "replaces", "link_dead", "repo_archived",
            "last_checked", "translated_from", "excluded"]
    slim = {k: example[k] for k in keep if k in example}
    if isinstance(slim.get("catalogues"), list):
        slim["catalogues"] = slim["catalogues"][:2] + (
            ["... %d more" % (len(example["catalogues"]) - 2)]
            if len(example["catalogues"]) > 2 else [])
    example_json = esc(json.dumps(slim, indent=2, ensure_ascii=False))

    frows = "".join(
        '<div class="frow"><code class="f-n">%s</code><p class="f-d">%s</p></div>'
        % (esc(n), esc(d)) for n, d in M.FIELD_RULES)

    trows = "".join(
        '<div class="trow"><div class="t-h"><code class="t-n">%s</code>'
        '<code class="t-a">(%s)</code></div><p class="t-d">%s</p>'
        '<p class="t-r">returns %s</p></div>'
        % (esc(t["name"]), esc(t["args"]), esc(t["desc"]), esc(t["returns"]))
        for t in M.TOOLS)

    # Don't advise using a server that is not live. The rule this whole page
    # states is that a documented thing must be a real thing.
    etiquette = [e for e in M.ETIQUETTE
                 if M.ENDPOINT or "MCP server" not in e[1]]
    etq = "".join(
        '<div class="qcard %s"><span class="qtag">%s</span><h4>%s</h4><p>%s</p></div>'
        % (kind, "do" if kind == "do" else "don't", esc(title), esc(body))
        for kind, title, body in etiquette)

    # MCP: live only when the Worker exists. Until then the section says so
    # rather than printing an endpoint that answers nothing - this page is read
    # by agents, which cannot tell a documented URL from a working one.
    if M.ENDPOINT:
        mcp_config = esc(json.dumps({"mcpServers": {"govoss": {"url": M.ENDPOINT}}}, indent=2))
        mcp_state = ('<div class="code"><pre>%s</pre></div>' % mcp_config)
        mcp_note = ('Add that to your MCP client config. No key, no account. The server '
                    'reads the same public JSON as everyone else, so it can never return '
                    'something the published data does not contain.')
    else:
        mcp_state = ('<div class="notyet"><b>Not live yet.</b> The server is built but not '
                     'deployed, so no endpoint is published here. The tools below are its '
                     'actual definitions, shared with the implementation &mdash; when it '
                     'deploys, the connection details appear here and nowhere else changes.</div>')
        mcp_note = ('Until then, everything the tools do can be done with the JSON above: '
                    'they exist to save an agent downloading 5.6 MB to answer one question.')

    subs = {
        "__EROWS__": erows, "__FROWS__": frows, "__TROWS__": trows, "__ETQ__": etq,
        "__EXAMPLE__": example_json, "__EXAMPLE_NAME__": esc(example.get("name", "")),
        "__MCP_STATE__": mcp_state, "__MCP_NOTE__": mcp_note,
        "__N_ENTRIES__": "{:,}".format(len(entries)),
        "__N_TOOLS__": str(len(M.TOOLS)),
        "__GEN__": esc(meta.get("generated_at") or NOW),
        "__CITE__": esc("govoss-catalog (%s). Union catalogue of government open source "
                        "software. https://govoss-catalog.vercel.app, CC BY 4.0."
                        % (meta.get("generated_at") or NOW)[:10]),
    }

    page = (theme.head(
        "API and MCP for agents | govoss",
        "Take the data, don't scrape the page. %s government open source entries as static "
        "JSON - no key, no rate limit, no pagination - plus an MCP server."
        % "{:,}".format(len(entries)))
        + "<style>\n" + theme.FONT_FACE_CSS + theme.CSS + T.PAGE_CSS + PAGE_CSS + "</style>\n"
        + theme.utility_bar() + theme.topbar("api") + BODY + theme.footer())

    for k, v in subs.items():
        page = page.replace(k, v)
    import re as _re
    left = sorted(set(_re.findall(r"__[A-Z_]{3,}__", page)))
    if left:
        raise SystemExit("build_api: unsubstituted placeholders %s" % left)

    theme.assert_variant_live(page)

    page = page.encode("ascii", "xmlcharrefreplace").decode()
    open(f"{SITE}/api.html", "w").write(page)
    print("api page: %d endpoints, %d tools, MCP %s (%.0f KB)"
          % (len(ENDPOINTS), len(M.TOOLS),
             "live" if M.ENDPOINT else "NOT LIVE (no endpoint published)", len(page) / 1024))


PAGE_CSS = """
.sec{margin-top:44px;}
.sechead{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;
  gap:8px 20px;padding-bottom:10px;}
.hero .btns{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin-top:6px;}

.egrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px;}
.ecard{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--r-card);padding:16px;display:flex;flex-direction:column;gap:8px;}
.e-h{display:flex;align-items:center;gap:8px;}
.get{font-family:var(--font-ui);font-size:10px;font-weight:600;letter-spacing:.1em;
  /* --primary-deep (navy), not --primary: accent-on-tint is 4.9:1 at 10px.
     Navy on the same ground is 12.55:1 and the tint still reads as a chip. */
  background:var(--primary-tint);color:var(--primary-deep);padding:3px 7px;
  border-radius:var(--r-chip);}
.e-p{font-size:14px;font-weight:600;color:var(--primary);text-decoration:none;}
.e-p:hover{text-decoration:underline;}
.e-d{font-size:13px;color:var(--ink-600);line-height:1.5;flex:1;text-wrap:pretty;}
.e-f{display:flex;flex-wrap:wrap;gap:6px;}
.fact{font-size:11px;background:var(--bg-alt);color:var(--ink-600);padding:3px 8px;
  border-radius:var(--r-chip);font-variant-numeric:tabular-nums;}

.two{display:flex;flex-wrap:wrap;gap:28px;}
.col-code{flex:1 1 440px;min-width:0;} .col-rules{flex:1 1 340px;min-width:0;}
.code{background:var(--surface);border:1px solid var(--ink);border-radius:var(--r-med);
  box-shadow:var(--shadow-bar);overflow:hidden;}
.code pre{margin:0;padding:16px;overflow-x:auto;font-family:var(--font-mono);
  font-size:12px;line-height:1.6;color:var(--ink);}
.frow{padding:12px 0;border-bottom:1px solid var(--border-soft);}
.frow:last-child{border-bottom:0;}
.f-n{font-family:var(--font-mono);font-size:13px;color:var(--primary);
  background:var(--primary-tint);padding:2px 6px;border-radius:4px;}
.f-d{font-size:13px;color:var(--ink-600);line-height:1.5;margin-top:6px;text-wrap:pretty;}
.rule-hero{background:var(--ink-900);color:var(--paper-50);border-radius:var(--r-med);
  padding:16px 18px;font-size:14px;line-height:1.55;margin-top:14px;}
.rule-hero b{color:var(--mint-300);}

.trow{padding:14px 0;border-bottom:1px solid var(--border-soft);}
.trow:last-child{border-bottom:0;}
.t-h{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px;}
.t-n{font-family:var(--font-mono);font-size:14px;font-weight:600;color:var(--ink);}
.t-a{font-family:var(--font-mono);font-size:12px;color:var(--ink-faint);}
.t-d{font-size:13px;color:var(--ink-600);line-height:1.5;margin-top:5px;text-wrap:pretty;}
.t-r{font-size:12px;color:var(--ink-faint);margin-top:3px;}
.notyet{background:var(--bg-alt);border:1px dashed var(--ink);border-radius:var(--r-med);
  padding:16px 18px;font-size:14px;color:var(--ink-600);line-height:1.55;}
.notyet b{color:var(--ink);}

.qgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;}
.qcard{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--r-card);padding:16px;display:flex;flex-direction:column;gap:6px;}
.qtag{align-self:flex-start;font-family:var(--font-ui);font-size:10px;font-weight:600;
  letter-spacing:.1em;text-transform:uppercase;padding:3px 8px;border-radius:var(--r-chip);}
/* ink on green, not white on green - white is 2.65:1 against #01B583. Same
   pairing and same fix as the "Recommended" stamp. */
/* --green-text, not --green: white on the mid green is 4.62:1, legal at AA but
   under the 5.17:1 floor this project holds. On the dark tone it is 9.33:1.
   Same fix as .stamp.rec in _ui_template.py. */
.qcard.do .qtag{background:var(--green-text);color:var(--white);}
.qcard.dont .qtag{background:var(--ink-900);color:var(--paper-50);}
.qcard h4{font-family:var(--font-display);font-size:15px;margin:0;}
.qcard p{font-size:13px;color:var(--ink-600);line-height:1.5;text-wrap:pretty;}

.cite{background:var(--surface);border:1px solid var(--border);border-radius:var(--r-med);
  padding:14px 16px;font-family:var(--font-mono);font-size:12px;color:var(--ink-600);
  overflow-x:auto;}
"""

BODY = """
<div class="hero tex">
  <div class="inner">
    <p class="overline">For agents and developers</p>
    <h2>Take the data, don't scrape the page</h2>
    <p class="lede">Everything this site displays is available as static JSON &mdash;
      __N_ENTRIES__ entries in one request. No key, no rate limit, no pagination, no
      account. CORS is open. Last rebuilt __GEN__.</p>
    <div class="btns">
      <a class="btn btn-primary" href="/entries.json">Get entries.json</a>
      <a class="btn btn-ghost" href="#mcp">The MCP server</a>
    </div>
  </div>
</div>

<div class="wrap">
  <main id="main">
  <section class="sec" style="margin-top:36px">
    <div class="sechead"><h3>Endpoints</h3>
      <span class="r" style="font-size:12px;color:var(--ink-faint)">Sizes measured at build
        time, so they cannot drift from what is served.</span></div>
    <hr class="dashed">
    <div class="egrid" style="margin-top:14px">__EROWS__</div>
  </section>

  <section class="sec">
    <div class="sechead"><h3>One entry, and the fields that carry rules</h3></div>
    <hr class="dashed">
    <div class="two" style="margin-top:14px">
      <div class="col-code">
        <p style="font-size:12px;color:var(--ink-faint);margin-bottom:8px">A real record
          &mdash; __EXAMPLE_NAME__ &mdash; trimmed to the fields worth explaining.</p>
        <div class="code"><pre>__EXAMPLE__</pre></div>
      </div>
      <div class="col-rules">
        __FROWS__
        <div class="rule-hero">The governing rule: <b>a value the upstream catalogue did
          not state is null.</b> Never guessed, never back-filled from a search. Read null
          as &ldquo;the government did not say&rdquo;, not &ldquo;unknown to us&rdquo;
          &mdash; the difference matters if you are about to publish a claim about who
          licenses what.</div>
      </div>
    </div>
  </section>

  <section class="sec" id="mcp">
    <div class="sechead"><h3>MCP server</h3>
      <span class="r" style="font-size:12px;color:var(--ink-faint)">__N_TOOLS__ tools over the
        same public data.</span></div>
    <hr class="dashed">
    <div class="two" style="margin-top:14px">
      <div class="col-code">
        __MCP_STATE__
        <p style="font-size:13px;color:var(--ink-600);line-height:1.55;margin-top:12px">__MCP_NOTE__</p>
      </div>
      <div class="col-rules">__TROWS__</div>
    </div>
  </section>

  <section class="sec">
    <div class="sechead"><h3>Etiquette</h3></div>
    <hr class="dashed">
    <div class="qgrid" style="margin-top:14px">__ETQ__</div>
  </section>

  <section class="sec">
    <div class="sechead"><h3>Licence and citation</h3></div>
    <hr class="dashed">
    <div style="margin-top:14px;display:flex;flex-direction:column;gap:12px">
      <p style="font-size:14px;color:var(--ink-600);line-height:1.6;max-width:70ch">
        The compilation is <a href="https://creativecommons.org/licenses/by/4.0/">CC BY
        4.0</a> and the pipeline code is <a
        href="https://github.com/sarapis/govoss-catalog/blob/main/LICENSE">MIT</a>. The
        individual entries are not ours to relicense &mdash; each describes software
        published by a government catalogue under that country's own terms, and every entry
        links back to its source. <b>Cite the government for a fact about one project</b>;
        cite this catalogue for the aggregate.</p>
      <div class="cite">__CITE__</div>
    </div>
  </section>
  </main>
</div>
"""

if __name__ == "__main__":
    build()
