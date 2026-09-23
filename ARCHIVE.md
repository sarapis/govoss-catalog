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

