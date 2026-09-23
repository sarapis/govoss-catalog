# Open items

Where the work stands as of **2026-09-23**. Written to be handed to whoever — or
whatever — picks this up cold. `CLAUDE.md` is auto-loaded and is the operating
manual; `ARCHIVE.md` holds the incidents behind its rules and older session
records, and is not required reading.

**State: 2,857 active entries · 488 set aside · 17 catalogues · 15 countries.**
Pipeline is `bash run.sh` (18 steps, ~20 min; the order is load-bearing and
documented at the top of the file). Scheduled Mondays 07:00. Live at
https://govoss-catalog.vercel.app, deployed and current.

## The one idea, if you remember nothing else

**Every failure sensor in this pipeline started as a `print`, and the one hard gate
read sensors that could not trip.** All the known instances are now files the
status page reads — `cache/_fetched.json`, `summary.failed_at`,
`out/taxonomy_unmapped.json`, `out/translation_orphans.json`,
`out/deploy_auth.txt` — plus `stage_guard.py`, which is the same idea one step
further: a stage that *destroys* data has to refuse, not report.

When you find the next one, the fix is not "add a warning"; it is **"write it where
the page already looks."** Three corollaries this cost real sessions to learn:

- **The total is rarely the trigger.** Something expected to grow needs a delta, or
  the page reads `warn` forever and nobody reads it.
- **A missing previous measurement is not zero.** That turns a standing backlog
  into a day-one false alarm.
- **If a guard cannot be made to fail, delete it.** One was written,
  sabotage-tested and removed this month for exactly that.

## State — verified, not recalled

```bash
git status --short && git log --oneline origin/main..HEAD   # clean, nothing unpushed
for t in test_*.py; do python3 $t; done                     # 8 suites, 310 checks
python3 -c "import json;d=json.load(open('site/status.json'));print(d['state'],d['problems'])"
```

- **Last run 2026-09-21**, trigger `schedule`, ok, 17/17 sources fetched cleanly.
- **Liveness 3,089/3,189 ok (96.9%)**, 26 dead, 39 archived.
- **8 test suites, 310 checks, all passing.** Manual — not in `run.sh`, because a
  test that can fail the weekly publish is one someone switches off.
- **`/sources.html` reads `warn`**, for two taxonomy values only. See Traps.
- Review `REVIEW-govoss-catalog-2026-08-28.md`: **F1–F6 closed, F8 at 5 of 8 gaps,
  F7 code-complete and credential-blocked.**

## Invariants — break these and something already fixed re-breaks

Each is pinned by a test or stated in full in `CLAUDE.md`; these are the ones whose
violation is silent.

- **`fetched_at` and `summary.checked` advance ONLY on success**, and both
  self-clear on a good run. Stamp either on a failure and staleness becomes
  undetectable again.
- **Never store a per-run value PER RECORD** — per-source or summary only. The same
  idea per record once turned one `liveness.json` diff into 47,563 lines.
- **`--from-cache` must not write `cache/_timing.json` or `cache/_fetched.json`**
  (guarded by `if want:`), or a no-network rebuild destroys the record of the last
  real fetch.
- **Look `_fetched.json` up by the CHECKPOINT key (`os2`), not `DK/os2`.** Getting
  this wrong is silent: the first version matched nothing for all 17 sources and
  reported `ok`.
- **`harvest.py` exits 0 on a failed source, on purpose.** Do not "fix" it into a
  hard failure — one flaky source would block the weekly publish of sixteen good
  ones.
- **`taxonomy.py` and `dedupe.py` refuse already-merged input** (`stage_guard.py`,
  pinned by `test_stage_guard.py`). Do not make either merge-aware and do not add
  `--force`. `merge_translations.py` is the same family but only *warns*, because
  it is safe to re-run and only its orphan count misleads.
- **`build_ui._fs_ident()` must match `first_seen.ident()`** or every entry reads as
  undated and the Recently-added strip silently empties.
- **`el.hidden` works only because `theme.py` ships
  `[hidden]{display:none!important}`.** Keep it; never `style.display`.
