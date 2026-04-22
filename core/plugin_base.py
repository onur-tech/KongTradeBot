"""Plugin base class and shared dataclasses for live and simulation strategies."""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional


PluginMode = Literal["live", "simulation"]


@dataclass
class Tick:
    """A single market price update."""
    market_id: str
    token_id: str
    price: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Signal:
    """A trade signal emitted by a strategy or wallet monitor."""
    market_id: str
    token_id: str
    side: Literal["buy", "sell"]
    price: float
    size_usdc: float
    source_wallet: str = ""
    tx_hash: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Order:
    """An order derived from a Signal, ready for execution."""
    signal: Signal
    size_usdc: float
    mode: PluginMode = "live"
    order_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Fill:
    """A confirmed order fill."""
    order_id: str
    market_id: str
    token_id: str
    filled_price: float
    filled_size_usdc: float
    mode: PluginMode = "live"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class StrategyPlugin(abc.ABC):
    """Abstract base class for all KongTrade strategy plugins.

    Subclass this, implement the three abstract methods, and pass
    ``mode="live"`` or ``mode="simulation"`` to the constructor.
    """

    def __init__(self, mode: PluginMode = "live") -> None:
        if mode not in ("live", "simulation"):
            raise ValueError(f"Invalid mode '{mode}'. Must be 'live' or 'simulation'.")
        self._mode: PluginMode = mode

    # ── mode helpers ──────────────────────────────────────────────────────────

    @property
    def mode(self) -> PluginMode:
        return self._mode

    def is_live(self) -> bool:
        return self._mode == "live"

    def is_simulation(self) -> bool:
        return self._mode == "simulation"

    # ── abstract interface ────────────────────────────────────────────────────

    @abc.abstractmethod
    async def on_signal(self, signal: Signal) -> Optional[Order]:
        """React to an incoming trade signal. Return an Order or None."""

    @abc.abstractmethod
    async def on_fill(self, fill: Fill) -> None:
        """Called when an order has been filled."""

    @abc.abstractmethod
    async def on_tick(self, tick: Tick) -> None:
        """Called on every market price tick."""
