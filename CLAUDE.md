# govoss-catalog

> Union catalogue of **government open source software**, harvested first-hand from 17
> national, municipal and international catalogues, normalised onto one schema, translated to
> English, categorised by function, de-duplicated and liveness-monitored.
>
> **2,753 entries · 17 catalogues · 15 countries incl. EU + global.** Live at
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

**Wikidata is the second source, reached BY URL ONLY** — `P1324` source code repository and
`P856` official website. 554 -> 645 entries carrying a QID.

*Never by name.* `Q936` (OpenStreetMap) has **no English label at all**, `Audacity` resolves to
three QIDs and `Caddy` to two, and `about` matches a real software item called `about` — and
generic repo names are everywhere here. Two guards, both added after watching them fail:
**the matched item must BE software** (17 of 92 homepage matches were not — `Q1199` is the
German state of Hesse, reached because an entry's landing is `hessen.de`, plus a Taiwanese
ministry and an elementary school), and **a homepage shared by entries with different names is
an organisation site**, not an identity (four unrelated German repos share `umwelt.info`).
Wikidata stores URL properties as **IRIs, not strings**, so `VALUES ?s { "https://…" }` matches
nothing silently; and the queries POST, because the VALUES blocks 414 on a GET.

Measured limit, so the yield is not overestimated: the repo route stamped 51 QIDs but produced
**one** merge — entries sharing a repo URL already merge on repo URL, so a QID derived from
that same URL tells dedupe nothing. It is worth running for identity coverage, not as the fix
for duplicates. It is best-effort: a slow SPARQL endpoint must never fail a gated step.

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
of taking the merge on trust. **95 entries appear in 2+ catalogues**, up from 37 as identity
coverage improved (see the crosswalk and dedupe sections)
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

### The "Recommended" stamp is retired (2026-08-14)

`In N catalogues` is now the only endorsement pill. The **Recommended** seal was removed
because it rendered one badge over two different claims:

- **`FR/sill` — 668 rows, a genuine publisher assertion.** SILL *is* the Socle
  Interministériel de Logiciels Libres, France's list of software recommended to public
  agents, so `harvest.py` sets the flag on every row and records
  `note: "recommended to public agents; not necessarily gov-authored"`.
- **`DE/opensource.muenchen.de` — 85 rows, OUR inference.** `recommended_for_gov = not
  built`. Munich's actual claim is *"in production use at the City of Munich"* — that is
  **adoption, not endorsement** — and the rule inverted it: software Munich *built*
  in-house got no seal, third-party software it merely runs did.

This is precisely the failure `wikidata_via: comptoir:<how>` exists to prevent, and there
is no `recommended_via` to separate an inferred claim from an asserted one. The pill was
also **inconsistent**: `recommended_for_gov` rides the merge survivor and is not in
`dedupe.py:UNION_LIST`, while a publiccode-tier row scores +40 against the flag's +5 — so
**70 of 753 flags are dropped on merge**, 24 of them on entries that still list `FR/sill`
as a source. AngularJS showed `Recommended` and `Archived upstream` side by side.

**The data is unchanged.** `catalog.json` keeps `recommended_for_gov` and `export_json.py`
still emits `recommended_for_government` — this was a display decision, not a deletion, the
same posture as flagging rather than dropping a filtered entry. **Do not reinstate an
endorsement stamp without first splitting the two provenances.**

## Identity and dedup

Join key is the **normalised repo URL** (`norm_repo()`: no scheme/www/.git, deep links
stripped). Cross-country overlap is genuinely tiny — 2 duplicates in ~1,940 repos — so the
union is additive.

For **upstream general-purpose software** (Angular, 7-Zip) repo URLs do *not* join: SILL
says `angular.dev`, Sweden says `angular.io`. Use the **Wikidata QID** instead. Precedence:
QID → normalised repo URL → homepage.

**Never name alone — but exact name AND exact homepage together is the third identity.**
Rules 1 and 2 cannot reach the commonest split: the same upstream tool listed by two
catalogues that recorded different repo URLs and carry no QID. OpenStreetMap was three
entries — Munich, Sweden, DPG — one with no repo at all and two pointing at different *wiki
pages*. It is a **conjunction of two independent identifiers**, which is what makes it safe:
Angular and AngularJS have different homepages, so that case is still prevented (verified —
they remain separate, `Q28925578` and `Q2849803`). And the homepage is what stops generic
names merging: `docs`, `about` and `api` never qualify because they have no landing page,
while four unrelated German repos sharing `umwelt.info` stay split because their names differ.
It collapsed Audacity, Masterportal and OpenStreetMap (3 -> 2; Sweden's record has neither a
homepage nor a real repo, so nothing can reach it without a hand-stamped QID).