- **Never reintroduce a per-source language assumption**, and never replace one with
  bare `detect_lang` — it calls 532 of 672 SILL descriptions English. SILL and
  code.overheid.nl use `lang_with_prior()`; see `CLAUDE.md` › Translation.

## Waiting on a human — not work that was skipped

- **A Vercel deploy token (F7).** Verified absent: `~/.config/govoss/` exists with
  mode 700 and a README, and no `vercel-token`. Everything around it is done — the
  route is recorded, the page warns while on the stored login, the pre-flight
  validates content not exit status. One command:
  `printf '%s' 'TOKEN' > ~/.config/govoss/vercel-token && chmod 600 ~/.config/govoss/vercel-token`
- **The demand-side go/no-go** (`DEMAND-SIDE-CATALOGUE.md`) — a scope decision about
  what the catalogue *is*, and a bigger one than it looks: see Candidates.
- **Three documents drafted and unsent** — a reply to an OpenForum Europe policy
  advisor, an OFE-voiced version of the EU catalogue defect report, and a
  shareable call for sources (`DEMAND-SIDE-CALL-FOR-SOURCES.md`, in the repo). The
  first two are session artefacts, not committed.

## Candidates, ranked

1. **Map `environmental-protection` and `geospatial-information`** — already done in
   `taxonomy.py`; this is just waiting for the next run to clear the artefact. No
   action unless the warning persists past Monday.
2. **The demand-side Stage 1**, but read the reframing first. The note asks for a
   second jurisdiction publishing product-level licence data; its own crux says
   that data exists in NYC only because Databook ran an LLM extraction. So the
   runnable test is to extract from a second jurisdiction's *raw* contract data —
   which prices in a cost the note never named: **an extraction pipeline is not
   harvesting**, and that breaks the condition its own Costs section sets. Portland
   was the intended test and is still `permission denied for table tenders`
   (re-checked 2026-09-21).
3. **F8's last three gaps**: `get()`'s raise semantics (needs a stubbed opener),
   crosswalk's three guards (inline in SPARQL-calling functions — they need the
   extraction `liveness.fold_history()` got), and the MCP Worker (JS).
4. **Expand `replaces.json`** — 245 of 2,857 entries. A seeded sample puts the
   honestly-mappable share of the publiccode tier at ~20%; search it by shape
   ("platform", CMS, ERP, workflow engine), don't sweep it. Read the `_README` first;
   `kind` and `confidence` both matter and `export_json.py` fails the build on a bad
   value. ⚠ Check existing product names before adding; `Dropbox Business` beside
   `Dropbox` splits one product across two index keys.
5. **Screen-reader testing has never been done.** The audits are contrast sweeps
   plus keyboard. Until it runs, nothing should claim conformance.

## govoss.cat — waiting on DNS (2026-09-23)

Registered at Namecheap; `govoss.cat` and `www.govoss.cat` are added to the
Vercel project. Decided: DNS on Cloudflare (sarapis.org account), English at the
root, Catalan at `/ca/` as everywhere else. Once the zone is active:

1. Cloudflare DNS, both **DNS only** (grey cloud): `A govoss.cat 76.76.21.21`,
   `A www.govoss.cat 76.76.21.21`. Vercel verifies and issues certificates itself.
2. Confirm it answers: `curl -sI https://govoss.cat/` must return 200 with the page.
3. Flip `sources.py:SITE_URL` to `https://govoss.cat` - the ONE place the address
   is written (hreflang, sitemap, robots, llms.txt, meta.json, citation). Only
   after step 2, or canonical links point at nothing.
4. Redirect the old address: in `deploy-vercel.json`, a `redirects` rule with
   `"has": [{"type": "host", "value": "govoss-catalog.vercel.app"}]` to
   `https://govoss.cat/:path*`, permanent. JSON paths included - agents follow.
5. Worker: add `"routes": [{"pattern": "mcp.govoss.cat", "custom_domain": true}]`
   to `mcp-server/wrangler.jsonc`, `npx wrangler deploy`, then point
   `mcp_tools.py:ENDPOINT` and the four docs at `https://mcp.govoss.cat`.
   `CATALOG_ORIGIN` can move to `https://govoss.cat` at the same time.

## Traps — looks broken but is not, and vice versa

