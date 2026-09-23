# UK curated list - DRAFT, on the backburner

**Status: parked 2026-09-23. Not a source, not wired into anything.** The owner's
direction: govoss ingests government-produced catalogues only, not lists of our own.
This file keeps the work so it can be picked up if that changes, or if a UK body
publishes a catalogue these could be checked against.

## Why a list at all (measured 2026-09-23)

GitHub's `github/government.github.com` `_data/governments.yml` names 215 UK orgs
(169 "U.K. Central", 46 "U.K. Councils"; 2 now 404, 33 with no active repos).

- **14,320** active non-fork repos (central 13,781, councils 539) - ~4.7x the whole
  catalogue. hmrc alone: 1,499 repos, 26 described.
- **0 `publiccode.yml`** in all 14,320 (raw HEAD of both spellings; positive control
  200 on `italia/18app`, `kiesraad/abacus`; code search agreed for alphagov, MoJ,
  hmrc, GCHQ before rate-limiting).
- Stars do not separate products: >=50 stars is 110 repos, about half guidance,
  posters or infrastructure, while Notify (75), Pay (49) and Forms (69) sit near or
  under the line.
- **No UK software register exists.** The only first-hand machine route is the GOV.UK
  Content API for the Service Toolkit, `https://www.gov.uk/api/content/service-toolkit`:
  six products (Design System, Prototype Kit, Notify, Pay, One Login, Forms), naming
  services, not repos.
- **0 UK repos in the catalogue today**, but UK-derived software already is: Canada's
  `cds-snc/notification-api` and Taiwan's `moda-gov-tw/notifications-admin`,
  `alphagov.forms-admin`, `alphagov.forms-product-page`. None is a GitHub fork, so
  linking them would need `variants.json` rows, which need the UK cores present.

Stars and last push below are from that measurement. Kind follows the catalogue's
own distinction: `variants.py` never resolves a variant to a `library` core.

## A. Products a government could adopt and run (24)

| # | repo | kind | stars | licence | why |
|---|---|---|---|---|---|
| 1 | `alphagov/notifications-api` (+ `notifications-admin`) | platform | 75 | MIT | GOV.UK Notify; Service Toolkit; already re-used by Canada and Taiwan |
| 2 | `govuk-pay/pay-publicapi` (+ `pay-frontend`, `pay-selfservice`) | platform | 49 | MIT | GOV.UK Pay; Service Toolkit |
| 3 | `govuk-forms/forms-admin` (+ `forms-runner`) | platform | 21 | MIT | GOV.UK Forms; Service Toolkit; re-used by Taiwan |
| 4 | `alphagov/govuk-prototype-kit` | tool | 338 | MIT | Service Toolkit |
| 5 | `alphagov/e-petitions` | application | 313 | MIT | Petitions service for Parliament; self-contained Rails app |
| 6 | `alphagov/signon` | application | 97 | MIT | Single sign-on for a suite of apps |
| 7 | `alphagov/tech-docs-template` | tool | 84 | MIT | Technical documentation site generator |
| 8 | `gchq/CyberChef` | application | 35,934 | Apache-2.0 | The one clear GCHQ product |
| 9 | `gchq/stroom` | platform | 487 | Apache-2.0 | Log and event processing platform; stands for its ~27 component repos |
| 10 | `gchq/Bailo` | application | 96 | Apache-2.0 | ML model lifecycle management |
| 11 | `gchq/sleeper` | platform | 107 | Apache-2.0 | Serverless key-value store |
| 12 | `gchq/LD-Explorer` | application | 26 | Apache-2.0 | Linked-data explorer |
| 13 | `UKGovernmentBEIS/inspect_ai` | framework | 2,850 | MIT | AI Security Institute's LLM evaluation framework |
| 14 | `UKGovernmentBEIS/control-arena` | framework | 241 | MIT | AISI AI-control evaluation settings |
| 15 | `digital-preservation/droid` | application | 393 | BSD-3-Clause | National Archives file-format identification, widely used by archives |
| 16 | `digital-preservation/csv-validator` | tool | 225 | MPL-2.0 | National Archives CSV schema validator |
| 17 | `nationalarchives/miiify` | application | 48 | MIT | Web annotation server |
| 18 | `dstl/Stone-Soup` | framework | 659 | MIT | Dstl target-tracking framework |
| 19 | `wmfs/tymly` | framework | 121 | MIT | West Midlands Fire Service digital-services framework |
| 20 | `dwp/govuk-casa` | framework | 40 | ISC | DWP framework for collect-and-submit services |
| 21 | `i-dot-ai/consult` | application | 62 | MIT | i.AI consultation-response analysis |
| 22 | `i-dot-ai/minute` | application | 37 | none | Meeting transcription and minuting; **no licence detected - check first** |
| 23 | `department-for-transport-BODS/bods` | application | 65 | none | Bus Open Data Service; **no licence detected - check first** |
| 24 | `Dorset-Council-UK/GIFramework-Maps` | application | 23 | MIT | Council .NET web map; the one council product found |

