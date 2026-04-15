#!/usr/bin/env bash
# run_all_overnight.sh — Run AutoResearch for all 5 instruments sequentially.
#
# Each instrument gets its own result directory and experiment log.
# Runs: XAUUSD → US30 → NAS100 → SPX → BTCUSD
#
# Usage:
#   export ANTHROPIC_API_KEY=sk-ant-...
#   bash research/run_all_overnight.sh
#
# Options (env vars):
#   ITERATIONS    iterations per instrument  (default: 50)
#   TARGET_PF     target profit_factor       (default: 2.5)
#   INSTRUMENTS   space-separated list       (default: all 5)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Preflight ────────────────────────────────────────────────
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "ERROR: ANTHROPIC_API_KEY is not set."
  exit 1
fi

if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 not found."
  exit 1
fi

ITERATIONS="${ITERATIONS:-50}"
TARGET_PF="${TARGET_PF:-2.5}"
INSTRUMENTS="${INSTRUMENTS:-XAUUSD US30 NAS100 SPX BTCUSD}"

STARTED=$(date '+%Y-%m-%d %H:%M:%S')
echo "================================================================"
echo "  AutoResearch — All Instruments"
echo "  Instruments : $INSTRUMENTS"
echo "  Iterations  : $ITERATIONS each"
echo "  Target PF   : $TARGET_PF"
echo "  Started     : $STARTED"
echo "================================================================"
echo ""

# ── Install dependencies once ────────────────────────────────
echo "Installing dependencies …"
python3 -m pip install -q -r requirements.txt

# ── Fetch all missing data upfront ───────────────────────────
echo ""
echo "Checking data files …"
for SYMBOL in $INSTRUMENTS; do
  DATA_FILE="data/${SYMBOL}_1H.csv"
  if [[ ! -f "$DATA_FILE" ]]; then
    python3 fetch_data.py --symbol "$SYMBOL"
  else
    ROW_COUNT=$(tail -n +2 "$DATA_FILE" | wc -l)
    echo "  $SYMBOL: $ROW_COUNT bars already cached"
  fi
done

# ── Run each instrument ──────────────────────────────────────
RESULTS_SUMMARY=()

for SYMBOL in $INSTRUMENTS; do
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  Starting: $SYMBOL"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  python3 agent.py \
    --symbol     "$SYMBOL" \
    --iterations "$ITERATIONS" \
    --target     "$TARGET_PF" \
    && STATUS="OK" || STATUS="FAILED"

  RESULTS_SUMMARY+=("$SYMBOL: $STATUS")
done

# ── Final summary ─────────────────────────────────────────────
echo ""
echo "================================================================"
echo "  All instruments complete"
echo "  Started  : $STARTED"
echo "  Finished : $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "  Results:"
for LINE in "${RESULTS_SUMMARY[@]}"; do
  echo "    $LINE"
done
echo ""
echo "  Best strategies saved in research/results/{SYMBOL}/best_strategy.py"
echo "  Logs in research/results/{SYMBOL}/experiment_log.json"
echo "================================================================"
