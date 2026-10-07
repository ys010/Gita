"""Download daily Open/Close prices for TBLA (Taboola) from Yahoo Finance.

Usage:
    pip install yfinance
    python get_tbla.py [START] [END]      # dates as YYYY-MM-DD, both optional
"""
import sys

import yfinance as yf

TICKER = "TBLA"


def main():
    start = sys.argv[1] if len(sys.argv) > 1 else None
    end = sys.argv[2] if len(sys.argv) > 2 else None

    kwargs = {"start": start, "end": end} if start else {"period": "max"}
    if start and end is None:
        kwargs.pop("end")

    df = yf.download(TICKER, auto_adjust=False, progress=False, **kwargs)
    if df.empty:
        sys.exit(f"No data returned for {TICKER}")

    # Newer yfinance versions return MultiIndex columns even for one ticker
    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)

    out = df[["Open", "Close"]]
    out.to_csv("tbla_open_close.csv")
    print(out.head(3))
    print(out.tail(3))
    print(f"Saved {len(out)} rows to tbla_open_close.csv")


if __name__ == "__main__":
    main()
