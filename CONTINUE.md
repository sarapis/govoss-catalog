# Open items

Where the work stands as of **2026-10-14**. `CLAUDE.md` (auto-loaded) is the rules; `ARCHIVE.md`
holds the reasoning, incidents and older session records. Neither is required reading beyond
what loads by itself.

**Live: 3,176 active entries · 3,884 rows · 20 catalogues · 169 OSPOs (2 unplaced).**
https://govoss.cat (Catalan at `/ca/`), MCP at https://mcp.govoss.cat, both on Cloudflare.
Pipeline `bash run.sh`, scheduled Mondays 07:00, publishes and commits itself.

## The one idea, if you remember nothing else

**Every failure sensor here started as a `print`, and the fix is never "add a warning": it is
"write it where the page already looks."** The instances are files `/catalogs` reads -
`cache/_fetched.json`, `summary.failed_at`, `out/taxonomy_unmapped.json`,
`out/translation_orphans.json`, `out/deploy_auth.txt`, `out/i18n_missing.json`,
`out/crosswalk_cache.json` - plus the refusals: `stage_guard.py` and the `/ospos.json` contract.
Corollaries: the total is rarely the trigger (use a delta); a missing measurement is not zero,
and not fresh either; if a guard cannot be made to fail, delete it. **2026-10-14 found a gap:**
`/status.json` reads `state: ok, problems: []` while 12 sources failed Monday - see Candidate 1/2.

## State - verified 2026-10-14, not recalled

```bash
git status --short && git log --oneline origin/main..HEAD   # clean, nothing unpushed
for t in test_*.py; do python3 $t; done                     # 13 suites, 935 checks, all pass
python3 -c "import json;d=json.load(open('cache/_fetched.json'));print({k:v['ok'] for k,v in d.items()})"
```

- `main` clean and pushed; last commit `e913f41` (a `--no-harvest` run, 2026-10-14 17:22Z,
  every step ok, deployed). `schedule/install.sh --diff`: the plist matches the template.
