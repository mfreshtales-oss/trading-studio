"""
strategy.py — SPX (S&P 500) scalping strategy.
THIS FILE IS MODIFIED BY THE AGENT.
"""

import pandas as pd

# Hypothesis: SPX clean price action suits EMA 9/21; tight stops work due to lower volatility
STRATEGY_PARAMS: dict = {
    "fast_ema": 9,
    "slow_ema": 21,

    "momentum_lookback": 5,
    "momentum_threshold": 0.001,   # SPX: ~5 pts on $5000 = 0.1% move to confirm

    "trend_ema": 50,
    "trend_filter_enabled": False,

    "min_ema_separation": 0.0003,

    "rr_ratio": 5.0,
    "risk_dollars": 10.0,          # 10-point stop on SPX (~0.2% of $5,000)

    "session_start_utc": 14,
    "session_end_utc": 17,

    "max_trades_per_day": 2,
}


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    p = STRATEGY_PARAMS
    df = df.copy()

    df["fast_ema"] = df["close"].ewm(span=p["fast_ema"], adjust=False).mean()
    df["slow_ema"] = df["close"].ewm(span=p["slow_ema"], adjust=False).mean()

    if p.get("trend_filter_enabled") and p.get("trend_ema", 0) > 0:
        df["trend_ema"] = df["close"].ewm(span=p["trend_ema"], adjust=False).mean()
    else:
        df["trend_ema"] = None

    df["ema_gap"]       = (df["fast_ema"] - df["slow_ema"]).abs() / df["slow_ema"]
    df["ema_diff"]      = df["fast_ema"] - df["slow_ema"]
    df["prev_ema_diff"] = df["ema_diff"].shift(1)
    df["cross_up"]      = (df["ema_diff"] > 0) & (df["prev_ema_diff"] <= 0)
    df["cross_down"]    = (df["ema_diff"] < 0) & (df["prev_ema_diff"] >= 0)
    df["momentum"]      = df["close"].pct_change(p["momentum_lookback"])

    separation_ok = df["ema_gap"] > p["min_ema_separation"]
    mom_long      = df["momentum"] > p["momentum_threshold"]
    mom_short     = df["momentum"] < -p["momentum_threshold"]

    long_ok  = df["cross_up"]   & mom_long  & separation_ok
    short_ok = df["cross_down"] & mom_short & separation_ok

    if p.get("trend_filter_enabled") and df["trend_ema"].notna().any():
        long_ok  = long_ok  & (df["close"] > df["trend_ema"])
        short_ok = short_ok & (df["close"] < df["trend_ema"])

    df["signal"] = 0
    df.loc[long_ok,  "signal"] = 1
    df.loc[short_ok, "signal"] = -1

    return df
