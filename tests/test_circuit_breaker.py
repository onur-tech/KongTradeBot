"""Unit tests for core/circuit_breaker.py — Phase 2.5"""
import sys
import json
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.circuit_breaker as cb_module
from core.circuit_breaker import CircuitBreaker, CBState


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class TestCircuitBreaker(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.state_path = Path(self.tmp.name)
        self._orig_path = cb_module.CB_STATE_PATH
        cb_module.CB_STATE_PATH = self.state_path

    def tearDown(self):
        cb_module.CB_STATE_PATH = self._orig_path
        self.state_path.unlink(missing_ok=True)

    def _cb(self, send=None):
        return CircuitBreaker(telegram_send=send)

    # ── Level triggering ──────────────────────────────────────────────────────

    def test_no_block_below_l1(self):
        cb = self._cb()
        run(cb.update(daily_loss_usd=40.0, bankroll=1000.0))  # 4% < 5%
        self.assertFalse(cb.is_blocked())
        self.assertEqual(cb.status()["level"], 0)

    def test_l1_triggered_at_threshold(self):
        cb = self._cb()
        run(cb.update(daily_loss_usd=50.0, bankroll=1000.0))  # exactly 5%
        self.assertEqual(cb.status()["level"], 1)
        self.assertFalse(cb.is_blocked())  # L1 warns but does NOT block

    def test_l2_triggered_and_blocks(self):
        cb = self._cb()
        run(cb.update(daily_loss_usd=100.0, bankroll=1000.0))  # 10%
        self.assertEqual(cb.status()["level"], 2)
        self.assertTrue(cb.is_blocked())

    def test_l3_triggered_and_blocks(self):
        cb = self._cb()
        run(cb.update(daily_loss_usd=150.0, bankroll=1000.0))  # 15%
        self.assertEqual(cb.status()["level"], 3)
        self.assertTrue(cb.is_blocked())

    def test_levels_do_not_downgrade(self):
        """Going from L3 back to 8% should NOT lower the level."""
        cb = self._cb()
        run(cb.update(150.0, 1000.0))   # hits L3
        run(cb.update(80.0, 1000.0))    # now "only" 8% — still L3
        self.assertEqual(cb.status()["level"], 3)

    # ── Idempotency ───────────────────────────────────────────────────────────

    def test_update_idempotent_at_same_level(self):
        send = AsyncMock()
        cb = self._cb(send=send)
        run(cb.update(50.0, 1000.0))   # triggers L1
        run(cb.update(55.0, 1000.0))   # still L1
        # Alert should fire only ONCE
        self.assertEqual(send.call_count, 1)

    # ── Persistence ───────────────────────────────────────────────────────────

    def test_state_saved_and_restored(self):
        cb1 = self._cb()
        run(cb1.update(150.0, 1000.0))  # hits L3

        # New instance — should restore from disk
        cb2 = self._cb()
        self.assertEqual(cb2.status()["level"], 3)
        self.assertTrue(cb2.is_blocked())

    # ── Reset ─────────────────────────────────────────────────────────────────

    def test_manual_reset_clears_all_levels(self):
        cb = self._cb()
        run(cb.update(150.0, 1000.0))
        cb.reset("test")
        self.assertEqual(cb.status()["level"], 0)
        self.assertFalse(cb.is_blocked())

    def test_daily_reset_clears_l1(self):
        cb = self._cb()
        run(cb.update(50.0, 1000.0))   # L1
        cb.daily_reset()
        self.assertEqual(cb.status()["level"], 0)

    def test_daily_reset_clears_l2(self):
        cb = self._cb()
        run(cb.update(100.0, 1000.0))  # L2
        cb.daily_reset()
        self.assertEqual(cb.status()["level"], 0)

    def test_daily_reset_does_not_clear_l3(self):
        cb = self._cb()
        run(cb.update(150.0, 1000.0))  # L3
        cb.daily_reset()
        self.assertEqual(cb.status()["level"], 3)   # L3 stays!

    # ── Pause expiry ──────────────────────────────────────────────────────────

    def test_l2_pause_expired_auto_unblocks(self):
        from datetime import timezone
        cb = self._cb()
        run(cb.update(100.0, 1000.0))  # hits L2
        # Override pause_until to be in the past
        past = "2020-01-01T00:00:00+00:00"
        cb._state.pause_until = past
        cb._save()
        # Now is_blocked should auto-reset
        self.assertFalse(cb.is_blocked())
        self.assertEqual(cb._state.level, 0)

    # ── Edge cases ────────────────────────────────────────────────────────────

    def test_zero_bankroll_safe(self):
        cb = self._cb()
        run(cb.update(100.0, 0.0))  # should not raise, no level change
        self.assertEqual(cb.status()["level"], 0)

    def test_telegram_called_on_l3(self):
        send = AsyncMock()
        cb = self._cb(send=send)
        run(cb.update(150.0, 1000.0))
        send.assert_called_once()
        call_text = send.call_args[0][0]
        self.assertIn("HALT", call_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