**Never fuzzy-match names.** Angular (`Q28925578`) and AngularJS (`Q2849803`) are different
products and one name contains the other. `comptoir-du-libre.org/api/v1/softwares.json` is a
useful ready-made crosswalk (`url_repository`, `wikidata`, `sill`, `wikipedia_en` in one row).

## Translation

`translations/tr_*.json` map `sha1(source_text)[:10]` -> English, so a translation
survives a re-harvest while upstream wording is unchanged. `desc_src` keeps the
original; `translated: true` marks machine translation. **2,921 of 2,938 described
entries display English.** Pinned by `test_translation_orphans.py` and
`test_detect_lang.py`.

- ⚠ **Keys hash the RAW `short_desc`, never a stripped one** — 12 Bulgarian
  descriptions carry surrounding whitespace, and stripping anywhere in the chain
  invalidates every key in every file at once.
- ⚠ **Read `desc_lang` (what is displayed), never `desc_src_lang`** (the language
  of the original). openCode and NL entries carry a foreign original in `desc_src`
  beside publisher English; counting by it reports 358 false "untranslated".
- **Entries with NO description are set aside** (`no-description`, 384) rather than
  shown — an editorial standard about publisher effort, running after
  `enrich_desc.py`, flagging not deleting. It read 316 entries out of the public
  API until `/entries.json` started carrying set-aside rows flagged.
- **Orphaned keys are reported** in `out/translation_orphans.json`; the trigger is
  GROWTH, not the total, and a missing previous figure is not zero. The naive
  definition ("keys this pass looked up") reports 1,762 of 1,762 on merged input.
- **The files are hand-maintained with MIXED indentation.** Rewriting them in one
  style turned a 62-line change into 1,145 lines of noise; preserve each file's own
  indent and key order.

