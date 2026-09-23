# Archive — incidents, in full

The reasoning behind rules that `CLAUDE.md` now states in one or two lines. Nothing
here is required reading. It is kept because a rule whose incident is forgotten
gets "simplified" back into the bug it was written to prevent, and because several
of these cost a session each to find.

`CLAUDE.md` is auto-loaded into every session and is the most expensive file in the
repo; this one is not loaded by anything. When a rule there earns a regression
test, its story belongs here and the rule keeps one line naming the test.

---

## UI incidents, 2026-09-20 to 2026-09-22

### ⚠ `el.hidden` needs `[hidden]{display:none!important}` — theme.py carries it

The `hidden` attribute hides via the UA stylesheet's `[hidden]{display:none}`, and
**any author `display:` rule outranks it.** Two elements were defeated by exactly
that, both shipped and live:

- `.drawer{display:flex}` — the More filters drawer rendered **253px tall with
  `hidden` set**, so it was open on every page load.
- `.more{display:block}` — "Show 100 more" was offered even for a 2-result list.
  Live since the 2026-08 restyle.

`theme.py` now carries `[hidden]{display:none!important}` in the shared reset, so
`el.hidden` means hidden on all four pages. Nothing in this repo assigns
`style.display`, so the `!important` is safe; keep it that way and keep using
`el.hidden`.

⚠ **`.nores` on /products.html was never affected, and the reason is the rule to
remember:** it has no author `display` rule, so the UA `[hidden]` won on its own.
The bug only appears where an author rule sets `display` on something you also
hide by attribute.

⚠ **Checking `el.hidden` is NOT checking that it is hidden.** The property reads
`true` while the element renders at full height — which is how this shipped: the
verification asserted `drawerHiddenInitially: true` and moved on. Assert
`getComputedStyle(el).display === 'none'`, or a rendered height of 0. Same rule as
"verify the built output, not the patch report", one level further in.

### The toolbar is ONE row above 940px, by `nowrap` not by tuned widths

`flex-wrap:wrap` wraps a line **before** shrinking anything on it, so capping each
control only moves the width at which it breaks — 160+220+190+100 fits the 825px
column at 1280 and wraps to two rows in the 615px column at 1024. Above the
breakpoint the toolbar is `nowrap` with `min-width:0` on the selects, so they
compress and ellipsis instead. Below 941px the sidebar goes static and wrapping is
correct, so the default stands.

- **Selects absorb the squeeze; buttons do not.** `flex:0 0 auto` +
  `white-space:nowrap` on `.tog`, because letting `#morefilters` shrink took it to
  67px, wrapped "More filters" onto two lines and made it 57px tall beside 38px
  selects. A control that changes height as the window narrows reads as broken.
- **`#lic` carries its own `max-width:220px` from an ID selector**, which outranks
  a class rule and left it hogging 220 of a 615px column, squeezing `#sort` to
  101px where "Sort: most catalogs" truncates to about three characters. An ID
  needs an ID to beat it: `.toolbar #lic`.
- **Anything that does not fit goes in the drawer.** `Replaces a paid product`
  moved there for this reason, leaving sort / licence / source catalog / More
  filters on the row.

⚠ **Measure rows by vertical CENTRE, not `top`.** The toolbar is
`align-items:center`, so controls of different heights have different `top` values
on the *same* row — which reported "2 rows" for a correct single-row layout twice
during this work. Compare `toolbar.height` against the tallest child instead.

### Recently added, and `cache/_first_seen.json` (2026-09-22)

Nothing recorded when an entry arrived. `history.json` carried the COUNT — `+16` —
but not which sixteen, so "what's new" could not be shown or even asked.
`first_seen.py` now stamps `cache/_first_seen.json` after dedupe, and it is
committed with the rest of `cache/` by the `record` step. Same contract as
`_fetched.json`: a date is written ONCE and never overwritten, and the file is
sorted so a weekly diff is ~20 lines.

⚠ **`None` means BASELINE and is not the same as absent.** Entries present at the
first weekly run carry `null` — they existed before the record began, and dating
them to the day the backfill ran would assert an arrival nobody observed. An id
carrying `null` is *known* and never reported as new; an id **missing** from the
file is genuinely unseen and gets stamped. Conflating them dated the entire
3,070-entry baseline to the backfill date on the first attempt. Current state:
**3,070 baseline, 119 dated across 9 weekly runs.**

