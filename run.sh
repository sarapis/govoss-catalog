#!/bin/bash
# Full pipeline: harvest -> translate -> categorise -> liveness -> page.
#
# Ordering matters and is not arbitrary:
#   harvest      rewrites catalog.json from the eight national sources
#   merge        re-applies stored translations (keyed on sha1 of source text,
#                so they survive a re-harvest as long as upstream wording is)
#   taxonomy     re-derives functions; must run AFTER merge because the keyword
#                inference reads the English description
#   enrich desc  fills missing descriptions from the GitHub API where upstream has
#                one; must run BEFORE translations, since recovered text is often
#                not English
#   crosswalk    stamps Wikidata QIDs from Comptoir du Libre so dedupe can merge
#                more; must run BEFORE dedupe and AFTER harvest
#   filters      flags non-software (forks, CI plumbing, deployment recipes) as
#                excluded; runs AFTER taxonomy so hidden rows still carry
#                functions for when the UI toggle reveals them
#   dedupe       merges records for the same software (QID, then repo URL). Must
#                run AFTER filters so forks are already gone, and BEFORE export
#   variants     links an entry to the catalogue entry it is a version of
#                (publiccode isBasedOn, or variants.json). AFTER dedupe, so a
#                claim resolves against surviving identities
#   first seen   stamps cache/_first_seen.json with the date each entry first
#                appeared; must run AFTER dedupe so the date attaches to the
#                surviving identity. Backfilled once from the weekly Data: commits
#   liveness     diffs against the previous liveness.json to find newly-dead repos
#   build_ui     regenerates catalogue.html from the finished catalog.json
#   build_site   assembles site/ from tracked sources (html, headers, redirects)
#   json export  writes site/entries.json + meta.json + by-product + by-category
#   api page     documents those files; measures them, so must run AFTER export
#   products page  the proprietary side: by-product.json made browsable, plus the
#                products governments buy that this catalogue cannot answer.
#                Reads by-product.json, so also AFTER export
#   deploy       publishes site/ to Cloudflare. After the sources page (which now
#                also writes status.json),
#                so the published copy describes the run that published it —
#                and gated on every earlier step succeeding.
#   record       commits and pushes the run's data output. LAST, sharing the
#                deploy's gate, so what is committed is what is published.
#
# Safe to re-run. Harvest checkpoints per source in cache/, so a network blip
# costs one source, not the whole run.

set -uo pipefail
cd "$(dirname "$0")"

# Pick an interpreter that actually has the deps, and say so if none does.
# Do NOT rely on `python3` from PATH: under launchd it resolved to Homebrew's
# python3, which has no pyyaml, so harvest died with ModuleNotFoundError while
# every later step still "succeeded" on stale data — a silent partial run.
PY=""
for cand in \
  /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
  /opt/homebrew/bin/python3 \
  /usr/bin/python3 \
  "$(command -v python3 || true)"
do
  [ -x "$cand" ] || continue
  if "$cand" -c "import yaml, certifi" >/dev/null 2>&1; then PY="$cand"; break; fi
done
if [ -z "$PY" ]; then
  echo "FATAL: no python3 found with pyyaml + certifi installed." >&2
  echo "       tried the Framework 3.12, homebrew, /usr/bin and PATH." >&2
  echo "       fix with: <interpreter> -m pip install pyyaml certifi" >&2
  exit 1
fi
echo "interpreter: $PY"

STAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "════════════════════════════════════════════════════════════"
echo "govoss-catalog run  $STAMP"
echo "════════════════════════════════════════════════════════════"

# Keep the previous catalogue as a rollback point and to diff counts against.
[ -f catalog.json ] && cp catalog.json out/catalog.prev.json

mkdir -p out
: > out/steps.tsv          # fresh per run; runlog.py reads it
STARTED=$(date -u +%Y-%m-%dT%H:%M:%SZ)
TRIGGER="${GOVOSS_TRIGGER:-manual}"

# steps.tsv is name<TAB>exit<TAB>seconds. The third column is new: the status
# page shows each step's share of the run, and nothing recorded how long a step
# took — only whether it exited 0. Duration is also the cheapest early warning
# that a source has started rate-limiting us.
step () {
  local label="$1"; shift
  local t0=$SECONDS
  echo ""
  echo "── $label ──────────────────────────────────────────"
  if "$@"; then
    printf '%s\t0\t%s\n' "$label" "$((SECONDS - t0))" >> out/steps.tsv
    return 0
  fi
  local code=$?
  printf '%s\t%s\t%s\n' "$label" "$code" "$((SECONDS - t0))" >> out/steps.tsv
  echo "!! step failed: $* (exit $code; continuing — later steps still add value)"
  return $code
}

