# -*- coding: utf-8 -*-
"""Catalog page template. Appended to build_ui.py's data layer by _assemble.py.

NO F-STRINGS. Everything here is a plain string with __PLACEHOLDER__ tokens
substituted at the end. That is deliberate: the old template was one giant
f-string, so every literal CSS and JS brace had to be doubled, and a single
missed pair either raised or silently swallowed a rule. Plain strings + explicit
.replace() removes that whole class of bug. Keep it this way.
"""

# ---------------------------------------------------------------- page CSS
PAGE_CSS = """
/* ---- hero ---- */
.hero{padding:60px 0 44px;text-align:center;}
.hero .inner{max-width:1440px;margin:0 auto;padding:0 40px;display:flex;
  flex-direction:column;align-items:center;gap:18px;}
.hero h1{max-width:16em;}
.hero .lede{font-size:18px;line-height:1.5;color:var(--ink-600);max-width:44em;}
.searchbar{display:flex;align-items:center;gap:8px;width:100%;max-width:760px;
  background:var(--surface);border:1px solid var(--ink);border-radius:var(--r-pill);
  box-shadow:var(--shadow-bar);padding:6px 6px 6px 20px;margin-top:6px;}
.searchbar input{flex:1;border:0;outline:0;background:transparent;font:inherit;
  font-size:16px;color:var(--ink);min-width:0;padding:10px 0;}
.searchbar input::placeholder{color:var(--ink-faint);}

/* ---- agent banner: must sit directly above the tiles, early in the DOM ---- */
.apibar{display:flex;flex-wrap:wrap;align-items:center;gap:12px 20px;
  background:var(--surface);border:1px solid var(--ink);border-radius:var(--r-med);
  box-shadow:var(--shadow-bar);padding:14px 20px;margin:0 0 24px;}
.apibar .lbl{font-family:var(--font-ui);font-size:11px;font-weight:600;
  letter-spacing:.14em;text-transform:uppercase;display:flex;align-items:center;gap:8px;
  white-space:nowrap;}
.apibar .msg{font-size:15px;color:var(--ink-600);flex:1 1 320px;min-width:0;}
.apibar .msg a{font-family:var(--font-mono);font-size:13px;}
/* a flex row with a gap, NOT margin between inline anchors: written adjacent
   with margin-left there was no whitespace to wrap at, so the three endpoints
   were one unbreakable run and pushed the page 17px wide at 320px. */
.apibar .links{display:flex;flex-wrap:wrap;gap:4px 10px;margin-top:4px;}

/* ---- stat tiles ---- */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
  gap:1px;background:var(--border);border:1px solid var(--border);
  border-radius:var(--r-table);overflow:hidden;margin:0 0 36px;}
.stat{background:var(--surface);padding:18px 20px;}
.stat b{display:block;font-family:var(--font-display);font-size:24px;font-weight:700;
  color:var(--primary);font-variant-numeric:tabular-nums;letter-spacing:-0.02em;}
.stat span{display:block;font-size:12px;color:var(--ink-600);margin-top:2px;}

/* ---- body: wrapping flex, NOT a fixed grid ----
   A fixed two-column grid collapsed the entry column to 48px at 924px wide.
   Wrapping flex has no such failure mode and needs no media query. */
.body{display:flex;flex-wrap:wrap;gap:40px;align-items:flex-start;}
.side{flex:1 1 260px;max-width:320px;position:sticky;top:20px;}
.results{flex:1 1 600px;min-width:0;}

/* ---- sidebar facets ---- */
.facets{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--r-card);padding:18px;}
.facets .fhead{display:flex;align-items:center;justify-content:space-between;
  margin-bottom:12px;}
.facets .fhead .t{font-family:var(--font-ui);font-size:11px;font-weight:600;
  letter-spacing:.14em;text-transform:uppercase;margin:0;}
.facets .fhead button{background:none;border:0;padding:0;cursor:pointer;
  font:inherit;font-size:12px;color:var(--primary);text-decoration:underline;}
.fq{width:100%;background:var(--bg-alt);border:1px solid var(--border);
  border-radius:var(--r-chip);padding:8px 10px;font:inherit;font-size:13px;
  color:var(--ink);outline:0;}
.fq::placeholder{color:var(--ink-faint);}
.fgroup{padding-top:14px;margin-top:14px;border-top:var(--divider);}
.fgroup:first-of-type{border-top:0;margin-top:10px;}
.fgroup h3{font-family:var(--font-ui);font-size:11px;font-weight:600;
  letter-spacing:.14em;text-transform:uppercase;color:var(--ink-600);margin:0 0 8px;}
.fopt{display:flex;align-items:center;justify-content:space-between;gap:8px;
  width:100%;background:none;border:0;cursor:pointer;font:inherit;font-size:13px;
  color:var(--ink);text-align:left;padding:5px 8px;border-radius:var(--r-chip);
  transition:background-color 120ms,color 120ms;}
.fopt:hover{background:var(--bg-alt);}
.fopt[aria-pressed="true"]{background:var(--primary-tint);color:var(--primary);
  font-weight:600;}
.fopt .n{font-variant-numeric:tabular-nums;color:var(--ink-faint);font-size:12px;}
.fopt[aria-pressed="true"] .n{color:var(--primary);}
.fmore{background:none;border:0;padding:5px 8px;cursor:pointer;font:inherit;
  font-size:12px;color:var(--primary);text-decoration:underline;}

/* ---- results toolbar ---- */
.toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:14px;}
.sel,.tog{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--r-pill);padding:8px 14px;font:inherit;font-size:13px;
  color:var(--ink);cursor:pointer;transition:background-color 120ms,color 120ms;
  /* a <select> sizes to its WIDEST OPTION by default - the licence list made it
     472px and scrolled the whole page sideways on a phone */
  max-width:100%;}
/* A native <select> ignores border-radius, padding and background on most
   platforms until its appearance is removed - which is why these three rendered
   as OS controls beside pill-shaped buttons. Removing the appearance also
   removes the dropdown arrow, so the chevron is drawn back in as a background
   image (a data URI, so it stays self-contained and costs no request).
   The colour is baked because a data URI cannot read a CSS variable; it is
   --ink-600. Width is capped because a select sizes to its WIDEST OPTION, and
   the licence list ran to several hundred pixels. */
.sel{
  appearance:none;-webkit-appearance:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8' fill='none' stroke='%234D4D4A' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M1 1.5 6 6.5 11 1.5'/%3E%3C/svg%3E");
  background-repeat:no-repeat;
  background-position:right 14px center;
  padding-right:34px;
  max-width:100%;
  width:auto;
  text-overflow:ellipsis;
}
.sel:hover{background-color:var(--bg-alt);}
/* the licence list is the long one; the others are short by nature */
#lic{max-width:220px;}
.tog[aria-pressed="true"]{background:var(--primary-tint);color:var(--primary);
  border-color:var(--primary);font-weight:600;}
.countline{display:flex;flex-wrap:wrap;gap:6px 14px;align-items:baseline;
  font-size:13px;color:var(--ink-600);margin-bottom:10px;}
.countline b{font-family:var(--font-display);font-size:16px;color:var(--ink);
  font-variant-numeric:tabular-nums;}
.colhead{display:flex;gap:12px;font-family:var(--font-ui);font-size:10px;
  font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-faint);
  padding:10px 20px 8px;}
.colhead .c1{flex:0 0 40px;} .colhead .c2{flex:1 1 380px;} .colhead .c3{flex:0 1 290px;}

/* ---- entry rows ---- */
.list{list-style:none;margin:0;padding:0;background:var(--surface);
  border:1px solid var(--border);border-radius:var(--r-card);overflow:hidden;}
.item{display:flex;flex-wrap:wrap;gap:12px;padding:18px 20px;
  border-bottom:1px solid var(--border-soft);transition:background-color 120ms;}
.item:last-child{border-bottom:0;}
.item:hover{background:var(--bg-alt);}
.item .cc{flex:0 0 40px;font-size:12px;font-weight:600;letter-spacing:.05em;
  color:var(--ink-600);padding-top:2px;}
.item .main{flex:1 1 380px;min-width:0;display:flex;flex-direction:column;gap:5px;}
.item .side2{flex:0 1 290px;display:flex;flex-wrap:wrap;gap:4px 14px;
  align-items:flex-start;font-size:12px;color:var(--ink-600);padding-top:2px;}
.item .title{display:flex;flex-wrap:wrap;align-items:center;gap:8px;}
.item .title a,.item .title span.nm{font-family:var(--font-display);font-size:16px;
  font-weight:600;color:var(--ink);text-decoration:none;letter-spacing:-0.01em;}
.item .title a:hover{color:var(--primary);text-decoration:underline;}
.item .desc{font-size:14px;line-height:1.5;color:var(--ink-600);text-wrap:pretty;}
.item .rp{font-size:12px;color:var(--primary);}
.item .meta{font-size:12px;color:var(--ink-faint);}
.item .why{font-size:12px;color:var(--ink-600);border-left:2px solid var(--ink);
  padding-left:8px;}

/* ---- stamps: three tiers, and the two loud ones carry a hard shadow ----
   Six pill types used to sit at one visual weight, so a licence and "this
   repository no longer exists" read identically. Quiet metadata now has no
   pill at all - it lives in the .meta line. */
.stamp{font-family:var(--font-ui);font-size:11px;font-weight:600;letter-spacing:.05em;
  text-transform:uppercase;padding:3px 8px;border-radius:var(--r-chip);
  display:inline-flex;align-items:center;gap:5px;white-space:nowrap;}
/* ink on green, not white on green: white measured 2.65:1 against #01B583 and
   failed 1.4.3. ink-900 is 6.62:1 on the same fill, so the green and its hard
   shadow - which is what makes this read as an endorsement - both survive. */
.stamp.rec{background:var(--green);color:var(--on-green);box-shadow:var(--shadow-green);}
.stamp.multi{background:var(--mint);color:var(--green-text);box-shadow:var(--shadow-green);}
.stamp.warn{background:var(--ink-900);color:var(--paper-50);}
.stamp svg{width:12px;height:12px;}

.more{display:block;width:100%;margin-top:16px;}
.note{font-size:12px;color:var(--ink-faint);line-height:1.6;margin-top:14px;max-width:70ch;}
.empty{padding:40px 20px;text-align:center;color:var(--ink-600);}

/* ---- submit block ---- */
.submit{background:var(--surface);border:1px solid var(--ink);
  border-radius:var(--r-med);box-shadow:var(--shadow-bar);padding:28px 32px;
  margin-top:48px;display:flex;flex-direction:column;gap:10px;align-items:flex-start;}

@media (max-width:940px){ .side{position:static;max-width:none;} }
@media (max-width:720px){
  .hero{padding:36px 0 28px;}
  .colhead{display:none;}
  /* every hit target, not just the obvious ones - .fmore ("Show all N") and the
     Clear all button were 28px and 18px */
  .btn,.fopt,.tog,.sel,.fmore,.facets .fhead button{min-height:44px;}
  .facets .fhead button,.fmore{display:inline-flex;align-items:center;}
}
"""

