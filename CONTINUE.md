# Open items

Where the work stands as of **2026-09-23**. `CLAUDE.md` (auto-loaded) is the rules;
`ARCHIVE.md` holds the reasoning and incidents behind them, including the full
long-form manual `CLAUDE.md` was pruned from on this date. Neither is required
reading beyond what loads by itself.

**State: 3,054 active entries · 3,553 rows · 19 catalogues · 16 countries and bodies.**
Live at https://govoss.cat (Catalan at `/ca/`), MCP at https://mcp.govoss.cat, both on
Cloudflare. Pipeline `bash run.sh`, scheduled Mondays 07:00, publishes and commits itself.

## The one idea, if you remember nothing else

**Every failure sensor here started as a `print`, and the fix is never "add a warning":
it is "write it where the page already looks."** The known instances are files
`/sources.html` reads - `cache/_fetched.json`, `summary.failed_at`,
`out/taxonomy_unmapped.json`, `out/translation_orphans.json`, `out/deploy_auth.txt`,
`out/i18n_missing.json` - plus `stage_guard.py`, the same idea one step further: a stage
that DESTROYS data refuses instead of reporting. Corollaries that cost real sessions:
the total is rarely the trigger (use a delta); a missing previous measurement is not
zero; if a guard cannot be made to fail, delete it.

## State - verified, not recalled

```bash
git status --short && git log --oneline origin/main..HEAD   # clean, nothing unpushed
for t in test_*.py; do python3 $t; done                     # 11 suites, 506 checks
python3 -c "import json;d=json.load(open('site/status.json'));print(d['state'],d['problems'])"
```

- Tree clean on `main`, nothing unpushed, one worktree. Last commit `e552cb0`.
- **Last run 2026-09-23**, trigger `manual`, all 19 steps ok, deployed and recorded
  (`6eb6635 Data: 2026-09-23 run - 3,054 entries (+197)`). It was the first live run
  of `first_seen.py`, the language fixes, variants, Switzerland and DIGG - all verified.
- **11 suites, 506 checks, all passing.** Manual on purpose.
- **`/sources.html` reads `warn` for ONE reason: F7**, the deploy running on wrangler's
  stored login. Intended until a token exists (Waiting on a human).
- Liveness 3,298 ok of 3,396 checked, 27 dead, 39 archived, 67 unknown.
- Variants: 12 linked to 9 cores (2 curated, 9 publisher `isBasedOn`, 1 fork - Bulgaria's
  CKAN). `replaces.json`: 303 keys, 300 active entries -> 343 products (+92 rows 2026-09-23, not yet
  deployed); 65 products still have no alternative. Orphaned translation keys: 3.
- Review `REVIEW-govoss-catalog-2026-08-28.md`: F1-F6 closed, F8 at 7 of 8 gaps, F7
  code-complete and credential-blocked (now a Cloudflare credential).

## Invariants - break these and something already fixed re-breaks

Tested ones live in `CLAUDE.md` › Tests as one line each. These are silent if violated:

- **`fetched_at` and `summary.checked` advance ONLY on success.** Stamp either on a
  failure and staleness becomes undetectable.
- **Never store a per-run value PER RECORD** - per-source or summary only.
- **`--from-cache` must not write `_fetched.json` / `_timing.json`** (guarded by `if want:`).
- **`harvest.py` exits 0 on a failed source, on purpose** - one flaky source must not
  block the publish of eighteen good ones.
- **`sources.py:SITE_URL` is the only place the address is written**, and every wrangler
  config pins `account_id`. Remove the pin and a cached login can deploy elsewhere.
