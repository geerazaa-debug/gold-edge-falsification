"""
Shield circuit breaker: stops trading when equity losses hit the limits in
ShieldLimits.

  DAILY_HALT -- equity fell max_daily_loss_pct below the day-start equity.
                Flatten and block entries until the next trading day.
  KILLED     -- equity fell max_drawdown_pct below its peak. Flatten and
                block entries PERMANENTLY. Only manual_reset() (a human,
                named operator) clears it; a new day does not.

Feed it every equity observation (floating P&L included) via update(). The
`day` key is whatever the caller's day boundary is -- for MT5 that is the
broker server date, matching how prop firms and MT5 reports roll days.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from gold_trading_system.core.risk_guardrails.validator import ShieldLimits


class BreakerState(str, Enum):
    ACTIVE = "ACTIVE"
    DAILY_HALT = "DAILY_HALT"
    KILLED = "KILLED"


@dataclass(frozen=True)
class BreakerVerdict:
    state: BreakerState
    flatten_now: bool        # True only on the update that trips the breaker
    daily_loss_pct: float
    drawdown_pct: float
    reason: str | None


class CircuitBreaker:
    def __init__(self, limits: ShieldLimits, initial_equity: float) -> None:
        if initial_equity <= 0:
            raise ValueError("initial_equity must be > 0")
        self._limits = limits
        self._state = BreakerState.ACTIVE
        self._reason: str | None = None
        self._day: date | None = None
        self._day_start_equity = initial_equity
        self._peak_equity = initial_equity
        self.trip_log: list[tuple[date | None, BreakerState, str]] = []

    @property
    def state(self) -> BreakerState:
        return self._state

    @property
    def halted_reason(self) -> str | None:
        return None if self._state is BreakerState.ACTIVE else self._reason

    def update(self, day: date, equity: float) -> BreakerVerdict:
        if day != self._day:
            self._day = day
            self._day_start_equity = equity
            if self._state is BreakerState.DAILY_HALT:
                self._state, self._reason = BreakerState.ACTIVE, None

        self._peak_equity = max(self._peak_equity, equity)
        daily_loss_pct = max(0.0, (self._day_start_equity - equity) / self._day_start_equity * 100.0)
        drawdown_pct = max(0.0, (self._peak_equity - equity) / self._peak_equity * 100.0)

        tripped = False
        if self._state is not BreakerState.KILLED and drawdown_pct >= self._limits.max_drawdown_pct:
            self._trip(BreakerState.KILLED,
                       f"drawdown {drawdown_pct:.2f}% >= {self._limits.max_drawdown_pct}% (human reset required)")
            tripped = True
        elif self._state is BreakerState.ACTIVE and daily_loss_pct >= self._limits.max_daily_loss_pct:
            self._trip(BreakerState.DAILY_HALT,
                       f"daily loss {daily_loss_pct:.2f}% >= {self._limits.max_daily_loss_pct}%")
            tripped = True

        return BreakerVerdict(self._state, tripped, daily_loss_pct, drawdown_pct, self.halted_reason)

    def manual_reset(self, operator: str, note: str) -> None:
        """Human sign-off to resume after a KILL. Re-bases the peak to the
        current day-start equity so the same drawdown does not re-trip."""
        if not operator.strip() or not note.strip():
            raise ValueError("manual_reset requires a named operator and a note")
        self.trip_log.append((self._day, BreakerState.ACTIVE, f"manual reset by {operator}: {note}"))
        self._state, self._reason = BreakerState.ACTIVE, None
        self._peak_equity = self._day_start_equity

    def _trip(self, state: BreakerState, reason: str) -> None:
        self._state, self._reason = state, reason
        self.trip_log.append((self._day, state, reason))
