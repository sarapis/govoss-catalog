# Colour contrast in the CTFG design system

**A design-system report, ready to send.** Three token-level issues found while building
govoss-catalog on the Civic Tech Field Guide design system, verified against the live
`civictech.guide` homepage. All three are one-line fixes upstream, and fixing them there fixes
every property at once.

**Reported by:** the govoss-catalog build (https://govoss-catalog.vercel.app) ·
**Date:** 2026-08-12 · **Standard:** WCAG 2.1 AA (1.4.3 Contrast, minimum)

---

## Summary

| # | Token | Used as | Measured | Required | Fix |
|---|---|---|---|---|---|
| 1 | `--ink-400` / `--ink-faint` | body text | **2.24 – 2.53:1** | 4.5:1 | point `--ink-faint` at `--ink-500` |
| 2 | `--green-500` / `--verified` | display text, and as a fill under white text | **2.34 – 2.65:1** | 3:1 large, 4.5:1 normal | use `--green-700` for text; `--ink-900` on green fills |
| 3 | icon set | decorative SVGs | n/a | 1.1.1 | ship `aria-hidden="true"` |

**These are not misuses by a consumer.** Number 1 is what `tokens/colors.css` itself declares
the faint-text alias to be. Number 2 is the colour named `--verified`, used the way the design
uses it. A consumer following the system correctly inherits both.

---

## 1. `--ink-faint` resolves to a colour that cannot carry text

`tokens/colors.css` line 41:

```css
--ink-faint:     var(--ink-400);      /* #9FA4A3 */
```

Measured against the system's own grounds:

| foreground | background | ratio | required | result |
|---|---|---|---|---|
| `#9FA4A3` | `--paper-50` `#FBFBFB` | **2.44:1** | 4.5:1 | ✗ fails |
| `#9FA4A3` | `--white` `#FFFFFF` | **2.53:1** | 4.5:1 | ✗ fails |

**Live evidence — civictech.guide homepage**, computed from the rendered page:

- `rgb(159,164,163)` at 12px on an event time (&ldquo;5:30pm&rdquo;) &mdash; **2.24:1**
- `rgb(159,164,163)` at 13px on a date (&ldquo;August 5, 2026&rdquo;) &mdash; **2.53:1**

`rgb(159,164,163)` is `#9FA4A3` exactly. The token is in production use on text.

**Suggested fix** &mdash; one line, no new colour, `--ink-500` is already in the palette:

```diff
-  --ink-faint:     var(--ink-400);
+  --ink-faint:     var(--ink-500);   /* #6B6B68 — 5.17:1 on paper-50, 5.35:1 on white */
```

`--ink-400` stays defined and remains correct for **non-text** use &mdash; borders, dividers,
disabled-state marks, chart fills &mdash; where 4.5:1 does not apply. The change is only to the
alias that components reach for when they colour words.

---

## 2. `--green-500` fails both as text and as a fill under white text

`--green-500` `#01B583` is aliased to `--green` and `--verified`. Two distinct failures:

**As display text.** On the civictech.guide homepage it sets headline phrases:

| text | size | ratio | required |
|---|---|---|---|
| &ldquo;exciting civic tech events&rdquo; | 34px | **2.34:1** | 3:1 (large) |
| &ldquo;exciting civic tech projects&rdquo; | 34px | **2.56:1** | 3:1 (large) |
| &ldquo;Adjacent Fields&rdquo; | 23px | **2.56:1** | 4.5:1 (not large at 23px/400) |

**As a fill under white text.** The restyle spec called for `--green-500` fill with white text
on endorsement stamps and DO tags: `#FFFFFF` on `#01B583` is **2.65:1**.

**Suggested fixes**, both in-palette:

```diff
  /* text on a light ground: use the deep green, not the bright one */
- color: var(--green-500);
+ color: var(--green-700);        /* #006348 — 7.30:1 on white */

  /* text on a green fill: ink, not white */
- background: var(--green-500); color: var(--white);      /* 2.65:1 */
+ background: var(--green-500); color: var(--ink-900);    /* 6.62:1 */
```

The second keeps the bright green fill **and** its `--shadow-green` hard shadow, which is what
makes the component read as an endorsement &mdash; only the text colour moves.

---

## 3. Icons ship with no `aria-hidden`

`_ds_bundle.js` contains **zero** occurrences of `aria-hidden`. The icons are decorative and sit
beside text that already says the same thing, so a screen reader announces them as noise.

**Suggested fix:** ship the line set with `aria-hidden="true"` by default, and let a consumer
opt into `role="img" aria-label="…"` on the rare icon that carries meaning alone.

---

## Also worth a look, lower confidence

`--mint-300` `#67F5C2` on `--violet-500` `#574FD9` is **4.37:1** &mdash; just under 4.5:1 for
normal text. This appears in the utility-bar specification rather than the design system's own
CSS, so it may be an application-level choice rather than a system one. White on violet-500 is
5.96:1 if a change is wanted.

---

## What govoss did in the meantime

Patched locally, and **recorded as divergence** so a future resync does not silently revert it:

- `--ink-faint` → `--ink-500`
- `--ink-900` on green fills instead of white
- utility-bar links white instead of mint
- `aria-hidden` added to every decorative icon

After these, contrast on all three govoss pages clears 4.5:1 with a **lowest measured ratio of
5.17:1**. We would rather drop the local patches and take the fix from upstream.

---

## Method and caveats

**Method.** Computed styles read from the rendered pages in a real browser, walking to the
first opaque ancestor background, with WCAG relative-luminance maths. Not a static analysis of
CSS &mdash; these are the values as they actually paint.

**Caveats, stated plainly:**

- The bundle inspected was the snapshot supplied in the govoss restyle handoff
  (`ctfg-design-system-8262bf6d`). **If the live design system has moved since, some of this may
  already be fixed** &mdash; the live-page evidence for items 1 and 2 says they were still
  present on 2026-08-12, but check before acting.
- Only the `civictech.guide` homepage was measured for live evidence; 10 contrast failures were
  found there in total. Other properties were not scanned. `nyc.civictech.guide` returns 401 and
  could not be checked.
- Contrast only. This is not a full WCAG audit of CTFG properties, and **no screen-reader
  testing was done** &mdash; item 3 is inferred from markup, not from listening to it.
- Suggested values are the minimum change that passes. A designer may prefer different colours;
  the point is the ratios, not my choices.
