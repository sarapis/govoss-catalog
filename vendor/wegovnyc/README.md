# Vendored: WeGovNYC design tokens

**Package: `@wegovnyc/design-tokens` v0.7.0 · commit `f5c95ad` · vendored 2026-08-13.**
Canonical source: <https://github.com/sarapis/wegovnyc-design-tokens> (public).

Read the active variant at runtime from any built page:
`getComputedStyle(document.documentElement).getPropertyValue('--wg-brand-id')`
→ `govoss`.

`theme.py` inlines these files at build time and asserts the version. **Do not
hand-edit them** — that is the transcription problem this directory exists to
remove. To take an upstream change: copy the files again, update the version and
commit above, and re-run the contrast audit.

## Why vendored rather than an npm dependency

govoss has no JavaScript build step and no `package_json` — it is Python that
emits self-contained HTML. wegov.nyc and UNNYC install the package as a git
dependency because they are Next.js apps with a bundler; govoss has nothing to
bundle with. Vendoring plus a version assert gives the same guarantee the
`node_modules` copy gives them: the file is a clean copy of a known release, not
a transcription that has drifted.

The tradeoff is real and worth stating: **an upstream fix does not reach govoss
until someone copies it here.** The version stamp in `theme.py` is what makes
that visible rather than silent.

## What is vendored, and what is not

| file | vendored | why |
|---|---|---|
| `src/core.css` | yes | the reference palette + the ~90 `--wg-*` semantics |
| `src/variant-govoss.css` | yes | govoss's remap — the two divergences live here |
| `src/variant-wegov.css` | **no** | another product's brand; scoped to a class govoss never stamps |
| `src/variant-unnyc.css` | **no** | same |
| `src/index.css` | **no** | loads every variant; govoss renders exactly one |
| `bin/wg-lint-tokens.mjs` | **no** | Node, and it lints *consumer* stylesheets. govoss's equivalent guard is the contrast assert in `theme.py` |

## Fonts are NOT vendored from the package

The package names families; it ships no `@font-face`. govoss self-hosts nine
woff2 in `fonts/` and serves them same-origin, because its readership is European
public-sector staff for whom a Google Fonts request is a live GDPR objection.
That is why `variant-govoss.css` overrides `--wg-font-display` to Space Grotesk
rather than the family's DM Serif Display: the face is not vendored here, and
adding one is an asset decision rather than a token decision.
