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

/* The API note: small, but plain visible text. It is an agent affordance, so it
   may not become a tooltip, a collapsed disclosure or an image. */
/* ⚠ theme.py's icons carry a viewBox and NO width/height, so an unsized one
   renders at the SVG default — the <> rendered enormous here. Every context that
   uses an icon has to size it; `.stamp svg` already does the same. */
.apinote svg{width:13px;height:13px;vertical-align:-2px;}
/* A flex ROW, not an inline paragraph. Inline, the pieces wrapped independently
   and scattered over four lines at 1280px: /meta.json alone on one, "API and MCP"
   two lines below it. Its natural single-line width is 766px against the 760px
   cap the searchbar sets, so the cap alone was breaking it. Flex keeps each piece
   whole and wraps only between them, which is the same reason `.apibar .links`
   was a flex row. `max-width` is dropped so one line fits; the hero's own padding
   still bounds it, and it wraps normally on narrow screens. */
.apinote{margin:10px 0 0;font-size:12.5px;line-height:1.7;color:var(--ink-600);
  display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 10px;}
.apinote b{color:var(--ink);font-weight:600;display:inline-flex;align-items:center;
  gap:6px;white-space:nowrap;}
.apinote .m{min-width:0;}
.apinote a{font-family:var(--font-mono,ui-monospace,monospace);font-size:12px;
  white-space:nowrap;}
/* NOT `.more` — that class already belongs to the "Show 100 more" button, which
   is `display:block;width:100%`. Reusing the name made this link a full-width
   flex item that filled its row and pushed itself onto a line of its own, which
   read as a wrapping bug and was a class collision. */
.apinote a.apimore{font-family:inherit;font-size:12.5px;font-weight:600;}

/* Recently added. The track is the ONLY thing that scrolls sideways on this page
   - it is its own overflow container, so the body never does. */
.recent{margin:0 0 20px;}
.rhead{display:flex;align-items:baseline;justify-content:space-between;gap:12px;
  flex-wrap:wrap;margin-bottom:10px;}
.rhead h2{font-size:13px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;
  color:var(--ink-600);margin:0;}
.rnav{display:flex;gap:6px;align-items:center;}
.rbtn{background:var(--surface);border:1px solid var(--border);border-radius:6px;
  width:30px;height:30px;line-height:1;cursor:pointer;color:var(--ink-600);
  font-size:14px;}
.rbtn:hover{background:var(--bg-alt);color:var(--ink);}
.rbtn[disabled]{opacity:.35;cursor:default;}
.rbtn:focus-visible,.rall:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}
.rall{background:none;border:0;padding:0 0 0 6px;cursor:pointer;font:inherit;
  font-size:12.5px;font-weight:600;color:var(--accent);}
.rtrack{display:flex;gap:10px;list-style:none;margin:0;padding:2px;
  overflow-x:auto;scroll-behavior:smooth;scroll-snap-type:x proximity;
  overscroll-behavior-x:contain;
  /* Scrollbar hidden, scrolling kept. The arrows are the affordance here, and a
     horizontal bar under a 10-card strip reads as a page defect. Keyboard and
     wheel/trackpad scrolling are unaffected. */
  scrollbar-width:none;-ms-overflow-style:none;}
.rtrack::-webkit-scrollbar{display:none;}
.rcard{flex:0 0 232px;scroll-snap-align:start;background:var(--surface);
  border:1px solid var(--border);border-radius:var(--r-card);padding:12px 14px;
  display:flex;flex-direction:column;gap:5px;min-width:0;}
.rcard .rt{font-weight:600;font-size:14px;line-height:1.3;overflow-wrap:anywhere;}
.rcard .rt a{color:inherit;}
.rcard .rd{font-size:12.5px;line-height:1.45;color:var(--ink-600);
  display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;}
.rcard .rm{margin-top:auto;padding-top:4px;font-size:11px;color:var(--ink-faint);
  display:flex;gap:6px;flex-wrap:wrap;align-items:baseline;}
.rcard .rm .fl{font-size:13px;line-height:1;cursor:default;}
@media (prefers-reduced-motion:reduce){.rtrack{scroll-behavior:auto;}}

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
/* max-height + overflow is what lets the sidebar carry any number of facet
   groups. Without it a `position:sticky` element taller than the viewport
   leaves its bottom permanently unreachable: measured 887px against an 860px
   viewport with only three groups, i.e. already broken before Source country
   was added. A facet group was once DELETED to treat this symptom. */
.side{flex:1 1 260px;max-width:320px;position:sticky;top:20px;
  max-height:calc(100vh - 40px);overflow-y:auto;overscroll-behavior:contain;}
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
/* Pressed state: pale ground + NAVY text, not accent-on-tint. Accent text on
   any ground pale enough to read as "selected" lands at 4.9:1 or worse; navy
   is 12.55:1 and the border plus weight carry the active signal. */
.fopt[aria-pressed="true"]{background:var(--primary-tint);color:var(--ink);
  font-weight:600;}
