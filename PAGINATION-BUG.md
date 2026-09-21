# Bug report: EU Open Source Solutions Catalogue — all query parameters ignored, 98% of solutions unreachable

**Affected URL:** https://interoperable-europe.ec.europa.eu/eu-oss-catalogue/solutions
**Tested:** 2026-08-10, ~14:00–14:40 UTC · **re-verified 2026-09-20, still present**
**Severity:** High — 1,064 of 1,084 catalogued solutions cannot be reached by any public route
**Reporter's interest:** building a first-hand harvester of national public-sector OSS catalogues; found this while evaluating whether to syndicate the EU catalogue instead

---

## Re-verified 2026-09-20 — still present, 41 days later

Re-run before sending. The defect is unchanged, and one new observation
strengthens it.

| request | result |
|---|---|
| `?page=3` | byte-identical response to the unparameterised page (254,606 bytes) |
| `?page=54` | byte-identical |
| `?oss_keys=nextcloud` | byte-identical |
| `?oss_keys=zzzznomatch` | byte-identical |
| `?cachebust=<random>` | **byte-identical** |

The set of solution links returned is the same for all six requests, compared
as sorted sets. The cache-buster returning an identical body again rules out
CDN caching: a URL never requested before still yields page 1.

**The catalogue is actively maintained while this persists.** Page 1's contents
have changed since August — it opened with `ciso-assistant`,
`easywebsite-markdown-webbook`, `elementpath`, `form-designer` and now opens
with `bytype`, `ciso-assistant`, `core-ux-mkdocs`, `design-sito-ict`. New
solutions are being added and published; they are simply unreachable once they
fall past the first page.

`sitemap.xml` is also unchanged in the relevant respect: 10,000 URLs across the
first five sitemap pages, **zero** of them `/eu-oss-catalogue/solutions/*`.

⚠ **Correction: the page serves 16 solutions, not 20.** Counted with a permissive
pattern against every `/eu-oss-catalogue/solutions/<slug>` href on the page, all
16 resolving to real slugs (`bytype`, `ciso-assistant`, `core-ux-mkdocs`,
`design-sito-ict`, `firma-con-io`, `forsakringskassans-designsystem`, `io`,
`odf-kit`, `one-identity`, `opencity-italia-la-stanza-del-cittadino`, `pleio`,
`publicodes`, `qfield`, `recommandations-collaboratives`, `semantic-mediawiki`,
`valtimo`). Everything below saying "20 solutions" is wrong, and the
`1,064 = 1,084 − 20` arithmetic in the header inherits the error. Either the page
size changed since August or the original count was mistaken; this pass cannot
distinguish those. **State the mechanism, not the arithmetic** — see below.

*Not re-confirmed today:* the total of 1,084. The page renders its result count in
a form widget that resisted plain-text extraction on this pass, so treat 1,084 and
the derived "1,064 unreachable" as of 2026-08-10 only.

**What IS re-confirmed is the mechanism**: every query string collapses to the same
response, so only the first page is reachable by any route. That claim needs
neither total and is the substance of the report. Lead with it.

---

## Summary

Every query string on the catalogue's browse page is ignored. Pagination, facet
filters, keyword search and sort all return the identical first page of 20
unfiltered results. Because solution pages are also absent from the sitemap,
there is no remaining route — UI, URL, crawler or API — to the other 1,064
solutions.

A second, independent check suggests the problem is not limited to this
route: the portal-wide search at `/search` also ignores its `keys` parameter.

## Steps to reproduce

```bash
curl -s 'https://interoperable-europe.ec.europa.eu/eu-oss-catalogue/solutions?page=3' \
  | grep -o 'title="Current page".\{0,80\}'
```

Expected: page 4 active, solutions 61–80.
Actual: `Current page … 1`, solutions 1–20.

## Observed behaviour

