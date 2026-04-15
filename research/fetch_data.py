"""
fetch_data.py — Pull historical XAUUSD 1H OHLCV data from FMP.

Usage:
    python fetch_data.py
    python fetch_data.py --symbol XAUUSD --from 2023-01-01 --to 2024-12-31

FMP_API_KEY is read from the environment (or falls back to the project key).
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
import requests

FMP_API_KEY = os.environ.get(
    "FMP_API_KEY",
    "3r9vq1WORcFNCxoL6OimVbTuUP4VpamD",  # same key used in index.html
)
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def fetch_historical_1h(symbol: str, from_date: str, to_date: str) -> pd.DataFrame | None:
    """Fetch 1-hour OHLCV bars from FMP stable endpoint."""
    url = f"https://financialmodelingprep.com/stable/historical-chart/1hour/{symbol}"
    params = {"from": from_date, "to": to_date, "apikey": FMP_API_KEY}

    print(f"Fetching {symbol} 1H data {from_date} → {to_date} …")
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"ERROR: HTTP request failed: {e}", file=sys.stderr)
        return None

    raw = resp.json()
    if not raw:
        print("ERROR: FMP returned empty response. Check symbol name and API key.")
        return None

    df = pd.DataFrame(raw)

    # Normalise column names
    rename = {"date": "datetime"}
    df = df.rename(columns=rename)
    df["datetime"] = pd.to_datetime(df["datetime"])

    # Keep only OHLCV + datetime
    keep = [c for c in ["datetime", "open", "high", "low", "close", "volume"] if c in df.columns]
    df = df[keep].sort_values("datetime").reset_index(drop=True)

    # Cast price columns to float
    for col in ["open", "high", "low", "close"]:
        if col in df.columns:
            df[col] = df[col].astype(float)

    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch historical OHLCV data from FMP")
    parser.add_argument("--symbol", default="XAUUSD", help="FMP symbol (default: XAUUSD)")
    parser.add_argument("--from", dest="from_date", default="2023-01-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", default="2024-12-31", help="End date YYYY-MM-DD")
    args = parser.parse_args()

    df = fetch_historical_1h(args.symbol, args.from_date, args.to_date)
    if df is None:
        sys.exit(1)

    output_path = DATA_DIR / f"{args.symbol}_1H.csv"
    df.to_csv(output_path, index=False)

    print(f"\nSaved {len(df):,} rows → {output_path}")
    print(f"Date range : {df['datetime'].min()}  →  {df['datetime'].max()}")
    print(f"Price range: ${df['close'].min():,.2f}  –  ${df['close'].max():,.2f}")
    print(f"\nSample (first 3 rows):\n{df.head(3).to_string(index=False)}")


if __name__ == "__main__":
    main()
