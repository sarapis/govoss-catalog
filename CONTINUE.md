# Open items

Where the work stands as of **2026-10-07 (late)**. `CLAUDE.md` (auto-loaded) is the rules;
`ARCHIVE.md` holds the reasoning, incidents and older session records. Neither is required
reading beyond what loads by itself.

**Live: 3,163 active entries · 3,883 rows · 20 catalogues · 16 countries and bodies.**
https://govoss.cat (Catalan at `/ca/`), MCP at https://mcp.govoss.cat, both on Cloudflare.
Pipeline `bash run.sh`, scheduled Mondays 07:00, publishes and commits itself.

## The one idea, if you remember nothing else

**Every failure sensor here started as a `print`, and the fix is never "add a warning":
it is "write it where the page already looks."** The instances are files `/sources.html`
reads - `cache/_fetched.json`, `summary.failed_at`, `out/taxonomy_unmapped.json`,
`out/translation_orphans.json`, `out/deploy_auth.txt`, `out/i18n_missing.json`,
`out/crosswalk_cache.json` - plus `stage_guard.py`, the same idea one step further: a stage
that DESTROYS data refuses instead of reporting. Corollaries: the total is rarely the
trigger (use a delta); a missing measurement is not zero, and not fresh either; if a guard
cannot be made to fail, delete it.

## State - verified 2026-10-07, not recalled

```bash
git status --short && git log --oneline origin/main..HEAD   # clean, nothing unpushed
for t in test_*.py; do python3 $t; done                     # 13 suites, 727 checks
curl -s "https://govoss.cat/status.json?v=$(date +%s)"       # live state + problems
```

- Tree clean on `main`, nothing unpushed, one worktree, no jobs or preview servers running.
  Schedule loaded; `bash schedule/install.sh --diff` says the plist matches the template.
- **Last run 2026-10-07 20:19Z, `--no-harvest` (trigger `rebuild`)**, 20 steps ok, deployed on
  `token-file`, recorded (`8baa50d`). Live-checked: every page of the reorganisation and
  `/ospos` (49 cards, 46 dots, 49 flags, Munich/Paris/CMS Resources links), the old-name and
  shared-search 301s, `/status.json` `ok`. Last HARVEST: 2026-10-07 19:50Z (`87b8143`).
- **openCode and code.europa.eu are on their 2026-10-05 data**: both answered 429 to the
  day's third harvest and the guard kept their last good lists. `cache/_fetched.json` was
  corrected by hand to say so (the short 19:03 run had stamped them fresh) - that correction
  is committed but reaches `/catalogs` only on the next build. Monday's run should refresh both.
- Liveness (2026-10-07 19:43Z): 3,530 ok of 3,619, 27 dead, 40 archived, 59 unknown.
  `replaces.json` 348 keys; 444 products, 379 with an alternative (live-checked).
  Variants: 14 linked to 12 cores. MCP Worker `fd7a287d` (search `n d o a u rp`; docs `/docs`).
- Site map: Home `/`, `/software`, `/catalogs`, `/ospos`, `/resources` in the nav; `/docs` is the
  top-right button; `/products` has no nav item (owner). `/ca/` copies of all.

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
  `dedupe.merge()` now backfills a sibling's real repo so a repo-less survivor keeps its
  identity (Mautic, ckan; `test_dedupe_identity.py`).
- **Network enters crosswalk only through `run()`'s `*_fn` arguments** (`test_crosswalk_run.py`).
- **A failed fetch is never "no data"**: `gitlab_scan()` counts non-404 failures and refuses a
  short list (`test_harvest_get.py`); `fetch_ospos.py` keeps a failed or halved list's last good
  copy (`test_ospos.py`). The catch-all that read failures as "none" published 86 short.
