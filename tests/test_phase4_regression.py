"""
Phase 4 Regression Test — CopyTradingPlugin vs. CopyTradingStrategy (legacy).

Feeds identical TradeSignal sequences through both implementations and asserts
that skip/copy decisions and key output attributes match.

Both implementations are wired with the same risk stub (always-allow, fixed size).
"""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.risk_manager import RiskDecision
from core.strategy_config import AggregationConfig, StrategyConfig
from core.wallet_monitor import TradeSignal
from strategies.copy_trading import CopyTradingStrategy
from strategies.copy_trading_plugin import CopyOrder as PluginCopyOrder
from strategies.copy_trading_plugin import CopyTradingPlugin
from utils.config import Config


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

WALLET_A = "0x019782cab5d844f02bafb71f512758be78579f3c"  # majorexploiter (broad)
WALLET_B = "0xbddf61af533ff524d27154e589d2d7a81510c684"  # Countryside (sports)


def _cfg() -> Config:
    c = Config()
    c.target_wallets = [WALLET_A, WALLET_B]
    c.dry_run = True
    c.portfolio_budget_usd = 1000.0
    c.copy_size_multiplier = 0.05
    c.max_trade_size_usd = 50.0
    c.min_trade_size_usd = 1.0
    c.whale_exit_copy_enabled = False
    return c


def _risk_stub() -> MagicMock:
    rm = MagicMock()
    rm.evaluate.return_value = RiskDecision(allowed=True, reason="OK", adjusted_size_usdc=10.0)
    return rm


def _scfg_from_yaml() -> StrategyConfig:
    from pathlib import Path
    from core.strategy_config import load
    return load(Path(__file__).parent.parent / "config" / "strategies" / "copy_trading.yaml")


def _make_signal(
    wallet=WALLET_A,
    question="NBA finals game 7",
    outcome="Yes",
    token_id="tok_nba",
    size_usdc=200.0,
    tx_hash=None,
) -> TradeSignal:
    from datetime import datetime, timezone
    return TradeSignal(
        tx_hash=tx_hash or f"0x{abs(hash((wallet, question, outcome))):x}",
        source_wallet=wallet,
        market_id="mkt_test",
        token_id=token_id,
        side="BUY",
        price=0.55,
        size_usdc=size_usdc,
        outcome=outcome,
        market_question=question,
    )


def _make_legacy(risk=None) -> CopyTradingStrategy:
    cfg = _cfg()
    rm = risk or _risk_stub()
    s = CopyTradingStrategy(cfg, rm)
    return s


def _make_plugin(risk=None, scfg=None, monkeypatch_env=None) -> CopyTradingPlugin:
    cfg = _cfg()
    rm = risk or _risk_stub()
    sc = scfg or _scfg_from_yaml()
    # Override aggregation window to 0 for instant flush
    sc.aggregation = AggregationConfig(
        window_s=0,
        multi_signal_multipliers=sc.aggregation.multi_signal_multipliers,
        herd_fraction=sc.aggregation.herd_fraction,
        early_entry_multiplier=sc.aggregation.early_entry_multiplier,
        early_entry_volume_usd=sc.aggregation.early_entry_volume_usd,
    )
    p = CopyTradingPlugin(cfg, rm, mode="simulation", scfg=sc)
    return p


# ---------------------------------------------------------------------------
# 1. Single sports signal from WALLET_A (broad wallet) → both copy it
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_regression_sports_signal_broad_wallet(monkeypatch):
    monkeypatch.setenv("WALLET_WEIGHTS", "")
    monkeypatch.setenv("CRYPTO_DAILY_SINGLE_SIGNAL", "false")  # require 2 wallets

    # Legacy
    legacy = _make_legacy()
    legacy_orders: List = []
    legacy.on_copy_order = AsyncMock(side_effect=lambda o: legacy_orders.append(o))

    # Plugin
    plugin = _make_plugin()
    plugin_orders: List = []
    plugin.on_copy_order = AsyncMock(side_effect=lambda o: plugin_orders.append(o))

    sig_a = _make_signal(wallet=WALLET_A, question="NBA finals game 7", outcome="Yes", token_id="tok_nba")
    sig_b = _make_signal(wallet=WALLET_B, question="NBA finals game 7", outcome="Yes", token_id="tok_nba",
                         tx_hash="0xbbb")

    # Legacy: AGGREGATION_WINDOW_S is 60 by default — override by monkey-patching module constant
    import strategies.copy_trading as _ct_mod
    orig = _ct_mod.AGGREGATION_WINDOW_S
    _ct_mod.AGGREGATION_WINDOW_S = 0
    try:
        await legacy.handle_signal(sig_a)
        await legacy.handle_signal(sig_b)
        await asyncio.sleep(0.05)
    finally:
        _ct_mod.AGGREGATION_WINDOW_S = orig

    await plugin.handle_signal(sig_a)
    await plugin.handle_signal(sig_b)
    await asyncio.sleep(0.05)

    # Both should have produced exactly 1 order
    assert len(legacy_orders) == 1, f"Legacy produced {len(legacy_orders)} orders"
    assert len(plugin_orders) == 1, f"Plugin produced {len(plugin_orders)} orders"


