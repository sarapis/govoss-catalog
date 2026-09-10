# Code review — sarapis/govoss-catalog — 2026-08-28

> ## ⚠ STATUS: all four actionable findings are FIXED (2026-09-10)
>
> | | | |
> |---|---|---|
> | **F1** failed source publishes as success | `bb59fb7` | `cache/_fetched.json`; `fetched_at` advances only on success; `/sources.html` warns >15d, critical >29d |
> | **F2** `os2()` overwrites its good checkpoint | `bb59fb7` | raises on failure **and** regression; `github_org_scan` now authenticates via `liveness.gh_token()` |
> | **F3** crashed liveness shows green | `100e757` | annotates `summary.failed_at`/`last_error`, preserves `checked`; page warns |
> | **F4** unmapped taxonomy value reaches nobody | `100e757` | `out/taxonomy_unmapped.json`; page warns naming the values |
>
> | **F5** re-running dedupe wipes provenance | `2026-09-10` | `stage_guard.assert_pre_dedupe()`; both dedupe **and taxonomy** refuse on merged input |
>
> | **F6** translation-key rot is invisible | `2026-09-10` | `out/translation_orphans.json`; page warns on GROWTH, runlog trends it |
>
> | **F8** one test file guards one function | `2026-09-10` | 6 suites / 163 checks; **5 of the 8 named gaps** incl. both priorities |
>
> **F7 remains open** (Vercel stored-login — a credential decision). F8 is
> substantially addressed but not closed: `get()`'s raise semantics, crosswalk's
> three guards and the Worker still have no tests. **None of this has run
> unattended yet** — 2026-09-14 07:00 is the first scheduled run to exercise it.
>
> Three bugs were found *while fixing*, all invisible to reading: the F1 warning
> was a silent no-op keyed on the wrong dict (`"DK/os2"` vs `"os2"`); `NOW` was
> referenced in `harvest.py` and never defined, which would have thrown on the
> first real harvest; and `--from-cache` blanked `_timing.json` and
> `_fetched.json` to `{}` — a bug `_timing.json` had carried since it was added.
> That ratio is the argument for testing a guard by making it fire.

**Scope:** full pipeline read (harvest, checkpoints, run.sh gates, dedupe, crosswalk,
liveness, translations, export, MCP Worker, schedule/secrets). Page builders read at
their data edges only. ~7,022 Python lines across 20 files, plus run.sh and a 358-line
Worker.

**Reviewer disclosure:** I authored commits `b79dcf9..11e5c8c` in this repo earlier the
same week (UI stamp retirement, doc rewrite, dead CSS removal, the `enrich_desc` token
fix, a `meta.json` key). Those areas got the same scrutiny, but a second reader should
weight them accordingly.

**Evidence run:** `test_detect_lang.py` → 23/23 pass. Six real scheduled runs in
`~/Library/Logs/govoss-harvest.log` were used as ground truth throughout — including one
live warning (F4) currently being ignored. Deployed-environment checks were done against
the installed launchd plist and the real filesystem, not the repo copy.

**Phase 3½:** 17 draft findings, 7 killed on refutation (listed at the end).

---

## Verdict

Deployable, and genuinely well-engineered against the failure class it names for
itself — the docs are unusually honest and most tripwires exist. But the tripwires are
**advisory prints into a log nobody reads**, while the one hard gate (steps.tsv → deploy)
is fed by sensors that report success on failure. The compound result: several realistic
failures publish a confidently wrong catalogue, commit it with a "Data: <date> run"
message, and show green on the status page. Every high/medium finding below is a variant
of that one theme.

---

## Findings

### F1 · HIGH · A failed harvest publishes and commits as success
`harvest.py:980-1015`, `run.sh:172-176`

- **Claim:** any number of failed sources — including all 17 — exits 0; the publish gate
  reads only step exit codes, so the run deploys and pushes a commit titled
  `Data: <date> run` built partly (or wholly) from stale checkpoints.
- **Trace:** per-source `except Exception` records `failed[k]` and continues → checkpoint
  reused (by design) → `main()` falls off the end after printing `FAILED SOURCES` —
  there is no `sys.exit(1)` path for it (`sys.exit(2)` at :968 fires only for an unknown
  source *name*) → `steps.tsv` gets `harvest 0` → `publish()`'s awk gate passes →
  deploy + `record` commit.
