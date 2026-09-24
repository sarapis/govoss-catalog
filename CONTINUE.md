# Open items

Where the work stands as of **2026-09-23 (late)**. `CLAUDE.md` (auto-loaded) is the rules;
`ARCHIVE.md` holds the reasoning and incidents behind them. Neither is required reading
beyond what loads by itself.

**Live: 3,127 active entries · 3,841 rows · 20 catalogues · 16 countries and bodies.**
https://govoss.cat (Catalan at `/ca/`), MCP at https://mcp.govoss.cat, both on Cloudflare.
Pipeline `bash run.sh`, scheduled Mondays 07:00, publishes and commits itself.

## The one idea, if you remember nothing else

**Every failure sensor here started as a `print`, and the fix is never "add a warning":
it is "write it where the page already looks."** The instances are files `/sources.html`
reads - `cache/_fetched.json`, `summary.failed_at`, `out/taxonomy_unmapped.json`,
`out/translation_orphans.json`, `out/deploy_auth.txt`, `out/i18n_missing.json`, and (new)
`out/crosswalk_cache.json` - plus `stage_guard.py`, the same idea one step further: a stage
that DESTROYS data refuses instead of reporting. Corollaries: the total is rarely the
trigger (use a delta); a missing measurement is not zero, and not fresh either; if a guard
cannot be made to fail, delete it.

## State - verified 2026-09-23, not recalled

```bash
git status --short && git log --oneline origin/main..HEAD   # clean, nothing unpushed
for t in test_*.py; do python3 $t; done                     # 12 suites, 545 checks
curl -s "https://govoss.cat/status.json?v=$(date +%s)"       # live state + problems
```

- Tree clean on `main`, nothing unpushed, one worktree, no jobs running. Last code commit
  `e71647c` (the handoff commit follows it).
  Schedule loaded; `bash schedule/install.sh --diff` says the plist matches the template.
- **Last run 2026-09-24 19:39Z**, `manual`, 19 steps ok, deployed on `token-file`,
  recorded (`6cbdcc5`). Everything committed up to `8dae0fc` is live.
- **12 suites, 545 checks, all passing.** Manual on purpose.
- Live `/status.json` still warns F7 (stored login): `/sources.html` is built before
  `deploy` and reads the PREVIOUS run's `deploy_auth`. The next run clears it.
- Liveness 3,486 ok of 3,612, 28 dead, 39 archived, 59 unknown. Variants: 12 linked to 9
  cores. `replaces.json`: 348 keys -> 379 products, all live; 65 products have none.
- MCP Worker version `e22a48dd`, reading the 2026-09-24 index.
- Review `REVIEW-govoss-catalog-2026-08-28.md`: F1-F6 and F8 closed; F7 credential-blocked.

## Invariants - break these and something already fixed re-breaks

Tested ones are one line each in `CLAUDE.md` › Tests. These are silent if violated:

- **`fetched_at`, `summary.checked` and `crosswalk_cache.json` stamps advance ONLY on
  success.** Stamp on a failure and staleness becomes undetectable.
- **Never store a per-run value PER RECORD** - per-source or summary only.
- **`--from-cache` must not write `_fetched.json` / `_timing.json`** (guarded by `if want:`).
- **`harvest.py` exits 0 on a failed source, on purpose** - one flaky source must not block
  the publish of the others.
- **`sources.py:SITE_URL` is the only place the address is written**, and every wrangler
  config pins `account_id`. Remove the pin and a cached login can deploy elsewhere.
