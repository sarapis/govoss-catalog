#!/usr/bin/env python3
"""Shared chrome for every generated page: tokens, fonts, topbar, footer, head.

WHY THIS FILE EXISTS
--------------------
Three builders (build_ui, build_sources, build_api) now render the same design
system. Before this, each one carried its own copy of the CSS, which is exactly
how `sources.py` came to exist for source labels: two copies of a value are two
values, and they disagree the moment one is edited. Every colour, font, radius
and shadow lives here once.

THE BRACE RULE, AND WHY THIS FILE ESCAPES IT
--------------------------------------------
The builders hold their markup in f-strings, so every literal `{` and `}` in CSS
has to be doubled — the single most common way to break them. **Everything in
this module is a PLAIN string, never an f-string**, so braces are literal and
CSS can be pasted in and read as CSS. Keep it that way: if you need a value
interpolated, use `.replace()` or a `%s`, not an f-string. The builders then
drop `theme.CSS` into their own f-strings through a `{theme.CSS}` slot, which
does not re-scan the contents for braces.

DESIGN AUTHORITY
----------------
Values come from the Civic Tech Field Guide design system supplied in the
restyle handoff. Do not invent colours, type or shadows outside these tokens.
Light-only by decision — see LIGHT-ONLY below.
"""

# --------------------------------------------------------------------------
# Fonts. Self-hosted, NOT a CDN.
#
# The design system loads these from fonts.googleapis.com. That is unusable
# here for two independent reasons: the pages are self-contained by rule, and
# the readership is European public-sector staff, for whom loading fonts from
# Google is a live GDPR objection (German courts have found against it). So the
# woff2s are vendored in fonts/ and served same-origin.
#
# Variable weight 400-700 in one file per subset: 8 files, 280 KB total, but
# unicode-range means a typical reader fetches only the ~103 KB latin set.
#
# Subsets, chosen from what the catalogue actually contains:
#   latin + latin-ext -> every European source (fr, de, pt, da, cs...)
#   cyrillic(-ext)    -> the 171 deliberately-untranslated Bulgarian entries.
#                        Inter carries the descriptions and is the only one of
#                        the three families with Cyrillic, so Space Grotesk and
#                        Archivo are latin-only on purpose.
#   NOT vietnamese/greek -> no source produces either.
#   CJK is in none of them; Taiwan's 57 Chinese names fall back to the system
#   face, which is correct — no webfont covers CJK at a sane size.
#
# OFL requires the licence travel with the fonts: fonts/OFL-*.txt, copied to
# site/fonts/ by build_site.sh.
# --------------------------------------------------------------------------

_FACES = [
    ("Space Grotesk", "space-grotesk-latin.woff2",
     "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,"
     "U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,"
     "U+2215,U+FEFF,U+FFFD"),
    ("Space Grotesk", "space-grotesk-latin-ext.woff2",
     "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,"
     "U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,"
     "U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF"),
    ("Archivo", "archivo-latin.woff2",
     "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,"
     "U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,"
     "U+2215,U+FEFF,U+FFFD"),
    ("Archivo", "archivo-latin-ext.woff2",
     "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,"
     "U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,"
     "U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF"),
    ("Inter", "inter-latin.woff2",
     "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,"
     "U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,"
     "U+2215,U+FEFF,U+FFFD"),
    ("Inter", "inter-latin-ext.woff2",
     "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,"
     "U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,"
     "U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF"),
    ("Inter", "inter-cyrillic.woff2",
     "U+0301,U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116"),
    ("Inter", "inter-cyrillic-ext.woff2",
     "U+0460-052F,U+1C80-1C8A,U+20B4,U+2DE0-2DFF,U+A640-A69F,U+FE2E-FE2F"),
]

FONT_FACE_CSS = "\n".join(
    "@font-face{font-family:'%s';font-style:normal;font-weight:400 700;"
    "font-display:swap;src:url('/fonts/%s') format('woff2');"
    "unicode-range:%s;}" % (fam, f, rng)
    for fam, f, rng in _FACES
)


# --------------------------------------------------------------------------
# Tokens.
#
# LIGHT-ONLY, by decision. The previous build had three-state theming; the
# approved designs are light-only, so the dark branches are gone rather than
# left half-maintained. Because of that, `body` MUST paint its own background
# explicitly — a page with a transparent body borrows whatever ground the host
# paints, which on a dark-mode browser renders dark text on dark.
# --------------------------------------------------------------------------

