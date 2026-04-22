"""
Integration test: StrategyPlugin using Safety modules in both modes.

Verifies that:
- A plugin wired with safety modules works in "live" mode
- The same plugin works identically in "simulation" mode
- Modes are isolated (sim state does not pollute live state)
"""
import asyncio
import pytest

from core.plugin_base import Fill, Order, Signal, StrategyPlugin, Tick
from core.circuit_breaker import CircuitBreaker
from core.thesis_guard import ThesisGuard
from core.kelly_sizer import kelly_size
from core.signature_check import run_self_check


# ── Concrete plugin — renamed to avoid pytest collection warning ──────────────

class _SamplePlugin(StrategyPlugin):
    """Minimal plugin that wires CircuitBreaker + ThesisGuard + KellySizer."""

    def __init__(self, mode="live"):
        super().__init__(mode=mode)
        self.circuit_breaker = CircuitBreaker(mode=mode)
        self.thesis_guard = ThesisGuard(mode=mode)
        self.orders_placed: list = []

    async def on_signal(self, signal: Signal):
        if self.circuit_breaker.is_blocked():
            return None
        size, fraction, cap = kelly_size(
            price=signal.price,
            bankroll=1000.0,
            mode=self.mode,
        )
        if size <= 0:
            return None
        order = Order(signal=signal, size_usdc=size, mode=self.mode)
        self.orders_placed.append(order)
        return order

    async def on_fill(self, fill: Fill) -> None:
        self.thesis_guard.register_position(
            fill.order_id, fill.order_id[:12], fill.filled_price
        )

    async def on_tick(self, tick: Tick) -> None:
        pass


def make_signal(price: float = 0.6) -> Signal:
    return Signal(
        market_id="mkt-test",
        token_id="tok-test",
        side="buy",
        price=price,
        size_usdc=10.0,
    )


# ── Test: plugin_with_safety_live ─────────────────────────────────────────────

def test_plugin_with_safety_live():
    plugin = _SamplePlugin(mode="live")
    plugin.circuit_breaker.reset("test_setup")
    assert plugin.is_live()
    assert plugin.circuit_breaker._mode == "live"
    assert plugin.thesis_guard._mode == "live"


def test_plugin_live_places_order_when_not_blocked():
    plugin = _SamplePlugin(mode="live")
    plugin.circuit_breaker.reset("test_setup")
    sig = make_signal(price=0.55)
    order = asyncio.run(plugin.on_signal(sig))
    assert order is not None
    assert order.mode == "live"
    assert order.size_usdc > 0
    assert len(plugin.orders_placed) == 1


def test_plugin_live_blocked_by_circuit_breaker():
    plugin = _SamplePlugin(mode="live")
    plugin.circuit_breaker.reset("test_setup")
    asyncio.run(plugin.circuit_breaker.update(daily_loss_usd=200.0, bankroll=1000.0))
    assert plugin.circuit_breaker.is_blocked()
    order = asyncio.run(plugin.on_signal(make_signal()))
    assert order is None
    plugin.circuit_breaker.reset("test_teardown")  # clean up disk state


# ── Test: plugin_with_safety_simulation ──────────────────────────────────────

def test_plugin_with_safety_simulation():
    plugin = _SamplePlugin(mode="simulation")
    assert plugin.is_simulation()
    assert plugin.circuit_breaker._mode == "simulation"
    assert plugin.thesis_guard._mode == "simulation"


def test_plugin_simulation_places_order():
    plugin = _SamplePlugin(mode="simulation")
    order = asyncio.run(plugin.on_signal(make_signal(price=0.6)))
    assert order is not None
    assert order.mode == "simulation"
    assert len(plugin.orders_placed) == 1


def test_plugin_simulation_cb_writes_sim_log():
    plugin = _SamplePlugin(mode="simulation")
    asyncio.run(plugin.circuit_breaker.update(daily_loss_usd=200.0, bankroll=1000.0))
    assert len(plugin.circuit_breaker._sim_log) > 0
    assert "SIM" in plugin.circuit_breaker._sim_log[0]


def test_plugin_simulation_thesis_guard_tracks_violations():
    plugin = _SamplePlugin(mode="simulation")
    plugin.thesis_guard.register_position("ord-sim-1", "wallet-sim", 0.6)
    v = plugin.thesis_guard.check_hard_stop("ord-sim-1", 0.6, 0.2)
    assert v is not None
    assert "SIM ThesisGuard" in plugin.thesis_guard._sim_log[0]


# ── Test: modes_are_isolated ──────────────────────────────────────────────────

def test_modes_are_isolated():
    live_plugin = _SamplePlugin(mode="live")
    sim_plugin = _SamplePlugin(mode="simulation")

    # Reset live CB to ensure no leftover disk state from other tests
    live_plugin.circuit_breaker.reset("isolation_test_setup")

    # Trigger CB on sim plugin only
    asyncio.run(sim_plugin.circuit_breaker.update(daily_loss_usd=200.0, bankroll=1000.0))
    assert sim_plugin.circuit_breaker.is_blocked()

    # Live plugin CB must be unaffected
    assert not live_plugin.circuit_breaker.is_blocked()

    # Orders placed on sim don't appear in live
    result = asyncio.run(sim_plugin.on_signal(make_signal()))  # blocked → None
    assert result is None
    assert len(live_plugin.orders_placed) == 0


def test_signature_check_sim_mode_writes_sim_log():
    from core.signature_check import _sim_log
    before = len(_sim_log)
    run_self_check(mode="simulation")
    assert len(_sim_log) > before
    assert "SIM" in _sim_log[-1]


def test_kelly_size_sim_mode_returns_valid_size():
    size, fraction, cap = kelly_size(price=0.5, bankroll=1000.0, mode="simulation")
    assert size > 0
    assert 0 <= fraction <= 1
