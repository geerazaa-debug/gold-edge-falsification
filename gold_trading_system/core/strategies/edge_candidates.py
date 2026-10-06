"""
Two edge hypotheses that are structurally different from the trend
strategies already rejected by the random-entry benchmark.

SessionBreakout (hypothesis A: volatility expansion at a session open)
    Range = high/low of bars in server hours [range_start, range_end).
    From range_end until trade_end, the FIRST bar that closes outside the
    range is traded in the breakout direction -- at most one trade a day.
    Squeeze filter: the range must be <= squeeze_factor x the median of the
    previous `squeeze_lookback` days' ranges (compressed range -> expansion).
    Stop at the range midpoint, clamped to [min_sl_atr, max_sl_atr] x ATR;
    TP = reward_risk x stop; flat at exit_hour (no overnight swap).
    Server time is GMT+2/+3, so London open = 10:00 and NY open = 16:30
    server time all year.

MeanReversionBands (hypothesis B: exhausted extremes revert)
    Long: the previous bar closed below the lower Bollinger band with RSI <=
    rsi_low, and this bar closes back inside the band, as an up bar. Mirror
    for shorts. Optional higher-timeframe filter: only fade in the direction
    of the HTF bias (buy dips in an uptrend). Stop beyond the extreme of the
    last `extreme_bars` bars plus a buffer, clamped to an ATR range; TP =
    reward_risk x stop (Shield's 1.5R minimum applies -- there is no early
    "middle band" exit that would undercut the declared target).

Both precompute their signals in __init__ from closed bars only.
"""

from __future__ import annotations

import statistics
from datetime import date

from gold_trading_system.core.strategies.m15_trend import EntrySignal, Indicators, _chandelier
from gold_trading_system.core.strategies.types import Side


def _clamp(value: float, lo: float, hi: float) -> float:
    return min(max(value, lo), hi)


class SessionBreakout:
    name = "session_breakout"

    def __init__(
        self, ind: Indicators, *, session: list[int], exit_hour: int, squeeze_factor: float,
        squeeze_lookback: int, atr_period: int, min_sl_atr: float, max_sl_atr: float,
        reward_risk: float, trail_atr_mult: float,
    ) -> None:
        self.point = ind.point
        self.atr = ind.atr_points(atr_period)
        self.timestamps = ind.timestamps
        self.exit_hour = exit_hour
        self.trail_atr_mult = trail_atr_mult
        range_start, range_end, trade_end = session
        self._signals: dict[int, EntrySignal] = {}

        ranges = self._daily_ranges(ind, range_start, range_end)
        traded: set[date] = set()
        for i, ts in enumerate(ind.timestamps):
            day = ts.date()
            rng = ranges.get(day)
            if rng is None or not range_end <= ts.hour < trade_end or day in traded or self.atr[i] is None:
                continue
            hi, lo = rng
            side = Side.BUY if ind.closes[i] > hi else Side.SELL if ind.closes[i] < lo else None
            if side is None:
                continue
            traded.add(day)
            history = past_widths_for(ranges, day, squeeze_lookback)
            if len(history) < squeeze_lookback or (hi - lo) > squeeze_factor * statistics.median(history):
                continue
            mid = (hi + lo) / 2
            sl = _clamp(abs(ind.closes[i] - mid) / self.point, min_sl_atr * self.atr[i], max_sl_atr * self.atr[i])
            self._signals[i] = EntrySignal(side, sl, sl * reward_risk)

    @staticmethod
    def _daily_ranges(ind: Indicators, start: int, end: int) -> dict[date, tuple[float, float]]:
        out: dict[date, tuple[float, float]] = {}
        for ts, h, lo in zip(ind.timestamps, ind.highs, ind.lows):
            if start <= ts.hour < end:
                d = ts.date()
                prev = out.get(d)
                out[d] = (h, lo) if prev is None else (max(prev[0], h), min(prev[1], lo))
        return out

    def entry_signal(self, i: int) -> EntrySignal | None:
        return self._signals.get(i)

    def exit_signal(self, i: int, side: Side) -> bool:
        return self.timestamps[i].hour >= self.exit_hour

    def trail_stop(self, i: int, side: Side, entry: float, initial_risk: float, best: float) -> float | None:
        return _chandelier(self.atr[i], self.point, self.trail_atr_mult, side, entry, initial_risk, best)


def past_widths_for(ranges: dict[date, tuple[float, float]], day: date, lookback: int) -> list[float]:
    """Range widths of the `lookback` trading days before `day` (oldest first)."""
    earlier = [d for d in ranges if d < day]
    return [ranges[d][0] - ranges[d][1] for d in sorted(earlier)[-lookback:]]


class MeanReversionBands:
    name = "mean_reversion_bands"

    def __init__(
        self, ind: Indicators, *, bb_period: int, bb_k: float, rsi_period: int, rsi_low: float,
        htf_minutes: int | None, htf_ema: int, htf_slope_bars: int, extreme_bars: int,
        stop_buffer_atr: float, atr_period: int, min_sl_atr: float, max_sl_atr: float,
        reward_risk: float, trail_atr_mult: float,
    ) -> None:
        self.point = ind.point
        self.atr = ind.atr_points(atr_period)
        self.trail_atr_mult = trail_atr_mult
        _, upper, lower = ind.bollinger(bb_period, bb_k)
        r = ind.rsi(rsi_period)
        bias = ind.htf_trend(htf_minutes, htf_ema, htf_slope_bars) if htf_minutes else None
        c, o, h, lo = ind.closes, ind.opens, ind.highs, ind.lows
        self._signals: dict[int, EntrySignal] = {}

        for i in range(max(extreme_bars, 1), len(c)):
            p = i - 1
            if None in (upper[p], lower[p], upper[i], lower[i], r[p], self.atr[i]):
                continue
            if c[p] < lower[p] and r[p] <= rsi_low and lower[i] < c[i] and c[i] > o[i]:
                side, dist = Side.BUY, c[i] - min(lo[i - extreme_bars:i + 1])
            elif c[p] > upper[p] and r[p] >= 100 - rsi_low and c[i] < upper[i] and c[i] < o[i]:
                side, dist = Side.SELL, max(h[i - extreme_bars:i + 1]) - c[i]
            else:
                continue
            if bias is not None and bias[i] is not side:
                continue
            sl = _clamp(dist / self.point + stop_buffer_atr * self.atr[i],
                        min_sl_atr * self.atr[i], max_sl_atr * self.atr[i])
            self._signals[i] = EntrySignal(side, sl, sl * reward_risk)

    def entry_signal(self, i: int) -> EntrySignal | None:
        return self._signals.get(i)

    def exit_signal(self, i: int, side: Side) -> bool:
        return False

    def trail_stop(self, i: int, side: Side, entry: float, initial_risk: float, best: float) -> float | None:
        return _chandelier(self.atr[i], self.point, self.trail_atr_mult, side, entry, initial_risk, best)