⚠ **The backfill counts only `Data:` commits.** git holds 27 revisions of
`catalog.json`, but 16 are dated 2026-08-11 — the project being *built*, not
entries arriving. Treating those as observations dated 1,185 entries to a day on
which nothing was harvested. A `Data:` commit is written by `record` at the end of
a run, so it is the only revision where the catalogue itself changed.

⚠ **`build_ui._fs_ident()` must match `first_seen.ident()` exactly** (`repo_key`,
falling back to `name|source`). If they drift every entry reads as undated and the
strip silently empties.

**The strip shows 10, and that is why the sort exists.** `Recently added` sits
where the API banner used to, above the stat tiles: ten cards, horizontally
scrollable, with `See all, newest first` switching the table to the matching sort.
A strip you can read beats one you have to work through.

⚠ **The strip's tie-break must match the table's `recent` sort exactly.** Python's
`reverse=True` on a `(date, name)` tuple reverses BOTH keys, so the strip led with
`VC Solar` while the table led with `bytype` — same date, opposite name order, and
"See all" landed the reader somewhere the strip did not start. Sort by name
ascending, then stable-sort by date descending, which is what the JS does.

⚠ **Undated entries sort LAST under `recent`, never first.** `fs` is `null` for the
3,070 baseline, and a falsy-to-empty-string comparison floats them to the top as if
they were the newest thing in the catalogue.

**The API note moved under the search field and shrank** — and that is compatible
with agent affordance 3 of 4, not a violation of it: the searchbar is in the hero,
so the note is now EARLIER in the DOM, which is what that affordance asks for. It
must stay visible text; a tooltip or a collapsed disclosure would end it.

⚠ **The strip's arrow-disabled test needs a tolerance, not `<= 0`.** The track
carries 2px of padding plus `scroll-snap-align`, and rests at `scrollLeft` **2** —
measured — so an exact test left the left arrow enabled on a strip already at its
start. `.rbtn`/`.rall` also had to be added to the 44px touch-target rule; they
were 30px.

### The toolbar, the drawer, and what "set aside" now says (2026-09-21)

- **Source country labels are country NAMES** ("Germany", not "DE"), from
  `sources.py:COUNTRY_NAME`. The facet **VALUE stays the code**, matched against
  `r.cs` — only the display changed. ⚠ `EU` and `GLOBAL` are not countries and are
  deliberately "European Union" and "Global": GLOBAL is the UN-affiliated DPG
  registry on a wider criterion than the rest, and conflating it with a state
  would misrepresent 253 entries.
- **`Sort: country` sorts by the NAME, not the code.** Once the label read
  "Germany", a code sort put Germany before Denmark and the list looked unsorted.
  `CCNAME` is derived from the facet labels so there is one source for them, with
  the flag stripped — sorting the raw label orders by emoji codepoint.
- **Source catalog is a toolbar `<select>`, not a sidebar facet.** SINGLE-select, by
  decision: the Source country facet now answers the case multi-select existed for
  ("all of Germany" rather than ticking openCode and Munich separately), and 17
  values make a better dropdown than a 6-of-17 facet with an expander. `SFACETS` is
  still built — it validates an incoming `?src=`.
- **`?src=<label>` and `?cc=<code>`** are entry points, both validated against the
  values the page actually offers. An unknown one is IGNORED, never applied:
  filtering to nothing would read as "this catalogue contributed no entries", which
  is the one claim `/sources.html` exists to disprove. ⚠ The link value is
  `SOURCES[key]["label"]` on BOTH sides — `build_sources.py` writes it,
  `build_ui.py:SRC_LABEL` and the dropdown consume it. If they diverge the link
  silently empties the catalogue.

**"Include 488 set-aside entries" is gone, and the reason is worth keeping.** One
label covered two unrelated claims, and the project's own owner asked what it meant
— which is the strongest evidence a label can get. It is now two controls in a
**More filters** drawer, with the counts computed in `build_ui.py` so they cannot
drift:

| control | n | the claim |
|---|---|---|
| `Show N with no description` | 384 | The publisher wrote none and GitHub had none either (`enrich_desc` runs first). An editorial standard about publisher effort. |
| `Show N judged not adoptable` | 104 | Fork, deployment recipe, CI plumbing, locale bundle, org metadata. A judgement about the artefact. |

