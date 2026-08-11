# govoss-catalog

> Aggregated catalogue of **national government open source software**, harvested
> first-hand from eight European national catalogues, normalised onto one schema,
> translated to English, categorised by function, and liveness-monitored.

Output: `catalogue.html` (self-contained browsable page) and `catalog.json` (the data).

## Live state

```
bash run.sh                  # full pipeline, ~15 min
python3 harvest.py --from-cache   # rebuild offline from checkpoints, no network
python3 harvest.py fr it     # re-harvest named sources only
python3 liveness.py          # monitor only (~4.5 min), diffs vs previous run
python3 analyze.py           # counts, overlap, licence + liveness breakdown
```

Schedule: **Mondays 07:00 local** via `~/Library/LaunchAgents/org.antigravity.govoss-harvest.plist`
(log: `~/Library/Logs/govoss-harvest.log`). Weekly is deliberate — these
catalogues move slowly and a run costs ~15 min of I/O against other people's
public infrastructure.

## The eight sources, and how each is reached

| Country | Source | Route | ~Count |
|---|---|---|---|
| 🇮🇹 IT | Developers Italia | **REST API** `api.developers.italia.it/v1/software` | 550 |
| 🇫🇷 FR | SILL | bulk JSON `code.gouv.fr/sill/api/sill.json` | 668 |
| 🇩🇪 DE | openCode | **GitLab API** on `gitlab.opencode.de` | 476 |
| 🇧🇪 BE | iMio | GitHub org `IMIO` | 236 |
| 🇸🇪 SE | Offentligkod | **GNU recutils file in git** (GitLab) | 148 |
| 🇫🇮 FI | Avoinkoodi | 3 static JSON files | 72 |
| 🇫🇷 FR | awesome-codegouvfr | bulk JSON | 19 |
| 🇪🇺 EU | code.europa.eu | GitLab API | ~12 |

**All eight converge on `publiccode.yml`** — that is what makes this an ingestion
project rather than a scraping project.

### Things that will bite you

- **Use `code.gouv.fr/sill/api/sill.json`, NOT `/data/sill.json`.** The latter is a
  reduced export with **no url field at all** — its `u` key is an *update timestamp*,
  which an earlier version mistook for a repo URL, giving every SILL row a date as its
  identity. The rich export also carries **Wikidata QIDs** (554/668), which is the only
  thing that makes upstream software joinable across catalogues.
- **openCode.de has no API**, but its directory slugs embed the GitLab project ID
  (`badge-api-4058` → project 4058) and the directory is auto-built from `publiccode.yml`
  in that GitLab. So the GitLab API *reproduces* the official listing. Never scrape the site.
- **The Netherlands needs an API key.** `api.developer.overheid.nl/oss-register/v1` returns
  `401 Missing credentials` on every read. Register at oss.developer.overheid.nl, then set
  `NL_API_KEY` (add it to the plist's `EnvironmentVariables`). Spec:
  `github.com/developer-overheid-nl/don-oss-register` → `api/openapi.json`.
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

Maps catalogue entry -> proprietary products it can replace, inverting the lookup so a
buyer starts from an invoice line. Currently **73 entries -> 95 products**, hand-seeded.
`export_json.py` **warns on keys matching no entry**, so the seed cannot rot unnoticed.

`confidence`: `strong` | `partial` | `adjacent`. `kind` matters as much:
- `software` — replaces the software
- `service` — the paid item is hosted service or CONTENT. Drupal does not replace *hosting*;
  Moodle does not produce *training content*. Without this the field generates confident
  category errors.
- `paid-tier` — the paid item is a commercial edition of software that is **already open
  source** (NGINX Plus, Elastic licence tiers, DBeaver PRO, MySQL Enterprise). Usually the
  cheapest win in a procurement review: often no migration, just a renewal you stop.

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

`history.json` begins 2026-08-11 and is seeded with the one genuine launchd run from
`~/Library/Logs/govoss-harvest.log`. That record carries a `_note` saying it predates the
dedupe, filter and export steps and the liveness confirmation pass — which is why its dead
count is 83 against today's 22. Nothing else is back-filled; with one run the page says so
rather than drawing a trend line it cannot support.

## Gotchas in this repo

- **`run.sh` resolves its own interpreter.** Do not add bare `python3` calls. Under launchd,
  PATH resolved to Homebrew's python3, which has no pyyaml — harvest died while every later
  step "succeeded" on stale data. `run.sh` now probes for an interpreter with `yaml`+`certifi`
  and exits 1 with instructions if none has them.
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