⚠ **SILL and code.overheid.nl use `lang_with_prior()`, NOT `detect_lang()`.**
Both used to hardcode `"fr"`/`"nl"`. `detect_lang` cannot replace that: it returns
`en` whenever it finds no foreign stopwords, and a short catalogue phrase has none
— it called **532 of 672** SILL descriptions English ("Logiciel d'édition de
vidéo"), which would have dropped them all out of translation. `lang_with_prior`
keeps the source's language unless the text carries **two distinct** English
function words that are not stopwords in any catalogue language. It moves 27 rows
to `en`, all read and all English; 13 were untranslated English showing as
foreign. Pinned by `test_detect_lang.py`, sabotaged three ways.

**Munich and DPG use the mirror, `lang_assume_en()`** — English unless
demonstrably foreign. They hardcoded `"en"`, which was right for 394 of 395 and
published Munich's German Epitaph description untranslated. Bare `detect_lang`
fixes that and mis-tags three English strings (`os` in "OS X" is Portuguese,
`la`/`no` Spanish), so a foreign verdict also needs fewer than two English
markers. Changes exactly one row. Its translation is already in `tr_de.json`.
## Categorisation

`taxonomy.py` collapses **233 inconsistent source values** onto 19 functional
categories. Explicit, never fuzzy, and **an unmapped value is a BUG** rather than an
"other" bucket — sources disagree structurally (publiccode ships controlled
kebab-case, SILL Title Case free text, Offentligkod Swedish, openCode drifts across
`IAM`/`IDM`/`Identity- und Access-Management`). 44% from source, 41% inferred from
text (flagged `functions_inferred`), 15% left unclassified rather than force-fitted.

`taxonomy.py` writes `out/taxonomy_unmapped.json` and `build_sources.py` warns by
name; it self-clears. Saying "it is a bug" was previously a print into a log nobody
read, and fired unnoticed twice.

**Three outcomes, not two.** Beside "map it" and "it's a bug" there is **map it to
`None`** — for a value describing the *audience* or the *artefact type* rather than
the function. `government`, `public-administration` and the DPG artefact types sit
there: every entry here is government software, so the label carries no functional
signal by construction, and the taxonomy falls through to text inference instead of
force-fitting a bucket.

⚠ **Check whether the entry is actually unclassified before treating an unmapped
value as an editorial judgement call.** `scheduling` and `government` both looked
like hard calls and neither was: each sat on an entry whose *other* category already
classified it, so the unmapped value cost a signal, not a classification. And check
for a sibling family — `M` already mapped six spellings of scheduling to
`case-workflow`, so any other home would have split one concept in two.

⚠ **`out/taxonomy_unmapped.json` and `site/status.json` are per-run artefacts**, so
a mapping fix does not clear the page until the next run. A local `warn` naming a
value you just mapped is stale output, not a failed fix — confirm by dry-running
`classify()`, not by reading the page.
## Liveness monitor

`liveness.py` -> `liveness.json`, reporting the **delta** — "3 newly dead" is a
signal, "81 dead" is a number nobody reads. Not 1,940 HEADs: GitHub via GraphQL
100-at-a-time, GitLab hosts via their API, ~240 others via HEAD serialised per
host. ~4.5 min. Current: **3,089 of 3,189 ok (96.9%), 26 dead, 39 archived, 69
unknown.** State machine pinned by `test_liveness_strikes.py`.

- **`403/429/5xx` are UNKNOWN, never dead.** An earlier all-HEAD version measured
  GitHub's rate limiter: 27% 429s.
- **Two consecutive dead observations before a dead verdict**, because single ones
  oscillate (a gitlab *group* URL 404s the projects API and answers HEAD
  inconsistently). One-offs are `pending`, never shown.
- **Every dead verdict is confirmed by a plain web HEAD.** Load-bearing:
  `gitlab.huma-num.fr` restricts anonymous API access, so a first version called
  **53 of 82** dead when they were fine, KiCad among them.
- **HEAD fetches the ORIGINAL url, never `repo_key`** — that is lowercased for
  joining and 404s case-sensitive paths.
- **It always exits 0**, but a crash annotates `summary.failed_at`/`last_error` and
  leaves `checked` standing, so `checked` means *last successful sweep* and its age
  is what the page warns on. A successful run rebuilds `summary`, clearing the
  markers.
## Per-source freshness (`cache/_fetched.json`) — read before trusting a count

Checkpoint reuse is deliberate: a failed source contributes its last good data
rather than dropping a country. That reuse used to be **invisible** — harvest exits
0 regardless, checkpoints carry no date, and the only per-source alarm fires on a
count of *zero*, which a reused checkpoint never produces. A source dead for six
months rendered as current, on a page saying `ok`, in a commit titled `Data: <date>
run`.

- **`fetched_at` advances ONLY on success.** A failure records its error and leaves
  the old timestamp standing; the growing age is the signal.
- **Per-source summary, never per-record.** 17 timestamps a week is meaningful
  churn; the same idea per record once turned one liveness diff into 47,563 lines.
- `build_sources.py` warns >15 days, critical >29 — thresholds in **runs**, not
  days.
- ⚠ **Look these up by the CHECKPOINT key (`os2`), not the `sources.py` key
  (`DK/os2`).** The first version matched nothing for all 17 sources, built cleanly
  and reported `ok`. `nlreg` has a checkpoint and no `sources.py` row; the two
  French catalogues share the `fr` checkpoint.
- ⚠ **`--from-cache` must not write `_fetched.json` or `_timing.json`** (guarded by
  `if want:`) — a no-network rebuild blanked both to `{}` and destroyed the record
  of the last real fetch.
- **`os2()` is the one adapter that could destroy its own checkpoint** — 20 orgs,
  failures swallowed, a short scan overwriting the last good copy. It now raises
  when orgs failed **and** the result regressed; failure alone is not the test.
- **`github_org_scan` authenticates via `liveness.gh_token()`**, not `GITHUB_TOKEN`
  alone — that variable is not in the plist, so scheduled runs scanned at 60/hr.

⚠ **Harvest still exits 0 on a failed source, deliberately.** One flaky source must
not block the weekly publish of sixteen good ones. The fix is visibility, not a
gate.
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
| `/entries.json` | every row incl. set-aside, flagged `excluded` |
| `/meta.json` | categories, sources, licences, counts, `generated_at`, known gaps |
| `/by-product.json` | **inverted index**: proprietary product -> alternatives |
| `/by-category/<key>.json` | one file per functional category |
| `/by-country/<CC>.json` | one file per country (15, incl. `EU` + `GLOBAL`) |
| `/v1/entries.json` | versioned alias so consumers can pin |

`Access-Control-Allow-Origin: *` on all `*.json`. `/api/entries`, `/api/catalog`,
`/catalog.json` and `/data.json` redirect to `/entries.json` — those are the paths the
first agent to use this catalogue probed and got 404 from. Cheaper to answer where callers
look than to expect them to read docs.

**No `POST /api/match`.** It cannot be a static file and the deployment is deliberately
backend-free. `/by-product.json` is that endpoint precomputed — 2 GETs answered a 17-line
procurement inventory in 0.2s, versus the ~35 browser searches it replaced.

### `replaces.json` — the field that changes what the catalogue is for

Maps catalogue entry -> proprietary products it can replace, inverting the lookup so
a buyer starts from an invoice line. **194 entries -> 290 products**, hand-seeded,
browsable at `/products.html`. Metadata in `proprietary.json` (descriptions: NYC's
own `purpose` string where available, hand-written otherwise; **functions
hand-assigned** — deriving them from the alternatives' categories filed Bitbucket
under *Case & Workflow Management*).

`confidence`: `strong` | `partial` | `adjacent`. `kind` matters as much —
`software` replaces it, `service` means the paid item is hosted service or CONTENT
(Drupal does not replace *hosting*), `paid-tier` means a commercial edition of
already-open-source software and is usually the cheapest win.

- **Matching UNIONS every key matching the survivor name or any `also_known_as`.**
  First-match-wins dropped GitLab's `GitLab Premium` row when dedupe picked a
  different survivor name.
- **`export_json.py` validates both vocabularies against the file's own `_README`
  and FAILS the step.** It used to pass silently — the by-product sort does
  `rank.get(confidence, 3)`, so a bad value just sorted last. Failing is right
  here: the file is hand-edited and the check is deterministic. Pinned by
  `test_filters.py`.
- ⚠ **Check a `paid-tier` row is keyed on the software the commercial edition is
  built from.** `Icinga -> Nagios XI` was `paid-tier` *and* mis-kinded: Icinga2 is
  a fork, so it is `software`/`partial`, and the real paid-tier exit is Nagios Core.
- **`export_json.py` warns on keys matching no entry**, so the seed cannot rot
  unnoticed — that warning is what caught the union bug above.
- **The page qualifies anything not `strong`+`software`** (62% of mappings).
  Display only: `rp` stays clean names for search and the filter, `rpq` carries the
  qualifier in a parallel array built in the same pass.
### Dedupe (`dedupe.py`)

Merges on **Wikidata QID, then normalised repo URL**, union-find so identities chain.
**Never on name similarity** — Angular `Q28925578` and AngularJS `Q2849803` are different
products and one name contains the other. 3,206 rows -> 2,753 active + 453 set aside,
178 merge groups.
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

### `stage_guard.py` — taxonomy and dedupe REFUSE merged input

Both are **destructive** on an already-merged `catalog.json`, silently, exiting 0:
dedupe resets every survivor's `catalogue_count` to 1 (the "In N catalogues" pill,
98 entries); taxonomy narrows `functions` on 45 entries, because `functions` is in
`UNION_LIST` and `classify()` only sees the survivor. `assert_pre_dedupe()` exits 2
if any **active** row carries `catalogue_count`; `harvest.py --from-cache` restores
the shape. Pinned by `test_stage_guard.py`.