step "harvest"      "$PY" -u harvest.py
step "enrich desc"  "$PY" -u enrich_desc.py    # fills gaps from GitHub; BEFORE translations
step "translations" "$PY" -u merge_translations.py
step "taxonomy"     "$PY" -u taxonomy.py
step "crosswalk"    "$PY" -u crosswalk.py
step "filters"      "$PY" -u filters.py
step "dedupe"       "$PY" -u dedupe.py
# AFTER dedupe: a variant claim resolves against SURVIVING entries. Pure
# recomputation, so safe to re-run; see variants.py.
step "variants"     "$PY" -u variants.py
# AFTER dedupe, so an entry is stamped under its surviving identity rather than
# under a row that is about to be merged away. Never fails the run: a missing
# date costs the "recently added" ordering, nothing else.
step "first seen"   "$PY" -u first_seen.py
step "liveness"     "$PY" -u liveness.py
step "build page"   "$PY" -u build_ui.py
step "assemble site" bash build_site.sh
step "json export"  "$PY" -u export_json.py

# ---- did the catalogue shrink unexpectedly? A source silently returning
# ---- nothing is the failure mode that looks like success.
"$PY" - <<'PY'
import json, os
cur = json.load(open("catalog.json"))
print("")
print("── summary ─────────────────────────────────────")
print(f"   entries: {len(cur)}")
if os.path.exists("out/catalog.prev.json"):
    prev = json.load(open("out/catalog.prev.json"))
    d = len(cur) - len(prev)
    print(f"   change:  {d:+d} vs previous run ({len(prev)})")
    if len(prev) and len(cur) < len(prev) * 0.9:
        print(f"   !! WARNING: catalogue shrank by more than 10%. Check whether a")
        print(f"   !! source returned empty rather than genuinely losing entries.")
    import collections
    pc = collections.Counter(r["source"] for r in prev)
    cc = collections.Counter(r["source"] for r in cur)
    for s in sorted(set(pc) | set(cc)):
        if pc.get(s, 0) != cc.get(s, 0):
            print(f"   {s}: {pc.get(s,0)} -> {cc.get(s,0)}")
lv = json.load(open("liveness.json"))["summary"]
print(f"   liveness: {lv['ok']} ok, {lv['dead']} dead, {lv['unknown']} unknown")
if lv["newly_dead"]:
    print(f"   NEWLY DEAD ({len(lv['newly_dead'])}):")
    for k in lv["newly_dead"][:10]:
        print(f"     {k}")
PY

step "run log"      "$PY" -u runlog.py "$STARTED" "$TRIGGER"
step "sources page" "$PY" -u build_sources.py   # also writes status.json
step "api page"     "$PY" -u build_api.py       # measures site/*.json, so runs after export
step "products page" "$PY" -u build_products.py # reads by-product.json, so runs after export

