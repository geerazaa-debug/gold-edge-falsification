"""
M15 trend-following signal generators for the backtest tournament.

All strategies are pure functions of precomputed indicator arrays and are
evaluated on a CLOSED bar i; the engine (core/backtester/m15_engine.py)
fills any resulting order at bar i+1's open. Nothing here sizes positions
or knows about the account -- that is Shield's job.

  BaselineCross   -- stand-in for the original EA: EMA fast/slow crossover,
                     fixed 1000-point stop, no TP, exit on the opposite cross.
                     (The real EA's .mq5 is not in the repo; this is an
                     approximation, not a reproduction.)
  AtrTrendFilter  -- same crossover trigger, but only in the direction of a
                     sloping EMA200, only while ADX >= adx_min (skips
                     side-way regimes), with ATR-scaled stop, R-multiple TP
                     and a chandelier trailing stop once 1R in profit.
  MtfPullback     -- H1/H4 trend bias (closed HTF bars only) with an M15
                     pullback-to-EMA entry and a structure-based stop.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from gold_trading_system.core.strategies.indicators import adx, atr, ema, rolling_std, rsi, sma
from gold_trading_system.core.strategies.types import Bar, Side


@dataclass(frozen=True)
class EntrySignal:
    side: Side
    stop_loss_points: float
    take_profit_points: float | None


class Indicators:
    """Indicator arrays computed once per bar series and shared by every
    parameter set in a grid search (only thresholds vary between runs)."""

    def __init__(self, bars: list[Bar], point: float, base_minutes: int = 15) -> None:
        self.point = point
        self.base_minutes = base_minutes  # bar length; HTF bars close on the last base bar
        self.opens = [b.open for b in bars]
        self.highs = [b.high for b in bars]
        self.lows = [b.low for b in bars]
        self.closes = [b.close for b in bars]
        self.timestamps = [b.timestamp for b in bars]
        self._ema: dict[int, list[float | None]] = {}
        self._atr: dict[int, list[float | None]] = {}
        self._adx: dict[int, list[float | None]] = {}
        self._htf: dict[tuple[int, int, int], list[Side | None]] = {}
        self._misc: dict[tuple, object] = {}

    def ema(self, period: int) -> list[float | None]:
        if period not in self._ema:
            self._ema[period] = ema(self.closes, period)
        return self._ema[period]

    def atr_points(self, period: int) -> list[float | None]:
        if period not in self._atr:
            self._atr[period] = [
                None if v is None else v / self.point for v in atr(self.highs, self.lows, self.closes, period)
            ]
        return self._atr[period]

    def adx(self, period: int) -> list[float | None]:
        if period not in self._adx:
            self._adx[period] = adx(self.highs, self.lows, self.closes, period)
        return self._adx[period]

    def rsi(self, period: int) -> list[float | None]:
        key = ("rsi", period)
        if key not in self._misc:
            self._misc[key] = rsi(self.closes, period)
        return self._misc[key]

    def bollinger(self, period: int, k: float) -> tuple[list[float | None], list[float | None], list[float | None]]:
        """(middle, upper, lower) bands: SMA +/- k population std devs."""
        key = ("bb", period, k)
        if key not in self._misc:
            mid, sd = sma(self.closes, period), rolling_std(self.closes, period)
            upper = [None if m is None else m + k * d for m, d in zip(mid, sd)]
            lower = [None if m is None else m - k * d for m, d in zip(mid, sd)]
            self._misc[key] = (mid, upper, lower)
        return self._misc[key]

    def htf_trend(self, tf_minutes: int, ema_period: int, slope_bars: int) -> list[Side | None]:
        """Higher-timeframe bias per M15 bar, built from the M15 bars themselves.

        At M15 bar i only HTF bars that have CLOSED by bar i's close are used
        (no look-ahead): BUY if the last closed HTF bar closed above its EMA
        and that EMA rose over `slope_bars` HTF bars, SELL for the mirror
        case, else None. Buckets align to server midnight, like MT5's H1/H4.
        """
        key = (tf_minutes, ema_period, slope_bars)
        if key not in self._htf:
            self._htf[key] = _htf_trend(
                self.timestamps, self.closes, tf_minutes, ema_period, slope_bars, self.base_minutes,
            )
        return self._htf[key]


def _htf_trend(
    timestamps: list[datetime], closes: list[float], tf_minutes: int, ema_period: int, slope_bars: int,
    base_minutes: int = 15,
) -> list[Side | None]:
    tf, base = timedelta(minutes=tf_minutes), timedelta(minutes=base_minutes)
    htf_closes: list[float] = []
    bucket_start: datetime | None = None
    last_closed: list[int] = []  # per M15 bar: index of the last CLOSED HTF bar, -1 if none
    for ts, close in zip(timestamps, closes):
        day = ts.replace(hour=0, minute=0, second=0, microsecond=0)
        start = day + ((ts - day) // tf) * tf
        if start != bucket_start:
            bucket_start = start
            htf_closes.append(close)
        else:
            htf_closes[-1] = close
        k = len(htf_closes) - 1
        last_closed.append(k if ts + base >= start + tf else k - 1)

    htf_ema = ema(htf_closes, ema_period)
    out: list[Side | None] = []
    for k in last_closed:
        j = k - slope_bars
        if j < 0 or htf_ema[k] is None or htf_ema[j] is None:
            out.append(None)
        elif htf_closes[k] > htf_ema[k] > htf_ema[j]:
            out.append(Side.BUY)
        elif htf_closes[k] < htf_ema[k] < htf_ema[j]:
            out.append(Side.SELL)
        else:
            out.append(None)
    return out


def _chandelier(
    atr_points: float | None, point: float, mult: float, side: Side, entry: float, initial_risk: float, best: float,
) -> float | None:
    """Trailing stop `mult` x ATR from the best price, armed once 1R in profit.
    The engine only ever ratchets it forward."""
    if atr_points is None:
        return None
    favorable = best - entry if side is Side.BUY else entry - best
    if favorable < initial_risk:
        return None
    offset = mult * atr_points * point
    return best - offset if side is Side.BUY else best + offset


def _cross(fast: list[float | None], slow: list[float | None], i: int) -> Side | None:
    if i < 1 or None in (fast[i], slow[i], fast[i - 1], slow[i - 1]):
        return None
    if fast[i] > slow[i] and fast[i - 1] <= slow[i - 1]:
        return Side.BUY
    if fast[i] < slow[i] and fast[i - 1] >= slow[i - 1]:
        return Side.SELL
    return None


class BaselineCross:
    name = "baseline_ema_cross"

    def __init__(self, ind: Indicators, fast_ema: int, slow_ema: int, stop_loss_points: float) -> None:
        self.fast, self.slow = ind.ema(fast_ema), ind.ema(slow_ema)
        self.stop_loss_points = stop_loss_points

    def entry_signal(self, i: int) -> EntrySignal | None:
        side = _cross(self.fast, self.slow, i)
        return None if side is None else EntrySignal(side, self.stop_loss_points, None)

    def exit_signal(self, i: int, side: Side) -> bool:
        cross = _cross(self.fast, self.slow, i)
        return cross is not None and cross is not side

    def trail_stop(self, i: int, side: Side, entry: float, initial_risk: float, best: float) -> float | None:
        return None


class AtrTrendFilter:
    name = "atr_trend_filter"

    def __init__(
        self, ind: Indicators, *, fast_ema: int, slow_ema: int, trend_ema: int, trend_slope_bars: int,
        atr_period: int, adx_period: int, adx_min: float, sl_atr_mult: float, reward_risk: float,
        trail_atr_mult: float,
    ) -> None:
        self.point = ind.point
        self.closes = ind.closes
        self.fast, self.slow, self.trend = ind.ema(fast_ema), ind.ema(slow_ema), ind.ema(trend_ema)
        self.atr = ind.atr_points(atr_period)
        self.adx = ind.adx(adx_period)
        self.slope_bars = trend_slope_bars
        self.adx_min = adx_min
        self.sl_atr_mult = sl_atr_mult
        self.reward_risk = reward_risk
        self.trail_atr_mult = trail_atr_mult

    def _trend(self, i: int) -> Side | None:
        j = i - self.slope_bars
        if j < 0 or self.trend[i] is None or self.trend[j] is None:
            return None
        if self.closes[i] > self.trend[i] and self.trend[i] > self.trend[j]:
            return Side.BUY
        if self.closes[i] < self.trend[i] and self.trend[i] < self.trend[j]:
            return Side.SELL
        return None

    def entry_signal(self, i: int) -> EntrySignal | None:
        side = _cross(self.fast, self.slow, i)
        if side is None or side is not self._trend(i):
            return None
        if self.adx[i] is None or self.adx[i] < self.adx_min or self.atr[i] is None:
            return None
        sl = self.sl_atr_mult * self.atr[i]
        return EntrySignal(side, sl, sl * self.reward_risk)

    def exit_signal(self, i: int, side: Side) -> bool:
        cross = _cross(self.fast, self.slow, i)
        return cross is not None and cross is not side

    def trail_stop(self, i: int, side: Side, entry: float, initial_risk: float, best: float) -> float | None:
        return _chandelier(self.atr[i], self.point, self.trail_atr_mult, side, entry, initial_risk, best)


class MtfPullback:
    """H1/H4 bias + M15 pullback entry.

    Long (mirror for short), evaluated on closed M15 bar i:
      * the HTF bias (Indicators.htf_trend) is BUY;
      * optional session window, broker server hours [start, end);
      * within the last `pullback_bars` bars price traded down to the M15
        EMA(`pullback_ema`) -- the pullback;
      * bar i closes back above that EMA AND above the prior bar's high --
        the trend resuming.
    Stop sits beyond the pullback's extreme plus `stop_buffer_atr` x ATR,
    clamped to [min_sl_atr, max_sl_atr] x ATR. TP = reward_risk x stop.
    Exits early when the HTF bias flips to the other side; chandelier trail
    once 1R in profit.
    """

    name = "mtf_pullback"

    def __init__(
        self, ind: Indicators, *, htf_minutes: int, htf_ema: int, htf_slope_bars: int, pullback_ema: int,
        pullback_bars: int, atr_period: int, stop_buffer_atr: float, min_sl_atr: float, max_sl_atr: float,
        reward_risk: float, trail_atr_mult: float, session_hours: list[int] | None,
    ) -> None:
        self.point = ind.point
        self.highs, self.lows, self.closes, self.timestamps = ind.highs, ind.lows, ind.closes, ind.timestamps
        self.bias = ind.htf_trend(htf_minutes, htf_ema, htf_slope_bars)
        self.pull = ind.ema(pullback_ema)
        self.atr = ind.atr_points(atr_period)
        self.pullback_bars = pullback_bars
        self.stop_buffer_atr, self.min_sl_atr, self.max_sl_atr = stop_buffer_atr, min_sl_atr, max_sl_atr
        self.reward_risk = reward_risk
        self.trail_atr_mult = trail_atr_mult
        self.session = tuple(session_hours) if session_hours else None

    def _in_session(self, i: int) -> bool:
        return self.session is None or self.session[0] <= self.timestamps[i].hour < self.session[1]

    def entry_signal(self, i: int) -> EntrySignal | None:
        side = self.bias[i]
        if side is None or i <= self.pullback_bars or not self._in_session(i):
            return None
        atr_pts, ema_now = self.atr[i], self.pull[i]
        window = range(i - self.pullback_bars, i)
        if atr_pts is None or ema_now is None or any(self.pull[j] is None for j in window):
            return None

        if side is Side.BUY:
            pulled_back = any(self.lows[j] <= self.pull[j] for j in window)
            resumed = self.closes[i] > ema_now and self.closes[i] > self.highs[i - 1]
            extreme_dist = self.closes[i] - min(self.lows[j] for j in range(i - self.pullback_bars, i + 1))
        else:
            pulled_back = any(self.highs[j] >= self.pull[j] for j in window)
            resumed = self.closes[i] < ema_now and self.closes[i] < self.lows[i - 1]
            extreme_dist = max(self.highs[j] for j in range(i - self.pullback_bars, i + 1)) - self.closes[i]
        if not (pulled_back and resumed):
            return None

        sl = extreme_dist / self.point + self.stop_buffer_atr * atr_pts
        sl = min(max(sl, self.min_sl_atr * atr_pts), self.max_sl_atr * atr_pts)
        return EntrySignal(side, sl, sl * self.reward_risk)

    def exit_signal(self, i: int, side: Side) -> bool:
        return self.bias[i] is not None and self.bias[i] is not side

    def trail_stop(self, i: int, side: Side, entry: float, initial_risk: float, best: float) -> float | None:
        return _chandelier(self.atr[i], self.point, self.trail_atr_mult, side, entry, initial_risk, best)
