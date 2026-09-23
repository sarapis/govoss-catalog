# govoss-catalog

> Union catalogue of **government open source software**, harvested first-hand from 19
> national, municipal and international catalogues, normalised onto one schema, translated,
> categorised by function, de-duplicated, linked to variants and liveness-monitored.
> **3,054 active entries · 19 catalogues · 16 countries and bodies.** Live at
> https://govoss.cat (Catalan at `/ca/`), MCP at https://mcp.govoss.cat.

This file is RULES ONLY - it loads into every session, budget 300 lines. The reasoning,
numbers and incidents behind each rule are in `ARCHIVE.md` › "The long-form operating
manual, as of 2026-09-23". Open items and traps: `CONTINUE.md`.

## Commands

```
bash run.sh                        # full pipeline, ~20 min: harvest -> ... -> deploy -> record
python3 harvest.py --from-cache    # rebuild catalog.json from checkpoints, no network
python3 harvest.py ch digg         # re-harvest named sources (checkpoint keys)
python3 liveness.py                # monitor only, ~5 min
for t in test_*.py; do python3 $t; done     # 11 suites, 506 checks, all manual
```

Scheduled **Mondays 07:00** (`bash schedule/install.sh`; log `~/Library/Logs/govoss-harvest.log`).
**The template in `schedule/` is the source of truth**; never edit the installed plist -
`install.sh --diff` shows drift. The run order is load-bearing and documented at the top of
`run.sh`; run the script, not the steps from memory. **The run publishes and commits itself.**

## Sources

- **`sources.py` is the single source of truth** for labels, links, routes, `SITE_URL`, country
  names and the survey of rejected catalogues; `/sources.html` + `/sources.json` render it.