| Request | Expected | Actual |
|---|---|---|
| `?page=3` | solutions 61–80 | page 1, same 20 solutions |
| `?page=54` (last) | final page | page 1, same 20 solutions |
| `?f[0]=category:accessibility` | filtered subset | **1084 results**, same 20 |
| `?oss_keys=nextcloud` | Nextcloud | **1084 results**, same 20 |
| `?oss_keys=zzzznomatch` | **0 results** | **1084 results**, same 20 |
| `/search?keys=zzzznomatch` | 0 results | **16426 results** |

The set of 20 solution links returned is byte-identical across all of the
above (compared as sorted sets; alphabetically first are `ciso-assistant`,
`easywebsite-markdown-webbook`, `elementpath`, `form-designer`).

## What has been ruled out

- **Not CDN caching.** Forcing a cache miss with a unique parameter still
  returns page 1. Response headers on that request:
  `x-cache: Miss from cloudfront`, `x-age: 57`,
  `cache-control: public, max-age=300, s-maxage=300`,
  `vary: Cookie,Accept-Encoding`. The request reached the origin and the
  origin returned page 1.
- **Not the client.** Reproduced in a real browser (Chromium). Navigating
  directly to `?page=3` shows "Current page 1". Clicking the "Next page"
  control changes the address bar to `?page=1` and the content does not
  change.
- **Not JavaScript-driven paging that failed to load.** The pager is a plain
  `<a href="?page=1" rel="next" class="page-link">` with no AJAX class,
  no `data-drupal-*` attributes, and no matching `views/ajax` endpoint in
  `drupalSettings`. A full page navigation is the intended mechanism.
- **Not session state.** Same result with a cookie jar established by first
  loading the unparameterised page.

## Why there is no workaround

- `sitemap.xml` (15 pages, checked all) contains **zero**
  `/eu-oss-catalogue/solutions/*` URLs. The solutions are not in the sitemap,
  so they are not discoverable by crawlers either — including search engines.
- `search_api_autocomplete/search_oss_catalogue?q=…` returns `[]` for every
  query tried (`a`, `e`, `open`).
- There is no public API: `/jsonapi`, `/jsonapi/node/solution`, `/api`,
  `/rest/eu-oss-catalogue` all return 404, and `?_format=json` returns HTML.

Individual solution pages work correctly **if you already know the slug**
(e.g. `/eu-oss-catalogue/solutions/publicodes` renders fully, with repository
URL, licence, source catalogue, vitality index and adopters). The data is
present and well-modelled. Only the routes that would let anyone enumerate it
are broken.

## Suspected cause

`drupalSettings` shows this is a Drupal `search_api` view named
`search_oss_catalogue` with facets `oss_category`, `oss_software_type`,
`oss_scope`, `oss_development_status` and `oss_source` — i.e. server-side
Views + Facets, which should honour these parameters.

The `x-age` header appears alongside CloudFront's own `x-cache`, indicating a
second cache layer in front of the origin application. The symptom — every
query string collapsing to the same rendered response — is what happens when
an anonymous page cache is keyed on **path only**, with the query string
excluded from the cache key. Drupal's own internal page cache does normally
include the query string, which points at the reverse proxy in front of it
rather than at Drupal.

That the portal-wide `/search?keys=` shows the same behaviour is consistent
with a cache-key configuration issue rather than anything specific to the OSS
catalogue view.

## Suggested fixes, in priority order

1. **Include the query string in the anonymous cache key** for at least the
   Views-backed routes. This alone should restore paging, facets and search.
2. **Add solution pages to `sitemap.xml`.** Currently the catalogue is
   invisible to search engines, which undercuts the discoverability goal the
   catalogue exists to serve.
3. **Add a regression test** asserting that
   `?oss_keys=<nonsense>` returns 0 results. The current failure is silent —
   the page looks healthy and reports a plausible total, which is why it can
   persist unnoticed.

## Related request

Please consider publishing a **public read API or bulk export** (JSON, or a
`publiccode.yml` collection). The national catalogues you federate mostly
offer one — Developers Italia has a documented REST API, code.gouv.fr
publishes bulk JSON dumps — and a machine-readable EU-level export would let
downstream users cross-check coverage instead of scraping. It would also mean
a failure like this one degrades discoverability rather than eliminating it.
