# Open items

Where the work stands as of 2026-08-12, and what is worth doing next. Doubles as a
continuation brief: written to be handed to whoever — or whatever — picks this up cold.

**Read `CLAUDE.md` first.** It is the operating manual. `README.md` has the overview,
`DESIGN-BRIEF.md` the design system as built, `UPSTREAM-CTFG.md` the design-system exchange.
Don't re-litigate decisions recorded there — particularly the deliberate exclusions.

State: **3,080 entries, 17 catalogues, 15 countries.** Pipeline is `bash run.sh` (~20 min,
15 steps; the order matters and is documented at the top of the file). Scheduled Mondays 07:00
— `bash schedule/install.sh`.

## Shipped 2026-08-12 (one long session)

- **Publishing is automatic.** `run.sh` ends with `deploy` then `record`, both gated on every
  earlier step exiting 0, so what is committed is what is published. No hand-deploys.
- **The repo is public:** github.com/sarapis/govoss-catalog, MIT code / CC BY 4.0 data.
  History audited clean before publishing; secret scanning and push protection on.
- **Committed JSON is deterministic** — sorted records, no per-record timestamps. Weekly churn
  fell from 50,199 diff lines to 2,365 (95%).
- **Three pages restyled** on the CTFG design system: catalog, sources+status merged, and a new
  `/api.html`. `build_status.py` retired; `/status.json` still written.
- **An MCP server** at `govoss-mcp.devin-31f.workers.dev` — public, keyless, five tools.
- **WCAG 2.1 AA audited**: 10 issues found and fixed, lowest ratio now 5.17:1.
- **Design tokens vendored** at `vendor/ctfg/` v2.0.0 rather than transcribed. Three defects
  reported upstream were fixed there, so our local patch is deleted.

## In rough priority order

1. **Expand `replaces.json`.** 108 of 3,080 entries map to 165 proprietary products. This is
   the field that makes the catalogue answer *"what can we stop paying for?"* rather than
   *"what exists"*. Read the `_README` block in that file first — `kind` (`software` /
   `service` / `paid-tier`) and `confidence` both matter, and getting them wrong produces
   confident category errors. `export_json.py` warns on keys that match nothing, so the file
   cannot rot unnoticed.

2. **Two OSOR leads left, both small:** ICT ReUse Belgium and Helsingborg City. Adullact and
   Forja redIRIS are academic/association rather than government. Diminishing returns — check
   `sources.py:SURVEY` for what's already been rejected and why before chasing anything.

3. **171 Bulgarian descriptions are untranslated** and that was a deliberate call: they're
   mostly long EU-funding project titles (`BG05SFOP001-…`) rather than software summaries. If
   you do them, triage first — translating a grant reference adds nothing.

4. **Screen-reader testing has never been done.** The WCAG audit was automated checks plus
   keyboard only. VoiceOver/NVDA against the catalog page is the honest next step, and until
   it runs, nothing should claim conformance.

5. **`HANDOFF-PROMPT.md` is stale** — it still quotes pre-restyle counts and does not know the
   MCP server exists. Refresh it before handing it to a downstream data consumer.

6. **Sparklines fill in over coming weeks.** Runs before 2026-08-12 have no per-catalogue
   record, so they render as grey "not recorded" bars rather than invented history.

7. **`get_stats` on the MCP server can be up to an hour stale** (1-hour edge cache on
   meta.json). Fine for weekly data, but the tool an agent polls to detect a rebuild lags.

## Things that are done and should be left alone

- **Do not syndicate the EU OSS Catalogue.** Its pager, facets and search all ignore query
  strings; only 20 of 1,084 solutions are reachable. `PAGINATION-BUG.md` is a finished report
  ready to send to the EC — that's still worth doing if you want a use for it.
- **Do not chase the UNODC "Directory of Open-Source Registries".** It's open-source
  *intelligence* (company registries for corruption investigators), not software.
- **Do not add `OS2World`, `os2edu`, `os2sd`, `OS2G` or `OS23Portfolios`** if you touch the
  Denmark adapter — they're name collisions (IBM OS/2, a Chinese OS project, Android ROM
  trees, a US student club, someone's coursework). `harvest.py:OS2_EXCLUDED` records why.
- **France's 24,440-repo inventory stays excluded.** It answers "who published this", not "is
  this useful to a government": 45% no description, 80% no licence, dominated by research
  code. Re-add it as an enrichment join if ever, never as catalogue entries.

## Verification habits this project earned the hard way

- Check the **built output**, not that a patch reported success.
- Confirm a **dead** verdict through a second channel before recording it.
- **Detect** description language from text; never assume it from the source.
- Run `bash run.sh` rather than the steps from memory — the ordering is load-bearing and I
  once rebuilt the whole site from un-deduped data by improvising it.
