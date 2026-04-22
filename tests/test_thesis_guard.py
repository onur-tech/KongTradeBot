"""Unit tests for core/thesis_guard.py — Phase 2.7"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.thesis_guard import ThesisGuard, ThesisViolation


class TestThesisGuard(unittest.TestCase):

    def setUp(self):
        self.guard = ThesisGuard()

    def _register(self, order_id="ord1", wallet="0xwhale", entry=0.65):
        self.guard.register_position(order_id, wallet, entry)

    # ── Hard-Stop ─────────────────────────────────────────────────────────────

    def test_hard_stop_not_triggered_below_threshold(self):
        self._register(entry=0.65)
        # 30% drop — default threshold is 40%
        v = self.guard.check_hard_stop("ord1", 0.65, 0.46)
        self.assertIsNone(v)

    def test_hard_stop_triggered_at_threshold(self):
        self._register(entry=0.65)
        # 40% drop: 0.65 * 0.60 = 0.39
        v = self.guard.check_hard_stop("ord1", 0.65, 0.39)
        self.assertIsNotNone(v)
        self.assertIsInstance(v, ThesisViolation)
        self.assertIn("Hard-stop", v.reason)

    def test_hard_stop_does_not_double_fire(self):
        self._register(entry=0.65)
        self.guard.check_hard_stop("ord1", 0.65, 0.30)  # triggers
        v2 = self.guard.check_hard_stop("ord1", 0.65, 0.20)  # should NOT re-fire
        self.assertIsNone(v2)

    def test_hard_stop_zero_entry_price_safe(self):
        v = self.guard.check_hard_stop("ord1", 0.0, 0.30)
        self.assertIsNone(v)

    def test_hard_stop_custom_threshold(self):
        with patch("core.thesis_guard.HARD_STOP_PCT", 0.20):
            guard = ThesisGuard()
            guard.register_position("ord1", "0xw", 0.65)
            # 25% drop
            v = guard.check_hard_stop("ord1", 0.65, 0.49)
            self.assertIsNotNone(v)

    # ── Whale Exit Invalidation ───────────────────────────────────────────────

    def test_whale_exit_invalidates_position(self):
        self._register("ord1", "0xwhale")
        affected = self.guard.on_whale_exit("0xwhale")
        self.assertIn("ord1", affected)
        self.assertIsNotNone(self.guard.get_violation("ord1"))

    def test_whale_exit_only_affects_that_wallet(self):
        self.guard.register_position("ord1", "0xwhale_A", 0.65)
        self.guard.register_position("ord2", "0xwhale_B", 0.70)
        self.guard.on_whale_exit("0xwhale_A")
        self.assertIsNotNone(self.guard.get_violation("ord1"))
        self.assertIsNone(self.guard.get_violation("ord2"))

    def test_whale_exit_disabled_by_flag(self):
        with patch("core.thesis_guard.EXIT_ON_WHALE_EXIT", False):
            guard = ThesisGuard()
            guard.register_position("ord1", "0xwhale", 0.65)
            affected = guard.on_whale_exit("0xwhale")
            self.assertEqual(affected, [])
            self.assertIsNone(guard.get_violation("ord1"))

    def test_whale_exit_unknown_wallet_returns_empty(self):
        affected = self.guard.on_whale_exit("0xunknown")
        self.assertEqual(affected, [])

    # ── clear_position ────────────────────────────────────────────────────────

    def test_clear_removes_violation(self):
        self._register(entry=0.65)
        self.guard.check_hard_stop("ord1", 0.65, 0.30)
        self.guard.clear_position("ord1")
        self.assertIsNone(self.guard.get_violation("ord1"))

    def test_clear_removes_from_wallet_map(self):
        self._register("ord1", "0xw", 0.65)
        self.guard.clear_position("ord1")
        affected = self.guard.on_whale_exit("0xw")
        self.assertEqual(affected, [])

    # ── Multi-position ────────────────────────────────────────────────────────

    def test_all_violations_returns_all(self):
        self.guard.register_position("a", "0xw", 0.65)
        self.guard.register_position("b", "0xw", 0.70)
        self.guard.check_hard_stop("a", 0.65, 0.30)
        self.guard.check_hard_stop("b", 0.70, 0.30)
        self.assertEqual(len(self.guard.all_violations()), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
