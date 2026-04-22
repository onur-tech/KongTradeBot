"""Tests for core/plugin_base.py."""
import asyncio
import pytest
from datetime import datetime, timezone

from core.plugin_base import (
    Fill,
    Order,
    PluginMode,
    Signal,
    StrategyPlugin,
    Tick,
)


# ── minimal concrete subclass ─────────────────────────────────────────────────

class _ConcretePlugin(StrategyPlugin):
    async def on_signal(self, signal: Signal):
        return Order(signal=signal, size_usdc=signal.size_usdc, mode=self.mode)

    async def on_fill(self, fill: Fill) -> None:
        pass

    async def on_tick(self, tick: Tick) -> None:
        pass


# ── instantiation ─────────────────────────────────────────────────────────────

def test_plugin_default_mode_is_live():
    p = _ConcretePlugin()
    assert p.mode == "live"


def test_plugin_live_mode_explicit():
    p = _ConcretePlugin(mode="live")
    assert p.is_live() is True
    assert p.is_simulation() is False


def test_plugin_simulation_mode():
    p = _ConcretePlugin(mode="simulation")
    assert p.mode == "simulation"
    assert p.is_simulation() is True
    assert p.is_live() is False


def test_plugin_invalid_mode_raises():
    with pytest.raises(ValueError, match="Invalid mode"):
        _ConcretePlugin(mode="paper")  # type: ignore[arg-type]


# ── abstract enforcement ──────────────────────────────────────────────────────

def test_abstract_class_cannot_be_instantiated():
    with pytest.raises(TypeError):
        StrategyPlugin()  # type: ignore[abstract]


# ── dataclasses ───────────────────────────────────────────────────────────────

def test_signal_defaults_timestamp():
    sig = Signal(
        market_id="m1", token_id="t1", side="buy", price=0.6, size_usdc=10.0
    )
    assert isinstance(sig.timestamp, datetime)
    assert sig.timestamp.tzinfo is not None


def test_tick_fields():
    tick = Tick(market_id="m1", token_id="t1", price=0.72)
    assert tick.price == 0.72
    assert isinstance(tick.timestamp, datetime)


def test_fill_mode_propagated():
    fill = Fill(
        order_id="ord1",
        market_id="m1",
        token_id="t1",
        filled_price=0.65,
        filled_size_usdc=10.0,
        mode="simulation",
    )
    assert fill.mode == "simulation"


# ── async interface ───────────────────────────────────────────────────────────

def test_on_signal_returns_order_in_live():
    p = _ConcretePlugin(mode="live")
    sig = Signal(market_id="m", token_id="t", side="buy", price=0.5, size_usdc=5.0)
    order = asyncio.run(p.on_signal(sig))
    assert order is not None
    assert order.mode == "live"
    assert order.size_usdc == 5.0


def test_on_signal_returns_order_in_simulation():
    p = _ConcretePlugin(mode="simulation")
    sig = Signal(market_id="m", token_id="t", side="sell", price=0.8, size_usdc=3.0)
    order = asyncio.run(p.on_signal(sig))
    assert order is not None
    assert order.mode == "simulation"