- **Why it matters here:** checkpoint reuse is intended degradation, but it is
  **unbounded and invisible**. Checkpoint records carry no date field (verified:
  `src_it.json`, 550 records, zero date-ish keys); the only signal is file mtime, which
  nothing reads. The status page's per-source alarm (`build_sources.py:97`) fires only on
  a *zero* count — a reused checkpoint contributes its old non-zero count, so a source
  failing for six months renders as current forever. `FAILED SOURCES` reaches only the
  launchd log — the exact "push nobody reads" this repo's own CLAUDE.md warns about.
- **Fix:** stamp a `fetched_at` per checkpoint file (one summary field, not per record —
  same rule as liveness); surface per-source age on /sources.html with a warn threshold
  (>2 runs stale); make harvest exit non-zero when `failed` is non-empty **or** write
  `failed` into a file runlog/build_sources reads, so staleness is visible even though
  the run legitimately continues.
- **Confidence: confirmed** (code path traced end to end; not simulated against the
  live schedule).

### F2 · HIGH · `os2()` overwrites its good checkpoint with a silently truncated scan
`harvest.py:454-463` (the swallow), `harvest.py:277-279` (the cause), `run.sh:119` (the missed tripwire)

- **Claim:** Denmark's 214 records can silently shrink to whatever was fetched before a
  GitHub rate limit hit, published and committed, with **no** warning firing anywhere.
- **Trace:** `github_org_scan` authenticates only via the `GITHUB_TOKEN` env var
  (`harvest.py:278`) — **verified absent from the installed launchd plist** (env is
  PATH/HOME/GOVOSS_TRIGGER only), so production runs unauthenticated at 60 req/hr.
  The run makes ~27+ API list calls (IMIO 3 pages, governmentbg 2, amagovpt, ogcio, plus
  ≥1 per each of **20** OS2 orgs). When a 403 arrives mid-`os2()`: `get()` raises
  immediately on 403 (`harvest.py:63-64`) → `os2()`'s per-org `except Exception` prints
  and **continues** → remaining orgs 403 too (same hour) → `os2()` *returns* the partial
  list → `main()` treats it as success and **overwrites `cache/src_os2.json`**,
  destroying the last-good copy the checkpoint design exists to keep.
- **The tripwire miss:** worst-case loss is −214 of 2,789 ≈ 7.7% — **below** the 10%
  shrink threshold at `run.sh:119`, so even the advisory warning stays silent. The
  per-source diff lines print only into the log.
- **Contrast:** `be()`/`bg()`/`pt()`/`ie()` let the exception propagate → source fails →
  checkpoint kept. `os2()` is the one adapter that defeats its own safety net.
- **Fix:** (a) use the `gh_token()` chain in `github_org_scan`, exactly as
  `enrich_desc.py` was fixed to do this week — one line, lifts the budget 60→5,000/hr;
  (b) in `os2()`, raise if any org failed (or if `len(out)` < half the checkpoint's
  count) instead of returning a partial as success.
- **Confidence: confirmed** for the code path and the missing token (config verified);
  the 403 trigger itself has not occurred in the six logged runs — stated plainly.

### F3 · MEDIUM · A crashed liveness run shows green on the status page
`liveness.py:371-376`, `build_sources.py` (steps table)

- **Claim:** `liveness.py` catches any exception from `main()` and `sys.exit(0)` — so
  `steps.tsv` records `liveness 0`, the status page renders the step **ok**, and the
  stale `liveness.json` keeps feeding old dead/ok counts to runlog, export
  (`last_checked`) and the site, indefinitely if the crash is persistent (e.g. a GraphQL
  schema change).
- **Why it's a finding despite being by design:** fail-open is the right call for a
  monitor ("a monitor that can fail the pipeline gets switched off") — but the *step
  ledger* then lies. "No newly-dead repos" is rendered identically whether the check ran
  clean or never ran. The repo's own bug-pattern #3 (absence of evidence) applies to its
  own monitor.
- **Fix:** keep exit 0, but write a distinct marker (`liveness SKIPPED` in steps.tsv, or
  a `summary.failed: true` in a sidecar) and have `build_sources.py` warn when
  `summary.checked` is older than the run it is rendering.
- **Confidence: confirmed** (path traced; crash simulated mentally, not injected).

### F4 · MEDIUM · The taxonomy unmapped-value alarm fired on the latest run and reached no one
`taxonomy.py:267`, live instance in the 08-24 run log

