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
Values come from `@wegovnyc/design-tokens`, vendored in vendor/wegovnyc/ and
applied through the `govoss` brand variant. Do not invent colours, type or
shadows outside these tokens. Light-only by decision — see LIGHT-ONLY below.

govoss ran on the Civic Tech Field Guide design system until 2026-08-13, when it
moved onto the shared Sarapis system by owner decision. CTFG remains a consumer
of this catalogue's data; it is no longer the brand, so its utility bar, mark
and CMS-fed footer columns are gone. DESIGN-BRIEF.md and UPSTREAM-CTFG.md are
kept as the historical record of that relationship — including three defects we
reported that CTFG fixed in its v2.0.0.
"""
import os
import re

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
    # Marcellus sets exactly one word - the Sarapis wordmark in the footer -
    # so it is latin-only on purpose. Taken from next.sarapis.org, whose
    # --sds-font-logo is "Marcellus", Georgia, "Times New Roman", serif.
    ("Marcellus", "marcellus-latin.woff2",
     "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,"
     "U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,"
     "U+2215,U+FEFF,U+FFFD"),
]

def _face(fam, f, rng):
    # Marcellus is a single-weight family. Declaring "400 700" on it would let
    # the browser synthesise a fake bold; the others are genuine variable fonts.
    w = "400" if fam == "Marcellus" else "400 700"
    return ("@font-face{font-family:'%s';font-style:normal;font-weight:%s;"
            "font-display:swap;src:url('/fonts/%s') format('woff2');"
            "unicode-range:%s;}" % (fam, w, f, rng))


FONT_FACE_CSS = "\n".join(_face(*x) for x in _FACES)


# --------------------------------------------------------------------------
# Tokens.
#
# LIGHT-ONLY, by decision. The previous build had three-state theming; the
# approved designs are light-only, so the dark branches are gone rather than
# left half-maintained. Because of that, `body` MUST paint its own background
# explicitly — a page with a transparent body borrows whatever ground the host
# paints, which on a dark-mode browser renders dark text on dark.
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# Tokens. VENDORED from @wegovnyc/design-tokens, not transcribed.
#
# theme.py used to re-declare every hex by hand. That put a copy of somebody
# else's values in our repo with no link back to them - the exact drift this
# module exists to prevent between our three builders, reintroduced one level up
# at the boundary we do not control. The token files now live in
# vendor/wegovnyc/ and are inlined at build time, so an upstream fix arrives as
# a file drop instead of another round of retyping.
#
# Vendored: core.css (reference palette + ~90 --wg-* semantics) and
# variant-govoss.css (govoss's remap). NOT vendored: the other products'
# variants, index.css (loads every variant; govoss renders one), and the Node
# lint. See vendor/wegovnyc/README.md.
#
# LIGHT-ONLY, by decision. The DS tokens are light-only already. Because of that
# `body` MUST paint its own background explicitly - a page with a transparent
# body borrows whatever ground the host paints.
# --------------------------------------------------------------------------

_VENDOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor", "wegovnyc")
_DS_FILES = ("core.css", "variant-govoss.css")


def _vendored_tokens():
    parts = []
    for name in _DS_FILES:
        with open(os.path.join(_VENDOR, name)) as fh:
            parts.append("/* ---- vendored from @wegovnyc/design-tokens: %s ---- */\n%s"
                         % (name, fh.read()))
    return "\n".join(parts)


# Everything below is OURS, applied after the vendored tokens so it wins.
#
# THIS IS AN ALIAS LAYER, and that is a deliberate divergence from how wegov.nyc
# and UNNYC consume the package. They migrated every rule to read `--wg-*`
# directly and deleted their alias layers (see KI wegovnyc-design-system), for a
# good reason: an alias that carries its own VALUE is unreachable by the variant
# system. These aliases carry no values - every one resolves to a `--wg-*`
# semantic - so a variant remap still propagates, which is the property that
# rule protects. What it buys is not touching ~250 `var(--x)` call sites spread
# across Python template strings, where a missed one fails silently.
#
# ⚠ THE MAPPING IS BY ROLE AND BY MEASURED CONTRAST, NOT BY NAME OR BY EYE.
# Two family semantics CANNOT be used where their names suggest, because govoss
# holds a 5.17:1 floor from its WCAG 2.1 AA audit and they fail it as text:
#
#     --wg-text-muted   2.90:1  <- govoss's tertiary tier is used 24x as TEXT
#     --wg-accent       3.15:1  <- govoss's --primary is used 26x, incl. links
#
# (Recomputed 2026-08-14 from the vendored CSS against the page ground #FBFBFB.
# These read 3.00 and 3.26 before; the real values are worse, not better, so the
# conclusion stood - but recompute rather than copy. The 5.13/13.15/8.69/5.31
# figures below all verified exact.)
#
# Mapping those naively would have broken the floor in 50 places. Both are fine
# for fills and non-text marks; they are simply not text colours here.
OVERRIDES_CSS = """
:root{
  /* ---- text tiers. Measured on the govoss page ground (#FBFBFB) ------------
     govoss carries THREE passing tiers; the family ships two plus a muted tier
     that fails. The mid tier borrows --wg-brand-light, which lands within
     0.2 of the value it replaces. Outgoing -> incoming:
       primary    17.4 -> 13.15   (--wg-text, navy rather than near-black)
       secondary   8.20 ->  8.69  (--wg-brand-light)
       tertiary    5.17 ->  5.31  (--wg-text-secondary) - slightly BETTER */
  --ink:        var(--wg-text);
  --ink-900:    var(--wg-text);
  --ink-800:    var(--wg-text);
  --ink-600:    var(--wg-brand-light);
  --ink-soft:   var(--wg-brand-light);
  --ink-500:    var(--wg-text-secondary);
  --ink-faint:  var(--wg-text-secondary);
  --ink-400:    var(--wg-border);        /* NON-TEXT ONLY, as upstream had it */

  /* ---- surfaces ---------------------------------------------------------- */
  --white:      var(--wg-text-inverse);
  --surface:    var(--wg-surface);
  --bg:         var(--wg-surface-warm);  /* the variant makes this cool #FBFBFB */
  --paper-50:   var(--wg-surface-warm);
  --bg-alt:     var(--wg-surface-band);
  --paper-100:  var(--wg-surface-band);
  --border:     var(--wg-border);
  --border-soft:var(--wg-border);
  --line-300:   var(--wg-border);
  --line-200:   var(--wg-border);

  /* ---- accent. --primary is govoss's link and emphasis colour and IS used as
     text, so it takes --wg-accent-strong (5.13:1), not --wg-accent (3.15:1).
     The brights stay reachable for fills via --primary-tint / --primary-lt. */
  --primary:      var(--wg-accent-strong);
  --primary-deep: var(--wg-brand);
  --primary-lt:   var(--wg-accent);
  --primary-lter: var(--wg-accent-soft);
  /* NOT --wg-accent-soft: that is un-blue-LIGHT (#7BB4E8), a mid blue, where
     govoss uses this token as a PALE ground behind accent text. Measured
     2.41:1 on the products toggle - a hard AA failure the audit caught. The
     pale navy band is the family's actual "tinted ground" token. */
  --primary-tint: var(--wg-surface-band);
  --link:         var(--wg-accent-strong);
  --link-hover:   var(--wg-brand);

  /* ---- success tones. --green is a FILL, --green-text is the text form;
     upstream drew that distinction and it survives here. These once dressed a
     "Recommended" seal, retired 2026-08-14; they now carry the multi-catalogue
     stamp, the sources page state marks and the API do/don't tags. */
  --green:      var(--wg-success);
  --green-text: var(--wg-success-text);
  --green-line: var(--wg-success-text);
  --on-green:   var(--wg-text-inverse);
  --verified:   var(--wg-success);
  --mint:       var(--wg-success-surface);
  --mint-100:   var(--wg-success-surface);
  --mint-300:   var(--wg-success-surface);

  /* ---- elevation. The hard-offset shadow (2px 2px 0) was the CTFG signature
     and goes with it; the family's is a soft ramp. This is the single most
     visible change on the page and it is intended, not incidental. */
  --shadow-ink:  var(--wg-brand-deep);
  --shadow-bar:  var(--wg-shadow-sm);
  --shadow-pill: var(--wg-shadow-sm);
  --shadow-green:var(--wg-shadow-sm);
  --shadow-soft: var(--wg-shadow-md);
  --divider:     1px dashed var(--wg-border);

  /* ---- radii: aliases onto the family scale, so a change upstream lands. */
  --r-chip:var(--wg-radius-sm); --r-med:var(--wg-radius-md);
  --r-card:var(--wg-radius-lg); --r-table:var(--wg-radius-xl);
  --r-pill:var(--wg-radius-pill);

  /* ---- type. The package names families but ships no @font-face; govoss
     self-hosts nine woff2 same-origin because a Google Fonts request is a live
     GDPR objection for European public-sector readers. --wg-font-display is
     remapped to Space Grotesk in variant-govoss.css for the same reason. */
  --font-display:var(--wg-font-display);
  --font-body:var(--wg-font-body);
  --font-ui:'Archivo',ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --font-mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;

  /* OURS - not a package token. The Sarapis wordmark face, matching
     next.sarapis.org's --sds-font-logo. */
  --font-logo:'Marcellus',Georgia,'Times New Roman',serif;
}
"""

def tokens_version():
    """The vendored package release, read from vendor/wegovnyc/README.md.

    The package's CSS files carry no version string of their own - unlike the
    CTFG set this replaced, where every file stamped the same v-string and all
    four agreeing WAS the check. So the README carries it, written by whoever
    copies the files, and the commit is recorded beside it. That is weaker: it
    is an assertion by the copier rather than a property of the copy. It is
    still worth having, because it makes "which release is this?" answerable
    without diffing against the package repo.

    --wg-brand-id is the runtime check that survives regardless: it resolves to
    "govoss" only if the variant file is present and applied.
    """
    readme = os.path.join(_VENDOR, "README.md")
    with open(readme) as fh:
        m = re.search(r"v(\d+\.\d+\.\d+)", fh.read()[:400])
    if not m:
        raise SystemExit("vendor/wegovnyc/README.md: no version stamp - "
                         "record the release that was copied")
    return m.group(1)


TOKENS_VERSION = tokens_version()
TOKENS_CSS = _vendored_tokens() + OVERRIDES_CSS


def assert_variant_live(html):
    """The brand variant must actually be APPLIED, not merely present.

    This is the one failure mode the design system has already had once, on
    wegov.nyc: `wegov-theme-civic.css` and `wegov-theme-tool.css` existed, were
    never imported and never applied to any subtree, so every semantic silently
    resolved to the wrong brand's values for months (KI wegovnyc-design-system,
    "the variant mechanism was dead code").

    govoss would fail differently and more visibly: variant-govoss.css is what
    remaps --wg-font-display to the self-hosted Space Grotesk, so an unapplied
    variant falls back to the family's 'DM Serif Display' - a face this repo
    deliberately does not ship, because a Google Fonts request is a GDPR
    objection for its readers. The page would silently render in Georgia.

    Cheap, deterministic, and it runs on every build.

    ⚠ MUST match the ROOT TAG, not a substring of the page. The first version of
    this check did `'data-brand="govoss"' not in html` and passed even with the
    attribute deleted - because the vendored variant file's own comment contains
    the literal text `[data-brand="govoss"]`, and that comment is inlined into
    every page. A guard that can only pass is not a guard. Caught by deleting the
    attribute and watching the build succeed; test guards adversarially.
    """
    m = re.search(r"<html\b[^>]*>", html)
    if not m:
        raise SystemExit("theme: no root element in the built page")
    tag = m.group(0)
    if "wg-govoss" not in tag and "govoss" not in tag:
        raise SystemExit(
            "theme: the govoss variant is not applied to the root element - "
            "every --wg-* semantic is resolving to the family default, and the "
            "display font falls back to a face this repo does not vendor.\n"
            "   root tag was: " + tag)
    return html

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
/* WCAG 2.4.1 Bypass Blocks. There are 45 tab stops before the first result on
   the catalog page - the facet sidebar alone is ~30 buttons - so a keyboard
   user had no way past them. Visually hidden until focused. */
.skip{position:absolute;left:-9999px;top:0;z-index:100;background:var(--surface);
  color:var(--ink);border:1px solid var(--ink);border-radius:0 0 var(--r-chip) 0;
  padding:12px 18px;font-family:var(--font-ui);font-size:13px;font-weight:600;}
.skip:focus{left:0;}

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
  background-image:radial-gradient(120% 90% at 15% 0%,var(--wg-accent-soft) 0%,transparent 55%),
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

/* The utility bar's CSS lived here. It was deleted 2026-08-14: the bar itself
   went on 2026-08-13 with the CTFG chrome, utility_bar() has returned only the
   skip link ever since, and no built page contains `class="ubar"` - so 13 rules
   were shipping to every reader for markup that does not exist.

   TWO LESSONS SURVIVE THE MARKUP. They are rules 3 and 7 in DESIGN-BRIEF.md,
   and this strip is the evidence they cite, so they are kept here rather than
   deleted with the code that earned them. Build any fixed-height strip this way:

     .strip .wrap,
     .strip .side  {min-width:0;}                      <- see below
     .strip .side  {overflow-x:auto;scrollbar-width:none;}
     @media (max-width:720px){ .strip a,.strip span{white-space:nowrap;} }

   1. min-width:0 is load-bearing. A flex item defaults to min-width:auto and
      refuses to shrink below its content, so the links pushed the PAGE wider
      than the viewport instead of scrolling inside their own strip. overflow-x
      alone does not fix it - the item has to be allowed to shrink first.
   2. A fixed-height strip must never wrap. At 375px "Part of the" wrapped to
      three lines inside a 36px bar and was clipped by the bar's own height. */

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
.brand .bsep{width:1px;height:26px;background:var(--border);margin:0 4px;}
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
/* A SENTENCE, not a chip row. This was display:flex with a gap, which made
   every text node and link its own flex item - so the punctuation detached and
   "MIT" wrapped onto a line by itself. Prose gets prose layout. */
/* Full width by decision (2026-08-14) — see the note in _ui_template.py. */
.foot .legal{font-size:12px;line-height:1.6;color:var(--ink-600);}
.foot .pub{display:flex;align-items:center;gap:16px;flex-wrap:wrap;}
.sds-logo{align-items:center;gap:.625rem;display:inline-flex;text-decoration:none;
  color:var(--ink);}
.sds-logo__mark{width:36px;height:36px;}
.sds-logo__word{font-family:var(--font-logo);letter-spacing:.05em;text-transform:uppercase;
  color:currentColor;font-size:1.5rem;font-weight:400;line-height:1;}
.foot .hair{width:1px;align-self:stretch;background:var(--border);min-height:34px;}

@media (max-width:720px){
  .wrap{padding:0 20px;}
  /* the publisher/legal divider is only meaningful side by side; once they
     stack it is a line dangling off the end of the wordmark */
  .foot .hair{display:none;}
  /* (The two .ubar rules that were here went with the bar on 2026-08-14. The
     no-wrap lesson is recorded with the rest of that strip's CSS above.) */
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

# (The utility bar this once described is gone; see utility_bar() below.) Not from a
# hand-copied list. ctfg_nav.py pulls Payload's `Main Menu` at build time, so
# when CTFG edits its menu this bar follows on the next weekly run and nobody has
# to remember this repo exists. The handoff shipped a guessed five-link set with
# a note to confirm it; this is the confirmation.
def utility_bar(nav=None):
    """The CTFG utility strip is GONE (2026-08-13, owner decision).

    govoss no longer presents as part of the Civic Tech Field Guide network, so
    the "Part of the Civic Tech Field Guide" bar and its CMS-fed link row are
    removed. CTFG remains a data consumer and a friend; it is simply not the
    brand. The skip link it used to carry is kept - it is an accessibility
    affordance, not chrome, and it must stay the first focusable element.

    `nav` is accepted and ignored so the four page builders keep one call shape
    while ctfg_nav.py is retired.
    """
    return '<a class="skip" href="#main">Skip to content</a>\n'


def _esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def topbar(active=""):
    """Site header. `active` is one of catalog | sources | api.

    The CTFG mark that used to sit right of the wordmark is GONE (2026-08-13):
    govoss is not presented as a CTFG chapter any more. The lockup is now just
    the govoss wordmark and its subtitle, set in live type so it matches the
    page's own Space Grotesk and stays selectable and searchable.
    """
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
""" % (
       item("/", "Catalog", "catalog"),
       item("/sources.html", "Sources", "sources"),
       item("/api.html", "API", "api"))