- **`/catalogues.geo.json` has an outside consumer**: un.opensource.nyc
  (`~/Antigravity/unnyc/scripts/fetch-govoss-catalogues.mjs`, PR #109) STOPS if a top-level
  key is missing (`about generated_at licence source trimmed not_drawn features`), a feature
  `kind` is not `country/union/city`, a licence string changes, or `generated_at` differs
  from `meta.json`'s. Only the last is pinned here (check 12c) - change the rest only
  together with that script.

## Waiting on a human - not work that was skipped

- **Helsingborg's 103 WordPress plugins: decide** (Hub `f88d3498`, Idea). Review: `HELSINGBORG-PLUGINS-REVIEW.md`.
  73 are at stake (30 have no description and stay out regardless); 13 municipal tools, 16
  Municipio modules, 44 plumbing; three options. Nothing in `filters.py` changed.
- **The Resources data has no licence statement** (`resources/ospo-resources.json`, compiled by
  UN+NYC). `/resources` credits UN+NYC and states none; give one and it goes on the page and in
  `/resources.json`. Replacing the file is also how it updates - nothing fetches it.
- **Delete the OLD MCP Worker** `govoss-mcp.devin-31f.workers.dev` - in the itspruvn.com
  Cloudflare account, which the deploy token cannot reach. Nothing points at it.
- **Four licence calls left open** (`filters.py` flags only what the source's licence
  string says): Graylog (SSPL, genuinely not OSI), MongoDB and PDFgear (SILL says unknown;
  both closed in fact), three publiccode-tier NC entries the publiccode exemption protects.
- **A Catalan speaker's read of `/ca/`**. No Catalan phase 2 (owner, 2026-09-23): data,
  products and source notes stay English. Do not re-propose it.
- **Screen-reader testing** has never been done - needs a person with a screen reader.
- **The demand-side go/no-go** (`DEMAND-SIDE-CATALOGUE.md`) and three drafted, unsent
  documents (an OFE reply and defect report - not committed - and
  `DEMAND-SIDE-CALL-FOR-SOURCES.md`).
- UK: a curated list of 40 is parked (`UK-CURATED-DRAFT.md`, Hub `dc3de350` Backburner).
  Scope rule: government-produced catalogues only, never a list govoss curates.

## Candidates, ranked

1. **Check Monday's 2026-10-12 scheduled run** - the first unattended run with `ospos fetch`, the
   GitLab failure guard and the reorganised pages: openCode ~478 active again (not 392),
   code.europa.eu ~14, both stamped fresh on `/catalogs`; the harvest log says "18" and "31"
   OSPOs; `/status.json` `ok`; Recently added only genuinely new ids.
2. **Tell UNNYC** their resources page could read `/ospos.json` (same FLOSS-PSO list, plus the
   academic offices and govoss's placements) instead of keeping its own copy - their repo.
3. **Act on the Helsingborg decision** once made - an allow-list of repo URLs in `filters.py`
   pinned in `test_filters.py` (never a name pattern); stamp returned ids `null` in
   `_first_seen.json` if the owner does not want a week of Helsingborg in the strip.
4. **Stale translation keys**: 3 in `tr_de.json`, 1 in `tr_it1.json` (TLSAssistant now ships
   English). Harmless (the sensor triggers on GROWTH); delete only with the owner's nod.

## Traps - looks broken but is not, and vice versa

- **`www.govoss.cat` and `govoss.cat` are different Workers.** `run.sh` never redeploys
  `govoss-www` or `mcp-server`; redeploy those by hand, only when their code changes.
- **To republish without harvesting, use `bash run.sh --no-harvest`** (verified 2026-10-07:
  harvest from cache in 0s, liveness and the OSPO fetch skipped). Three full runs in a day drew
  429s from openCode and code.europa.eu. It logs trigger `rebuild` and resets the "last run"
  age on /catalogs; per-source ages and the liveness date stay true.
- **A new OSPO upstream has no map location until `ospos/locations.json` gets it** (keyed by
  the id `fetch_ospos.py` derives from its URL). It is still listed; /ospos names it as not on
  the map. Place it at its city (seat) or its organisation's headquarters (hq).
- **Never edit `run.sh` itself while it runs** - bash reads the script as it executes.
- **Do not edit page builders while `run.sh` runs** - it builds from the working tree, so a
  half-made edit can publish. Wait for the run to finish.
- **Right after a deploy, a NEW file can 404 for a minute** (`/catalogues.geo.json` did) and
  an old page can come back stale. Cache-bust (`?v=$(date +%s%N)`) and re-check before
  calling anything broken.
- **The stat-row CSS in `_ui_template.py` is shared by every page** (the others import its
  `PAGE_CSS`). A catalog-only change gave `/sources.html` an empty grey cell; each row now
  carries `.six`/`.five` for its tile count (check 12d).
- **English in a foreign slot is fixed with a `tr_*.json` row, never by loosening
  detection.** code.overheid.nl's prior needs two English markers ("Repo for project MijND"
  has none); a publiccode.yml `de` key holding English is the publisher's claim.
- **The old `govoss-catalog.vercel.app` redirect has no CORS header** - scripts follow it,
  browser cross-origin fetches fail. The `www` redirect DOES carry CORS (`test_workers.py`).
- **Wikidata's query service truncates with HTTP 200** and answers 429/503 after heavy
  same-day use. The crosswalk falls back and reports; not a regression.
- **Test end to end on a scratch copy, never by hand in the repo.** `rsync --exclude .git
  --exclude site` to the scratchpad, then `harvest.py --from-cache` .. `variants.py`.
  `first_seen.py`, `liveness.py`, `record` and every by-hand stage rewrite committed files.
- **Compare stages like-for-like** (a `git archive HEAD` baseline run to the same stage).
  A `--from-cache` rebuild skips `enrich_desc.py`, so it reports 6 translation orphans where a
  live run reports 3 - the extra 3 (`tr_fise.json`) are that mode, not rot.
- **`detect_lang` tags English-with-one-foreign-word as foreign under that org's hint**
  ("Custom API Endpoint for Lärrum") - accepted and pinned: visible in the queue beats hidden.
- **Translation keys hash the RAW text; look rows up by TEXT, not by name.** OS2 has one
  `.github` per org - a name lookup keyed a translation to the wrong repo.
- **`/catalogs` can warn about missing page translations one run late** - it reads the
  previous build's `out/i18n_missing.json`. Build twice locally before believing it.
- **3,074 of 3,540 first-seen ids are `null`** - the baseline, known and never new.
  Set-aside rows are never recorded, so a reinstated row arrives as Recently added.
- **Munich's SDS Calculator links to itself under two catalogues** via `isBasedOn`. Harmless.
- **The vendored design-token CSS mentions `govoss-catalog.vercel.app` in a comment.**
  Copied from upstream as-is; do not "fix" it here.
- **`out/` and `site/` are gitignored** - a fresh checkout has neither; `test_built_pages.py`
  SKIPs until the pages are built.
- **Preview the real routing with launch config `site-worker`** (`wrangler dev --local` on
  `site/`): clean paths and 301s only exist in the Worker; the plain `site` config cannot show them.
- **The browser pane returns stale and blank frames.** `computer {action:"zoom"}` returns a
  fresh full frame when `screenshot` shows a blank band; measure with `javascript_tool`.
- **`PAGINATION-BUG.md` is about someone else's service**, not a defect here.
- **Sabotage with `PYTHONDONTWRITEBYTECODE=1 python3 -B`**, and check the sabotage APPLIED.
  `grep` here is ugrep: back-references like `\1` error out, so a result filter can print
  nothing and look like a pass - read each suite's last line instead. Quote sabotage heredocs
  (`<<'EOF'`): an unquoted one ran `$(...)` inside a regex and the sabotage never applied.

## Session 2026-10-07, in one screen

Shipped and live-checked: the reorganisation (Home + `/software` split from the catalog, Sources
-> `/catalogs`, API -> `/docs` as the top-right button, `/resources` from UN+NYC's OSPO resources
file, clean paths and 301s in `site-worker.js`, the nav wrapping up to 900px); `/ospos` (FLOSS-PSO
+ SustainOSS academic map, Government/Academic and country filters, a North America + Europe
map, flags, Resources links); `run.sh --no-harvest`; the GitLab failed-fetch guard after openCode
published 86 short. Mistakes: a full re-run to republish restored checkpoints drew the 429s that
`--no-harvest` now avoids; a Resources class reused `.rhead` (now pinned by a check).

## Session 2026-09-23 (late) -> 29, in one screen

Shipped and live-checked unless marked: the deploy token (F7 closed; first scheduled
Cloudflare deploy on `token-file`); tests count checks instead of hard-coding (four totals
were wrong, one a phantom pass); +58 `replaces.json` rows / 36 products; dedupe repo
backfill (Mautic, ckan); MCP search reads repo URLs; catalog URLs carry the whole view
(`?q=&fn=&cc=...`); stats above Recently added, "Find a filter..."; the `/sources.html` map
as the Map view of Harvested catalogues, plus `/catalogues.geo.json` (UNNYC now reads it);
stat rows never leave a grey cell. Not live yet: five translations, the GeoJSON timestamp
fix (found during handoff: the two stamps matched only by luck). Written, undecided: the
Helsingborg review.

---

## Starting the next session

> I'm continuing work on ~/Antigravity/govoss-catalog, a union catalogue of government
> open source software (live at https://govoss.cat, repo github.com/sarapis/govoss-catalog).
>
> Read `/Users/devin/Antigravity/govoss-catalog/CONTINUE.md` first - it has the state,
> what's waiting on me, the ranked next moves, and the traps. Read
> `/Users/devin/Antigravity/govoss-catalog/HELSINGBORG-PLUGINS-REVIEW.md` only if I have
> decided on the plugins, and `ARCHIVE.md` only if a rule in `CLAUDE.md` is too terse to apply.
>
> Start with candidate 1 once the 2026-10-12 scheduled run has happened; if it has not, say
> so and ask.
>
> Do not write a handoff, continuation prompt, or session record unless I ask for
> `/handoff`. End your turn with what you did and what you recommend next.
