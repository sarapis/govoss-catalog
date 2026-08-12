# govoss-catalog

A union catalogue of **government open source software**, harvested first-hand from 17
national, municipal and international catalogues, normalised onto one schema, translated to
English, categorised by function, de-duplicated, and liveness-monitored.

**Live:** https://govoss-catalog.vercel.app
· [JSON API](https://govoss-catalog.vercel.app/entries.json)
· [sources](https://govoss-catalog.vercel.app/sources.html)
· [status](https://govoss-catalog.vercel.app/status.html)
· [llms.txt](https://govoss-catalog.vercel.app/llms.txt)

| | |
|---|---|
| Entries | **3,070** |
| Catalogues | **17**, across 14 countries + the EU + a global registry |
| English descriptions | 100% of described entries (excl. 171 deliberately-untranslated Bulgarian) |
| Functional categories | 19, all 233 source category values explicitly mapped |
| Repos reachable | 97.1% · 24 confirmed dead · 43 archived |
| Procurement mappings | 108 entries → 165 proprietary products |

## What makes it different

**It answers "what can we stop paying for?", not just "what exists".** `by-product.json` is
an inverted index keyed by proprietary product name — two HTTP requests resolve a whole
software licence inventory. That came from a real request: an agent analysing NYC's 948
licence contracts needed the lookup to run from the invoice, not from the solution.

**It records what it does not know.** Machine translations are flagged `translated_from`,
inferred categories `categories_inferred`, crosswalked identity `wikidata_via`. `licence_spdx`
is `null` rather than a guess where the upstream string is not real SPDX. 13 catalogues that
were checked and *rejected* are published with the reason, because a verified dead end saves
the next person the same twenty minutes.

**It monitors itself.** Repository liveness is re-checked every run and diffed against the
previous one, so a dead link is a signal rather than a number nobody reads. Dead verdicts
require two consecutive observations, because single observations oscillate.

## Quick start

Python 3.10+, two dependencies:

```bash
pip install -r requirements.txt
```

```bash
bash run.sh                     # full pipeline, ~25 min
python3 harvest.py --from-cache # rebuild offline from checkpoints, no network
python3 harvest.py fr it        # re-harvest named sources only
python3 liveness.py             # monitor only, diffs against the previous run
python3 analyze.py              # counts, overlap, licence + liveness breakdown
python3 test_detect_lang.py     # regression test for language detection
```

```bash
bash schedule/install.sh        # macOS: install + load the weekly LaunchAgent
```

Runs Mondays 07:00 local, logging to `~/Library/Logs/govoss-harvest.log`. The LaunchAgent is
rendered from `schedule/*.plist.template` rather than checked in verbatim, because launchd
does not expand `~` inside a plist and a checked-in copy of somebody's home directory drifts
from the one actually running.

**The run publishes and records itself.** `run.sh` deploys `site/` to Vercel and then commits
and pushes the run's data output — both gated on every earlier step succeeding, so a run with
a failed step publishes nothing, commits nothing, and leaves the last good copy up. What is
committed here is what is live. `generated_at` in `/meta.json` is the freshness signal, and
`/status.html` flips to **Stale** on its own if it has not been republished in over 8 days.

## Pipeline

`run.sh` runs these in order, and the order matters:

| step | what |
|---|---|
| `harvest.py` | 17 source adapters; checkpoints per source to `cache/` |
| `merge_translations.py` | applies `translations/tr_*.json`, keyed on `sha1(source text)` |
| `taxonomy.py` | 233 source category values → 19 functions; unmapped values are reported as bugs |
| `crosswalk.py` | stamps Wikidata QIDs from Comptoir du Libre so dedupe can merge more |
| `filters.py` | flags forks, CI plumbing, deployment recipes as not-adoptable |
| `dedupe.py` | merges on QID then repo URL; never on name similarity |
| `liveness.py` | GitHub GraphQL + GitLab APIs + per-host HEAD; diffs vs last run |
| `build_ui.py` → `build_site.sh` → `export_json.py` | the page, the deploy dir, the JSON |
| `runlog.py` → `build_sources.py` → `build_status.py` | run history, sources page, status page |
| `deploy` → `record` | publish `site/` to Vercel, then commit + push the data — both gated on every earlier step passing |

## Data model

Static files, no backend. `site/` is assembled from tracked sources and deployed to Vercel.

    /entries.json              all entries, structured fields
    /meta.json                 category enum, sources, counts, known gaps
    /by-product.json           proprietary product -> open source alternatives
    /by-category/<key>.json    one file per functional category
    /sources.json              the 17 catalogues + 13 surveyed and rejected
    /status.json               freshness, per-source counts, change log
    /v1/entries.json           versioned alias

CORS is open on all JSON. `/api/entries`, `/api/catalog`, `/catalog.json` and `/data.json`
redirect to `/entries.json` — those are the paths the first consumer tried.

## Sources

France (SILL, awesome-codegouvfr) · Italy (Developers Italia) · Germany (openCode, Munich) ·
Denmark (OS2) · Bulgaria (e-Government Ministry) · Belgium (iMio) · Sweden (Offentligkod) ·
Netherlands (code.overheid.nl) · Portugal (ARTE) · Canada (Open Resource Exchange) ·
Taiwan (moda) · Finland (Avoinkoodi) · Ireland (OGCIO) · EU institutions (code.europa.eu) ·
global (Digital Public Goods Registry)

All are ingested **first-hand**. The EU's own aggregate catalogue is deliberately *not* a
source: its pager, facets and search all ignore query strings, so only 20 of its 1,084
solutions are reachable — see `PAGINATION-BUG.md`.

Source definitions, access routes and the rejected survey live in `sources.py`, which is the
single source of truth shared by the page, the JSON and the docs.

## Contributing

Two contributions are worth more than the rest:

**A source we've missed.** The pattern that generalises is *find the machine route the
catalogue's own site is built from, and read that* — an API, a bulk export, a file in git —
never a scraped rendered page. Every one of the 17 was found that way. Check
[`/sources.json`](https://govoss-catalog.vercel.app/sources.json) first: it publishes 13
catalogues already checked and **rejected**, with the reason, precisely so nobody spends the
same twenty minutes twice. A live endpoint is not a working source — `code.gov` returns HTTP
200 and is retired; India's OpenForge has an API, 1,502 projects and zero code.

**A `replaces.json` mapping.** This is the field that makes the catalogue answer *"what can
we stop paying for?"* rather than *"what exists"*, and it is hand-seeded, so it is the
thinnest part. Read the `_README` block in that file before adding: `kind`
(`software` / `service` / `paid-tier`) and `confidence` both matter, and getting them wrong
produces confident category errors — Drupal does not replace *hosting*, Moodle does not
produce *training content*.

Read `CLAUDE.md` before changing anything. It records what has already been tried and
rejected, and the four bug shapes that came back repeatedly.

## Files

- `CLAUDE.md` — the operating manual: every gotcha, why each decision was made, what not to
  re-litigate. **Read this before changing anything.**
- `CONTINUE.md` — open items and where to pick up
- `HANDOFF-PROMPT.md` — paste-ready brief for a downstream data consumer
- `PAGINATION-BUG.md` — bug report for the EU OSS Catalogue, ready to send
- `sources.py` · `replaces.json` · `translations/` — the curated inputs
- `catalog.json` · `liveness.json` · `history.json` — the data products

## Licence

Two different things, two different terms:

- **Code** — MIT. See [`LICENSE`](LICENSE).
- **The compilation** (normalisation, translation, categorisation, dedupe, liveness,
  procurement mappings) — CC BY 4.0. See [`LICENSE-DATA`](LICENSE-DATA).
- **The entries themselves** are *not* ours to relicense. Each describes software published
  by an upstream catalogue under that catalogue's own terms, which differ by country. Every
  entry carries `source` and, where one exists, `entry_url` linking back to the upstream
  record. Check those terms before redistributing entry content at scale.

If you maintain a catalogued project or a source catalogue and something here is wrong,
misattributed, or should not be included — open an issue. Removal requests from publishers
are honoured.
