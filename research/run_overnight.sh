#!/usr/bin/env bash
# run_overnight.sh — Set up and launch the AutoResearch loop.
#
# Usage:
#   export ANTHROPIC_API_KEY=sk-ant-...
#   bash research/run_overnight.sh
#
# Options (env vars):
#   ITERATIONS    max agent iterations   (default: 100)
#   TARGET_PF     target profit_factor   (default: 2.5)
#   FMP_API_KEY   override FMP API key   (optional)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Preflight checks ─────────────────────────────────────────
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "ERROR: ANTHROPIC_API_KEY is not set."
  echo "       export ANTHROPIC_API_KEY=sk-ant-..."
  exit 1
fi

if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 not found."
  exit 1
fi

# ── Install dependencies ─────────────────────────────────────
echo "Installing dependencies …"
python3 -m pip install -q -r requirements.txt

# ── Fetch data if not already present ───────────────────────
DATA_FILE="data/XAUUSD_1H.csv"
if [[ ! -f "$DATA_FILE" ]]; then
  echo "Fetching historical XAUUSD data …"
  python3 fetch_data.py
else
  ROW_COUNT=$(tail -n +2 "$DATA_FILE" | wc -l)
  echo "Using existing data: $DATA_FILE  ($ROW_COUNT bars)"
fi

# ── Launch agent loop ────────────────────────────────────────
ITERATIONS="${ITERATIONS:-100}"
TARGET_PF="${TARGET_PF:-2.5}"

echo ""
echo "Starting AutoResearch loop"
echo "  Iterations : $ITERATIONS"
echo "  Target PF  : $TARGET_PF"
echo ""

python3 agent.py --iterations "$ITERATIONS" --target "$TARGET_PF"