- **Scope: catalogues a government produces (or a government body's own forge org). Never a
  list govoss curates itself** (owner, 2026-09-23; the parked UK list is `UK-CURATED-DRAFT.md`).
- **The pattern: find the machine route the catalogue's own site is built from, and read that.**
  Never scrape a rendered page. Every source here was found that way.
- **Checkpoint keys (`os2`, `ch`) are not `sources.py` keys (`DK/os2`, `CH/swiss`).** Look
  `_fetched.json`/`_timing.json` up by checkpoint key or everything silently matches nothing.
- Per-source traps, one line each (detail in the archive):
  - SILL: use `code.gouv.fr/sill/api/sill.json`, never `/data/sill.json` (no url field).
  - openCode: the GitLab API reproduces the directory; use `web_url`, never a constructed link.
  - NL: `code.overheid.nl` is open Forgejo, no key. The OSS register (`nlreg`) still needs one.
  - Canada: every field is an `{en, fr}` dict - `loc()` flattens; tags go to `keywords`.
  - Sweden: the recutils `Url` field mixes repos and homepages; `is_repo_url()` (explicit forge
    hosts, owner AND repo in the path) decides, and everything else is `landing`.
  - Taiwan: use the official open-data export, not the SPA's POST API.
  - Helsingborg: the org scan reads each repo's `composer.json` (`composer=True`); a declared
    `wordpress-plugin`/`wordpress-muplugin` is set aside by filters.py. Themes stay - Municipio IS one.
  - DPG: repo URLs are free text; extras go to `extra_repos`. Deep links are HEAD-verified.
  - Switzerland: the Chancellery's `swiss/index` README is the org list; publiccode tier only;
    four accounts are users (list with `/users/<x>/repos`). Refuses under 20 accounts.
  - Refused on purpose: Spain CTT and the Adullact forge (bot challenges - never bypass),
    code.gov (retired), oss.kr (wrong shape), the EU aggregate catalogue (broken pager, wrong
    layer - `PAGINATION-BUG.md`), UNODC "open-source registries" (OSINT, a false lead).
- **Harvest exits 0 on a failed source, deliberately**; the failed source reuses its
  checkpoint. Visibility is `cache/_fetched.json` (advances ONLY on success) and its age on
  `/sources.html`. `--from-cache` must never write `_fetched.json` or `_timing.json`.
- **Multi-org adapters (`os2`, `ch`) share `_refuse_short_scan()`**: raise when sub-sources
  failed AND the result shrank, so a partial scan never overwrites a good checkpoint.
- `github_org_scan` authenticates via `liveness.gh_token()`; `GITHUB_TOKEN` is not in the plist.

## Identity, dedupe, variants

- **Dedupe merges on Wikidata QID, then normalised repo URL, then exact name AND exact
  homepage together. Never on name similarity** (Angular `Q28925578` ≠ AngularJS `Q2849803`).
  Pinned by `test_dedupe_identity.py`. Survivor selection uses namespace containment.
- **Crosswalk stamps QIDs from Wikidata BY URL ONLY and from Comptoir du Libre** (repo ->
  SILL id -> website -> exact name). Matched item must BE software; a homepage shared by
  differently-named entries is an organisation. Records `wikidata_via`. Never fails a step.
  Third route, `redirect_matches()`: LENDS an existing QID to a same-name row in another
  catalogue only when both homepages end, after redirects, at the IDENTICAL page (path included).
  Fourth, `repo_rename_matches()`: the same when GitHub resolves both repos to ONE repository
  (a rename or transfer). Both share `_lend()`'s guards and skip pairs already equal.
  **Its inputs refresh after 6 days** (`out/crosswalk_cache.json`; no stamp = stale; the stamp
  moves only on success; a failure keeps the old copy). `/sources.html` warns past 14 days.
  Websites are asked per homepage (an asked set, so new ones are sent); repos come from the full
  P1324 dump, accepted ONLY when its rows match a COUNT - the service truncates with HTTP 200.
  A software-check batch that fails twice is UNVERIFIED: not stamped, never trusted, never fatal.
- **`taxonomy.py` and `dedupe.py` REFUSE already-merged input** (`stage_guard.py`, pinned by
  `test_stage_guard.py`). Do not make them merge-aware or add `--force`; rebuild with
  `--from-cache`. To verify a change, dry-run the pure function, not a by-hand re-run.
- **Variants (`variants.py`, after dedupe) link, never merge**: `variant_of` from, in order,
  `variants.json` (curated, keyed on REPO URL, can veto), publiccode `isBasedOn`, and forge
  fork parents. Rules, each pinned by `test_variants.py`: resolves only to an active entry by
  repo URL; never to a `library` core; never from an `addon`/`configurationFiles` entry; never a
  homepage; chains to the root; a fork counts only across DIFFERENT catalogues (a qualifying
  `upstream-fork` is reinstated, `reinstated_as_variant` kept, and undone first every run).
- A variant with no mapping inherits its core's `replaces` (`inherited_from`), kept OUT of
  `by-product.json`. The page FOLDS a variant under its core only when both are in the results.
- `catalogue_count` counts listings of the SAME software; `variant_count` counts versions.
  Different claims, different pills. **Do not reinstate an endorsement ("Recommended") stamp**
  without first splitting SILL's asserted claim from Munich's inferred one.

## Language and translation

- `translations/tr_*.json` map `sha1(raw short_desc)[:10]` -> English. **Hash the RAW text,
  never stripped.** Files are hand-maintained with MIXED indentation - preserve each one's.
- **Read `desc_lang` (what is displayed), never `desc_src_lang`.**
- **Never a per-source language assumption, and never bare `detect_lang` in its place** (it
  answers `en` whenever it finds no stopwords, and short catalogue phrases have none). SILL and
  code.overheid.nl use `lang_with_prior()`; Munich and DPG use `lang_assume_en()`; forges use
  `detect_lang(text, hint=)`: the hint breaks ties, AND decides when the text carries one marker
  for it that is not an English homograph ("Ett childtema för Municipio" is Swedish). `ä`/`ö` count for de, sv AND fi;
  Finnish `se` never matches after `. - /`. **Over-correcting toward English is the worse
  failure.** All pinned by `test_detect_lang.py` (59 real strings).
- Entries with no description are set aside (`no-description`), not deleted.
- Orphaned keys -> `out/translation_orphans.json`; the trigger is GROWTH, and a missing
  previous figure is not zero. `merge_translations.py` WARNS on merged input (count misleads).
  Pinned by `test_translation_orphans.py`.

## Categorisation

`taxonomy.py` maps source values onto 19 functions, explicitly, never fuzzily. **An unmapped
value is a bug**, surfaced in `out/taxonomy_unmapped.json` and on `/sources.html`. Three
outcomes: map it, fix it, or map it to `None` (audience/artefact labels like `government`,
placeholders like `<TBD>`) so text inference runs. Before calling a value hard, check whether
the entry is already classified by another value, and check for a sibling spelling family.
`out/` artefacts are per-run: a fixed mapping clears the page on the NEXT run.

## Liveness

`liveness.py` reports the DELTA. `403/429/5xx` are unknown, never dead; two consecutive dead
observations before a verdict; every dead verdict confirmed by a plain web HEAD of the
ORIGINAL url. Always exits 0; a crash leaves `summary.checked` standing (last good sweep).
State machine pinned by `test_liveness_strikes.py`.

## Filters

`filters.py` FLAGS, never deletes (`excluded` + `exclude_reason`). Anything with a
`publiccode.yml` is never filtered. `fork: true` is evidence; names are not. Two rules were
removed after they caught real products (`Products.PloneMeeting`, a `-german` build) - do not
re-add them. Pinned by `test_filters.py`. Licence rules read the SOURCE'S claim (`closed-licence`,
`non-commercial-licence`); never flag SSPL/Elastic (stale for Elasticsearch, now AGPL) or an
unknown (`N/A`, `Je ne sais pas`) - unknown is not closed.

