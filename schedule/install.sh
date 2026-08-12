#!/bin/bash
# Render the LaunchAgent from the template and load it.
#
# The template is the single source of truth. The installed copy under
# ~/Library/LaunchAgents is DERIVED — never edit it directly, or the tracked
# template and the thing actually running drift, and the tracked one is the copy
# you will read when something breaks a year from now. That drift is the same
# failure this pipeline guards against everywhere else: a record that looks
# authoritative and is not.
#
# launchd does not expand ~ or $HOME inside a plist, so every path must be
# absolute — hence rendering rather than shipping a plist with someone's home
# directory baked into it.
#
#   bash schedule/install.sh            # render, load, show status
#   bash schedule/install.sh --diff     # show what would change, install nothing
set -euo pipefail

REPO=$(cd "$(dirname "$0")/.." && pwd)
LABEL=org.antigravity.govoss-harvest
TEMPLATE="$REPO/schedule/$LABEL.plist.template"
TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"

[ -f "$TEMPLATE" ] || { echo "missing $TEMPLATE" >&2; exit 1; }

rendered=$(sed -e "s|__HOME__|$HOME|g" -e "s|__REPO__|$REPO|g" "$TEMPLATE")

if [ "${1:-}" = "--diff" ]; then
  if [ -f "$TARGET" ]; then
    diff -u "$TARGET" <(printf '%s\n' "$rendered") && echo "installed plist matches the template."
  else
    echo "not installed yet; would create $TARGET"
  fi
  exit 0
fi

mkdir -p "$HOME/Library/LaunchAgents"
printf '%s\n' "$rendered" > "$TARGET"
plutil -lint "$TARGET"

# bootout first: bootstrap on an already-loaded label fails, and a plist edit is
# not picked up by a running job.
launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$UID" "$TARGET"

echo ""
echo "installed $TARGET"
launchctl print "gui/$UID/$LABEL" | grep -E "^\s+(state|path) " || true
echo ""
echo "run it now:  launchctl kickstart -k gui/\$UID/$LABEL"
echo "log:         $HOME/Library/Logs/govoss-harvest.log"
