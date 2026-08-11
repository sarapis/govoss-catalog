#!/usr/bin/env python3
"""Generate a self-contained browsable page from catalog.json."""
import json, os, collections, html, importlib.util

OUT = os.path.dirname(os.path.abspath(__file__))
c = json.load(open(f"{OUT}/catalog.json"))
_spec = importlib.util.spec_from_file_location("taxonomy", f"{OUT}/taxonomy.py")
_tax = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_tax)
FUNCTIONS = _tax.FUNCTIONS

# Liveness is surfaced ON THE PAGE, not just in liveness.json — a monitor whose
# output lives only in a file nobody opens is the same failure as no monitor.
LIVE = {}
if os.path.exists(f"{OUT}/liveness.json"):
    LIVE = json.load(open(f"{OUT}/liveness.json")).get("repos", {})

SRC_LABEL = {
    "IT/developers-italia": "Developers Italia",
    "FR/sill": "SILL",
    "FR/awesome-codegouvfr": "awesome-codegouvfr",
    "DE/openCode": "openCode",
    "BE/iMio": "iMio",
    "SE/offentligkod": "Offentligkod",
    "FI/avoinkoodi": "Avoinkoodi",
    "EU/code.europa.eu": "code.europa.eu",
}
CLAIM = {
    "IT/developers-italia": "built for public administration",
    "DE/openCode": "built for public administration",
    "EU/code.europa.eu": "built by EU institutions",
    "BE/iMio": "built by Walloon municipalities",
    "SE/offentligkod": "in use by Swedish public bodies",
    "FI/avoinkoodi": "Finnish public-sector project",
    "FR/awesome-codegouvfr": "curated French public-sector",
    "FR/sill": "recommended to public agents",
}

rows = []
for r in c:
    rows.append({
        "n": r.get("name") or "(unnamed)",
        "c": r.get("country"),
        "s": SRC_LABEL.get(r.get("source"), r.get("source")),
        "t": r.get("tier"),
        "l": r.get("license") or "",
        "d": (r.get("short_desc") or "")[:230],
        "u": r.get("repo") or "",
        "h": r.get("landing") or "",
        "st": r.get("dev_status") or "",
        "o": r.get("repo_owner") or "",
        "g": (r.get("categories") or [])[:4],
        "ub": len(r.get("used_by") or []),
        "rec": 1 if r.get("recommended_for_gov") else 0,
        "fx": r.get("functions") or [],
        "tr": 1 if r.get("translated") else 0,
        "sl": r.get("desc_src_lang") or "",
        "qid": r.get("wikidata") or "",
        "ex": r.get("exclude_reason") or "",
        # dead_since is only set after 2 consecutive dead observations, so the
        # page never shows a one-off 404 as "repo gone"
        "lv": (lambda v: "dead" if v.get("dead_since")
                    else ("archived" if v.get("archived") else ""))(
                    LIVE.get(r.get("repo_key") or "", {})),
    })
rows.sort(key=lambda x: (x["n"] or "").lower())
n_ex = sum(1 for r in rows if r["ex"])

# facet counts describe the DEFAULT view (excluded hidden), or the chips would
# advertise entries the list will not show
_inc = [r for r in rows if not r["ex"]]
countries = collections.Counter(r["c"] for r in _inc)
sources = collections.Counter(r["s"] for r in _inc)
licenses = collections.Counter(r["l"] for r in _inc if r["l"])
n_pc = sum(1 for r in _inc if r["t"] == "publiccode")
n_repos = len({r["u"] for r in _inc if r["u"]})
n_tr = sum(1 for r in _inc if r["tr"])
n_en = sum(1 for r in _inc if r["d"] and not r["tr"])
funcs = collections.Counter(f for r in _inc for f in r["fx"])
n_dead = sum(1 for r in _inc if r["lv"] == "dead")
FFACETS = json.dumps([[k, FUNCTIONS[k], n] for k, n in funcs.most_common()])