.fopt .n{font-variant-numeric:tabular-nums;color:var(--ink-faint);font-size:12px;}
.fopt[aria-pressed="true"] .n{color:var(--ink-600);}
/* display:block matters for the anchor variant ("Show all" on a group with a
   `link`): an inline <a> would ignore the 44px min-height touch target below. */
.fmore{display:block;text-align:left;background:none;border:0;padding:5px 8px;
  cursor:pointer;font:inherit;font-size:12px;color:var(--primary);
  text-decoration:underline;}

/* ---- results toolbar ---- */
/* The toolbar is meant to be ONE row. A <select> is sized by its longest option,
   and "Digital Public Goods Registry (GLOBAL) (253)" made #src 329px wide, which
   with the other controls totalled 1,029px in a 615px column and wrapped to
   THREE rows. Capping the width truncates the closed display only — the dropdown
   list still shows each option in full — and everything that does not fit has
   moved into the drawer instead. */
.toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:14px;}
/* Caps are sized for the WIDEST LANGUAGE's closed label (measured 2026-09-23):
   "Ordena: més catàlegs" needs 185px, "Qualsevol llicència" 164px. The English
   caps (190/170/150) clipped every Catalan label and even English "Sort:
   recently added" (176px). A cap is only a ceiling - each select still takes its
   own intrinsic width up to it. Re-measure when adding a language; a static
   check cannot see font metrics. */
.toolbar .sel{max-width:216px;}
.toolbar #sort{max-width:190px;}
/* #lic carries its own `max-width:220px` from an ID selector, which outranks the
   class rule above and left it hogging 220 of a 615px column — squeezing #sort to
   101px, where "Sort: most catalogs" truncates to about three characters. An ID
   needs an ID to beat it. "Any licence" fits comfortably; the long SPDX names
   ellipsis either way. */
.toolbar #lic{max-width:170px;}
.drawer .sel{max-width:none;}
/* ONE ROW above the sidebar breakpoint, and it has to be `nowrap` rather than
   tuned widths. With `flex-wrap:wrap` the browser wraps a line BEFORE shrinking
   anything on it, so capping each control just moves the width at which it
   breaks: 160+220+190+100 fits an 825px column at 1280 and wraps to two rows in
   the 615px column at 1024. `nowrap` plus `min-width:0` lets them compress
   instead, so the row holds at any desktop width and the labels ellipsis (which
   `.sel` already does). Below 941px the sidebar goes static and wrapping is
   correct, so the default stands. */
@media (min-width:941px){
  .toolbar{flex-wrap:nowrap;}
  /* The SELECTS absorb the squeeze — they already ellipsis. The buttons do not:
     letting #morefilters shrink took it to 67px, wrapped "More filters" onto two
     lines and made it 57px tall beside 38px selects. A control that changes
     height when the window narrows reads as broken. */
  .toolbar .sel{min-width:0;flex:1 1 auto;}
  /* ...except #sort. It is the one label a reader must read to know the order
     they are looking at, and it shrank FIRST: at 1024px (a 615px column) it was
     118px wide and "Sort: most catalogs" read as "Sort: m…". Licence and source
     are filters whose empty state is self-evident, so they take the squeeze. */
  .toolbar #sort{flex:0 0 auto;}
  /* Equal bases, so licence and source share the squeeze. With flex-basis:auto
     the shrink is weighted by each select's natural width, and #lic's long SPDX
     options made it refuse to shrink while #src took the whole cut. At 1024px
     the pair still needs a few px more than the row has in Catalan (318 vs 311),
     so one of them ellipses by a few px there; from ~1100px up both fit. */
  .toolbar #lic, .toolbar #src{flex:1 1 150px;}
  .toolbar .tog{flex:0 0 auto;white-space:nowrap;}
}
.drawer{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--r-card);padding:14px 16px;margin:-6px 0 14px;
  display:flex;flex-direction:column;gap:12px;}
.drow{display:flex;flex-wrap:wrap;gap:8px;align-items:center;}
.dlab{font-family:var(--font-ui);font-size:11px;font-weight:600;
  letter-spacing:.04em;text-transform:uppercase;color:var(--ink-600);
  flex:0 0 100%;}
