"""Tests for strategies/copy_trading_plugin.py — CopyTradingPlugin."""
from __future__ import annotations

import asyncio
import json
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.plugin_base import Fill, Order, Signal, Tick
from core.risk_manager import RiskDecision
from core.strategy_config import AggregationConfig, StrategyConfig, load as load_cfg
from core.wallet_monitor import TradeSignal
from strategies.copy_trading_plugin import (
    CopyOrder,
    CopyTradingPlugin,
    WalletPerformance,
)
from utils.config import Config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WALLET_A = "0x" + "a" * 40
WALLET_B = "0x" + "b" * 40
WALLET_C = "0x" + "c" * 40


def _make_scfg(**overrides) -> StrategyConfig:
    agg = AggregationConfig(
        window_s=0,  # instant flush in tests
        multi_signal_multipliers={1: 1.0, 2: 1.5, 3: 2.0},
        herd_fraction=0.50,
        early_entry_multiplier=1.5,
        early_entry_volume_usd=10_000.0,
    )
    cfg = StrategyConfig(
        aggregation=agg,
        default_multiplier=1.0,
        wallet_multipliers={WALLET_A: 2.0, WALLET_B: 1.0},
        wallet_categories={WALLET_A: ["sports"], WALLET_B: ["crypto"]},
        wallet_names={WALLET_A: "WalletAlpha", WALLET_B: "WalletBeta"},
        category_keywords={
            "sports": ["nba", "football"],
            "crypto": ["bitcoin", "btc"],
        },
        crypto_daily_keywords=["bitcoin-above", "btc-daily"],
    )
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


def _make_config(wallets=None) -> Config:
    c = Config()
    c.target_wallets = wallets or [WALLET_A, WALLET_B]
    c.dry_run = True
    c.portfolio_budget_usd = 1000.0
    c.copy_size_multiplier = 0.05
    return c


def _make_risk(allowed=True, adjusted=10.0) -> MagicMock:
    rm = MagicMock()
    rm.evaluate.return_value = RiskDecision(
        allowed=allowed,
        reason="OK" if allowed else "BLOCKED",
        adjusted_size_usdc=adjusted,
    )
    return rm


def _make_signal(
    wallet=None,
    market_id="mkt1",
    token_id="tok1",
    side="BUY",
    price=0.55,
    size_usdc=100.0,
    outcome="Yes",
    question="NBA game result",
    tx_hash=None,
) -> TradeSignal:
    from datetime import datetime, timezone
    return TradeSignal(
        tx_hash=tx_hash or f"0x{hash(wallet or WALLET_A):x}",
        source_wallet=wallet or WALLET_A,
        market_id=market_id,
        token_id=token_id,
        side=side,
        price=price,
        size_usdc=size_usdc,
        outcome=outcome,
        market_question=question,
    )


def _make_plugin(wallets=None, allowed=True, adjusted=10.0) -> CopyTradingPlugin:
    cfg = _make_config(wallets)
    risk = _make_risk(allowed=allowed, adjusted=adjusted)
    scfg = _make_scfg()
    p = CopyTradingPlugin(config=cfg, risk=risk, mode="simulation", scfg=scfg)
    return p


# ---------------------------------------------------------------------------
# 1. Construction and ABC compliance
# ---------------------------------------------------------------------------

def test_plugin_is_strategy_plugin():
    from core.plugin_base import StrategyPlugin
    p = _make_plugin()
    assert isinstance(p, StrategyPlugin)


def test_plugin_mode_live():
    cfg = _make_config()
    risk = _make_risk()
    p = CopyTradingPlugin(config=cfg, risk=risk, mode="live", scfg=_make_scfg())
    assert p.is_live()
    assert not p.is_simulation()


def test_plugin_mode_simulation():
    p = _make_plugin()
    assert p.is_simulation()
    assert not p.is_live()


def test_invalid_mode_raises():
    with pytest.raises(ValueError):
        CopyTradingPlugin(config=_make_config(), risk=_make_risk(), mode="invalid")


# ---------------------------------------------------------------------------
# 2. Wallet helpers (use YAML config, not hardcoded dicts)
# ---------------------------------------------------------------------------

def test_wallet_name_known():
    p = _make_plugin()
    assert p._wallet_name(WALLET_A) == "WalletAlpha"


def test_wallet_name_unknown_truncated():
    p = _make_plugin()
    unknown = "0x" + "f" * 40
    name = p._wallet_name(unknown)
    assert name.endswith("...")
    assert len(name) < 20