## B. Components and libraries (16) - index well, but never variant cores

| # | repo | stars | licence | why |
|---|---|---|---|---|
| 25 | `alphagov/govuk-frontend` | 1,458 | MIT | GOV.UK Design System code; Service Toolkit |
| 26 | `alphagov/accessible-autocomplete` | 954 | MIT | Accessible component, used well beyond the UK |
| 27 | `nhsuk/nhsuk-frontend` | 683 | MIT | NHS design system code |
| 28 | `nhsuk/nhsuk-prototype-kit` | 76 | MIT | NHS prototype kit |
| 29 | `ministryofjustice/moj-frontend` | 58 | MIT | MOJ Design System |
| 30 | `UKHomeOffice/design-system` | 83 | none | Home Office Design System; **no licence detected** |
| 31 | `scottish-government-design-system/design-system` | 46 | MIT | Scottish public-sector design system |
| 32 | `ONSdigital/design-system` | 42 | MIT | ONS Design System |
| 33 | `UKHomeOffice/keycloak-theme-govuk` | 144 | MIT | GOV.UK theme for Keycloak |
| 34 | `moj-analytical-services/splink` | 2,425 | MIT | Probabilistic record linkage |
| 35 | `moj-analytical-services/uk_address_matcher` | 75 | MIT | UK address matching |
| 36 | `i-dot-ai/themefinder` | 93 | MIT | Topic modelling for consultation responses |
| 37 | `wmfs/statebox` | 45 | MIT | Amazon States Language workflow engine |
| 38 | `ukaea/PROCESS` | 71 | MIT | Fusion power-plant systems code |
| 39 | `metomi/rose` | 69 | GPL-3.0 | Met Office application-configuration toolkit |
| 40 | `ONSdigital/gptables` | 46 | NOASSERTION | Good-practice statistical tables |

## Considered and left out

- `gchq/Gaffer` (1,787 stars) - **archived**.
- GOV.UK One Login (`govuk-one-login/*`) - Service Toolkit product, but
  `authentication-frontend` carries no licence and the product is spread over ~160
  repos with no obvious entry point. Needs a human to name the repo.
- `alphagov/whitehall`, `router`, `publishing-api`, `frontend` - GOV.UK's own
  publishing stack, not something another government would run on its own.
- `DEFRA/digital-form-builder` - last pushed 2024-09; the active fork lives under
  `XGovFormBuilder`, which is not in the government list.
- Guidance, standards and papers: `UKHomeOffice/posters`, `ukncsc/zero-trust-architecture`,
  `gchq/BoilingFrogs`, `alphagov/gds-way`, `alphagov/guide-to-wcag`, the
  `*-technical-guidance` repos.
- Infrastructure: `ministryofjustice/modernisation-platform`, `cloud-platform*`,
  `alphagov/govuk-infrastructure`, `UKHomeOffice/vault-sidekick`, `aws-root-account`.
- Data and dashboards: `UKHSA-Internal/coronavirus-dashboard*`, `edinburghcouncil/datasets`,
  `i-dot-ai/awesome-gov-datasets`.
- Analyst packages (R/Python for internal reporting): `NHSRplotthedots`,
  `FunnelPlotR`, `phsmethods`, `aftables`, `govcookiecutter`. Arguably libraries;
  left out to keep the list to things with users outside the publishing team.

## If this is picked up

- It would be the catalogue's first source that is govoss's own selection. It needs
  its own tier and a visible "curated by govoss, not a government catalogue" note on
  `/sources.html`, `sources.json` and `llms.txt`.
- The Service Toolkit's six products are the only part with a first-hand machine route.
- Add `variants.json` rows for Notify (CA, TW) and Forms (TW) in the same change.
- Re-check licences for rows marked none, and re-measure stars/pushes - this is a
  snapshot.