⚠ **Keep both reachable.** That toggle is the only UI route to those entries, and
`Products.PloneMeeting` is among them — it vanished once already. Both remain in
`/entries.json` flagged with an `exclude_reason` regardless of the toggles.

⚠ **The denominator moves with the toggles.** `render()` recomputes the universe
from the same predicate, or "N of M" compares the filtered list against a universe
the page is not showing. Verified: 2,857 → 3,241 (+384) → 3,345 (+104).

The drawer also holds **Repository state**, moved out of the toolbar: it is rarely
touched and the toolbar was full. Toggle it with `el.hidden`, never
`style.display` — the page reset carries `[hidden]{display:none!important}`, which
would win.

### The catalog sidebar is bounded, and that is load-bearing

`.side` is `position:sticky` **with `max-height:calc(100vh - 40px)` and
`overflow-y:auto`**, reset to static/unbounded under the 940px breakpoint. Keep all
three: an unbounded sticky element taller than the viewport leaves its bottom
permanently unreachable, and the facet list grows every time a source is added.

⚠ **A whole facet group was once DELETED to treat that symptom.** The Source country
facet was removed with the reasoning "the sidebar had grown taller than the viewport,
which stopped it pinning" — and it did not work: measured on the live page at
1280x860 with the facet already gone, the sidebar was **887px against an 860px
viewport**, still 27px unreachable. The cause was the missing bound, not the group
count. Bounding it fixed the pre-existing overhang *and* made room for the facet to
come back (820px cap, 1,143px of content scrolling internally).

The other half of that removal — "largely redundant with Source catalog, a catalogue
belongs to one country" — was half true and worth understanding before trusting a
similar argument. A catalogue belongs to one country, but a **country has several
catalogues**: DE is openCode + Munich, FR is SILL + awesome-codegouvfr. The removal
comment named its own cost, "everything from Germany now means selecting openCode and
Munich separately", and that is exactly the query the facet exists to answer. It also
restores something no combination of source facets could: **64 multi-catalogue entries
whose `countries` span several states** (LibreOffice and QGIS are `[DE, FR, GLOBAL,
IT]`) are findable under each, because the facet matches `r.cs`, not the single `r.c`.

⚠ **`current()` routes every facet key EXPLICITLY — never restore the `else` default.**
It was `if fn / else if rp / else srcs`, so adding the `cc` group silently pushed
country codes into the source-catalog filter, which matches no source label and empties
the list. "No entries from Germany" is what that looks like from the outside. A default
branch that swallows unknown keys is how a new facet breaks an old one.

### `/sources.html` answers four questions, deliberately

Rebuilt 2026-09-20 after a policy researcher asked how the data is obtained, whether it can be
filtered regionally, how much there is, and how reliable it is. Three gaps, now closed:

- **Depth per source, not just volume.** `N% publiccode` on every row. SILL contributes 670
  entries of which **4%** carry a publisher-written `publiccode.yml`; Developers Italia
  contributes 537 of which **100%** do. Two similar-looking counts, very different datasets —
  the page used to render them identically.
- **Link health per source.** `N% links live`, counting only repos with a DECIDED verdict:
  `unknown` (403/429/5xx) is excluded from the denominator rather than counted as either, the
  same rule `liveness.py` uses. Attributes rot to the catalogue that published the link
  instead of pooling it into one site-wide figure.
- **A `By country` grid** linking `/by-country/<CC>.json`, ⚠ **with the caveat rendered on the
  page**: the code is the country of the **catalogue that listed the software**, not the tier
  of government that published it — there is no municipal/regional/national field. That
  distinction belongs where the number is read, not only in docs; it is the figure most likely
  to be misread by the audience most likely to want it.

⚠ **Do not build the country grid out of `.crow`.** It was, first: the 5-column catalogue-row
grid left three cells empty and made each country **141px** tall, turning a 15-row lookup
table into ~2,100px of scrolling. `.cgrid`/`.ccard` is 46px a card, 5 across at 1200px, 260px
for the whole section. Measure the rendered DOM — the preview pane returns blank screenshots
for this page.


---

## How these were found

