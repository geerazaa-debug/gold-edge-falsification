"""
Random-entry benchmark (null model) for the tournament strategies.

For each strategy, a matched RandomEntry is built that copies:
  * its entry FREQUENCY (share of bars where the strategy signals),
  * its typical stop size in ATR units (median over its own signals),
  * its reward:risk and trailing stop,
so the ONLY difference is where the entries come from. Each matched random
strategy runs `iterations` seeds per window, in two modes:

  expectancy -- fixed lot on a huge account (no margin limit, no breaker):
                measures R per trade with full sample size.
  shield     -- $10k behind Shield: how often a zero-edge entry gets killed
                at the 20% drawdown, and the return distribution.

The strategy's own result is placed in the random distribution: `p` is the
share of random seeds whose avg R is >= the strategy's. p near 0 = edge;
p around 0.5 = indistinguishable from coin flips.

Writes reports/random_benchmark_<TF>.json / .md, and inserts the table into
reports/tournament_report_<TF>.md when it exists. Run the tournament on the
same --timeframe first so the IS-selected params are benchmarked too.

Run: venv/Scripts/python.exe skills/run_random_benchmark.py [--timeframe M15|H1|H4] [--iterations 100]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT.parent))

from gold_trading_system.core.backtester.m15_engine import FixedLot, ShieldSizing, compute_metrics  # noqa: E402
from gold_trading_system.core.strategies.random_entry import RandomEntry  # noqa: E402
from gold_trading_system.core.strategies.types import Side  # noqa: E402
from gold_trading_system.skills.run_backtest_tournament import (  # noqa: E402
    TUNABLE,
    Context,
    build_context,
    load_bars,
    load_config,
    report_path,
)

REPORTS = PROJECT_ROOT / "reports"
EXPECTANCY_LOT, EXPECTANCY_CAPITAL = FixedLot(0.10), 10_000_000.0
BEGIN, END = "<!-- random-benchmark:begin -->", "<!-- random-benchmark:end -->"


def candidates(timeframe: str) -> dict[str, tuple[str, dict]]:
    """Strategies to benchmark: each tunable strategy's defaults, plus the
    IS-selected params from the last tournament run on this timeframe."""
    out = {f"{key} default": (key, {}) for key in TUNABLE}
    results = report_path("tournament_results", timeframe, ".json")
    if results.exists():
        for key, search in json.loads(results.read_text(encoding="utf-8")).get("searches", {}).items():
            if search.get("best"):
                out[f"{key} IS-selected"] = (key, search["best"]["params"])
    return out


def match_profile(ctx: Context, key: str, params: dict, window: str, null: str) -> dict:
    """RandomEntry kwargs matched to the strategy's own signals: entry rate,
    median stop (ATR units), R:R, trail, and -- depending on `null` -- side:
      coin  -- 50/50 long/short
      side  -- the strategy's own long share (removes market drift as an "edge")
      bias  -- side = the strategy's HTF bias on that bar; only timing is random
               (does the entry trigger add anything over just following the bias?)
    """
    strat = ctx.strategy(key, window, **params)
    full = {**ctx.cfg[key], **params}
    atr = ctx.ind[window].atr_points(full["atr_period"])
    n = len(ctx.windows[window])
    ratios, longs = [], 0
    for i in range(n):
        sig = strat.entry_signal(i)
        if sig is not None and atr[i]:
            ratios.append(sig.stop_loss_points / atr[i])
            longs += sig.side is Side.BUY
    eligible_bars = n
    profile = {
        "atr_period": full["atr_period"],
        "sl_atr_mult": statistics.median(ratios) if ratios else 1.5,
        "reward_risk": full["reward_risk"],
        "trail_atr_mult": full["trail_atr_mult"],
        "session_hours": full.get("session_hours"),
        "long_prob": 0.5 if null == "coin" or not ratios else longs / len(ratios),
    }
    if null == "bias":
        bias = getattr(strat, "bias", None)
        if bias is None:
            raise ValueError(f"{key} has no HTF bias to match")
        profile["sides"] = bias
        eligible_bars = sum(b is not None for b in bias)
    profile["entry_prob"] = min(max(len(ratios) / max(eligible_bars, 1), 1e-4), 1.0)
    return profile


def _summary(values: list[float]) -> dict:
    s = sorted(values)
    return {"mean": round(statistics.fmean(s), 4), "p05": round(s[len(s) // 20], 4),
            "median": round(statistics.median(s), 4), "p95": round(s[(len(s) * 19) // 20], 4)}


def benchmark(ctx: Context, key: str, params: dict, window: str, iterations: int, seed0: int, null: str) -> dict:
    profile = match_profile(ctx, key, params, window, null)
    shield = ShieldSizing(ctx.limits)
    actual_e = compute_metrics(ctx.run(window, ctx.strategy(key, window, **params), EXPECTANCY_LOT, EXPECTANCY_CAPITAL))
    actual_s = compute_metrics(ctx.run(window, ctx.strategy(key, window, **params), shield, 10_000.0))

    rand_r, rand_pf, rand_ret, rand_trades, kills = [], [], [], [], 0
    for k in range(iterations):
        rnd = RandomEntry(ctx.ind[window], seed=seed0 + k, **profile)
        e = compute_metrics(ctx.run(window, rnd, EXPECTANCY_LOT, EXPECTANCY_CAPITAL))
        s = compute_metrics(ctx.run(window, RandomEntry(ctx.ind[window], seed=seed0 + k, **profile), shield, 10_000.0))
        rand_r.append(e["avg_r"])
        rand_pf.append(e["profit_factor"] or 0.0)
        rand_trades.append(e["trades"])
        rand_ret.append(s["return_pct"])
        kills += s["killed"]

    return {
        "window": window,
        "null": null,
        "profile": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in profile.items() if k != "sides"},
        "strategy": {"trades": actual_e["trades"], "avg_r": actual_e["avg_r"], "profit_factor": actual_e["profit_factor"],
                     "win_rate_pct": actual_e["win_rate_pct"], "shield_return_pct": actual_s["return_pct"],
                     "shield_killed": actual_s["killed"]},
        "random": {"avg_r": _summary(rand_r), "profit_factor": _summary(rand_pf),
                   "trades_median": statistics.median(rand_trades), "shield_return_pct": _summary(rand_ret),
                   "shield_kill_rate": round(kills / iterations, 3)},
        "p_value": round(sum(r >= actual_e["avg_r"] for r in rand_r) / iterations, 3),
    }


def to_markdown(rows: dict, iterations: int) -> str:
    lines = [
        BEGIN,
        f"## Random-entry benchmark ({iterations} seeds per row, side-matched null)",
        "",
        "Random entries with the strategy's own entry rate, long share, median stop (ATR units), R:R and trail. "
        "Expectancy columns: fixed 0.10 lot, no breaker. Shield columns: $10k behind Shield. "
        "`p` = share of random seeds with avg R >= the strategy's (low = edge, ~0.5 = coin flip).",
        "",
        "| Strategy | Window | Trades (strat / rand med) | Strat avg R | Random avg R mean [p05, p95] | Strat PF | Random PF med "
        "| p | Strat Shield ret % | Random Shield ret % med | Random kill rate |",
        "|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for label, by_window in rows.items():
        for r in by_window:
            s, rd = r["strategy"], r["random"]
            lines.append(
                f"| {label} | {r['window']} | {s['trades']} / {rd['trades_median']:.0f} | {s['avg_r']:.3f} | "
                f"{rd['avg_r']['mean']:.3f} [{rd['avg_r']['p05']:.3f}, {rd['avg_r']['p95']:.3f}] | "
                f"{s['profit_factor'] or 0:.2f} | {rd['profit_factor']['median']:.2f} | {r['p_value']:.2f} | "
                f"{s['shield_return_pct']:.1f}{' (killed)' if s['shield_killed'] else ''} | "
                f"{rd['shield_return_pct']['median']:.1f} | {rd['shield_kill_rate']:.0%} |"
            )
    return "\n".join(lines + [END]) + "\n"


def splice_into_tournament_report(block: str, timeframe: str) -> None:
    path = report_path("tournament_report", timeframe, ".md")
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if BEGIN in text and END in text:
        text = text[: text.index(BEGIN)] + block + text[text.index(END) + len(END) + 1:]
    else:
        text = text.rstrip("\n") + "\n\n" + block
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Random-entry null-model benchmark")
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--seed", type=int, default=1000)
    parser.add_argument("--timeframe", default="M15", choices=["M15", "H1", "H4"])
    parser.add_argument("--null", default="side", choices=["coin", "side", "bias"],
                        help="random twin's side: 50/50, the strategy's long share, or its HTF bias")
    parser.add_argument("--only", nargs="+", help="benchmark only these labels, e.g. 'mtf_pullback default'")
    args = parser.parse_args()

    cfg = load_config(args.timeframe)
    ctx = build_context(cfg, load_bars(cfg, refresh=False))

    rows: dict[str, list[dict]] = {}
    for label, (key, params) in candidates(args.timeframe).items():
        if args.only and label not in args.only:
            continue
        rows[label] = [benchmark(ctx, key, params, w, args.iterations, args.seed, args.null) for w in ("IS", "OOS")]
        for r in rows[label]:
            print(f"{label:28s} {r['window']:3s} strat avgR {r['strategy']['avg_r']:+.3f}  random mean "
                  f"{r['random']['avg_r']['mean']:+.3f} [{r['random']['avg_r']['p05']:+.3f}, "
                  f"{r['random']['avg_r']['p95']:+.3f}]  p={r['p_value']:.2f}  "
                  f"random kill rate {r['random']['shield_kill_rate']:.0%}")

    REPORTS.mkdir(exist_ok=True)
    if args.only or args.null != "side":  # a focused check must not overwrite the standard report
        out = report_path(f"random_benchmark_{args.null}_n{args.iterations}", args.timeframe, ".json")
        out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"wrote {out}")
        return
    report_path("random_benchmark", args.timeframe, ".json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    block = to_markdown(rows, args.iterations)
    md = report_path("random_benchmark", args.timeframe, ".md")
    md.write_text(block, encoding="utf-8")
    splice_into_tournament_report(block, args.timeframe)
    print(f"wrote {md} (and spliced into tournament_report_{args.timeframe}.md)")


if __name__ == "__main__":
    main()
