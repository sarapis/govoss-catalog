# Open items

Where the work stands as of **2026-09-10**, and what is worth doing next. Doubles as a
continuation brief: written to be handed to whoever — or whatever — picks this up cold.

**Read `CLAUDE.md` first.** It is the operating manual and it records *why* each decision was
made. `README.md` is the public overview. `DESIGN-BRIEF.md` is the design system as built.
`DEMAND-SIDE-CATALOGUE.md` is a live proposal with a decision still open.

⚠ **`UPSTREAM-CTFG.md` and `CTFG-CONTRAST-REPORT.md` are HISTORICAL RECORD, not guidance.**
govoss left the Civic Tech Field Guide design system on 2026-08-13.

State: **2,834 entries · 484 set aside · 17 catalogues · 15 countries.** Pipeline is
`bash run.sh` (16 steps, ~20 min; the order is load-bearing and documented at the top of the
file). Scheduled Mondays 07:00 — `bash schedule/install.sh`.

## The one idea, if you remember nothing else

**Every failure sensor in this pipeline was a `print`, and the one hard gate reads sensors
that cannot trip.** `steps.tsv` was built so the end state cannot hide a failed *step* — and
then failed sources, a crashed monitor, unmapped taxonomy values and rotted translation keys
all learned to hide inside steps that exit 0. The 2026-09-10 fixes moved **all five** of
those into files the status page reads — F1 `cache/_fetched.json`, F3 `summary.failed_at`,
F4 `out/taxonomy_unmapped.json`, F6 `out/translation_orphans.json` — plus F5, which was the
same idea one layer down: a stage that destroys data has to *refuse*, not report.

**So the known instances are closed, and the rule is what survives:** when you find the next
one, the fix is not "add a warning"; it is "write it where the page already looks." Two
corollaries this week earned the hard way — **the total is rarely the trigger** (rot that is
expected to grow needs a delta, or the page reads `warn` forever and nobody reads it), and
**a missing previous measurement is not zero** (that turns a standing backlog into a day-one
false alarm).

### Invariants — break these and something already fixed re-breaks

- **`fetched_at` / `summary.checked` advance ONLY on success.** That is what makes a growing
  age mean "stale". Stamp either on a failure and staleness becomes undetectable again.
- **Both self-clear.** A successful run rebuilds them from scratch, so no stale error
  outlives its failure. If you add a marker that persists, people learn to ignore the page.
- **Never store a per-run value PER RECORD** — per-source/summary only. The same idea per
  record once turned one `liveness.json` diff into 47,563 lines.
- **`--from-cache` must not write `cache/_timing.json` or `cache/_fetched.json`** (guarded by
  `if want:`). Without it a no-network rebuild blanks them to `{}` and destroys the record of
  the last real fetch.
- **Look up `_fetched.json` by the CHECKPOINT key (`os2`), not the `sources.py` key
  (`DK/os2`).** Getting this wrong is silent: the first version matched nothing for all 17
  sources, built cleanly and reported `ok`.
- **`harvest.py` exits 0 on a failed source, on purpose.** Do not "fix" it into a hard
  failure — one flaky source would then block the weekly publish of sixteen good ones.

### Waiting on a human — not work that was skipped

- **The demand-side go/no-go** (item 0) — a scope decision about what the catalogue *is*.
- **A Vercel deploy token** (F7) — a credential decision.

### Traps — looks broken but is not, and vice versa

- **`/sources.html` reads `warn` until the next run, and that is not a regression.**
  `scheduling` was the only unmapped value and it was mapped on 2026-09-10, but
  `out/taxonomy_unmapped.json` and `site/status.json` are per-run artefacts — they still
  hold the pre-fix state, so local reads `warn` until `taxonomy.py` runs again. Verified by
  dry-running `classify()` over the whole catalogue: the unmapped set is now empty, so the
  warning self-clears on 09-14.
