# A demand-side catalogue

> Proposal, not a decision. Should govoss gain a second catalogue — the **proprietary
> software governments actually buy** — harvested from procurement data, and should that
> become what powers matching instead of the hand-seeded `replaces.json`?
>
> Written 2026-08-13 after joining NYC's software licence export against the catalogue.
> **Read `CLAUDE.md` first**, particularly the `replaces.json` section and the four
> recurring bugs. This note assumes them.

## The short version

Yes, but **not as a catalogue of proprietary software** — as a catalogue of *procurement
evidence*, harvested from contract data the way the open source side is harvested from
government catalogues. It **re-founds `replaces.json` rather than replacing it**, because
the edge between the two catalogues stays a human judgement no dataset asserts.

There is one untested assumption that decides the whole thing. It is in *The go/no-go* below.

### Correction, 2026-08-13: it lives HERE, not in a sibling repo

An earlier draft of this note recommended a sibling repo. **That was wrong, and the
argument was sloppy.** It conflated two things and only defended one:

- **(A) proprietary products as browsable, first-class objects.** This is unambiguously
  part of this app. `by-product.json` already existed, the README already framed the
  catalogue as answering the question from an invoice line, and the catalog page already
  had a *Replaces a paid product* filter. A product view was the missing half of a feature
  that was already half-built — and the half a buyer actually starts from.
- **(B) harvesting contract data across jurisdictions.** The identity-and-maintenance
  argument was about this, but was stated as though it covered (A) too.

And on (B) the framing was still off: this repo already ingests 17 external sources, so an
eighteenth *kind* of source is not a category break. What would be a break is govoss
becoming responsible for *maintaining* procurement data.

The decisive argument is one the sibling-repo framing missed entirely: **a catalogue you
cannot browse is a catalogue you cannot check.** See *What building it found* — making the
product side visible immediately surfaced five classes of defect that had been sitting in
`replaces.json` unnoticed, including one that split a product in two on the page.

**What survives:** keep *spend figures* out of the published catalogue. Use them to rank the
seed queue and prove coverage gaps, but do not make govoss a place people go to learn what
NYC spends. Databook owns that and publishes it better. The dollars stay in the analysis
layer; the product names, aliases and alternatives are catalogue content.

## Why this came up

`replaces.json` is the single hand-written artefact in a project that otherwise refuses to
hand-write anything. Every one of the 17 sources was found by locating the machine route a
catalogue's own site is built from; none was transcribed, none was scraped. The seed file is
the exception, and when asked how its entries were chosen the honest answer was: from one
person's knowledge of the software market, unverified, biased toward software that person
happens to know.

It also has no provenance. Mappings carry `product`, `vendor`, `confidence`, `kind`, `note` —
nothing recording who asserted it or on what basis. Compare `wikidata_via: comptoir:<how>`,
which exists precisely so an inferred identity is never mistaken for a publisher-asserted
one. A hand-seeded mapping and a publisher's own `publiccode.yml` declaration are
indistinguishable in the data.

Zero of the 211 mappings come from the publisher route. All of them are the seed.

## What NYC proved

`https://api.databook.nyc/oce/licenses/export` — a 385 KB CSV, no auth:

| | |
|---|---|
| Contracts | 1,601 |
| Total `current_amount` | **$1,770,420,800** |
| Distinct products | 927 (815 families) |
| Competitively bid | **6 of 1,601** |

Columns: `contract_id, family, product, purpose, agency, vendor_name, award_amount,
current_amount, start_date, end_date, expiring_before_2030, procurement_method,
competitively_bid, ai_model, unidentified_product`.

This is the artefact that makes the idea viable. Raw NYC contract records do **not** support
it — their titles read "Microsoft Premier Support" and the vendor field names a reseller
(`Kiteworks` billed by `NewBeg Inc`, `Splunk` by `KAMBRIAN CORPORATION`, `Archibus` by
`Visionaryz Inc`). Someone at Databook ran an LLM extraction over those records to produce a
clean `product` column. **The demand-side data exists because that extraction was done, not
because procurement systems publish it.** That distinction is the crux.

### The join, measured

Exact match on `product` then `family`, no substring matching:

- **194 / 1,601 rows (12%), $50,743,852 — 2.9% of spend.**

Adding three hand-verified aliases (`ArcGIS`, `ESRI ArcGIS`, `ESRI` → `ArcGIS Desktop`):

