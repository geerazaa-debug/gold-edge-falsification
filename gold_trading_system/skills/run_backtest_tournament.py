"""
Backtest tournament: the original-EA stand-in vs. tunable strategies behind
Shield, on real XAUUSD history (M15, H1 or H4) from the local MT5.

Protocol (to keep the optimization honest):
  1. Split bars chronologically: in-sample (IS) = first 70%, out-of-sample
     (OOS) = last 30% (config/strategy_config.yaml -> data).
  2. Grid-search each tunable strategy on IS only. Pick the best IS Sharpe
     among combos with >= min_trades and IS max DD < Shield's drawdown limit.
  3. Score each winner ONCE on OOS, next to the baseline and the untuned
     defaults. OOS numbers are the ones to believe.

Each entrant runs at every --capital (default $100, $1,000, $10,000):
Shield's risk-% sizing often cannot place a 0.01-lot trade on a small
account, and the tournament shows that instead of hiding it.

Writes reports/tournament_results_<TF>.json, reports/tournament_report_<TF>.md
and reports/trades_log.json (OOS trades of the best OOS selected strategy at
the largest capital).

Run: venv/Scripts/python.exe skills/run_backtest_tournament.py [--timeframe M15|H1|H4] [--capital ...] [--refresh-data]
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT.parent))

from gold_trading_system.config_loader import load_yaml  # noqa: E402
from gold_trading_system.core.backtester.m15_engine import (  # noqa: E402
    CostModel,
    FixedLot,
    ShieldSizing,
    compute_metrics,
    run_backtest,
)
from gold_trading_system.core.data_ingestion.mt5_history import fetch_from_mt5, load_csv, save_csv  # noqa: E402
from gold_trading_system.core.risk_guardrails.validator import (  # noqa: E402
    InstrumentSpec,
    ShieldLimits,
    load_shield_limits,
)
from gold_trading_system.core.strategies.edge_candidates import MeanReversionBands, SessionBreakout  # noqa: E402
from gold_trading_system.core.strategies.m15_trend import (  # noqa: E402
    AtrTrendFilter,
    BaselineCross,
    Indicators,
    MtfPullback,
)
from gold_trading_system.core.strategies.types import Bar  # noqa: E402

REPORTS = PROJECT_ROOT / "reports"
TUNABLE = {
    "atr_trend": AtrTrendFilter,
    "mtf_pullback": MtfPullback,
    "session_breakout": SessionBreakout,
    "mean_reversion_bands": MeanReversionBands,
}
COLUMNS = ("entrant", "window", "capital", "trades", "win_rate_pct", "profit_factor", "net_profit",
           "return_pct", "max_equity_dd_pct", "sharpe_daily_annualized", "max_consecutive_losses", "flags")


@dataclass
class Context:
    windows: dict[str, list[Bar]]
    ind: dict[str, Indicators]
    cfg: dict
    costs: CostModel
    inst: InstrumentSpec
    limits: ShieldLimits

    def strategy(self, key: str, window: str, **overrides):
        return TUNABLE[key](self.ind[window], **{**self.cfg[key], **overrides})

    def baseline(self, window: str) -> BaselineCross:
        b = self.cfg["baseline"]
        return BaselineCross(self.ind[window], b["fast_ema"], b["slow_ema"], b["stop_loss_points"])

    def run(self, window: str, strat, sizing, capital: float):
        return run_backtest(self.windows[window], strat, sizing, capital, self.costs, self.inst)


def cost_model(spread_floor: float) -> CostModel:
    bc = load_yaml("broker_costs.yaml")
    return CostModel(
        spread_floor_points=spread_floor,
        commission_per_lot_rt=bc["commission"]["per_lot_round_turn_usd"],
        swap_long_per_lot_night=bc["swap"]["swap_long_usd_per_lot_per_night"],
        swap_short_per_lot_night=bc["swap"]["swap_short_usd_per_lot_per_night"],
        contract_size=bc["contract"]["contract_size_oz"],
    )


def flags(m: dict) -> str:
    out = []
    if m["killed"]:
        out.append("KILLED")
    if m["stopped_out"]:
        out.append("STOP-OUT")
    if m["breaker_trips"]:
        out.append(f"{m['breaker_trips']} trips")
    if m["shield_rejections"]:
        top = max(m["shield_rejections"].items(), key=lambda kv: kv[1])
        out.append(f"rej {sum(m['shield_rejections'].values())} (mostly {top[0]})")
    return ", ".join(out)


def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:,.2f}"
    return "-" if v is None else str(v)


def print_table(rows: list[dict]) -> None:
    cells = [[_fmt(r.get(c)) for c in COLUMNS] for r in rows]
    widths = [max(len(c), *(len(row[k]) for row in cells)) for k, c in enumerate(COLUMNS)]
    print("  ".join(c.ljust(w) for c, w in zip(COLUMNS, widths)))
    print("  ".join("-" * w for w in widths))
    for row in cells:
        print("  ".join(v.ljust(w) for v, w in zip(row, widths)))


def grid_search(ctx: Context, key: str, capital: float) -> dict:
    """IS-only grid search for one tunable strategy; returns its summary."""
    grid_cfg = ctx.cfg["optimization"]["grids"][key]
    names = list(grid_cfg)
    shield = ShieldSizing(ctx.limits)
    grid = []
    for values in itertools.product(*(grid_cfg[n] for n in names)):
        params = dict(zip(names, values))
        m = compute_metrics(ctx.run("IS", ctx.strategy(key, "IS", **params), shield, capital))
        grid.append({"params": params, **m})

    min_trades = ctx.cfg["optimization"]["min_trades"]
    eligible = [g for g in grid if g["trades"] >= min_trades and g["max_equity_dd_pct"] < ctx.limits.max_drawdown_pct]
    best = max(eligible, key=lambda g: g["sharpe_daily_annualized"]) if eligible else None

    oos_ok = 0
    for g in eligible:
        m = compute_metrics(ctx.run("OOS", ctx.strategy(key, "OOS", **g["params"]), shield, capital))
        oos_ok += m["net_profit"] > 0 and m["max_equity_dd_pct"] < ctx.limits.max_drawdown_pct
    return {"grid": grid, "eligible": len(eligible), "best": best, "oos_robust": f"{oos_ok}/{len(eligible)}"}


def score_entrants(ctx: Context, searches: dict, capitals: list[float]) -> tuple[list[dict], dict]:
    """Run every entrant on IS and OOS at every capital. Returns the table rows
    and the OOS trade lists of the selected strategies at the largest capital."""
    shield, top_capital = ShieldSizing(ctx.limits), max(capitals)
    rows, selected_trades = [], {}
    for window, capital in itertools.product(("IS", "OOS"), capitals):
        entrants = [("baseline (0.01 lot, 1000pt SL)", ctx.baseline(window), FixedLot(ctx.cfg["baseline"]["fixed_lot"]))]
        for key, search in searches.items():
            entrants.append((f"{key} default + Shield", ctx.strategy(key, window), shield))
            if search["best"]:
                entrants.append((f"{key} IS-selected + Shield", ctx.strategy(key, window, **search["best"]["params"]), shield))
        for label, strat, sizing in entrants:
            res = ctx.run(window, strat, sizing, capital)
            m = compute_metrics(res)
            rows.append({"entrant": label, "window": window, "capital": capital, **m, "flags": flags(m),
                         "breaker_trip_log": res.breaker_trips})
            if window == "OOS" and capital == top_capital and "IS-selected" in label:
                selected_trades[label] = ([asdict(t) for t in res.trades], m["net_profit"])
    return rows, selected_trades


def markdown_report(ctx: Context, searches: dict, rows: list[dict]) -> str:
    w = ctx.windows
    lines = [
        f"# Tournament report -- {ctx.cfg['timeframe']}",
        "",
        f"Generated {datetime.now().isoformat(timespec='seconds')}. XAUUSD {ctx.cfg['timeframe']}, "
        f"IS {w['IS'][0].timestamp:%Y-%m-%d} -> {w['IS'][-1].timestamp:%Y-%m-%d}, "
        f"OOS {w['OOS'][0].timestamp:%Y-%m-%d} -> {w['OOS'][-1].timestamp:%Y-%m-%d}. "
        f"Spread floor {ctx.costs.spread_floor_points:.0f} pts; Shield risk {ctx.limits.risk_per_trade_pct}%/trade.",
        "",
        "## Grid searches (in-sample only)",
        "",
        "| Strategy | Combos | Eligible | Selected params | IS Sharpe | IS DD % | Eligible combos profitable OOS |",
        "|---|---:|---:|---|---:|---:|---:|",
    ]
    for key, s in searches.items():
        b = s["best"]
        sel = "none eligible" if b is None else f"`{b['params']}`"
        lines.append(f"| {key} | {len(s['grid'])} | {s['eligible']} | {sel} | "
                     f"{_fmt(b and b['sharpe_daily_annualized'])} | {_fmt(b and b['max_equity_dd_pct'])} | {s['oos_robust']} |")
    cols = ("entrant", "capital", "trades", "win_rate_pct", "profit_factor", "return_pct",
            "max_equity_dd_pct", "sharpe_daily_annualized", "flags")
    for window in ("OOS", "IS"):
        lines += ["", f"## {window} results", "", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        lines += ["| " + " | ".join(_fmt(r[c]) for c in cols) + " |" for r in rows if r["window"] == window]
    return "\n".join(lines) + "\n"


def load_config(timeframe: str) -> dict:
    """strategy_config.yaml with the timeframe's `params` / `grids` overrides applied."""
    cfg = load_yaml("strategy_config.yaml")
    tf_cfg = cfg["timeframes"][timeframe]
    for key, patch in tf_cfg.get("params", {}).items():
        cfg[key] = {**cfg[key], **patch}
    for key, patch in tf_cfg.get("grids", {}).items():
        cfg["optimization"]["grids"][key] = {**cfg["optimization"]["grids"][key], **patch}
    cfg["timeframe"], cfg["base_minutes"] = timeframe, tf_cfg["base_minutes"]
    _check_htf_above_base(cfg)
    return cfg


