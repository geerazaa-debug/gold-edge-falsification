"""
Option B (pre-registered in reports/STATE_SNAPSHOT.md, milestone 6):
H4 mtf_pullback behind Shield vs Buy & Hold gold, same bars, same costs.

Single pass by design: no parameters, no grid. Both sides run through the
same engine (core/backtester/m15_engine.py) so spread, commission, swap and
drawdown are measured identically. Buy & Hold = one long at 1x notional
($10,000 / (price x 100 oz), floored to 0.01 lot), entered on bar 1's open
(the engine fills bar 0's signal at the next open) and held to the end.

Writes reports/buy_hold_overlay_H4.json and appends its table to
reports/tournament_report_H4.md.

Run: venv/Scripts/python.exe skills/run_buy_hold_overlay.py
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT.parent))

from gold_trading_system.core.backtester.m15_engine import (  # noqa: E402
    BacktestResult,
    FixedLot,
    ShieldSizing,
    compute_metrics,
    run_backtest,
)
from gold_trading_system.core.strategies.m15_trend import EntrySignal  # noqa: E402
from gold_trading_system.core.strategies.types import Side  # noqa: E402
from gold_trading_system.skills.run_backtest_tournament import (  # noqa: E402
    build_context,
    load_bars,
    load_config,
    report_path,
)

CAPITAL = 10_000.0
SWAP_PRICE_REF = 4147.62  # XAUUSD bid when the demo swap was read, 2026-10-04
BEGIN, END = "<!-- buy-hold-overlay:begin -->", "<!-- buy-hold-overlay:end -->"


class BuyAndHold:
    """Long on the first bar, never exits; the stop is set just above zero."""

    name = "buy_and_hold"

    def __init__(self, first_close: float, point: float) -> None:
        self._stop_points = first_close * 0.99 / point

    def entry_signal(self, i: int) -> EntrySignal | None:
        return EntrySignal(Side.BUY, self._stop_points, None) if i == 0 else None

    def exit_signal(self, i: int, side: Side) -> bool:
        return False

    def trail_stop(self, i, side, entry, initial_risk, best):
        return None


def curve_stats(res: BacktestResult) -> dict:
    """CAGR, Sharpe, Sortino from the daily equity curve."""
    d0, d1 = res.daily_equity[0][0], res.daily_equity[-1][0]
    years = max((d1 - d0).days / 365.25, 1e-9)
    equities = [e for _, e in res.daily_equity]
    rets = [(b - a) / a for a, b in zip(equities, equities[1:]) if a > 0]
    mean = statistics.fmean(rets) if rets else 0.0
    std = statistics.stdev(rets) if len(rets) > 1 else 0.0
    downside = math.sqrt(sum(min(r, 0.0) ** 2 for r in rets) / len(rets)) if rets else 0.0
    start = res.initial_equity
    return {
        "cagr_pct": round(((res.final_equity / start) ** (1 / years) - 1) * 100, 2) if res.final_equity > 0 else -100.0,
        "sharpe": round(mean / std * math.sqrt(252), 2) if std else 0.0,
        "sortino": round(mean / downside * math.sqrt(252), 2) if downside else 0.0,
        "years": round(years, 2),
    }


def evaluate(strat: dict, bh: dict) -> dict:
    dd_ok = strat["max_equity_dd_pct"] <= 0.70 * bh["max_equity_dd_pct"]
    if bh["cagr_pct"] > 0:
        cagr_ok = strat["cagr_pct"] >= 0.70 * bh["cagr_pct"]
    else:
        cagr_ok = strat["cagr_pct"] >= bh["cagr_pct"]
    return {"dd_ok": dd_ok, "cagr_ok": cagr_ok, "pass": dd_ok and cagr_ok}


def summarize(res: BacktestResult) -> dict:
    m = compute_metrics(res)
    keys = ("final_equity", "return_pct", "max_equity_dd_pct", "trades", "profit_factor", "win_rate_pct",
            "killed", "breaker_trips")
    return {**{k: m[k] for k in keys}, **curve_stats(res)}


def to_markdown(rows: list[dict], verdict: bool) -> str:
    lines = [BEGIN, "## Option B -- H4 mtf_pullback vs Buy & Hold (pre-registered, single pass)", "",
             "| Window | Swap model | System | CAGR % | Max DD % | Sharpe | Sortino | Return % | Trades | PF | Notes |",
             "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in rows:
        for name, m in (("mtf_pullback + Shield", r["strategy"]), ("Buy & Hold", r["buy_hold"])):
            note = "KILLED" if m["killed"] else ""
            lines.append(f"| {r['window']} | {r['swap']} | {name} | {m['cagr_pct']:.2f} | {m['max_equity_dd_pct']:.2f} | "
                         f"{m['sharpe']:.2f} | {m['sortino']:.2f} | {m['return_pct']:.1f} | {m['trades']} | "
                         f"{m['profit_factor'] if m['profit_factor'] is not None else '-'} | {note} |")
        c = r["criteria"]
        lines.append(f"| {r['window']} | {r['swap']} | **criteria** | {'ok' if c['cagr_ok'] else 'FAIL'} | "
                     f"{'ok' if c['dd_ok'] else 'FAIL'} | | | | | | {'PASS' if c['pass'] else 'FAIL'} |")
    lines += ["", f"**Overall: {'PASS' if verdict else 'FAIL'}** (all windows x swap models must pass)", END]
    return "\n".join(lines) + "\n"


def main() -> None:
    cfg = load_config("H4")
    ctx = build_context(cfg, load_bars(cfg, refresh=False))
    shield = ShieldSizing(ctx.limits)
    rows = []
    for swap_name, costs in (("fixed", ctx.costs), ("price-scaled", replace(ctx.costs, swap_price_ref=SWAP_PRICE_REF))):
        for window in ("IS", "OOS"):
            bars = ctx.windows[window]
            strat_res = run_backtest(bars, ctx.strategy("mtf_pullback", window), shield, CAPITAL, costs, ctx.inst)
            lot = math.floor(CAPITAL / (bars[0].close * costs.contract_size) / ctx.inst.lot_step) * ctx.inst.lot_step
            bh_res = run_backtest(bars, BuyAndHold(bars[0].close, ctx.inst.point), FixedLot(round(lot, 2)),
                                  CAPITAL, costs, ctx.inst)
            strat, bh = summarize(strat_res), summarize(bh_res)
            rows.append({"window": window, "swap": swap_name, "period": f"{bars[0].timestamp:%Y-%m-%d} -> "
                         f"{bars[-1].timestamp:%Y-%m-%d}", "bh_lot": round(lot, 2), "strategy": strat,
                         "buy_hold": bh, "criteria": evaluate(strat, bh)})
            r = rows[-1]
            print(f"{window:3s} {swap_name:12s} strat CAGR {strat['cagr_pct']:6.2f}% DD {strat['max_equity_dd_pct']:6.2f}% "
                  f"| B&H CAGR {bh['cagr_pct']:6.2f}% DD {bh['max_equity_dd_pct']:6.2f}% (lot {r['bh_lot']}) "
                  f"-> {'PASS' if r['criteria']['pass'] else 'FAIL'} {r['criteria']}")

    verdict = all(r["criteria"]["pass"] for r in rows)
    print(f"\nOVERALL: {'PASS' if verdict else 'FAIL'}")
    out = report_path("buy_hold_overlay", "H4", ".json")
    out.write_text(json.dumps({"overall_pass": verdict, "rows": rows}, indent=2, default=str), encoding="utf-8")

    block = to_markdown(rows, verdict)
    md = report_path("tournament_report", "H4", ".md")
    text = md.read_text(encoding="utf-8") if md.exists() else ""
    if BEGIN in text:
        text = text[: text.index(BEGIN)] + block + text[text.index(END) + len(END) + 1:]
    else:
        text = text.rstrip("\n") + "\n\n" + block
    md.write_text(text, encoding="utf-8")
    print(f"wrote {out} and updated {md}")


if __name__ == "__main__":
    main()
