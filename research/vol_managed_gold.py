"""Vol-managed long gold vs matched-exposure buy & hold.

Implements research/PREREG_vol_managed_gold.md (commits 55dc5a3, d499272) literally.

Mechanics the pre-reg leaves implicit, fixed here before the first run:
  M1  Daily close = close of the last H4 bar of each calendar date (server time).
  M2  sigma_t may use returns from before a window's start (past data, no look-ahead).
      The IS window can only start trading once 20 returns exist (day 21 of the data).
  M3  Between rebalances the position is held in ounces, so the realised weight drifts with
      price. The band test compares the target with this realised weight.
  M4  If the current position is zero, any non-zero target is traded (band undefined at 0).
  M5  Per traded lot (100 oz), each side pays half the 35-point spread ($17.50) plus half the
      $6 commission ($3.00).
  M6  Swap is charged at each daily close on the ounces held into the next day: 3 nights if
      that close is a Wednesday, else 1.
  M7  The benchmark buys w_bar * $10,000 of gold at the window's first close (paying one side
      of costs), holds the ounces unchanged, and pays swap like the treatment. w_bar is the
      treatment's mean realised weight over the window's daily closes.
  M8  Final marks are not closed out (no exit cost) for either side.

Usage:  python research/vol_managed_gold.py path/to/XAUUSD_H4.csv
Writes research/results/vol_managed_gold.json and refuses to overwrite it.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
import sys
from datetime import date, datetime
from pathlib import Path

CAPITAL = 10_000.0
SIGMA_TARGET, C_MAX, LOOKBACK, BAND = 0.15, 1.0, 20, 0.20
OZ_PER_LOT = 100.0
COST_PER_LOT_SIDE = 35 * 0.01 * OZ_PER_LOT / 2 + 6.0 / 2       # $17.50 + $3.00
SWAP_PTS, SWAP_REF = -12.6, 4147.62                              # points/lot/night, price-scaled
WINDOWS = {"IS": (date(2004, 6, 11), date(2020, 2, 17)), "OOS": (date(2020, 2, 17), None)}
OUT = Path(__file__).resolve().parent / "results" / "vol_managed_gold.json"


def daily_closes(path: str) -> list[tuple[date, float]]:
    last: dict[date, float] = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            last[datetime.fromisoformat(row["time"]).date()] = float(row["close"])
    return sorted(last.items())


def swap_per_oz(price: float, d: date) -> float:
    nights = 3 if d.weekday() == 2 else 1
    return SWAP_PTS * 0.01 * (price / SWAP_REF) * nights           # $ per oz (negative)


def metrics(equity: list[float]) -> dict:
    rets = [equity[i] / equity[i - 1] - 1 for i in range(1, len(equity))]
    sd = statistics.stdev(rets)
    peak, mdd = equity[0], 0.0
    for e in equity:
        peak = max(peak, e)
        mdd = max(mdd, 1 - e / peak)
    years = len(rets) / 252
    cagr = (equity[-1] / equity[0]) ** (1 / years) - 1
    return {"sharpe": statistics.fmean(rets) / sd * math.sqrt(252), "max_dd": mdd, "cagr": cagr,
            "calmar": cagr / mdd if mdd else None, "final": equity[-1], "days": len(rets)}


def run_window(days: list[tuple[date, float]], start: date, end: date | None) -> dict:
    logr = [math.log(days[i][1] / days[i - 1][1]) for i in range(1, len(days))]   # logr[i-1] ends day i
    idx = [i for i, (d, _) in enumerate(days) if d >= start and (end is None or d < end) and i >= LOOKBACK + 1]
    # treatment
    cash, oz, eq_t, weights, traded_lots, week = CAPITAL, 0.0, [], [], 0.0, None
    for k, i in enumerate(idx):
        d, p = days[i]
        equity = cash + oz * p
        wk = d.isocalendar()[:2]
        if wk != week:                                    # first daily close of the week
            week = wk
            sigma = statistics.stdev(logr[i - 1 - LOOKBACK:i - 1]) * math.sqrt(252)   # returns to day t-1
            w_tgt = min(C_MAX, SIGMA_TARGET / sigma)
            w_cur = oz * p / equity
            if (w_cur == 0 and w_tgt > 0) or (w_cur > 0 and abs(w_tgt - w_cur) / w_cur > BAND):
                new_oz = w_tgt * equity / p
                lots = abs(new_oz - oz) / OZ_PER_LOT
                cash -= (new_oz - oz) * p + lots * COST_PER_LOT_SIDE
                traded_lots += lots
                oz = new_oz
        equity = cash + oz * p
        eq_t.append(equity)
        weights.append(oz * p / equity)
        cash += oz * swap_per_oz(p, d)                    # held overnight into next day
    w_bar = statistics.fmean(weights)
    # benchmark: static ounces bought at the first close
    d0, p0 = days[idx[0]]
    oz_b = w_bar * CAPITAL / p0
    cash_b = CAPITAL - oz_b * p0 - oz_b / OZ_PER_LOT * COST_PER_LOT_SIDE
    eq_b = []
    for i in idx:
        d, p = days[i]
        eq_b.append(cash_b + oz_b * p)
        cash_b += oz_b * swap_per_oz(p, d)
    t, b = metrics(eq_t), metrics(eq_b)
    return {"start": str(days[idx[0]][0]), "end": str(days[idx[-1]][0]), "w_bar": w_bar,
            "turnover_lots": traded_lots, "treatment": t, "benchmark": b,
            "pass_sharpe": t["sharpe"] > b["sharpe"], "pass_dd": t["max_dd"] <= b["max_dd"]}


def main() -> None:
    if OUT.exists():
        sys.exit(f"REFUSED: {OUT} exists; this test runs once")
    days = daily_closes(sys.argv[1])
    res = {name: run_window(days, *w) for name, w in WINDOWS.items()}
    res["verdict"] = "PASS" if all(r["pass_sharpe"] and r["pass_dd"] for r in res.values()) else "FAIL"
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
