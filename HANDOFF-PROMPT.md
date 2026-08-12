The European public-sector open source catalogue has grown substantially since you last
used it, and several numbers you may have published from it are now wrong. Everything
below is live at https://govoss-catalog.vercel.app — static JSON, CORS-open, no auth.

**If you kept anything from the previous handoff: it said 1,995 entries from 8 catalogues.
It is now 3,063 entries from 17 catalogues across 14 countries plus a global registry.**

## What changed that affects your conclusions

1. **`replaces` coverage nearly doubled and now answers three questions you got zero
   results for.** 108 entries map to **165 proprietary products** (was 87 → 95). Critically:

   | you reported empty | now resolves to |
   |---|---|
   | SMS / mass notification ($900K) | **GOV.UK Notify** (strong), **RapidPro** (partial) |
   | mobile field data collection ($278K) | **CommCare, KoboToolbox, ODK** (all strong) |
   | digital signage ($86K) | **OS2Display** (strong, Danish municipal) |
   | social media scheduling ($902K, Hootsuite) | **still effectively empty** — Mautic is mapped `adjacent` only |

   The first three were empty because the catalogue lacked the *sources*, not because no
   European alternative existed. Adding the Digital Public Goods registry and OS2 Denmark
   filled them. Hootsuite remains a genuine gap — Mautic does campaigns and automation, it
   does **not** schedule social posts, and it is deliberately marked `adjacent` with a note
   so it is not mistaken for closing that gap.

2. **New high-value mappings worth re-running your inventory against:** VMware vSphere →
   Proxmox, DocuSign → Esup-Signature, Lansweeper/Track-It! → GLPI, Visio → Draw.io,
   Microsoft Project → GanttProject/OpenProject, Panopto/Kaltura → Esup-Pod, Doodle →
   Framadate, MindManager → Freeplane, Snagit → Greenshot, Airtable → Grist,
   NAVEX EthicsPoint → GlobaLeaks, Formstack → OS2Forms/GOV.UK Forms.

3. **More `paid-tier` finds — your ~$385K category.** Docker Desktop → Docker,
   Red Hat Enterprise Linux → Rocky Linux, MySQL Enterprise → MariaDB, GitLab Premium →
   GitLab CE, Metabase Pro → Metabase, Nagios XI → Icinga. These are usually the cheapest
   wins: often no migration, just a renewal you stop.

4. **Entry counts changed again — dedupe got much better.** A Comptoir du Libre crosswalk
   now stamps Wikidata QIDs onto entries that lacked them, which lifted merges from 156 to
   **241** and multi-catalogue entries from 46 to **105**. If you counted "how many options
   exist", recount.

## New field you will want: `catalogue_count` + `catalogues[]`

How many **distinct national catalogues** list this software, with a deep link into each
one's own record. This is the strongest independent-adoption signal in the dataset — far
better than stars.

```python
import json, urllib.request
E = json.load(urllib.request.urlopen("https://govoss-catalog.vercel.app/entries.json"))
strong = [e for e in E if e["catalogue_count"] >= 3]     # 23 entries
```

LibreOffice and QGIS are listed by **5** catalogues each; Drupal, GitLab, Matomo and
NextCloud Server by 4. Three or more governments independently cataloguing the same tool is
a much better procurement signal than any single listing.

## Endpoints (unchanged, plus two)

    GET /entries.json              3,063 entries, structured fields
    GET /meta.json                 category enum, sources, counts, known gaps
    GET /by-product.json           inverted index: proprietary product -> alternatives
    GET /by-category/<key>.json    one file per functional category
    GET /sources.json              NEW — the 17 catalogues, plus 13 surveyed and rejected
    GET /status.json               NEW — freshness, per-source counts, change log
    GET /v1/entries.json           versioned alias
    GET /llms.txt                  how to use all of it

`/api/entries`, `/api/catalog`, `/catalog.json` and `/data.json` still redirect to
`/entries.json`.

## The 17 catalogues now

France (SILL + awesome-codegouvfr), Italy (Developers Italia), Germany (openCode + **Munich**),
**Denmark (OS2)**, **Bulgaria (e-Government Ministry)**, Belgium (iMio), Sweden (Offentligkod),
Netherlands (code.overheid.nl), **Portugal (ARTE)**, Canada (Open Resource Exchange),
**Taiwan (moda)**, Finland (Avoinkoodi), **Ireland (OGCIO)**, EU institutions, and the
**global Digital Public Goods registry**.

Bold = new since your last handoff. Note the DPG registry uses a **wider criterion**: DPGs
are vetted for SDG relevance and many are NGO- or university-built rather than
government-published. They carry `dpg: true` and country `GLOBAL`, so filter them out if
your question is strictly "what do governments publish".

## Provenance to carry into anything you publish

- **1,608 of 2,745 descriptions (59%) are machine translations** from German, Italian,
  French, Dutch, Danish, Portuguese, Finnish, Swedish and Chinese. Each carries
  `translated_from` and `description_original`. Do not present them as publisher wording.
- **171 Bulgarian descriptions are NOT translated** and remain in Cyrillic. Deliberate: they
  are mostly long EU-funding project titles rather than software summaries. `description_lang`
  will say `bg`.
- `categories_inferred: true` means the category came from keyword rules, not the publisher.
- `wikidata_via: comptoir:*` means the QID was inferred from a crosswalk, not asserted upstream.
- **102 entries are filtered out** of `entries.json` as not-adoptable software: forks of
  upstream projects, CI plumbing, deployment recipes, locale bundles.
- `link_dead` is true for 24 entries, confirmed over two consecutive checks.
- `generated_at` in `/meta.json` is the build time, and the weekly run now publishes itself,
  so build time and deploy time track each other. A run with any failed step publishes
  nothing, so a `generated_at` that has stopped moving means the pipeline broke, not that
  someone forgot to deploy — `/status.json` says which step.

## Still worth knowing

`/sources.json` now carries a `survey` array of **13 catalogues checked and rejected**, with
the reason — US code.gov is retired, India's OpenForge publishes no code, Korea's oss.kr is a
promotion portal, Spain's CTT is behind a CAPTCHA, Cyprus has no code platform at all. If you
are asked "why isn't country X in here", that array is the answer.

Highest-value thing you could contribute back is still **more `replaces` mappings**. You have
the invoice side, which is the half this catalogue cannot see — and the three gaps closed
above only got closed because you reported them as empty.