- **Only one wrangler config may claim a hostname** (`www.govoss.cat` is `govoss-www`'s).
- **`build_ui._fs_ident()` must equal `first_seen.ident()`** or the Recently-added strip
  silently empties.

## Waiting on a human - not work that was skipped

- **A Cloudflare API token (F7)**, Workers Scripts:Edit on Devin@sarapis.org's Account.
  Verified absent: `~/.config/govoss/` holds only its README. One command:
  `printf '%s' 'TOKEN' > ~/.config/govoss/cloudflare-token && chmod 600 ~/.config/govoss/cloudflare-token`
- **Delete the OLD MCP Worker** `govoss-mcp.devin-31f.workers.dev` (still answering, still
  the pre-variant code) - it is in the itspruvn.com Cloudflare account, which the
  deploy login cannot reach. Nothing in the repo points at it any more.
- **Redeploy the MCP Worker** (`cd mcp-server && npx wrangler deploy`): its code changed
  2026-09-23 - search now reads owner and also-known-as (both promised, neither searched), and
  the instructions no longer claim "17" catalogues. Safe in either order with Monday's run:
  the old Worker ignores the new index fields. Verify with a `search_entries` for "Rocket.Chat".
- **A Catalan speaker's read of `/ca/`** before pointing Catalan institutions at it. The
  strings are machine-written; `i18n/ca.json` is the one file to edit.
- **The demand-side go/no-go** (`DEMAND-SIDE-CATALOGUE.md`) - a scope decision about what
  the catalogue is. And three drafted, unsent documents (an OpenForum Europe reply, an
  OFE-voiced EU defect report - session artefacts, not committed - and
  `DEMAND-SIDE-CALL-FOR-SOURCES.md`).

## Check on the next run (2026-09-28) - first live run of five changes

Expected, from an end-to-end run on a scratch copy (harvest --from-cache .. variants):
- **Active 3,054 -> 3,030.** 21 rows flagged by the licence filter (12 `closed-licence`,
  9 `non-commercial-licence`); 4 new merges - KNIME (redirect loan), Prometheus, Spring
  Boot, Ubuntu (Swedish homepages now `landing`); FreeFileSync splits, correctly (its
  SILL row is flagged). Démarches simplifiées stays ONE entry (repo-rename loan).
- **`out/crosswalk_cache.json` shows three fresh `fetched_at`** and no error; the step
  adds ~6 minutes. A 429/503 from Wikidata falls back and is reported, never fails.
- **Sweden re-harvests into the new shape** (58 repos, 109 landings). If SE fails that run,
  its old checkpoint is reused and the 3 Swedish merges wait a week - not a regression.
- **Recently added shows no false "new" entries**: the 4 identities that move were
  migrated in `cache/_first_seen.json` (all baseline `null`).
- Liveness checks ~109 fewer URLs: Swedish homepages were being checked as repos.
- **Helsingborg's first harvest** (source 20, `hbg`): 291 rows, 103 set aside as
  `wordpress-plugin`, ~98 active and correctly shown as Recently added. With it, the
  scratch run gave **active 3,128** (3,030 + 98); update the header counts in CLAUDE.md
  and here (20 catalogues) once the run confirms them.
- **22 descriptions change language** as DIGG, OS2, ARTE and Helsingborg re-harvest (one
  Swedish/Danish/Portuguese marker under the org's hint no longer defaults to English);
  all have translations, so like-for-like untranslated stays 13 -> 13.

## Candidates, ranked

**Scope rule (owner, 2026-09-23): government-produced catalogues only - never a list
govoss curates itself.** The UK was measured and has no catalogue (`sources.py:SURVEY`
GB entry, status `none-found`; GCHQ folded into it). A hand-picked list of 40 UK
products is parked in `UK-CURATED-DRAFT.md` and Hub task `dc3de350` (Backburner).

1. **Expand `replaces.json` by SHAPE, not sweep.** First pass done 2026-09-23 (+92 rows,
   66 entries, 16 new products). Two routes worked: the DEMAND side (products in
   `proprietary.json` with no alternative - 13 of 78 closed; the other 65 are verticals
   with nothing in the catalogue, a real gap not a to-do) and the SUPPLY side (unmapped
   entries that carry a Wikidata QID - recognisable software; 467 of them, ~50 mapped).
   n8n was skipped on purpose: its Sustainable Use License is not open source.
2. **Licence filter shipped 2026-09-23, first live on the next run** (`filters.py`
   `LICENCE_RULES`): 21 rows flagged - 12 `closed-licence` (all SILL: Veeam, Obsidian x2,
   PDF24, Postman, n8n, IrfanView, Balabolka, HEC-RAS, Wink, silhouette, FreeFileSync) and
   9 `non-commercial-licence` (7 DPG content items, 2 SILL). Verify on that run that the
   flagged count by reason matches. Deliberately NOT flagged, owner's call: Graylog (SSPL,
   genuinely not OSI), MongoDB and PDFgear (licence unknown in SILL; both closed in fact),
   and three publiccode-tier NC entries the publiccode exemption protects.
3. **F8's last gap**: crosswalk's `__main__` wiring (Comptoir precedence, org-shared-homepage
   skip). `get()` and the Workers are now pinned (`test_harvest_get.py`, `test_workers.py`).
   **Screen-reader testing** has never been done.

## Traps - looks broken but is not, and vice versa

- **`www.govoss.cat` and `govoss.cat` are different Workers.** A deploy of the site never
  touches `www`, and `run.sh` never redeploys `govoss-www` or `mcp-server` (no data).
- **The old `govoss-catalog.vercel.app` redirect has no CORS header**, so a browser page
  fetching the OLD JSON cross-origin fails. Scripts and agents follow it. The `www`
  redirect DOES carry CORS - by design, verified end to end.
- **`/sources.html` can warn about missing page translations one run late** - it is built
  before `/api.html` and `/products.html` and reads their entries from the previous run.
- **3,070 of 3,391 first-seen ids are `null`** - the baseline, known and never new. Not a gap.
- **A variant list that includes an obvious mirror is expected**: Munich's SDS Calculator
  links to itself under two catalogues via its publisher's `isBasedOn`. It folds; harmless.
- **The vendored design-token CSS mentions `govoss-catalog.vercel.app` in a comment.** It is
  copied from upstream as-is; do not "fix" it here.
- **`out/` and `site/` are gitignored** - absent on a fresh checkout; `build_sources.py`
  degrades to `ok`, and `test_built_pages.py` SKIPs until the pages are built.
- **The browser pane returns stale and blank frames.** Measure the DOM; rebuild `site/`
  before testing it. A `curl` seconds after a deploy can also hit a stale edge copy -
  cache-bust, and re-check before concluding anything.
- **`PAGINATION-BUG.md` is about someone else's service**, not a defect here.
- **`python3 -B` for sabotage runs.** Same-second, same-size edits otherwise run stale
  bytecode - this produced a false "guard is load-bearing" conclusion once this session.

## Last session (2026-09-22 → 23), in one screen

Shipped, each verified live or by test: shared get-involved block; per-source language
fixes for SILL/NL (`lang_with_prior`) and Munich/DPG (`lang_assume_en`); +52
`replaces.json` mappings; the variants system (`variants.py`, curated/publisher/fork
evidence, inheritance, folding, MCP + products fields); Switzerland and DIGG sources and
the shared ä/ö language fix; the OSOR list fully evaluated (`sources.py:SURVEY`); Catalan
copies of all four pages (`i18n.py`); hosting moved from Vercel to Cloudflare at
govoss.cat with `www` and `mcp.` subdomains; `CLAUDE.md` pruned 949 -> 243 lines into rules.
Mistakes worth knowing: one commit (`84ec9c3`) went out with a failing check (fixed in
`ea3f93f`); a sabotage script once left `variants.py` broken (restored from a backup).

---

## Starting the next session

> I'm continuing work on ~/Antigravity/govoss-catalog, a union catalogue of government
> open source software (live at https://govoss.cat, repo github.com/sarapis/govoss-catalog).
>
> Read `/Users/devin/Antigravity/govoss-catalog/CONTINUE.md` first - it has the state,
> what's waiting on me, the ranked next moves, and the traps. Read
> `/Users/devin/Antigravity/govoss-catalog/ARCHIVE.md` only if a rule in `CLAUDE.md` is too
> terse to apply and you need the reasoning behind it.
>
> Start with candidate 1: expand `replaces.json` by shape.
>
> Do not write a handoff, continuation prompt, or session record unless I ask for
> `/handoff`. End your turn with what you did and what you recommend next.
