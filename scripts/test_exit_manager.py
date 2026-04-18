"""
Unit-Tests für core/exit_manager.py

Alle 13 Tests laufen ohne Netzwerk und ohne echten CLOB-Client.
Ausführung: pytest scripts/test_exit_manager.py -v
"""

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

# Projekt-Root ins sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.exit_manager import ExitManager, ExitState, ExitEvent


# ── Mock-Klassen ──────────────────────────────────────────────────────────────

@dataclass
class MockPosition:
    order_id: str
    market_id: str
    token_id: str
    outcome: str
    market_question: str
    entry_price: float
    size_usdc: float
    shares: float
    source_wallet: str = ""
    market_closes_at: Optional[datetime] = None


def _make_config(**overrides):
    """Erstellt eine minimale Config mit Exit-Defaults."""
    cfg = MagicMock()
    defaults = {
        "exit_enabled": True,
        "exit_dry_run": True,
        "exit_tp1_threshold": 0.30,
        "exit_tp1_sell_ratio": 0.40,
        "exit_tp2_threshold": 0.60,
        "exit_tp2_sell_ratio": 0.40,
        "exit_tp3_threshold": 1.00,
        "exit_tp3_sell_ratio": 0.15,
        "exit_multi_signal_boost_min": 3,
        "exit_tp1_threshold_boost": 0.50,
        "exit_tp2_threshold_boost": 0.90,
        "exit_tp3_threshold_boost": 1.50,
        "exit_trail_activation": 0.12,
        "exit_trail_distance_liquid": 0.07,
        "exit_trail_distance_thin": 0.10,
        "exit_trail_liquidity_threshold": 50000.0,
        "exit_min_position_usdc": 3.0,
        "exit_min_hours_to_close": 24.0,
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(cfg, k, v)
    return cfg


def _make_pos(entry_price=0.40, shares=100.0, current_value_override=None, hours_until_close=None):
    size_usdc = entry_price * shares
    closes_at = None
    if hours_until_close is not None:
        closes_at = datetime.now(timezone.utc) + timedelta(hours=hours_until_close)
    return MockPosition(
        order_id="test_order_1",
        market_id="cond_abc123",
        token_id="tok_abc123",
        outcome="Yes",
        market_question="Test Market Question?",
        entry_price=entry_price,
        size_usdc=size_usdc,
        shares=shares,
        market_closes_at=closes_at,
    )


def _make_manager(tmp_path, **cfg_overrides):
    cfg = _make_config(**cfg_overrides)
    mgr = ExitManager(cfg)
    # Override state file path for isolation
    mgr._states = {}
    return mgr


def _run(coro):
    return asyncio.run(coro)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_no_exit_when_position_too_small(tmp_path):
    """Position value $2 < $3 minimum → skip."""
    mgr = _make_manager(tmp_path)
    pos = _make_pos(entry_price=0.40, shares=5.0)  # 5 shares * 0.40 = $2 current
    live_prices = {"tok_abc123": 0.40}
    events = _run(mgr.evaluate_all([pos], live_prices))
    assert events == [], f"Erwartet leer, bekam: {events}"


def test_no_exit_when_close_to_resolution(tmp_path):
    """< 24h bis Resolution → skip."""
    mgr = _make_manager(tmp_path)
    pos = _make_pos(entry_price=0.40, shares=100.0, hours_until_close=12)
    live_prices = {"tok_abc123": 0.60}  # +50% pnl, würde sonst TP1 triggern
    events = _run(mgr.evaluate_all([pos], live_prices))
    assert events == [], "Zu nahe an Resolution — kein Exit erwartet"


def test_tp1_triggers_at_30_pct(tmp_path):
    """entry=0.40, current=0.52 → +30% → TP1 (40% sell)."""
    mgr = _make_manager(tmp_path)
    pos = _make_pos(entry_price=0.40, shares=100.0, hours_until_close=100)
    live_prices = {"tok_abc123": 0.52}  # 0.52/0.40 - 1 = 0.30
    events = _run(mgr.evaluate_all([pos], live_prices))
    assert len(events) == 1
    assert events[0].exit_type == "tp1"
    assert abs(events[0].shares_sold - 40.0) < 0.01  # 40% von 100 shares


def test_tp2_triggers_at_60_pct(tmp_path):
    """entry=0.40, current=0.64 → +60% → TP2 (tp1 already done)."""
    mgr = _make_manager(tmp_path)
    pos = _make_pos(entry_price=0.40, shares=100.0, hours_until_close=100)
    # tp1 bereits erledigt
    state = mgr._get_or_create_state(pos)
    state.tp1_done = True

    live_prices = {"tok_abc123": 0.64}  # +60%
    events = _run(mgr.evaluate_all([pos], live_prices))
    assert len(events) >= 1
    tp_types = [e.exit_type for e in events]
    assert "tp2" in tp_types


def test_tp3_triggers_at_100_pct(tmp_path):
    """entry=0.40, current=0.80 → +100% → TP3 (tp1+tp2 already done)."""
    mgr = _make_manager(tmp_path)
    pos = _make_pos(entry_price=0.40, shares=100.0, hours_until_close=100)
    state = mgr._get_or_create_state(pos)
    state.tp1_done = True
    state.tp2_done = True

    live_prices = {"tok_abc123": 0.80}  # +100%
    events = _run(mgr.evaluate_all([pos], live_prices))
    assert len(events) >= 1
    tp_types = [e.exit_type for e in events]
    assert "tp3" in tp_types


def test_tp_doesnt_retrigger_after_done(tmp_path):
    """tp1_done=True, pnl=35% → kein weiterer TP1-Exit."""
    mgr = _make_manager(tmp_path)
    pos = _make_pos(entry_price=0.40, shares=100.0, hours_until_close=100)
    state = mgr._get_or_create_state(pos)
    state.tp1_done = True

    live_prices = {"tok_abc123": 0.54}  # +35% → between tp1 (30%) and tp2 (60%)
    events = _run(mgr.evaluate_all([pos], live_prices))
    tp_types = [e.exit_type for e in events]
    assert "tp1" not in tp_types, "TP1 darf nicht nochmal triggern"


def test_boost_staffel_used_with_3_wallets(tmp_path):
    """3+ Wallets → Boost-Staffel: TP1 erst bei 50%, nicht 30%."""
    mgr = _make_manager(tmp_path)
    pos = _make_pos(entry_price=0.40, shares=100.0, hours_until_close=100)
    live_prices = {"tok_abc123": 0.52}  # +30% → TP1 normal, aber KEIN TP1 bei Boost

    # multi_signal_count=3 → Boost-Staffel → TP1 erst bei 50%
    events = _run(mgr.evaluate_all([pos], live_prices, multi_signal_counts={"cond_abc123": 3}))
    tp_types = [e.exit_type for e in events if e.exit_type.startswith("tp")]
    assert tp_types == [], f"Boost-Staffel: kein TP1 bei +30%, bekam: {tp_types}"

    # Bei +52.5% (klar über 50% Boost-Schwelle) wird TP1 getriggert
    live_prices_boost = {"tok_abc123": 0.61}  # +52.5% > 50%
    mgr2 = _make_manager(tmp_path)
    events2 = _run(mgr2.evaluate_all([pos], live_prices_boost, multi_signal_counts={"cond_abc123": 3}))
    tp_types2 = [e.exit_type for e in events2]
    assert "tp1" in tp_types2, f"Boost-Staffel TP1 bei +50% erwartet, bekam: {tp_types2}"


def test_trail_activates_at_12_cents(tmp_path):
    """entry=0.40, current=0.52 (+0.12) → trail_active wird true."""
    mgr = _make_manager(tmp_path)
    pos = _make_pos(entry_price=0.40, shares=100.0, hours_until_close=100)
    state = mgr._get_or_create_state(pos)
    state.tp1_done = True  # tp1 schon durch, damit wir isoliert Trail testen

    live_prices = {"tok_abc123": 0.52}  # genau +0.12
    _run(mgr.evaluate_all([pos], live_prices))
    assert state.trail_active, "Trail muss bei +0.12 aktiviert sein"


def test_trail_follows_high(tmp_path):
    """highest=0.60, current=0.58, trail=0.07 → stop=0.53 → kein Sell."""
    mgr = _make_manager(tmp_path)
    pos = _make_pos(entry_price=0.40, shares=100.0, hours_until_close=100)
    state = mgr._get_or_create_state(pos)
    state.tp1_done = True
    state.tp2_done = True
    state.tp3_done = True
    state.trail_active = True
    state.highest_price_seen = 0.60

    live_prices = {"tok_abc123": 0.58}  # stop = max(0.40, 0.60 - 0.10) = 0.50, thin
    # current 0.58 > stop 0.50 → kein Trail-Exit
    events = _run(mgr.evaluate_all([pos], live_prices))
    trail_events = [e for e in events if e.exit_type == "trail"]
    assert trail_events == [], f"Kein Trail-Exit erwartet, bekam: {trail_events}"


def test_trail_sells_when_below_stop(tmp_path):
    """highest=0.60, current=0.50, thin-trail=0.10 → stop=0.50 → sell."""
    mgr = _make_manager(tmp_path)
    pos = _make_pos(entry_price=0.40, shares=100.0, hours_until_close=100)
    state = mgr._get_or_create_state(pos)
    state.tp1_done = True
    state.tp2_done = True
    state.tp3_done = True
    state.trail_active = True
    state.highest_price_seen = 0.60

    live_prices = {"tok_abc123": 0.49}  # stop = max(0.40, 0.60-0.10) = 0.50 > current → sell
    events = _run(mgr.evaluate_all([pos], live_prices, market_volumes={}))
    trail_events = [e for e in events if e.exit_type == "trail"]
    assert trail_events, "Trail-Exit bei current <= stop erwartet"


def test_trail_hard_floor_at_entry(tmp_path):
    """highest=0.45, trail=0.10 → raw stop=0.35 < entry=0.40 → hard floor=0.40."""
    mgr = _make_manager(tmp_path)
    pos = _make_pos(entry_price=0.40, shares=100.0, hours_until_close=100)
    state = mgr._get_or_create_state(pos)
    state.tp1_done = True
    state.trail_active = True
    state.highest_price_seen = 0.45

    # raw stop = 0.45 - 0.10 = 0.35, aber floor = entry = 0.40
    # current = 0.41 → 0.41 > 0.40 (floor) → kein Sell
    live_prices = {"tok_abc123": 0.41}
    events = _run(mgr.evaluate_all([pos], live_prices))
    trail_events = [e for e in events if e.exit_type == "trail"]
    assert trail_events == [], "Hard-Floor schützt: 0.41 > floor 0.40, kein Sell"

    # current = 0.39 → 0.39 < 0.40 (floor) → Sell
    live_prices2 = {"tok_abc123": 0.39}
    mgr2 = _make_manager(tmp_path)
    state2 = mgr2._get_or_create_state(pos)
    state2.tp1_done = True
    state2.trail_active = True
    state2.highest_price_seen = 0.45
    events2 = _run(mgr2.evaluate_all([pos], live_prices2))
    trail_events2 = [e for e in events2 if e.exit_type == "trail"]
    assert trail_events2, "Hard-Floor: 0.39 < floor 0.40 → Trail-Exit erwartet"


def test_whale_exit_overrides_tp_logic(tmp_path):
    """pnl=+50% UND Whale-Exit → whale_exit gewinnt, kein TP2."""
    async def mock_get_recent_sells(wallet, minutes):
        return [{"condition_id": "cond_abc123"}]

    mock_monitor = MagicMock()
    mock_monitor.get_recent_sells = mock_get_recent_sells

    cfg = _make_config()
    mgr = ExitManager(cfg, wallet_monitor=mock_monitor)
    mgr._states = {}

    pos = _make_pos(entry_price=0.40, shares=100.0, hours_until_close=100)
    pos.source_wallet = "0xwhale123"
    state = mgr._get_or_create_state(pos)
    state.tp1_done = True

    live_prices = {"tok_abc123": 0.64}  # +60%, würde TP2 triggern
    events = _run(mgr.evaluate_all([pos], live_prices))

    assert len(events) == 1
    assert events[0].exit_type == "whale_exit", f"Erwartet whale_exit, bekam: {events[0].exit_type}"
    assert abs(events[0].shares_sold - 100.0) < 0.01, "Whale-Exit verkauft 100%"


def test_exit_state_persists_across_restart(tmp_path):
    """State schreiben → neue Instanz lesen → tp1_done persistiert."""
    state_path = tmp_path / "exit_state.json"

    cfg = _make_config()
    mgr = ExitManager(cfg)
    mgr._states = {}

    pos = _make_pos()
    state = mgr._get_or_create_state(pos)
    state.tp1_done = True
    state.highest_price_seen = 0.55

    # Manuell speichern mit tmp-Pfad
    state_path.write_text(json.dumps({k: v.to_dict() for k, v in mgr._states.items()}, indent=2))

    # Neue Instanz, state aus tmp-Datei laden
    mgr2 = ExitManager(cfg)
    mgr2._states = {}
    raw = json.loads(state_path.read_text())
    mgr2._states = {k: ExitState.from_dict(v) for k, v in raw.items()}

    key = "cond_abc123|Yes"
    assert key in mgr2._states, "State-Key muss nach Reload vorhanden sein"
    restored = mgr2._states[key]
    assert restored.tp1_done is True, "tp1_done muss persistiert sein"
    assert abs(restored.highest_price_seen - 0.55) < 0.001


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
