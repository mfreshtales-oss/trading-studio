# AutoResearch: US30 (Dow Jones) Strategy Optimizer
# FMP Symbol: ^DJI

## Objective
Maximize **profit_factor** on US30 (Dow Jones Industrial Average) during
the NY session while satisfying all hard constraints below.

## Hard Constraints (never violate these)
- NY session only: 14:30–17:00 UTC (9:30 AM–12:00 PM ET)
- Minimum RR per trade: 5:1
- Maximum 2 trades per day
- Minimum win rate: 35%
- Maximum weekly drawdown: 10R

## Instrument Context
- US30 moves in integer points; price range ~$36,000–$44,000
- `risk_dollars` represents points (e.g., 50 = a 50-point stop)
- Typical NY open volatility: 50–200 points in first 30 minutes
- Responds strongly to macro news (Fed, jobs, CPI) — be conservative on news days
- Trending instrument — EMA crossover suits it well
- Morning reversals after overnight gaps are common setups

## Metric to Optimize
**Primary:** `profit_factor` — higher is better. Target ≥ 2.0.
**Secondary:** `win_rate`

## Research Directions
1. **EMA tuning** — Try 5/13, 8/21, 9/21, 13/34 on 1H bars
2. **Momentum threshold** — US30 moves fast; may need higher threshold (0.002–0.005)
3. **Risk size** — Test 30, 50, 75, 100-point stops
4. **RR ratio** — Test 5:1 through 7:1 (US30 can run far on trend days)
5. **Trend filter** — Only long above 200 EMA, short below
6. **Session window** — Try 13:30–16:00 UTC for pre-open + NY session

## What NOT to Change
- backtest.py (fixed harness)
- Hard constraints above
- The data source or timeframe (1H US30)

## Hypothesis Log
Agent builds here. Motivated by results, one change at a time.