- **The MCP Worker's `search_entries` change needs `wrangler deploy`**
  (`mcp-server/`); it is not part of `run.sh`. The index fields ship with the
  site either way. It now lives in **Devin@sarapis.org's Account**
  (`account_id` pinned in `mcp-server/wrangler.jsonc`, 2026-09-23). The OLD copy
  at `govoss-mcp.devin-31f.workers.dev` (itspruvn.com account) still runs the
  pre-variant code; delete it once nothing points at it - that needs the
  itspruvn.com login.
- **`/sources.html` can warn about missing page translations one run late.**
  It is built before `/api.html` and `/products.html`, so it reads their
  entries in `out/i18n_missing.json` from the PREVIOUS run. A fix to those
  two pages clears the warning on the following run.

- **`/sources.html` reading `warn` is correct right now.** Two taxonomy values are
  genuinely unmapped *in the published artefact*; both are already mapped in
  `taxonomy.py`. `out/taxonomy_unmapped.json` is per-run, so a mapping fix does not
  clear the page until the next run. Confirm by dry-running `classify()`, not by
  reading the page.
- **`out/translation_orphans.json` reads 0, and that is real** — but only when
  measured *in position*. Run `merge_translations.py` by hand on a post-dedupe
  `catalog.json` and it reports ~37, of which ~29 are rows dedupe merged away, not
  rot. The script now says so when it detects merged input.
- **A "flat" source count is not staleness.** Eight catalogues genuinely do not
  change weekly; freshness comes from `_fetched.json`, not from the count moving.
- **The Recently-added strip being all-German is real**, not a bug — the 2026-09-21
  run added 20 entries, almost all openCode.
- **3,070 of 3,189 entries carry no first-seen date.** That is the baseline, not a
  gap: they predate the record, and `null` there means *known and never new*, which
  is deliberately not the same as absent.
- **`out/` is gitignored**, so its artefacts are per-run and absent on a fresh
  checkout; `build_sources.py` degrades to `ok`, by design.
- **`PAGINATION-BUG.md` is a report about someone else's service**, not a defect
  here. Re-verified 2026-09-20, still reproducing.
- **Nine class names in `_ui_template.py` carry more than one rule block.** Most are
  a base plus a media-query override, but a collision there cost a session: a link
  given `class="more"` inherited `display:block;width:100%` and looked like a
  wrapping bug.

## Verification habits this project earned the hard way

- Check the **built output**, not that a patch reported success — and after a
  structural edit, grep for what should still be there.
- **Test a guard adversarially.** If it cannot be made to fail, delete it.
- Confirm a **dead** verdict through a second channel before asserting it.
- **Detect** description language from text; read `desc_lang`, never
  `desc_src_lang`.
- Measure UI rows by **vertical centre**, not `top`; assert
  `getComputedStyle(el).display`, not `el.hidden`.
- Run `bash run.sh` rather than the steps from memory — the ordering is
  load-bearing.
- **The browser pane returns stale and blank frames.** Measure the DOM; rebuild
  `site/` before testing it.

---

## Starting the next session

Paste this into a fresh session in `~/Antigravity/govoss-catalog`:

> I'm continuing work on ~/Antigravity/govoss-catalog, a union catalogue of
> government open source software (live at https://govoss-catalog.vercel.app,
> repo github.com/sarapis/govoss-catalog).
>
> Read `/Users/devin/Antigravity/govoss-catalog/CONTINUE.md` first — it has the
> state, the invariants, what's waiting on me, and a traps section that will save
> you a morning. Everything else is conditional: read
> `/Users/devin/Antigravity/govoss-catalog/ARCHIVE.md` only if you need the
> incident behind a rule, `DEMAND-SIDE-CATALOGUE.md` only if you touch the
> demand-side question, and `REVIEW-govoss-catalog-2026-08-28.md` only if you work
> on F7 or F8.
>
> Tree is clean and everything is pushed as of 2026-09-23. The next scheduled run
> is Monday 07:00 and will be the first to exercise `first_seen.py`.
>
> Do not write a handoff, continuation prompt, or session record unless I ask for
> `/handoff`. End your turn with what you did and what you recommend next.
