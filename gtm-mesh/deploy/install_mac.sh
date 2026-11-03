#!/bin/bash
# One-time setup on the Mac Mini: venv, package, and the weekly + daily schedules.
# Usage: ./deploy/install_mac.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"

python3 -m venv .venv
.venv/bin/pip install --upgrade pip >/dev/null
.venv/bin/pip install -e . >/dev/null
mkdir -p logs

if [ ! -f .env ]; then
  echo "ANTHROPIC_API_KEY=" > .env
  chmod 600 .env
  echo "Created .env - paste the client's Anthropic API key into it."
fi

AGENTS="$HOME/Library/LaunchAgents"
mkdir -p "$AGENTS"
for f in deploy/launchd/*.plist; do
  name="$(basename "$f")"
  sed "s#__MESH_HOME__#$HERE#g" "$f" > "$AGENTS/$name"
  launchctl bootout "gui/$(id -u)/${name%.plist}" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$AGENTS/$name"
  echo "Scheduled ${name%.plist}"
done
echo "Done. Test a run now with: deploy/run.sh daily && tail -n 50 logs/*.log"
echo "Tip: System Settings > Energy > 'Prevent automatic sleeping' so scheduled runs fire."
