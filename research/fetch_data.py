"""
fetch_data.py — Pull historical 1H OHLCV data from FMP for any supported instrument.

Usage:
    python fetch_data.py                          # fetches all 5 instruments
    python fetch_data.py --symbol XAUUSD
    python fetch_data.py --symbol US30 --from 2023-01-01 --to 2024-12-31

Supported symbols: XAUUSD, US30, NAS100, SPX, BTCUSD
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
    "3r9vq1WORcFNCxoL6OimVbTuUP4VpamD",
)
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Map clean instrument names → FMP API symbols
FMP_SYMBOL_MAP: dict[str, str] = {
    "XAUUSD": "XAUUSD",
    "US30":   "^DJI",
    "NAS100": "^IXIC",
    "SPX":    "^GSPC",
    "BTCUSD": "BTCUSD",
}

ALL_INSTRUMENTS = list(FMP_SYMBOL_MAP.keys())


def fetch_historical_1h(
    instrument: str, from_date: str, to_date: str
) -> pd.DataFrame | None:
    """Fetch 1-hour OHLCV bars for a clean instrument name (e.g. 'US30')."""
    fmp_symbol = FMP_SYMBOL_MAP.get(instrument)
    if fmp_symbol is None:
        print(f"ERROR: Unknown instrument '{instrument}'. Supported: {ALL_INSTRUMENTS}")
        return None

    url = f"https://financialmodelingprep.com/stable/historical-chart/1hour/{fmp_symbol}"
    params = {"from": from_date, "to": to_date, "apikey": FMP_API_KEY}

    print(f"Fetching {instrument} ({fmp_symbol}) 1H data {from_date} → {to_date} …")
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"ERROR: HTTP request failed: {e}", file=sys.stderr)
        return None

    raw = resp.json()
    if not raw:
        print(f"ERROR: FMP returned empty response for {fmp_symbol}.")
        return None

    df = pd.DataFrame(raw)
    df = df.rename(columns={"date": "datetime"})
    df["datetime"] = pd.to_datetime(df["datetime"])

    keep = [c for c in ["datetime", "open", "high", "low", "close", "volume"] if c in df.columns]
    df = df[keep].sort_values("datetime").reset_index(drop=True)

    for col in ["open", "high", "low", "close"]:
        if col in df.columns:
            df[col] = df[col].astype(float)

    return df


def fetch_and_save(instrument: str, from_date: str, to_date: str) -> bool:
    df = fetch_historical_1h(instrument, from_date, to_date)
    if df is None:
        return False

    output_path = DATA_DIR / f"{instrument}_1H.csv"
    df.to_csv(output_path, index=False)

    print(f"  Saved {len(df):,} rows → {output_path}")
    print(f"  Date range : {df['datetime'].min()}  →  {df['datetime'].max()}")
    print(f"  Price range: {df['close'].min():,.2f}  –  {df['close'].max():,.2f}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch historical OHLCV data from FMP")
    parser.add_argument(
        "--symbol",
        default=None,
        help=f"Instrument name. One of: {ALL_INSTRUMENTS}. Omit to fetch all.",
    )
    parser.add_argument("--from", dest="from_date", default="2023-01-01")
    parser.add_argument("--to",   dest="to_date",   default="2024-12-31")
    args = parser.parse_args()

    targets = [args.symbol] if args.symbol else ALL_INSTRUMENTS
    failed  = []

    for instrument in targets:
        print()
        ok = fetch_and_save(instrument, args.from_date, args.to_date)
        if not ok:
            failed.append(instrument)

    if failed:
        print(f"\nWARNING: Failed to fetch: {failed}")
        sys.exit(1)
    else:
        print(f"\nAll done. Data saved to {DATA_DIR}/")


if __name__ == "__main__":
    main()