# ---------------------------------------------------------------------------
# 2. Wallet category filter: sports wallet → skip crypto market
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_regression_category_filter_crypto_skip(monkeypatch):
    monkeypatch.setenv("WALLET_WEIGHTS", "")

    # WALLET_B is sports-only — a BTC question must be skipped

    legacy = _make_legacy()
    legacy_orders: List = []
    legacy.on_copy_order = AsyncMock(side_effect=lambda o: legacy_orders.append(o))

    plugin = _make_plugin()
    plugin_orders: List = []
    plugin.on_copy_order = AsyncMock(side_effect=lambda o: plugin_orders.append(o))

    sig = _make_signal(wallet=WALLET_B, question="Will Bitcoin reach $100k this month?", outcome="Yes")

    import strategies.copy_trading as _ct_mod
    orig = _ct_mod.AGGREGATION_WINDOW_S
    _ct_mod.AGGREGATION_WINDOW_S = 0
    try:
        await legacy.handle_signal(sig)
        await asyncio.sleep(0.05)
    finally:
        _ct_mod.AGGREGATION_WINDOW_S = orig

    await plugin.handle_signal(sig)
    await asyncio.sleep(0.05)

    assert len(legacy_orders) == 0, "Legacy should skip crypto for sports-only wallet"
    assert len(plugin_orders) == 0, "Plugin should skip crypto for sports-only wallet"


# ---------------------------------------------------------------------------
# 3. Risk rejection → both skip
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_regression_risk_rejected(monkeypatch):
    monkeypatch.setenv("WALLET_WEIGHTS", "")
    monkeypatch.setenv("CRYPTO_DAILY_SINGLE_SIGNAL", "true")

    risk = _risk_stub()
    risk.evaluate.return_value = RiskDecision(allowed=False, reason="DAILY_LOSS", adjusted_size_usdc=0.0)

    legacy = _make_legacy(risk=risk)
    legacy_orders: List = []
    legacy.on_copy_order = AsyncMock(side_effect=lambda o: legacy_orders.append(o))

    plugin = _make_plugin(risk=risk)
    plugin_orders: List = []
    plugin.on_copy_order = AsyncMock(side_effect=lambda o: plugin_orders.append(o))

    # Use crypto-daily so 1 wallet is enough (min_sigs=1)
    sig = _make_signal(wallet=WALLET_A, question="bitcoin-above 70k today", outcome="Yes", token_id="btc_tok")

    import strategies.copy_trading as _ct_mod
    orig = _ct_mod.AGGREGATION_WINDOW_S
    _ct_mod.AGGREGATION_WINDOW_S = 0
    try:
        await legacy.handle_signal(sig)
        await asyncio.sleep(0.05)
    finally:
        _ct_mod.AGGREGATION_WINDOW_S = orig

    await plugin.handle_signal(sig)
    await asyncio.sleep(0.05)

    assert len(legacy_orders) == 0
    assert len(plugin_orders) == 0


# ---------------------------------------------------------------------------
# 4. Win-rate decay → both skip
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_regression_win_rate_decay(monkeypatch):
    monkeypatch.setenv("WALLET_WEIGHTS", "")
    monkeypatch.setenv("CRYPTO_DAILY_SINGLE_SIGNAL", "true")

    legacy = _make_legacy()
    legacy_orders: List = []
    legacy.on_copy_order = AsyncMock(side_effect=lambda o: legacy_orders.append(o))

    plugin = _make_plugin()
    plugin_orders: List = []
    plugin.on_copy_order = AsyncMock(side_effect=lambda o: plugin_orders.append(o))

    # Force decay: 10 consecutive losses for WALLET_A
    for obj in (legacy, plugin):
        perf = obj.wallet_performance.get(WALLET_A)
        if perf:
            for _ in range(10):
                perf.record(-1.0)

    sig = _make_signal(wallet=WALLET_A, question="bitcoin-above 70k today", outcome="Yes", token_id="btc_tok")

    import strategies.copy_trading as _ct_mod
    orig = _ct_mod.AGGREGATION_WINDOW_S
    _ct_mod.AGGREGATION_WINDOW_S = 0
    try:
        await legacy.handle_signal(sig)
        await asyncio.sleep(0.05)
    finally:
        _ct_mod.AGGREGATION_WINDOW_S = orig

    await plugin.handle_signal(sig)
    await asyncio.sleep(0.05)

    assert len(legacy_orders) == 0, "Legacy should skip decaying wallet"
    assert len(plugin_orders) == 0, "Plugin should skip decaying wallet"


# ---------------------------------------------------------------------------
# 5. Stats structure compatibility
# ---------------------------------------------------------------------------

def test_regression_get_status_keys():
    """Both implementations must expose the same top-level stat keys."""
    legacy = _make_legacy()
    plugin = _make_plugin()

    legacy_status = legacy.get_status()
    plugin_status = plugin.get_status()

    shared_keys = {"signals_received", "orders_created", "orders_skipped", "wallets"}
    for key in shared_keys:
        assert key in legacy_status, f"Legacy missing key: {key}"
        assert key in plugin_status, f"Plugin missing key: {key}"


# ---------------------------------------------------------------------------
# 6. DRY_RUN flag propagated correctly
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_regression_dry_run_flag(monkeypatch):
    monkeypatch.setenv("WALLET_WEIGHTS", "")
    monkeypatch.setenv("CRYPTO_DAILY_SINGLE_SIGNAL", "true")

    plugin = _make_plugin()
    orders: List = []
    plugin.on_copy_order = AsyncMock(side_effect=lambda o: orders.append(o))

    sig = _make_signal(wallet=WALLET_A, question="bitcoin-above 70k today", outcome="Yes", token_id="btc_tok")
    await plugin.handle_signal(sig)
    await asyncio.sleep(0.05)

    assert len(orders) == 1
    assert orders[0].dry_run is True  # Config has dry_run=True
