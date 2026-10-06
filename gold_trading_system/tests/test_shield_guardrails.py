"""
Shield (core/risk_guardrails), Wilder ADX, and the M15 tournament engine's
fill rules -- each checked against hand-computed expectations.
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gold_trading_system.core.backtester.m15_engine import (  # noqa: E402
    CostModel,
    FixedLot,
    ShieldSizing,
    compute_metrics,
    run_backtest,
)
from gold_trading_system.core.risk_guardrails.circuit_breaker import BreakerState, CircuitBreaker  # noqa: E402
from gold_trading_system.core.risk_guardrails.validator import (  # noqa: E402
    AccountSnapshot,
    InstrumentSpec,
    ShieldLimits,
    ShieldValidator,
    TradeRequest,
    TradeSide,
    load_shield_limits,
)
from gold_trading_system.core.strategies.indicators import adx  # noqa: E402
from gold_trading_system.core.strategies.m15_trend import EntrySignal  # noqa: E402
from gold_trading_system.core.strategies.types import Bar, Side  # noqa: E402

LIMITS = ShieldLimits(
    max_daily_loss_pct=5.0, max_drawdown_pct=20.0, risk_per_trade_pct=1.0, min_reward_risk=1.5,
    max_total_open_risk_pct=2.0, max_spread_points=80, max_lot_size=5.0,
)
NO_COSTS = CostModel(spread_floor_points=0, commission_per_lot_rt=0, swap_long_per_lot_night=0,
                     swap_short_per_lot_night=0)


def _buy(entry=2000.0, sl=1990.0, tp=2020.0, spread=30.0) -> TradeRequest:
    return TradeRequest(side=TradeSide.BUY, entry_price=entry, stop_loss_price=sl,
                        take_profit_price=tp, spread_points=spread)


# --- ShieldLimits: YAML can only tighten -----------------------------------

def test_repo_risk_rules_yaml_loads():
    limits = load_shield_limits()
    assert limits.max_daily_loss_pct <= 5.0 and limits.max_drawdown_pct <= 20.0


@pytest.mark.parametrize("field,value", [
    ("max_daily_loss_pct", 6.0), ("max_drawdown_pct", 25.0), ("risk_per_trade_pct", 3.0),
    ("min_reward_risk", 1.0), ("max_lot_size", 50.0),
])
def test_limits_looser_than_hard_ceiling_are_rejected(field, value):
    with pytest.raises(ValidationError):
        ShieldLimits(**{**LIMITS.model_dump(), field: value})


def test_limits_are_frozen_and_reject_unknown_keys():
    with pytest.raises(ValidationError):
        LIMITS.max_drawdown_pct = 50.0
    with pytest.raises(ValidationError):
        ShieldLimits(**{**LIMITS.model_dump(), "disable_shield": True})


# --- TradeRequest / ShieldValidator ----------------------------------------

def test_stop_on_wrong_side_cannot_be_constructed():
    with pytest.raises(ValidationError):
        _buy(sl=2010.0)


def test_risk_based_lot_size():
    # $10k * 1% = $100 budget; 1000-point stop costs $10 per 0.01 lot -> 0.10 lot
    d = ShieldValidator(LIMITS, InstrumentSpec()).validate(_buy(), AccountSnapshot(equity=10_000))
    assert d.approved and d.lot_size == pytest.approx(0.10) and d.risk_usd == pytest.approx(100.0)


def test_small_account_is_rejected_not_clamped_up_to_min_lot():
    # $100 * 1% = $1 budget, but 0.01 lot at a 1000-point stop risks $10
    d = ShieldValidator(LIMITS, InstrumentSpec()).validate(_buy(), AccountSnapshot(equity=100))
    assert not d.approved and d.lot_size == 0.0
    assert d.reasons[0].startswith("account_too_small")


def test_reward_risk_spread_and_open_risk_rules():
    v = ShieldValidator(LIMITS, InstrumentSpec())
    assert v.validate(_buy(tp=2014.0), AccountSnapshot(equity=10_000)).reasons[0].startswith("reward_risk")
    assert v.validate(_buy(spread=81), AccountSnapshot(equity=10_000)).reasons[0].startswith("spread")
    d = v.validate(_buy(), AccountSnapshot(equity=10_000, open_risk_usd=150))
    assert d.reasons[0].startswith("open_risk")


def test_exact_minimum_reward_risk_is_not_lost_to_float_rounding():
    import random
    rng = random.Random(1)
    v = ShieldValidator(LIMITS, InstrumentSpec())
    for _ in range(1000):
        entry, sl = round(rng.uniform(3000, 4200), 2) + 0.35, rng.uniform(500, 2000)
        for side, sign in ((TradeSide.BUY, 1), (TradeSide.SELL, -1)):
            req = TradeRequest(side=side, entry_price=entry, stop_loss_price=entry - sign * sl * 0.01,
                               take_profit_price=entry + sign * 1.5 * sl * 0.01, spread_points=35)
            d = v.validate(req, AccountSnapshot(equity=1e6))
            assert d.approved, d.reasons
    # just below the minimum is still rejected
    d = v.validate(_buy(tp=2000 + 14.99), AccountSnapshot(equity=10_000))
    assert d.reasons[0].startswith("reward_risk")


def test_halted_breaker_blocks_entries():
    d = ShieldValidator(LIMITS, InstrumentSpec()).validate(_buy(), AccountSnapshot(equity=10_000), "daily loss")
    assert not d.approved and d.reasons[0].startswith("circuit_breaker")


# --- CircuitBreaker ---------------------------------------------------------

def test_daily_halt_trips_at_5pct_and_clears_next_day():
    cb = CircuitBreaker(LIMITS, 1000.0)
    d1, d2 = date(2026, 1, 5), date(2026, 1, 6)
    assert cb.update(d1, 1000.0).state is BreakerState.ACTIVE
    v = cb.update(d1, 950.0)
    assert v.state is BreakerState.DAILY_HALT and v.flatten_now
    assert not cb.update(d1, 940.0).flatten_now  # only the tripping update flattens
    assert cb.update(d2, 940.0).state is BreakerState.ACTIVE


def test_drawdown_kill_is_latched_until_human_reset():
    cb = CircuitBreaker(LIMITS, 1000.0)
    for k, eq in enumerate([970, 930, 890, 850, 800]):  # each day < 5%, cumulative 20%
        v = cb.update(date(2026, 1, 5) + timedelta(days=k), float(eq))
    assert v.state is BreakerState.KILLED and v.flatten_now
    assert cb.update(date(2026, 2, 1), 800.0).state is BreakerState.KILLED
    with pytest.raises(ValueError):
        cb.manual_reset(" ", "resume")
    cb.manual_reset("operator", "reviewed")
    assert cb.update(date(2026, 2, 2), 800.0).state is BreakerState.ACTIVE


# --- ADX --------------------------------------------------------------------

def test_adx_alignment_and_steady_trend():
    n, p = 60, 14
    highs = [100.0 + i + 0.5 for i in range(n)]
    lows = [100.0 + i - 0.5 for i in range(n)]
    closes = [100.0 + i for i in range(n)]
    out = adx(highs, lows, closes, p)
    assert all(v is None for v in out[: 2 * p - 1]) and out[2 * p - 1] is not None
    assert out[-1] == pytest.approx(100.0)  # pure up-move: +DI=100, -DI=0 -> DX=100


# --- M15 engine fills -------------------------------------------------------

class _OneShot:
    """Signals one entry on bar `at`, never exits on signal."""
    name = "one_shot"

    def __init__(self, at: int, sig: EntrySignal) -> None:
        self.at, self.sig = at, sig

    def entry_signal(self, i):
        return self.sig if i == self.at else None

    def exit_signal(self, i, side):
        return False

    def trail_stop(self, i, side, entry, initial_risk, best):
        return None


def _bars(rows) -> list[Bar]:
    t0 = datetime(2026, 1, 5, 10, 0)
    return [Bar(t0 + timedelta(minutes=15 * k), o, h, l, c, 0.0, spread_points=0.0)
            for k, (o, h, l, c) in enumerate(rows)]


def test_entry_fills_next_open_and_stop_wins_when_both_touched():
    bars = _bars([(2000, 2001, 1999, 2000), (2000, 2025, 1985, 2000), (2000, 2000, 2000, 2000)])
    res = run_backtest(bars, _OneShot(0, EntrySignal(Side.BUY, 1000, 2000)), FixedLot(0.01), 1000.0, NO_COSTS)
    (t,) = res.trades
    assert t.entry_price == 2000.0 and t.exit_reason == "stop" and t.pnl_usd == pytest.approx(-10.0)


def test_gap_through_stop_fills_at_open():
    bars = _bars([(2000, 2001, 1999, 2000), (2000, 2001, 1999, 2000), (1980, 1981, 1975, 1978)])
    res = run_backtest(bars, _OneShot(0, EntrySignal(Side.BUY, 1000, None)), FixedLot(0.01), 1000.0, NO_COSTS)
    (t,) = res.trades
    assert t.exit_reason == "stop_gap" and t.exit_price == 1980.0 and t.r_multiple == pytest.approx(-2.0)


def test_shield_mode_sizes_by_risk_and_rejects_small_account():
    bars = _bars([(2000, 2001, 1999, 2000), (2000, 2021, 1999, 2010), (2010, 2010, 2010, 2010)])
    sig = EntrySignal(Side.BUY, 1000, 2000)
    big = run_backtest(bars, _OneShot(0, sig), ShieldSizing(LIMITS), 10_000.0, NO_COSTS)
    (t,) = big.trades
    assert t.lot == pytest.approx(0.10) and t.exit_reason == "target" and t.pnl_usd == pytest.approx(200.0)
    small = run_backtest(bars, _OneShot(0, sig), ShieldSizing(LIMITS), 100.0, NO_COSTS)
    assert small.trades == [] and compute_metrics(small)["shield_rejections"] == {"account_too_small": 1}


# --- Higher-timeframe bias: no look-ahead -----------------------------------

def _htf(timestamps, closes, tf=60, period=3, slope=1):
    from gold_trading_system.core.strategies.m15_trend import _htf_trend
    return _htf_trend(timestamps, closes, tf, period, slope)


def test_htf_bias_never_uses_unfinished_or_future_bars():
    import random
    rng = random.Random(7)
    t0 = datetime(2026, 1, 5, 0, 0)
    ts = [t0 + timedelta(minutes=15 * k) for k in range(400) if k % 37 != 5]  # a few missing bars
    closes, px = [], 2000.0
    for _ in ts:
        px += rng.uniform(-3, 3.2)
        closes.append(px)
    full = _htf(ts, closes)
    for i in range(0, len(ts), 7):
        assert _htf(ts[: i + 1], closes[: i + 1])[i] == full[i], f"bar {i} changed when future bars were removed"


def test_htf_bar_counts_as_closed_only_on_its_last_m15_bar():
    t0 = datetime(2026, 1, 5, 0, 0)
    ts = [t0 + timedelta(minutes=15 * k) for k in range(16)]
    closes = [2000.0 + 10 * (k // 4) for k in range(16)]  # each H1 bar closes 10 higher
    out = _htf(ts, closes, period=2, slope=1)
    # H1 closes 2000/2010/2020; EMA(2) = None/2005/2015. First BUY needs H1 bar 2
    # closed (2020 > 2015 > 2005), which happens on its last M15 bar, index 11 (02:45).
    assert out[10] is None and out[11] is Side.BUY


# --- Random-entry null model --------------------------------------------------

def test_random_entry_is_seeded_balanced_and_matches_entry_rate():
    from gold_trading_system.core.strategies.m15_trend import Indicators
    from gold_trading_system.core.strategies.random_entry import RandomEntry

    t0 = datetime(2026, 1, 5)
    bars = [Bar(t0 + timedelta(minutes=15 * k), 2000, 2004, 1996, 2000 + (k % 3), 0.0) for k in range(5000)]
    ind = Indicators(bars, 0.01)
    kw = dict(entry_prob=0.1, atr_period=14, sl_atr_mult=1.5, reward_risk=2.0, trail_atr_mult=3.0)
    first, second = RandomEntry(ind, seed=1, **kw), RandomEntry(ind, seed=1, **kw)
    sigs = [first.entry_signal(i) for i in range(len(bars))]
    again = [second.entry_signal(i) for i in range(len(bars))]
    fired = [s for s in sigs if s]
    assert sigs == again
    assert abs(len(fired) / len(bars) - 0.1) < 0.02
    assert abs(sum(s.side is Side.BUY for s in fired) / len(fired) - 0.5) < 0.06
    assert all(s.take_profit_points == pytest.approx(2.0 * s.stop_loss_points) for s in fired)


# --- Edge candidates: signals never depend on future bars ---------------------

def _random_walk_bars(days: int, seed: int = 3) -> list[Bar]:
    import random
    rng = random.Random(seed)
    t0, px, out = datetime(2026, 1, 5), 2000.0, []
    for k in range(days * 96):
        o = px
        px += rng.gauss(0, 1.5)
        hi, lo = max(o, px) + abs(rng.gauss(0, 0.8)), min(o, px) - abs(rng.gauss(0, 0.8))
        out.append(Bar(t0 + timedelta(minutes=15 * k), o, hi, lo, px, 0.0))
    return out


@pytest.mark.parametrize("key", ["session_breakout", "mean_reversion_bands"])
def test_edge_candidate_signals_have_no_look_ahead(key):
    from gold_trading_system.config_loader import load_yaml
    from gold_trading_system.core.strategies.edge_candidates import MeanReversionBands, SessionBreakout
    from gold_trading_system.core.strategies.m15_trend import Indicators

    cls = {"session_breakout": SessionBreakout, "mean_reversion_bands": MeanReversionBands}[key]
    params = load_yaml("strategy_config.yaml")[key]
    bars = _random_walk_bars(60)
    full = cls(Indicators(bars, 0.01), **params)._signals
    assert full, "fixture produced no signals -- test would be vacuous"
    for cut in (len(bars) // 2, len(bars) - 37):
        part = cls(Indicators(bars[:cut], 0.01), **params)._signals
        assert part == {i: s for i, s in full.items() if i < cut}


def test_session_breakout_trades_at_most_once_per_day():
    from gold_trading_system.config_loader import load_yaml
    from gold_trading_system.core.strategies.edge_candidates import SessionBreakout
    from gold_trading_system.core.strategies.m15_trend import Indicators

    bars = _random_walk_bars(60)
    params = {**load_yaml("strategy_config.yaml")["session_breakout"], "squeeze_factor": 99}
    sigs = SessionBreakout(Indicators(bars, 0.01), **params)._signals
    days = [bars[i].timestamp.date() for i in sigs]
    assert len(days) == len(set(days)) > 10
    assert all(10 <= bars[i].timestamp.hour < 14 for i in sigs)


# --- Buy & Hold benchmark + price-scaled swap (synthetic data only) ------------

def test_buy_and_hold_one_long_held_to_end_with_scaled_swap():
    from dataclasses import replace
    from gold_trading_system.skills.run_buy_hold_overlay import BuyAndHold, curve_stats

    t0 = datetime(2026, 1, 5)  # Monday
    closes = [2000.0, 2000.0, 2010.0, 2020.0, 2040.0]
    bars = [Bar(t0 + timedelta(days=k), c, c + 1, c - 1, c, 0.0, spread_points=0.0) for k, c in enumerate(closes)]
    costs = replace(NO_COSTS, swap_long_per_lot_night=-10.0)
    res = run_backtest(bars, BuyAndHold(2000.0, 0.01), FixedLot(0.05), 10_000.0, costs)
    (t,) = res.trades
    assert t.entry_price == 2000.0 and t.exit_reason == "end_of_data"
    # 3 nights held (Tue->Wed is triple): 1 + 3 + 1 = 5 nights x $10 x 0.05 lot = $2.50
    assert res.final_equity == pytest.approx(10_000 + 40 * 100 * 0.05 - 2.5)
    scaled = run_backtest(bars, BuyAndHold(2000.0, 0.01), FixedLot(0.05), 10_000.0,
                          replace(costs, swap_price_ref=4000.0))
    # each night's swap x (previous close / 4000): (2000 + 3*2010 + 2020) / 4000 x $0.50
    assert scaled.final_equity == pytest.approx(10_000 + 200 - 0.5 * (2000 + 3 * 2010 + 2020) / 4000)
    assert curve_stats(res)["cagr_pct"] > 0