def test_wallet_multiplier_known():
    p = _make_plugin()
    assert p._wallet_multiplier(WALLET_A) == pytest.approx(2.0)


def test_wallet_multiplier_unknown_uses_default():
    p = _make_plugin()
    unknown = "0x" + "f" * 40
    assert p._wallet_multiplier(unknown) == pytest.approx(1.0)  # default_multiplier=1.0 in test scfg


# ---------------------------------------------------------------------------
# 3. Category detection and wallet filter
# ---------------------------------------------------------------------------

def test_detect_category_sports():
    p = _make_plugin()
    assert p._detect_category("nba game tonight") == "sports"


def test_detect_category_crypto():
    p = _make_plugin()
    assert p._detect_category("will bitcoin rise today") == "crypto"


def test_detect_category_unknown():
    p = _make_plugin()
    assert p._detect_category("random unrelated market") == "other"


def test_should_copy_allrounder_wallet():
    """Wallet not in categories → Allrounder, always copy."""
    p = _make_plugin()
    ok, reason = p._should_copy(WALLET_C, "anything goes")
    assert ok
    assert "Allrounder" in reason


def test_should_copy_sports_wallet_sports_market():
    p = _make_plugin()
    ok, _ = p._should_copy(WALLET_A, "NBA finals game 7")
    assert ok


def test_should_copy_sports_wallet_crypto_market():
    p = _make_plugin()
    ok, reason = p._should_copy(WALLET_A, "will bitcoin reach 100k")
    assert not ok
    assert "sports" in reason.lower() or "kategorie" in reason.lower()


# ---------------------------------------------------------------------------
# 4. Crypto-daily detection
# ---------------------------------------------------------------------------

def test_is_crypto_daily_slug():
    p = _make_plugin()
    sig = _make_signal(question="Will BTC rise today")
    sig_with_slug = TradeSignal(
        tx_hash=sig.tx_hash,
        source_wallet=sig.source_wallet,
        market_id=sig.market_id,
        token_id=sig.token_id,
        side=sig.side,
        price=sig.price,
        size_usdc=sig.size_usdc,
        outcome=sig.outcome,
        market_question="bitcoin-above 70k today",
    )
    assert p._is_crypto_daily(sig_with_slug)


def test_is_crypto_daily_not_matched():
    p = _make_plugin()
    sig = _make_signal(question="NBA game result")
    assert not p._is_crypto_daily(sig)


# ---------------------------------------------------------------------------
# 5. WalletPerformance
# ---------------------------------------------------------------------------

def test_wallet_performance_decay_triggers_at_45pct():
    wp = WalletPerformance(wallet_address=WALLET_A)
    for _ in range(10):
        wp.record(-1.0)  # 0% recent win rate
    assert wp.is_decaying


def test_wallet_performance_no_decay_below_10_trades():
    wp = WalletPerformance(wallet_address=WALLET_A)
    for _ in range(9):
        wp.record(-1.0)
    assert not wp.is_decaying


def test_wallet_performance_trend_declining():
    wp = WalletPerformance(wallet_address=WALLET_A)
    # 20 total trades, 15 wins (75%)
    for _ in range(15):
        wp.record(1.0)
    for _ in range(5):
        wp.record(-1.0)
    # Now 10 more recent trades, all losses → recent_win_rate = 0%
    for _ in range(10):
        wp.record(-1.0)
    assert wp.is_trend_declining
    assert wp.win_rate > 0.0
    assert wp.recent_win_rate < wp.win_rate - 0.10


def test_wallet_performance_record_updates_counters():
    wp = WalletPerformance(wallet_address=WALLET_A)
    wp.record(5.0)
    wp.record(-3.0)
    assert wp.trades_total == 2
    assert wp.trades_won == 1
    assert wp.trades_lost == 1
    assert wp.total_pnl_usd == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# 6. handle_signal → order dispatched via callback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_signal_creates_order(monkeypatch):
    monkeypatch.setenv("CRYPTO_DAILY_SINGLE_SIGNAL", "true")
    # WALLET_C has no category restriction (Allrounder); crypto-daily → min_sigs=1
    p = _make_plugin(wallets=[WALLET_C])
    orders: List[CopyOrder] = []
    p.on_copy_order = AsyncMock(side_effect=lambda o: orders.append(o))

    sig = _make_signal(wallet=WALLET_C, question="bitcoin-above 70k today",
                       token_id="btc_tok", outcome="Yes")
    await p.handle_signal(sig)
    await asyncio.sleep(0.01)  # flush aggregation (window_s=0)

    assert len(orders) == 1
    assert orders[0].dry_run is True
    assert orders[0].size_usdc == pytest.approx(10.0)