- **219 / 1,601 rows (14%), $64,213,331 — 3.6% of spend.**

Largest matched lines:

| NYC spend | Catalogue alternative |
|---|---|
| $16,144,590 Salesforce | Odoo, Dolibarr *(partial)* |
| $13,469,480 Esri ArcGIS | **QGIS** |
| $5,369,256 SAS | R *(partial)* |
| $3,915,000 Everbridge | RapidPro *(partial)* |
| $3,144,784 DocuSign | **Esup-Signature** *(strong)* |
| $2,125,475 Splunk | Graylog, Grafana, OpenSearch |
| $2,051,140 Elasticsearch | **OpenSearch** *(paid tier)* |
| $1,495,603 SolarWinds | **Zabbix, Icinga** *(strong)* |
| $1,453,452 Red Hat Enterprise Linux | **Rocky Linux** *(paid tier)* |
| $1,255,362 Zoom | **Jitsi Meet, BigBlueButton** *(strong)* |

The paid-tier rows are the cheapest wins by construction: a licence decision, not a migration.

### Two things the join got wrong, and what they teach

**Esri was a false miss worth $13.5M.** The first pass showed `Esri ArcGIS` unmatched, which
was not credible — QGIS is in the catalogue with adopters and is one of the strongest
substitutions in existence. NYC writes `ArcGIS`, `ESRI ArcGIS`, `Esri ArcGIS`, `ESRI`; the
index holds `ArcGIS Desktop`, `ArcGIS Pro`, `ArcGIS Server`, `ArcGIS Field Maps`. Exact match
failed on the bare name.

**The matching is limited by naming, not by what the catalogue holds.** That is the single
most useful finding here, and it is the strongest argument for the proposal: harvested
aliases are data, guessed aliases are a seed file.

**The $643M "Microsoft" line is not addressable and was deliberately not mapped.** It
decomposes into $573,752,896 "Microsoft ELA", $56,995,396 Unified Support, $11,544,440
Premier Support. The ELA is a bundle spanning Windows, servers and Azure; the rest are
support contracts. Mapping any of it to LibreOffice would be exactly the category error the
`kind` vocabulary exists to prevent. Across the file, **$146,157,139 (8%)** is support,
maintenance or advisory — not licences at all.

## What the unmatched 96% says

Ranked by spend, the unmatched set is dominated by software with no open source counterpart:
Axon body cameras ($112M), Intergraph 911 dispatch ($65M), NICE public-safety recording
($57M), Casebuilder investigative case management ($46M), ShotSpotter gunshot detection
($44M), Geotab telematics ($42M), Ivalua procurement ($38M), Tyler property tax ($15M).

US municipal and public-safety verticals. European government open source does not cover
them and will not. **Seeding `replaces.json` harder does not move this number.**

So the deliverable is a **gap report, not a savings report** — and that is worth building
anyway, because it says which products the seed should map next, ranked by real dollars
instead of by recall, and it says where no open source answer exists at all.

**Go in knowing the headline.** A demand-side catalogue makes the low number visible: *most
government software spend has no open source alternative, and here is precisely which parts
do.* That is a defensible and important finding. It is not a flattering one. Decide now
whether that is the story you want to be holding, because the architecture will publish it.

## What the second catalogue fixes, and what it does not

**Fixes — the vocabulary and the demand signal:**

- **Provenance as evidence.** Each product carries "seen in contract X, $Y, agency Z". That is
  the `via` field the seed lacks, sourced rather than asserted.
- **Aliases become data.** Four spellings of Esri in one jurisdiction cost $13.5M of invisible
  matches. Harvested, the variants are recorded.
- **The seed queue is ordered by dollars**, not by whoever is writing it.
- **Identity is already solved.** Wikidata covers proprietary software well — Salesforce,
  ArcGIS, Splunk all carry QIDs — and `dedupe.py` merges on QID first. The existing machinery
  transfers unchanged.
- **It answers a better question:** not "what open source exists" but "how much of government
  software spend has an open source answer".

**Does not fix — the edge.** Something still has to assert *QGIS replaces ArcGIS*, with a
`kind` and a `confidence`. No procurement dataset says that. If the second catalogue creates
the impression the judgement went away, it will do damage: the judgement is irreducible. What
it removes is **guessing which products matter**, which was the actual weakness.

