#!/bin/bash
# Full pipeline: harvest -> translate -> categorise -> liveness -> page.
#
# Ordering matters and is not arbitrary:
#   harvest      rewrites catalog.json from the eight national sources
#   merge        re-applies stored translations (keyed on sha1 of source text,
#                so they survive a re-harvest as long as upstream wording is)
#   taxonomy     re-derives functions; must run AFTER merge because the keyword
#                inference reads the English description
#   filters      flags non-software (forks, CI plumbing, deployment recipes) as
#                excluded; runs AFTER taxonomy so hidden rows still carry
#                functions for when the UI toggle reveals them
#   dedupe       merges records for the same software (QID, then repo URL). Must
#                run AFTER filters so forks are already gone, and BEFORE export
#   liveness     diffs against the previous liveness.json to find newly-dead repos
#   build_ui     regenerates catalogue.html from the finished catalog.json
#   build_site   assembles site/ from tracked sources (html + vercel.json)
#   json export  writes site/entries.json + meta.json + by-product + by-category
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

step () {
  echo ""
  echo "── $1 ──────────────────────────────────────────"
  shift
  if ! "$@"; then
    echo "!! step failed: $* (continuing — later steps still add value)"
    return 1
  fi
}

step "harvest"      "$PY" -u harvest.py
step "translations" "$PY" -u merge_translations.py
step "taxonomy"     "$PY" -u taxonomy.py
step "filters"      "$PY" -u filters.py
step "dedupe"       "$PY" -u dedupe.py
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

echo ""
echo "done  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