- **Live says `ok`, local says `warn`.** The live copy was built 09-07, before these fixes.
  Not drift — just an unpublished change. It resolves itself on 09-14.
- **`cache/_fetched.json` has 16 entries, not 17.** `nlreg` is key-gated and absent from
  `sources.py`; `harvest.py` still harvests it, so the next run adds it.
- **A "flat" source count is not evidence of staleness.** Eight catalogues genuinely do not
  change weekly. Freshness now comes from `_fetched.json`, not from the count moving.
- **`out/` is gitignored**, so `taxonomy_unmapped.json` is per-run. Absent on a fresh
  checkout until `taxonomy.py` runs — `build_sources.py` degrades to `ok`, by design.
- **`PAGINATION-BUG.md` is a report about someone else's service**, not a defect here.

## ⚠ First thing to check

**Monday 2026-09-14 07:00 is the first unattended run to exercise the F1–F4 fixes** (the
freshness file, the os2 guard, authenticated GitHub, the liveness crash marker, the unmapped
warning). Nothing below has been through a real scheduled run.

*This section previously said 2026-08-17 and warned about a shrink warning and an
`enrich_desc` rate limit. Four scheduled runs have happened since — 08-17, 08-24, 08-31,
09-07, all clean, zero `FAILED SOURCES` — and both of those expectations are obsolete;
`enrich_desc` now fills ~40 with no limit hit.*

What to look at:
- **`cache/_fetched.json` — every source stamped `2026-09-14`, `ok: true`.** An older
  `fetched_at` means that source failed and silently reused its checkpoint, which before
  this week left no trace anywhere. It holds **16** entries today and should hold **17**
  after the run: the bootstrap iterated `sources.py`, which has no row for the key-gated
  `nlreg`, but `harvest.py` does harvest it.
- **`/sources.html` should read `ok`.** `scheduling` — the one unmapped value, and the only
  thing that had it at `warn` — was mapped on 2026-09-10, so this is the run where
  `out/taxonomy_unmapped.json` is rewritten to `{}` and the warning self-clears. A `warn`
  naming any *other* value is new and real. ⚠ Both the LIVE page and the local
  `site/status.json` read `warn`/`ok` from artefacts built before that fix — do not mistake
  either gap for a bug.
- **The GitHub-backed sources (BE, BG, PT, IE, DK/os2) run authenticated for the first
  time.** Counts should not move; `_timing.json` may drop.

## Shipped 2026-09-10 — the code review, and its top four findings

**`REVIEW-govoss-catalog-2026-08-28.md`** is in the repo and recorded in the Hub
(`~/vault/reviews/sarapis__govoss-catalog.md`). 8 findings from 17 drafts. Its verdict is
one sentence worth keeping: *every failure sensor in this pipeline is a print, and the one
hard gate reads sensors that cannot trip.*

- **F1** `bb59fb7` — `cache/_fetched.json` per source. `fetched_at` advances **only on a
  success**, so a failing source's age grows; `build_sources.py` warns >15d, critical >29d,
  and stamps the row. Harvest still exits 0 on a failed source **deliberately** — one flaky
  source must not block the publish of sixteen good ones.
- **F2** `bb59fb7` — `os2()` raises when orgs failed **and** the result regressed, instead of
  overwriting its own checkpoint with a truncated scan. `github_org_scan` now authenticates
  via `liveness.gh_token()` (60 → 5,000 req/hr).
- **F3** `100e757` — a crashed `liveness.py` annotates `summary.failed_at`/`last_error` and
  preserves `checked`; it still exits 0.
- **F4** `100e757` — `taxonomy.py` writes `out/taxonomy_unmapped.json`; the page warns by name.

All four self-clear on success, which was verified rather than assumed.

**F6 also closed — `out/translation_orphans.json`.** `merge_translations.py` now reports
tr_*.json keys whose source text is no longer in the catalogue: **59 of 1,762 today** (3%).
The entry falls back to its foreign original, which stays documented and accepted — what was
missing was any report that it happened. `runlog.py` records the total into `history.json`
and `build_sources.py` warns when it **grows**. Three decisions worth not re-litigating:

