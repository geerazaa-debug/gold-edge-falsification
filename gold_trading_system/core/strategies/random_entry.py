"""
Random-entry null model: the zero-edge benchmark for the tournament.

Entries are coin flips -- on each eligible flat bar, enter with probability
`entry_prob`, side by `long_prob` (or a given per-bar side) -- but
everything AFTER the entry is identical to the trend strategies: ATR stop, R-multiple TP, chandelier trail once 1R in
profit, same engine, same costs, same Shield. Whatever R-per-trade this
earns is what the exit mechanics + cost friction produce with NO
information in the entry. A strategy only has an entry edge if it beats
this distribution.

Seeded and precomputed per instance, so a run is reproducible and the coin
flips do not depend on how often the engine asks.
"""

from __future__ import annotations

import random

from gold_trading_system.core.strategies.m15_trend import EntrySignal, Indicators, _chandelier
from gold_trading_system.core.strategies.types import Side


class RandomEntry:
    name = "random_entry"

    def __init__(
        self, ind: Indicators, *, seed: int, entry_prob: float, atr_period: int, sl_atr_mult: float,
        reward_risk: float, trail_atr_mult: float, session_hours: list[int] | None = None,
        long_prob: float = 0.5, sides: list[Side | None] | None = None,
    ) -> None:
        """`long_prob` sets the long share (match the strategy's own, so a long
        bias in a rising market is not mistaken for timing skill). `sides`
        instead fixes the side per bar (e.g. the strategy's HTF bias; None =
        no entry), so only the TIMING is random."""
        if not 0 < entry_prob <= 1:
            raise ValueError("entry_prob must be in (0, 1]")
        rng = random.Random(seed)
        n = len(ind.closes)
        self._fire = [rng.random() < entry_prob for _ in range(n)]
        coin = [Side.BUY if rng.random() < long_prob else Side.SELL for _ in range(n)]
        self._side = coin if sides is None else list(sides)
        self.point = ind.point
        self.timestamps = ind.timestamps
        self.atr = ind.atr_points(atr_period)
        self.sl_atr_mult, self.reward_risk, self.trail_atr_mult = sl_atr_mult, reward_risk, trail_atr_mult
        self.session = tuple(session_hours) if session_hours else None

    def entry_signal(self, i: int) -> EntrySignal | None:
        if not self._fire[i] or self.atr[i] is None or self._side[i] is None:
            return None
        if self.session and not self.session[0] <= self.timestamps[i].hour < self.session[1]:
            return None
        sl = self.sl_atr_mult * self.atr[i]
        return EntrySignal(self._side[i], sl, sl * self.reward_risk)

    def exit_signal(self, i: int, side: Side) -> bool:
        return False

    def trail_stop(self, i: int, side: Side, entry: float, initial_risk: float, best: float) -> float | None:
        return _chandelier(self.atr[i], self.point, self.trail_atr_mult, side, entry, initial_risk, best)