DATA = json.dumps(rows, separators=(",", ":"))
CFACETS = json.dumps(sorted(countries.items(), key=lambda x: -x[1]))
SFACETS = json.dumps(sorted(sources.items(), key=lambda x: -x[1]))
LOPTS = "".join(f'<option value="{html.escape(k)}">{html.escape(k)} ({v})</option>'
                for k, v in licenses.most_common()
                ).encode("ascii", "xmlcharrefreplace").decode()

PAGE = f"""<title>European public-sector open source &mdash; aggregated catalogue</title>
<style>
:root {{
  --paper:#F7F8F7; --raised:#EDEFEE; --sunk:#E4E7E5;
  --ink:#171A19; --slate:#626B67; --hairline:#DBDFDC;
  --accent:#0F6B5C; --accent-dim:#E0EEEA;
  --stable:#0F6B5C; --beta:#8A5A00; --dev:#1F4E8C; --obsolete:#A32A22; --concept:#5A5F7A;
  --sans:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",sans-serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
}}
@media (prefers-color-scheme:dark) {{
  :root {{
    --paper:#0E110F; --raised:#171B18; --sunk:#1F2521;
    --ink:#E3E8E4; --slate:#939C97; --hairline:#262C28;
    --accent:#56C0AB; --accent-dim:#152420;
    --stable:#56C0AB; --beta:#D9A43F; --dev:#7FA9E0; --obsolete:#EF7A70; --concept:#9AA1BC;
  }}
}}
:root[data-theme="dark"] {{
  --paper:#0E110F; --raised:#171B18; --sunk:#1F2521;
  --ink:#E3E8E4; --slate:#939C97; --hairline:#262C28;
  --accent:#56C0AB; --accent-dim:#152420;
  --stable:#56C0AB; --beta:#D9A43F; --dev:#7FA9E0; --obsolete:#EF7A70; --concept:#9AA1BC;
}}
:root[data-theme="light"] {{
  --paper:#F7F8F7; --raised:#EDEFEE; --sunk:#E4E7E5;
  --ink:#171A19; --slate:#626B67; --hairline:#DBDFDC;
  --accent:#0F6B5C; --accent-dim:#E0EEEA;
  --stable:#0F6B5C; --beta:#8A5A00; --dev:#1F4E8C; --obsolete:#A32A22; --concept:#5A5F7A;
}}

body {{ background:var(--paper); color:var(--ink); font-family:var(--sans);
       font-size:15px; line-height:1.5; -webkit-font-smoothing:antialiased; }}
.wrap {{ max-width:1120px; margin:0 auto; padding:2rem 1.1rem 5rem; }}

h1 {{ font-size:clamp(1.4rem,3.4vw,1.9rem); font-weight:640; letter-spacing:-.02em;
      margin:0; text-wrap:balance; }}
.sub {{ color:var(--slate); margin:.5rem 0 0; max-width:70ch; font-size:.95rem; }}

.stats {{ display:flex; flex-wrap:wrap; gap:.1rem 2.2rem; margin:1.4rem 0 0;
          padding:.9rem 0; border-top:1px solid var(--hairline);
          border-bottom:1px solid var(--hairline); }}
.stat {{ display:flex; flex-direction:column; gap:.1rem; padding:.2rem 0; }}
.stat b {{ font-family:var(--mono); font-size:1.32rem; font-weight:600;
           font-variant-numeric:tabular-nums; letter-spacing:-.02em; }}
.stat span {{ font-family:var(--mono); font-size:.63rem; letter-spacing:.11em;
              text-transform:uppercase; color:var(--slate); }}

.controls {{ position:sticky; top:0; z-index:20; background:var(--paper);
             padding:1rem 0 .8rem; border-bottom:1px solid var(--hairline);
             margin-bottom:.2rem; display:flex; flex-direction:column; gap:.75rem; }}
.row1 {{ display:flex; flex-wrap:wrap; gap:.6rem; align-items:center; }}
input[type=search], select {{ font-family:inherit; font-size:.9rem; color:var(--ink);
  background:var(--raised); border:1px solid var(--hairline); border-radius:5px;
  padding:.5rem .7rem; }}
input[type=search] {{ flex:1 1 15rem; min-width:0; }}
input[type=search]::placeholder {{ color:var(--slate); }}
select {{ cursor:pointer; }}

.chips {{ display:flex; flex-wrap:wrap; gap:.35rem; }}
.tog {{ display:flex; align-items:center; gap:.4rem; font-family:var(--mono);
  font-size:.72rem; color:var(--slate); letter-spacing:.03em; white-space:nowrap;
  cursor:pointer; }}
.pill.ex {{ color:var(--concept); border:1px dashed var(--concept); }}
.chip {{ font-family:var(--mono); font-size:.74rem; letter-spacing:.03em;
  background:var(--raised); color:var(--slate); border:1px solid var(--hairline);
  border-radius:20px; padding:.24rem .62rem; cursor:pointer; }}
.chip .k {{ color:var(--ink); font-weight:600; }}
.chip[aria-pressed="true"] {{ background:var(--accent); border-color:var(--accent);
  color:var(--paper); }}
.chip[aria-pressed="true"] .k {{ color:var(--paper); }}

.count {{ font-family:var(--mono); font-size:.75rem; color:var(--slate);
          letter-spacing:.04em; padding:.5rem 0 .3rem; }}
.count b {{ color:var(--ink); font-variant-numeric:tabular-nums; }}

ul.list {{ list-style:none; margin:0; padding:0; display:flex; flex-direction:column; }}
li.item {{ border-bottom:1px solid var(--hairline); padding:.9rem .2rem;
           display:grid; grid-template-columns:2.6rem 1fr; gap:.1rem .8rem; }}
li.item:hover {{ background:var(--raised); }}
.cc {{ font-family:var(--mono); font-size:.7rem; font-weight:600; letter-spacing:.06em;
       color:var(--accent); padding-top:.18rem; }}
.body {{ min-width:0; display:flex; flex-direction:column; gap:.3rem; }}
.title {{ display:flex; flex-wrap:wrap; align-items:baseline; gap:.5rem; }}
.title a {{ color:var(--ink); font-weight:600; font-size:1rem; text-decoration:none;
            border-bottom:1px solid transparent; }}
.title a:hover {{ border-bottom-color:var(--accent); color:var(--accent); }}
.pill {{ font-family:var(--mono); font-size:.63rem; letter-spacing:.07em;
         text-transform:uppercase; padding:.12rem .42rem; border-radius:3px;
         background:var(--sunk); color:var(--slate); white-space:nowrap; }}
.pill.stable{{color:var(--stable)}} .pill.beta{{color:var(--beta)}}
.pill.development{{color:var(--dev)}} .pill.obsolete{{color:var(--obsolete)}}
.pill.concept{{color:var(--concept)}}
.pill.rec {{ background:var(--accent-dim); color:var(--accent); }}
.pill.dead {{ color:var(--obsolete); border:1px solid var(--obsolete); }}
.desc {{ color:var(--slate); font-size:.88rem; max-width:82ch; }}
.foot {{ display:flex; flex-wrap:wrap; gap:.35rem .9rem; font-family:var(--mono);
         font-size:.7rem; color:var(--slate); letter-spacing:.02em; }}
.foot .src {{ color:var(--ink); }}
.foot a {{ color:var(--slate); text-decoration:none; border-bottom:1px solid var(--hairline);
           word-break:break-all; }}
.foot a:hover {{ color:var(--accent); border-bottom-color:var(--accent); }}

.more {{ margin:1.4rem auto 0; display:block; font-family:var(--mono); font-size:.78rem;
  letter-spacing:.06em; text-transform:uppercase; background:none; color:var(--accent);
  border:1px solid var(--hairline); border-radius:5px; padding:.6rem 1.3rem; cursor:pointer; }}
.more:hover {{ background:var(--accent-dim); border-color:var(--accent); }}
.empty {{ padding:3rem 0; color:var(--slate); text-align:center; }}
footer {{ margin-top:2.5rem; padding-top:1.1rem; border-top:1px solid var(--hairline);
          color:var(--slate); font-size:.8rem; max-width:78ch; }}
:focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}
@media (max-width:620px) {{ li.item {{ grid-template-columns:1fr; }} .cc {{ padding:0; }} }}
</style>

<div class="wrap">
  <h1>European public-sector open source</h1>
  <p class="sub">Eight national catalogues, harvested first-hand and joined on repository URL.
     Every entry asserts fitness for government use &mdash; either a government built it for
     government work, or a government recommends it.</p>

  <div class="stats">
    <div class="stat"><b>{len(_inc)}</b><span>entries</span></div>
    <div class="stat"><b>{n_repos}</b><span>distinct repos</span></div>
    <div class="stat"><b>{len(countries)}</b><span>countries</span></div>
    <div class="stat"><b>{n_pc}</b><span>with publiccode.yml</span></div>
    <div class="stat"><b>{n_en + n_tr}</b><span>in English</span></div>
    <div class="stat"><b>{len(funcs)}</b><span>functions</span></div>
    <div class="stat"><b>{n_dead}</b><span>dead links</span></div>
  </div>

  <div class="controls">
    <div class="row1">
      <input type="search" id="q" placeholder="Search name, description, owner, category&hellip;"
             autocomplete="off" aria-label="Search catalogue">
      <select id="lic" aria-label="Filter by licence">
        <option value="">All licences</option>{LOPTS}
      </select>
      <select id="sort" aria-label="Sort">
        <option value="name">A&ndash;Z</option>
        <option value="adopters">Most adopters</option>
        <option value="country">By country</option>
      </select>
      <label class="tog"><input type="checkbox" id="showex"> show {n_ex} filtered</label>
      <select id="lv" aria-label="Filter by repository state">
        <option value="">Any repo state</option>
        <option value="ok">Live repos only</option>
        <option value="dead">Dead links only</option>
        <option value="archived">Archived only</option>
      </select>
    </div>
    <div class="chips" id="fc" role="group" aria-label="Filter by function"></div>
    <div class="chips" id="cc" role="group" aria-label="Filter by country"></div>
    <div class="chips" id="sc" role="group" aria-label="Filter by source catalogue"></div>
  </div>

  <div class="count" id="count"></div>
  <ul class="list" id="list"></ul>
  <button class="more" id="more" hidden>Show more</button>

  <footer>Harvested {len(rows)} entries from Developers Italia (REST API), SILL and
    awesome-codegouvfr (bulk JSON), openCode and code.europa.eu (GitLab API), iMio (GitHub),
    Offentligkod (recutils in git) and Avoinkoodi (static JSON). The Netherlands register needs
    an API key; Ireland, Portugal and Cyprus have no machine route found yet. The EU aggregate
    catalogue is deliberately not syndicated &mdash; its paging and search are broken.</footer>
</div>

<script>
const DATA = {DATA};
const CF = {CFACETS}, SF = {SFACETS}, FF = {FFACETS};
const PAGE = 100;
let shown = PAGE, activeC = new Set(), activeS = new Set(), activeF = new Set();

const el = id => document.getElementById(id);
const esc = s => (s??'').replace(/[&<>"]/g, m => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[m]));

function chips(host, facets, active) {{
  host.innerHTML = facets.map(f => {{
    const [k,label,n] = f.length === 3 ? f : [f[0], f[0], f[1]];
    return `<button class="chip" data-k="${{esc(k)}}" aria-pressed="false"><span class="k">${{esc(label)}}</span> ${{n}}</button>`;
  }}).join('');
  host.onclick = e => {{
    const b = e.target.closest('.chip'); if (!b) return;
    const k = b.dataset.k;
    active.has(k) ? active.delete(k) : active.add(k);
    b.setAttribute('aria-pressed', active.has(k));
    shown = PAGE; render();
  }};
}}

function current() {{
  const q = el('q').value.trim().toLowerCase();
  const lic = el('lic').value;
  const lvf = el('lv').value;
  const showex = el('showex').checked;
  let out = DATA.filter(r =>
    (showex || !r.ex) &&
    (!activeC.size || activeC.has(r.c)) &&
    (!activeS.size || activeS.has(r.s)) &&
    (!activeF.size || r.fx.some(f => activeF.has(f))) &&
    (!lic || r.l === lic) &&
    (!lvf || (lvf === 'ok' ? !r.lv : r.lv === lvf)) &&
    (!q || (r.n+' '+r.d+' '+r.o+' '+r.g.join(' ')).toLowerCase().includes(q))
  );
  const s = el('sort').value;
  if (s === 'adopters') out.sort((a,b) => b.ub - a.ub || a.n.localeCompare(b.n));
  else if (s === 'country') out.sort((a,b) => a.c.localeCompare(b.c) || a.n.localeCompare(b.n));
  else out.sort((a,b) => a.n.toLowerCase().localeCompare(b.n.toLowerCase()));
  return out;
}}

function render() {{
  const rs = current();
  const showingEx = el('showex').checked;   // never rely on the id-global
  const universe = showingEx ? DATA.length : DATA.filter(r => !r.ex).length;
  el('count').innerHTML = `<b>${{rs.length}}</b> of ${{universe}} entries`;
  el('list').innerHTML = rs.slice(0, shown).map(r => {{
    const link = r.u || r.h;
    const host = link ? link.replace(/^https?:\\/\\//,'').replace(/\\/$/,'') : '';
    return `<li class="item">
      <div class="cc">${{esc(r.c)}}</div>
      <div class="body">
        <div class="title">
          ${{link ? `<a href="${{esc(link)}}" target="_blank" rel="noopener">${{esc(r.n)}}</a>`
                 : `<span>${{esc(r.n)}}</span>`}}
          ${{r.st ? `<span class="pill ${{esc(r.st)}}">${{esc(r.st)}}</span>` : ''}}
          ${{r.rec ? `<span class="pill rec">recommended</span>` : ''}}
          ${{r.qid ? `<span class="pill">${{esc(r.qid)}}</span>` : ''}}
          ${{r.l ? `<span class="pill">${{esc(r.l)}}</span>` : ''}}
          ${{r.lv === 'dead' ? `<span class="pill dead" title="repository URL returned 404/410 at last check">repo gone</span>` : ''}}
          ${{r.lv === 'archived' ? `<span class="pill">archived</span>` : ''}}
          ${{r.ex ? `<span class="pill ex" title="filtered out of the default view">${{esc(r.ex)}}</span>` : ''}}
        </div>
        ${{r.d ? `<div class="desc">${{esc(r.d)}}</div>` : ''}}
        <div class="foot">
          <span class="src">${{esc(r.s)}}</span>
          ${{r.o ? `<span>${{esc(r.o)}}</span>` : ''}}
          ${{r.ub ? `<span>${{r.ub}} adopter${{r.ub>1?'s':''}}</span>` : ''}}
          ${{r.fx.length ? `<span>${{esc(r.fx.map(k=>FLABEL[k]||k).join(' \\u00b7 '))}}</span>` : ''}}
          ${{r.tr ? `<span title="machine-translated from ${{esc(r.sl)}}">translated from ${{esc(r.sl)}}</span>` : ''}}
          ${{link ? `<a href="${{esc(link)}}" target="_blank" rel="noopener">${{esc(host)}}</a>` : ''}}
        </div>
      </div></li>`;
  }}).join('') || `<div class="empty">Nothing matches those filters.</div>`;
  el('more').hidden = rs.length <= shown;
  el('more').textContent = `Show more (${{rs.length - shown}} remaining)`;
}}

const FLABEL = Object.fromEntries(FF.map(([k,l,n]) => [k,l]));
chips(el('fc'), FF, activeF);
chips(el('cc'), CF, activeC);
chips(el('sc'), SF, activeS);
el('q').oninput = () => {{ shown = PAGE; render(); }};
el('lic').onchange = () => {{ shown = PAGE; render(); }};
el('lv').onchange = () => {{ shown = PAGE; render(); }};
el('showex').onchange = () => {{ shown = PAGE; render(); }};
el('sort').onchange = () => {{ shown = PAGE; render(); }};
el('more').onclick = () => {{ shown += PAGE * 4; render(); }};
render();
</script>
"""

path = f"{OUT}/catalogue.html"
open(path, "w").write(PAGE)
print(f"wrote {path}  ({len(PAGE)/1024:.0f} KB, {len(rows)} rows)")