def _check_htf_above_base(cfg: dict) -> None:
    base = cfg["base_minutes"]
    for key in TUNABLE:
        values = [cfg[key].get("htf_minutes")] + list(cfg["optimization"]["grids"][key].get("htf_minutes", []))
        bad = [v for v in values if v is not None and v <= base]
        if bad:
            raise ValueError(f"{cfg['timeframe']}: {key} htf_minutes {bad} must exceed the {base}-minute bars")


def load_bars(cfg: dict, refresh: bool) -> list[Bar]:
    csv_path = PROJECT_ROOT / cfg["data"]["csv"].format(timeframe=cfg["timeframe"])
    if refresh or not csv_path.exists():
        save_csv(fetch_from_mt5(timeframe=cfg["timeframe"]), csv_path)
    return load_csv(csv_path)


def build_context(cfg: dict, bars: list[Bar]) -> Context:
    split = int(len(bars) * cfg["data"]["in_sample_fraction"])
    windows = {"IS": bars[:split], "OOS": bars[split:]}
    inst = InstrumentSpec()
    ind = {k: Indicators(v, inst.point, cfg["base_minutes"]) for k, v in windows.items()}
    return Context(windows, ind, cfg, cost_model(cfg["data"]["spread_floor_points"]), inst, load_shield_limits())


