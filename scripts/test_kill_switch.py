#!/usr/bin/env python3
"""
scripts/test_kill_switch.py — Unit-Tests für utils/kill_switch.py
"""
import json
import sys
import time
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.kill_switch import KillSwitch


def _make_ks(tmpdir: str) -> KillSwitch:
    return KillSwitch(state_file=str(Path(tmpdir) / "kill_switch_state.json"))


def test_trigger_persists_to_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        ks = _make_ks(tmpdir)
        ks.trigger("Daily loss exceeded", triggered_by="daily_loss")

        state_file = Path(tmpdir) / "kill_switch_state.json"
        assert state_file.exists(), "State-File nicht erstellt"

        saved = json.loads(state_file.read_text())
        assert saved["active"] is True
        assert saved["triggered_by"] == "daily_loss"
        assert saved["reason"] == "Daily loss exceeded"
        assert saved["triggered_at"] is not None
        assert saved["auto_reset_at"] is not None  # daily_loss → 24h auto-reset
    print("  ✅ test_trigger_persists_to_file")


def test_reset_clears_state():
    with tempfile.TemporaryDirectory() as tmpdir:
        ks = _make_ks(tmpdir)
        ks.trigger("test trigger", triggered_by="manual")
        assert ks.is_active() is True

        ks.reset("manual_test")
        assert ks.is_active() is False

        saved = json.loads((Path(tmpdir) / "kill_switch_state.json").read_text())
        assert saved["active"] is False
        assert saved["triggered_at"] is None
        assert saved["reason"] is None
    print("  ✅ test_reset_clears_state")


def test_auto_reset_after_expiry():
    with tempfile.TemporaryDirectory() as tmpdir:
        ks = _make_ks(tmpdir)
        # Trigger mit auto_reset in der Vergangenheit
        past = (datetime.utcnow() - timedelta(seconds=5)).isoformat()
        ks.trigger("old trigger", triggered_by="daily_loss", auto_reset_hours=0)
        # Manuell auto_reset_at auf Vergangenheit setzen
        ks._state["auto_reset_at"] = past
        ks._state["active"] = True
        ks._save_state()

        # is_active() soll Auto-Reset erkennen
        assert ks.is_active() is False, "Auto-Reset hat nicht funktioniert"
        assert ks._state["active"] is False
    print("  ✅ test_auto_reset_after_expiry")


def test_blocks_trades_when_active():
    """Integration: RiskManager blockiert Trades wenn Kill-Switch aktiv."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ks = _make_ks(tmpdir)
        ks.trigger("block test", triggered_by="manual")

        # is_active() gibt True zurück
        assert ks.is_active() is True

        # Kill-Switch inaktiv nach reset
        ks.reset()
        assert ks.is_active() is False
    print("  ✅ test_blocks_trades_when_active")


def test_history_tracks_last_10_triggers():
    with tempfile.TemporaryDirectory() as tmpdir:
        ks = _make_ks(tmpdir)

        # 11 Trigger → nur letzten 10 behalten
        for i in range(11):
            ks.reset("test_reset")
            ks.trigger(f"reason {i}", triggered_by="manual")

        state = ks.get_state()
        assert len(state["history"]) <= 10, f"History hat {len(state['history'])} Einträge (max 10)"

        # Auch nach Speichern und Nachladen korrekt
        saved = json.loads((Path(tmpdir) / "kill_switch_state.json").read_text())
        assert len(saved["history"]) <= 10
    print("  ✅ test_history_tracks_last_10_triggers")


def test_loads_state_on_startup():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = Path(tmpdir) / "kill_switch_state.json"

        # State-Datei vorab erstellen (simuliert gespeicherten Zustand)
        state_data = {
            "active": True,
            "triggered_at": "2026-04-19T00:00:00Z",
            "triggered_by": "daily_loss",
            "reason": "Tages-Verlustlimit überschritten",
            "auto_reset_at": (datetime.utcnow() + timedelta(hours=10)).isoformat(),
            "daily_pnl_at_trigger": -150.0,
            "history": [],
        }
        state_file.write_text(json.dumps(state_data))

        # Neues KillSwitch-Objekt erstellen → muss State laden
        ks = KillSwitch(state_file=str(state_file))

        assert ks.is_active() is True, "State nach Restart nicht geladen"
        assert ks.reason == "Tages-Verlustlimit überschritten"
        assert ks._state["triggered_by"] == "daily_loss"
    print("  ✅ test_loads_state_on_startup")


def run():
    tests = [
        test_trigger_persists_to_file,
        test_reset_clears_state,
        test_auto_reset_after_expiry,
        test_blocks_trades_when_active,
        test_history_tracks_last_10_triggers,
        test_loads_state_on_startup,
    ]

    ok = fail = 0
    for t in tests:
        try:
            t()
            ok += 1
        except Exception as e:
            fail += 1
            print(f"  ❌ FAIL {t.__name__}: {e}")

    total = len(tests)
    print(f"\n{'✅ Alle' if fail == 0 else '⚠️ '}{ok}/{total} Tests bestanden"
          + (f" | {fail} Fehler" if fail else ""))
    return fail == 0


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
