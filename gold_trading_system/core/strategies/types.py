"""
Shared vocabulary for strategies, the risk engine, and (later) the
backtester/execution layer -- deliberately shaped like an MT5/MQL5 EA's
action set (OrderSend / OrderModify / OrderClose) so this logic maps
cleanly onto real MQL5 code later, while staying real, runnable,
testable Python now rather than literal pseudocode.

Strategies never touch the market directly: `Strategy.evaluate()` only
*proposes* a list of SignalAction objects. The risk engine (Phase 2,
core/risk_engine) decides which of those proposals are actually allowed,
and a later execution layer (backtester in Phase 4, live/dry-run bridge
in Phase 3) is what actually turns an approved action into a fill.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

    def opposite(self) -> "Side":
        return Side.SELL if self is Side.BUY else Side.BUY


class OrderType(str, Enum):
    MARKET = "MARKET"
    STOP = "STOP"
    LIMIT = "LIMIT"


class ActionType(str, Enum):
    OPEN_MARKET = "OPEN_MARKET"
    OPEN_PENDING = "OPEN_PENDING"
    CANCEL_PENDING = "CANCEL_PENDING"
    CLOSE_POSITION = "CLOSE_POSITION"
    # CLOSE_ALL scope convention: closes every open position belonging to
    # `SignalAction.strategy_name` (e.g. a grid strategy closing its own
    # basket). The one reserved value strategy_name="RISK_ENGINE" means
    # "every open position across every strategy, system-wide" -- used
    # only by RiskEngine's own hard-stop injection, never proposed by a
    # strategy itself.
    CLOSE_ALL = "CLOSE_ALL"
    MODIFY_SL = "MODIFY_SL"
    # Reduces a position's lot_size by SignalAction.lot_size, closing that
    # portion and leaving the remainder open at its original entry/stop/
    # target. Not proposed by any Phase 2 strategy -- added for Phase 3's
    # dry-run simulator, which applies a partial-profit-taking rule at the
    # execution-infrastructure layer rather than inside a strategy.
    PARTIAL_CLOSE = "PARTIAL_CLOSE"


@dataclass(frozen=True)
class ContractSpec:
    """From config/broker_costs.yaml -> contract. Shared by any strategy
    or risk-engine component that needs to convert raw price distance
    into points, or points into USD P&L.
    """

    price_point: float
    point_value_usd_per_lot: float


@dataclass(frozen=True)
class Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    atr_points: float | None = None       # precomputed ATR(14) in points, if available
    spread_points: float | None = None    # live spread at this bar's close, if available


@dataclass(frozen=True)
class SignalAction:
    action: ActionType
    strategy_name: str
    reason: str = ""
    side: Side | None = None
    order_type: OrderType = OrderType.MARKET
    lot_size: float = 0.0
    stop_loss_points: float | None = None
    take_profit_points: float | None = None
    pending_distance_points: float | None = None
    expiry_bars: int | None = None
    grid_level: int = 0
    position_id: str | None = None        # target of CLOSE_POSITION / MODIFY_SL
    pending_order_id: str | None = None   # target of CANCEL_PENDING
    new_stop_loss_price: float | None = None
    # % of equity to risk on this trade, sized against stop_loss_points --
    # None means "use lot_size as
    # proposed, dynamic sizing does not apply" (e.g. DT Grid, which has no
    # fixed per-trade stop-loss distance to size against). When set, the
    # risk engine OVERRIDES lot_size with a risk-%-derived value, clipped
    # to [min_lot_size, max_lot_size] from risk_limits.yaml.
    risk_pct: float | None = None


@dataclass
class Position:
    position_id: str
    strategy_name: str
    side: Side
    lot_size: float
    entry_price: float
    opened_at: datetime
    stop_loss_price: float | None = None
    take_profit_price: float | None = None
    grid_level: int = 0


@dataclass
class PendingOrder:
    order_id: str
    strategy_name: str
    side: Side
    order_type: OrderType
    trigger_price: float
    lot_size: float
    stop_loss_points: float
    take_profit_points: float
    placed_at_bar_index: int
    expiry_bars: int


@dataclass
class StrategyContext:
    """Read-only snapshot handed to Strategy.evaluate() each bar. Strategies
    must not mutate open_positions/pending_orders directly -- they only
    propose actions; the execution layer applies them and rebuilds the
    next context.
    """

    bar_index: int
    bar: Bar
    history: list[Bar]              # bars up to and including `bar`, oldest first
    open_positions: list[Position] = field(default_factory=list)
    pending_orders: list[PendingOrder] = field(default_factory=list)
    equity: float = 0.0
    balance: float = 0.0
    trades_today: int = 0
    # Rolling window of the higher timeframe's revealed bars (M15, for an
    # M1-frequency strategy), supplied by the execution simulator so an
    # M1 strategy can implement a genuine higher-timeframe trend filter
    # (e.g. DT Point's EMA200) rather than faking it on its own faster
    # timeframe. Same list reference as the M15 strategies' own history
    # -- read-only, per this class's existing no-mutation contract.
    higher_tf_history: list[Bar] = field(default_factory=list)
    # Bars elapsed since THIS strategy's most recent closed trade that was
    # a loss, or None if it has no losing trade yet (or no trades at all).
    # Computed by the execution simulator from its own closed-trade
    # ledger; used by e.g. DT Point's post-stopout cooldown.
    bars_since_last_loss: int | None = None