TOKENS_CSS = """
:root{
  /* neutrals */
  --white:#FFFFFF; --ink-900:#19191E; --ink-600:#4D4D4A; --ink-500:#6B6B68;
  --ink-400:#9FA4A3; --line-300:#CDCDCB; --line-200:#ECECEC;
  --paper-100:#F1F1F1; --paper-50:#FBFBFB;
  /* violet (primary) */
  --violet-700:#1F1A73; --violet-500:#574FD9; --violet-300:#877DFF; --violet-100:#F1F0FF;
  /* green / mint */
  --green-700:#006348; --green-500:#01B583; --mint-300:#67F5C2; --mint-100:#EAFFF9;
  --shadow-ink:#181818;

  /* semantic aliases - components read THESE, never the base values */
  --bg:var(--paper-50); --bg-alt:var(--paper-100); --surface:var(--white);
  --ink:var(--ink-900); --ink-soft:var(--ink-500); --ink-faint:var(--ink-400);
  --border:var(--line-300); --border-soft:var(--line-200);
  --primary:var(--violet-500); --primary-deep:var(--violet-700);
  --primary-tint:var(--violet-100);
  --green:var(--green-500); --mint:var(--mint-300);

  /* type */
  --font-display:'Space Grotesk',ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --font-ui:'Archivo',ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --font-body:'Inter',ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --font-mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;

  /* radius */
  --r-chip:5px; --r-med:10px; --r-card:14px; --r-table:20px; --r-pill:999px;

  /* hard offset shadows, zero blur - the CTFG signature */
  --shadow-bar:2px 2px 0 0 var(--shadow-ink);
  --shadow-pill:2px 2px 0 0 var(--primary-deep);
  --shadow-green:2px 2px 0 0 var(--green-700);
  --divider:1px dashed var(--ink);
}
"""

# --------------------------------------------------------------------------
# Base + chrome CSS shared by all three pages.
# --------------------------------------------------------------------------