@pytest.mark.asyncio
async def test_handle_signal_skips_risk_rejected():
    p = _make_plugin(allowed=False)
    orders: List[CopyOrder] = []
    p.on_copy_order = AsyncMock(side_effect=lambda o: orders.append(o))

    sig = _make_signal(wallet=WALLET_A, question="NBA game result")
    await p.handle_signal(sig)
    await asyncio.sleep(0.01)

    assert len(orders) == 0
    assert p.stats["orders_skipped"] >= 1


@pytest.mark.asyncio
async def test_handle_signal_skips_wrong_category():
    """WALLET_A is sports-only; sending a crypto signal must be skipped."""
    p = _make_plugin()
    orders: List[CopyOrder] = []
    p.on_copy_order = AsyncMock(side_effect=lambda o: orders.append(o))

    sig = _make_signal(wallet=WALLET_A, question="will bitcoin hit 100k")
    await p.handle_signal(sig)
    await asyncio.sleep(0.01)

    assert len(orders) == 0


@pytest.mark.asyncio
async def test_handle_signal_multi_signal_boost():
    """Two wallets on same token → 1.5x multiplier applied."""
    cfg = _make_config(wallets=[WALLET_A, WALLET_B, WALLET_C])
    risk = _make_risk(allowed=True, adjusted=15.0)
    scfg = _make_scfg(
        wallet_categories={},  # all allrounders for this test
    )
    p = CopyTradingPlugin(config=cfg, risk=risk, mode="simulation", scfg=scfg)
    orders: List[CopyOrder] = []
    p.on_copy_order = AsyncMock(side_effect=lambda o: orders.append(o))

    sig_a = _make_signal(wallet=WALLET_A, question="NBA game result", tx_hash="0xaaa")
    sig_b = _make_signal(wallet=WALLET_B, question="NBA game result", tx_hash="0xbbb",
                         token_id=sig_a.token_id, outcome=sig_a.outcome)

    await p.handle_signal(sig_a)
    await p.handle_signal(sig_b)
    await asyncio.sleep(0.01)

    assert len(orders) == 1
    assert p.stats["multi_signals"] == 1


@pytest.mark.asyncio
async def test_handle_signal_no_duplicate_from_same_wallet(monkeypatch):
    monkeypatch.setenv("CRYPTO_DAILY_SINGLE_SIGNAL", "true")
    # WALLET_C is an Allrounder; crypto-daily → min_sigs=1
    p = _make_plugin(wallets=[WALLET_C])
    orders: List[CopyOrder] = []
    p.on_copy_order = AsyncMock(side_effect=lambda o: orders.append(o))

    sig = _make_signal(wallet=WALLET_C, question="bitcoin-above 70k today",
                       token_id="btc_tok", outcome="Yes")
    await p.handle_signal(sig)
    await p.handle_signal(sig)  # same wallet + same key → deduplicated
    await asyncio.sleep(0.01)

    assert len(orders) == 1  # only one order dispatched


# ---------------------------------------------------------------------------
# 7. on_signal (ABC entry point)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_on_signal_routes_to_handle_signal():
    p = _make_plugin()
    orders: List[CopyOrder] = []
    p.on_copy_order = AsyncMock(side_effect=lambda o: orders.append(o))

    sig = Signal(
        market_id="mkt1",
        token_id="tok1",
        side="BUY",
        price=0.55,
        size_usdc=100.0,
        source_wallet=WALLET_A,
        tx_hash="0xabc",
    )
    # Patch _should_copy to allow (default category filter for on_signal input)
    with patch.object(p, "_should_copy", return_value=(True, "Allrounder")):
        result = await p.on_signal(sig)

    await asyncio.sleep(0.01)
    assert result is None  # always returns None (dispatches via callback)


# ---------------------------------------------------------------------------
# 8. get_status
# ---------------------------------------------------------------------------

def test_get_status_structure():
    p = _make_plugin()
    status = p.get_status()
    assert status["strategy"] == "copy_trading_plugin"
    assert "signals_received" in status
    assert "orders_created" in status
    assert "wallets" in status


# ---------------------------------------------------------------------------
# 9. Integration with production YAML
# ---------------------------------------------------------------------------

