#!/usr/bin/env bash
# run_overnight.sh — Run AutoResearch for a single instrument.
#
# Usage:
#   export ANTHROPIC_API_KEY=sk-ant-...
#   SYMBOL=XAUUSD bash research/run_overnight.sh
#   SYMBOL=US30   bash research/run_overnight.sh
#   SYMBOL=NAS100 bash research/run_overnight.sh
#   SYMBOL=SPX    bash research/run_overnight.sh
#   SYMBOL=BTCUSD bash research/run_overnight.sh
#
# Options (env vars):
#   SYMBOL        instrument to optimize   (default: XAUUSD)
#   ITERATIONS    max agent iterations     (default: 100)
#   TARGET_PF     target profit_factor     (default: 2.5)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SYMBOL="${SYMBOL:-XAUUSD}"

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

VALID_SYMBOLS="XAUUSD US30 NAS100 SPX BTCUSD"
if [[ ! " $VALID_SYMBOLS " =~ " $SYMBOL " ]]; then
  echo "ERROR: Unknown symbol '$SYMBOL'. Valid: $VALID_SYMBOLS"
  exit 1
fi

# ── Install dependencies ─────────────────────────────────────
echo "Installing dependencies …"
python3 -m pip install -q -r requirements.txt

# ── Fetch data if not already present ───────────────────────
DATA_FILE="data/${SYMBOL}_1H.csv"
if [[ ! -f "$DATA_FILE" ]]; then
  echo "Fetching historical $SYMBOL data …"
  python3 fetch_data.py --symbol "$SYMBOL"
else
  ROW_COUNT=$(tail -n +2 "$DATA_FILE" | wc -l)
  echo "Using existing data: $DATA_FILE  ($ROW_COUNT bars)"
fi

# ── Launch agent loop ────────────────────────────────────────
ITERATIONS="${ITERATIONS:-100}"
TARGET_PF="${TARGET_PF:-2.5}"

echo ""
echo "Starting AutoResearch loop"
echo "  Symbol     : $SYMBOL"
echo "  Iterations : $ITERATIONS"
echo "  Target PF  : $TARGET_PF"
echo ""

python3 agent.py --symbol "$SYMBOL" --iterations "$ITERATIONS" --target "$TARGET_PF"