Every one surfaced from *measuring the rendered page*, not from reading the patch:

- `el.hidden` read `true` while the element rendered 253px tall.
- `getBoundingClientRect().top` reported two rows for a correct single-row
  toolbar, twice, because `align-items:center` gives differently-sized controls
  different tops. Measure by vertical centre, or container height against the
  tallest child.
- `API and MCP` looked like a wrapping bug and was a class collision: it measured
  873px — the full container — because `class="more"` already means
  `display:block;width:100%`.

The general rule, which `test_built_pages.py` now enforces for the cases it can
reach: **verify the built output, not the patch report** — and when the thing you
are checking is visual, verify the computed style or the measured box, not the
property you set.


---

## Session records, 2026-08-13 to 2026-09-10

Moved out of `CONTINUE.md` 2026-09-23 so it keeps only the two most recent.

## Shipped 2026-09-10 — the code review, and its top four findings

**`REVIEW-govoss-catalog-2026-08-28.md`** is in the repo and recorded in the Hub
(`~/vault/reviews/sarapis__govoss-catalog.md`). 8 findings from 17 drafts. Its verdict is
one sentence worth keeping: *every failure sensor in this pipeline is a print, and the one
hard gate reads sensors that cannot trip.*

- **F1** `bb59fb7` — `cache/_fetched.json` per source. `fetched_at` advances **only on a
  success**, so a failing source's age grows; `build_sources.py` warns >15d, critical >29d,
  and stamps the row. Harvest still exits 0 on a failed source **deliberately** — one flaky
  source must not block the publish of sixteen good ones.
- **F2** `bb59fb7` — `os2()` raises when orgs failed **and** the result regressed, instead of
  overwriting its own checkpoint with a truncated scan. `github_org_scan` now authenticates
  via `liveness.gh_token()` (60 → 5,000 req/hr).
- **F3** `100e757` — a crashed `liveness.py` annotates `summary.failed_at`/`last_error` and
  preserves `checked`; it still exits 0.
- **F4** `100e757` — `taxonomy.py` writes `out/taxonomy_unmapped.json`; the page warns by name.

All four self-clear on success, which was verified rather than assumed.

**F8 substantially addressed — the suite is 6 files / 163 checks**, from 1 file / 23. Run
them all before touching `dedupe.py`, `liveness.py`, `filters.py`, `taxonomy.py`,
`merge_translations.py` or `export_json.py`:

```
for t in test_*.py; do python3 $t; done
```

`liveness.fold_history()` was **extracted from `main()`** so the two-strike state machine
could be tested without a network sweep. The extracted body was checked line-for-line
identical to the block it replaced, and the refactored monitor was then run for real —
6m43s, 3,065 ok / 27 dead / 1 pending / 1 newly dead — so the refactor is confirmed
end-to-end, not just by unit test.

**Three defects fell out of sabotage-testing the new suites**, none of which they were
looking for:

- **`norm_repo`/`norm_site` stripped `^www.` and `^https?://` BEFORE lowercasing**, so a
  capitalised `Www.` produced a key that could not join its lowercase twin. Latent — 0 of
  4,464 real URLs — fixed with `re.I`, and verified a no-op on all 4,464.
- **The `replaces.json` refusal named the key lowercased**, pointing at a string you cannot
  grep for in the hand-edited file it tells you to fix.
- **`filters.py`'s cost comment was stale in the direction that argues for weakening the
  rule** — it still claimed set-aside entries vanish from `/entries.json`, which stopped
  being true on 08-14. Verified: 3,318 rows, 484 flagged, PloneMeeting present.

**F6 also closed — `out/translation_orphans.json`.** `merge_translations.py` now reports
tr_*.json keys whose source text is no longer in the catalogue: **59 of 1,762 today** (3%).
The entry falls back to its foreign original, which stays documented and accepted — what was
missing was any report that it happened. `runlog.py` records the total into `history.json`
and `build_sources.py` warns when it **grows**. Three decisions worth not re-litigating:

- **The obvious implementation is wrong, badly.** "Keys this merge pass actually looked up"
  is the natural reading, and a merged row carries `translated: True` and short-circuits
  before the lookup — so on already-merged input it reports **1,762 of 1,762 keys orphaned**
  against a real 59. Measured, not imagined. The rule instead hashes the SOURCE TEXT still in
  the catalogue, from `short_desc` (the original on a raw row) **and** `desc_src` (the
  original on a merged one), which is stable across re-runs by construction. Verified against
  all 1,731 merged rows carrying a `desc_src`: zero false orphans.