- **The obvious implementation is wrong, badly.** "Keys this merge pass actually looked up"
  is the natural reading, and a merged row carries `translated: True` and short-circuits
  before the lookup — so on already-merged input it reports **1,762 of 1,762 keys orphaned**
  against a real 59. Measured, not imagined. The rule instead hashes the SOURCE TEXT still in
  the catalogue, from `short_desc` (the original on a raw row) **and** `desc_src` (the
  original on a merged one), which is stable across re-runs by construction. Verified against
  all 1,731 merged rows carrying a `desc_src`: zero false orphans.
- **The DELTA is the trigger, not the total.** Rot is expected to be non-zero and slowly
  growing, so warning on 59 would have shipped a page that reads `warn` from day one for a
  pre-existing backlog — and a warning that is always on is one you stop reading. Same call
  `liveness.py` already makes: "3 newly-dead repos" over "81 dead".
- **A missing previous figure is NOT zero.** `runs[-2]` predates F6 and has no
  `orphan_keys`; treating that as 0 would have reported the whole standing backlog as new rot
  on the first run. Verified across the whole matrix (prev absent / 59→60 / flat / improved /
  0→60): only genuine growth warns.

`test_translation_orphans.py` locks in both rules side by side, so the naive one cannot look
reasonable to the next reader, and was checked by sabotage — dropping `desc_src` from the
live set, and stripping text before hashing (the Bulgarian whitespace trap), each fail
several assertions.

**F5 also closed — `stage_guard.py`.** `dedupe.py` **and `taxonomy.py`** now refuse to run
on an already-merged `catalog.json` (marker: `catalogue_count` on an active row). Both were
destroying data only the merge has: dedupe resets `catalogue_count` to 1 on every survivor,
wiping the "In N catalogues" pill; taxonomy narrows `functions` on **45 entries**, because
`functions` is union'd in `dedupe.py:UNION_LIST` and `classify()` only sees the survivor.
Three things about it worth not re-litigating:

- **It refuses; it is not merge-aware, and there is no `--force`.** Unioning the recomputed
  value with the stored one is the obvious fix and it is wrong — a corrected mapping, or a
  record that legitimately stopped being multi-catalogue, would keep its stale value forever
  with nothing to say so. That is a loud bug traded for a silent permanent one. The way
  forward is `python3 harvest.py --from-cache`, which is offline and cheap.
- **Verified by sabotage.** Stubbed to `return False`, both stages exit **0** and modify
  `catalog.json` — the destruction observed, not inferred. `test_stage_guard.py` locks in
  both directions plus the two mistakes that would make the guard useless (`all()` for
  `any()`; forgetting to skip `excluded` rows, which never carry the marker).
- **The first version of the test had the hole this repo keeps hitting.** It asked
  `stage_guard.is_post_dedupe()` whether `catalog.json` was merged, so a sabotaged no-op
  guard reported "not merged" and the test *skipped* its subprocess cases — the ones that
  prove destruction is prevented — precisely when the guard was broken. A test must never
  ask the thing it is testing whether to run its hardest case.

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