BASE_CSS = """
*{box-sizing:border-box;}
html{-webkit-text-size-adjust:100%;}
body{
  margin:0;
  background:var(--bg);           /* explicit: see LIGHT-ONLY above */
  color:var(--ink);
  font-family:var(--font-body);
  font-size:16px;
  line-height:1.5;
  letter-spacing:-0.01em;
  -webkit-font-smoothing:antialiased;
}
a{color:var(--primary);text-underline-offset:2px;}
a:hover{color:var(--primary-deep);}
h1,h2,h3{font-family:var(--font-display);font-weight:700;letter-spacing:-0.02em;
  line-height:1.1;margin:0;text-wrap:balance;}
h1{font-size:48px;} h2{font-size:34px;} h3{font-size:24px;line-height:1.25;}
p{margin:0;}
.wrap{max-width:1440px;margin:0 auto;padding:0 40px;}
.overline{font-family:var(--font-ui);font-size:13px;font-weight:600;
  letter-spacing:.14em;text-transform:uppercase;color:var(--ink-600);}
.mono{font-family:var(--font-mono);}
.num{font-variant-numeric:tabular-nums;}
.dashed{border:0;border-top:var(--divider);width:100%;margin:0;}
:focus-visible{outline:2px solid var(--primary);outline-offset:2px;border-radius:3px;}

/* buttons */
.btn{font-family:var(--font-ui);font-size:13px;font-weight:600;letter-spacing:.05em;
  text-transform:uppercase;border-radius:var(--r-pill);padding:11px 22px;
  border:1px solid transparent;cursor:pointer;display:inline-flex;align-items:center;
  gap:8px;text-decoration:none;transition:background-color 120ms,color 120ms,transform 120ms;}
.btn-primary{background:var(--primary);color:var(--white);}
.btn-primary:hover{background:var(--primary-deep);color:var(--white);}
.btn-ghost{background:var(--surface);color:var(--ink);border-color:var(--border);}
.btn-ghost:hover{background:var(--bg-alt);color:var(--ink);}
.btn:active{transform:translateY(1px);}

/* texture - SVG data URIs, no external images, so they port cleanly */
.tex{position:relative;overflow:hidden;
  background-image:radial-gradient(120% 90% at 15% 0%,var(--violet-100) 0%,transparent 55%),
                   radial-gradient(110% 80% at 92% 100%,var(--mint-100) 0%,transparent 60%);}
.tex::before{content:"";position:absolute;inset:-40px;opacity:.16;pointer-events:none;
  background-image:
    repeating-radial-gradient(circle at 30% 40%,transparent 0 22px,var(--ink) 22px 23px),
    repeating-radial-gradient(circle at 78% 65%,transparent 0 30px,var(--ink) 30px 31px);
  -webkit-mask-image:linear-gradient(#000,transparent 92%);
          mask-image:linear-gradient(#000,transparent 92%);}
.tex::after{content:"";position:absolute;inset:0;pointer-events:none;opacity:.5;
  mix-blend-mode:multiply;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.4'/%3E%3C/svg%3E");}
.tex > *{position:relative;z-index:1;}

/* utility bar */
.ubar{background:var(--primary);color:var(--white);height:36px;display:flex;align-items:center;}
.ubar .wrap{display:flex;align-items:center;justify-content:space-between;gap:16px;width:100%;}
.ubar a{color:var(--mint-300);text-decoration:none;}
.ubar a:hover{color:var(--white);text-decoration:underline;}
.ubar .u-l,.ubar .u-r{display:flex;align-items:center;gap:20px;
  font-family:var(--font-ui);font-size:11px;font-weight:600;letter-spacing:.14em;
  text-transform:uppercase;}
.ubar .u-pre{opacity:.75;}
.ubar .u-ctfg{color:var(--white);text-decoration:underline;
  text-decoration-color:var(--mint-300);text-decoration-thickness:2px;}
.ubar .u-r{overflow-x:auto;scrollbar-width:none;}
.ubar .u-r::-webkit-scrollbar{display:none;}

/* topbar */
/* min-height + flex centring, NOT height:88px with a height:100% child.
   The child percentage resolved against an auto-height parent once the mobile
   query set the bar to height:auto, and the topbar rendered 522px tall. There
   is no percentage height here now, so that cannot recur. */
.topbar{min-height:88px;background:var(--bg);border-bottom:var(--divider);
  display:flex;align-items:center;}
.topbar .wrap{display:flex;align-items:center;justify-content:space-between;
  width:100%;gap:24px;}
.brand{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--ink);}
.brand .bmark{font-family:var(--font-display);font-weight:700;font-size:26px;
  letter-spacing:-0.03em;color:var(--primary);}
.brand .bsub{font-family:var(--font-ui);font-size:9px;font-weight:600;letter-spacing:.1em;
  text-transform:uppercase;color:var(--ink-600);line-height:1.15;max-width:9em;}
.nav{display:flex;align-items:center;gap:26px;}
.nav a{font-family:var(--font-ui);font-weight:600;font-size:15px;color:var(--ink);
  text-decoration:none;}
.nav a:hover{color:var(--primary);}
.nav a[aria-current="page"]{color:var(--primary);}
.topbar .t-r{display:flex;align-items:center;gap:12px;}

/* footer */
.foot{margin-top:56px;padding:48px 0 44px;border-top:var(--divider);}
.foot .cols{display:flex;flex-wrap:wrap;gap:32px 48px;}
.foot .col{display:flex;flex-direction:column;gap:8px;min-width:150px;}
.foot .col h4{font-family:var(--font-ui);font-size:11px;font-weight:600;
  letter-spacing:.14em;text-transform:uppercase;color:var(--ink-600);margin:0;}
.foot .col a{font-size:12px;color:var(--ink);text-decoration:none;}
.foot .col a:hover{color:var(--primary);text-decoration:underline;}
.foot .legal{display:flex;flex-wrap:wrap;align-items:center;gap:10px 18px;
  font-size:12px;color:var(--ink-600);}
.foot .pub{display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
.foot .pub .mark{font-family:var(--font-display);font-weight:700;font-size:20px;
  letter-spacing:-0.02em;color:var(--ink);text-decoration:none;}
.foot .hair{width:1px;align-self:stretch;background:var(--border);min-height:34px;}

@media (max-width:720px){
  .wrap{padding:0 20px;}
  h1{font-size:34px;} h2{font-size:26px;}
  .topbar{min-height:0;padding:14px 0;}
  .topbar .wrap{flex-wrap:wrap;row-gap:12px;}
}
@media (prefers-reduced-motion:reduce){
  *{transition:none !important;animation:none !important;}
}
"""

CSS = TOKENS_CSS + BASE_CSS


# --------------------------------------------------------------------------
# Chrome fragments.
# --------------------------------------------------------------------------

# The utility bar link set in the handoff is flagged there as a reconstruction
# of the global CTFG products, to be confirmed against nyc.civictech.guide.
# Until it is confirmed, we ship ONE link to civictech.guide rather than five
# guessed deep links: a wrong nav item is a broken promise to the reader, and
# this page has no way to know it broke.
UTILITY_BAR = """
<div class="ubar"><div class="wrap">
  <div class="u-l"><span class="u-pre">Part of the</span>
    <a class="u-ctfg" href="https://civictech.guide">Civic Tech Field Guide</a></div>
  <div class="u-r"><a href="https://civictech.guide">The guide</a></div>
</div></div>
"""