- **Only one wrangler config may claim a hostname** (`www.govoss.cat` is `govoss-www`'s).
- **`build_ui._fs_ident()` must equal `first_seen.ident()`**, and a change that MOVES an
  entry's identity (repo_key <-> name|source) must migrate its `cache/_first_seen.json`
  key in the same commit, or it shows as Recently added. Done for 4 ids on 2026-09-23.
- **Network enters crosswalk only through `run()`'s `*_fn` arguments** - put it anywhere
  else and the glue is untestable again (`test_crosswalk_run.py`).

## Waiting on a human - not work that was skipped

- **Cloudflare API token (F7): IN PLACE 2026-09-23**, `~/.config/govoss/cloudflare-token`.
  whoami, token verify (active, no expiry) and an undeployed `wrangler versions upload`
  (version fc337081, production untouched) all pass. The 09-28 run should record
  `deploy_auth` = `token-file`; then close Hub `35f61ead` (at Review).
- **Delete the OLD MCP Worker** `govoss-mcp.devin-31f.workers.dev` - in the itspruvn.com
  Cloudflare account, which the deploy login cannot reach. Nothing points at it.
- **Four licence calls left open** (`filters.py` flags only what the source's licence
  string says): Graylog (SSPL, genuinely not OSI), MongoDB and PDFgear (SILL says unknown;
  both closed in fact), three publiccode-tier NC entries the publiccode exemption protects.
- **Review the 103 Helsingborg WordPress plugins set aside** - reviewed like the iMio rules
  were; two iMio rules were removed after catching real products. The `api-*-manager`
  repos (WordPress-based backends) are the likeliest false positives.
- **A Catalan speaker's read of `/ca/`**. No Catalan phase 2 (owner, 2026-09-23): data,
  products and source notes stay English. Do not re-propose it.
- **The demand-side go/no-go** (`DEMAND-SIDE-CATALOGUE.md`) and three drafted, unsent
  documents (an OFE reply and defect report - not committed - and
  `DEMAND-SIDE-CALL-FOR-SOURCES.md`).
- UK: a curated list of 40 is parked (`UK-CURATED-DRAFT.md`, Hub `dc3de350` Backburner).
  Scope rule: government-produced catalogues only, never a list govoss curates.

## The 2026-09-24 run, checked against its expectations

Matched: 3,127 active (expected ~3,128), 20 catalogues; licence filter 12 + 9; Helsingborg
98 active + 103 `wordpress-plugin`; KNIME, Prometheus, Spring Boot, Ubuntu merged; FreeFileSync
split; Démarches one entry; `crosswalk_cache.json` three fresh stamps; untranslated unchanged
like-for-like (the same 9 active rows); `deploy_auth` = `token-file`.
Contradicted, and resolved:
- **Recently added had 4 non-Helsingborg ids.** Magnolia and Unomi are genuinely new in Munich.
  F13 KI Assistenz: openCode changed its repo upstream (an org URL -> a repo). Mautic: Munich
  newly lists it, the repo-less Munich row won the merge and DROPPED DPG's repo, moving the
  identity. Fixed in `dedupe.merge()` (backfill a sibling's REAL repo; ckan too) - live next run.
- **MCP "rocket.chat" -> 0.** The expectation came from a test FIXTURE (owner + aka); the real
  SILL row has neither and the Swedish "Rocket Chat" row is set aside. Search works as
  promised. Finding it would mean searching the repo URL too - a contract change, not done.
- Liveness: 3,612 URLs, not ~109 fewer - that figure ignored Helsingborg's 291 rows.
- 3 orphaned `tr_de.json` keys: upstream rewordings (KI-Buddy and two others). Sensor working.

## Candidates, ranked

1. **Verify the next run**: Mautic and ckan carry their repos, F7 warning gone.
2. ~~Count checks, never hard-code them~~ - DONE 2026-09-23: every suite now counts
   `len(ran)`. The hard-coded totals were wrong in four suites: liveness 33 (ran 41),
   filters 69 (70), built_pages 69 (76), stage_guard 15 (ran 14 - a phantom pass).
3. **Expand `replaces.json` by SHAPE, not sweep.** Two routes worked on 2026-09-23 (+92
   rows): the DEMAND side (products in `proprietary.json` with no alternative - 13 of 78
   closed; the other 65 are verticals nothing here does) and the SUPPLY side (unmapped
   entries carrying a Wikidata QID: 467, ~50 mapped). n8n skipped: not open source.
   Second supply pass 2026-09-23 (late): +58 rows on 45 keys, 36 new products; the
   remaining ~370 unmapped QID entries are mostly libraries, languages, OSes and
   free desktop tools nobody pays for - diminishing returns on this route now.
4. **Screen-reader testing** has never been done - needs a person with a screen reader.

## Traps - looks broken but is not, and vice versa

- **`www.govoss.cat` and `govoss.cat` are different Workers.** `run.sh` never redeploys
  `govoss-www` or `mcp-server`; redeploy those by hand, only when their code changes.
- **The old `govoss-catalog.vercel.app` redirect has no CORS header** - scripts follow it,
  browser cross-origin fetches fail. The `www` redirect DOES carry CORS (`test_workers.py`).
- **Wikidata's query service truncates with HTTP 200** (11,116 of 28,759 rows, once) and
  answers 429/503 after heavy same-day use. The crosswalk falls back and reports; a manual
  rerun right after a big session often skips Wikidata. Not a regression.
- **Test end to end on a scratch copy, never by hand in the repo.** `rsync --exclude .git
  --exclude site` to the scratchpad, then `harvest.py --from-cache` .. `variants.py`.
  `first_seen.py`, `liveness.py`, `record` and every by-hand stage run rewrite committed
  files, and `taxonomy.py`/`dedupe.py` refuse merged input anyway.
- **Compare stages like-for-like.** A pre-dedupe catalogue diffed against the committed
  (post-dedupe) one shows merged-away rows as "new gaps" - build a baseline with
  `git archive HEAD` and run it to the same stage.
- **`detect_lang` tags English-with-one-foreign-word as foreign under that org's hint**
  ("Custom API Endpoint for Lärrum") - accepted and pinned: visible in the translation
  queue beats foreign text hidden as English.
- **Translation keys hash the RAW text; look rows up by TEXT, not by name.** OS2 has one
  `.github` per org - a name lookup keyed a translation to the wrong repo (caught by audit).
- **`/sources.html` can warn about missing page translations one run late** - it is built
  before `/api.html` and `/products.html` and reads their entries from the previous run.
- **3,074 of 3,395 first-seen ids are `null`** - the baseline, known and never new.
- **Munich's SDS Calculator links to itself under two catalogues** via its publisher's
  `isBasedOn`. It folds; harmless.
- **The vendored design-token CSS mentions `govoss-catalog.vercel.app` in a comment.**
  Copied from upstream as-is; do not "fix" it here.
- **`out/` and `site/` are gitignored** - a fresh checkout has neither; `build_sources.py`
  degrades to `ok`, `test_built_pages.py` SKIPs until the pages are built.
- **The browser pane returns stale and blank frames**, and a `curl` right after a deploy
  can hit a stale edge copy. Cache-bust (`?v=$(date +%s)`) and re-check.
- **`PAGINATION-BUG.md` is about someone else's service**, not a defect here.
- **Sabotage with `PYTHONDONTWRITEBYTECODE=1 python3 -B`**, and check a sabotage actually
  APPLIED: two this session silently did not (shell escaping), and one "passed" only because
  a second guard covered the same case. Filter output to `^FAIL|checks passed`.

## Session 2026-09-23 (evening), in one screen

Shipped, each verified by suite and by scratch end-to-end run (not yet live): UK sized (215
orgs, 14,320 repos, 0 publiccode - no UK catalogue; GCHQ folded into a `none-found` survey
entry); +92 `replaces.json` rows; licence filter; KNIME, Démarches, Prometheus/Spring
Boot/Ubuntu merges via redirect and repo-rename QID loans and a Swedish adapter fix;
crosswalk inputs refresh weekly (they had been frozen since 08-13; P1324 dump now
count-checked); retries for every crosswalk fetch; Helsingborg as source 20 with a
`wordpress-plugin` rule; the one-marker language fix (17 live descriptions were mis-tagged
English); new suites for `get()`, the Workers and crosswalk's glue (F8 closed); MCP search
now reads owner/aka and no longer claims "17" catalogues (Worker deployed, live-checked).
NOT done: nothing run live - the Monday run is the real test of all of it.

## Session 2026-09-22 -> 23, in one screen

Shared get-involved block; `lang_with_prior`/`lang_assume_en`; +52 `replaces.json` rows;
the variants system; Switzerland and DIGG; the OSOR list evaluated; Catalan chrome for all
four pages; hosting moved from Vercel to Cloudflare; `CLAUDE.md` pruned 949 -> 243 lines.
Mistakes: one commit (`84ec9c3`) shipped a failing check (fixed `ea3f93f`); a sabotage
script once left `variants.py` broken (restored from a backup).

---

## To resume

> I'm continuing work on ~/Antigravity/govoss-catalog, a union catalogue of government
> open source software (live at https://govoss.cat, repo github.com/sarapis/govoss-catalog).
>
> Read `/Users/devin/Antigravity/govoss-catalog/CONTINUE.md` first - it has the state,
> what's waiting on me, the ranked next moves, and the traps. Read
> `/Users/devin/Antigravity/govoss-catalog/ARCHIVE.md` only if a rule in `CLAUDE.md` is too
> terse to apply and you need the reasoning behind it.
>
> Start with candidate 1: check the 2026-09-28 run against the "First: check the next run"
> list, and fix whatever it contradicts before starting anything new.
>
> Do not write a handoff, continuation prompt, or session record unless I ask for
> `/handoff`. End your turn with what you did and what you recommend next.