## Costs

**Nobody maintains it upstream.** govoss works because 17 governments do the maintenance. A
proprietary catalogue has no such constituency, so it is viable **only** if harvested from
procurement data, which governments do maintain. The moment anyone hand-lists proprietary
products at scale, it rots and the seed file has been rebuilt with extra steps. The 79
products in `proprietary.json` are a seed against that rule, not an exception to it — they
exist to make gaps visible, and the file says so.

**It widens what govoss claims.** The identity — *union catalogue of government open source
software, harvested first-hand* — is load-bearing in these docs. Naming proprietary products
is a different kind of statement, and a wrong one is a different kind of wrong. That is the
reason for the spend-figures line above, and for `proprietary.json` carrying its NYC-shaped
bias in its own `_README` rather than in a commit message.

## What shipped, 2026-08-13

Stage 0 of the plan below, plus the browsable surface:

| | |
|---|---|
| `/products.html` + `/products.json` | `build_products.py`. 302 products with 407 alternatives, 79 with none. Cards are STATIC HTML, so deep links (`#p-dropbox`) work natively and an agent reading raw HTML gets the content. |
| `proprietary.json` | 79 products governments buy that this catalogue cannot answer — 70 software, 9 content or data. Checked in and hand-maintained; `run.sh` never touches api.databook.nyc. |
| `product_aliases.json` | 9 verified synonyms. Vendor-family and variant spellings seen in procurement records. |
| Catalog sidebar | A **Replaces** facet, most-replaceable first. Clicking filters the catalogue in place; *Show all* leaves for the products page. |
| `?rp=<product>` | Links the two pages. Ignored unless the product is a real facet value — an unknown one would filter to nothing, which reads as "no alternatives exist". |

**Proprietary software is deliberately NOT in the top nav.** It is a way *into* the open
source, not a peer of it. A nav item would misstate what this catalogue is.

## What building it found

Every one of these was invisible until the product side became browsable, which is the
argument for building it:

1. **Product-name fragmentation, self-inflicted.** The 98 mappings added on 2026-08-12 used
   more specific product names than the existing seed — `Dropbox Business` where the seed
   already had `Dropbox`, `Bitbucket Data Center` beside `Bitbucket`, `GitHub Enterprise
   Server` beside `GitHub Enterprise`. Each split one product across two index keys, so
   clicking *Dropbox* showed NextCloud but hid Seafile and ownCloud. 11 names canonicalised.
   **Check the existing product names before adding a mapping.**
2. **A stylised name split a product in two.** `</>Neighborland` and `Neighborland` were
   separate keys, so Decidim and Consul Democracy never appeared together. Caught by the
   anchor-id collision guard in `build_products.py`, which exists for exactly this.
3. **Two "products" were categories.** `case / evidence management` and `case management
   (child protection)`, vendor `various`. Nobody is billed for those, and an index keyed on
   invoice lines cannot use them. Dropped.
4. **Vendor-family names hide real matches.** Procurement records write `Atlassian`,
   `Elastic Search`, `Socrata`, `Informatica`, `OpenText`, `Alfresco`; the index writes the
   product. A first pass at `proprietary.json` therefore claimed *nothing replaces Atlassian*.
   Fixed via `product_aliases.json` — and this is the same defect class as the $13.5M Esri
   miss, which is why aliases are worth harvesting rather than guessing.
5. **Not everything unmatched is a gap.** Support contracts, advisory retainers and payment
   processing are not software licences; content subscriptions (Westlaw, LexisNexis, INRIX)
   cannot be substituted by software at all. Both are separated out, because listing them as
   unfilled gaps is the same category error `kind` exists to prevent.

Deliberately NOT merged: `Windows Server file services` stays distinct from `Windows Server`
(Samba replaces the role, not the OS), and `Elasticsearch (Elastic Licence tiers)` keeps its
parenthetical because it is the paid-tier row.

## Normalisation, and where AI belongs

Four different jobs hide under "normalise product names". They have different answers.

**1. Extraction (contract title → product).** AI, yes. Titles are wildly heterogeneous and
rules do badly. NYC already did this.

