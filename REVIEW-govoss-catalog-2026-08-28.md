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
> **F5–F8 remain open** (dedupe re-run wipes provenance; translation-key rot;
> Vercel stored-login; one test file). **None of this has run unattended yet** —
> 2026-09-14 07:00 is the first scheduled run to exercise it.
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

### F6 · LOW · Translation-key rot is invisible
`merge_translations.py` (no orphan report)

- Reworded upstream text silently falls back to the foreign original (documented,
  accepted), but nothing reports tr_*.json keys that no longer match anything — the
  exact rot `export_json.py` warns about for `replaces.json` keys. A wording change
  upstream shows up only as the English-coverage tile drifting down by ones.
- **Fix:** print (and count into history) unmatched-key totals per tr file.
- **Confidence: confirmed.**

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