- **Claim:** `!! 1 UNMAPPED source values: 'information-and-communication-technology' (2)`
  printed on 2026-08-24; taxonomy exited 0; the two entries shipped unclassified; the
  status page has no channel for it (its problems list is failed-steps / overdue /
  zero-count only).
- **Why it matters:** CLAUDE.md's stated standard is "an unmapped value is reported as a
  bug" — but the report lands in a log the same docs call a dead letterbox. This is not
  hypothetical: it is happening now, and the warning's value ("only useful while it stays
  near zero") decays every week it scrolls by.
- **Fix:** count unmapped values into `history.json` via runlog and render a warn chip on
  /sources.html when non-zero; and map the one live value.
- **Confidence: confirmed** (live occurrence in the log).

### F5 · MEDIUM-LOW · Re-running dedupe destroys multi-catalogue provenance, silently
`dedupe.py:211-218`

- **Claim:** the `len(g)==1` branch **unconditionally overwrites** `catalogue_entries`
  and resets `catalogue_count` to 1. Run `python3 dedupe.py` a second time on already-
  merged output (no fresh harvest in between) and every merged record loses its
  "In N catalogs" provenance — the page's only endorsement pill — while everything else
  looks normal.
- **Reachability:** operator error only; the documented workflows re-run harvest first.
  But the handover's question — "does any stage detect that its precondition was not
  met?" — has the answer *no*, and this is the concrete damage. All in-place
  catalog.json writers share the shape; dedupe is the one where a re-run corrupts rather
  than merely repeats.
- **Fix:** guard at entry: if any record already carries `catalogue_count`, refuse
  (or skip the reset when `catalogue_entries` exists).
- **Confidence: confirmed** by code reading; not executed against the live file (would
  have modified state mid-review).

**CLOSED 2026-09-10 — `stage_guard.py`, and the review's parenthetical was the wrong
one of its two options.** "Skip the reset when `catalogue_entries` exists" makes the
stage merge-aware, which means a record that legitimately *stopped* being listed by
three catalogues keeps its stale count forever, with nothing to say so — a loud bug
traded for a silent permanent one, in the reassuring direction. So it refuses, with no
`--force`; the way forward is `harvest.py --from-cache`, which is offline and cheap.

**Executing it found a second instance the code reading missed, exactly where the
review said to look** ("all in-place catalog.json writers share the shape"):
**`taxonomy.py` has the same defect.** `functions` is in `dedupe.py:UNION_LIST`, so a
survivor carries functions from its merge partners, and `classify()` recomputes from
the survivor alone — returning at most one function from the inference branch, and
never consulting inference once a source category maps. A second pass **narrows 45
entries** (7-Zip loses `data-analytics`, Apache HTTP Server `infrastructure`, Decidim
`citizen-services`). Both stages now call the same guard.

Verified by sabotage, not by watching it pass: with the guard stubbed to `return
False`, both stages exit **0** and modify `catalog.json` — the silent destruction, run
for real against a backed-up copy rather than reasoned about. `test_stage_guard.py`
locks in both directions, including the two implementation mistakes that would leave
the guard useless (`all()` for `any()`, forgetting to skip `excluded` rows) and a
subprocess case asserting `catalog.json` is byte-identical after a refusal.

### F6 · LOW · Translation-key rot is invisible
`merge_translations.py` (no orphan report)

- Reworded upstream text silently falls back to the foreign original (documented,
  accepted), but nothing reports tr_*.json keys that no longer match anything — the
  exact rot `export_json.py` warns about for `replaces.json` keys. A wording change
  upstream shows up only as the English-coverage tile drifting down by ones.
- **Fix:** print (and count into history) unmatched-key totals per tr file.
- **Confidence: confirmed.**

**CLOSED 2026-09-10.** Done as specified — per-file totals printed,
`out/translation_orphans.json` written for the page, total trended into `history.json` —
plus two things the finding did not anticipate:

**The natural implementation of "unmatched" is unusable.** "Keys this pass looked up" reports
**1,762 of 1,762 orphaned** on already-merged input, because a merged row carries
`translated: True` and short-circuits before the lookup. The rule hashes the source text
still present in the catalogue — `short_desc` on a raw row, `desc_src` on a merged one —
giving a re-run-stable **59 of 1,762** (3%). Checked against all 1,731 merged rows carrying a
`desc_src`: zero false orphans.

