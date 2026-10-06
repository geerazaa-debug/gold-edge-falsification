"""
Bar-by-bar M15 backtest engine for the tournament (skills/run_backtest_tournament.py).

Fill model (conservative on purpose):
  * Signals are read on a CLOSED bar i and filled at bar i+1's open.
  * MT5 bars are BID. Longs enter at ask (= bid + spread) and exit at bid;
    shorts enter at bid and exit at ask. Spread = max(bar spread, floor).
  * Stops/targets are checked against the bar's high/low. If a bar touches
    both, the STOP is assumed to fill first. A bar that opens beyond the
    stop fills at the open (gap), never at the stop price.
  * Commission per lot round-turn and nightly swap (triple on Wednesday)
    come from config/broker_costs.yaml.
  * Margin: an entry needs free margin; equity < stop_out_level x margin
    force-closes (MT5-style stop-out).

Sizing modes:
  * FixedLot  -- the original EA's behaviour: constant lot, no guardrails.
  * Shield    -- every entry goes through ShieldValidator (risk-% sizing,
                 min R:R, spread cap) and a CircuitBreaker watching the
                 worst intrabar equity. When the breaker trips, the open
                 position is closed at that bar's close (a live monitor
                 would act sooner on ticks; this is an approximation).
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Protocol

from gold_trading_system.core.risk_guardrails.circuit_breaker import BreakerState, CircuitBreaker
from gold_trading_system.core.risk_guardrails.validator import (
    AccountSnapshot,
    InstrumentSpec,
    ShieldLimits,
    ShieldValidator,
    TradeRequest,
    TradeSide,
)
from gold_trading_system.core.strategies.m15_trend import EntrySignal
from gold_trading_system.core.strategies.types import Bar, Side


class Strategy(Protocol):
    name: str

    def entry_signal(self, i: int) -> EntrySignal | None: ...
    def exit_signal(self, i: int, side: Side) -> bool: ...
    def trail_stop(self, i: int, side: Side, entry: float, initial_risk: float, best: float) -> float | None: ...


@dataclass(frozen=True)
class CostModel:
    spread_floor_points: float = 30.0
    commission_per_lot_rt: float = 6.0
    swap_long_per_lot_night: float = -6.5
    swap_short_per_lot_night: float = -2.3
    triple_swap_weekday: int = 2          # Monday=0 -> Wednesday
    # None: swap is a fixed $ per lot per night. A price: swap scales by
    # (bar price / this reference) -- the same rate as a share of notional.
    swap_price_ref: float | None = None
    contract_size: float = 100.0
    leverage: float = 100.0
    stop_out_level: float = 0.5           # equity / margin


@dataclass(frozen=True)
class FixedLot:
    lot: float


@dataclass(frozen=True)
class ShieldSizing:
    limits: ShieldLimits


@dataclass
class _Position:
    side: Side
    lot: float
    entry_price: float
    stop: float
    target: float | None
    initial_risk: float     # price distance entry -> initial stop
    best: float
    opened_at: datetime
    swap_paid: float = 0.0


@dataclass(frozen=True)
class Trade:
    side: str
    lot: float
    opened_at: str
    closed_at: str
    entry_price: float
    exit_price: float
    exit_reason: str
    pnl_usd: float          # net of spread, commission and swap
    r_multiple: float


@dataclass
class BacktestResult:
    strategy: str
    sizing: str
    initial_equity: float
    trades: list[Trade] = field(default_factory=list)
    daily_equity: list[tuple[date, float]] = field(default_factory=list)
    max_dd_pct: float = 0.0
    max_dd_usd: float = 0.0
    final_equity: float = 0.0
    shield_rejections: Counter = field(default_factory=Counter)
    breaker_trips: list[tuple[str, str, str]] = field(default_factory=list)
    killed: bool = False
    stopped_out: bool = False


def run_backtest(
    bars: list[Bar], strategy: Strategy, sizing: FixedLot | ShieldSizing,
    initial_equity: float, costs: CostModel = CostModel(), instrument: InstrumentSpec = InstrumentSpec(),
) -> BacktestResult:
    return _Simulator(bars, strategy, sizing, initial_equity, costs, instrument).run()


class _Simulator:
    """One backtest run. Each bar goes through the steps in run(), in order."""

    def __init__(
        self, bars: list[Bar], strategy: Strategy, sizing: FixedLot | ShieldSizing,
        initial_equity: float, costs: CostModel, instrument: InstrumentSpec,
    ) -> None:
        self.bars, self.strategy, self.sizing = bars, strategy, sizing
        self.costs, self.inst = costs, instrument
        use_shield = isinstance(sizing, ShieldSizing)
        self.shield = ShieldValidator(sizing.limits, instrument) if use_shield else None
        self.breaker = CircuitBreaker(sizing.limits, initial_equity) if use_shield else None
        self.res = BacktestResult(strategy.name, "shield" if use_shield else f"fixed_{sizing.lot}", initial_equity)
        self.balance = initial_equity
        self.peak = initial_equity
        self.pos: _Position | None = None
        self.pending_close = False
        self.pending_entry: EntrySignal | None = None
        self.prev_day: date | None = None

    # --- price helpers -------------------------------------------------------
    def _spread(self, b: Bar) -> float:
        return max(b.spread_points or 0.0, self.costs.spread_floor_points) * self.inst.point

    @staticmethod
    def _exit_price(side: Side, bid: float, spread: float) -> float:
        return bid if side is Side.BUY else bid + spread

    def _pnl(self, p: _Position, exit_px: float) -> float:
        sign = 1.0 if p.side is Side.BUY else -1.0
        return sign * (exit_px - p.entry_price) / self.inst.point * self.inst.point_value_usd_per_lot * p.lot

    def _floating(self, bid: float, spread: float) -> float:
        return self._pnl(self.pos, self._exit_price(self.pos.side, bid, spread)) if self.pos else 0.0

    def _margin(self, lot: float, price: float) -> float:
        return lot * self.costs.contract_size * price / self.costs.leverage

    # --- main loop -----------------------------------------------------------
    def run(self) -> BacktestResult:
        for i, b in enumerate(self.bars):
            spread = self._spread(b)
            tripped_at_open = self._roll_day(i, b, spread)
            self._fill_pending(b, spread)
            if self.pos is None and self.res.killed:
                continue
            self._check_stop_and_target(b, spread)
            self._mark_equity_and_guard(b, spread, tripped_at_open)
            if self.balance <= 0:
                self.res.stopped_out = True
                break
            self._manage_and_signal(i, b, spread)

        if self.pos:
            last = self.bars[-1]
            self._close(self._exit_price(self.pos.side, last.close, self._spread(last)), last.timestamp, "end_of_data")
        if self.bars:
            self.res.daily_equity.append((self.bars[-1].timestamp.date(), self.balance))
        self.res.final_equity = self.balance
        return self.res

    def _roll_day(self, i: int, b: Bar, spread: float) -> bool:
        """On a new server day: record the previous day's equity, charge swap,
        and set the breaker's day-start equity. True if that trips the breaker."""
        day = b.timestamp.date()
        if day == self.prev_day:
            return False
        if self.prev_day is not None:
            prev = self.bars[i - 1]
            self.res.daily_equity.append((self.prev_day, self.balance + self._floating(prev.close, self._spread(prev))))
            if self.pos:
                c = self.costs
                nights = 3 if self.prev_day.weekday() == c.triple_swap_weekday else 1
                rate = c.swap_long_per_lot_night if self.pos.side is Side.BUY else c.swap_short_per_lot_night
                swap = rate * self.pos.lot * nights
                if c.swap_price_ref:
                    swap *= prev.close / c.swap_price_ref
                self.balance += swap
                self.pos.swap_paid += swap
        self.prev_day = day
        if self.breaker is None:
            return False
        return self.breaker.update(day, self.balance + self._floating(b.open, spread)).flatten_now

    def _fill_pending(self, b: Bar, spread: float) -> None:
        """Orders decided on the previous close fill at this bar's open."""
        if self.pos and self.pending_close:
            self._close(self._exit_price(self.pos.side, b.open, spread), b.timestamp, "signal_exit")
        self.pending_close = False
        if self.pending_entry and self.pos is None:
            self.pos = self._open(self.pending_entry, b, spread)
        self.pending_entry = None

    def _check_stop_and_target(self, b: Bar, spread: float) -> None:
        p = self.pos
        if p is None:
            return
        if p.side is Side.BUY:
            o, hi, lo = b.open, b.high, b.low
            hit_stop, gapped = lo <= p.stop, o <= p.stop
            hit_target = p.target is not None and hi >= p.target
        else:  # shorts exit on the ask
            o, hi, lo = b.open + spread, b.high + spread, b.low + spread
            hit_stop, gapped = hi >= p.stop, o >= p.stop
            hit_target = p.target is not None and lo <= p.target
        if gapped:
            self._close(o, b.timestamp, "stop_gap")
        elif hit_stop:  # stop wins when a bar touches both
            self._close(p.stop, b.timestamp, "stop")
        elif hit_target:
            self._close(p.target, b.timestamp, "target")

    def _mark_equity_and_guard(self, b: Bar, spread: float, tripped_at_open: bool) -> None:
        """Drawdown on the worst intrabar equity, then stop-out and breaker."""
        worst = self.balance
        if self.pos:
            worst += self._floating(b.low if self.pos.side is Side.BUY else b.high, spread)
        dd_usd = self.peak - worst
        self.res.max_dd_usd = max(self.res.max_dd_usd, dd_usd)
        self.res.max_dd_pct = max(self.res.max_dd_pct, dd_usd / self.peak * 100.0 if self.peak > 0 else 100.0)

        if self.pos and worst < self.costs.stop_out_level * self._margin(self.pos.lot, b.close):
            self._close(self._exit_price(self.pos.side, b.close, spread), b.timestamp, "stop_out")
            self.res.stopped_out = True

        if self.breaker:
            verdict = self.breaker.update(b.timestamp.date(), worst)
            if verdict.flatten_now or tripped_at_open:
                self.res.breaker_trips.append((b.timestamp.date().isoformat(), verdict.state.value, verdict.reason or ""))
                if self.pos:
                    self._close(self._exit_price(self.pos.side, b.close, spread), b.timestamp, "circuit_breaker")
                self.res.killed = verdict.state is BreakerState.KILLED

        self.peak = max(self.peak, self.balance + self._floating(b.close, spread))

    def _manage_and_signal(self, i: int, b: Bar, spread: float) -> None:
        """At the close: ratchet the trailing stop, then decide next-bar orders."""
        p = self.pos
        if p:
            p.best = max(p.best, b.high) if p.side is Side.BUY else min(p.best, b.low + spread)
            new_stop = self.strategy.trail_stop(i, p.side, p.entry_price, p.initial_risk, p.best)
            direction = 1.0 if p.side is Side.BUY else -1.0
            if new_stop is not None and (new_stop - p.stop) * direction > 0:
                p.stop = new_stop
            self.pending_close = self.strategy.exit_signal(i, p.side)
        if (p is None or self.pending_close) and not self.res.killed:
            self.pending_entry = self.strategy.entry_signal(i)

    # --- order handling ------------------------------------------------------
    def _close(self, exit_px: float, when: datetime, reason: str) -> None:
        p = self.pos
        gross = self._pnl(p, exit_px)
        commission = self.costs.commission_per_lot_rt * p.lot
        self.balance += gross - commission       # swap was already booked nightly
        net = gross - commission + p.swap_paid
        risk_usd = p.initial_risk / self.inst.point * self.inst.point_value_usd_per_lot * p.lot
        self.res.trades.append(Trade(
            p.side.value, p.lot, p.opened_at.isoformat(), when.isoformat(), round(p.entry_price, 2),
            round(exit_px, 2), reason, round(net, 2), round(net / risk_usd, 3) if risk_usd else 0.0,
        ))
        self.pos = None

    def _open(self, sig: EntrySignal, b: Bar, spread: float) -> _Position | None:
        pt = self.inst.point
        entry = b.open + spread if sig.side is Side.BUY else b.open
        sign = 1.0 if sig.side is Side.BUY else -1.0
        stop = entry - sign * sig.stop_loss_points * pt
        target = None if sig.take_profit_points is None else entry + sign * sig.take_profit_points * pt

        lot = self._shield_lot(sig, entry, stop, target, spread) if self.shield else self.sizing.lot
        if lot is None:
            return None
        if self.balance < self._margin(lot, entry):
            self.res.shield_rejections["insufficient_margin"] += 1
            return None
        return _Position(sig.side, lot, entry, stop, target, abs(entry - stop), entry, b.timestamp)

    def _shield_lot(
        self, sig: EntrySignal, entry: float, stop: float, target: float | None, spread: float,
    ) -> float | None:
        if target is None:
            self.res.shield_rejections["no_take_profit"] += 1
            return None
        request = TradeRequest(
            side=TradeSide(sig.side.value), entry_price=entry, stop_loss_price=stop,
            take_profit_price=target, spread_points=spread / self.inst.point, strategy=self.res.strategy,
        )
        decision = self.shield.validate(request, AccountSnapshot(equity=self.balance), self.breaker.halted_reason)
        if not decision.approved:
            for reason in decision.reasons:
                self.res.shield_rejections[reason.split(":")[0]] += 1
            return None
        return decision.lot_size