# Published by Sarapis, affiliated with CTFG - not a CTFG property.
#
# The Sarapis lockup is the REAL one, pulled from next.sarapis.org rather than
# redrawn: /sarapis-mark.png at 36px beside the word in Marcellus, uppercase,
# .05em tracking, weight 400 - which is exactly what that site's `.sds-logo`
# and `--sds-font-logo` specify. The design brief said to use the real mark and
# not redraw it; this is that.
#
# LICENCE BADGES: the handoff pairs a CC BY-NC-SA badge with "data CC BY 4.0".
# Shipping that image would tell a scanning reader the data is NonCommercial -
# the opposite of what the repo grants, and a direct deterrent to the reuse this
# catalogue exists to enable. The terms are stated in words instead, each scoped
# to what it actually covers.
#
# The four CMS-fed "Footer - <group>" columns are GONE (2026-08-13). They were
# CTFG's network links, kept in step by fetching cms.civictech.guide at build
# time; govoss is not part of that network any more. What replaces them is
# govoss's own material, which is what a reader of THIS page wants anyway.
#
# Side effect worth having: with ctfg_nav.py retired, the build makes no network
# request at all. A weekly unattended run can no longer be affected by a third
# party's CMS being slow or down.
def footer(nav=None):
    """`nav` is accepted and ignored, so the four builders keep one call shape."""
    cols = (
        '<div class="col"><h4>This catalogue</h4>'
        '<a href="/">Browse entries</a>'
        '<a href="/products.html">Proprietary software</a>'
        '<a href="/sources.html">Sources &amp; harvest status</a>'
        '<a href="/api.html">API for agents</a>'
        '</div>'
        '<div class="col"><h4>Data</h4>'
        '<a href="/entries.json">entries.json</a>'
        '<a href="/by-product.json">by-product.json</a>'
        '<a href="/meta.json">meta.json</a>'
        '<a href="/llms.txt">llms.txt</a>'
        '</div>'
        '<div class="col"><h4>Project</h4>'
        '<a href="https://github.com/sarapis/govoss-catalog">Source on GitHub</a>'
        '<a href="https://github.com/sarapis/govoss-catalog/issues">Report a problem</a>'
        '<a href="/sources.html#surveyed">Catalogues we rejected, and why</a>'
        '</div>'
    )
    return """
<footer class="foot tex"><div class="wrap">
  <div class="cols">__COLS__</div>
  <hr class="dashed" style="margin:28px 0 20px">
  <div class="pub">
    <a class="sds-logo" href="https://sarapis.org">
      <img class="sds-logo__mark" src="/sarapis-mark.png" alt="" width="36" height="36">
      <span class="sds-logo__word">Sarapis</span>
    </a>
    <span class="hair"></span>
    <span class="legal">
      Published by Sarapis.
      Catalogue data <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>;
      code <a href="https://github.com/sarapis/govoss-catalog/blob/main/LICENSE">MIT</a>.
      Individual entries remain under the terms of the government catalogue that
      published them &mdash; every entry links back to its source.
    </span>
  </div>
</div></footer>
""".replace("__COLS__", cols)


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
<html lang="en" class="wg-govoss" data-brand="govoss">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s</title>
<meta name="description" content="%s">
<link rel="alternate" type="application/json" href="/entries.json" title="All entries as JSON">
<link rel="alternate" type="application/json" href="/meta.json" title="Catalogue metadata">
<link rel="alternate" type="application/json" href="/status.json" title="Build status">
%s""" % (title, description,
         ('<link rel="canonical" href="%s">\n' % canonical) if canonical else "")
