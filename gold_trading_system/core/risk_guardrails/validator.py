"""
Shield: deterministic pre-trade validation and risk-based position sizing.

No strategy, script, or AI agent can loosen these rules at runtime:

  * HARD_* ceilings are module constants. config/risk_rules.yaml is loaded
    into a frozen ShieldLimits model whose validators reject any value
    looser than its ceiling -- the YAML can only tighten.
  * ShieldLimits and every request/decision model are frozen; a strategy
    holding a reference cannot mutate them.
  * The validator never rounds a lot UP to the broker minimum. If the risk
    budget cannot afford min_lot at the proposed stop, the trade is
    REJECTED. (An earlier sizing module clamped up to min_lot, which on a
    $100 account silently turned a 1% risk into 10%+.)

Changing a HARD_* constant is a human decision, not an agent one -- see
README.md "Risk-limit policy".
"""

from __future__ import annotations

import math
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

HARD_MAX_DAILY_LOSS_PCT = 5.0
HARD_MAX_DRAWDOWN_PCT = 20.0
HARD_MAX_RISK_PER_TRADE_PCT = 2.0
HARD_MIN_REWARD_RISK = 1.5
HARD_MAX_TOTAL_OPEN_RISK_PCT = 4.0
HARD_MAX_SPREAD_POINTS = 150.0
HARD_MAX_LOT_SIZE = 10.0

DEFAULT_RULES_PATH = Path(__file__).resolve().parents[2] / "config" / "risk_rules.yaml"


class ShieldLimits(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max_daily_loss_pct: float = Field(gt=0, le=HARD_MAX_DAILY_LOSS_PCT)
    max_drawdown_pct: float = Field(gt=0, le=HARD_MAX_DRAWDOWN_PCT)
    risk_per_trade_pct: float = Field(gt=0, le=HARD_MAX_RISK_PER_TRADE_PCT)
    min_reward_risk: float = Field(ge=HARD_MIN_REWARD_RISK)
    max_total_open_risk_pct: float = Field(gt=0, le=HARD_MAX_TOTAL_OPEN_RISK_PCT)
    max_spread_points: float = Field(gt=0, le=HARD_MAX_SPREAD_POINTS)
    max_lot_size: float = Field(gt=0, le=HARD_MAX_LOT_SIZE)

    @model_validator(mode="after")
    def _open_risk_covers_one_trade(self) -> ShieldLimits:
        if self.max_total_open_risk_pct < self.risk_per_trade_pct:
            raise ValueError("max_total_open_risk_pct must be >= risk_per_trade_pct")
        return self


def load_shield_limits(path: Path = DEFAULT_RULES_PATH) -> ShieldLimits:
    with path.open("r", encoding="utf-8") as f:
        return ShieldLimits(**yaml.safe_load(f))


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class InstrumentSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = "XAUUSD"
    point: float = Field(default=0.01, gt=0)
    point_value_usd_per_lot: float = Field(default=1.0, gt=0)  # $ per 1-point move per 1.0 lot
    min_lot: float = Field(default=0.01, gt=0)
    lot_step: float = Field(default=0.01, gt=0)


class AccountSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    equity: float = Field(gt=0)
    open_risk_usd: float = Field(default=0.0, ge=0)  # sum of risk-at-stop of open positions


class TradeRequest(BaseModel):
    """A strategy's proposal. Prices are what the order would be sent at.
    Structural sanity (SL/TP on the correct side of entry) is enforced here,
    so a malformed request cannot even be constructed."""

    model_config = ConfigDict(frozen=True)

    side: TradeSide
    entry_price: float = Field(gt=0)
    stop_loss_price: float = Field(gt=0)
    take_profit_price: float = Field(gt=0)
    spread_points: float = Field(ge=0)
    strategy: str = "unknown"

    @field_validator("entry_price", "stop_loss_price", "take_profit_price")
    @classmethod
    def _finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("price must be finite")
        return v

    @model_validator(mode="after")
    def _levels_on_correct_side(self) -> TradeRequest:
        if self.side is TradeSide.BUY:
            ok = self.stop_loss_price < self.entry_price < self.take_profit_price
        else:
            ok = self.take_profit_price < self.entry_price < self.stop_loss_price
        if not ok:
            raise ValueError(
                f"{self.side.value}: need SL/entry/TP ordered correctly, got "
                f"SL={self.stop_loss_price} entry={self.entry_price} TP={self.take_profit_price}"
            )
        return self


class ShieldDecision(BaseModel):
    """`reasons` entries are "<code>: <detail>"; codes are circuit_breaker,
    spread, reward_risk, account_too_small, open_risk."""

    model_config = ConfigDict(frozen=True)

    approved: bool
    lot_size: float = 0.0
    risk_usd: float = 0.0
    reward_risk: float = 0.0
    reasons: tuple[str, ...] = ()


class ShieldValidator:
    def __init__(self, limits: ShieldLimits, instrument: InstrumentSpec) -> None:
        self._limits = limits
        self._instrument = instrument

    @property
    def limits(self) -> ShieldLimits:
        return self._limits

    def validate(
        self, request: TradeRequest, account: AccountSnapshot, trading_halted_reason: str | None = None,
    ) -> ShieldDecision:
        lim, inst = self._limits, self._instrument
        reasons: list[str] = []

        if trading_halted_reason:
            reasons.append(f"circuit_breaker: {trading_halted_reason}")

        if request.spread_points > lim.max_spread_points:
            reasons.append(f"spread: {request.spread_points:.0f} > max {lim.max_spread_points:.0f} points")

        sl_points = abs(request.entry_price - request.stop_loss_price) / inst.point
        tp_points = abs(request.take_profit_price - request.entry_price) / inst.point
        # Rounded: levels arrive as float prices, so an exact 1.5R request can
        # compute as 1.4999999999999998 and be wrongly rejected (~33% of them).
        reward_risk = round(tp_points / sl_points, 6)
        if reward_risk < lim.min_reward_risk:
            reasons.append(f"reward_risk: {reward_risk:.2f} < min {lim.min_reward_risk:.2f}")

        risk_budget = account.equity * lim.risk_per_trade_pct / 100.0
        risk_per_lot = sl_points * inst.point_value_usd_per_lot
        # Round DOWN to the lot step (small epsilon absorbs float noise in exact multiples).
        lot = math.floor(risk_budget / risk_per_lot / inst.lot_step + 1e-9) * inst.lot_step
        lot = round(min(lot, lim.max_lot_size), 8)
        if lot < inst.min_lot:
            reasons.append(
                f"account_too_small: min lot {inst.min_lot} at {sl_points:.0f}-point stop risks "
                f"${inst.min_lot * risk_per_lot:.2f}, budget is ${risk_budget:.2f} "
                f"({lim.risk_per_trade_pct}% of ${account.equity:.2f})"
            )
            lot = 0.0
        risk_usd = lot * risk_per_lot

        open_risk_cap = account.equity * lim.max_total_open_risk_pct / 100.0
        if account.open_risk_usd + risk_usd > open_risk_cap + 1e-9:
            reasons.append(
                f"open_risk: ${account.open_risk_usd + risk_usd:.2f} would exceed cap ${open_risk_cap:.2f}"
            )

        if reasons:
            return ShieldDecision(approved=False, reward_risk=reward_risk, reasons=tuple(reasons))
        return ShieldDecision(approved=True, lot_size=lot, risk_usd=risk_usd, reward_risk=reward_risk)
