# govoss-catalog

> Aggregated catalogue of **national government open source software**, harvested
> first-hand from eight European national catalogues, normalised onto one schema,
> translated to English, categorised by function, and liveness-monitored.

Output: `catalogue.html` (self-contained browsable page) and `catalog.json` (the data).

## Live state

```
bash run.sh                  # full pipeline, ~15 min
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
- **iMio contributes 236 repos but only 1 `publiccode.yml`**, so the rest are indexed at the
  thinner `index` tier. Meta-repos like `.github` still appear; a name-pattern filter is a
  reasonable next step.
- **France's 24,440-repo inventory (`repositories/json/all.json`) is deliberately excluded.**
  It answers "who published this", not "is this useful to a government": 45% no description,
  80% no licence, dominated by research code, only 18 entries with a `publiccode.yml`. See the
  comment in `harvest.py:fr()`. Re-add it as an *enrichment join* (it has `is_archived`,
  `last_update`, `software_heritage_url`), never as catalogue entries.