⚠ **It REFUSES; do not make it merge-aware and do not add `--force`.** Unioning the
recomputed value with the stored one means a corrected mapping, or a record that
legitimately stopped being multi-catalogue, keeps its stale value forever with
nothing to say so — a loud bug traded for a silent permanent one.

⚠ **A by-hand re-run is therefore the wrong way to verify a change to either
stage.** Dry-run the pure function and diff it against itself with and without
your edit; that separates your 1 change from the 45 the merge accounts for.

⚠ **`merge_translations.py` is in the same family but WARNS rather than refusing.**
Its orphan count is position-dependent — run after dedupe, merged-away rows take
their source text with them and their translations look rotted (measured: 32
reported, 29 of them dedupe casualties). Re-running is safe; only the reading
misleads. Guard what destroys data, warn where the number lies.
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

`run.sh`'s last two steps publish and commit. Before they existed the weekly run
regenerated everything and published none of it, while its own status page still
said "Operational".

- **`deploy` is gated on `out/steps.tsv`** — any non-zero step and nothing is
  published; a partially harvested catalogue overwriting a good public copy is
  worse than a stale one. It runs after the run log and pages, so the published
  copy describes the run that published it, and **aborts if
  `site/.vercel/project.json` is missing** (`site/` is gitignored, and
  `vercel deploy --yes` would silently create a NEW project).