1. ~~**Map `scheduling` in `taxonomy.py:M`.**~~ **Done 2026-09-10 — `scheduling` →
   `case-workflow`.** It was NOT the three-way editorial call recorded here, and the two
   reasons are worth keeping:
   - **`M` already maps the whole sibling family to `case-workflow`** —
     `appointment-scheduling`, `online-booking`, `booking-and-reservation`,
     `calendar-management`, `termine`, `event-management`. Putting `scheduling` anywhere else
     would have split one concept across two functions, which is the drift `M` exists to
     collapse. So this is not widening a bucket to silence the alarm.
   - **No entry was shipping unclassified.** The single entry is `newdle` (DE/openCode,
     CERN/Indico's meeting-scheduling tool), whose categories are
     `['scheduling', 'project-collaboration']` — the second already mapped, so it carried
     `functions: ['case-workflow']` throughout. The unmapped value cost a *signal*, never a
     classification.
   Verified by dry-running `classify()` over all 3,318 rows: unmapped set now empty, and the
   change is provably output-neutral (identical diff computed with and without the mapping).
   ⚠ The rule still stands for the next one: do **not** silence an unmapped value by widening
   a bucket — the warning is only useful near zero.

2. **F7–F8 from the review are open** (F5 and F6 closed 2026-09-10 — see below), in the
   review's own words:
   - **F7** deploy rests on the Vercel CLI's stored login; `~/.config/govoss/vercel-token`
     does not exist (verified).
   - **F8** the test suite is **three** files now (`test_stage_guard.py` with F5,
     `test_translation_orphans.py` with F6), but **dedupe identity and liveness's two-strike
     logic still have none**, and they are the same shape of regression-prone pure function
     that earned `detect_lang` its suite. This is the one genuinely open piece of the
     review's central theme.

3. **Expand `replaces.json`.** 194 of 2,834 entries → 290 products. Read the `_README` block
   first: `kind` (`software` / `service` / `paid-tier`) and `confidence` both matter, and
   getting them wrong produces confident category errors. `export_json.py` **fails the build**
   on an invalid value and warns on keys matching nothing.
   ⚠ **Check existing product names before adding.** Yesterday's additions used more specific
   names than the seed already had (`Dropbox Business` beside `Dropbox`), splitting one
   product across two index keys.

4. **Databook design harmonisation is handed off**, not done. See
   `~/Antigravity/Databook2/docs/LANDING-HARMONISATION-PLAN.md` — Phase 1 is the approved
   visual change, Phase 2 adds a `databook` variant to the token package. Give it to a
   Databook-focused session; it is written to be executed cold.

5. ~~**`enrich_desc.py` is rate-limited to ~8 entries per run.**~~ **Fixed 2026-08-14, and it
   needed no credential at all.** The step read `GITHUB_TOKEN` alone — never set under
   launchd — while `liveness.py` had been resolving one via `gh auth token` the whole time.
   `enrich_desc` now imports `liveness.gh_token()`; verified under a launchd-like environment
   (`env -i PATH=<plist PATH> HOME=$HOME`), the core limit goes **60 → 5,000/hour**, so the
   251-entry backlog should clear in the first run rather than ~31 weeks.
   ⚠ **The earlier advice here was wrong twice.** It is not blocked on a credential, and the
   plist is the wrong home for one regardless: LaunchAgent plists are world-readable
   (`-rw-r--r--`) and get swept into backups, which is precisely why `run.sh` reads the Vercel
   token from a chmod-600 file. `gh_token()` now takes `GITHUB_TOKEN`, then
   `~/.config/govoss/github-token`, then `gh` — so an unscoped PAT is available as a
   least-privilege option (the `gh` token carries `repo` and `workflow`), but it is optional.
   **Confirm on the first run** that `enrich desc` reports filling hundreds, not ~8.

6. **Screen-reader testing has never been done.** The audits are automated contrast sweeps
   plus keyboard. VoiceOver/NVDA against the catalog page is the honest next step, and until
   it runs nothing should claim conformance. Note `/products.html` is a large table — the
   surface most likely to expose problems.

7. **The get-involved block is duplicated** in `_ui_template.py` and `build_sources.py`. It
   already caused one bug: a fix applied to one left the other stale. Same shape as the
   `SRC_LABEL` duplication removed this session.

8. **Two OSOR leads left, both small:** ICT ReUse Belgium and Helsingborg City. Check
   `sources.py:SURVEY` for what has already been rejected and why before chasing anything.

9. **8 Bulgarian entries show no description** — their entire upstream text was a contract
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
