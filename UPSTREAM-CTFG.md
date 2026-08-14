# Upstream exchange with the CTFG design system

> ⚠ **HISTORICAL RECORD, not live guidance.** govoss moved off the Civic Tech Field Guide
> design system on 2026-08-13 and now runs on `@wegovnyc/design-tokens` under the `govoss`
> brand variant (`vendor/wegovnyc/`). CTFG remains a consumer of this catalogue's data — the
> change is branding, not the relationship. This file is kept because the exchange it records
> was real and useful: three defects reported, three fixed in CTFG's v2.0.0.

The record of reporting three accessibility defects upstream and taking the fix back. Kept
because the outcome — **we deleted our local patch instead of carrying it forever** — is the
thing worth repeating, and because the reasoning is not recoverable from the diffs.

Companion files: `CTFG-CONTRAST-REPORT.md` (the report as sent), `vendor/ctfg/` (the tokens and
their VERSION), `DESIGN-BRIEF.md` (the system as built).

---

## What happened, in order

1. **A WCAG audit of govoss found 10 issues.** Seven were ours. Three were defects in the CTFG
   design system that any consumer following it correctly would inherit.
2. **Patched locally, and recorded as divergence** so a future resync could not silently revert
   them.
3. **Reported upstream** with measured evidence — including from the live `civictech.guide`
   homepage, not just the handoff bundle, which is what made it actionable.
4. **Claude Design shipped tokens v2.0.0**, fixing all three plus adding semantic tokens we
   asked for by implication (`--green-text`, `--green-line`, `--on-green`).
5. **We deleted our patch.** Override layer now holds no patches at all.

## The three findings

| # | What the system shipped | Measured | Fixed in |
|---|---|---|---|
| 1 | `--ink-faint: var(--ink-400)` — the semantic alias for faint **text** | 2.24–2.53:1 | v2.0.0 → `--ink-500` |
| 2 | `--green-500` / `--verified` as text, and as a fill under white text | 2.34–2.65:1 | v2.0.0 → `--green-text`, `--on-green` |
| 3 | icon set with zero `aria-hidden` | §1.1.1 | v2.0.0 → `aria-hidden` + `focusable="false"` |

Finding 1 is the instructive one: **the design system's own semantic alias for faint text
pointed at a colour that could not legally carry text.** Not a misuse — an inherited defect.

## What we asked for beyond the colours

- **A version.** The 1.0.0 bundle carried no version marker of any kind; the only identifier
  was a folder UUID with no ordering, so "is this newer?" could only be answered by diffing.
  v2.0.0 introduced a system-wide v-string in every file plus `--ctfg-tokens-version` /
  `--ctfg-tokens-date` as custom properties readable at runtime.
- **A policy.** v2.0.0's `VERSION` defines repointing an alias as **MAJOR** even though no hex
  literal moves — which is exactly the class of change that shipped silently and caused
  finding 1.
- **A defined vendorable set**, with our three exclusions written in as deliberate rather than
  as our idiosyncrasy.

## What we told them back

- **`--ink-soft` → ink-600 is a no-op here.** Their release flags it as required-but-visually-
  unreviewed because it darkens every secondary string. Nothing in this project colours
  anything with `--ink-soft` (verified by grep), so **our clean adoption is not evidence the
  change is fine.** Someone using the semantic tier has to look at it.
- **We are an unrepresentative consumer.** Our component CSS is our own, so we exercise their
  semantic aliases far less than a property built on `.ctfg-*` components would.
- **No screen-reader testing** was done on either side, so finding 3 is adopted on trust.

## The rule this produced

**Report upstream, patch locally, label the patch, delete it when the fix lands.**

A patch that merely restates upstream is not harmless — it reads as a deliberate divergence to
the next person and outlives the reason for it. That is why `theme.py` labels every override as
either **PATCH** (delete when upstream fixes it) or **DIVERGENCE** (keep across updates), and
why `vendor/ctfg/README.md` says to check the override layer on a MAJOR.

Today the override layer is: one divergence (self-hosted fonts, now *sanctioned* in their
VERSION), plus two additions of our own (`--font-logo`, and short aliases onto their
`--radius-*` scale). Zero patches.