- **The DELTA is the trigger, not the total.** Rot is expected to be non-zero and slowly
  growing, so warning on 59 would have shipped a page that reads `warn` from day one for a
  pre-existing backlog — and a warning that is always on is one you stop reading. Same call
  `liveness.py` already makes: "3 newly-dead repos" over "81 dead".
- **A missing previous figure is NOT zero.** `runs[-2]` predates F6 and has no
  `orphan_keys`; treating that as 0 would have reported the whole standing backlog as new rot
  on the first run. Verified across the whole matrix (prev absent / 59→60 / flat / improved /
  0→60): only genuine growth warns.

`test_translation_orphans.py` locks in both rules side by side, so the naive one cannot look
reasonable to the next reader, and was checked by sabotage — dropping `desc_src` from the
live set, and stripping text before hashing (the Bulgarian whitespace trap), each fail
several assertions.

**F5 also closed — `stage_guard.py`.** `dedupe.py` **and `taxonomy.py`** now refuse to run
on an already-merged `catalog.json` (marker: `catalogue_count` on an active row). Both were
destroying data only the merge has: dedupe resets `catalogue_count` to 1 on every survivor,
wiping the "In N catalogues" pill; taxonomy narrows `functions` on **45 entries**, because
`functions` is union'd in `dedupe.py:UNION_LIST` and `classify()` only sees the survivor.
Three things about it worth not re-litigating:

- **It refuses; it is not merge-aware, and there is no `--force`.** Unioning the recomputed
  value with the stored one is the obvious fix and it is wrong — a corrected mapping, or a
  record that legitimately stopped being multi-catalogue, would keep its stale value forever
  with nothing to say so. That is a loud bug traded for a silent permanent one. The way
  forward is `python3 harvest.py --from-cache`, which is offline and cheap.
- **Verified by sabotage.** Stubbed to `return False`, both stages exit **0** and modify
  `catalog.json` — the destruction observed, not inferred. `test_stage_guard.py` locks in
  both directions plus the two mistakes that would make the guard useless (`all()` for
  `any()`; forgetting to skip `excluded` rows, which never carry the marker).
- **The first version of the test had the hole this repo keeps hitting.** It asked
  `stage_guard.is_post_dedupe()` whether `catalog.json` was merged, so a sabotaged no-op
  guard reported "not merged" and the test *skipped* its subprocess cases — the ones that
  prove destruction is prevented — precisely when the guard was broken. A test must never
  ask the thing it is testing whether to run its hardest case.

## Shipped 2026-08-13/14

- **govoss left the CTFG design system** for `@wegovnyc/design-tokens` v0.7.0 under a `govoss`
  brand variant — the system wegov.nyc and unnyc.wegov.nyc share. No CTFG chrome, no NYC
  identity. `ctfg_nav.py` retired, so **the build now makes no network request at all**.
- **`/products.html`** — the proprietary side made browsable: one dense table of 372 products
  with description, function, alternatives and a link into the filtered catalogue.
- **`replaces.json` 108 → 194 entries**, 290 products. Entry point is a `Replaces` facet in
  the catalog sidebar, not a nav item.
- **Bulgarian translated** (175), **descriptions enriched from GitHub**, and entries with **no
  description at all set aside** (351). Entry and English counts now agree: 2,753 / 2,751.
- **Identity**: Wikidata added as a second QID source (by URL, never by name) and a third
  dedupe key (exact name **and** exact homepage). 554 → 644 QIDs.
- **`/entries.json` carries set-aside rows**, flagged `excluded` — the derived indexes stay
  curated.
- **WCAG re-audited** after the design move: zero failures, lowest 4.9:1.

---

## The long-form operating manual, as of 2026-09-23

`CLAUDE.md` grew to 949 lines (budget 300; it is auto-loaded into every session). On
2026-09-23 it was rewritten as rules only, and its full text moved here verbatim,
headings demoted one level. When a rule in `CLAUDE.md` reads too terse to apply,
its reasoning, numbers and incidents are below.

### govoss-catalog

