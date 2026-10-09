# Open items

Where the work stands as of **2026-10-09**. `CLAUDE.md` (auto-loaded) is the rules; `ARCHIVE.md`
holds the reasoning, incidents and older session records. Neither is required reading beyond
what loads by itself.

**Live: 3,175 active entries · 3,883 rows · 20 catalogues · 16 countries and bodies · 169 OSPOs.**
https://govoss.cat (Catalan at `/ca/`), MCP at https://mcp.govoss.cat, both on Cloudflare.
Pipeline `bash run.sh`, scheduled Mondays 07:00, publishes and commits itself.

## The one idea, if you remember nothing else

**Every failure sensor here started as a `print`, and the fix is never "add a warning": it is
"write it where the page already looks."** The instances are files `/catalogs` reads -
`cache/_fetched.json`, `summary.failed_at`, `out/taxonomy_unmapped.json`,
`out/translation_orphans.json`, `out/deploy_auth.txt`, `out/i18n_missing.json`,
`out/crosswalk_cache.json` - plus the refusals one step further: `stage_guard.py`, and since
2026-10-07 the `/ospos.json` contract, which refuses rather than ships a file an outside reader
would choke on. Corollaries: the total is rarely the trigger (use a delta); a missing measurement
is not zero, and not fresh either; if a guard cannot be made to fail, delete it.

## State - verified 2026-10-09, not recalled

```bash
git status --short && git log --oneline origin/main..HEAD   # clean, nothing unpushed
for t in test_*.py; do python3 $t; done                     # 13 suites, 923 checks
curl -s "https://govoss.cat/status.json?v=$(date +%s)"       # live state + problems
```

- Tree clean on `main`, nothing unpushed, one worktree, no runs or preview servers.
  `bash schedule/install.sh --diff`: the plist matches the template.
- **Last run 2026-10-09 15:19Z, `--no-harvest`**, every step ok, deployed on `token-file`,
  recorded (`0dd0a41`); `/status.json` problems `[]`. Last full HARVEST 2026-10-07 19:50Z.
- **openCode (`de`) and code.europa.eu (`eu`) are still on 2026-10-05 data** - both answered 429
  on 2026-10-07 and the short-scan guard kept their last good lists (`cache/_fetched.json`:
  `ok: false`). Monday's run is the first chance to refresh them.
- Liveness (2026-10-07 19:43Z): 3,530 ok, 27 dead, 40 archived, 59 unknown. `replaces.json`
  349 keys; 379 products with an alternative (`meta.json`). Variants: 14 linked.
- `/ospos`: 169 offices (18 government, 33 academic, 118 corporate), all three lists fetched
  2026-10-09 by hand (`python3 fetch_ospos.py`); one world map, 40 pins, 4 offices unplaced.
  `/ospos.json` passes `ospo_contract.doc_problems()` live, as does `/ospos.example-failed.json`.
- First-seen: 3,552 ids, 3,074 of them `null` (baseline). The 12 Helsingborg tools carry
  2026-10-08, so they lead Recently added this week - by the owner's choice.

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
- **A change that MOVES an entry's identity (repo_key <-> name|source) must migrate its
  `cache/_first_seen.json` key in the same commit**, or it shows as Recently added.
- **Network enters crosswalk only through `run()`'s `*_fn` arguments** (`test_crosswalk_run.py`).
- **A failed fetch is never "no data"**: GitLab scans refuse a short list (`test_harvest_get.py`);
  each OSPO list keeps its last good copy (`test_ospos.py`).
- **Two OUTSIDE consumers, both UNNYC**: `/catalogues.geo.json` (their fetch script stops on a
  missing top-level key, an unknown feature `kind`, a changed licence string, or `generated_at`
  != `meta.json`'s - only the last is pinned here, 12c) and `/ospos.json` (contract in
  `ospo_contract.py`, pinned). Change either only together with them.
- **`ospos/locations.json` is hand-curated truth.** `place_from_wikidata.py` only ADDS ids; a
  wrong Wikidata HQ is corrected in the file by hand with `via: "hand, <date>"`, never by
  re-running the script over it.

## Waiting on a human - not work that was skipped