## Export, replaces, products

- Static files in `site/`, no backend. `/entries.json` carries EVERY row, set-aside ones
  flagged. `/by-product.json` is the precomputed "what replaces X" endpoint. Schema 1.2.0.
- **`replaces.json` is hand-curated; `export_json.py` FAILS on a bad `confidence`/`kind`**
  (pinned by `test_filters.py`) and warns on keys matching no entry. Matching UNIONS the
  survivor name and every `also_known_as`. Check existing product names before adding
  ("Dropbox Business" beside "Dropbox" splits one product); a `paid-tier` row must be keyed on
  the software the paid edition is built from. Every mapped product needs a
  `proprietary.json` record or `build_products.py` fails. **Key a mapping on something that
  matches ONE entry** - bare "Docs" and "Consul" each matched unrelated software.
- A publisher's own `replaces:` in publiccode.yml is read (`via: publiccode`), bad vocabulary
  DROPPED not fatal (it is their file), unknown products kept off `by-product.json` and the page.
- **Committed JSON is deterministic**: `sort_keys=True` + the total `stable_order()`, never a
  per-run value stored per record (that once made a 47,563-line diff).

## Publishing and hosting

- **Cloudflare since 2026-09-23** (it was Vercel). The site is the `govoss-site` Worker
  (`wrangler.site.jsonc`, assets from `site/`) at `govoss.cat`; `www` is the `govoss-www`
  redirect Worker (301, query kept, CORS on the redirect); MCP is `mcp-server/` at
  `mcp.govoss.cat`. All in Devin@sarapis.org's Account, **`account_id` pinned in every
  wrangler config** - a cached login for another account once took a deploy.
- **`deploy` is gated on `out/steps.tsv`**: any failed step and nothing publishes. **`record`**
  commits `catalog.json`, `history.json`, `liveness.json`, `cache/` with an explicit path list,
  only on `main`, never force-pushes, same gate.
- `publish()` resolves wrangler AND node itself (a node-script CLI under launchd's PATH reads
  as an auth failure when it is not). Verify with `publish()` under `env -i PATH=<plist PATH>`.