def test_plugin_with_production_yaml(monkeypatch):
    # Clear WALLET_WEIGHTS so env overrides don't interfere with YAML values
    monkeypatch.setenv("WALLET_WEIGHTS", "")
    prod_path = Path(__file__).parent.parent / "config" / "strategies" / "copy_trading.yaml"
    scfg = load_cfg(prod_path)
    cfg = _make_config()
    risk = _make_risk()
    p = CopyTradingPlugin(config=cfg, risk=risk, mode="simulation", scfg=scfg)
    assert p._wallet_multiplier("0xbddf61af533ff524d27154e589d2d7a81510c684") == pytest.approx(3.0)
    assert p._wallet_name("0xbddf61af533ff524d27154e589d2d7a81510c684") == "Countryside"


# ---------------------------------------------------------------------------
# 10. Phase 5A: Signal-Scoring, Decay, Category-WR integration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_phase5a_scoring_enabled_by_default(monkeypatch):
    """SIGNAL_SCORING_ENABLED=true → scoring layer is active."""
    monkeypatch.setenv("SIGNAL_SCORING_ENABLED", "true")
    p = _make_plugin(wallets=[WALLET_C])
    assert p._scoring_enabled is True


@pytest.mark.asyncio
async def test_phase5a_scoring_disabled_via_env(monkeypatch):
    """SIGNAL_SCORING_ENABLED=false → scoring layer inactive."""
    monkeypatch.setenv("SIGNAL_SCORING_ENABLED", "false")
    p = _make_plugin(wallets=[WALLET_C])
    assert p._scoring_enabled is False


@pytest.mark.asyncio
async def test_phase5a_category_wr_skip(monkeypatch):
    """Category-WR check: wallet with poor WR in detected category → signal skipped."""
    monkeypatch.setenv("CRYPTO_DAILY_SINGLE_SIGNAL", "true")
    monkeypatch.setenv("SIGNAL_SCORING_ENABLED", "true")

    p = _make_plugin(wallets=[WALLET_C])
    orders: List[CopyOrder] = []
    p.on_copy_order = AsyncMock(side_effect=lambda o: orders.append(o))

    # Mock category tracker to reject
    from unittest.mock import MagicMock
    p._cat_tracker.should_accept_signal = MagicMock(return_value=False)

    sig = _make_signal(wallet=WALLET_C, question="bitcoin-above 70k today",
                       token_id="btc_tok", outcome="Yes")
    await p.handle_signal(sig)
    await asyncio.sleep(0.01)

    assert len(orders) == 0
    assert p.stats["orders_skipped"] >= 1


@pytest.mark.asyncio
async def test_phase5a_decay_multiplier_applied(monkeypatch):
    """Decay monitor adjusting wallet_mult is reflected in order path (no crash)."""
    monkeypatch.setenv("CRYPTO_DAILY_SINGLE_SIGNAL", "true")
    monkeypatch.setenv("SIGNAL_SCORING_ENABLED", "true")

    p = _make_plugin(wallets=[WALLET_C])
    orders: List[CopyOrder] = []
    p.on_copy_order = AsyncMock(side_effect=lambda o: orders.append(o))

    # Mock decay to return hard downgrade
    from unittest.mock import MagicMock
    from core.wallet_decay import WalletDecayDecision
    p._decay_monitor.evaluate = MagicMock(
        return_value=WalletDecayDecision(WALLET_C, 1.0, 0.2, "hard_downgrade_roi_below_minus20", {})
    )

    sig = _make_signal(wallet=WALLET_C, question="bitcoin-above 70k today",
                       token_id="btc_tok", outcome="Yes")
    await p.handle_signal(sig)
    await asyncio.sleep(0.01)

    # Order still created (decay reduces size but doesn't block)
    assert len(orders) == 1
    # wallet_multiplier on the order should reflect the decayed value (0.2)
    assert orders[0].wallet_multiplier == pytest.approx(0.2)


@pytest.mark.asyncio
async def test_phase5a_scoring_disabled_no_decay_applied(monkeypatch):
    """When scoring disabled, decay monitor is not called."""
    monkeypatch.setenv("CRYPTO_DAILY_SINGLE_SIGNAL", "true")
    monkeypatch.setenv("SIGNAL_SCORING_ENABLED", "false")

    p = _make_plugin(wallets=[WALLET_C])
    orders: List[CopyOrder] = []
    p.on_copy_order = AsyncMock(side_effect=lambda o: orders.append(o))

    from unittest.mock import MagicMock
    p._decay_monitor.evaluate = MagicMock()

    sig = _make_signal(wallet=WALLET_C, question="bitcoin-above 70k today",
                       token_id="btc_tok", outcome="Yes")
    await p.handle_signal(sig)
    await asyncio.sleep(0.01)

    # Decay monitor should NOT have been called
    p._decay_monitor.evaluate.assert_not_called()
    assert len(orders) == 1
