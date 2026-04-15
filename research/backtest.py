"""
backtest.py — Fixed evaluation harness. DO NOT MODIFY.

Loads XAUUSD_1H.csv, runs strategy.generate_signals(), simulates trades,
and prints a JSON metrics dict to stdout.

Exit codes:
    0  — success, metrics printed to stdout as JSON
    1  — error (data missing, strategy crash, etc.)

Usage:
    python backtest.py
    python backtest.py --data data/XAUUSD_1H.csv
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def load_strategy():
    """Dynamically load strategy.py so agent changes are always picked up."""
    strategy_path = Path(__file__).parent / "strategy.py"
    spec = importlib.util.spec_from_file_location("strategy", strategy_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, parse_dates=["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)
    return df


def filter_session(df: pd.DataFrame, start_h: int, end_h: int) -> pd.DataFrame:
    """Keep rows whose hour is in [start_h, end_h)."""
    hour = df["datetime"].dt.hour
    return df[(hour >= start_h) & (hour < end_h)].copy().reset_index(drop=True)


# ─────────────────────────────────────────────────────────────
# Core backtest
# ─────────────────────────────────────────────────────────────

def run_backtest(df: pd.DataFrame, strategy) -> dict:
    p = strategy.STRATEGY_PARAMS

    # Enforce hard constraint on RR
    if p["rr_ratio"] < 5.0:
        return {"error": f"rr_ratio={p['rr_ratio']} violates hard constraint (min 5.0)"}

    # Session filter
    df_sess = filter_session(df, p["session_start_utc"], p["session_end_utc"])
    if df_sess.empty:
        return {"error": "No bars in session window"}

    # Generate signals
    try:
        df_sig = strategy.generate_signals(df_sess)
    except Exception as exc:
        return {"error": f"generate_signals() raised: {exc}"}

    signal_col = df_sig["signal"]
    entries = df_sig[signal_col != 0].copy()

    if entries.empty:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_r": 0.0,
            "max_drawdown_r": 0.0,
            "sharpe_r": 0.0,
            "wins": 0,
            "losses": 0,
            "note": "No signals generated",
        }

    # Simulate each trade
    trades = []
    daily_counts: dict = {}
    risk = p["risk_dollars"]
    rr = p["rr_ratio"]
    max_daily = p["max_trades_per_day"]

    # Work on positional index within df_sig for look-forward
    sig_arr = df_sig.reset_index(drop=True)

    for row_idx, row in sig_arr.iterrows():
        if row["signal"] == 0:
            continue

        date_key = row["datetime"].date()
        if daily_counts.get(date_key, 0) >= max_daily:
            continue

        direction = int(row["signal"])
        entry_price = float(row["close"])

        if direction == 1:  # long
            stop   = entry_price - risk
            target = entry_price + risk * rr
        else:               # short
            stop   = entry_price + risk
            target = entry_price - risk * rr

        # Scan forward up to 100 bars for hit
        outcome = None
        for fwd in range(row_idx + 1, min(row_idx + 101, len(sig_arr))):
            bar = sig_arr.iloc[fwd]
            if direction == 1:
                if float(bar["low"])  <= stop:   outcome = "loss"; break
                if float(bar["high"]) >= target: outcome = "win";  break
            else:
                if float(bar["high"]) >= stop:   outcome = "loss"; break
                if float(bar["low"])  <= target: outcome = "win";  break

        if outcome is None:
            continue  # trade still open at end of window — skip

        r_value = rr if outcome == "win" else -1.0
        trades.append({
            "datetime":  row["datetime"].isoformat(),
            "direction": "long" if direction == 1 else "short",
            "entry":     round(entry_price, 4),
            "stop":      round(stop, 4),
            "target":    round(target, 4),
            "outcome":   outcome,
            "r":         r_value,
        })
        daily_counts[date_key] = daily_counts.get(date_key, 0) + 1

    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_r": 0.0,
            "max_drawdown_r": 0.0,
            "sharpe_r": 0.0,
            "wins": 0,
            "losses": 0,
            "note": "All signals filtered by daily limit or open at end of data",
        }

    wins   = [t for t in trades if t["outcome"] == "win"]
    losses = [t for t in trades if t["outcome"] == "loss"]

    win_rate      = len(wins) / len(trades)
    gross_profit  = sum(t["r"] for t in wins)
    gross_loss    = abs(sum(t["r"] for t in losses)) or 1e-9
    profit_factor = round(gross_profit / gross_loss, 4)
    total_r       = round(sum(t["r"] for t in trades), 2)

    # Max drawdown in R
    cumulative = np.cumsum([t["r"] for t in trades])
    peak = cumulative[0]
    max_dd = 0.0
    for val in cumulative:
        if val > peak:
            peak = val
        dd = peak - val
        if dd > max_dd:
            max_dd = dd

    # Sharpe-like ratio on per-trade R
    r_vals = np.array([t["r"] for t in trades])
    sharpe = float(r_vals.mean() / r_vals.std()) if r_vals.std() > 0 else 0.0

    return {
        "total_trades":    len(trades),
        "wins":            len(wins),
        "losses":          len(losses),
        "win_rate":        round(win_rate, 4),
        "profit_factor":   profit_factor,
        "total_r":         total_r,
        "max_drawdown_r":  round(float(max_dd), 2),
        "sharpe_r":        round(sharpe, 4),
    }


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Run XAUUSD strategy backtest")
    parser.add_argument(
        "--data",
        default=str(Path(__file__).parent / "data" / "XAUUSD_1H.csv"),
        help="Path to OHLCV CSV",
    )
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        print(
            json.dumps({"error": f"Data file not found: {data_path}. Run fetch_data.py first."}),
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        df = load_data(data_path)
    except Exception as exc:
        print(json.dumps({"error": f"Failed to load data: {exc}"}), file=sys.stderr)
        sys.exit(1)

    try:
        strategy = load_strategy()
    except Exception as exc:
        print(json.dumps({"error": f"Failed to load strategy.py: {exc}"}), file=sys.stderr)
        sys.exit(1)

    metrics = run_backtest(df, strategy)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
