#!/usr/bin/env python3
"""Build site/sources.html + site/sources.json from sources.py + live counts."""
import json, os, importlib.util, collections, time

OUT = os.path.dirname(os.path.abspath(__file__))
SITE = f"{OUT}/site"
_s = importlib.util.spec_from_file_location("sources", f"{OUT}/sources.py")
S = importlib.util.module_from_spec(_s); _s.loader.exec_module(S)

NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
STATUS_LABEL = {"ready": "ready to add", "retired": "retired", "broken": "broken",
                "no-code": "no code published", "wrong-shape": "not a code catalogue",
                "bot-protected": "bot-protected", "false-lead": "false lead", "none-found": "none exists",
                "needs-research": "needs research", "unresolved": "unresolved",
                "different-shape": "different shape"}


def esc(s):
    return ("" if s is None else str(s)).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build():
    cat = json.load(open(f"{OUT}/catalog.json"))
    active = [r for r in cat if not r.get("excluded")]
    # count by ORIGINAL source, so a merged entry credits every catalogue that asserted it
    counts = collections.Counter(
        s for r in active for s in (r.get("sources") or [r.get("source")]) if s)

    rows, sj = "", []
    for key, meta in sorted(S.SOURCES.items(), key=lambda kv: -counts.get(kv[0], 0)):
        n = counts.get(key, 0)
        sj.append({**meta, "key": key, "entries": n})
        rows += (
            f'<tr><td>{meta["flag"]} <b>{esc(meta["country"])}</b></td>'
            f'<td><a href="{esc(meta["site"])}" target="_blank" rel="noopener">'
            f'{esc(meta["label"])}</a></td>'
            f'<td class="num">{n}</td>'
            f'<td class="mono dim">{esc(meta["route"])}</td>'
            f'<td class="dim">{esc(meta.get("claim"))}</td>'
            f'<td class="mono"><a href="{esc(meta["api"])}" target="_blank" rel="noopener">endpoint</a></td>'
            f'</tr>'
            + (f'<tr class="note"><td></td><td colspan="5" class="dim">{esc(meta["note"])}</td></tr>'
               if meta.get("note") else ""))

    srows = ""
    for e in S.SURVEY:
        srows += (
            f'<tr><td>{e["flag"]} <b>{esc(e["country"])}</b></td>'
            f'<td><a href="{esc(e["url"])}" target="_blank" rel="noopener">{esc(e["name"])}</a></td>'
            f'<td><span class="st st-{esc(e["status"])}">{esc(STATUS_LABEL.get(e["status"], e["status"]))}</span></td></tr>'
            f'<tr class="note"><td></td><td colspan="2" class="dim">{esc(e["detail"])}</td></tr>')

    n_countries = len({m['country'] for m in S.SOURCES.values()})
    json.dump({"generated_at": NOW, "ingested": sj, "survey": S.SURVEY},
              open(f"{SITE}/sources.json", "w"), indent=1)

    page = f"""<title>govoss-catalog &mdash; sources</title>
<link rel="alternate" type="application/json" href="/sources.json" title="This page as JSON">
<style>
:root {{ --paper:#F7F8F7; --raised:#EDEFEE; --ink:#171A19; --slate:#626B67;
  --hairline:#DBDFDC; --accent:#0F6B5C; --accent-dim:#E0EEEA;
  --good:#0F6B5C; --warn:#8A5A00; --bad:#A32A22;
  --sans:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace; }}
@media (prefers-color-scheme:dark) {{ :root {{ --paper:#0E110F; --raised:#171B18;
  --ink:#E3E8E4; --slate:#939C97; --hairline:#262C28; --accent:#56C0AB;
  --accent-dim:#152420; --good:#56C0AB; --warn:#D9A43F; --bad:#EF7A70; }} }}
:root[data-theme="dark"] {{ --paper:#0E110F; --raised:#171B18; --ink:#E3E8E4;
  --slate:#939C97; --hairline:#262C28; --accent:#56C0AB; --accent-dim:#152420;
  --good:#56C0AB; --warn:#D9A43F; --bad:#EF7A70; }}
:root[data-theme="light"] {{ --paper:#F7F8F7; --raised:#EDEFEE; --ink:#171A19;
  --slate:#626B67; --hairline:#DBDFDC; --accent:#0F6B5C; --accent-dim:#E0EEEA;
  --good:#0F6B5C; --warn:#8A5A00; --bad:#A32A22; }}
body {{ background:var(--paper); color:var(--ink); font-family:var(--sans);
  font-size:15px; line-height:1.55; -webkit-font-smoothing:antialiased; }}
.wrap {{ max-width:1000px; margin:0 auto; padding:2rem 1.1rem 5rem;
  display:flex; flex-direction:column; gap:2rem; }}
h1 {{ font-size:clamp(1.4rem,3.5vw,1.85rem); font-weight:640; letter-spacing:-.02em; margin:0; }}
h2 {{ font-size:1.08rem; font-weight:640; margin:0; padding-bottom:.4rem;
  border-bottom:1px solid var(--hairline); }}
p {{ margin:0; max-width:74ch; }} .dim {{ color:var(--slate); }} .mono {{ font-family:var(--mono); }}
a {{ color:var(--accent); }}
.num {{ font-family:var(--mono); font-variant-numeric:tabular-nums; text-align:right; }}
section {{ display:flex; flex-direction:column; gap:.8rem; }}
.scroller {{ overflow-x:auto; border:1px solid var(--hairline); border-radius:4px; }}
table {{ border-collapse:collapse; width:100%; font-size:.88rem; }}
th,td {{ text-align:left; padding:.5rem .8rem; border-bottom:1px solid var(--hairline); }}
thead th {{ font-family:var(--mono); font-size:.63rem; letter-spacing:.1em;
  text-transform:uppercase; color:var(--slate); background:var(--raised); font-weight:500;
  white-space:nowrap; }}
tr.note td {{ border-bottom:1px solid var(--hairline); font-size:.83rem;
  padding-top:0; padding-bottom:.7rem; }}
tr.note {{ }}
.st {{ font-family:var(--mono); font-size:.65rem; letter-spacing:.07em; text-transform:uppercase;
  padding:.12rem .45rem; border-radius:3px; white-space:nowrap; }}
.st-ready {{ color:var(--good); border:1px solid var(--good); }}
.st-retired,.st-broken,.st-no-code {{ color:var(--bad); border:1px solid var(--bad); }}
.st-needs-research,.st-unresolved {{ color:var(--warn); border:1px solid var(--warn); }}
.st-different-shape,.st-wrong-shape {{ color:var(--slate); border:1px solid var(--hairline); }}
.st-bot-protected {{ color:var(--warn); border:1px solid var(--warn); }}
.st-false-lead,.st-none-found {{ color:var(--slate); border:1px dashed var(--slate); }}
.bar {{ background:var(--accent-dim); border-left:3px solid var(--accent); border-radius:2px;
  padding:.7rem 1rem; font-size:.9rem; }}
footer {{ border-top:1px solid var(--hairline); padding-top:1rem; color:var(--slate); font-size:.82rem; }}
:focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}
</style>

<div class="wrap">
  <header>
    <h1>Sources</h1>
    <p class="dim">Every entry in this catalogue comes from one of the national catalogues
       below, harvested first-hand. Counts credit <em>every</em> catalogue that asserted an
       entry, so they sum to more than the {len(active)} de-duplicated entries.</p>
    <p class="bar">Machine-readable: <a href="/sources.json"><code>/sources.json</code></a>
       &middot; <a href="/">catalogue</a> &middot; <a href="/status.html">status</a>
       &middot; <a href="/llms.txt">llms.txt</a></p>
  </header>

  <section>
    <h2>Ingested &mdash; {len(S.SOURCES)} catalogues, {n_countries} countries</h2>
    <div class="scroller"><table>
      <thead><tr><th></th><th>Catalogue</th><th class="num">Entries</th><th>Access route</th>
        <th>What it asserts</th><th>Data</th></tr></thead>
      <tbody>{rows}</tbody>
    </table></div>
  </section>

  <section>
    <h2>Surveyed but not ingested</h2>
    <p class="dim">Found while looking beyond Europe. A verified dead end is worth recording:
       it stops the next person re-probing code.gov and reaching the same conclusion.</p>
    <div class="scroller"><table>
      <thead><tr><th></th><th>Catalogue</th><th>Status</th></tr></thead>
      <tbody>{srows}</tbody>
    </table></div>
  </section>

  <section>
    <h2>Deliberately not a source</h2>
    <p>The EU's own
      <a href="https://interoperable-europe.ec.europa.eu/eu-oss-catalogue" target="_blank" rel="noopener">Open
      Source Solutions Catalogue</a> federates most of the above, and is <b>not</b> used here.
      Its pager, facets and keyword search all ignore the query string, so only 20 of its 1,084
      solutions are reachable by any public route. It also ingests France's 19-entry curated
      list rather than the French sources themselves, so syndicating it would inherit that gap
      permanently.</p>
  </section>

  <footer>Generated {esc(NOW)}. Source definitions live in <span class="mono">sources.py</span>,
    shared by the page, the JSON export and this table so a URL cannot disagree between them.</footer>
</div>
"""
    page = page.encode("ascii", "xmlcharrefreplace").decode()
    open(f"{SITE}/sources.html", "w").write(page)
    print(f"sources page: {len(S.SOURCES)} ingested, {len(S.SURVEY)} surveyed "
          f"({len(page)/1024:.0f} KB) + sources.json")
    for k, m in S.SOURCES.items():
        if counts.get(k, 0) == 0:
            print(f"   !! {k} has 0 entries but is listed as ingested")


if __name__ == "__main__":
    build()
