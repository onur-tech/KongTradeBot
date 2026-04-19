#!/usr/bin/env python3
"""
scripts/test_watchdog.py — Unit-Tests für watchdog.py
"""
import json
import os
import sys
import signal
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

# watchdog liegt im Root, nicht in utils/
import importlib.util
spec = importlib.util.spec_from_file_location(
    "watchdog", Path(__file__).parent.parent / "watchdog.py"
)
wd = importlib.util.load_from_spec = spec
import watchdog as wd


# ── Hilfsfunktionen ──────────────────────────────────────────────────────────

def _patch_globals(tmpdir: str, pid_alive: bool, hb_fresh: bool, hb_age: int = 60):
    """Patcht alle file-system Abhängigkeiten auf tmpdir."""
    state_file = Path(tmpdir) / "watchdog_state.json"
    return {
        "wd.LOCK_FILE":      patch.object(wd, "LOCK_FILE",      Path(tmpdir) / "bot.lock"),
        "wd.HEARTBEAT_FILE": patch.object(wd, "HEARTBEAT_FILE", Path(tmpdir) / "heartbeat.txt"),
        "wd.STATE_FILE":     patch.object(wd, "STATE_FILE",     state_file),
        "check_lock":        patch.object(wd, "check_lock_pid",  return_value=(12345, pid_alive)),
        "check_hb":          patch.object(wd, "check_heartbeat", return_value=(hb_fresh, hb_age)),
        "restart":           patch.object(wd, "restart_service", return_value=True),
        "telegram":          patch.object(wd, "send_telegram"),
        "graceful":          patch.object(wd, "graceful_shutdown", return_value=True),
        "cleanup":           patch.object(wd, "cleanup_stale_lock"),
    }


def _apply_patches(patches: dict):
    started = {}
    for name, p in patches.items():
        started[name] = p.start()
    return started


def _stop_patches(patches: dict):
    for p in patches.values():
        try:
            p.stop()
        except RuntimeError:
            pass


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_skip_restart_if_bot_alive_and_heartbeat_fresh():
    with tempfile.TemporaryDirectory() as tmpdir:
        patches = _patch_globals(tmpdir, pid_alive=True, hb_fresh=True, hb_age=30)
        mocks = _apply_patches(patches)
        try:
            result = wd.check()
            assert result == "ok", f"Erwartet 'ok', bekommen {result!r}"
            mocks["restart"].assert_not_called()
            mocks["graceful"].assert_not_called()
        finally:
            _stop_patches(patches)
    print("  ✅ test_skip_restart_if_bot_alive_and_heartbeat_fresh")


def test_restart_if_heartbeat_stale():
    with tempfile.TemporaryDirectory() as tmpdir:
        patches = _patch_globals(tmpdir, pid_alive=True, hb_fresh=False, hb_age=700)
        mocks = _apply_patches(patches)
        try:
            result = wd.check()
            assert result == "restarted", f"Erwartet 'restarted', bekommen {result!r}"
            mocks["graceful"].assert_called_once_with(12345)
            mocks["restart"].assert_called_once()
        finally:
            _stop_patches(patches)
    print("  ✅ test_restart_if_heartbeat_stale")


def test_cleanup_stale_lock_if_process_dead():
    with tempfile.TemporaryDirectory() as tmpdir:
        patches = _patch_globals(tmpdir, pid_alive=False, hb_fresh=False, hb_age=700)
        # check_lock_pid gibt zurück: PID existiert (stale lock) aber Prozess tot
        patches["check_lock"] = patch.object(wd, "check_lock_pid", return_value=(99999, False))
        mocks = _apply_patches(patches)
        try:
            result = wd.check()
            mocks["cleanup"].assert_called_once_with(99999)
            # Danach wird Restart versucht
            assert result in ("restarted", "rate_limited")
        finally:
            _stop_patches(patches)
    print("  ✅ test_cleanup_stale_lock_if_process_dead")


def test_rate_limit_blocks_restart_after_3():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = Path(tmpdir) / "watchdog_state.json"
        # 3 Restarts in letzter Stunde eingetragen
        now = time.time()
        state = {
            "restarts": [now - 1800, now - 900, now - 300],
            "rate_limit_alert_sent": False,
        }
        state_file.write_text(json.dumps(state))

        patches = _patch_globals(tmpdir, pid_alive=False, hb_fresh=False, hb_age=700)
        patches["wd.STATE_FILE"] = patch.object(wd, "STATE_FILE", state_file)
        mocks = _apply_patches(patches)
        try:
            result = wd.check()
            assert result == "rate_limited", f"Erwartet 'rate_limited', bekommen {result!r}"
            mocks["restart"].assert_not_called()
            mocks["telegram"].assert_called()  # Alert wurde gesendet
        finally:
            _stop_patches(patches)
    print("  ✅ test_rate_limit_blocks_restart_after_3")


def test_rate_limit_resets_after_1h_stability():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = Path(tmpdir) / "watchdog_state.json"
        # 3 Restarts, aber alle ÄLTER als 1h
        now = time.time()
        state = {
            "restarts": [now - 7200, now - 5400, now - 3700],  # alle > 3600s alt
            "rate_limit_alert_sent": False,
        }
        state_file.write_text(json.dumps(state))

        patches = _patch_globals(tmpdir, pid_alive=False, hb_fresh=False, hb_age=700)
        patches["wd.STATE_FILE"] = patch.object(wd, "STATE_FILE", state_file)
        mocks = _apply_patches(patches)
        try:
            result = wd.check()
            # Alte Restarts zählen nicht → Restart erlaubt
            assert result == "restarted", f"Erwartet 'restarted', bekommen {result!r}"
            mocks["restart"].assert_called_once()
        finally:
            _stop_patches(patches)
    print("  ✅ test_rate_limit_resets_after_1h_stability")


def test_graceful_shutdown_before_sigkill():
    """graceful_shutdown() sendet SIGTERM, wartet, dann SIGKILL falls nötig."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_pid = 99998

        # Simuliere: Prozess stirbt nach SIGTERM sofort
        call_count = {"n": 0}
        def fake_pid_exists(pid):
            call_count["n"] += 1
            return call_count["n"] <= 1  # erste Prüfung: lebt; zweite: tot

        with patch("watchdog.psutil.pid_exists", side_effect=fake_pid_exists), \
             patch("watchdog.os.kill") as mock_kill, \
             patch("watchdog.time.sleep"):  # sleep nicht wirklich warten
            # Erzeuge nicht DRY_RUN-Modus
            original_dry = wd.DRY_RUN
            wd.DRY_RUN = False
            try:
                result = wd.graceful_shutdown(fake_pid)
                # SIGTERM sollte gesendet worden sein
                mock_kill.assert_called_with(fake_pid, signal.SIGTERM)
                assert result is True
            finally:
                wd.DRY_RUN = original_dry
    print("  ✅ test_graceful_shutdown_before_sigkill")


# ── Runner ────────────────────────────────────────────────────────────────────

def run():
    tests = [
        test_skip_restart_if_bot_alive_and_heartbeat_fresh,
        test_restart_if_heartbeat_stale,
        test_cleanup_stale_lock_if_process_dead,
        test_rate_limit_blocks_restart_after_3,
        test_rate_limit_resets_after_1h_stability,
        test_graceful_shutdown_before_sigkill,
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
