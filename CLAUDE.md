# govoss-catalog

> Union catalogue of **government open source software**, harvested first-hand from 17
> national, municipal and international catalogues, normalised onto one schema, translated to
> English, categorised by function, de-duplicated and liveness-monitored.
>
> **3,080 entries · 17 catalogues · 15 countries incl. EU + global.** Live at
> https://govoss-catalog.vercel.app — see `README.md` for the public overview and
> `CONTINUE.md` for open items. This file is the operating manual: it records why each
> decision was made and what not to re-litigate.

Output: `catalogue.html` (self-contained browsable page) and `catalog.json` (the data).

## Live state

```
bash run.sh                  # full pipeline, ~15 min
python3 harvest.py --from-cache   # rebuild offline from checkpoints, no network
python3 harvest.py fr it     # re-harvest named sources only
python3 liveness.py          # monitor only (~4.5 min), diffs vs previous run
python3 analyze.py           # counts, overlap, licence + liveness breakdown
```

Schedule: **Mondays 07:00 local**, installed with `bash schedule/install.sh` (log:
`~/Library/Logs/govoss-harvest.log`). **The template under `schedule/` is the source of
truth** — the copy in `~/Library/LaunchAgents` is derived, so never edit it in place or the
tracked version and the running one drift, and the tracked one is what you will read when
something breaks. `bash schedule/install.sh --diff` shows whether they have. Weekly is deliberate — these
catalogues move slowly and a run costs ~15 min of I/O against other people's
public infrastructure.

**The run publishes itself** — `run.sh` ends with a `deploy` step that pushes `site/` to
Vercel, so there is no manual `vercel deploy --prod` any more. See *Publishing* below.

## The 17 sources, and how each is reached

| Country | Source | Route | ~Count |
|---|---|---|---|
| 🇮🇹 IT | Developers Italia | **REST API** `api.developers.italia.it/v1/software` | 550 |
| 🇫🇷 FR | SILL | bulk JSON `code.gouv.fr/sill/api/sill.json` | 668 |
| 🇩🇪 DE | openCode | **GitLab API** on `gitlab.opencode.de` | 476 |
| 🇧🇪 BE | iMio | GitHub org `IMIO` | 236 |
| 🇸🇪 SE | Offentligkod | **GNU recutils file in git** (GitLab) | 148 |
| 🇫🇮 FI | Avoinkoodi | 3 static JSON files | 72 |
| 🇫🇷 FR | awesome-codegouvfr | bulk JSON | 19 |
| 🇪🇺 EU | code.europa.eu | GitLab API | ~10 |
| 🇳🇱 NL | code.overheid.nl | **Forgejo API** (open, no key) | 134 |
| 🇨🇦 CA | Open Resource Exchange | `code.json` | 67 |

| 🇹🇼 TW | Public Code Platform (moda) | **official open-data export** | 58 |
| 🇮🇪 IE | OGCIO Ireland | GitHub org | 5 |
| 🌐 GLOBAL | Digital Public Goods Registry | REST API | 249 |

**`sources.py` is the single source of truth** for source labels, links, access routes and
the global survey. Imported by `build_ui.py`, `export_json.py` and `build_sources.py`, so a
URL cannot disagree between the page, the JSON and the docs. `/sources.html` + `/sources.json`
render it with live counts.

Not all of them use `publiccode.yml` any more — that was true of the original eight and is
still the richest tier (1,080 entries), but the catalogue now also ingests `code.json`
(Canada), recutils in git (Sweden), markdown frontmatter (Munich), an official open-data
export (Taiwan), plain GitHub/GitLab/Forgejo org scans (Belgium, Ireland, Portugal, Denmark,
Bulgaria, Netherlands) and a REST API (DPG). **The pattern that generalises is: find the
machine route the catalogue's own site is built from, and read that.** Every source here was
found that way, never by scraping a rendered page.

### Things that will bite you

- **Use `code.gouv.fr/sill/api/sill.json`, NOT `/data/sill.json`.** The latter is a
  reduced export with **no url field at all** — its `u` key is an *update timestamp*,
  which an earlier version mistook for a repo URL, giving every SILL row a date as its
  identity. The rich export also carries **Wikidata QIDs** (554/668), which is the only
  thing that makes upstream software joinable across catalogues.
- **openCode.de has no API**, but its directory slugs embed the GitLab project ID
  (`badge-api-4058` → project 4058) and the directory is auto-built from `publiccode.yml`
  in that GitLab. So the GitLab API *reproduces* the official listing. Never scrape the site.