**The total cannot be the trigger.** Rot is expected to be non-zero and slowly growing, so
warning on the standing 59 would ship a page reading `warn` from day one — the state in which
a reader stops looking, which is the same end state as no sensor. `build_sources.py` warns on
GROWTH against the previous run, and treats a missing previous figure as unknown rather than
zero; the whole matrix was verified (prev absent / 59→60 / flat / improved / 0→60).

`test_translation_orphans.py` exercises both rules side by side and was validated by
sabotage.

### F7 · LOW · Deploy auth rests on the Vercel CLI's stored login
`run.sh:205-208`; verified: `~/.config/govoss/vercel-token` does not exist, no
`VERCEL_TOKEN` in the plist

- The plist's own comment calls this the fragile mode ("a stored login can be revoked and
  would then fail silently-ish every Monday"). Failure is at least *visible* — deploy
  step exits non-zero, record is skipped, and the browser-side Stale badge flips after 8
  days — so this is config debt, not a silent-wrongness path.
- **Fix:** mint a deploy-scoped token into the chmod-600 file the code already prefers.
- **Confidence: confirmed** (filesystem checked).

### F8 · LOW · One test file guards one function
`test_detect_lang.py` (23/23 pass) is the entire suite

- Untested, specifically: `get()`'s raise semantics (which F2 turns on), the dedupe
  identity rules and `merge()` union behaviour, crosswalk's three guards, `filters.py`
  rules, translation-key hashing (the raw-vs-stripped trap is documented but not locked
  in), liveness's two-strike logic, `export_json`'s vocabulary validation, and the
  Worker. `detect_lang` got its suite after five recurrences; dedupe identity and the
  two-strike logic are the same shape of pure, regression-prone function and are one
  incident away from earning theirs the same way.
- **Confidence: confirmed** (absence verified).

**SUBSTANTIALLY ADDRESSED 2026-09-10 — 5 of the 8 gaps, including both named priorities.**
The suite went from 1 file / 23 checks to **6 files / 163 checks**:

| gap | status |
|---|---|
| dedupe identity + `merge()` union | `test_dedupe_identity.py` — 41 checks |
| liveness two-strike logic | `test_liveness_strikes.py` — 33 checks |
| translation-key hashing | `test_translation_orphans.py` (landed with F6) — 14 |
| `filters.py` rules | `test_filters.py` — 28 of its 37 |
| `export_json` vocabulary validation | `test_filters.py` — 9 of its 37 |
| `get()` raise semantics | **still none** — needs a stubbed opener |
| crosswalk's three guards | **still none** — inline inside SPARQL-calling functions; needs the same extraction `fold_history` got |
| the MCP Worker | **still none** — JS on Cloudflare, outside this Python suite |

`liveness.fold_history()` was extracted from `main()` to make the state machine testable at
all; the extracted body was verified line-for-line identical to the original block, and the
refactored monitor was then run for real (6m43s, 3,065 ok / 27 dead / **1 pending** / 1 newly
dead), so the refactor is confirmed end-to-end and not merely by unit test.

Every suite was validated by SABOTAGE, which is what turned up three defects the tests were
not looking for:

1. **`norm_repo`/`norm_site` substituted `^www.` and `^https?://` BEFORE lowercasing**, so a
   capitalised `Www.` or `HTTPS://` survived and produced a key that could not join its
   lowercase twin. Latent — **0 of 4,464 real URLs** trigger it — and fixed with `re.I`,
   verified a no-op on every one of those 4,464.
2. **The `replaces.json` refusal named the key lowercased** (`limesurvey` for a file that
   spells it `LimeSurvey`), i.e. pointed at a string you cannot grep for in the hand-edited
   file it tells you to fix. Now iterates `replaces_raw` instead of the lookup map.
3. **`filters.py`'s cost comment was stale in the direction that argues for weakening the
   rule.** It claimed a set-aside entry "disappears from /entries.json and every derived
   file… 316 entries removed from the public API". `entries.json` has carried every row
   flagged since 08-14 — verified: 3,318 rows, 484 flagged, PloneMeeting present. A stale
   cost estimate is an argument for softening a rule that is cheaper than advertised.

---

## Checked and sound