# ---------------------------------------------------------------- icons
ICONS = {
    "code": '<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6">'
            '</polyline><polyline points="8 6 2 12 8 18"></polyline></svg>',
    "alert": '<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" '
             'stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 '
             '1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>'
             '<line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17">'
             '</line></svg>',
    "seal": '<svg aria-hidden="true" viewBox="0 0 24 24" fill="currentColor"><path d="M12 1.5l2.6 2.1 3.3-.3.9 3.2 '
            '2.8 1.8-1.4 3 1.4 3-2.8 1.8-.9 3.2-3.3-.3L12 22.5l-2.6-2.1-3.3.3-.9-3.2L2.4 15.7l'
            '1.4-3-1.4-3 2.8-1.8.9-3.2 3.3.3z" opacity=".95"/><path d="M10.6 15.4L7.8 12.6l1.2-1.2 '
            '1.6 1.6 4-4 1.2 1.2z" fill="#fff"/></svg>',
    "search": '<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
              'stroke-linecap="round"><circle cx="11" cy="11" r="8"></circle>'
              '<line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
}

# ---------------------------------------------------------------- markup
BODY = """
<div class="hero tex">
  <div class="inner">
    <p class="overline">The union catalog &middot; updated every Monday</p>
    <h1>Open source software catalog for governments</h1>
    <p class="lede">An aggregation of open source software catalogs from national, regional,
      local and global governing institutions &mdash; updated weekly. Are we missing a catalog?
      <a href="#submit">Submit it here</a>.</p>
    <div class="searchbar">
      <input type="search" id="q" autocomplete="off"
             placeholder="Search __NENTRIES__ entries, or a product you pay for"
             aria-label="Search the catalog">
      <button class="btn btn-primary" id="qbtn">Search</button>
    </div>
  </div>
</div>

<div class="wrap">
  <!-- Agent affordance 3 of 4: this banner must stay directly above the stat
       tiles and early in the DOM, so a text extraction hits it in the first
       screenful. Moved below the fold, it stops doing its job. -->
  <div class="apibar">
    <span class="lbl">__ICON_CODE__ Building something?</span>
    <span class="msg">Don't scrape this page. The whole catalog is one request:
      <span class="links"><a href="/entries.json">/entries.json</a>
      <a href="/sources.json">/sources.json</a>
      <a href="/meta.json">/meta.json</a></span></span>
    <a class="btn btn-ghost" href="/api.html">API and MCP</a>
  </div>

  <div class="stats">
    <div class="stat"><b>__N_ENTRIES__</b><span>entries</span></div>
    <div class="stat"><b>__N_SOURCES__</b><span>source catalogs</span></div>
    <div class="stat"><b>__N_PC__</b><span>with publiccode.yml</span></div>
    <div class="stat"><b>__N_EN__</b><span>in English or translated</span></div>
    <div class="stat"><b>__N_FUNCS__</b><span>functions</span></div>
    <div class="stat"><b>__N_MULTI__</b><span>in 2+ catalogs</span></div>
  </div>

  <main id="main" class="body">
    <aside class="side">
      <div class="facets">
        <div class="fhead"><h2 class="t">Filters</h2>
          <button type="button" id="clearall">Clear all</button></div>
        <input class="fq" id="fq" type="search" autocomplete="off"
               placeholder="Narrow the filters&hellip;" aria-label="Filter the filter options">
        <div id="facetgroups"></div>
      </div>
    </aside>

    <div class="results">
      <div class="toolbar">
        <select class="sel" id="sort" aria-label="Sort entries">
          <option value="catalogs">Sort: most catalogs</option>
          <option value="name">Sort: name A&ndash;Z</option>
          <option value="country">Sort: country</option>
        </select>
        <select class="sel" id="lic" aria-label="Filter by licence">
          <option value="">Any licence</option>__LOPTS__
        </select>
        <select class="sel" id="lv" aria-label="Filter by repository state">
          <option value="">Any repo state</option>
          <option value="ok">Reachable</option>
          <option value="archived">Archived upstream</option>
          <option value="dead">Repo gone</option>
        </select>
        <button class="tog" type="button" id="onlyrep" aria-pressed="false">Replaces a paid product</button>
        <button class="tog" type="button" id="setaside" aria-pressed="false">Include __N_EX__ set-aside entries</button>
      </div>

      <div class="countline"><span id="count"></span><span id="fcount"></span></div>
      <hr class="dashed">
      <div class="colhead"><span class="c1">CC</span><span class="c2">Entry</span>
        <span class="c3">Function &middot; harvested from</span></div>

      <ul class="list" id="list"></ul>
      <button class="btn btn-ghost more" type="button" id="more" hidden>Show 100 more</button>

      <p class="note">A blank licence means the upstream catalogue did not state a real SPDX
      identifier &mdash; it is left empty rather than guessed. &ldquo;Repo gone&rdquo; requires two
      consecutive failed checks, so a single 404 never shows here. Set-aside entries were
      harvested but held out of the default view (forks of upstream projects, CI plumbing,
      deployment recipes, locale bundles); they keep their reason, stay in the data, and come
      back with the toggle above.</p>
    </div>
  </main>

  <div class="submit" id="submit">
    <p class="overline">Get involved</p>
    <h3>Are we missing a catalog?</h3>
    <p style="color:var(--ink-600);max-width:60ch">If your government publishes an open source
      register, or you know one that is not listed, open an issue and it will be assessed
      against the same first-hand rule as the __N_SOURCES__ already here.</p>
    <a class="btn btn-primary" href="https://github.com/sarapis/govoss-catalog/issues/new">Submit a catalog</a>
  </div>
</div>
"""