# ---- publish -------------------------------------------------------------
# Without this the weekly run regenerated everything and published none of it:
# the live copy silently went stale while its own status page, baked at build
# time, still read "Operational".
#
# Hosted on Cloudflare since 2026-09-23 (Workers static assets, wrangler.site.jsonc,
# account pinned there). It was Vercel; the move put DNS, site and MCP server in
# one account. The Vercel lessons carry over unchanged:
#
#  1. GATED on out/steps.tsv. A partial run overwriting a good public copy is
#     worse than a stale one — the whole point of steps.tsv is that reading the
#     end state cannot tell a failed harvest from a successful one.
#  2. The CLI *and its interpreter* are resolved, never assumed. wrangler is a
#     node script (#!/usr/bin/env node), exactly like the vercel CLI that failed
#     under launchd with "env: node: No such file or directory" — which reads as
#     an auth problem if you only look at the deploy not happening. It is the
#     copy in mcp-server/node_modules (npm install there on a fresh checkout).
#  3. A TOKEN is preferred, because a stored login can be revoked or expire and
#     would then fail every Monday. Set CLOUDFLARE_API_TOKEN in the plist, or put
#     the token alone in ~/.config/govoss/cloudflare-token (chmod 600). It needs
#     Workers Scripts:Edit on Devin@sarapis.org's Account. Without either, this
#     falls back to wrangler's stored login and says so (F7).
publish () {
  local failed
  failed=$(awk -F'\t' '$2 != "0" { printf "%s ", $1 }' out/steps.tsv)
  if [ -n "$failed" ]; then
    echo "NOT PUBLISHING — failed step(s): $failed"
    echo "  the public copy stays on the last good run; fix and re-run."
    return 1
  fi

  local WRANGLER=""
  for cand in "$PWD/mcp-server/node_modules/.bin/wrangler" "$HOME/.npm-global/bin/wrangler" \
              /opt/homebrew/bin/wrangler /usr/local/bin/wrangler "$(command -v wrangler || true)"
  do
    [ -x "$cand" ] && { WRANGLER="$cand"; break; }
  done
  if [ -z "$WRANGLER" ]; then
    echo "NOT PUBLISHING — wrangler not found (cd mcp-server && npm install)." >&2
    return 1
  fi

  # the CLI is a node script; make sure `env node` can find one.
  local NODE=""
  for cand in /usr/local/bin/node /opt/homebrew/bin/node "$(command -v node || true)" \
              "$HOME"/.nvm/versions/node/*/bin/node
  do
    [ -x "$cand" ] && { NODE="$cand"; break; }
  done
  if [ -z "$NODE" ]; then
    echo "NOT PUBLISHING — no node found; wrangler cannot run without one." >&2
    return 1
  fi
  export PATH="$(dirname "$NODE"):$PATH"

  # A missing account pin would let a cached login for another account take the
  # deploy - which happened to the MCP Worker before its account was pinned.
  if ! grep -q '"account_id"' wrangler.site.jsonc 2>/dev/null; then
    echo "NOT PUBLISHING — wrangler.site.jsonc is missing or has no account_id." >&2
    return 1
  fi

  local token="${CLOUDFLARE_API_TOKEN:-}"
  local tokfile="${CLOUDFLARE_TOKEN_FILE:-$HOME/.config/govoss/cloudflare-token}"
  local route="stored-login"
  [ -n "$token" ] && route="env:CLOUDFLARE_API_TOKEN"
  if [ -z "$token" ] && [ -r "$tokfile" ]; then
    token=$(tr -d ' \t\r\n' < "$tokfile")
    [ -n "$token" ] && route="token-file"
  fi

  # F7: which auth route this ran on, written where the status page can read it.
  # A print is not a sensor: a revoked login fails the deploy, but the only
  # outward signal is the public copy going stale and the Stale badge not
  # flipping for 8 days. Recording the route makes the weaker posture visible on
  # the run that uses it.
  mkdir -p out
  printf '%s' "$route" > out/deploy_auth.txt

  # PRE-FLIGHT: whoami distinguishes "auth is broken" from every other reason a
  # deploy fails. NON-FATAL - the deploy is the real test. ⚠ Checks CONTENT: a
  # working login prints the pinned account id; anything else is a failure,
  # whatever the exit status says.
  local who
  who=$(CLOUDFLARE_API_TOKEN="$token" "$WRANGLER" whoami 2>&1 || true)
  if printf '%s' "$who" | grep -q "a8e2fa072ede7a6389e8db8cad00f774"; then
    echo "auth: $route (Devin@sarapis.org's Account)"
  else
    echo "auth: $route — PRE-FLIGHT FAILED: $(printf '%s' "$who" | tail -2 | tr '\n' ' ')" >&2
    echo "  if the deploy now fails, this is why, and it is auth, not PATH." >&2
    if [ "$route" = "stored-login" ]; then
      echo "  wrangler's stored login looks missing or expired. Mint a token with" >&2
      echo "  Workers Scripts:Edit at https://dash.cloudflare.com/profile/api-tokens" >&2
      echo "    printf '%s' '<TOKEN>' > $tokfile && chmod 600 $tokfile" >&2
    fi
  fi

  echo "wrangler: $WRANGLER  (node $("$NODE" --version))"
  if [ "$route" = "stored-login" ]; then
    echo "no CLOUDFLARE_API_TOKEN and no $tokfile — using wrangler's stored login;"
    echo "  /sources.html carries this as a warning until a token is in place."
    "$WRANGLER" deploy --config wrangler.site.jsonc
  else
    CLOUDFLARE_API_TOKEN="$token" "$WRANGLER" deploy --config wrangler.site.jsonc
  fi
}
step "deploy" publish

# ---- record --------------------------------------------------------------
# Commit and push the run's data output, so github.com/sarapis/govoss-catalog
# reflects what is live instead of whatever was last committed by hand.
#
# Runs AFTER deploy and shares its gate, which gives the invariant worth having:
# what is committed is what is published. A run that failed a step publishes
# nothing and records nothing, so the repo never claims a state the site is not in.
#
# Deliberately narrow, because this is a PUBLIC repo and this runs unattended:
#   - stages an EXPLICIT path list, never `git add -A`. An automated `add -A` is
#     how a stray token, scratch file or half-finished edit gets published; the
#     .gitignore rules are a backstop, not the plan.
#   - refuses to run anywhere but `main`, and refuses mid-rebase/merge/bisect, so
#     it cannot commit onto work in progress.
#   - `git commit -- <paths>` scopes the commit to those paths even if something
#     else was already staged, so a human's staged edits are left alone.
#   - NEVER force-pushes. If origin moved ahead the commit stays local and says
#     so; a data file auto-rebased through a conflict is worse than a stale repo.
#   - GIT_TERMINAL_PROMPT=0: a credential prompt under launchd would hang the job
#     forever with no terminal to answer it.
DATA_PATHS=(catalog.json history.json liveness.json cache/)

record () {
  local failed
  failed=$(awk -F'\t' '$2 != "0" { printf "%s ", $1 }' out/steps.tsv)
  if [ -n "$failed" ]; then
    echo "NOT RECORDING — failed step(s): $failed"
    echo "  nothing was published, so there is nothing to record."
    return 1
  fi

  export GIT_TERMINAL_PROMPT=0

  git rev-parse --git-dir >/dev/null 2>&1 || { echo "not a git repo; skipping."; return 0; }

  local branch; branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
  if [ "$branch" != "main" ]; then
    echo "SKIPPING — on branch '$branch', not main. Not committing onto someone's work."
    return 0
  fi

  local gd; gd=$(git rev-parse --git-dir)
  if [ -d "$gd/rebase-merge" ] || [ -d "$gd/rebase-apply" ] \
     || [ -f "$gd/MERGE_HEAD" ] || [ -f "$gd/BISECT_LOG" ]; then
    echo "SKIPPING — a rebase/merge/bisect is in progress."
    return 0
  fi

  git add -- "${DATA_PATHS[@]}"
  if git diff --cached --quiet -- "${DATA_PATHS[@]}"; then
    echo "no data changes to record."
    return 0
  fi

  local msg
  msg=$("$PY" - <<'PY'
import json
h = json.load(open("history.json"))["runs"][-1]
d = h.get("delta") or {}
lv = h.get("liveness") or {}
n = h["entries"]["active"]
head = f"Data: {h['run_at'][:10]} run - {n:,} entries"
if d.get("entries_active"):
    head += f" ({d['entries_active']:+d})"
out = [head, "",
       f"Automatic record of the {h.get('trigger') or 'manual'} run that published at "
       f"{h['run_at']}. Every pipeline step exited 0 and the deploy succeeded, so what is "
       f"committed here is what is live.", ""]
for k, v in (d.get("per_source") or {}).items():
    out.append(f"  {k}: {v:+d}")
if lv.get("newly_dead"):
    out.append(f"  newly dead: {', '.join(lv['newly_dead'][:5])}")
if lv.get("revived"):
    out.append(f"  revived: {', '.join(lv['revived'][:5])}")
print("\n".join(out))
PY
)
  git commit -q -m "$msg" -- "${DATA_PATHS[@]}" || { echo "commit failed" >&2; return 1; }
  echo "committed $(git rev-parse --short HEAD)"

  if git push -q origin main 2>&1; then
    echo "pushed to origin/main"
  else
    echo "!! COMMITTED LOCALLY BUT PUSH FAILED — origin has probably moved ahead." >&2
    echo "   Not force-pushing. Resolve by hand:" >&2
    echo "     git pull --rebase origin main && git push origin main" >&2
    return 1
  fi
}
step "record" record

echo ""
echo "done  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
