#!/bin/bash
# Wrapper launchd calls. Loads the API key from .env and logs each run.
# Usage: deploy/run.sh weekly|daily
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"
mkdir -p logs
if [ -f .env ]; then set -a; . ./.env; set +a; fi
MODE="${1:-weekly}"
STAMP="$(date +%Y-%m-%d_%H%M)"
"$HERE/.venv/bin/gtm-mesh" cycle all --mode "$MODE" >> "logs/$STAMP-$MODE.log" 2>&1
