# AutoResearch: XAUUSD Scalping Strategy Optimizer

## Objective
Maximize **profit_factor** on XAUUSD (Gold Spot) during the NY session
while satisfying all hard constraints below.

## Hard Constraints (never violate these)
- NY session only: 14:30–17:00 UTC (9:30 AM–12:00 PM ET)
- Minimum RR per trade: 5:1
- Maximum 2 trades per day
- Minimum win rate: 35% (below this, the strategy is not tradeable)
- Maximum weekly drawdown: 10R

## Metric to Optimize
**Primary:** `profit_factor` (gross profit / gross loss) — higher is better.
A profit_factor above 2.0 is considered good; above 3.0 is excellent.

**Secondary (tiebreaker):** `win_rate`

## Current Baseline
profit_factor: (see results/experiment_log.json after first run)

## Research Directions for the Agent
Explore these ideas one at a time, most promising first:

1. **EMA tuning** — Try different fast/slow EMA combinations (e.g., 5/13, 8/21, 9/21, 13/34, 21/55)
2. **Momentum threshold** — Higher threshold = fewer but higher-quality signals
3. **Session window** — Narrow or widen the NY session entry window
4. **RR ratio** — Test 5:1 through 8:1 in 0.5 increments
5. **Risk size** — Try ATR-based risk (5–20 pips) vs fixed
6. **EMA separation filter** — Require EMAs to be a minimum % apart before entry
7. **Trend filter** — Only take longs when price is above 50 EMA, shorts below

## What NOT to Change
- The backtesting framework (backtest.py) — it is fixed
- Hard constraints above — they are non-negotiable
- The data source or timeframe (1H XAUUSD)

## Hypothesis Log
The agent should build on previous experiment results.
Each modification should be motivated by a clear hypothesis.
If an experiment fails, understand why before trying the next idea.
