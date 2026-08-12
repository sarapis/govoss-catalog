# Vendored: Civic Tech Field Guide design tokens

**Source bundle:** `ctfg-design-system-8262bf6d-6a64-4698-80f1-8ba62eb3db88`
(supplied in the govoss restyle handoff, 2026-08-12)

`theme.py` inlines these files at build time. **Do not hand-edit them** — that is
the transcription problem this directory exists to remove. To take an upstream
change, replace the files and bump the version above.

## What is vendored, and what is not

| file | vendored | why |
|---|---|---|
| `tokens/colors.css` | yes | pure `:root` custom properties |
| `tokens/typography.css` | yes | families, weights, type scale |
| `tokens/spacing.css` | yes | spacing steps and radii |
| `tokens/effects.css` | yes | the hard-offset shadows and the dashed divider |
| `styles.css` | **no** | contains no rules — its only non-`@import` line loads Google Fonts, which this project deliberately does not do |
| `tokens/fonts.css` | **no** | `@font-face` pointing at the jsDelivr CDN. Same objection; we vendor woff2 in `fonts/` and serve same-origin |
| `tokens/interactions.css` | **no** | component rules targeting `.ctfg-*` classes this project never stamps |
| `_ds_bundle.js` | **no** | 70 KB of React components; our components are our own |

## Our overrides

Applied in `theme.py` **after** these files, each one labelled. Two kinds:

- **Accessibility patches** — `--ink-faint` points at `--ink-500`, not `--ink-400`.
  Delete this when the upstream fix lands; see `CTFG-CONTRAST-REPORT.md`.
- **Deliberate divergence** — the font stacks carry full fallbacks and no
  Cascadia Code, because we self-host and do not load any font CDN.
