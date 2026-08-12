# Continuation prompt

Paste this into a fresh session to pick up where 2026-08-11 left off.

---

I'm continuing work on **`~/Antigravity/govoss-catalog`** — a union catalogue of government
open source software, live at https://govoss-catalog.vercel.app

**Read `CLAUDE.md` first.** It's the operating manual: every source's access route, why each
design decision was made, and a section called *"Four bugs that recurred"* listing failure
shapes that came back repeatedly. `README.md` has the public overview. Don't re-litigate
decisions recorded there — particularly the deliberate exclusions.

Current state: **3,063 entries, 17 catalogues, 14 countries + EU + a global registry.**
Pipeline is `bash run.sh` (~25 min, order matters — it's documented at the top of the file).
Scheduled weekly via `org.antigravity.govoss-harvest` (Mondays 07:00).

## The one thing that actually needs doing

**The weekly harvest regenerates everything and publishes none of it.** `run.sh` has no
deploy step, so I've been running `vercel deploy --prod` by hand after every change. Next
Monday the public copy silently goes stale while the status page still says "Operational".

The fix: put a `VERCEL_TOKEN` in the plist's `EnvironmentVariables` (the CLI's stored auth
does not work from a launchd job — verified), add a deploy step to `run.sh` gated on
`out/steps.tsv` showing no failures, and confirm by kickstarting the job and checking
`generated_at` moves on the live `/meta.json`. Maybe 15 minutes. **Do this first** — it's the
difference between a durable catalogue and one that needs nursing.

## Then, in rough priority order

1. **Expand `replaces.json`.** 108 of 3,063 entries map to 165 proprietary products. This is
   the field that makes the catalogue answer *"what can we stop paying for?"* rather than
   *"what exists"*. Read the `_README` block in that file first — `kind` (`software` /
   `service` / `paid-tier`) and `confidence` both matter, and getting them wrong produces
   confident category errors. `export_json.py` warns on keys that match nothing, so the file
   cannot rot unnoticed.

2. **Two OSOR leads left, both small:** ICT ReUse Belgium and Helsingborg City. Adullact and
   Forja redIRIS are academic/association rather than government. Diminishing returns — check
   `sources.py:SURVEY` for what's already been rejected and why before chasing anything.

3. **171 Bulgarian descriptions are untranslated** and that was a deliberate call: they're
   mostly long EU-funding project titles (`BG05SFOP001-…`) rather than software summaries. If
   you do them, triage first — translating a grant reference adds nothing.

4. **`HANDOFF-PROMPT.md`** is current as of this state. If the catalogue changes materially,
   it needs updating again — a downstream agent working from stale counts is worse than one
   with none.

## Things that are done and should be left alone

- **Do not syndicate the EU OSS Catalogue.** Its pager, facets and search all ignore query
  strings; only 20 of 1,084 solutions are reachable. `PAGINATION-BUG.md` is a finished report
  ready to send to the EC — that's still worth doing if you want a use for it.
- **Do not chase the UNODC "Directory of Open-Source Registries".** It's open-source
  *intelligence* (company registries for corruption investigators), not software.
- **Do not add `OS2World`, `os2edu`, `os2sd`, `OS2G` or `OS23Portfolios`** if you touch the
  Denmark adapter — they're name collisions (IBM OS/2, a Chinese OS project, Android ROM
  trees, a US student club, someone's coursework). `harvest.py:OS2_EXCLUDED` records why.
- **France's 24,440-repo inventory stays excluded.** It answers "who published this", not "is
  this useful to a government": 45% no description, 80% no licence, dominated by research
  code. Re-add it as an enrichment join if ever, never as catalogue entries.

## Verification habits this project earned the hard way

- Check the **built output**, not that a patch reported success.
- Confirm a **dead** verdict through a second channel before recording it.
- **Detect** description language from text; never assume it from the source.
- Run `bash run.sh` rather than the steps from memory — the ordering is load-bearing and I
  once rebuilt the whole site from un-deduped data by improvising it.