- **The deploy/record gate itself** (`run.sh publish()`/record): awk over steps.tsv,
  refusal paths, project-link guard, branch/rebase guards, explicit path list, no
  force-push — all as documented. The problem is upstream sensors (F1/F3), not the gate.
- **`get()`** raises on persistent failure and immediately on 401/403/404 — no
  None-returns to propagate as empty data.
- **Dedupe identity rules**: QID → repo → name+homepage conjunction, with the
  documented counterexamples (Angular/AngularJS separate; umwelt.info non-merge)
  holding in code, not just in prose. Survivor scoring's namespace-containment logic
  matches its docstring.
- **Crosswalk guards**: software-class SPARQL check, org-shared-homepage skip, exact-name
  only — the 08-24 log shows them working (36 skipped, 17 rejected as non-software).
- **Liveness two-strike + web-HEAD confirmation + unknown-never-dead**: all real; the
  `dead_count` reset on an `unknown` observation delays verdicts (conservative — fine).
- **`enrich_desc.py`**: fail-soft, cached, resumes; token chain verified working under a
  launchd-shaped env (41-byte token resolves; 08-17 run made 191 calls, no limit).
- **The MCP Worker**: fixed fetch paths (no arg reaches a URL), clamped limits,
  status-aware caching with cache-key-busting retry, errors that name the URL. Public
  and keyless is by design for read-only data. `.dev.vars` is gitignored, untracked.
- **Deterministic outputs**: stable_order + sort_keys everywhere committed; regenerating
  the geo/catalogue files reproduces byte-identical output.

## Not reviewed

- `build_ui.py` / `build_sources.py` / `build_api.py` / `build_products.py` /
  `theme.py` / `_ui_template.py` beyond their data-input edges (~2,300 lines of HTML/CSS
  assembly; failure mode is visible on the page, and I edited several this week —
  fresh-eyes value was higher elsewhere).
- `scripts/gen_*.py` (hand-run seed tooling), `analyze.py` (read-only), vendored CSS,
  `_scratch/`.
- Vercel/Cloudflare dashboards (no access assumed this session beyond what the CLI
  already proved); Worker secrets in production were not enumerated — the Worker's code
  requires none.
- `PAGINATION-BUG.md` — upstream report, per the handover.

## Themes

One theme, five findings (F1–F4, F6): **every failure sensor that exists is a print;
every hard gate reads a sensor that cannot trip.** The repo already knows this — its
docs coined "a green pipeline log once hid a dead harvest" — but the pattern has
regrown one layer up: steps.tsv was built so the end state can't hide a failed step,
and now failed *sources*, crashed *monitors*, unmapped *values* and rotted *keys* all
hide inside steps that exit 0. The fix is one habit applied five times: everything
currently printed as `!!` should also land in `history.json` and render as a chip on
/sources.html, which is exactly the pull-based surface the task-drift strip already
proved out.

**Applied all five times as of 2026-09-10** (F1 `cache/_fetched.json`, F3
`summary.failed_at`, F4 `out/taxonomy_unmapped.json`, F6 `out/translation_orphans.json`,
and F5 by refusing rather than reporting). Two refinements the habit needed in practice:
the **total is rarely the trigger** — a sensor for something expected to grow needs a
delta, or the page reads `warn` forever and stops being read — and **a missing previous
measurement is not zero**, which otherwise converts a standing backlog into a day-one
false alarm. Both are the rule `liveness.py` already followed.

## Killed in phase 3½ (7)

1. `gitlab_scan` 60-page cap truncation — cap is ~6,000 projects, far above current
   listings; would show in per-source counts. Hardening, not a finding.
2. Worker SSRF / path injection — tool args never reach URLs; paths are fixed.
3. `meta.json` count ambiguity — fixed this week (`rows_in_entries_json`), verified live.
4. Two-strike reset via `unknown` — delays dead verdicts; conservative by design.
5. name+homepage merge over-collapse — conjunction guard + measured groups all genuine.
6. `.dev.vars` exposure — gitignored, untracked, 1 kv pair.
7. "Deploy fails silently" — it fails loudly in steps.tsv and the next status build;
   downgraded to F7 config note.

## Style note

Comment discipline is the best in the portfolio — most functions explain *why*, with
the incident that taught it. Two nits: `run.sh:5` still says "eight national sources"
(it's 17), and the duplicated `stable_order` in harvest/dedupe is documented as
deliberate but now has a third near-copy of ordering concerns in `export_json.py`'s
compact writer.