- **Monday 2026-10-12's scheduled run lost DNS partway** (`URLError [Errno 8] nodename nor
  servname`, from ~11:12Z). 9 sources refreshed (`ca fi ie nl nlreg pt se tw` + `liveness`, swept
  11:41Z: 3,532 ok, 27 dead, 40 archived, 58 unknown). **12 did not** and keep their last good
  checkpoint, `ok: false` in `cache/_fetched.json`: `be bg ch digg dpg fr hbg it muc os2` (from
  2026-10-07) and `de eu` (openCode, code.europa.eu - from **2026-10-05**). The guards held: OS2
  refused "0 repos vs 300". Crosswalk inputs (Comptoir, Wikidata) kept their 2026-10-05 copies.
- **All three OSPO lists are `ok: false` live** (fetch failed 2026-10-12T11:20:53Z; rows are the
  2026-10-09 copy). UNNYC refuses to refresh while `sources["floss-pso"].ok` is false, so **their
  copy is frozen since Monday**. `python3 fetch_ospos.py` (no harvest traffic) fixes it.
- `/ospos`: 169 offices (18 government, 33 academic, 118 corporate), 167 on the map; Cuemby and
  Intersect MBO unplaced on purpose (no verifiable office). `/ospos.json` passes its contract.
- The "Get project updates" signup is live on every page (footer) and home; it forwards to the
  Sarapis Payload CMS `campaign-signups` (`campaign: govoss`). **No real signup has been made yet.**
- First-seen: 3,554 ids, 3,074 `null` (baseline).

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
- **Two OUTSIDE consumers, both UNNYC**: `/catalogues.geo.json` and `/ospos.json` (contract in
  `ospo_contract.py`, pinned). Change either only together with them.
- **`ospos/locations.json` is hand-curated truth.** `place_from_wikidata.py` only ADDS ids; a
  wrong Wikidata HQ is corrected by hand with `via: "hand, <date>"` (six were, from SEC filings).
- **An office's software count, its card button and `/software?ospo=<id>` are ONE rule**,
  `build_ospos.office_indices()`; `build_ui` maps its catalog positions onto DATA's name-sorted
  rows through `_ROW_POS`. Pinned by `test_built_pages.py` (it compares ENTRIES, not positions).
- **Signups go to Payload `campaign-signups`, never a separate store** (owner, 2026-10-14, to
  align with un.opensource.nyc; the Airtable CRM path was built, never published, removed).
  Honeypot never forwarded, campaign `govoss`: `test_workers.py`.

## Waiting on a human - not work that was skipped

- **Delete the junk Payload row I created**: `campaign-signups` id 4, `a!b@example.org`, campaign
  `govoss`, source `/probe` (a probe Payload accepted; anonymous access cannot delete). Not
  verified deleted - anonymous reads are 403.
- **One real signup** with the owner's own address, then check the row in the Payload admin
  (Submissions › Campaign Signups) - the only part of the signup path not verified live.
- **Sending updates**: manual from the Payload admin, as for UNNYC. No confirmation email, no
  unsubscribe link, no rate limit (CMS review finding M6) on any Sarapis list; the shared
  subscriber service is Databook `docs/REVIEW-APP-SCOPE.md` §6.5, deferred. The owner's call.
- **PR [sarapis/govoss-catalog#2](https://github.com/sarapis/govoss-catalog/pull/2)** (Olivia,
  "facet counts reflect the other active filters", 1 file): branched from `83f8b23`, before the
  Product-category fold, credits and signup commits. Merges cleanly in git; NOT reviewed against
  `fnFold()`, which hides facet buttons by index.
- **A legal glance at the one-line OSPO credits** (sources + licences + logo notice; the rest
  under "More info"): reflects the usual reading of CC0/MIT/Apache-2.0/ISC, not legal advice.
- **A Catalan speaker's read of `/ca/`** - added since: the signup copy, the OSPO credits line,
  "Agrupa per país", "Mostra les 17". No Catalan phase 2 (owner, 2026-09-23); data stays English.
- **UK scope** - government forge orgs are in scope (owner, 2026-10-08); Hub `dc3de350` parked the
  UK (215 government GitHub orgs, 14,320 repos, ~4.7x the catalogue). The owner's call.
- **The Resources data has no licence statement** (`resources/ospo-resources.json`, by UN+NYC).
- **Delete the OLD MCP Worker** `govoss-mcp.devin-31f.workers.dev` (itspruvn.com account, which
  the deploy token cannot reach). Nothing points at it.
- **Four licence calls left open**: Graylog (SSPL), MongoDB and PDFgear (SILL says unknown; both
  closed in fact), three publiccode-tier NC entries the publiccode exemption protects.
- **Screen-reader testing** has never been done - needs a person with a screen reader.
- **The demand-side go/no-go** (`DEMAND-SIDE-CATALOGUE.md`) and drafted, unsent documents.
- **Sarapis CRM (Airtable)**: 9 NYC OSPO organisations + 5 people added 2026-10-09 (Owner and
  Follow-up left blank); Mike Nolan (UNDP) linked. Nothing pending unless the owner wants follow-up.
- **Cleanup**: remote branch `ospos-atlas` (merged into `main`), and the local worktree
  `../govoss-merge-preview` with local branches `ospos-atlas-fixes`, `preview/ospos-atlas-merge`.

## Candidates, ranked

1. **Recover from Monday's DNS failure.** `python3 fetch_ospos.py` first (unfreezes UNNYC, no
   harvest traffic), then ONE full `bash run.sh` to refresh the 12 stale sources - `de`/`eu` are
   9 days old. Why now: UNNYC is frozen and the next scheduled run is 2026-10-19. One full run
   is safe; three in a day draw 429s from openCode and code.europa.eu.
2. **Make a failed harvest survive a rebuild in `/status.json`.** Today `last_run` is whatever ran
   last, so any `--no-harvest` publish after a failed Monday reports `ok, []`. Report sources whose
   last attempt failed (`ok: false` in `_fetched.json`, and the OSPO lists') in `problems`, from
   the files, not from the last run. Why now: it hid Monday's failure through six publishes.
3. **Review PR #2** against the fold (Waiting on a human has the risk).
4. **Why did DNS fail at 07:00?** Check whether the Mac was waking (`pmset -g log`). If so, a
   retry of failed sources later in the run, or a later launchd slot, before changing anything.
5. **OSPO "ownership" field for academic offices** (public/private/intergovernmental) - asked as
   optional by UNNYC; needs each office verified (CERN is intergovernmental).

## Traps - looks broken but is not, and vice versa

- **`/status.json` `state: ok` does not mean the last HARVEST worked** (Candidate 2). Read
  `cache/_fetched.json` `ok` per source, and `/ospos.json` `sources[*].ok`.
- **`www.govoss.cat` and `govoss.cat` are different Workers.** `run.sh` never redeploys
  `govoss-www` or `mcp-server`; redeploy those by hand, only when their code changes.
- **To republish without harvesting, use `bash run.sh --no-harvest`** - it skips the catalogue
  harvest, liveness AND the OSPO fetch; run `python3 fetch_ospos.py` first to refresh OSPOs.
- **Never edit `run.sh` or a page builder while `run.sh` runs** - it builds from the working tree.
- **Right after a deploy an old file can come back stale for a minute.** Cache-bust
  (`?v=$(date +%s%N)`) and re-check.
- **This shell is zsh: `for c in "python3 x.py" ...; do $c; done` does NOT word-split.** Wrap
  such loops in `bash -c '...'`.
- **The preview browser caches pages, and a HIDDEN pane throttles timers and never runs
  `requestAnimationFrame`.** Navigate with a fresh `?v=`; debounce layout work with `setTimeout`,
  not rAF (the tag clamp kept a stale "+N" until it was); a screenshot may show pre-script state.
- **`python3 -m http.server` (launch config `site`) does not map clean paths** - `/software` 404s
  there; open `software.html`, or use `site-worker` (`wrangler dev`) for real routing.
- **Probe Payload ONLY with an obviously invalid address** ("not-an-email" -> 400). It ACCEPTED
  `a!b@example.org` and created row 4; anonymous access cannot delete it.
- **Payload `campaign-signups` allows duplicate emails** and anonymous reads are 403, so govoss
  cannot dedupe; duplicates are expected and harmless.
- **Markers resolve BEFORE placeholders.** HTML carrying `⟪…⟫` put in through a `__X__`
  placeholder stays untranslated; insert it before `i18n.markers` (home uses an `<!--SIGNUP-->`
  token for this).
- **A CSS escape inside a Python string is a Python escape first**: `content:"\2192"` shipped as
  a control character + "92". Write `"\\2192"`; `test_built_pages.py` now rejects control chars.
- **The "no class the shared styles use" check reads CSS comments too** - writing `theme.py's
  .wrap` in a comment tripped it on `.py` and `.wrap`.
- **Worker code must log with `console.error`**: the `test_workers.py` harness parses stdout as
  JSON, and one `console.log` broke every check.
- **A check that greps an attribute can be satisfied by something else.** Sabotage each new
  check, big enough to matter, with `PYTHONDONTWRITEBYTECODE=1 python3 -B`; check it APPLIED.
- **A test that compares two derived lists can pass with both wrong** - `/software?ospo=` was
  checked position-against-position while both used unsorted positions. Compare the THINGS.
- **Wikidata's query service** truncates with HTTP 200, answers 429/503 after heavy use, times
  out on full-property scans; take the PREFERRED-rank HQ; a Crunchbase id can map to a subsidiary.
- **`geo/build_geo.py` re-stamps `catalogue_shapes.json`'s date even when nothing changed** -
  `git checkout` it if the diff is the date alone.
- **A new FLOSS-PSO office makes that list REFUSE (contract) until placed** in
  `ospos/locations.json`; a new academic or corporate one is listed and named as not on the map.
- **The stat-row CSS in `_ui_template.py` is shared by every page**; home-only rules live in
  `HOME_CSS`. The home signup card reuses `.submit` (theme's Get involved card).
- **English in a foreign slot is fixed with a `tr_*.json` row, never by loosening detection.**
- **Test end to end on a scratch copy, never by hand in the repo**, and compare like for like.
- **Translation keys hash the RAW text; look rows up by TEXT, not by name.**
- **`/catalogs` can warn about missing page translations one run late** - build twice locally.
- **Set-aside rows are never recorded in first-seen**, so a reinstated row arrives as Recently added.
- **The vendored design-token CSS mentions `govoss-catalog.vercel.app` in a comment** - upstream's.
- **`out/`, `site/`, `catalogue*.html`, `home*.html` are gitignored** - a fresh checkout or a new
  worktree has none; `test_built_pages.py` SKIPs until the pages are built (copy them in).

## Session 2026-10-09 -> 2026-10-14, in one screen

Shipped and live-checked: UNNYC's two reports answered (unplaced rows allowed by source, stated
in the contract; the IPA "misname" was IPA's own 2026-06 rename - my override was reverted the
same hour); WalmartLabs/JiHu placed, six Wikidata HQs corrected; Olivia's OSPO Atlas (PR #1)
reviewed, extended and merged - Type first on Government, no country-following map, flat list
with Group by country, flag + country on cards, sort by software (no ranks), one link to
`/software?ospo=`, code profiles in a dialog, logo notice, two-row tag clamp, six categories then
Show all, no type colour, shared page gutters, a taller box, one-line credits + More info; the
"Get project updates" signup (footer + home, paired with Get involved) into Payload; NYC OSPO
contacts into the Sarapis CRM. Mistakes: a probe that created a CMS row; an Airtable store built
before checking the sister sites; `/software?ospo=` first shipped wrong positions (caught before
publish); a Monday harvest failure missed for two days because `/status.json` said ok.

## Session 2026-10-07 (late) -> 2026-10-09, in one screen

Shipped and live-checked: one page header on every inner page; a new home (section cards, the
catalogues strip, Recently added); the nav without Home; `/ospos.json` pinned as UNNYC's contract;
the OSPO Alliance credited; 12 Helsingborg plugins reinstated; corporate OSPOs from the TODO
landscape, placed from Wikidata; one world map. Mistakes: a test comparing escaped with
unescaped text; a check satisfied by card attributes; a placement script that trusted the first
of several Wikidata HQs; the preview loaded into the owner's own tab.

---

## Starting the next session

> I'm continuing work on ~/Antigravity/govoss-catalog, a union catalogue of government
> open source software (live at https://govoss.cat, repo github.com/sarapis/govoss-catalog).
>
> Read `/Users/devin/Antigravity/govoss-catalog/CONTINUE.md` first - it has the state,
> what's waiting on me, the ranked next moves, and the traps. Read `ARCHIVE.md` only if a rule
> in `CLAUDE.md` is too terse to apply.
>
> Start with candidate 1 (recover from Monday's DNS failure): tell me the plan and ask before
> the full `bash run.sh`, since it publishes.
>
> Do not write a handoff, continuation prompt, or session record unless I ask for
> `/handoff`. End your turn with what you did and what you recommend next.