# ---------------------------------------------------------------- behaviour
SCRIPT = """
<script>
var DATA = __DATA__;
var FFACETS = __FFACETS__, CFACETS = __CFACETS__, SFACETS = __SFACETS__;
var PAGE_SIZE = 100;

/* State. NOTHING here is named after an element id: browsers expose ids as
   globals, and a variable that collides silently resolves to the element -
   always truthy - which once broke an entry-count denominator without throwing. */
var activeFacets = new Set();
var facetQuery = '';
var onlyReplaces = false;
var showSetAside = false;
var visibleCount = PAGE_SIZE;
var expanded = new Set();

var el = function (id) { return document.getElementById(id); };
function esc(s) {
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
var GROUPS = [
  { key: 'fn', title: 'Function', rows: FFACETS.map(function (f) { return [f[0], f[1], f[2]]; }) },
  { key: 'cc', title: 'Country', rows: CFACETS.map(function (f) { return [f[0], f[0], f[1]]; }) },
  { key: 'src', title: 'Source catalog', rows: SFACETS.map(function (f) { return [f[0], f[0], f[1]]; }) }
];

function renderFacets() {
  var q = facetQuery.toLowerCase();
  el('facetgroups').innerHTML = GROUPS.map(function (g) {
    var rows = g.rows.filter(function (r) { return !q || r[1].toLowerCase().indexOf(q) >= 0; });
    var open = expanded.has(g.key) || q;
    var show = open ? rows : rows.slice(0, 6);
    var opts = show.map(function (r) {
      var id = g.key + ':' + r[0];
      var on = activeFacets.has(id);
      return '<button type="button" class="fopt" data-f="' + esc(id) + '" aria-pressed="' +
        (on ? 'true' : 'false') + '"><span>' + esc(r[1]) + '</span><span class="n">' + r[2] +
        '</span></button>';
    }).join('');
    var more = (!q && rows.length > 6)
      ? '<button type="button" class="fmore" data-g="' + esc(g.key) + '">' +
        (open ? 'Show fewer' : 'Show all ' + rows.length + ' \\u2192') + '</button>' : '';
    if (!rows.length) opts = '<p class="meta" style="padding:4px 8px">No match</p>';
    return '<div class="fgroup"><h3>' + esc(g.title) + '</h3>' + opts + more + '</div>';
  }).join('');
}

function current() {
  var q = (el('q').value || '').trim().toLowerCase();
  var lic = el('lic').value, lvf = el('lv').value, sort = el('sort').value;
  var fns = [], ccs = [], srcs = [];
  activeFacets.forEach(function (id) {
    var i = id.indexOf(':'), k = id.slice(0, i), v = id.slice(i + 1);
    if (k === 'fn') fns.push(v); else if (k === 'cc') ccs.push(v); else srcs.push(v);
  });
  var out = DATA.filter(function (r) {
    if (!showSetAside && r.ex) return false;
    if (fns.length && !r.fx.some(function (f) { return fns.indexOf(f) >= 0; })) return false;
    if (ccs.length && !(r.cs || [r.c]).some(function (x) { return ccs.indexOf(x) >= 0; })) return false;
    if (srcs.length && !(r.ss || [r.s]).some(function (x) { return srcs.indexOf(x) >= 0; })) return false;
    if (lic && r.l !== lic) return false;
    if (lvf && (lvf === 'ok' ? !!r.lv : r.lv !== lvf)) return false;
    if (onlyReplaces && !(r.rp && r.rp.length)) return false;
    if (q) {
      var hay = (r.n + ' ' + r.d + ' ' + r.o + ' ' + (r.g || []).join(' ') + ' ' +
                 (r.aka || []).join(' ') + ' ' + (r.rp || []).join(' ')).toLowerCase();
      if (hay.indexOf(q) < 0) return false;
    }
    return true;
  });
  if (sort === 'name') out.sort(function (a, b) { return a.n.toLowerCase().localeCompare(b.n.toLowerCase()); });
  else if (sort === 'country') out.sort(function (a, b) { return a.c.localeCompare(b.c) || a.n.localeCompare(b.n); });
  else out.sort(function (a, b) { return (b.cc2 || 1) - (a.cc2 || 1) || b.ub - a.ub || a.n.localeCompare(b.n); });
  return out;
}

function stamps(r) {
  var s = '';
  if (r.rec) s += '<span class="stamp rec">__ICON_SEAL__ Recommended</span>';
  if (r.cc2 > 1) s += '<span class="stamp multi">In ' + r.cc2 + ' catalogs</span>';
  if (r.lv === 'dead') s += '<span class="stamp warn">__ICON_ALERT__ Repo gone</span>';
  else if (r.lv === 'archived') s += '<span class="stamp warn">__ICON_ALERT__ Archived upstream</span>';
  return s;
}

function render() {
  var rs = current();
  var universe = showSetAside ? DATA.length : DATA.filter(function (r) { return !r.ex; }).length;
  el('count').innerHTML = '<b>' + rs.length.toLocaleString() + '</b> of ' +
    universe.toLocaleString() + ' entries';
  var nf = activeFacets.size + (onlyReplaces ? 1 : 0) +
           (el('lic').value ? 1 : 0) + (el('lv').value ? 1 : 0);
  el('fcount').textContent = nf ? (nf + (nf === 1 ? ' filter applied' : ' filters applied')) : '';

  if (!rs.length) {
    el('list').innerHTML = '<li class="empty">No entries match. ' +
      '<button type="button" class="fmore" id="clear2">Clear the filters</button></li>';
    el('more').hidden = true;
    var c2 = el('clear2'); if (c2) c2.onclick = clearAll;
    return;
  }
  el('list').innerHTML = rs.slice(0, visibleCount).map(function (r) {
    var link = r.u || r.h;
    var meta = [];
    if (r.l) meta.push(esc(r.l)); else meta.push('Licence not stated by the source');
    if (r.qid) meta.push(esc(r.qid));
    var srcs = (r.ce && r.ce.length ? r.ce : []).map(function (c) {
      return c.u ? '<a href="' + esc(c.u) + '" target="_blank" rel="noopener">' + esc(c.l) + '</a>'
                 : esc(c.l);
    }).join(' + ') || esc((r.ss || [r.s]).join(' + '));
    return '<li class="item">' +
      '<div class="cc">' + esc(r.c) + '</div>' +
      '<div class="main">' +
        '<div class="title">' +
          (link ? '<a href="' + esc(link) + '" target="_blank" rel="noopener">' + esc(r.n) + '</a>'
                : '<span class="nm">' + esc(r.n) + '</span>') + stamps(r) +
        '</div>' +
        (r.d ? '<div class="desc">' + esc(r.d) + '</div>' : '') +
        (r.rp && r.rp.length ? '<div class="rp">Replaces ' + esc(r.rp.join(', ')) + '</div>' : '') +
        '<div class="meta">' + meta.join(' &middot; ') + '</div>' +
        (r.ex ? '<div class="why">Set aside: ' + esc(r.ex) + '</div>' : '') +
      '</div>' +
      '<div class="side2"><span>' + esc((r.fx || []).slice(0, 2).join(', ')) + '</span>' +
        '<span>' + srcs + '</span></div>' +
    '</li>';
  }).join('');
  el('more').hidden = rs.length <= visibleCount;
}

function reset() { visibleCount = PAGE_SIZE; render(); }
function clearAll() {
  activeFacets.clear(); facetQuery = ''; onlyReplaces = false;
  el('fq').value = ''; el('lic').value = ''; el('lv').value = '';
  el('onlyrep').setAttribute('aria-pressed', 'false');
  renderFacets(); reset();
}

el('facetgroups').addEventListener('click', function (e) {
  var f = e.target.closest('[data-f]'), g = e.target.closest('[data-g]');
  if (f) {
    var id = f.getAttribute('data-f');
    if (activeFacets.has(id)) activeFacets.delete(id); else activeFacets.add(id);
    renderFacets(); reset();
  } else if (g) {
    var k = g.getAttribute('data-g');
    if (expanded.has(k)) expanded.delete(k); else expanded.add(k);
    renderFacets();
  }
});
el('fq').oninput = function () { facetQuery = this.value; renderFacets(); };
el('q').oninput = reset;
el('qbtn').onclick = reset;
el('lic').onchange = reset;
el('lv').onchange = reset;
el('sort').onchange = reset;
el('clearall').onclick = clearAll;
el('onlyrep').onclick = function () {
  onlyReplaces = !onlyReplaces;
  this.setAttribute('aria-pressed', onlyReplaces ? 'true' : 'false');
  reset();
};
el('setaside').onclick = function () {
  showSetAside = !showSetAside;
  this.setAttribute('aria-pressed', showSetAside ? 'true' : 'false');
  reset();
};
el('more').onclick = function () { visibleCount += PAGE_SIZE; render(); };

renderFacets();
render();
</script>
"""
