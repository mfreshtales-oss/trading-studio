"""
strategy.py — XAUUSD scalping strategy.

THIS FILE IS MODIFIED BY THE AGENT. Do not hand-edit unless resetting.

The agent tunes STRATEGY_PARAMS and may rewrite generate_signals(),
but must never violate the hard constraints in program.md.
"""

import pandas as pd

# ─────────────────────────────────────────────────────────────
# STRATEGY PARAMS  ← agent edits this dict
# ─────────────────────────────────────────────────────────────
STRATEGY_PARAMS: dict = {
    # EMA periods
    "fast_ema": 9,
    "slow_ema": 21,

    # Momentum confirmation
    "momentum_lookback": 5,        # bars to look back
    "momentum_threshold": 0.0015,  # minimum % price move to confirm

    # Trend filter: only trade in direction of this slower EMA
    "trend_ema": 50,               # set to 0 to disable
    "trend_filter_enabled": False,

    # EMA separation: require a minimum gap between fast/slow before entry
    "min_ema_separation": 0.0005,  # as a fraction of slow_ema price

    # Risk / Reward  (must stay >= 5.0 per program.md)
    "rr_ratio": 5.0,

    # Stop size in price units ($)  e.g. 1.5 = $1.50 stop on XAUUSD
    "risk_dollars": 1.50,

    # Session filter (UTC hour, inclusive start, exclusive end)
    "session_start_utc": 14,       # 9:30 AM ET ≈ 14:30 UTC
    "session_end_utc": 17,         # 12:00 PM ET ≈ 17:00 UTC

    # Max trades per calendar day
    "max_trades_per_day": 2,
}


# ─────────────────────────────────────────────────────────────
# SIGNAL GENERATION  ← agent may rewrite this function
# ─────────────────────────────────────────────────────────────
def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add trading signals to df.

    Args:
        df: DataFrame with columns [datetime, open, high, low, close, volume].
            Already filtered to session hours by backtest.py.

    Returns:
        Same df with extra columns:
            fast_ema, slow_ema — indicator values
            signal             — 1=long entry, -1=short entry, 0=no trade
    """
    p = STRATEGY_PARAMS
    df = df.copy()

    # ── Indicators ─────────────────────────────────────────
    df["fast_ema"] = df["close"].ewm(span=p["fast_ema"], adjust=False).mean()
    df["slow_ema"] = df["close"].ewm(span=p["slow_ema"], adjust=False).mean()

    # Optional trend filter
    if p.get("trend_filter_enabled") and p.get("trend_ema", 0) > 0:
        df["trend_ema"] = df["close"].ewm(span=p["trend_ema"], adjust=False).mean()
    else:
        df["trend_ema"] = None

    # EMA gap as a fraction of price
    df["ema_gap"] = (df["fast_ema"] - df["slow_ema"]).abs() / df["slow_ema"]

    # Crossover detection
    df["ema_diff"] = df["fast_ema"] - df["slow_ema"]
    df["prev_ema_diff"] = df["ema_diff"].shift(1)
    df["cross_up"] = (df["ema_diff"] > 0) & (df["prev_ema_diff"] <= 0)
    df["cross_down"] = (df["ema_diff"] < 0) & (df["prev_ema_diff"] >= 0)

    # Momentum (% change over lookback bars)
    df["momentum"] = df["close"].pct_change(p["momentum_lookback"])

    # ── Entry conditions ────────────────────────────────────
    separation_ok = df["ema_gap"] > p["min_ema_separation"]
    mom_long = df["momentum"] > p["momentum_threshold"]
    mom_short = df["momentum"] < -p["momentum_threshold"]

    long_ok = df["cross_up"] & mom_long & separation_ok
    short_ok = df["cross_down"] & mom_short & separation_ok

    # Apply optional trend filter
    if p.get("trend_filter_enabled") and df["trend_ema"].notna().any():
        long_ok = long_ok & (df["close"] > df["trend_ema"])
        short_ok = short_ok & (df["close"] < df["trend_ema"])

    df["signal"] = 0
    df.loc[long_ok, "signal"] = 1
    df.loc[short_ok, "signal"] = -1

    return df