.dnote{font-size:12px;line-height:1.55;color:var(--ink-600);margin:0;}
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
.tog[aria-pressed="true"]{background:var(--primary-tint);color:var(--ink);
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
.item .vars{font-size:12px;color:var(--ink-600);}
/* Qualifier on a replaces target that is not a like-for-like software swap.
   --ink-faint is the documented tertiary tier (5.17:1 on paper), so this sits
   at the audited floor rather than below it. */
.item .rp .rpq{color:var(--ink-faint);}
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
/* The green pairing, measured - keep these numbers, the .stamp.rec rule they
   were written for is gone but they govern every green mark on the site.
   White on the mid green (#01B583) is 2.65:1 and fails 1.4.3; ink-900 on it is
   6.62:1; white on --green-text is 9.33:1. So --green is the FILL token for
   non-text marks and --green-text carries any words, which is the split
   upstream draws too. */
.stamp.multi{background:var(--mint);color:var(--green-text);box-shadow:var(--shadow-green);}
.stamp.warn{background:var(--ink-900);color:var(--paper-50);}
.stamp svg{width:12px;height:12px;}

.more{display:block;width:100%;margin-top:16px;}
/* Prose here is FULL WIDTH by decision (2026-08-14). The 65-75ch measure rule is
   real, but these blocks sit directly beneath full-width tables and card lists,
   and a 530px column under a 1345px list reads as a layout mistake rather than as
   a considered line length. Owner call; revert by restoring a max-width in ch. */
.note{font-size:12px;color:var(--ink-faint);line-height:1.6;margin-top:14px;}
.empty{padding:40px 20px;text-align:center;color:var(--ink-600);}

/* ---- submit block ---- */
.submit{background:var(--surface);border:1px solid var(--ink);
  border-radius:var(--r-med);box-shadow:var(--shadow-bar);padding:28px 32px;
  margin-top:48px;display:flex;flex-direction:column;gap:10px;align-items:flex-start;}

@media (max-width:940px){ .side{position:static;max-width:none;
  max-height:none;overflow-y:visible;} }
@media (max-width:720px){
  .hero{padding:36px 0 28px;}
  .colhead{display:none;}
  /* every hit target, not just the obvious ones - .fmore ("Show all N") and the
     Clear all button were 28px and 18px */
  .btn,.fopt,.tog,.sel,.fmore,.facets .fhead button,
  .rbtn,.rall{min-height:44px;}
  /* square, or a 44px-tall 30px-wide arrow reads as a mis-sized button */
  .rbtn{min-width:44px;}
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
    <p class="overline">⟪The union catalog &middot; updated every Monday⟫</p>
    <h1>⟪Open source software catalog for governments⟫</h1>
    <p class="lede">⟪An aggregation of open source software catalogs from national, regional,
      local and global governing institutions &mdash; updated weekly. Are we missing a catalog?
      <a href="#submit">Submit it here</a>.⟫</p>
    <div class="searchbar">
      <input type="search" id="q" autocomplete="off"
             placeholder="⟪Search __NENTRIES__ entries, or a product you pay for⟫"
             aria-label="⟪Search the catalog⟫">
      <button class="btn btn-primary" id="qbtn">⟪Search⟫</button>
    </div>
    <!-- Agent affordance 3 of 4. It used to sit above the stat tiles; directly
         under the search field is EARLIER in the DOM, so a text extraction hits
         it sooner, not later. Smaller, because it is a standing note rather than
         an announcement — but it must stay visible text, not a tooltip or a
         collapsed disclosure, or it stops being an affordance at all. -->
    <p class="apinote">
      <b>__ICON_CODE__ ⟪Building something?⟫</b>
      <span class="m">⟪Don&rsquo;t scrape this page &mdash; the whole catalog is one
        request:⟫</span>
      <a href="/entries.json">/entries.json</a>
      <a href="/sources.json">/sources.json</a>
      <a href="/meta.json">/meta.json</a>
      <a class="apimore" href="/api.html">⟪API and MCP &rarr;⟫</a>
    </p>
  </div>
</div>

<div class="wrap">
  <!-- Recently added. Hidden entirely when there are no dated entries rather
       than rendered empty: a fresh checkout has no cache/_first_seen.json, and an
       empty strip claiming "recently added" is worse than no strip. -->
  <section class="recent" id="recent" hidden>
    <div class="rhead">
      <h2>⟪Recently added⟫</h2>
      <div class="rnav">
        <button type="button" class="rbtn" id="rprev" aria-label="⟪Scroll left⟫">&larr;</button>
        <button type="button" class="rbtn" id="rnext" aria-label="⟪Scroll right⟫">&rarr;</button>
        <button type="button" class="rall" id="rall">⟪See all, newest first⟫</button>
      </div>
    </div>
    <ul class="rtrack" id="rtrack"></ul>
  </section>

  <div class="stats">
    <div class="stat"><b>__N_ENTRIES__</b><span>⟪entries⟫</span></div>
    <div class="stat"><b>__N_SOURCES__</b><span>⟪source catalogs⟫</span></div>
    <div class="stat"><b>__N_PC__</b><span>⟪with publiccode.yml⟫</span></div>
    <div class="stat"><b>__N_EN__</b><span>⟪in English or translated⟫</span></div>
    <div class="stat"><b>__N_FUNCS__</b><span>⟪functions⟫</span></div>
    <div class="stat"><b>__N_MULTI__</b><span>⟪in 2+ catalogs⟫</span></div>
  </div>

  <main id="main" class="body">
    <aside class="side">
      <div class="facets">
        <div class="fhead"><h2 class="t">⟪Filters⟫</h2>
          <button type="button" id="clearall">⟪Clear all⟫</button></div>
        <input class="fq" id="fq" type="search" autocomplete="off"
               placeholder="⟪Narrow the filters&hellip;⟫" aria-label="⟪Filter the filter options⟫">
        <div id="facetgroups"></div>
      </div>
    </aside>

    <div class="results">
      <div class="toolbar">
        <select class="sel" id="sort" aria-label="⟪Sort entries⟫">
          <option value="catalogs">⟪Sort: most catalogs⟫</option>
          <option value="name">⟪Sort: name A&ndash;Z⟫</option>
          <option value="country">⟪Sort: country⟫</option>
          <option value="recent">⟪Sort: recently added⟫</option>
        </select>
        <select class="sel" id="lic" aria-label="⟪Filter by licence⟫">
          <option value="">⟪Any licence⟫</option>__LOPTS__
        </select>
        <select class="sel" id="src" aria-label="⟪Filter by source catalog⟫">
          <option value="">⟪Any source catalog⟫</option>__SOPTS__
        </select>
        <button class="tog" type="button" id="morefilters" aria-expanded="false"
                aria-controls="drawer">⟪More filters⟫</button>
      </div>

      <!-- The drawer holds the controls that are rarely touched and need more
           words than a toolbar chip allows. The set-aside toggle lived in the
           toolbar as "Include 488 set-aside entries", which named neither what
           was set aside nor why - and it covered TWO unrelated claims, so no
           single label could. Split and spelled out here instead. -->
      <div class="drawer" id="drawer" hidden>
        <div class="drow">
          <span class="dlab">⟪Procurement⟫</span>
          <button class="tog" type="button" id="onlyrep" aria-pressed="false">⟪Replaces a paid product⟫</button>
        </div>
        <div class="drow">
          <label class="dlab" for="lv">⟪Repository state⟫</label>
          <select class="sel" id="lv" aria-label="⟪Filter by repository state⟫">
            <option value="">⟪Any repo state⟫</option>
            <option value="ok">⟪Reachable⟫</option>
            <option value="archived">⟪Archived upstream⟫</option>
            <option value="dead">⟪Repo gone⟫</option>
          </select>
        </div>
        <div class="drow">
          <span class="dlab">⟪Entries held out of the default view⟫</span>
          <button class="tog" type="button" id="exnodesc" aria-pressed="false">
            ⟪Show __N_EX_NODESC__ with no description⟫</button>
          <button class="tog" type="button" id="exnotsoft" aria-pressed="false">
            ⟪Show __N_EX_NOTSOFT__ judged not adoptable⟫</button>
        </div>
        <p class="dnote">⟪No description means the publisher wrote none and GitHub had
          none either &mdash; not saying what software does is a failure to share it.
          Not adoptable means an upstream fork, a deployment recipe, CI plumbing, a
          locale bundle or org metadata: real files, but nothing a government can
          adopt. Both are <b>flagged, never deleted</b>, and both are always present
          in <span class="mono">/entries.json</span> with an
          <span class="mono">exclude_reason</span>.⟫</p>
      </div>

      <div class="countline"><span id="count"></span><span id="fcount"></span></div>
      <hr class="dashed">
      <div class="colhead"><span class="c1">CC</span><span class="c2">⟪Entry⟫</span>
        <span class="c3">⟪Function &middot; harvested from⟫</span></div>

      <ul class="list" id="list"></ul>
      <button class="btn btn-ghost more" type="button" id="more" hidden>⟪Show 100 more⟫</button>

      <p class="note">⟪A blank licence means the upstream catalogue did not state a real SPDX
      identifier &mdash; it is left empty rather than guessed. &ldquo;Repo gone&rdquo; requires two
      consecutive failed checks, so a single 404 never shows here. Set-aside entries were
      harvested but held out of the default view (forks of upstream projects, CI plumbing,
      deployment recipes, locale bundles); they keep their reason, stay in the data, and come
      back with the toggle above. Entries whose publisher wrote <b>no description at all</b>
      are among them: the upstream catalogue published none, GitHub had none either, and one is
      not invented here &mdash; not saying what the software does is a failure to share it.
      __N_NODESC__ stay in the default view despite having none, because they shipped a
      <code>publiccode.yml</code>, and a publisher's own declaration that something is reusable
      is never overridden by a rule of ours.⟫</p>
    </div>
  </main>

  __SUBMIT__
</div>
"""

# ---------------------------------------------------------------- behaviour
SCRIPT = """
<script>
var DATA = __DATA__;
var FFACETS = __FFACETS__, SFACETS = __SFACETS__, PFACETS = __PFACETS__;
var CCFACETS = __CCFACETS__;
var NEWEST = __NEWEST__;
var SRCFLAG = __SRCFLAG__;
// code -> display name, derived from the facet labels so there is ONE source for
// them. The flag is stripped: the label is "<flag> Germany" and sorting on that
// would order by emoji codepoint, not by name.
var CCNAME = {}, CCFLAG = {};
CCFACETS.forEach(function (f) {
  // The facet label is "<flag> <name>". Both halves are taken from it rather than
  // shipped twice, so a remapped flag or a renamed country cannot disagree
  // between the sidebar and the Recently added strip. A label with no space is a
  // name with no flag: keep the name, leave the flag empty.
  var lbl = String(f[1]), sp = lbl.indexOf(' ');
  CCNAME[f[0]] = sp > 0 ? lbl.slice(sp + 1) : lbl;
  CCFLAG[f[0]] = sp > 0 ? lbl.slice(0, sp) : '';
});
function ccLabel(code) { return CCNAME[code] || code; }
// Flag where there is one, country NAME where there is not — never an empty cell.
function ccFlag(code) { return CCFLAG[code] || ccLabel(code); }
var PAGE_SIZE = 100;
var LANG = '__LANG__';   // number format for this copy of the page

/* State. NOTHING here is named after an element id: browsers expose ids as
   globals, and a variable that collides silently resolves to the element -
   always truthy - which once broke an entry-count denominator without throwing. */
var activeFacets = new Set();
var facetQuery = '';
var onlyReplaces = false;
// Two flags, not one: the old single `showSetAside` could not express "show me
// the undescribed ones but not the forks", and the label could not say which was
// which. r.ex carries the reason, so the split is in the data already.
var showNoDesc = false;
var showNotSoft = false;
var visibleCount = PAGE_SIZE;
var expanded = new Set();

var el = function (id) { return document.getElementById(id); };
function esc(s) {
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
// Anchor id for a product on products.html. MUST match pslug() in
// build_products.py, which owns the ids this links to.
function pslug(s) {
  return String(s == null ? '' : s).toLowerCase().replace(/[^a-z0-9]+/g, '-')
    .replace(/-+/g, '-').replace(/^-|-$/g, '');
}
var GROUPS = [
  { key: 'fn', title: '⟪js:Function⟫', rows: FFACETS.map(function (f) { return [f[0], f[1], f[2]]; }) },
  { key: 'rp', title: '⟪js:Replaces⟫', rows: PFACETS.map(function (f) { return [f[0], f[1], f[2]]; }),
    link: 'products.html', linkLabel: '⟪js:Proprietary software catalog⟫' },
  // Source COUNTRY, deliberately named that way: it is the country of the
  // catalogue that listed the software, not the tier of government that published
  // it. Matched against r.cs (all countries), so an entry listed in two countries
  // appears under both. Labels are country NAMES; the VALUE stays the code.
  //
  // Source CATALOG is not here any more - it is the #src <select> in the toolbar.
  // SFACETS is still used, to validate an incoming ?src= value.
  { key: 'cc', title: '⟪js:Source country⟫', rows: CCFACETS.map(function (f) { return [f[0], f[1], f[2]]; }) }
];

function renderFacets() {
  var q = facetQuery.toLowerCase();
  el('facetgroups').innerHTML = GROUPS.map(function (g) {
    var rows = g.rows.filter(function (r) { return !q || r[1].toLowerCase().indexOf(q) >= 0; });
    var open = expanded.has(g.key) || q;
    var show = open ? rows : rows.slice(0, 6);
    // An ACTIVE facet outside the top 6 would otherwise be invisible while still
    // filtering — the toolbar says "1 filter applied" and nothing shows which.
    // Arrives that way via ?rp=<product> from products.html, where the product
    // is rarely one of the six most-replaceable.
    if (!open) {
      rows.forEach(function (r) {
        if (activeFacets.has(g.key + ':' + r[0]) && show.indexOf(r) < 0) show = show.concat([r]);
      });
    }
    var opts = show.map(function (r) {
      var id = g.key + ':' + r[0];
      var on = activeFacets.has(id);
      return '<button type="button" class="fopt" data-f="' + esc(id) + '" aria-pressed="' +
        (on ? 'true' : 'false') + '"><span>' + esc(r[1]) + '</span><span class="n">' + r[2] +
        '</span></button>';
    }).join('');
    // A group with `link` sends "Show all" to its own page rather than expanding
    // in place. For Replaces that is the point: the page also carries the
    // products with NO alternative, which can never appear as a facet.
    var more = g.link
      ? '<a class="fmore" href="' + esc(g.link) + '">' + esc(g.linkLabel) + ' \\u2192</a>'
      : ((!q && rows.length > 6)
        ? '<button type="button" class="fmore" data-g="' + esc(g.key) + '">' +
          (open ? '⟪js:Show fewer⟫' : '⟪js:Show all⟫ ' + rows.length + ' \\u2192') + '</button>' : '');
    if (!rows.length) opts = '<p class="meta" style="padding:4px 8px">⟪js:No match⟫</p>';
    return '<div class="fgroup"><h3>' + esc(g.title) + '</h3>' + opts + more + '</div>';
  }).join('');
}

// VARIANTS (variants.py): an entry that is a version of another carries vo, the
// DATA index of its core; the core carries vs, its variants' indices. After
// filtering, a variant is FOLDED under its core when the core is in the same
// result set - the list shows the core once, naming its variants. When the core
// is filtered out (e.g. ?src= Munich), the variant stands alone, saying what it
// is a version of. Never hidden outright: a source filter that silently drops
// its variants reads as "this catalogue contributed nothing", the claim
// /sources.html exists to disprove.
var lastFolded = 0;   // how many the last current() folded, for the count line
function fold(list) {
  var inSet = new Set(list.map(function (r) { return r.__i; }));
  var kept = list.filter(function (r) { return r.vo == null || !inSet.has(r.vo); });
  lastFolded = list.length - kept.length;
  return kept;
}
DATA.forEach(function (r, i) { r.__i = i; });

function current() {
  var q = (el('q').value || '').trim().toLowerCase();
  var lic = el('lic').value, lvf = el('lv').value, sort = el('sort').value;
  var fns = [], srcs = [], rps = [], ccs = [];
  // Every key routed EXPLICITLY. This was `else srcs.push(v)`, a catch-all, so
  // adding the 'cc' group silently pushed country codes into the source-catalog
  // filter — which matches nothing and empties the list, reading as "no entries
  // from Germany". A default branch that swallows unknown keys is how a new
  // facet breaks the old one.
  activeFacets.forEach(function (id) {
    var i = id.indexOf(':'), k = id.slice(0, i), v = id.slice(i + 1);
    if (k === 'fn') fns.push(v);
    else if (k === 'rp') rps.push(v);
    else if (k === 'cc') ccs.push(v);
  });
  // Source catalog is a single-select dropdown now, not a facet set.
  var srcOne = el('src').value;
  if (srcOne) srcs.push(srcOne);
  var out = DATA.filter(function (r) {
    if (r.ex) {
      // r.ex is the exclude_reason. 'no-description' is an editorial standard
      // about publisher effort; every other reason is a judgement that the thing
      // is not adoptable software. They are shown independently.
      if (r.ex === 'no-description' ? !showNoDesc : !showNotSoft) return false;
    }
    if (fns.length && !r.fx.some(function (f) { return fns.indexOf(f) >= 0; })) return false;
    if (ccs.length && !(r.cs || [r.c]).some(function (x) { return ccs.indexOf(x) >= 0; })) return false;
    if (srcs.length && !(r.ss || [r.s]).some(function (x) { return srcs.indexOf(x) >= 0; })) return false;
    if (rps.length && !(r.rp || []).some(function (x) { return rps.indexOf(x) >= 0; })) return false;
    if (lic && r.l !== lic) return false;
    if (lvf && (lvf === 'ok' ? !!r.lv : r.lv !== lvf)) return false;
    if (onlyReplaces && !(r.rp && r.rp.length)) return false;
    if (q) {
      var hay = (r.n + ' ' + r.d + ' ' + r.o + ' ' + (r.g || []).join(' ') + ' ' +
                 (r.aka || []).join(' ') + ' ' + (r.rp || []).join(' ') + ' ' +
                 (r.vs || []).map(function (i) { return DATA[i].n + ' ' + DATA[i].o; }).join(' ')
                ).toLowerCase();
      if (hay.indexOf(q) < 0) return false;
    }
    return true;
  });
  out = fold(out);
  if (sort === 'name') out.sort(function (a, b) { return a.n.toLowerCase().localeCompare(b.n.toLowerCase()); });
  // Sort by the DISPLAYED name, not the code. Once the facet started showing
  // "Germany" instead of "DE", a code sort put Germany before Denmark and the
  // list read as unsorted. Sort on what the reader can see.
  else if (sort === 'country') out.sort(function (a, b) {
    return ccLabel(a.c).localeCompare(ccLabel(b.c)) || a.n.localeCompare(b.n); });
  // Recently added. UNDATED ENTRIES SORT LAST, never first: `fs` is null for the
  // 3,070 that predate the record, and an empty string would sort them to the top
  // as if they were the newest thing in the catalogue.
  else if (sort === 'recent') out.sort(function (a, b) {
    if (!a.fs && !b.fs) return a.n.localeCompare(b.n);
    if (!a.fs) return 1;
    if (!b.fs) return -1;
    return b.fs.localeCompare(a.fs) || a.n.localeCompare(b.n); });
  else out.sort(function (a, b) { return (b.cc2 || 1) - (a.cc2 || 1) || b.ub - a.ub || a.n.localeCompare(b.n); });
  return out;
}

function stamps(r) {
  var s = '';
  // No "Recommended" stamp (retired 2026-08-14): one pill could not carry both
  // SILL's real assertion and Munich's inferred one. The field is still in
  // /entries.json as recommended_for_government. See build_ui.py for why.
  if (r.cc2 > 1) s += '<span class="stamp multi">⟪js:In⟫ ' + r.cc2 + ' ⟪js:catalogs⟫</span>';
  // A DIFFERENT claim from "In N catalogs" (listings of the same software), so a
  // different pill: N governments run their own version of it.
  if (r.vs && r.vs.length) s += '<span class="stamp multi">' + r.vs.length +
    (r.vs.length === 1 ? ' ⟪js:variant⟫' : ' ⟪js:variants⟫') + '</span>';
  if (r.lv === 'dead') s += '<span class="stamp warn">__ICON_ALERT__ ⟪js:Repo gone⟫</span>';
  else if (r.lv === 'archived') s += '<span class="stamp warn">__ICON_ALERT__ ⟪js:Archived upstream⟫</span>';
  return s;
}

function render() {
  var rs = current();
  // The denominator has to move with the toggles, or "N of M" silently compares
  // the filtered list against a universe the page is not showing.
  // NOT folded: a variant is still an entry, and the headline stat counts it.
  // The gap is explained instead, or an unfiltered page reads as filtered.
  var universe = DATA.filter(function (r) {
    if (!r.ex) return true;
    return r.ex === 'no-description' ? showNoDesc : showNotSoft;
  }).length;
  el('count').innerHTML = '<b>' + rs.length.toLocaleString(LANG) + '</b> ⟪js:of⟫ ' +
    universe.toLocaleString(LANG) + ' ⟪js:entries⟫' + (lastFolded ? ' &middot; ' + lastFolded +
    (lastFolded === 1 ? ' ⟪js:variant listed under its core⟫'
                      : ' ⟪js:variants listed under their core⟫') : '');
  var nf = activeFacets.size + (onlyReplaces ? 1 : 0) +
           (el('lic').value ? 1 : 0) + (el('lv').value ? 1 : 0) +
           (el('src').value ? 1 : 0);
  el('fcount').textContent = nf ? (nf + (nf === 1 ? ' ⟪js:filter applied⟫' : ' ⟪js:filters applied⟫')) : '';

  if (!rs.length) {
    el('list').innerHTML = '<li class="empty">⟪js:No entries match.⟫ ' +
      '<button type="button" class="fmore" id="clear2">⟪js:Clear the filters⟫</button></li>';
    el('more').hidden = true;
    var c2 = el('clear2'); if (c2) c2.onclick = clearAll;
    return;
  }
  el('list').innerHTML = rs.slice(0, visibleCount).map(function (r) {
    var link = r.u || r.h;
    var meta = [];
    if (r.l) meta.push(esc(r.l)); else meta.push('⟪js:Licence not stated by the source⟫');
    if (r.qid) meta.push(esc(r.qid));
    // Each source catalogue carries its country's flag. An entry listed by three
    // catalogues shows three flags, which is the point: it is the quickest read of
    // "who else publishes this" on a card that has no room for a sentence.
    // Unknown label -> no flag rather than a placeholder; a wrong flag asserts a
    // country the data never claimed.
    function flagged(label, href) {
      var f = SRCFLAG[label] ? SRCFLAG[label] + ' ' : '';
      return href
        ? f + '<a href="' + esc(href) + '" target="_blank" rel="noopener">' + esc(label) + '</a>'
        : f + esc(label);
    }
    var srcs = (r.ce && r.ce.length ? r.ce : []).map(function (c) {
      return flagged(c.l, c.u);
    }).join(' + ') || (r.ss || [r.s]).map(function (l) { return flagged(l); }).join(' + ');
    return '<li class="item">' +
      '<div class="cc">' + esc(r.c) + '</div>' +
      '<div class="main">' +
        '<div class="title">' +
          (link ? '<a href="' + esc(link) + '" target="_blank" rel="noopener">' + esc(r.n) + '</a>'
                : '<span class="nm">' + esc(r.n) + '</span>') + stamps(r) +
        '</div>' +
        (r.d ? '<div class="desc">' + esc(r.d) + '</div>' : '') +
        (r.rp && r.rp.length ? '<div class="rp">⟪js:Replaces⟫ ' + r.rp.map(function(p, i){
            var q = (r.rpq || [])[i];
            return '<a href="products.html#p-' + esc(pslug(p)) + '">' + esc(p) + '</a>' +
              (q ? ' <span class="rpq">(' + esc(q) + ')</span>' : '');
        }).join(', ') + '</div>' : '') +
        (r.vs && r.vs.length ? '<div class="vars">⟪js:Variants:⟫ ' + r.vs.map(function (i) {
            var v = DATA[i], vl = v.u || v.h;
            var nm = esc(v.n) + (v.o ? ' <span class="rpq">(' + esc(v.o) + ')</span>' : '');
            return vl ? '<a href="' + esc(vl) + '" target="_blank" rel="noopener">' + nm + '</a>' : nm;
          }).join(', ') + '</div>' : '') +
        (r.vo != null ? '<div class="vars">⟪js:A version of⟫ <b>' + esc(DATA[r.vo].n) + '</b></div>' : '') +
        '<div class="meta">' + meta.join(' &middot; ') + '</div>' +
        (r.ex ? '<div class="why">⟪js:Set aside:⟫ ' + esc(r.ex) + '</div>' : '') +
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
  showNoDesc = false; showNotSoft = false;
  el('fq').value = ''; el('lic').value = ''; el('lv').value = ''; el('src').value = '';
  el('onlyrep').setAttribute('aria-pressed', 'false');
  el('exnodesc').setAttribute('aria-pressed', 'false');
  el('exnotsoft').setAttribute('aria-pressed', 'false');
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
el('src').onchange = reset;
el('sort').onchange = reset;
el('clearall').onclick = clearAll;
el('onlyrep').onclick = function () {
  onlyReplaces = !onlyReplaces;
  this.setAttribute('aria-pressed', onlyReplaces ? 'true' : 'false');
  reset();
};
el('morefilters').onclick = function () {
  // el.hidden, not style.display: the page reset sets [hidden]{display:none
  // !important}, so toggling style.display would be overridden and the drawer
  // would never appear.
  var open = el('drawer').hidden;
  el('drawer').hidden = !open;
  this.setAttribute('aria-expanded', open ? 'true' : 'false');
};
el('exnodesc').onclick = function () {
  showNoDesc = !showNoDesc;
  this.setAttribute('aria-pressed', showNoDesc ? 'true' : 'false');
  reset();
};
el('exnotsoft').onclick = function () {
  showNotSoft = !showNotSoft;
  this.setAttribute('aria-pressed', showNotSoft ? 'true' : 'false');
  reset();
};
el('more').onclick = function () { visibleCount += PAGE_SIZE; render(); };

// ?rp=<product> arrives from products.html ("See in catalog"). Activated only
// if the product is a real facet value - an unknown one would silently filter
// the catalogue to nothing, which reads as "no alternatives exist".
(function () {
  var m = /[?&]rp=([^&]*)/.exec(location.search);
  if (!m) return;
  var want = decodeURIComponent(m[1].replace(/\\+/g, ' '));
  var known = PFACETS.some(function (f) { return f[0] === want; });
  if (known) activeFacets.add('rp:' + want);
})();

// ?src=<catalog label> arrives from sources.html ("See catalog entries"). Same
// guard as ?rp=: set the dropdown only if the value is one it actually offers.
// An unknown value would filter the catalogue to nothing and read as "this
// catalogue contributed no entries", which is the one thing that page exists to
// disprove. Both sides read sources.py SOURCES[key]["label"].
(function () {
  var m = /[?&]src=([^&]*)/.exec(location.search);
  if (!m) return;
  var want = decodeURIComponent(m[1].replace(/\\+/g, ' '));
  var sel = el('src');
  for (var i = 0; i < sel.options.length; i++) {
    if (sel.options[i].value === want) { sel.value = want; return; }
  }
})();

// ?cc=<country code> for completeness, validated against the facet values.
(function () {
  var m = /[?&]cc=([^&]*)/.exec(location.search);
  if (!m) return;
  var want = decodeURIComponent(m[1].replace(/\\+/g, ' ')).toUpperCase();
  if (CCFACETS.some(function (f) { return f[0] === want; })) activeFacets.add('cc:' + want);
})();

// ---- Recently added strip.
(function () {
  if (!NEWEST.length) return;            // stays hidden; see the markup comment
  el('recent').hidden = false;
  el('rtrack').innerHTML = NEWEST.map(function (r) {
    var title = r.u
      ? '<a href="' + esc(r.u) + '" target="_blank" rel="noopener">' + esc(r.n) + '</a>'
      : esc(r.n);
    return '<li class="rcard"><div class="rt">' + title + '</div>' +
      (r.d ? '<div class="rd">' + esc(r.d) + '</div>' : '') +
      // The flag carries a `title` with the country name: a bare emoji is a poor
      // label on its own, and the name is the thing a reader may actually need.
      '<div class="rm"><span class="fl" title="' + esc(ccLabel(r.c)) + '">' +
        esc(ccFlag(r.c)) + '</span>' +
      '<span>' + esc(r.s) + '</span>' +
      '<span>&middot;</span><span>' + esc(r.fs) + '</span></div></li>';
  }).join('');

  var track = el('rtrack');
  function page(dir) {
    // Scroll by a whole card plus its gap, so a card never lands half-cut.
    var card = track.querySelector('.rcard');
    var step = card ? card.getBoundingClientRect().width + 10 : 240;
    track.scrollBy({ left: dir * step * 2, behavior: 'smooth' });
  }
  el('rprev').onclick = function () { page(-1); };
  el('rnext').onclick = function () { page(1); };

  function arrows() {
    // Disabled at the ends rather than hidden, so the control does not move.
    //
    // ⚠ TOLERANCE, not `<= 0`. The track carries 2px of padding and
    // scroll-snap-align, and it settles at scrollLeft 2 at rest — measured, so
    // an exact test left the left arrow enabled on a strip already at its start.
    // Sub-pixel rounding puts the right end a fraction short for the same reason.
    var EPS = 4;
    var max = track.scrollWidth - track.clientWidth;
    el('rprev').disabled = track.scrollLeft <= EPS;
    el('rnext').disabled = track.scrollLeft >= max - EPS;
  }
  track.addEventListener('scroll', arrows);
  window.addEventListener('resize', arrows);
  arrows();

  // "See all" is the strip's whole reason for being only ten long: it hands the
  // reader the full list in the table, ordered the same way.
  el('rall').onclick = function () {
    el('sort').value = 'recent';
    reset();
    el('list').scrollIntoView({ behavior: 'smooth', block: 'start' });
  };
})();

renderFacets();
render();
</script>
"""