- **The Netherlands no longer needs an API key.** `code.overheid.nl` is the government's own
  self-hosted **Forgejo/Gitea 1.22** with the standard open `api/v1` — 134 repos (MinBZK,
  Rijkswaterstaat, Amsterdam, the Electoral Council's Abacus vote-counting software), no auth.
  The separate OSS *register* (`api.developer.overheid.nl/oss-register/v1`) still 401s without a
  key and is kept as `nlreg`, but it is no longer blocking: the code platform is arguably the
  better source anyway — first-hand repos rather than a register of pointers.
- **Canada localises everything.** `code.open.canada.ca/code.json` nests `tier → adminCode →
  releases[]`, and `name`, `tags`, `licence`, `homepageURL` **and `repositoryURL`** are all
  `{en, fr}` dicts. Passing them through crashed taxonomy, filters and dedupe in turn; `loc()`
  flattens them. Its `tags` are free-text research topics ("SIR", "compartment model"), so they
  go to `keywords`, **not** `categories` — feeding them to the taxonomy produced ~100
  unmappable one-offs, and that warning is only useful while it stays near zero.
- **Read the EU catalogue's FACET NAMES — they work even though its search does not.**
  The source facets are plain text in the page HTML: `hosting_platform:ogcio` resolved
  Ireland (Office of the Government CIO, `github.com/ogcio`), previously listed as
  unresolved. Three remain unidentified as catalogues: `arte` (Franco-German broadcaster),
  `city_of_ghent` (a municipality) and `dmrid_dits` (`github.com/DMRID` is an individual
  with one repo). Reading facet labels beats guessing hostnames.
- **The UNODC "Directory of Open-Source Registries" is a FALSE LEAD — do not chase it.**
  GlobE is UNODC's anti-corruption law-enforcement network, and "open-source registries"
  there means open-source *intelligence*: company and beneficial-ownership registries for
  investigators. It surfaced in a software-catalogue search and reads plausibly relevant
  from the title alone, which is exactly why it is recorded.
- **Taiwan: use the PUBLISHED dataset, not the SPA's API.** code.gov.tw is a Vue SPA. Its
  internal API works — `POST /api/PublicProgramInfo/queryList` lists 58 programmes and
  `.../getPublicProgramData` returns repo URLs — but that is two undocumented POSTs per
  entry. The site also links an official open-data export at
  `/api/OpenDataSet/PublicProgramInfoData/json`: one GET, repo URLs included, officially
  published. Note `PublicProgram` (submission side, requires My eGov agency verification)
  is a different endpoint from `PublicProgramInfo` (public read). Programme names stay in
  Chinese as published; descriptions are translated.
- **DPG repository URLs are free text.** Some pack several URLs plus prose into one field
  (`…/therapist-web-app, https://…/patient-app, and https://…`). Taken verbatim they 404 and
  register as newly-dead repos — dead links jumped 21 → 39 before the regex extraction
  landed. Extra URLs go to `extra_repos`.
- **Spain's CTT is bot-protected and stays that way.** Every route — HTML, RSS, `/api/*` —
  returns HTTP 200 with an F5/BIG-IP TSPD CAPTCHA page instead of data. Bypassing a CAPTCHA
  is not on the table. The legitimate route is Spain allowlisting a harvester or publishing
  via datos.gob.es. Re-check rather than retry; the block is deliberate.
- **Korea's oss.kr is the wrong shape.** A national OSS *promotion* portal — contests,
  contribution academy, licence verification, news — whose `/opensource/hub/<id>` pages
  profile upstream projects (Node.js and the like), not Korean public-sector code, and carry
  no adoption data. Nothing to ingest without changing what the catalogue means.
- **code.gov is retired.** It 302s to a Digital.gov policy page and `api.code.gov` returns the
  same HTML. The US federal inventory that *defined* the `code.json` schema is gone — but the
  schema outlived it, and Canada still uses it. Recorded in `sources.py:SURVEY` so nobody
  re-probes it.
- **Ireland, Portugal and Cyprus** appear as EU-catalogue facets but no machine route was
  found. Listed in `harvest.py` as `UNRESOLVED` rather than silently dropped.

## The EU aggregate catalogue is deliberately NOT syndicated

`interoperable-europe.ec.europa.eu/eu-oss-catalogue` federates all eight of these.
**Do not use it as a source.** As of 2026-08-10 its pager, facets *and* keyword search
all ignore the query string — every URL returns the same first 20 of 1,084 solutions, so
1,064 are unreachable. Verified on a forced CDN cache miss and in a real browser. Solution
pages are also absent from `sitemap.xml`. Full writeup with reproduction: `PAGINATION-BUG.md`.

Beyond the bug, it is the wrong layer: it ingests France's **19-entry** curated list rather
than the real French sources, so syndicating it inherits that hole permanently.

## Identity crosswalk (`crosswalk.py`)

Runs AFTER harvest and BEFORE dedupe, and adds no coverage — it only fills in Wikidata QIDs
entries were missing, because dedupe unions on QID first and repo URL second. An entry with
no QID can only merge with something sharing its exact repo URL, which is why the same tool
listed by two catalogues with slightly different URLs stayed split.

Comptoir du Libre (ADULLACT) is the one open source carrying several identifiers on the SAME
row: 780 entries, all with a repo URL and website, 270 with a QID, 349 with a SILL id. It
stamped **121 QIDs**, which lifted dedupe from 156 to **241 merges** and multi-catalogue
entries from 46 to **105**.

Match order is repo URL → SILL id → website → **exact** full name. Never fuzzy: Angular
`Q28925578` and AngularJS `Q2849803` are different products and one name is a substring of
the other. Every stamped QID records `wikidata_via: comptoir:<how>` so an inferred identity
is never mistaken for a publisher-asserted one.

## Cross-catalogue presence

`catalogue_count` + `catalogues[]` per entry: how many DISTINCT catalogues list this
software, with a **deep link into each** so a reader can verify the claim upstream instead
of taking the merge on trust. **37 entries appear in 2+ catalogues** (34 in two, 3 in three
— NextCloud Server, QGIS and OpenProject each in Developers Italia + SILL + DPG). Sortable
in the UI via "In most catalogues", and a stat tile.

**Every emitted deep link is verified.** 1,611 links, full sweep, zero broken. Two rules
had to be thrown away to get there:

- **openCode**: do NOT construct `opencode.de/en/software/<slug>-<id>`. The public directory
  lists only ~270 of the 477 projects carrying a publiccode.yml, so a constructed link 404s
  for ~40% of them (POLAR, App Config…). Use the GitLab `web_url`, which always exists and
  is the record the directory is generated from.
- **DPG**: the registry slug is not derivable from the API name — the API says
  "NextCloud Server", the registry serves `/r/nextcloud`. Scraping the index yields only 20
  of 249 slugs (JS-paginated). So each candidate is HEAD-checked at harvest time: 221/249
  verified, the other 28 get `null`.

`entry_url` is deliberately null for Developers Italia (JS app, no software pages in its
sitemap), Offentligkod and Canada (no per-entry route). A guessed deep link is worse than
none — the same rule as `licence_spdx`.

## Identity and dedup

Join key is the **normalised repo URL** (`norm_repo()`: no scheme/www/.git, deep links
stripped). Cross-country overlap is genuinely tiny — 2 duplicates in ~1,940 repos — so the
union is additive.

For **upstream general-purpose software** (Angular, 7-Zip) repo URLs do *not* join: SILL
says `angular.dev`, Sweden says `angular.io`. Use the **Wikidata QID** instead. Precedence:
QID → normalised repo URL → homepage.

**Never fuzzy-match names.** Angular (`Q28925578`) and AngularJS (`Q2849803`) are different
products and one name contains the other. `comptoir-du-libre.org/api/v1/softwares.json` is a
useful ready-made crosswalk (`url_repository`, `wikidata`, `sill`, `wikipedia_en` in one row).

## Translation

`translations/tr_*.json` map `sha1(source_text)[:10]` → English. Keying on the text hash means
translations **survive a re-harvest** as long as upstream wording is unchanged.
`merge_translations.py` applies them; `desc_src` keeps the original and `translated: true`
marks machine translation so it is never confused with publisher-supplied English (`desc_en`).

Coverage is 100% of described entries (452 source English + 1,486 translated). 239 entries
have no description upstream and are left empty rather than invented.

**Two traps that produced false "done" claims:**
1. Gap detection keyed off `desc_lang`, which the index-tier adapters never set — so 72
   Finnish and 7 Swedish descriptions were skipped entirely while the queue reported 100%.
   Adapters now set `desc_lang`; **verify against content, not against the queue.**
2. **12 entries declare `description.en` but are not English** (`Hochwasserinfosystem` is pure
   German; `Leezenflow` is half-German). Trusting the language tag leaves them untranslated
   while reporting success. Catch these by grepping *output* for foreign function words.

## Categorisation

`taxonomy.py` collapses **233 inconsistent source values** onto 19 functional categories.
The mapping is explicit, never fuzzy, and **an unmapped value is reported as a bug** rather
than bucketed into "other". Sources disagree structurally: publiccode ships controlled
kebab-case, SILL ships Title Case free text, Offentligkod ships Swedish, openCode has drift
(`IAM` / `IDM` / `Identity- und Access-Management` all separately).

64% classified from source, 23% inferred from text via multilingual keyword rules (flagged
`functions_inferred`), 14% left unclassified rather than force-fitted.

## Liveness monitor

`liveness.py` → `liveness.json`, and reports the **delta** against the previous run, which is
the part with value: 3 newly-dead repos is a signal, "81 dead" is a number nobody reads.

It is **not** 1,940 HEAD requests. An earlier version was, and **27% came back 429** — that
measured GitHub's rate limiter, not the catalogue. Instead: GitHub via **GraphQL, 100 repos
per request** (~14 requests, and yields `isArchived`/`pushedAt` too); GitLab hosts via their
API; the ~240 repos across 176 other hosts via HEAD **serialised per host** with backoff.
Runtime ~4.5 min, no throttling.

`403/429/5xx` are recorded as **unknown, never dead** — the distinction matters, since
treating rate-limiting as death would invent drift. Current: **96.3% ok, 22 confirmed dead (1.1%), 48 unknown (2.5%), 15 archived**.

**Every dead verdict is confirmed with a plain web HEAD before being recorded.** This is not
belt-and-braces, it is load-bearing: `gitlab.huma-num.fr` restricts anonymous API access, so
its live projects returned 404 from `/api/v4` while the web URL answered 200. The first version
without this pass called **53 of 82** "dead" repos dead when they were fine — including KiCad,
Lazarus IDE and FreePascal — overstating the dead rate roughly 3x and reporting live projects
as newly-dead drift. An API 404 is not evidence of absence.

**A dead verdict requires TWO consecutive dead observations** (`dead_count` persists in
liveness.json). Single observations oscillate: `gitlab.com/opentestfactory` is a *group* URL,
not a project URL, so the projects API 404s it and HEAD answers inconsistently — one run
"rescued" it, the next declared it dead. An unstable signal is worse than a steady wrong one
because it trains you to ignore the report. One-off 404s are reported as **pending**, never as
dead, and never shown on the page.

**HEAD always fetches the ORIGINAL url, never `repo_key`.** repo_key is lowercased for joining;
fetching it 404s case-sensitive paths — which is how a Wikipedia page SILL uses as BeautifulSoup's
"repository" got reported dead. GitHub and GitLab are case-insensitive, which is why this hid.

Roughly a third of raw 404s are not dead software at all but **upstream data quality**: SILL
points at gitweb CGI (`git.postgresql.org/gitweb/?p=postgresql`), an SVN trunk, a download page,
and in one case a Wikipedia article. Those resolve via the confirmation HEAD; the residue that
genuinely is gone is dominated by removed GitHub repos (15 of 22).

Dead and archived state is also shown **on the page** (stat tile, `repo gone` pill, and a
repo-state filter), because a monitor whose output only lands in a JSON file nobody opens is
the same failure as having no monitor.

It always **exits 0**: a monitor that can fail the pipeline gets switched off the first time
it is wrong.

## Filtering non-software (`filters.py`)

iMio publishes 236 repos but only **one** has a `publiccode.yml`, so the rest are indexed
from bare GitHub metadata. That is real coverage, but it sweeps in things no government can
adopt. `filters.py` flags **58** entries; the page hides them by default behind a
`show 58 filtered` toggle, and each carries a reason pill.

| reason | n | rule |
|---|---|---|
| `upstream-fork` | 30 | GitHub `fork: true` — evidence, not a name guess |
| `deployment-recipe` | 18 | `buildout.*`, `server.*`, `scripts-*` — install other software, aren't it |
| `locale-bundle` | 5 | `*.locales` — translation resources, no functionality |
| `ci-plumbing` | 4 | `gha`, `security-scanning`, `*-action` |
| `org-meta` | 1 | `.github` |

**It FLAGS, never deletes** (`excluded` + `exclude_reason` stay on the record), and anything
with a `publiccode.yml` is never filtered — the publisher explicitly declared that reusable,
which beats any heuristic here.

`fork: true` is the load-bearing rule: it catches `ZODB`, `zope.sendmail`,
`Products.CMFEditions`, `puppetlabs-vcsrepo` and `oca-web`. "ZODB, Belgian public-sector
software" was simply wrong.

**Two rules were removed after reviewing what they actually caught** — the reason flagging
beats deleting:
1. A `no-usable-metadata` rule (missing description) hit **61** entries including
   **`Products.PloneMeeting`** — iMio's flagship deliberations product — plus `Products.urban`
   and the ten municipality `Products.Meeting*` profiles Walloon councils actually run. A
   missing GitHub description is an upstream metadata gap, **not** evidence something is not
   software. Same error shape as treating an API 404 as a dead repo.
2. A `-german$` locale rule caught `teleservices-iacitizen-german`, a German-language *build*
   of a real product. Do not re-add it.

## Machine-readable export (`export_json.py`) + dedupe

Static files in `site/`, no backend. `run.sh` emits them every run.

| path | what |
|---|---|
| `/entries.json` | 1,995 entries, structured fields (2.9 MB) |
| `/meta.json` | categories, sources, licences, counts, `generated_at`, known gaps |
| `/by-product.json` | **inverted index**: proprietary product -> alternatives |
| `/by-category/<key>.json` | one file per functional category |
| `/v1/entries.json` | versioned alias so consumers can pin |

`Access-Control-Allow-Origin: *` on all `*.json`. `/api/entries`, `/api/catalog`,
`/catalog.json` and `/data.json` redirect to `/entries.json` — those are the paths the
first agent to use this catalogue probed and got 404 from. Cheaper to answer where callers
look than to expect them to read docs.

**No `POST /api/match`.** It cannot be a static file and the deployment is deliberately
backend-free. `/by-product.json` is that endpoint precomputed — 2 GETs answered a 17-line
procurement inventory in 0.2s, versus the ~35 browser searches it replaced.

### `replaces.json` — the field that changes what the catalogue is for

**Matching UNIONS every key that matches the survivor name or any `also_known_as`.**
First-match-wins was wrong: dedupe can pick a different survivor name than a mapping was
keyed on — merging "GitLab Community Edition" into "GitLab" flagged three keys as rot when
they were merely redundant, *and* silently dropped what those keys mapped that the survivor's
did not (GitLab lost its `GitLab Premium` paid-tier row). The orphan warning is what caught
it, which is the whole reason that warning exists.

Maps catalogue entry -> proprietary products it can replace, inverting the lookup so a
buyer starts from an invoice line. Currently **211 entries -> 312 products**, hand-seeded.
`export_json.py` **warns on keys matching no entry**, so the seed cannot rot unnoticed.

`confidence`: `strong` | `partial` | `adjacent`. `kind` matters as much:
- `software` — replaces the software
- `service` — the paid item is hosted service or CONTENT. Drupal does not replace *hosting*;
  Moodle does not produce *training content*. Without this the field generates confident
  category errors.
- `paid-tier` — the paid item is a commercial edition of software that is **already open
  source** (NGINX Plus, Elastic licence tiers, DBeaver PRO, MySQL Enterprise). Usually the
  cheapest win in a procurement review: often no migration, just a renewal you stop.

**`export_json.py` validates both vocabularies against the file's own `_README` and FAILS
the step on a bad value.** It used to pass silently: the by-product sort does
`rank.get(confidence, 3)`, so an invalid confidence just sorted last. That is how
`Icinga -> Nagios XI` sat with `confidence: "paid-tier"` — a `kind` value in the confidence
field. Same rule as `taxonomy.py`: an unmapped value is a **bug**, not something to bucket.
Failing is right here because this file is hand-edited and the check is deterministic — it
cannot be wrong the way a network measurement can, and failing at export means a bad edit
never reaches the deploy.

That entry was also mis-*kinded*. `paid-tier` promises "no migration, just a renewal you
stop", and Icinga2 is a **fork** of Nagios, not a rebuild — so it is `software`/`partial`,
and the genuine paid-tier exit from Nagios XI is **Nagios Core**, which is separately in
the catalogue. Check that the paid-tier row is keyed on the software the commercial edition
is actually built from.

**The page qualifies anything that is not `strong` + `software`.** 62% of mappings are not
like-for-like swaps (21% paid tier or hosted service, 53% partial or adjacent), and the
catalog page used to print all of them as a flat `Replaces X, Y, Z` — asserting exactly the
category error the `_README` exists to prevent. It now renders `Contentful (hosted service,
adjacent)`. The qualifier is **display only**: `rp` stays the clean product names so the
search haystack and the "Replaces a paid product" filter are unchanged, and `rpq` carries
the qualifier in a parallel array built in the same pass so the two cannot fall out of
alignment. `note` is export-only — it reaches `entries.json` and `by-product.json`, never
the page.

Publishers can also declare `replaces:` in their own `publiccode.yml` (non-standard
extension) and `harvest.py` picks it up, so claims can be owned upstream.

### Dedupe (`dedupe.py`)

Merges on **Wikidata QID, then normalised repo URL**, union-find so identities chain.
**Never on name similarity** — Angular `Q28925578` and AngularJS `Q2849803` are different
products and one name contains the other. 2,122 -> 1,995 (127 collapsed, 84 groups).
Pre-merge rows kept in `out/dupes.json` for audit.

Only 15 groups are cross-country (Matomo FR+IT, OpenProject DE+FR+IT — genuine, and the
point of a union catalogue). The other 69 are **personal forks on gitlab.opencode.de**: 15
projects (`tlrz/opendesk`, `dschmidt/opendesk`, …) each carry upstream's publiccode.yml
declaring `url: .../bmi/opendesk`. GitLab exposes `forked_from_project` only on a
single-project GET, but it is not needed — a project whose declared url is not itself is a
fork or mirror, and the declared url is the identity.

**Survivor selection uses namespace containment, not suffix matching.** openDesk declares
`bmi/opendesk` while the canonical project lives at `bmi/opendesk/deployment/opendesk`, so an
`endswith()` test failed for the real project *and* every fork, and richness alone handed the
entry to `tlrz/opendesk` — a fork.

## Agent discoverability

The page tells agents not to scrape it, in four places, because the first consumer probed
eight dead paths and then drove a headless browser:

1. An **HTML comment above `<title>`** listing the endpoints — for agents that read raw HTML.
2. `<link rel="alternate" type="application/json">` x3 and a `<meta name="description">`.
   These sit before any visible markup; browsers hoist them into the implied `<head>`, so
   they work on the raw Vercel-served file even though it has no explicit `<head>`.
3. A **visible banner** directly above the stat tiles, so a text extraction hits it early.
4. **`/llms.txt`** — generated by `export_json.py`, so its counts can never drift from the
   data. Plus `/robots.txt` and `/sitemap.xml`.

## Status page (`build_status.py` + `runlog.py`)

`/status.html` and `/status.json`: freshness, per-source counts, pipeline step results,
open items, and a change log. Built from `history.json`, which `runlog.py` appends to at
the end of every run.

**Step outcomes come from `out/steps.tsv`**, which `run.sh` writes as it goes. This is not
redundant: reading the end state cannot distinguish "harvest failed and later steps ran on
stale data" from "harvest succeeded" — which is exactly the silent partial run that once
produced a fully green log with a dead harvest inside it.

Health is three states with defined triggers: any failed step or >8 days since a run is
`critical`; a source contributing 0 records or an overdue run is `warn`; otherwise `ok`.
Per-source counts are read from the **checkpoints**, so a source that failed shows its last
good figure rather than silently reading as zero.

The page also **re-judges its own freshness in the browser**. The badge is baked at build
time, so a copy that stopped being republished would keep reading "Operational" no matter
how old it got — a green signal that is green because nothing updated it, which is the same
failure shape as the silent partial run. A few lines of JS compare `run_at` against the
reader's clock using the same 8-day trigger and flip the badge to **Stale**.

## Publishing

`run.sh`'s last step is `deploy`, which pushes `site/` to Vercel. Before it existed the
weekly run regenerated everything and published none of it: the live copy went stale while
its own status page still said "Operational", and every update needed a hand-run
`vercel deploy --prod`.

- **Gated on `out/steps.tsv`.** Any non-zero step and nothing is published — a partially
  harvested catalogue overwriting a good public copy is worse than a stale one.
- **Runs last**, after the run log, sources and status pages, so the published copy
  describes the run that published it.
- **Aborts if `site/.vercel/project.json` is missing.** `site/` is gitignored, so a fresh
  checkout has no project link, and `vercel deploy --yes` would silently create a *new*
  project rather than fail. Relink with `cd site && vercel link --yes --project govoss-catalog`.
- **Auth**: `VERCEL_TOKEN`, else `~/.config/govoss/vercel-token` (chmod 600), else the CLI's
  stored login. The file is preferred over the plist because LaunchAgent plists are
  world-readable and end up in backups, and rotating a file needs no `launchctl` reload.

### `record` — the run commits and pushes its own data

The step after `deploy`, sharing its gate, so **what is committed is what is published**. It
commits `catalog.json`, `history.json`, `liveness.json` and `cache/` and pushes to
`origin/main`. Before it existed the repo showed whatever was last committed by hand while
the site moved on weekly — the same drift as the manual deploy, one layer over.

It is deliberately narrow, because this is a public repo and it runs unattended:

- **Explicit path list, never `git add -A`.** An automated `add -A` is how a stray token,
  scratch file or half-finished edit gets published. `.gitignore` is a backstop, not the plan.
- **Refuses any branch but `main`**, and refuses mid-rebase/merge/bisect, so it cannot commit
  onto work in progress.
- **`git commit -- <paths>`** scopes the commit to the data even if a human had something else
  staged; their staged edits survive untouched. Verified, along with every guard above.
- **Never force-pushes.** If origin moved ahead the commit stays local and says so — a data
  file auto-rebased through a conflict is worse than a stale repo.
- **`GIT_TERMINAL_PROMPT=0`.** A credential prompt under launchd would hang the job forever
  with no terminal to answer it.

Git auth is macOS keychain (`credential.helper osxkeychain`, from Xcode's gitconfig) and it
*does* resolve from a launchd job — checked with `git credential fill` under `env -i`, not
inferred. Note `git ls-remote` and a no-op `git push --dry-run` both succeed on a public repo
**without authenticating**, so neither is evidence the credential works; that is the same
absence-of-evidence shape as bug 3 below.

### Committed JSON must be deterministic

**Every file in `DATA_PATHS` is written sorted, and stores no per-record timestamp.** This is
not tidiness — before it, week-over-week churn was **50,199 diff lines; it is now 2,365**, a
95% cut, and the repo went from ~100–250 MB/year of growth to single digits.

Two causes, both measured rather than guessed:

1. **Unstable record order.** Adapters emit in whatever order upstream answered, so
   byte-identical records changed position. `cache/src_tw.json` churned **458 lines with 0 of
   its 58 records changed** — the cleanest possible demonstration. Sorting took it to 0.
2. **A per-run timestamp stored per record.** `liveness.json` gave every repo a `checked`
   field set to the same `NOW`, so all 3,005 records differed every run against ~90 real
   changes. That one field was 47,563 of the 47,563-line diff; without it, 487.

Rules for anything added to `DATA_PATHS`:

- Write with `sort_keys=True` **and** sort the records with `stable_order()`. That key is
  deliberately **total** — name alone ties constantly (localised builds, forks, the same
  product in two catalogues) and a tie lets rows swap between runs, which is the churn you
  were removing. It is duplicated in `harvest.py` and `dedupe.py` on purpose; importing
  `harvest` would execute its module body.
- **Never store a per-run value per record.** It belongs in a summary. `export_json.py` reads
  `summary.checked` for every entry's `last_checked`, guarded by `if lv` so an entry with no
  liveness record stays `null` instead of inheriting a time it was never checked at.

The real payoff is not the megabytes: `git log -p liveness.json` now answers "what changed
this week", which it could not before. History you cannot read is history you are storing for
nothing — the same objection this repo already makes about a monitor nobody opens.

`catalog.json` is the one file that did not shrink (998 → 1,072 lines). Its churn was already
mostly genuine, so there was nothing artificial to remove.

**"Deploy doesn't work under launchd" was a misdiagnosis, and it is the same bug as the
python3 with no pyyaml — third instance in this repo.** The `vercel` shim's shebang is
`#!/usr/bin/env node`, `node` was not on the launchd PATH, and the job died with
`env: node: No such file or directory` — which reads as an auth failure if all you observe
is that nothing deployed. Stored auth is fine; check with
`env -i PATH=<plist PATH> HOME=$HOME vercel whoami`. Both the plist PATH and `publish()`
now resolve **`/usr/local/bin/node`**, not the nvm one — that path carries a version number
and moves on every upgrade.

`history.json` begins 2026-08-11 and is seeded with the one genuine launchd run from
`~/Library/Logs/govoss-harvest.log`. That record carries a `_note` saying it predates the
dedupe, filter and export steps and the liveness confirmation pass — which is why its dead
count is 83 against today's 22. Nothing else is back-filled; with one run the page says so
rather than drawing a trend line it cannot support.

## The pages (restyled 2026-08-12)

Three surfaces, all generated, all on the Civic Tech Field Guide design system:

| page | built by |
|---|---|
| `/` catalog | `build_ui.py` + `_ui_template.py` |
| `/sources.html` sources **and build status** | `build_sources.py` |
| `/api.html` API + MCP | `build_api.py` |
| shared chrome | `theme.py` |

`build_status.py` is **retired** — its page merged into `/sources.html`, which 308s from
`/status.html`. **`/status.json` is still written**: retiring the page was a design decision,
retiring the endpoint would break agents.

**No f-strings for markup.** `theme.py` and `_ui_template.py` hold CSS/HTML/JS as PLAIN strings
with `__PLACEHOLDER__` tokens substituted at the end, and the substitution asserts none
survived. This removed the brace-doubling trap that was the most common way these files broke.

**Tokens are VENDORED, not transcribed** — `vendor/ctfg/` holds the CTFG token files at a
pinned version and `theme.py` inlines them at build time, asserting all four agree. Overrides
are labelled **PATCH** (delete when upstream fixes it) or **DIVERGENCE** (keep). See
`DESIGN-BRIEF.md` and `UPSTREAM-CTFG.md`.

**Fonts are self-hosted** (`fonts/`, 9 woff2, 344 KB, ~103 KB typically fetched). The design
system loads them from a CDN; we do not, because the readership is European public-sector staff
and a Google Fonts request is a live GDPR objection. Upstream now records this as a sanctioned
divergence.

## The MCP server

`mcp-server/` — a Cloudflare Worker at `https://govoss-mcp.devin-31f.workers.dev`. Public,
keyless, stateless, no Durable Object. Five tools; the contract lives once in `mcp_tools.py`,
read by both the Worker and `/api.html`.

It reads **`mcp-index.json`**, not `entries.json`: a Worker gets 10ms CPU and parsing the 5.6 MB
export blows that on a cold isolate. `export_json.py` writes the 852 KB index in the same run,
so they cannot drift. **Not part of `run.sh`** — it holds no data, so a weekly rebuild reaches
it with no redeploy.

**Two Cloudflare traps it cost us.** `cf: {cacheTtl}` caches EVERY status, so a 404 fetched
before the file existed was cached for an hour and the tool reported it missing long after it
was published. And `cacheTtl: 0` does **not** force a cache miss — it controls how long a
response is stored — so the retry must change the cache KEY (a throwaway query param) to escape
a cached failure.

## Accessibility

WCAG 2.1 AA audited 2026-08-12: 10 issues found and fixed, lowest contrast ratio now 5.17:1 on
all three pages. **No screen-reader testing has been done** — do not read the audit as a
conformance claim. `DESIGN-BRIEF.md` has the seven UI rules this produced, including that a
native `<select>` ignores your CSS until `appearance:none`, and that a flex item's default
`min-width:auto` defeats `overflow-x`.

## Four bugs that recurred — check for these first

The same shapes came back repeatedly. If something looks wrong, suspect these before
anything else:

1. **A responding endpoint is not a working source.** `code.gov` returns 200 and is retired.
   India's OpenForge has a live API, 1,502 projects and zero code. A green pipeline log once
   hid a dead harvest. *Verify content, not status codes.*
2. **Language tagging.** Broke **five** times: Finnish/Swedish skipped entirely, 12 entries
   declaring `description.en` while being German, all 88 Portuguese strings mislabelled
   English, 45 English strings called Danish because English *for* is also a Danish stopword
   — and then, after that was "fixed" by requiring two markers, English text that simply
   repeats the homograph: *"used **for** enabling … **for** Dexterity content"* scored two
   Danish markers, *"print **a** rss feed from **a** given URL"* two Portuguese ones. Five
   iMio repos were tagged `da`/`pt`.
   Now: two markers **of which at least one is not also an English word** (`_EN_HOMOGRAPH`).
   **`test_detect_lang.py` locks all five recurrences in with real catalogue strings** —
   run it after touching `_STOP`, `_EN_HOMOGRAPH` or `detect_lang`.
   Two traps found while fixing it, both worth knowing:
   - **Over-correcting is the worse failure.** A first attempt also listed `la`, `le`, `per`,
     `van`, `die` as English homographs — true in a dictionary, but they are the *core*
     stopwords of Italian, French and Dutch, and that version called *"Applicazione vocale su
     Alexa per la richiesta"* English. Mislabelling foreign text as English silently drops it
     **out** of the translation queue; the original bug only put the wrong text **in**. Keep
     `_EN_HOMOGRAPH` to high-frequency English function words.
   - **Diacritics are evidence, not decoration.** Transcribing a Danish test case as
     `gor … Faelleskommunal` instead of `gør … Fælleskommunal` made it fail, because `ø`/`æ`
     were the entire signal. Test strings must be byte-exact from the catalogue.
   *Never reintroduce a per-source language assumption.*
3. **Absence of evidence treated as evidence of absence.** An API 404 meant "dead repo" until
   `gitlab.huma-num.fr` turned out to restrict anonymous API access — 53 of 82 "dead" repos
   were alive, including KiCad. A missing GitHub description meant "not software" until it
   excluded `Products.PloneMeeting`. *Confirm through a second channel before asserting.*
4. **String-replace patching fails silently.** A visible UI banner "landed" against markup
   from a different file and simply did not appear. `showex` resolved to an id-global DOM
   element instead of the variable. *Verify the built output, not the patch report.*

## Gotchas in this repo

- **`run.sh` resolves its own interpreter.** Do not add bare `python3` calls. Under launchd,
  PATH resolved to Homebrew's python3, which has no pyyaml — harvest died while every later
  step "succeeded" on stale data. `run.sh` now probes for an interpreter with `yaml`+`certifi`
  and exits 1 with instructions if none has them. **The publish step hit the identical bug
  from the other direction** — `vercel` was on PATH but its `#!/usr/bin/env node` was not.
  Treat "works in my shell, not under launchd" as a PATH question first, every time.
- **Harvest checkpoints per source** to `cache/src_<key>.json` the moment a source succeeds,
  and `catalog.json` is assembled from *every* checkpoint on disk. This exists because a DNS
  blip once killed four sources and overwrote a complete catalogue with a partial one.
- **`run.sh` warns if the catalogue shrinks >10%** and prints per-source deltas. A source
  silently returning empty is the failure mode that looks like success.
- **`catalogue.html` is emitted as pure ASCII** (0 non-ASCII bytes): data is `\uXXXX`-escaped,
  prose uses HTML entities, and the one non-ASCII char in the JS is a `·` escape since
  entities are *not* decoded inside `<script>`. Artifacts cannot set `<meta charset>`, so
  depending on the host to declare UTF-8 rendered "open source â€” aggregated".
- **Never name a JS variable after an element `id`.** `showex` was declared inside `current()`
  but read in `render()`; it did not throw, because browsers expose ids as globals — so the
  name silently resolved to the checkbox *element* (always truthy) and the count denominator
  was permanently wrong. Read `el('showex').checked` explicitly.
- **France's 24,440-repo inventory (`repositories/json/all.json`) is deliberately excluded.**
  It answers "who published this", not "is this useful to a government": 45% no description,
  80% no licence, dominated by research code, only 18 entries with a `publiccode.yml`. See the
  comment in `harvest.py:fr()`. Re-add it as an *enrichment join* (it has `is_archived`,
  `last_update`, `software_heritage_url`), never as catalogue entries.
