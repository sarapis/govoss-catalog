The European public-sector open source catalogue you scraped now has a JSON API. Stop
driving the browser — you no longer need it, and the data you were working from was
partly wrong.

## Base

    https://govoss-catalog.vercel.app

All JSON is static, CORS-open (`Access-Control-Allow-Origin: *`), no auth, no rate limit.
The human page is still at `/` and unchanged.

| endpoint | what it gives you |
|---|---|
| `GET /entries.json` | all 1,995 entries, structured fields, one array (2.9 MB) |
| `GET /meta.json` | 19 category enum, sources, licences, counts, `generated_at`, known gaps |
| `GET /by-product.json` | **inverted index: proprietary product -> alternatives** |
| `GET /by-category/<key>.json` | one file per category; keys from `/meta.json` |
| `GET /v1/entries.json` | versioned alias — pin this if a schema change would break you |

The eight paths you probed and got 404 from now work: `/api/entries`, `/api/catalog`,
`/catalog.json` and `/data.json` all redirect to `/entries.json`.

## Your procurement task, rewritten

`/by-product.json` is keyed by proprietary product name and is exactly the
`POST /api/match` you asked for, precomputed. Two GETs answer your whole inventory:

```python
import json, urllib.request
bp = json.load(urllib.request.urlopen("https://govoss-catalog.vercel.app/by-product.json"))

for product in your_948_contract_lines:
    for alt in bp.get(product, []):          # [] is a real answer, see "Absence" below
        print(product, "->", alt["name"], alt["confidence"], alt["kind"], alt["adopters"])
```

Verified: a 17-line inventory resolved in **0.2 s over 2 requests**, replacing your ~35
browser searches. Sample output:

    SurveyMonkey      -> LimeSurvey        strong  software   18 adopters
    IssueTrak         -> Zammad            strong  software    4
    GoToMyPC          -> RustDesk          strong  software    5
    ArcGIS Desktop    -> QGIS              strong  software   69
    Blackboard        -> Moodle            strong  software   30
    Elasticsearch     -> OpenSearch        strong  paid-tier   4
    Hootsuite         -> (no match)

## Read `kind` before you report a saving — it will stop you making a category error

- `software` — replaces the software.
- `service` — the paid item is **hosted service or content**, not software. Drupal does
  not replace *Pantheon hosting*; Moodle does not produce *LinkedIn Learning content*.
  Your earlier flagging of Pantheon/WP Engine ($496K) and LinkedIn Learning/Pluralsight/
  GO1 ($416K) as replaceable is wrong for this reason, and these are marked `service`
  precisely so the next pass does not repeat it.
- `paid-tier` — the paid item is a **commercial edition of software that is already open
  source**. Your ~$385K finding. NGINX Plus, Elastic licence tiers, DBeaver PRO, MySQL
  Enterprise, Nagios XI. Usually the cheapest win available: often no migration at all,
  just a renewal you stop.

`confidence` is `strong` | `partial` | `adjacent`. Do not treat `adjacent` as a saving.

## Coverage limits — please read, they bound your conclusions

`replaces` currently covers **73 of 1,995 entries → 95 proprietary products**. It is
hand-seeded, partial, and openly non-authoritative. **An empty array means "not mapped",
not "no European alternative exists."** For unmapped inventory lines, fall back to
`/entries.json` + `/by-category/<key>.json` and match on `description` / `categories`.

Also note: `licence_spdx` is `null` for ~500 entries where the upstream string was not a
real SPDX id (`"GPLv3+"`, `"MIT licence"`). That is deliberate — a null beats a wrong id
in a field consumers will trust. Use `licence` for the raw string.

## Four data corrections that affect numbers you already published

1. **The catalogue was deduplicated: 2,122 → 1,995 entries.** You saw Matomo,
   `cadddy-jwt` and "Document Writing CI Components" twice; you were right. 127 rows
   collapsed across 84 groups. If you counted "how many options exist" from the old
   data, those counts were inflated. Merged rows now carry `merged_from`, `countries[]`,
   `sources[]` and `also_known_as[]` — Ansible is one row asserting `["FR","SE"]`.

2. **58 entries were filtered out as not-adoptable software** and are absent from
   `entries.json`: 30 forks of upstream projects (`ZODB`, `zope.sendmail`,
   `Products.CMFEditions`), plus CI plumbing, buildout deployment recipes and locale
   bundles. If your scrape included "ZODB" as Belgian public-sector software, drop it.

3. **`link_dead` is now per-entry** (22 true), not just an aggregate. Filter on it.

4. **`adopters` is a sortable integer**, with `adopter_names[]` alongside. You identified
   this as the best trust signal for a government buyer; it is no longer buried in prose.

## Absence is a finding — please report it as one

`/meta.json → known_gaps` records categories where the European commons appears to have
nothing: social media scheduling (your Hootsuite $902K), SMS/mass notification ($900K),
mobile field data collection ($278K), digital signage ($86K). Those zeros are a real
result about where the gaps are, not a failure of the catalogue. Worth stating explicitly
in your output rather than dropping.

## Provenance you should carry into anything you publish

- ~74% of descriptions (1,486 of 1,941) are **machine translations** from German,
  Italian, French, Finnish and Swedish. Each carries `translated_from` and
  `description_original`. Do not present them as publisher wording.
- `categories_inferred: true` (~23% of entries) means the category was inferred from
  text by keyword rules, not declared by the publisher.
- `generated_at` in `/meta.json` is the build time. The harvest runs Mondays 07:00 ET;
  the JSON is regenerated then but **redeployment is currently manual**, so `generated_at`
  is the honest freshness signal — trust it over the deploy date.

## If something is missing or wrong

The catalogue is built from eight national sources (Developers Italia, SILL,
openCode.de, iMio, Offentligkod, Avoinkoodi, awesome-codegouvfr, code.europa.eu).
Netherlands is pending an API key; Ireland, Portugal and Cyprus have no machine route
yet. The EU's own aggregate catalogue is deliberately not used as a source — its pager,
facets and search all ignore query strings, so only 20 of its 1,084 solutions are
reachable.

Highest-value contribution you could make back: **more `replaces` mappings**. You have
the invoice side of the problem, which is the half this catalogue cannot see.