**2. Variant folding.** Mostly not a string problem. Measured on NYC: 927 distinct strings
fold to 887 on case and punctuation — **40 collapse for free (4%)**, things like
`E-builder`/`e-Builder` and `DocuSign`/`Docusign`. The residue needs world knowledge:
`Documentum` and `EMC Documentum` are one product across a corporate sale while `Liquid
Office` in the same family is not; `Microsoft ELA`, `Microsoft Premier Support` and
`Microsoft` must **not** collapse. That is LLM-shaped work and invisible-failure-prone.

**927 products is reviewable by a person.** This is not a scale problem, which settles the
architecture: the model produces a *reviewable draft*, never a runtime answer.

**3. Identity across jurisdictions.** Wikidata QID, not the model's opinion. Ask it for the
QID, then verify the QID resolves and its label matches — that converts an unfalsifiable
guess into a checkable claim.

**4. The `replaces` edge.** Human. A model will produce fluent, plausible mappings all day,
and this is the one place where wrong costs money and is hardest to detect.

### Rules for the AI layer

Copy the translation pattern exactly — it is the precedent in this repo and it works:
`sha1(source_text)[:10]` keys, cached to disk, original preserved in `desc_src`, output marked
`translated: true` so it is never confused with a publisher's own English.

- **Offline, cached, keyed on input hash — never in the pipeline path.** Not stylistic:
  committed JSON here is deterministic on purpose (week-over-week churn fell 50,199 → 2,365
  lines). A model call inside the pipeline reintroduces exactly the nondeterminism that cut
  bought, and `git log -p` stops answering "what changed this week".
- **Mark provenance** — `via: ai:<model>`, never blended with harvested or human assertions.
- **Ground to a QID** wherever possible.
- **Never let it decide a merge.** Angular `Q28925578` / AngularJS `Q2849803` is the standing
  rule. It was re-proved during this analysis: a five-line substring check matched
  `PCIS ClaimsVISION` to `Visio`.
- **Verify against content, not the queue.** The translation bug reported 100% coverage while
  72 Finnish descriptions sat untranslated. A normaliser reporting 927/927 resolved says
  nothing about whether `Liquid Office` was wrongly folded into `Documentum`.

### Do not treat NYC's product column as canonical

It is LLM-extracted by **two different models** — `gemini-3.1-flash-lite` on 1,400 rows,
`gemini-3.5-flash` on 201 — so row-to-row consistency is not guaranteed upstream. Keep the raw
string and normalise independently.

Their `unidentified_product` flag is worth copying: **31 honest failures rather than 31
confident guesses**, the same discipline as treating an unmapped taxonomy value as a bug
rather than bucketing it into "other".

## The go/no-go

**The untested assumption: that product-level licence data generalises beyond NYC.**

NYC's export may be bespoke. If other jurisdictions publish only vendor-level contract data —
which is what NYC itself looked like before the extraction — then this is not a catalogue, it
is an NYC report wearing a catalogue's clothes.

This was not verified. The Portland OCDS connector was the intended test and returned
`permission denied for table tenders` on every call.

**Stage 0 — DONE 2026-08-13.** NYC treated as a single source; the no-alternative list is
published on `/products.html` and the matched side is browsable. See *What shipped*.

**Stage 1 — the go/no-go.** Get **one** more jurisdiction with product-level licence data and
check whether product names normalise across the two. A day's work, not a project. If two
jurisdictions cohere it is a catalogue; if they do not, building one has been avoided.

**Stage 2 — build, only if Stage 1 passes.** Harvest pipeline, QID-keyed identity, aliases as
data, and `replaces.json` narrows to edges-only against a harvested vocabulary.

## Not decided here

- **Stage 1 has not run.** Whether product-level licence data generalises beyond NYC is still
  the open question, and everything past Stage 0 depends on it.
- Whether the NYC CSV should be vendored. Recommendation is **no** — it is NYC's to publish and
  the export URL is the durable reference. `proprietary.json` is the checked-in derivative.
- How far to take alias harvesting. Nine are recorded; the remaining unmatched families are a
  worklist, and each one converted is spend that moves from "no answer" to "answered". This
  carries no curation risk — synonyms are verifiable, unlike the `replaces` edge.
- Whether the facet count and the product page should agree exactly. They differ by design
  today: the facet counts *entries* the filter will show (Confluence 7), the product page
  counts *distinct software* after by-product.json collapses same-named rows (Confluence 6).
  Both are right in context, but a reader comparing the two surfaces will notice.
