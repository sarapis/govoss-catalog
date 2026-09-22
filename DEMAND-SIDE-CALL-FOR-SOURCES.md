# Wanted: governments that publish what software they actually use

> A shareable brief, written 2026-09-21. The internal analysis and the decision it
> serves are in `DEMAND-SIDE-CATALOGUE.md`; **this file is the version to send to
> someone who might know of a source.** Keep it standalone — assume the reader has
> never heard of govoss.

## The ask, in one sentence

**We are looking for governments that publish, as data, a list of the software
products they actually run or license — at the level of the product name, not the
vendor or the contract.**

We have exactly one. We need a second to know whether the first was a fluke.

## Why the product name is the whole thing

[govoss-catalog](https://govoss-catalog.vercel.app) is a union catalogue of
government **open source** software: 2,857 entries harvested first-hand from 17
national, municipal and international catalogues across 15 countries. That side
works, because 17 governments maintain it for us.

The question it cannot answer is the one a public buyer actually starts from:
*we spend money on this proprietary product — is there a public-sector-proven open
source alternative?* Answering that needs the other half of the shelf: **what
governments are actually running.**

New York City turns out to publish it. `api.databook.nyc/oce/licenses/export` is a
385 KB CSV, no authentication, one row per software contract:

```
contract_id, family, product, purpose, agency, vendor_name, award_amount,
current_amount, start_date, end_date, expiring_before_2030,
procurement_method, competitively_bid, ai_model, unidentified_product
```

1,601 contracts. $1.77bn. 927 distinct products. **Six of the 1,601 were
competitively bid.**

That `product` column is the entire reason this is usable — and it is also the
reason we are asking for help rather than just harvesting more. **Raw procurement
records do not contain it.** NYC's own underlying contracts read *"Microsoft
Premier Support"*, and the vendor field names a reseller: Kiteworks billed by
*NewBeg Inc*, Splunk by *KAMBRIAN CORPORATION*, Archibus by *Visionaryz Inc*.
Someone at NYC's Databook project ran an extraction over those records to produce a
clean product column.

So the honest position: **the data we need exists in one city because somebody did
that work, not because procurement systems publish it.** If that is true
everywhere, this is an NYC report, not a catalogue. If two jurisdictions cohere, it
is a catalogue. That is the whole question.

## The 30-second test

Open the dataset. Pick any row. **Can you tell which software product it is for,
without guessing?**

| ✅ qualifies | ❌ does not |
|---|---|
| `product: ArcGIS Desktop` | `title: GIS Software Maintenance Agreement` |
| `product: Splunk Enterprise` | `vendor: KAMBRIAN CORPORATION` |
| An application register naming *Nextcloud*, *SAP*, *Matomo* | A tender notice for "IT consultancy services" |
| One row per product or per licence | One row per framework agreement covering everything |

If the product name is recoverable only by inference from a contract title, it is
the NYC *raw* case — interesting, but it needs the extraction step, and that is the
cost we are trying to find out whether we can avoid.

## Two genres, and the second is better

**1. Procurement or licence exports** — what was bought. This is the NYC shape.
Often lives with a transparency or open-data team, sometimes released under FOI.

**2. Application portfolio registers** — what is actually *run*. A government
listing its own application landscape: system name, the software behind it, the
owning department, sometimes lifecycle status.

**We would rather have the second**, for a reason that matters more than
convenience: it is maintained by its publisher as part of running their IT estate.
Procurement exports that need an extraction step make *us* responsible for
generating the data, and a catalogue nobody maintains upstream rots. Everything
that works about the open source side of govoss works because the publisher
maintains it.

### Terms worth searching, since these registers are rarely called the same thing twice

- **EN** — application portfolio · application landscape · software inventory ·
  IT asset register · licence register · software catalogue · systems inventory
- **NL** — applicatielandschap · applicatieportfolio · softwarecatalogus
- **DE** — Anwendungslandschaft · Applikationsportfolio · Softwareverzeichnis ·
  IT-Bestandsverzeichnis
- **FR** — cartographie applicative · portefeuille applicatif · inventaire logiciel
- **IT** — catalogo applicativi · censimento del patrimonio ICT
- **ES** — catálogo de aplicaciones · inventario de software
- **DA / SV / NO** — applikationsportefølje · applikationsportfölj ·
  applikasjonsportefølje

Municipal associations and shared-service organisations are a good place to ask:
they often hold this centrally for many authorities at once. Denmark's OS2 and the
Dutch and German municipal IT cooperatives are the kind of body that would know.

## What we would do with it

Join it against the open source catalogue on product identity and publish the
result. Be warned what the result looks like — we have measured it on NYC, and it
is not a savings pitch:

- **3.6% of NYC's software spend has an open source alternative in the catalogue**
  (219 of 1,601 contracts, $64.2m of $1.77bn).
- The **matching is limited by naming, not by coverage.** `Esri ArcGIS` first
  showed as unmatched — a **$13.5m false miss** — because NYC writes `ESRI` and the
  catalogue holds `ArcGIS Desktop`. Three verified aliases fixed it. Harvested
  aliases are data; guessed ones are a seed file, which is why more jurisdictions
  beats more guessing.
- The unmatched 96% is dominated by software with **no open source counterpart and
  no prospect of one**: body cameras ($112m), 911 dispatch ($65m), public-safety
  recording ($57m), gunshot detection ($44m), fleet telematics ($42m).

So the deliverable is a **gap report, not a savings report**: *most government
software spend has no open source alternative, and here is precisely which parts
do.* We think that is the more useful finding, and we would rather say it plainly
up front than have anyone help us on a false premise.

There is also a directly practical output. Ranked by real money rather than by
guesswork, it says which products an alternatives catalogue should cover next.

## What we already have, for context

govoss carries publisher-declared adopters on **1,294 of 2,857 entries, naming
9,946 distinct public bodies**. That is the closest existing signal, and it is the
wrong shape for this: it is un-normalised, skews national rather than municipal,
and says who adopted the *open source*, never what they pay for instead.

## If you know of one

Send the URL, or the name of the team that would hold it. A single dataset is
enough — we do not need a programme, a partnership or an introduction. If it turns
out to be vendor-level only, that is still a useful answer, and we will record it
as checked so nobody repeats the search.

Everything govoss holds is CORS-open static JSON, no key, no rate limit:
`govoss-catalog.vercel.app/entries.json`, with provenance and build health at
`/sources.html`.

---

*Status: Portland, Oregon's OCDS database was the intended second jurisdiction.
Every query returns `permission denied for table tenders` — retried 2026-09-21,
still blocked. If you have access to that database, you are one grant away from
answering this.*
