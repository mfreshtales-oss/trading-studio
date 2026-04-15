# AutoResearch: SPX (S&P 500) Strategy Optimizer
# FMP Symbol: ^GSPC

## Objective
Maximize **profit_factor** on SPX (S&P 500) during the NY session while
satisfying all hard constraints below.

## Hard Constraints (never violate these)
- NY session only: 14:30–17:00 UTC (9:30 AM–12:00 PM ET)
- Minimum RR per trade: 5:1
- Maximum 2 trades per day
- Minimum win rate: 35%
- Maximum weekly drawdown: 10R

## Instrument Context
- SPX is the broadest US index — less volatile than NAS, more than bonds
- Price range ~$4,500–$5,800; typical 1H range: 10–50 points
- `risk_dollars` represents points (e.g., 10 = a 10-point stop)
- Mean-reverting tendencies between sessions, trending intraday
- Highly liquid, clean price action — signal quality tends to be good
- Sensitive to VIX; when VIX > 25, widen stops or skip short signals

## Metric to Optimize
**Primary:** `profit_factor` — higher is better. Target ≥ 2.0.
**Secondary:** `win_rate`

## Research Directions
1. **EMA tuning** — Test 9/21, 13/34, 21/55 on 1H bars
2. **Momentum threshold** — SPX moves cleanly; 0.001–0.003 range
3. **Risk size** — Test 8, 10, 15, 20-point stops (SPX tight moves)
4. **RR ratio** — 5:1–7:1; SPX has reliable follow-through on NY open
5. **Trend filter** — 50 EMA filter to avoid counter-trend trades
6. **Session window** — Widen to 13:30–17:00 UTC for pre-open flow

## What NOT to Change
- backtest.py (fixed harness)
- Hard constraints above
- The data source or timeframe (1H SPX)
