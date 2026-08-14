# Open items

Where the work stands as of **2026-08-14**, and what is worth doing next. Doubles as a
continuation brief: written to be handed to whoever — or whatever — picks this up cold.

**Read `CLAUDE.md` first.** It is the operating manual and it records *why* each decision was
made. `README.md` is the public overview. `DESIGN-BRIEF.md` is the design system as built.
`DEMAND-SIDE-CATALOGUE.md` is a live proposal with a decision still open.

⚠ **`UPSTREAM-CTFG.md` and `CTFG-CONTRAST-REPORT.md` are HISTORICAL RECORD, not guidance.**
govoss left the Civic Tech Field Guide design system on 2026-08-13.

State: **2,753 entries · 453 set aside · 17 catalogues · 15 countries.** Pipeline is
`bash run.sh` (16 steps, ~20 min; the order is load-bearing and documented at the top of the
file). Scheduled Mondays 07:00 — `bash schedule/install.sh`.

## ⚠ First thing to check

**Monday 2026-08-17 07:00 is the first unattended run to exercise everything below.** Nothing
in this session has been through a real scheduled run. Look at `/sources.html` — it reports
its own build status — and confirm `generated_at` in `/meta.json` moved.

Expect, and do NOT treat as faults:
- **The >10% shrink warning fires once.** 3,069 → 2,753 is the intended effect of setting
  aside entries with no description. `run.sh` prints it by design.
- **`enrich_desc` fills only ~8 entries** and reports being rate limited. See item 3.

## Shipped 2026-08-13/14

- **govoss left the CTFG design system** for `@wegovnyc/design-tokens` v0.7.0 under a `govoss`
  brand variant — the system wegov.nyc and unnyc.wegov.nyc share. No CTFG chrome, no NYC
  identity. `ctfg_nav.py` retired, so **the build now makes no network request at all**.
- **`/products.html`** — the proprietary side made browsable: one dense table of 372 products
  with description, function, alternatives and a link into the filtered catalogue.
- **`replaces.json` 108 → 194 entries**, 290 products. Entry point is a `Replaces` facet in
  the catalog sidebar, not a nav item.
- **Bulgarian translated** (175), **descriptions enriched from GitHub**, and entries with **no
  description at all set aside** (351). Entry and English counts now agree: 2,753 / 2,751.
- **Identity**: Wikidata added as a second QID source (by URL, never by name) and a third
  dedupe key (exact name **and** exact homepage). 554 → 644 QIDs.
- **`/entries.json` carries set-aside rows**, flagged `excluded` — the derived indexes stay
  curated.
- **WCAG re-audited** after the design move: zero failures, lowest 4.9:1.

## In rough priority order

0. **Decide the demand-side catalogue.** `DEMAND-SIDE-CATALOGUE.md` proposes harvesting the
   proprietary software governments actually buy, from procurement data, rather than
   hand-seeding it. NYC's licence export (1,601 contracts, $1.77B, 927 products) joins the
   catalogue at **3.6% of spend**, and the note argues the limit is *naming, not coverage*:
   four spellings of Esri hid $13.5M that QGIS answers. **Stage 1 — the go/no-go — has NOT
   been run:** get one more jurisdiction with product-level licence data and check whether
   product names normalise across two. A day's work, and it decides everything after it.
   Read this before doing (1) — it may reorder the work.

1. **Expand `replaces.json`.** 194 of 2,753 entries → 290 products. Read the `_README` block
   first: `kind` (`software` / `service` / `paid-tier`) and `confidence` both matter, and
   getting them wrong produces confident category errors. `export_json.py` **fails the build**
   on an invalid value and warns on keys matching nothing.
   ⚠ **Check existing product names before adding.** Yesterday's additions used more specific
   names than the seed already had (`Dropbox Business` beside `Dropbox`), splitting one
   product across two index keys.

2. **Databook design harmonisation is handed off**, not done. See
   `~/Antigravity/Databook2/docs/LANDING-HARMONISATION-PLAN.md` — Phase 1 is the approved
   visual change, Phase 2 adds a `databook` variant to the token package. Give it to a
   Databook-focused session; it is written to be executed cold.

3. **`enrich_desc.py` is rate-limited to ~8 entries per run.** No `GITHUB_TOKEN` in the
   LaunchAgent, so it gets 60 unauthenticated requests/hour against 251 candidates — ~31
   weeks. It caches and resumes, so it converges, but a PAT **with no scopes at all** added to
   `schedule/*.plist.template` would finish it in one run. Not done because it needs a
   credential decision.

4. **Screen-reader testing has never been done.** The audits are automated contrast sweeps
   plus keyboard. VoiceOver/NVDA against the catalog page is the honest next step, and until
   it runs nothing should claim conformance. Note `/products.html` is a large table — the
   surface most likely to expose problems.

5. **The get-involved block is duplicated** in `_ui_template.py` and `build_sources.py`. It
   already caused one bug: a fix applied to one left the other stale. Same shape as the
   `SRC_LABEL` duplication removed this session.

6. **Two OSOR leads left, both small:** ICT ReUse Belgium and Helsingborg City. Check
   `sources.py:SURVEY` for what has already been rejected and why before chasing anything.

7. **8 Bulgarian entries show no description** — their entire upstream text was a contract
   number, so `tr_bg.json` maps them to an empty string, which `merge_translations.py` treats
   as no description. They are set aside, correctly.

## Things that are done and should be left alone

- **Do not syndicate the EU OSS Catalogue.** Its pager, facets and search all ignore query
  strings; only 20 of 1,084 solutions are reachable. `PAGINATION-BUG.md` is a finished report
  ready to send to the EC — still worth doing if you want a use for it.
- **Do not chase the UNODC "Directory of Open-Source Registries".** It is open-source
  *intelligence* (company registries for corruption investigators), not software.
- **Do not add `OS2World`, `os2edu`, `os2sd`, `OS2G` or `OS23Portfolios`** to the Denmark
  adapter — name collisions. `harvest.py:OS2_EXCLUDED` records why.
- **France's 24,440-repo inventory stays excluded.** Re-add as an enrichment join if ever,
  never as catalogue entries.
- **Do not re-add a naive "missing description = not software" rule.** The current
  `no-description` rule is an editorial standard about publisher effort, it runs AFTER
  `enrich_desc.py`, and it flags rather than deletes. The comment in `filters.py` explains
  what makes it different from the rule that was removed for hiding `Products.PloneMeeting`.

## Verification habits this project earned the hard way

- Check the **built output**, not that a patch reported success.
- **Test a guard adversarially.** Two guards written this session could only ever pass until
  they were tested by breaking the thing they check.
- Confirm a **dead** verdict through a second channel before asserting it.
- **Detect** description language from text, and read `desc_lang` (what is displayed), never
  `desc_src_lang` (the original).
- **Audit interactive states**, not just the page at rest — a 2.41:1 failure hid behind an
  unpressed toggle.
- Run `bash run.sh` rather than the steps from memory — the ordering is load-bearing.
- **The browser pane returns stale and blank frames.** Measure the DOM; treat screenshots as
  a secondary signal, and rebuild `site/` before testing it.