- **UNNYC: send them the corporate-OSPO prompt** (in this session's chat, 2026-10-09). Nothing
  they read changed (FLOSS-PSO rows identical, diffed), but `/ospos.json` gained a source, a
  type, 9 country codes and row fields - a strict script could throw. It is live now.
- **UK scope - reopened by the 2026-10-08 decision?** The owner confirmed government forge orgs
  are in scope. Hub `dc3de350` (Backburner) parked the UK because no UK catalogue exists, with
  "revisit if the scope rule changes"; the UK has 215 government GitHub orgs, 14,320 repos
  (~4.7x the catalogue). Whether that makes UK org scans in scope is the owner's call.
- **The Resources data has no licence statement** (`resources/ospo-resources.json`, by UN+NYC;
  checked 2026-10-09: no licence field). Give one and it goes on the page and in `/resources.json`.
- **Delete the OLD MCP Worker** `govoss-mcp.devin-31f.workers.dev` - in the itspruvn.com
  Cloudflare account, which the deploy token cannot reach. Nothing points at it.
- **Four licence calls left open**: Graylog (SSPL, not OSI), MongoDB and PDFgear (SILL says
  unknown; both closed in fact), three publiccode-tier NC entries the publiccode exemption protects.
- **Numbers outside the headers**: the home search placeholder ("Search 3,175 entries") and the
  pages' meta descriptions still carry counts. They update themselves; offered, not decided.
- **A Catalan speaker's read of `/ca/`** - more chrome this week (home, headers, OSPOs). No Catalan
  phase 2 (owner, 2026-09-23): data stays English. Do not re-propose it.
- **Screen-reader testing** has never been done - needs a person with a screen reader.
- **The demand-side go/no-go** (`DEMAND-SIDE-CATALOGUE.md`) and drafted, unsent documents
  (`DEMAND-SIDE-CALL-FOR-SOURCES.md`; an OFE reply and defect report - not committed).
- FLOSS-PSO data defects (Thessaloniki's Greek "Το", RECIA's empty description): the owner
  reported filing them on their forum 2026-10-08 - not verified here. A fix arrives by the
  weekly fetch with nothing to do.

## Candidates, ranked

1. **Check Monday's 2026-10-12 scheduled run** - the first unattended run of everything since
   2026-10-07: openCode (561 records, 478 active today) and code.europa.eu (23 records, 14
   active) refreshed, both `ok: true` and fresh
   on `/catalogs`; the harvest log says 18 / 31 / 120 OSPOs (`todo-landscape` fetched unattended
   for the first time); the 12 Helsingborg tools still active after a FULL harvest; home cards
   equal their pages (12e); `/status.json` `[]`.
2. **The four unplaced companies** (Cuemby, Intersect MBO, JiHu (GitLab), WalmartLabs): place
   only from a verifiable source; the page names them meanwhile. Also spot-check a few Wikidata
   placements by eye - six were wrong in the first pass.
3. **Re-measure contrast for the corporate chip** - 4.62:1 (AA), below the 2026-08-13 audit's
   lowest of 4.9. A darker text token would fix it.
4. **OSPO map density** - one world map merges the Bay Area into a 40-office pin and crowds
   Europe; on a phone it is 305x124px. Only if the owner wants it: zoom, or a smaller merge.
5. **OSPO "ownership" field for academic offices** (public/private/intergovernmental) - asked as
   optional by UNNYC; needs each office verified (CERN is intergovernmental, not public).

## Traps - looks broken but is not, and vice versa

- **`www.govoss.cat` and `govoss.cat` are different Workers.** `run.sh` never redeploys
  `govoss-www` or `mcp-server`; redeploy those by hand, only when their code changes.
- **To republish without harvesting, use `bash run.sh --no-harvest`** - it skips the catalogue
  harvest, liveness AND the OSPO fetch; run `python3 fetch_ospos.py` first to refresh OSPOs.
  Three full runs in a day draw 429s from openCode and code.europa.eu.
- **Never edit `run.sh` or a page builder while `run.sh` runs** - it reads the script as it goes
  and builds from the working tree, so a half-made edit can publish.
- **Right after a deploy an old page or file can come back stale for a minute** (the home OSPO
  card read 49 for one fetch on 2026-10-09). Cache-bust (`?v=$(date +%s%N)`) and re-check.
- **This shell is zsh: `for c in "python3 x.py" ...; do $c; done` does NOT word-split** - every
  command "fails" silently. Wrap such loops in `bash -c '...'`.
- **The preview browser caches pages**: navigate with a fresh `?v=` before believing a screenshot.
  And use the preview's OWN tab id - one session loaded the preview into a tab the owner had
  open on GitLab. A computed colour may come back as `color(srgb …)`; convert through a canvas
  before computing contrast (a naive parse reported 3.80 for a real 4.62).
- **A check that greps an attribute can be satisfied by something else** - `data-type="corporate"`
  is on every corporate card, so removing the filter BUTTON passed. Sabotage each new check;
  and make the sabotage big enough to matter (a sixth-decimal change sat inside a tolerance).
- **Wikidata's query service**: truncates with HTTP 200, answers 429/503 after heavy use, and a
  query that scans every value of a property (P856) times out as 502 - look up exact IRIs.
  Multiple HQ values: take the PREFERRED rank; a Crunchbase id can map to a subsidiary's item.
- **`geo/build_geo.py` re-stamps `catalogue_shapes.json`'s date even when nothing changed** -
  `git checkout` it if the diff is the date alone (the Natural Earth input's sha256 is recorded).
- **A new OSPO upstream has no map location until `ospos/locations.json` gets it** (keyed by the
  id `fetch_ospos.py` derives). A new FLOSS-PSO office makes that list REFUSE (contract) until
  placed; a new academic or corporate one is listed and named as not on the map.
- **The stat-row CSS in `_ui_template.py` is shared by every page** (the others import its
  `PAGE_CSS`); home-only rules live in `HOME_CSS`. Each stat row carries `.six`/`.five` (12d).
- **English in a foreign slot is fixed with a `tr_*.json` row, never by loosening detection.**
- **Test end to end on a scratch copy, never by hand in the repo** (`rsync --exclude .git
  --exclude site`, then `harvest.py --from-cache` .. `variants.py`), and **compare like for like**
  - a baseline run of the same stages: skipping `enrich_desc`/`crosswalk` shifts other entries.
- **Translation keys hash the RAW text; look rows up by TEXT, not by name** (OS2 has one
  `.github` per org).
- **`/catalogs` can warn about missing page translations one run late** - it reads the previous
  build's `out/i18n_missing.json`. Build twice locally before believing it.
- **Set-aside rows are never recorded in first-seen**, so a reinstated row arrives as Recently
  added (the 12 Helsingborg tools did, by choice).
- **The vendored design-token CSS mentions `govoss-catalog.vercel.app` in a comment** - upstream's;
  do not "fix" it. `PAGINATION-BUG.md` is about someone else's service.
- **`out/` and `site/` are gitignored** - a fresh checkout has neither; `test_built_pages.py`
  SKIPs until the pages are built.
- **Preview the real routing with launch config `site-worker`** (`wrangler dev --local` on `site/`).
- **Sabotage with `PYTHONDONTWRITEBYTECODE=1 python3 -B`**, and check the sabotage APPLIED.
  `grep` here is ugrep (no back-references). Quote sabotage heredocs (`<<'EOF'`).

## Session 2026-10-07 (late) -> 2026-10-09, in one screen

Shipped and live-checked: stale translation keys deleted; OSPO cards fold code links past three;
map pins with popups; one page header on every inner page (nav name as the only h1, number-free
one-line ledes); a new home (section cards, the catalogues as a scrolling strip, "Recently added
open source software"); the nav without Home; `/ospos.json` pinned as UNNYC's contract (CC0 for
govoss's own fields, `country_names`, a failed-fetch example); the OSPO Alliance credited and added
to `/resources` as govoss's own; 12 Helsingborg plugins reinstated (Hub `f88d3498` Done); corporate
OSPOs from the TODO Group landscape, placed from Wikidata; one world map. Mistakes: a test that
compared escaped with unescaped text; a check satisfied by card attributes; a placement script
that trusted the first of several Wikidata HQs; the preview loaded into the owner's own tab.

## Session 2026-10-07, in one screen

Shipped and live-checked: the reorganisation (Home + `/software` split from the catalog, Sources
-> `/catalogs`, API -> `/docs` as the top-right button, `/resources` from UN+NYC's OSPO resources
file, clean paths and 301s in `site-worker.js`); `/ospos` (FLOSS-PSO + SustainOSS academic map,
filters, a regional map, flags, Resources links); `run.sh --no-harvest`; the GitLab failed-fetch
guard after openCode published 86 short. Mistakes: a full re-run to republish drew the 429s that
`--no-harvest` now avoids; a Resources class reused `.rhead` (now pinned by a check).

---

## Starting the next session

> I'm continuing work on ~/Antigravity/govoss-catalog, a union catalogue of government
> open source software (live at https://govoss.cat, repo github.com/sarapis/govoss-catalog).
>
> Read `/Users/devin/Antigravity/govoss-catalog/CONTINUE.md` first - it has the state,
> what's waiting on me, the ranked next moves, and the traps. Read `ARCHIVE.md` only if a rule
> in `CLAUDE.md` is too terse to apply.
>
> Start with candidate 1 once the 2026-10-12 scheduled run has happened; if it has not, say
> so and ask.
>
> Do not write a handoff, continuation prompt, or session record unless I ask for
> `/handoff`. End your turn with what you did and what you recommend next.