def report_path(stem: str, timeframe: str, suffix: str) -> Path:
    return REPORTS / f"{stem}_{timeframe}{suffix}"


def main() -> None:
    parser = argparse.ArgumentParser(description="XAUUSD strategy tournament")
    parser.add_argument("--timeframe", default="M15", choices=["M15", "H1", "H4"])
    parser.add_argument("--capital", type=float, nargs="+", default=[100.0, 1_000.0, 10_000.0])
    parser.add_argument("--refresh-data", action="store_true", help="re-download history from MT5 first")
    args = parser.parse_args()

    cfg = load_config(args.timeframe)
    bars = load_bars(cfg, args.refresh_data)
    ctx = build_context(cfg, bars)
    w = ctx.windows
    print(f"{args.timeframe}: {len(bars)} bars; IS {w['IS'][0].timestamp} -> {w['IS'][-1].timestamp}; "
          f"OOS {w['OOS'][0].timestamp} -> {w['OOS'][-1].timestamp}")

    searches = {key: grid_search(ctx, key, max(args.capital)) for key in TUNABLE}
    for key, s in searches.items():
        b = s["best"]
        print(f"{key}: {len(s['grid'])} combos, {s['eligible']} eligible, selected "
              f"{b and b['params']}, OOS-robust {s['oos_robust']}")

    rows, selected_trades = score_entrants(ctx, searches, args.capital)
    print()
    print_table(rows)

    REPORTS.mkdir(exist_ok=True)
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "timeframe": args.timeframe,
        "data": {"bars": len(bars), "first": bars[0].timestamp.isoformat(), "last": bars[-1].timestamp.isoformat(),
                 "is_end": w["IS"][-1].timestamp.isoformat(), "spread_floor_points": ctx.costs.spread_floor_points},
        "shield_limits": ctx.limits.model_dump(),
        "searches": searches,
        "results": rows,
    }
    results_path = report_path("tournament_results", args.timeframe, ".json")
    report_md = report_path("tournament_report", args.timeframe, ".md")
    results_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    report_md.write_text(markdown_report(ctx, searches, rows), encoding="utf-8")
    if selected_trades:
        label, (trades, _) = max(selected_trades.items(), key=lambda kv: kv[1][1])
        (REPORTS / "trades_log.json").write_text(json.dumps(trades, indent=2), encoding="utf-8")
        print(f"\ntrades_log.json <- OOS trades of '{label}' ({args.timeframe})")
    print(f"wrote {results_path} and {report_md}")


if __name__ == "__main__":
    main()
