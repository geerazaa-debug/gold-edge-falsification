"""
Minimal, dependency-free indicator library (no NumPy/pandas) so each
function can be reasoned about line-by-line the way an MQL5 iMA/iATR call
would be. All functions are pure and return a list aligned to the input,
with None padding during the warm-up period rather than raising or
silently shortening the series.
"""

from __future__ import annotations


def sma(values: list[float], period: int) -> list[float | None]:
    if period < 1:
        raise ValueError("period must be >= 1")
    out: list[float | None] = [None] * (period - 1)
    for i in range(period - 1, len(values)):
        out.append(sum(values[i - period + 1: i + 1]) / period)
    return out


def ema(values: list[float], period: int) -> list[float | None]:
    """Standard exponential moving average, seeded with the SMA of the
    first `period` values (a common, well-defined seeding convention).
    """
    if period < 1:
        raise ValueError("period must be >= 1")
    if len(values) < period:
        return [None] * len(values)

    alpha = 2.0 / (period + 1.0)
    out: list[float | None] = [None] * (period - 1)
    seed = sum(values[:period]) / period
    out.append(seed)
    prev = seed
    for i in range(period, len(values)):
        current = alpha * values[i] + (1.0 - alpha) * prev
        out.append(current)
        prev = current
    return out


def moving_average(values: list[float], period: int, ma_type: str = "EMA") -> list[float | None]:
    ma_type = ma_type.upper()
    if ma_type == "SMA":
        return sma(values, period)
    if ma_type == "EMA":
        return ema(values, period)
    raise ValueError(f"Unknown ma_type: {ma_type}")


def true_range(prev_close: float, high: float, low: float) -> float:
    return max(high - low, abs(high - prev_close), abs(low - prev_close))


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> list[float | None]:
    """Simple (non-Wilder-smoothed) ATR, aligned to the input series.
    Index i's value covers true ranges over bars [i-period+1, i].
    """
    n = len(closes)
    if not (len(highs) == len(lows) == n):
        raise ValueError("highs/lows/closes must be equal length")

    out: list[float | None] = [None] * n
    for i in range(1, n):
        # need `period` true-range values ending at i, i.e. bars 1..i, requiring i >= period
        if i < period:
            continue
        ranges = [
            true_range(closes[j - 1], highs[j], lows[j])
            for j in range(i - period + 1, i + 1)
        ]
        out[i] = sum(ranges) / period
    return out


def rolling_std(values: list[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * (period - 1)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1: i + 1]
        mean = sum(window) / period
        var = sum((x - mean) ** 2 for x in window) / period
        out.append(var ** 0.5)
    return out


def donchian_last(highs: list[float], lows: list[float], period: int) -> tuple[float | None, float | None]:
    """Same convention as donchian_channel (window strictly BEFORE the
    last bar), but computes only the final (upper, lower) pair in O(period)
    instead of O(n) -- for a caller (like DT Trailing) that only ever
    needs the latest value, calling the full donchian_channel() on every
    new bar recomputes the entire history each time, which is O(n^2)
    over a full run. Correctness cross-checked against donchian_channel's
    last entry before use (see tests).
    """
    n = len(highs)
    if n <= period:
        return None, None
    upper = max(highs[n - period - 1: n - 1])
    lower = min(lows[n - period - 1: n - 1])
    return upper, lower


def donchian_channel(
    highs: list[float], lows: list[float], period: int
) -> tuple[list[float | None], list[float | None]]:
    """Returns (upper, lower) channel series. upper[i]/lower[i] are the
    highest high / lowest low over the `period` bars STRICTLY BEFORE bar
    i (i.e. excluding bar i itself) -- the correct convention for a
    breakout signal (comparing the current bar's close against the prior
    channel, not a channel that already includes the current bar).
    """
    n = len(highs)
    upper: list[float | None] = [None] * n
    lower: list[float | None] = [None] * n
    for i in range(period, n):
        upper[i] = max(highs[i - period:i])
        lower[i] = min(lows[i - period:i])
    return upper, lower


def adx(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> list[float | None]:
    """Wilder's ADX, aligned to the input series (same as MT5's iADXWilder).

    +DM/-DM and TR are Wilder-smoothed (seeded with the sum of the first
    `period` values), DX is averaged the same way into ADX. The first
    value appears at index 2*period - 1; earlier entries are None.
    """
    n = len(closes)
    if not (len(highs) == len(lows) == n):
        raise ValueError("highs/lows/closes must be equal length")
    if period < 1:
        raise ValueError("period must be >= 1")

    out: list[float | None] = [None] * n
    if n < 2 * period:
        return out

    tr_s = plus_s = minus_s = 0.0
    dx_values: list[float] = []
    adx_prev: float | None = None
    for i in range(1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm = up if up > down and up > 0 else 0.0
        minus_dm = down if down > up and down > 0 else 0.0
        tr = true_range(closes[i - 1], highs[i], lows[i])

        if i <= period:
            tr_s += tr
            plus_s += plus_dm
            minus_s += minus_dm
            if i < period:
                continue
        else:
            tr_s = tr_s - tr_s / period + tr
            plus_s = plus_s - plus_s / period + plus_dm
            minus_s = minus_s - minus_s / period + minus_dm

        if tr_s == 0:
            dx = 0.0
        else:
            plus_di = 100.0 * plus_s / tr_s
            minus_di = 100.0 * minus_s / tr_s
            di_sum = plus_di + minus_di
            dx = 0.0 if di_sum == 0 else 100.0 * abs(plus_di - minus_di) / di_sum

        if adx_prev is None:
            dx_values.append(dx)
            if len(dx_values) == period:
                adx_prev = sum(dx_values) / period
                out[i] = adx_prev
        else:
            adx_prev = (adx_prev * (period - 1) + dx) / period
            out[i] = adx_prev
    return out


def rsi(values: list[float], period: int = 14) -> list[float | None]:
    """Wilder's RSI, aligned to the input; first value at index `period`."""
    n = len(values)
    out: list[float | None] = [None] * n
    if n <= period:
        return out
    gains = losses = 0.0
    for i in range(1, period + 1):
        change = values[i] - values[i - 1]
        gains += max(change, 0.0)
        losses += max(-change, 0.0)
    avg_gain, avg_loss = gains / period, losses / period
    for i in range(period, n):
        if i > period:
            change = values[i] - values[i - 1]
            avg_gain = (avg_gain * (period - 1) + max(change, 0.0)) / period
            avg_loss = (avg_loss * (period - 1) + max(-change, 0.0)) / period
        out[i] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return out