- **Deploy auth is REPORTED (F7)**: token env -> `~/.config/govoss/cloudflare-token` -> stored
  login, recorded to `out/deploy_auth.txt` -> `history.json`; `/sources.html` warns while it is
  `stored-login`. `None` is not `stored-login`. The pre-flight checks whoami CONTENT for the
  pinned account id, and is non-fatal.
- Headers/redirects: `deploy-cloudflare/_headers` + `_redirects`, copied by `build_site.sh`.
  **`html_handling` is `"none"`** so `/sources.html` is served as-is (the default 307s it);
  `site-worker.js` restores `/`, `/ca/` and `/ca`->`/ca/`, running only when no asset matches.
  Pinned by `test_built_pages.py` check 13.
- A Worker custom domain needs the hostname FREE of DNS records (error 100117). Only one
  config may claim a hostname (checked for `www`).
- `govoss-catalog.vercel.app` 308s every path to govoss.cat (`deploy-vercel.json` is that whole
  last deploy); a browser cross-origin fetch of the OLD JSON fails (no CORS on Vercel redirects).
- **`sources.py:SITE_URL` is the one place the address is written.** Flip it only once the new
  address answers.

## The pages

- Four pages x two languages: `/`, `/sources.html`, `/api.html`, `/products.html`, and each
  under `/ca/`. `build_ui.py` + `_ui_template.py`, `build_sources.py`, `build_api.py`,
  `build_products.py`; chrome in `theme.py`. `/status.html` 308s to `/sources.html`, but
  `/status.json` is still written - retiring an endpoint breaks agents.
- **No f-strings for markup**: plain strings with `__PLACEHOLDER__` tokens, asserted none survive.
- Tokens are VENDORED (`vendor/wegovnyc/`), `theme.py` is an alias layer onto `--wg-*` mapped by
  ROLE and MEASURED contrast; `assert_variant_live()` checks the ROOT tag. Fonts self-hosted.