> Union catalogue of **government open source software**, harvested first-hand from 17
> national, municipal and international catalogues, normalised onto one schema, translated to
> English, categorised by function, de-duplicated and liveness-monitored.
>
> **2,753 entries · 17 catalogues · 15 countries incl. EU + global.** Live at
> https://govoss.cat (Cloudflare; MCP at https://mcp.govoss.cat) — see `README.md` for the public overview and
> `CONTINUE.md` for open items. This file is the operating manual: it records why each
> decision was made and what not to re-litigate.

Output: `catalogue.html` (self-contained browsable page) and `catalog.json` (the data).

### Live state

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
Cloudflare, so there is no manual deploy any more. See *Publishing* below.

### The 17 sources, and how each is reached

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

#### Things that will bite you

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

### The EU aggregate catalogue is deliberately NOT syndicated

`interoperable-europe.ec.europa.eu/eu-oss-catalogue` federates all eight of these.
**Do not use it as a source.** As of 2026-08-10 its pager, facets *and* keyword search
all ignore the query string — every URL returns the same first 20 of 1,084 solutions, so
1,064 are unreachable. Verified on a forced CDN cache miss and in a real browser. Solution
pages are also absent from `sitemap.xml`. Full writeup with reproduction: `PAGINATION-BUG.md`.

Beyond the bug, it is the wrong layer: it ingests France's **19-entry** curated list rather
than the real French sources, so syndicating it inherits that hole permanently.

### Identity crosswalk (`crosswalk.py`)

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

### Cross-catalogue presence

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

#### The "Recommended" stamp is retired (2026-08-14)

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

### Identity and dedup

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

### Translation

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
### Categorisation

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
### Liveness monitor

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
### Per-source freshness (`cache/_fetched.json`) — read before trusting a count

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
### Filtering non-software (`filters.py`)

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

### Machine-readable export (`export_json.py`) + dedupe

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

#### `replaces.json` — the field that changes what the catalogue is for

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
#### Dedupe (`dedupe.py`)

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

#### `stage_guard.py` — taxonomy and dedupe REFUSE merged input

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

#### Variants (`variants.py`, `variants.json`)

"This entry is a version of that one" - three city participation portals are
all Consul Democracy. **Linked, never merged**: merging would destroy the
adoption evidence (three governments running their own) and blur
`catalogue_count`, which counts listings of the SAME software. Runs after
dedupe, so claims resolve against surviving entries; recomputes every run, so
it needs no stage_guard.

- **Evidence is repo URLs only**: the publisher's `publiccode.yml` `isBasedOn`
  (harvest keeps it raw as `based_on`), or `variants.json`, keyed on REPO URL
  because the bare name "Consul" is also HashiCorp Consul. A curated row can
  add a link or VETO one (`based_on: null`), and must say what was checked.
- ⚠ **`isBasedOn` is rare and noisy**: 31 of 551 Italian files, many naming a
  dependency. So a claim counts only if it resolves to an active entry, and
  never if the core is a `library` (Bootstrap Italia), the entry is an `addon`
  or `configurationFiles`, or the claim is a homepage (`www.debian.org`).
- **A variant inherits its core's `replaces`** (`inherited_from` on the row,
  "via X" on the page) unless it has its own; inherited rows stay OUT of
  `by-product.json`, so a buyer sees the core once with its `variant_count`.
- **The page FOLDS, never hides**: a variant disappears under its core only when
  the core is in the same result set. Hiding it outright would make a source
  filter read as "this catalogue contributed nothing".