def topbar(active=""):
    """Site header. `active` is one of catalog | sources | api."""
    def item(href, label, key):
        cur = ' aria-current="page"' if key == active else ""
        return '<a href="%s"%s>%s</a>' % (href, cur, label)
    return """
<header class="topbar"><div class="wrap">
  <a class="brand" href="/">
    <span class="bmark">govoss</span>
    <span class="bsub">Government<br>open source</span>
  </a>
  <nav class="nav">%s %s %s</nav>
  <div class="t-r">
    <a class="btn btn-primary" href="/#submit">Submit a catalog</a>
  </div>
</div></header>
""" % (item("/", "Catalog", "catalog"),
       item("/sources.html", "Sources", "sources"),
       item("/api.html", "API", "api"))


# Published by Sarapis, affiliated with CTFG — not a CTFG property.
#
# The Sarapis mark is NOT in the handoff bundle and the brief says to use the
# real one rather than redraw it, so the publisher slot is a text wordmark
# until the asset arrives. It is deliberately not a placeholder box: a missing
# logo should read as a considered wordmark, not as a broken image.
#
# LICENCE BADGES: the handoff pairs a CC BY-NC-SA badge with "data CC BY 4.0".
# Shipping that image would tell a scanning reader the data is NonCommercial —
# the opposite of what the repo grants, and a direct deterrent to the reuse
# this catalogue exists to enable. The terms are stated in words instead, each
# scoped to what it actually covers.
FOOTER = """
<footer class="foot tex"><div class="wrap">
  <div class="cols">
    <div class="col">
      <h4>Catalog</h4>
      <a href="/">Browse entries</a>
      <a href="/sources.html">Sources &amp; harvest status</a>
      <a href="/api.html">API for agents</a>
      <a href="/#submit">Submit a catalog</a>
    </div>
    <div class="col">
      <h4>Data</h4>
      <a href="/entries.json">entries.json</a>
      <a href="/sources.json">sources.json</a>
      <a href="/by-product.json">by-product.json</a>
      <a href="/llms.txt">llms.txt</a>
    </div>
    <div class="col">
      <h4>Project</h4>
      <a href="https://github.com/sarapis/govoss-catalog">Source on GitHub</a>
      <a href="https://github.com/sarapis/govoss-catalog/issues/new">Report a correction</a>
      <a href="https://civictech.guide">Civic Tech Field Guide</a>
    </div>
  </div>
  <hr class="dashed" style="margin:28px 0 20px">
  <div class="pub">
    <a class="mark" href="https://sarapis.org">Sarapis</a>
    <span class="hair"></span>
    <span class="legal" style="max-width:52em">
      Published by Sarapis, in affiliation with the Civic Tech Field Guide.
      Catalogue data <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>;
      code <a href="https://github.com/sarapis/govoss-catalog/blob/main/LICENSE">MIT</a>.
      Individual entries remain under the terms of the government catalogue that
      published them &mdash; every entry links back to its source.
    </span>
  </div>
</div></footer>
"""


def head(title, description, canonical=""):
    """The <head> contents, including the agent affordances.

    Affordance 1 of 4 is the HTML comment ABOVE <title>, for agents that read
    raw HTML rather than rendering it. Affordance 2 is the alternate links and
    the meta description. Both must stay ahead of any visible markup. (3 is the
    on-page banner, in build_ui; 4 is the endpoint paths themselves.)

    The description no longer says "eight European national catalogues" — that
    was wrong in the shipped site: 17 catalogues, 3,070 entries, 15 countries,
    and not only Europe.
    """
    return """<!--
  govoss-catalog - a union catalogue of government open source software.

  PLEASE DO NOT SCRAPE THIS PAGE. Everything here is available as JSON:
    GET /entries.json        every entry, one request, no key, no pagination
    GET /meta.json           counts, category enum, sources, generated_at
    GET /by-product.json     proprietary product -> open source alternatives
    GET /by-category/<key>.json
    GET /sources.json        the catalogues harvested, and those rejected
    GET /status.json         freshness, last run, changelog
  CORS is open. Full notes for agents: /llms.txt and /api.html
-->
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s</title>
<meta name="description" content="%s">
<link rel="alternate" type="application/json" href="/entries.json" title="All entries as JSON">
<link rel="alternate" type="application/json" href="/meta.json" title="Catalogue metadata">
<link rel="alternate" type="application/json" href="/status.json" title="Build status">
%s""" % (title, description,
         ('<link rel="canonical" href="%s">\n' % canonical) if canonical else "")