- **`record` commits `catalog.json`, `history.json`, `liveness.json` and `cache/`
  and pushes**, sharing the deploy's gate so what is committed is what is
  published. Deliberately narrow: explicit path list never `git add -A`; refuses
  any branch but `main` and mid-rebase/merge/bisect; `git commit -- <paths>` so a
  human's staged edits survive; never force-pushes; `GIT_TERMINAL_PROMPT=0`
  because a prompt under launchd hangs forever.
- Git auth is the macOS keychain and **does** resolve under launchd — checked with
  `git credential fill` under `env -i`. ⚠ `git ls-remote` and `push --dry-run` both
  succeed on a public repo *without* authenticating, so neither is evidence.
- ⚠ **"Deploy doesn't work under launchd" was a misdiagnosis** — the `vercel` shim's
  `#!/usr/bin/env node` could not find node on the launchd PATH, which reads as an
  auth failure. Third instance of the same shape (see the python3/pyyaml gotcha).
  Check with `env -i PATH=<plist PATH> HOME=$HOME vercel whoami`.

### Deploy auth is REPORTED, not just relied on (F7)

Auth resolves `VERCEL_TOKEN` -> `~/.config/govoss/vercel-token` (chmod 600) -> the
CLI's stored login, and `publish()` records which to `out/deploy_auth.txt`;
`runlog.py` puts it in `history.json` as `deploy_auth` and `build_sources.py`
**warns while the route is `stored-login`**. The fragile mode was already
*printed*, and a print is not a sensor: a revoked login fails the deploy, but the
only outward signal is the site going stale and the Stale badge not flipping for 8
days.

- ⚠ **`None` is not `stored-login`.** A run that never reached deploy records
  `None` and must not warn — defaulting it would report a posture the run never had.
- `warn`, not `critical`: nothing is broken while the login works, and over-grading
  config debt trains the reader to ignore the page.
- **The pre-flight checks CONTENT, not exit status.** `vercel whoami` prints a bare
  username on success and an `Error: … err.sh/…` block otherwise. It does exit 1,
  but that only survives `| tail -1` because `run.sh` sets `pipefail` 130 lines
  earlier — a check that silently no-ops if someone edits that line. It is also
  deliberately **non-fatal**: a transient hiccup must not block a good publish; it
  only makes the failure legible (auth, not PATH).
- ⚠ **The remaining step is a CREDENTIAL, not code.** Mint a token at
  vercel.com/account/tokens into the file; `~/.config/govoss/` exists (mode 700,
  with a README). Until then the page carries the warning, which is intended.

### Committed JSON must be deterministic

Every file in `DATA_PATHS` is written sorted with no per-record timestamp. Not
tidiness: weekly churn went **50,199 diff lines -> 2,365**, and repo growth from
~100-250 MB/year to single digits. Two causes, both measured — unstable record
order (`src_tw.json` churned 458 lines with 0 of 58 records changed) and a per-run
timestamp stored per record (`liveness.json`'s `checked` was 47,563 of a
47,563-line diff).

- Write with `sort_keys=True` **and** `stable_order()`, whose key is deliberately
  total — name alone ties constantly and a tie lets rows swap between runs. It is
  duplicated in `harvest.py` and `dedupe.py` on purpose; importing `harvest`
  executes its module body.
- **Never store a per-run value per record.** It belongs in a summary.

The payoff is not megabytes: `git log -p liveness.json` now answers "what changed
this week", which it could not before.

## The pages

Four generated surfaces on `@wegovnyc/design-tokens` under the **`govoss` brand
variant** — the system wegov.nyc and unnyc.wegov.nyc share. `/` (`build_ui.py` +
`_ui_template.py`), `/sources.html` (`build_sources.py`, also build status),
`/api.html`, `/products.html`, shared chrome in `theme.py`. `build_status.py` is
retired; `/status.html` 308s to `/sources.html`, but **`/status.json` is still
written** — retiring a page is a design decision, retiring an endpoint breaks
agents.

