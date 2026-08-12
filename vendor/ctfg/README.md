# Vendored: Civic Tech Field Guide design tokens

**Version: 2.0.0 &middot; 2026-08-12.** Read it at runtime from any built page:
`getComputedStyle(document.documentElement).getPropertyValue('--ctfg-tokens-version')`.

The version is **system-wide**, so all four files carry the same string; `theme.py`
asserts they agree and fails the build if they do not, because a set whose files
disagree is a bad copy rather than a valid mix. The bundle folder UUID is a build
identifier with no ordering and is not a version.

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

- **Accessibility patches — none.** The `--ink-faint` patch was deleted on adopting
  2.0.0, which fixes it upstream. A patch that merely restates upstream reads as a
  divergence to the next person.
- **Deliberate divergence** — the font stacks carry full fallbacks and no
  Cascadia Code, because we self-host and load no font CDN. 2.0.0 records this
  under *Sanctioned divergences* in `VERSION`, so it is agreed rather than tolerated.

## On taking the next update

`VERSION` says a MAJOR means a rendered value moved or an alias was repointed —
**check the override layer on a major.** 2.0.0 also moved `--ink-soft` to ink-600 and
flags it as required-but-visually-unreviewed. That one is a no-op here: nothing in
this project colours anything with `--ink-soft`. Verified by grep, not assumed.
