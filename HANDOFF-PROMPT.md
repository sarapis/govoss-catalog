# Continuation prompt

Paste the block below into a fresh session in `~/Antigravity/govoss-catalog`.
Written 2026-08-14, after the session that added the proprietary catalogue, the
curation rule and the design-system move.

---

I'm continuing work on ~/Antigravity/govoss-catalog — a union catalogue of government open
source software. Live at https://govoss-catalog.vercel.app, public at
github.com/sarapis/govoss-catalog, MCP server at govoss-mcp.devin-31f.workers.dev.

READ FIRST, in this order:
  CLAUDE.md                  the operating manual — every gotcha and why each decision was made
  CONTINUE.md                what's open, in priority order, and what to check first
  DEMAND-SIDE-CATALOGUE.md   a live proposal with a decision still open
  DESIGN-BRIEF.md            the design system as built, incl. seven UI rules paid for in bugs

⚠ UPSTREAM-CTFG.md and CTFG-CONTRAST-REPORT.md are HISTORICAL RECORD. govoss left the Civic
Tech Field Guide design system on 2026-08-13 and now runs on @wegovnyc/design-tokens v0.7.0
under a `govoss` brand variant (vendored at vendor/wegovnyc/). CTFG is still a data consumer —
the change was branding, not the relationship. Don't re-litigate it, and don't reintroduce NYC
identity either: readers are European public-sector staff and the catalogue's credibility rests
on reading as neutral.

STATE: 2,753 active entries · 453 set aside and flagged · 17 catalogues · 15 countries.
`bash run.sh` is 16 steps, ~20 min, and ends by deploying to Vercel AND committing+pushing the
data — both gated on every earlier step exiting 0. Scheduled Mondays 07:00 via launchd.
Do NOT hand-deploy or run run.sh just to preview: it's a 20-minute harvest against fourteen
governments' infrastructure. Use `python3 build_ui.py && bash build_site.sh`, or
`cd site && vercel deploy --yes` for a preview URL.

FIRST THING TO CHECK: Monday 2026-08-17 07:00 is the first unattended run to exercise the new
enrich_desc step, the Wikidata crosswalk routes, the reworked dedupe, the no-description
curation rule and a build that makes no network request at all. Look at /sources.html (it
reports its own build status) and confirm generated_at in /meta.json moved. Two things are
EXPECTED, not faults: the >10% shrink warning fires once (3,069 → 2,753 is the intended effect
of the curation rule), and enrich_desc fills only ~8 entries before hitting GitHub's
unauthenticated rate limit.

OPEN, in rough priority order — CONTINUE.md has the full list with detail:

1. Decide the demand-side catalogue. DEMAND-SIDE-CATALOGUE.md proposes harvesting the
   proprietary software governments actually buy, from procurement data, rather than
   hand-seeding it. NYC's licence export joins the catalogue at 3.6% of spend and the note
   argues the limit is naming, not coverage. Stage 1 — the go/no-go — has NOT been run: get one
   more jurisdiction with product-level licence data and see whether product names normalise
   across two. A day's work, and it decides everything after it.

2. Expand replaces.json (194 entries → 290 products). Read its _README first: `kind` and
   `confidence` both matter and getting them wrong produces confident category errors.
   export_json.py FAILS the build on an invalid value. Check existing product names before
   adding — last session's additions split Dropbox across two keys by using a more specific
   name than the seed already had.

3. Databook design harmonisation is handed off, not done:
   ~/Antigravity/Databook2/docs/LANDING-HARMONISATION-PLAN.md. Give it to a Databook session.

4. enrich_desc.py needs a GITHUB_TOKEN in schedule/*.plist.template to finish its 251-entry
   backlog in one run instead of ~31 weeks. A PAT with no scopes at all is enough. Needs a
   credential decision, which is why it wasn't done.

5. Screen-reader testing has never been done. Contrast is swept automatically (zero AA
   failures, lowest 4.9:1) but VoiceOver/NVDA has never run. /products.html is a large table —
   the surface most likely to expose problems.

THINGS THAT WILL BITE YOU, beyond CLAUDE.md's list:

- Test guards adversarially. Two guards written last session could only ever pass until they
  were tested by breaking the thing they check — one substring-matched text that appears in a
  vendored CSS comment.
- Audit interactive states, not just the page at rest. A 2.41:1 contrast failure hid behind an
  unpressed toggle and the first full sweep reported zero failures.
- Read desc_lang (what is displayed), never desc_src_lang (the language of the original).
  Reading the wrong one produced a confident report of 358 untranslated entries that were
  already in English.
- Translation keys hash the RAW short_desc. Twelve Bulgarian descriptions carry surrounding
  whitespace, and keys built from .strip()ed text matched nothing, silently.
- The browser pane returns stale and blank frames. Measure the DOM; rebuild site/ before
  testing it — one "failure" last session was just build_site.sh not having been re-run.
- No f-strings for markup. theme.py, _ui_template.py and the build_*.py page templates use
  plain strings with __PLACEHOLDER__ tokens; the substitution asserts none survived.
- The get-involved block is DUPLICATED in _ui_template.py and build_sources.py. It has already
  caused one bug where a fix to one left the other stale.