- **No f-strings for markup.** `theme.py` and `_ui_template.py` hold CSS/HTML/JS as
  plain strings with `__PLACEHOLDER__` tokens substituted at the end, and the
  substitution asserts none survived. This removed the brace-doubling trap.
- **Tokens are VENDORED, not transcribed** (`vendor/wegovnyc/`, pinned release,
  inlined at build). govoss has no bundler. The tradeoff is real: an upstream fix
  does not reach govoss until someone copies it.
- **`theme.py` is an ALIAS LAYER onto `--wg-*`**, diverging from the siblings which
  migrated and deleted their aliases. The aliases carry no values, so a variant
  remap still propagates — that is the property to protect.
- ⚠ **The alias map is by ROLE and MEASURED CONTRAST, never by name.**
  `--wg-text-muted` is 2.90:1 and `--wg-accent` 3.15:1 on the page ground, and
  govoss uses those roles 24 and 26 times as text. Recompute rather than copy;
  these read 3.00/3.26 until they were re-measured.
- **The brand variant must be APPLIED, not merely present.**
  `theme.assert_variant_live()` checks the ROOT TAG — an unapplied variant falls
  back to a face this repo does not ship and the page silently renders in Georgia.
  ⚠ Its first version substring-searched the whole page and the vendored CSS's own
  comment contains the literal, so it could only ever pass.
- **Fonts are self-hosted** — the readership is European public-sector staff and a
  Google Fonts request is a live GDPR objection. Upstream records this as a
  sanctioned divergence.

govoss left the CTFG design system on 2026-08-13 by owner decision; CTFG remains a
consumer of this data. `DESIGN-BRIEF.md` has the UI rules; `UPSTREAM-CTFG.md` and
`CTFG-CONTRAST-REPORT.md` are historical record. Side effect worth having: the
build now makes **no network request at all**.
### Catalog page UI — rules paid for in bugs

Full incidents in `ARCHIVE.md`; `test_built_pages.py` pins what a static check can
reach. These bite again if violated.

- **`el.hidden` works only because `theme.py` ships `[hidden]{display:none!important}`.**
  The attribute hides via the UA stylesheet, which ANY author `display:` rule
  outranks — `.drawer{display:flex}` rendered 253px tall with `hidden` set, and
  `.more{display:block}` offered "Show 100 more" for a 2-result list. Never
  `style.display`.
- ⚠ **Checking `el.hidden` is not checking that it is hidden.** The property reads
  `true` while the element renders full height. Assert
  `getComputedStyle(el).display === 'none'`.
- ⚠ **Measure rows by vertical CENTRE, not `top`** — `align-items:center` gives
  differently-sized controls different tops on the *same* row. This reported
  "2 rows" for a correct single-row toolbar twice.
- ⚠ **Check a class name is free.** `class="more"` collided with the "Show 100
  more" button's `display:block;width:100%`, so a link filled its row and looked
  like a wrapping bug. Nine names in `_ui_template.py` carry >1 rule block.
- **The toolbar is one row above 940px by `flex-wrap:nowrap` + `min-width:0`**, not
  tuned widths — wrap wraps a line *before* shrinking anything on it. Selects
  absorb the squeeze; `.tog` gets `flex:0 0 auto` or it wraps its label and changes
  height. `#lic` needs `.toolbar #lic` to beat its own ID rule.
- **`.side` is sticky WITH `max-height:calc(100vh - 40px)` + `overflow-y:auto`**,
  static under 940px. Unbounded, its bottom is unreachable — measured 887px in an
  860px viewport *after* a facet group was deleted to "fix" it. The bound is the
  fix; the group count never was.
- ⚠ **`current()` routes every facet key EXPLICITLY.** It was `else srcs.push(v)`,
  so a new `cc` group silently filtered by source and emptied the list.
- **`?src=<label>` / `?cc=<code>` are validated and an unknown value is IGNORED.**
  Filtering to nothing reads as "this catalogue contributed no entries" — the claim
  `/sources.html` exists to disprove. The value is `SOURCES[key]["label"]` on both
  sides.
- **Source country shows NAMES; the facet VALUE stays the code**, matched against
  `r.cs` so a multi-country entry is findable under each. `EU`/`GLOBAL` are not
  countries. `Sort: country` sorts by the displayed name.