- **Forks are the third evidence** (`fork_parent`: one GitHub GET per fork,
  inline on Forgejo). ⚠ **A fork counts only when a DIFFERENT catalogue
  publishes it than lists its parent.** Of 71 forks, 15 have a parent in the
  catalogue but 13 are copies inside one catalogue (OS2 modules forked between
  OS2's own orgs, Dutch doc repos) and ARTE's udata fork sits in a catalogue
  that already lists upstream udata - leaving Bulgaria's CKAN. A qualifying
  `upstream-fork` is REINSTATED (original reason in `reinstated_as_variant`);
  each run first undoes last run's reinstatements, so the stage stays pure.
- **Publishers can declare `replaces:` in publiccode.yml** (non-standard; 0 of
  551 Italian files do). Rows are marked `via: publiccode`, bad vocabulary is
  DROPPED not fatal - the opposite of `replaces.json`, because it is someone
  else's file - and an unknown product stays off `by-product.json` and the page,
  which would otherwise link a missing anchor.

### Agent discoverability

The page tells agents not to scrape it, in four places, because the first consumer probed
eight dead paths and then drove a headless browser:

1. An **HTML comment above `<title>`** listing the endpoints — for agents that read raw HTML.
2. `<link rel="alternate" type="application/json">` x3 and a `<meta name="description">`.
   These sit before any visible markup; browsers hoist them into the implied `<head>`, so
   they work on the raw served file even though it has no explicit `<head>`.
3. A **visible banner** directly above the stat tiles, so a text extraction hits it early.
4. **`/llms.txt`** — generated by `export_json.py`, so its counts can never drift from the
   data. Plus `/robots.txt` and `/sitemap.xml`.

### Status page (`build_status.py` + `runlog.py`)

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

### Publishing

`run.sh`'s last two steps publish and commit. Before they existed the weekly run
regenerated everything and published none of it, while its own status page still
said "Operational".

- **`deploy` is gated on `out/steps.tsv`** — any non-zero step and nothing is
  published; a partially harvested catalogue overwriting a good public copy is
  worse than a stale one. It runs after the run log and pages, so the published
  copy describes the run that published it, and **refuses if
  `wrangler.site.jsonc` carries no `account_id`** - a cached login for another
  account once took a deploy.
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
  wrangler is a node script too; `publish()` resolves both. Verified by running
  `publish()` itself under `env -i PATH=<plist PATH> HOME=$HOME`.

#### Hosting: Cloudflare (since 2026-09-23; it was Vercel)

The site is an assets-only Worker (`govoss-site`, `wrangler.site.jsonc`) serving
`site/` at `govoss.cat` (a custom domain - Cloudflare owns its DNS record and
certificate). `www.govoss.cat` is a separate tiny Worker (`govoss-www`,
`wrangler.www.jsonc`, `deploy-cloudflare/www-redirect.js`) that 301s every path to
the apex, query kept, WITH `Access-Control-Allow-Origin` on the redirect so a
cross-origin browser fetch survives it. A Worker because the deploy login cannot
edit zone rules; separate so the site itself runs no script per request. run.sh
does not redeploy it (it holds no data). DNS, site and the MCP Worker share
Devin@sarapis.org's Account.

- **Headers and redirects are `deploy-cloudflare/_headers` + `_redirects`**,
  copied into `site/` by `build_site.sh` and pinned by `test_built_pages.py`:
  CORS on every JSON file, the six agent paths, `/status.html` -> `/sources.html`.
- ⚠ **`html_handling` is `"none"`**, so `/sources.html` is served as-is; the
  default 307s it to `/sources`, breaking every link, canonical and hreflang.
  `none` also drops directory indexes, which `deploy-cloudflare/site-worker.js`
  restores (`/`, `/ca/`, `/ca` -> `/ca/`); it runs only when no asset matches.
- ⚠ **A Worker custom domain needs the hostname free of DNS records** - Cloudflare
  refuses with code 100117 ("externally managed DNS records"), and the deploy
  "partially updates". Delete the records, then deploy.
- **`govoss-catalog.vercel.app` permanently redirects every path to govoss.cat**
  (`deploy-vercel.json` is that whole last deploy; redeploy it from an empty
  directory with the project link). Vercel adds no CORS header to a redirect, so
  a browser fetching the OLD JSON URL cross-origin fails - scripts and agents
  follow it fine. `sources.py:SITE_URL` is the one place the address is written.

#### Deploy auth is REPORTED, not just relied on (F7)

Auth resolves `CLOUDFLARE_API_TOKEN` -> `~/.config/govoss/cloudflare-token`
(chmod 600) -> wrangler's stored login, and `publish()` records which to `out/deploy_auth.txt`;
`runlog.py` puts it in `history.json` as `deploy_auth` and `build_sources.py`
**warns while the route is `stored-login`**. The fragile mode was already
*printed*, and a print is not a sensor: a revoked login fails the deploy, but the
only outward signal is the site going stale and the Stale badge not flipping for 8
days.

- ⚠ **`None` is not `stored-login`.** A run that never reached deploy records
  `None` and must not warn — defaulting it would report a posture the run never had.
- `warn`, not `critical`: nothing is broken while the login works, and over-grading
  config debt trains the reader to ignore the page.
- **The pre-flight checks CONTENT, not exit status.** `wrangler whoami` must print
  the pinned account id; anything else is a failure whatever the exit code says
  (the Vercel version of this check only worked because of `pipefail`). It is
  deliberately **non-fatal**: a transient hiccup must not block a good publish; it
  only makes the failure legible (auth, not PATH).
- ⚠ **The remaining step is a CREDENTIAL, not code.** Mint a Cloudflare API token
  with Workers Scripts:Edit on Devin@sarapis.org's Account into the file;
  `~/.config/govoss/` exists (mode 700, with a README). Until then the page carries
  the warning, which is intended.

#### Committed JSON must be deterministic

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

### The pages

**Every page is built once per language** — English at `/`, Catalan at `/ca/`
(`i18n.py`, `i18n/ca.json`). Phase 1: the chrome is translated; descriptions,
source notes, survey write-ups, operator diagnostics and the API contract stay
English on every copy, because they are data or a contract.

- **Translations are keyed on the English text** (a gettext msgid). Templates mark
  strings `⟪…⟫`, or `⟪js:…⟫` inside a single-quoted JS string; Python-built
  strings use `i18n.t(lang, msg, **kw)` with NAMED arguments, because Catalan
  word order differs ("fa {n} d"). Rewording an English string orphans its
  translation, which is reported rather than shown stale.
- ⚠ **Order is load-bearing: markers → placeholders → links.** Markers resolve
  while `__PLACEHOLDERS__` are intact so msgids stay stable; values go in after;
  `i18n.links()` then points root-relative page links at `/ca/`, skipping any tag
  with `hreflang` (the switcher and alternates must point at the OTHER language).
- ⚠ **`⟪js:…⟫` escapes to `\uXXXX`.** A Catalan apostrophe inside a single-quoted
  JS string breaks the whole catalog while every static check passes;
  `test_built_pages.py` runs `node --check` on each copy's inline script for that.
- **A missing translation falls back to English** and lands in
  `out/i18n_missing.json`, which `/sources.html` warns on. A translation whose
  placeholders differ from the English FAILS the build (it is our own file).
- **Adding a language** is `i18n.LANGS` + `i18n/<lang>.json` + `NAMES`; the
  builders, links and tests loop over `LANGS`.

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
#### Catalog page UI — rules paid for in bugs

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

#### Recently added, and `cache/_first_seen.json`

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

#### The API note is agent affordance 3 of 4

Small, directly under the search field — *earlier* in the DOM than its old slot
above the stat tiles, so the affordance improved. It must stay visible text: never
a tooltip, a collapsed disclosure or an image. ⚠ `theme.py`'s icons carry a viewBox
and no width/height, so every context sizes its own or it renders enormous.

#### `/sources.html` answers four questions

How the data is obtained, whether it filters regionally, how much there is, how
reliable it is — after a policy researcher asked all four. Per source: `N%
publiccode` (depth, not volume — SILL is 4% of 670, Developers Italia 100% of 537)
and `N% links live` (unknowns excluded from the denominator), plus a `By country`
grid linking `/by-country/<CC>.json`.

⚠ **The country code is the country of the CATALOGUE, not the tier of government
that published the software** — there is no municipal/regional/national field. The
caveat ships in the JSON, on the page, in `meta.json` and in `llms.txt`: it is the
figure most likely to be misread by the audience most likely to want it.


### The MCP server

`mcp-server/` — a Cloudflare Worker at `https://mcp.govoss.cat` (custom domain on
Devin@sarapis.org's Account; `account_id` pinned in its wrangler.jsonc). Public,
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

### Accessibility

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

### Tests

Eight suites, 310 checks, **all manual** — a test step that can fail the weekly
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
| `test_built_pages.py` | the built pages + four cross-page contracts, and every language copy (lang, hreflang, links, inline script parses) |
| `test_variants.py` | every `variants.resolve()` rule incl. forks and reinstatement, the real Consul portals and CKAN/udata forks, `norm_repo` parity |

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
### Four bugs that recurred — check for these first

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
### Gotchas in this repo

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
