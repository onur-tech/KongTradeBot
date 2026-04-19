#!/usr/bin/env python3
"""
scripts/test_error_handler.py — Unit-Tests für utils/error_handler.py
"""
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

import utils.error_handler as eh


def _reset_state():
    """Zurücksetzen zwischen Tests."""
    eh._error_rate_limit.clear()
    eh._telegram_send = None


# ── Hilfsfunktion ─────────────────────────────────────────────────────────────

def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_handle_error_logs_to_file():
    _reset_state()
    with tempfile.TemporaryDirectory() as tmpdir:
        eh.DATA_DIR   = Path(tmpdir)
        eh.ERROR_LOG  = Path(tmpdir) / "error_log.jsonl"
        eh.ERROR_STATS = Path(tmpdir) / "error_stats.json"

        err = ValueError("test message")
        run(eh.handle_error(err, context="test_context", severity="ERROR", telegram_alert=False))

        assert eh.ERROR_LOG.exists(), "error_log.jsonl wurde nicht erstellt"
        line = eh.ERROR_LOG.read_text().strip()
        entry = json.loads(line)
        assert entry["error_type"] == "ValueError"
        assert entry["error_message"] == "test message"
        assert entry["context"] == "test_context"
        assert entry["severity"] == "ERROR"
        assert "timestamp" in entry
        assert "stack_trace" in entry
    print("  ✅ test_handle_error_logs_to_file")


def test_handle_error_sends_telegram_alert():
    _reset_state()
    with tempfile.TemporaryDirectory() as tmpdir:
        eh.DATA_DIR   = Path(tmpdir)
        eh.ERROR_LOG  = Path(tmpdir) / "error_log.jsonl"
        eh.ERROR_STATS = Path(tmpdir) / "error_stats.json"

        sent = []
        async def fake_send(msg): sent.append(msg)

        eh.set_telegram_sender(fake_send)
        err = RuntimeError("boom")
        run(eh.handle_error(err, context="ctx", severity="WARNING", telegram_alert=True))

        assert len(sent) == 1, f"Erwartet 1 Alert, bekommen {len(sent)}"
        assert "WARNING" in sent[0]
        assert "RuntimeError" in sent[0]
    print("  ✅ test_handle_error_sends_telegram_alert")


def test_handle_error_rate_limits():
    _reset_state()
    with tempfile.TemporaryDirectory() as tmpdir:
        eh.DATA_DIR   = Path(tmpdir)
        eh.ERROR_LOG  = Path(tmpdir) / "error_log.jsonl"
        eh.ERROR_STATS = Path(tmpdir) / "error_stats.json"

        sent = []
        async def fake_send(msg): sent.append(msg)

        eh.set_telegram_sender(fake_send)
        err = RuntimeError("repeated")

        # Erster Call → Alert
        run(eh.handle_error(err, context="ctx", severity="WARNING", telegram_alert=True))
        # Zweiter Call direkt danach → kein zweiter Alert (rate limit)
        run(eh.handle_error(err, context="ctx", severity="WARNING", telegram_alert=True))

        assert len(sent) == 1, f"Rate-Limit versagt: {len(sent)} Alerts statt 1"
    print("  ✅ test_handle_error_rate_limits")


def test_handle_error_reraise():
    _reset_state()
    with tempfile.TemporaryDirectory() as tmpdir:
        eh.DATA_DIR   = Path(tmpdir)
        eh.ERROR_LOG  = Path(tmpdir) / "error_log.jsonl"
        eh.ERROR_STATS = Path(tmpdir) / "error_stats.json"

        err = KeyError("missing_key")
        raised = False
        try:
            run(eh.handle_error(err, context="ctx", severity="ERROR",
                                telegram_alert=False, reraise=True))
        except KeyError:
            raised = True

        assert raised, "reraise=True hat Exception nicht weitergereicht"
    print("  ✅ test_handle_error_reraise")


def test_safe_call_transparent_catches_and_logs():
    _reset_state()
    with tempfile.TemporaryDirectory() as tmpdir:
        eh.DATA_DIR   = Path(tmpdir)
        eh.ERROR_LOG  = Path(tmpdir) / "error_log.jsonl"
        eh.ERROR_STATS = Path(tmpdir) / "error_stats.json"

        @eh.safe_call_transparent("test_fn", "WARNING")
        async def broken_fn(x):
            raise TypeError(f"bad type {x}")

        run(broken_fn("hello"))

        assert eh.ERROR_LOG.exists(), "error_log.jsonl nicht erstellt"
        entry = json.loads(eh.ERROR_LOG.read_text().strip())
        assert entry["error_type"] == "TypeError"
        assert "test_fn" in entry["context"]
    print("  ✅ test_safe_call_transparent_catches_and_logs")


def test_safe_call_transparent_returns_none_on_error():
    _reset_state()
    with tempfile.TemporaryDirectory() as tmpdir:
        eh.DATA_DIR   = Path(tmpdir)
        eh.ERROR_LOG  = Path(tmpdir) / "error_log.jsonl"
        eh.ERROR_STATS = Path(tmpdir) / "error_stats.json"

        @eh.safe_call_transparent("fn2", "ERROR")
        async def always_fails():
            raise ValueError("fail")

        result = run(always_fails())
        assert result is None, f"Erwartet None, bekommen {result!r}"
    print("  ✅ test_safe_call_transparent_returns_none_on_error")


def test_error_stats_updates_correctly():
    _reset_state()
    with tempfile.TemporaryDirectory() as tmpdir:
        eh.DATA_DIR   = Path(tmpdir)
        eh.ERROR_LOG  = Path(tmpdir) / "error_log.jsonl"
        eh.ERROR_STATS = Path(tmpdir) / "error_stats.json"

        run(eh.handle_error(ValueError("a"), "ctx1", severity="WARNING", telegram_alert=False))
        run(eh.handle_error(ValueError("b"), "ctx2", severity="WARNING", telegram_alert=False))
        run(eh.handle_error(RuntimeError("c"), "ctx3", severity="ERROR", telegram_alert=False))

        stats = json.loads(eh.ERROR_STATS.read_text())
        assert stats.get("WARNING:ValueError") == 2
        assert stats.get("ERROR:RuntimeError") == 1
        assert stats.get("_total") == 3
    print("  ✅ test_error_stats_updates_correctly")


# ── Runner ────────────────────────────────────────────────────────────────────

def run_all():
    orig_data  = eh.DATA_DIR
    orig_log   = eh.ERROR_LOG
    orig_stats = eh.ERROR_STATS

    tests = [
        test_handle_error_logs_to_file,
        test_handle_error_sends_telegram_alert,
        test_handle_error_rate_limits,
        test_handle_error_reraise,
        test_safe_call_transparent_catches_and_logs,
        test_safe_call_transparent_returns_none_on_error,
        test_error_stats_updates_correctly,
    ]

    ok = fail = 0
    for t in tests:
        try:
            t()
            ok += 1
        except Exception as e:
            fail += 1
            print(f"  ❌ FAIL {t.__name__}: {e}")
        finally:
            # Pfade nach jedem Test zurücksetzen
            eh.DATA_DIR   = orig_data
            eh.ERROR_LOG  = orig_log
            eh.ERROR_STATS = orig_stats
            _reset_state()

    total = len(tests)
    print(f"\n{'✅ Alle' if fail == 0 else '⚠️ '}{ok}/{total} Tests bestanden"
          + (f" | {fail} Fehler" if fail else ""))
    return fail == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