- **Language copies (`i18n.py`, `i18n/ca.json`)**: phase 1 translates chrome only; data and the
  API contract stay English. Keys are the English text. Templates mark `⟪…⟫`, or `⟪js:…⟫` in a
  JS string (escapes apostrophes to `\uXXXX`); Python strings use `i18n.t(lang, msg, **kw)` with
  NAMED args. **Order: markers -> placeholders -> links.** A missing translation falls back to
  English and lands in `out/i18n_missing.json` (warned on); mismatched placeholders fail the
  build. Pinned by `test_built_pages.py` check 12 (incl. `node --check` of each copy's script).
- UI rules that cost a bug each (pinned where static checks can reach, in `test_built_pages.py`):
  - `el.hidden` works only because `theme.py` ships `[hidden]{display:none!important}`; never
    `style.display`. Checking `el.hidden` is not checking it is hidden - assert computed display.
  - Measure rows by vertical CENTRE, not `top`. Check a class name is free before using it.
  - Toolbar is one row above 940px by `nowrap` + `min-width:0`; `#sort` never shrinks; licence
    and source share the squeeze on equal bases. Caps are sized for the widest language -
    re-measure (1024px is the tightest column) when adding one.
  - `.side` is sticky WITH a max-height; `current()` routes every facet key explicitly.
  - `?src=`/`?cc=`/`?rp=` values are validated and an unknown one IGNORED, never filtered to
    nothing. Source country shows names; the facet value stays the code.
  - Never name a JS variable after an element `id` (ids are globals).
  - `catalogue.html` is pure ASCII; entities are not decoded inside `<script>`.
- **Recently added**: `cache/_first_seen.json`, where `null` means BASELINE (never new) and a
  missing id is unseen. `build_ui._fs_ident()` must equal `first_seen.ident()`. Undated sorts last.
- **The country code is the country of the CATALOGUE, not the tier of government** - the caveat
  ships in the JSON, on the page, in `meta.json` and `llms.txt`.
- Agents are told not to scrape in four places: the HTML comment above `<title>`, alternate
  links, the visible note under the search field (never a tooltip), and `/llms.txt`.

## MCP server

`mcp-server/`, a stateless Worker; the tool contract lives once in `mcp_tools.py`. It reads
`mcp-index.json` (a Worker gets 10ms CPU; the 5.6 MB export does not parse in time), written
in the same export run. **Not part of `run.sh`** - redeploy only when its code changes, and
never write a catalogue COUNT into it (it said 17 while 19 were live). Search reads every field
the tool promises: `n d o a rp` - add to `compact()` in `export_json.py` and `matches()` together. `cf:
{cacheTtl}` caches every status, and `cacheTtl: 0` does not force a miss: change the cache KEY.

## Accessibility

WCAG 2.1 AA contrast re-audited 2026-08-13 on every text node including pressed states (lowest
4.9:1). **No screen-reader testing has been done** - never read the audit as conformance.

## Tests

Eleven suites, 506 checks, **all manual** - a test that can fail the weekly publish is one someone
switches off. Run before touching any stage or page builder. **Validate every suite by SABOTAGE,
and sabotage with `PYTHONDONTWRITEBYTECODE=1 python3 -B`** (a same-second, same-size edit
otherwise runs the previous bytecode). Rules from doing it: a test must never ask the thing it
tests whether to run its hardest case; if a guard cannot be made to fail, delete it; match a
config's ROUTE, not its text (a comment once satisfied a check).

| file | pins |
|---|---|
| `test_detect_lang.py` | language tagging, incl. `lang_with_prior`/`lang_assume_en`, shared ä/ö, org hints |
| `test_dedupe_identity.py` | the three identity rules, `norm_repo`/`norm_site`, survivor, unions, redirect/repo-rename QID loans, `is_repo_url` |
| `test_crosswalk_cache.py` | crosswalk input refresh: stale-when-unstamped, stamp-only-on-success, asked-set, sensor, retry, unverified-not-stamped |
| `test_liveness_strikes.py` | `fold_history()`: two strikes, unknown-never-dead, revival |
| `test_translation_orphans.py` | orphan detection, and the naive rule it rejects |
| `test_filters.py` | `classify()` incl. licence and `wordpress-plugin`, the `replaces.json` gate, publisher `replaces:` |
| `test_stage_guard.py` | refuse-on-merged-input, both directions |
| `test_variants.py` | every `variants.resolve()` rule, forks, reinstatement, real cases |
| `test_built_pages.py` | built pages, cross-page contracts, language copies, hosting files |
| `test_harvest_get.py` | `get()`: 401/403/404 raise at once, the rest retried then raised, a non-JSON 200 raises, never None; `_refuse_short_scan()` |
| `test_workers.py` | the three Workers under Node: site indexes and `/ca`, `www` 301 + CORS, MCP JSON-RPC, search fields, cache-KEY retry, and the tool contract vs `mcp_tools.py` |

Untested, with reasons: crosswalk's `__main__` wiring (Comptoir precedence, the org-shared-homepage
skip) - its parts are pinned, the glue needs a stubbed Comptoir and SPARQL together.

## Four bugs that recurred - suspect these first

1. **A responding endpoint is not a working source.** Verify content, not status codes.
2. **Language tagging** - broken six times. See Language above; run `test_detect_lang.py`.
3. **Absence of evidence treated as evidence of absence.** Confirm through a second channel.
4. **String-replace patching fails silently.** Verify the built output; after a structural edit,
   grep for what should still be there.

## Gotchas

- `run.sh` resolves its own python3 (needs `yaml` + `certifi`); never add bare `python3` calls.
  "Works in my shell, not under launchd" is a PATH question first, every time.
- Harvest checkpoints per source the moment one succeeds; `catalog.json` is assembled from
  every checkpoint on disk. `run.sh` warns if the catalogue shrinks >10%.
- France's 24,440-repo inventory is excluded on purpose - an enrichment join at most.
- `out/` and `site/` are gitignored per-run artefacts; a fresh checkout has neither.
