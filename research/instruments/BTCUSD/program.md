# AutoResearch: BTCUSD (Bitcoin) Strategy Optimizer
# FMP Symbol: BTCUSD

## Objective
Maximize **profit_factor** on BTCUSD during the active trading window
while satisfying all hard constraints below.

## Hard Constraints (never violate these)
- Active window: 13:00–22:00 UTC (covers London close + NY full session + early evening)
- Bitcoin trades 24/7 — broader window than equity indices is intentional
- Minimum RR per trade: 5:1
- Maximum 2 trades per day
- Minimum win rate: 35%
- Maximum weekly drawdown: 10R

## Instrument Context
- BTCUSD price range ~$40,000–$100,000; typical 1H range: $200–$2,000
- `risk_dollars` is an actual dollar stop (e.g., 300 = $300 stop on Bitcoin)
- Bitcoin is highly volatile — wider stops prevent premature stopouts
- 24/7 trading but highest volume during NY session (14:30–21:00 UTC)
- Strong trending behaviour; momentum strategies work well
- Correlated with risk-on/off sentiment — watch macro context
- Overnight moves can be large — next-day sessions often continue the trend

## Metric to Optimize
**Primary:** `profit_factor` — higher is better. Target ≥ 2.0.
**Secondary:** `win_rate`

## Research Directions
1. **Risk size** — Bitcoin needs wider stops; test $200, $300, $500, $750
2. **Session window** — Test 13:00–22:00 vs 14:00–20:00 vs 00:00–23:00 (all day)
3. **EMA tuning** — Test 9/21, 13/34, 21/55 on 1H bars
4. **Momentum threshold** — BTC moves fast; 0.003–0.010 range
5. **RR ratio** — BTC trends strongly; test 5:1–10:1
6. **Trend filter** — BTC in long-term uptrend; long-only bias may help

## What NOT to Change
- backtest.py (fixed harness)
- Hard constraints above
- The data source or timeframe (1H BTCUSD)
