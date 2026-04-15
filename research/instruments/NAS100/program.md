# AutoResearch: NAS100 (Nasdaq Composite) Strategy Optimizer
# FMP Symbol: ^IXIC

## Objective
Maximize **profit_factor** on NAS100 during the NY session while satisfying
all hard constraints below.

## Hard Constraints (never violate these)
- NY session only: 14:30–17:00 UTC (9:30 AM–12:00 PM ET)
- Minimum RR per trade: 5:1
- Maximum 2 trades per day
- Minimum win rate: 35%
- Maximum weekly drawdown: 10R

## Instrument Context
- NAS100 is tech-heavy, more volatile than US30 and SPX
- Price range ~$14,000–$20,000; moves 100–400 points on active days
- `risk_dollars` represents points (e.g., 30 = a 30-point stop)
- Higher beta — trends more aggressively but also reverses harder
- Very sensitive to rate expectations and big-tech earnings
- Morning momentum trades (first 60–90 mins of NY) work well
- Gap fills are common — watch overnight levels

## Metric to Optimize
**Primary:** `profit_factor` — higher is better. Target ≥ 2.0.
**Secondary:** `win_rate`

## Research Directions
1. **EMA tuning** — Try faster combinations: 5/13, 8/21, 9/21
2. **Momentum threshold** — NAS moves fast; test 0.002–0.004
3. **Risk size** — Test 20, 30, 50-point stops
4. **RR ratio** — NAS100 trends hard; test 5:1–8:1
5. **Trend filter** — Strong trending instrument, filter aligns well
6. **Separation filter** — Higher gap requirement may filter noise on choppy days

## What NOT to Change
- backtest.py (fixed harness)
- Hard constraints above
- The data source or timeframe (1H NAS100)