- **Flags split out of the facet label in JS** — one source for flag and name, so
  sidebar and strip cannot disagree. Unknown -> the name, never an empty cell.

### Recently added, and `cache/_first_seen.json`

`first_seen.py` stamps when each entry first appeared, after dedupe, committed with
`cache/`. Backfilled once from the weekly `Data:` commits — **3,070 baseline, 119
dated across 9 runs.**

- ⚠ **`null` means BASELINE, not absent.** An id carrying `null` predates the record
  and is never "new"; a *missing* id is unseen and gets stamped. Conflating them
  dated the whole 3,070-entry baseline to the backfill day.
- ⚠ **Only `Data:` commits count as observations** — 16 of git's 27 revisions of
  `catalog.json` are the project being *built*, not entries arriving.
- ⚠ **`build_ui._fs_ident()` must match `first_seen.ident()`** or every entry reads
  as undated and the strip silently empties.
- The strip shows **10**, carrying a description **only when English**; the rest is
  reachable via `Sort: recently added`, whose tie-break must match the strip's
  (name ascending, then date descending — `reverse=True` on a tuple reverses both
  keys and the two led with different entries).
- ⚠ **Undated entries sort LAST under `recent`,** never first.

### The API note is agent affordance 3 of 4

Small, directly under the search field — *earlier* in the DOM than its old slot
above the stat tiles, so the affordance improved. It must stay visible text: never
a tooltip, a collapsed disclosure or an image. ⚠ `theme.py`'s icons carry a viewBox
and no width/height, so every context sizes its own or it renders enormous.

### `/sources.html` answers four questions

How the data is obtained, whether it filters regionally, how much there is, how
reliable it is — after a policy researcher asked all four. Per source: `N%
publiccode` (depth, not volume — SILL is 4% of 670, Developers Italia 100% of 537)
and `N% links live` (unknowns excluded from the denominator), plus a `By country`
grid linking `/by-country/<CC>.json`.

⚠ **The country code is the country of the CATALOGUE, not the tier of government
that published the software** — there is no municipal/regional/national field. The
caveat ships in the JSON, on the page, in `meta.json` and in `llms.txt`: it is the
figure most likely to be misread by the audience most likely to want it.


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

WCAG 2.1 AA re-audited 2026-08-13 after the design-system move, by sweeping **every text node
on all four pages** (plus pressed/toggled states, which a static sweep misses): **zero failures,
lowest ratio 4.9:1** on accent-over-tint chips. The previous 5.17:1 was a property of the CTFG
palette, not a requirement — 4.9 clears AA's 4.5 with margin, and chasing 5.17 by darkening
every accent chip would cost the accent identity for no accessibility gain.

The move DID surface one genuine failure and three tight spots, all fixed: the pressed toggle
was **2.41:1** (`--wg-accent-soft` is a mid blue, where govoss uses that token as a pale ground
— pressed states now use navy text), and three 10-11px badges sat at 4.62-4.9 on mid green or
tint, now on the dark tone. **The first sweep missed the 2.41 entirely because no facet was
pressed** — audit interactive states explicitly, not just the page at rest. **No screen-reader testing has been done** — do not read the audit as a
conformance claim. `DESIGN-BRIEF.md` has the seven UI rules this produced, including that a
native `<select>` ignores your CSS until `appearance:none`, and that a flex item's default
`min-width:auto` defeats `overflow-x`.

## Tests

Seven suites, 193 checks, **all manual** — a test step that can fail the weekly
publish is one someone switches off, and `run.sh` already gates its deploy on every
build step exiting 0. Run before touching `dedupe.py`, `liveness.py`, `filters.py`,
`taxonomy.py`, `merge_translations.py`, `export_json.py` or the page builders:

```bash
for t in test_*.py; do python3 $t; done
```

| file | pins |
|---|---|
| `test_detect_lang.py` | 5 language-tagging recurrences, real catalogue strings |
| `test_dedupe_identity.py` | the 3 identity rules, `norm_repo`/`norm_site`, survivor selection, `merge()` unions |
| `test_liveness_strikes.py` | `fold_history()` — two strikes, unknown-never-dead, revival, oscillation |
| `test_translation_orphans.py` | orphan detection, and the naive rule it rejects |
| `test_filters.py` | `classify()` incl. 2 rules removed for cause, + the `replaces.json` vocabulary gate |
| `test_stage_guard.py` | refuse-on-merged-input, both directions |
| `test_built_pages.py` | the built pages + three cross-page contracts |

