"""
Scout: download XAUUSD history from the local MT5 terminal and cache it as CSV.

The MetaTrader5 package talks to a RUNNING, logged-in terminal over IPC.
copy_rates_from_pos() fails with (-2, 'Invalid params') when `count`
exceeds the terminal's "Max bars in chart" setting (terminal_info().maxbars,
100000 by default), so requests are clamped just below it.

Bar timestamps are broker SERVER time (MT5 returns them as epoch seconds
in the server's zone). They are kept naive, and day boundaries everywhere
downstream use this clock -- the same one MT5 reports and prop firms use.
Prices are BID; the bar's `spread` field (points) is kept so a backtest can
reconstruct the ask side.

Run: venv/Scripts/python.exe -m core.data_ingestion.mt5_history [--count N]
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT.parent))

from gold_trading_system.core.strategies.types import Bar  # noqa: E402

DEFAULT_CACHE = PROJECT_ROOT / "data" / "history" / "XAUUSD_M15.csv"
CSV_FIELDS = ("time", "open", "high", "low", "close", "tick_volume", "spread")


class HistoryError(RuntimeError):
    pass


def fetch_from_mt5(symbol: str = "XAUUSD", timeframe: str = "M15", count: int = 99_000) -> list[Bar]:
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise HistoryError("MetaTrader5 package not installed (Windows only)") from exc

    if not mt5.initialize():
        raise HistoryError(f"mt5.initialize() failed: {mt5.last_error()} -- is the terminal running and logged in?")
    try:
        if not mt5.symbol_select(symbol, True):
            raise HistoryError(f"symbol_select({symbol}) failed: {mt5.last_error()}")
        tf = getattr(mt5, f"TIMEFRAME_{timeframe}")
        count = min(count, mt5.terminal_info().maxbars - 1)
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None or len(rates) == 0:
            raise HistoryError(f"copy_rates_from_pos({symbol}, {timeframe}, {count}) failed: {mt5.last_error()}")
    finally:
        mt5.shutdown()

    return [
        Bar(
            timestamp=datetime.fromtimestamp(int(r["time"]), timezone.utc).replace(tzinfo=None),
            open=float(r["open"]), high=float(r["high"]), low=float(r["low"]), close=float(r["close"]),
            volume=float(r["tick_volume"]), spread_points=float(r["spread"]),
        )
        for r in rates
    ]


def save_csv(bars: list[Bar], path: Path = DEFAULT_CACHE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(CSV_FIELDS)
        for b in bars:
            w.writerow((b.timestamp.isoformat(), b.open, b.high, b.low, b.close, b.volume, b.spread_points))


def load_csv(path: Path = DEFAULT_CACHE) -> list[Bar]:
    if not path.exists():
        raise HistoryError(f"{path} not found -- run: python -m core.data_ingestion.mt5_history")
    with path.open("r", encoding="utf-8") as f:
        return [
            Bar(
                timestamp=datetime.fromisoformat(row["time"]),
                open=float(row["open"]), high=float(row["high"]), low=float(row["low"]),
                close=float(row["close"]), volume=float(row["tick_volume"]),
                spread_points=float(row["spread"]),
            )
            for row in csv.DictReader(f)
        ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="M15")
    parser.add_argument("--count", type=int, default=99_000)
    parser.add_argument("--out", type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args()

    bars = fetch_from_mt5(args.symbol, args.timeframe, args.count)
    save_csv(bars, args.out)
    print(f"saved {len(bars)} bars {bars[0].timestamp} -> {bars[-1].timestamp} to {args.out}")


if __name__ == "__main__":
    main()