def compute_metrics(res: BacktestResult) -> dict:
    pnls = [t.pnl_usd for t in res.trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gross_win, gross_loss = sum(wins), -sum(losses)

    longest = streak = 0
    for p in pnls:
        streak = streak + 1 if p <= 0 else 0
        longest = max(longest, streak)

    equities = [e for _, e in res.daily_equity]
    rets = [(b - a) / a for a, b in zip(equities, equities[1:]) if a > 0]
    sharpe = 0.0
    if len(rets) > 1:
        mean = sum(rets) / len(rets)
        std = math.sqrt(sum((r - mean) ** 2 for r in rets) / (len(rets) - 1))
        sharpe = mean / std * math.sqrt(252) if std > 0 else 0.0

    net = res.final_equity - res.initial_equity
    return {
        "strategy": res.strategy,
        "sizing": res.sizing,
        "initial_equity": res.initial_equity,
        "final_equity": round(res.final_equity, 2),
        "net_profit": round(net, 2),
        "return_pct": round(net / res.initial_equity * 100, 2),
        "trades": len(pnls),
        "win_rate_pct": round(len(wins) / len(pnls) * 100, 2) if pnls else 0.0,
        "profit_factor": round(gross_win / gross_loss, 3) if gross_loss > 0 else None,
        "avg_r": round(sum(t.r_multiple for t in res.trades) / len(pnls), 3) if pnls else 0.0,
        "max_consecutive_losses": longest,
        "max_equity_dd_pct": round(res.max_dd_pct, 2),
        "max_equity_dd_usd": round(res.max_dd_usd, 2),
        "recovery_factor": round(net / res.max_dd_usd, 2) if res.max_dd_usd > 0 else None,
        "sharpe_daily_annualized": round(sharpe, 2),
        "shield_rejections": dict(res.shield_rejections),
        "breaker_trips": len(res.breaker_trips),
        "killed": res.killed,
        "stopped_out": res.stopped_out,
    }