**Every suite is validated by SABOTAGE** — break the thing it checks and watch it
fail — because this repo has shipped a guard that could only ever pass.

⚠ **Sabotage with `PYTHONDONTWRITEBYTECODE=1 python3 -B`.** The suites load modules
via `spec_from_file_location`, which trusts `__pycache__` when mtime and size
match — and a sed swapping `2` for `1` inside the same second changes neither. Every
run then tests the PREVIOUS edit, and a restored file reports failures. Three rules
came out of doing that:

- **A test must never ask the thing it tests whether to run its hardest case.**
  `test_stage_guard.py` keyed its subprocess cases on `is_post_dedupe()`, so a
  sabotaged guard made the test *skip* the cases that prove destruction.
- **If a guard cannot be made to fail, delete it.** A "do the two `pslug`
  implementations agree?" check was written, sabotage-tested and removed: both
  collapse `[^a-z0-9]+` then `-+`, which absorbs every plausible one-sided edit.
  Replaced by an outcome check — do the links land? — which survives causes nobody
  thought of.
- **Sabotage finds bugs the assertions were not written for.** Three did: a
  `^www\.`-before-`.lower()` case bug in `norm_repo` (latent, 0 of 4,464 URLs), a
  refusal naming a lowercased key you cannot grep for, and a stale cost comment
  arguing for weakening a rule.

Untested, with reasons: `get()`'s raise semantics (needs a stubbed opener),
crosswalk's three guards (inline in SPARQL-calling functions — they need the
extraction `fold_history()` got), and the MCP Worker (JS on Cloudflare).
## Four bugs that recurred — check for these first

If something looks wrong, suspect these before anything else.

1. **A responding endpoint is not a working source.** `code.gov` returns 200 and is
   retired; India's OpenForge has a live API, 1,502 projects and zero code; a green
   pipeline log once hid a dead harvest. *Verify content, not status codes.*
2. **Language tagging** — broke **five** times: per-source tagging skipping Finnish
   and Swedish; 12 entries declaring `description.en` while German; 88 Portuguese
   strings called English; 45 English strings called Danish because English *for*
   is a Danish stopword; then English text repeating that homograph twice. Now: two
   markers, at least one not also an English word (`_EN_HOMOGRAPH`). Pinned by
   `test_detect_lang.py` — run it after touching `_STOP`, `_EN_HOMOGRAPH` or
   `detect_lang`. ⚠ **Over-correcting is the worse failure**: listing `la`/`le`/
   `per`/`van`/`die` as English homographs called Italian and French text English,
   which drops real text *out* of the queue. ⚠ **Diacritics are the signal** — a
   test string transcribed `gor` for `gør` fails for the right reason.
   *Never reintroduce a per-source language assumption* — and never swap one for
   bare `detect_lang` either; see `lang_with_prior` under Translation.
3. **Absence of evidence treated as evidence of absence.** An API 404 meant "dead
   repo" until `gitlab.huma-num.fr` turned out to restrict anonymous access — 53 of
   82 were alive, KiCad among them. A missing description meant "not software"
   until it excluded `Products.PloneMeeting`. *Confirm through a second channel.*
4. **String-replace patching fails silently.** A banner "landed" against markup from
   a different file and never appeared. *Verify the built output, not the patch
   report* — and after a structural edit, grep for what should still be there. This
   bit twice while pruning these very docs: a `##`-level replacement swallowed four
   `###` subsections, both times caught only by checking.
## Gotchas in this repo

- **`run.sh` resolves its own interpreter.** Do not add bare `python3` calls. Under launchd,
  PATH resolved to Homebrew's python3, which has no pyyaml — harvest died while every later
  step "succeeded" on stale data. `run.sh` now probes for an interpreter with `yaml`+`certifi`
  and exits 1 with instructions if none has them. **The publish step hit the identical bug
  from the other direction** — `vercel` was on PATH but its `#!/usr/bin/env node` was not.
  Treat "works in my shell, not under launchd" as a PATH question first, every time.
- **Two stages refuse to run on already-merged `catalog.json`** (`taxonomy.py`, `dedupe.py`)
  — see `stage_guard.py`. If one exits 2 saying REFUSING, rebuild with
  `python3 harvest.py --from-cache`; do not reach for a force flag, there isn't one.
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
