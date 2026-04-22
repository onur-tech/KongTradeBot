"""Unit tests for core/kelly_sizer.py — Phase 2.4"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.kelly_sizer import kelly_size


class TestKellySizer(unittest.TestCase):

    # ── Basic calculations ────────────────────────────────────────────────────

    def test_returns_tuple_of_three(self):
        size, frac, cap = kelly_size(0.65, 1000.0)
        self.assertIsInstance(size, float)
        self.assertIsInstance(frac, float)

    def test_positive_size_for_typical_params(self):
        size, frac, cap = kelly_size(0.65, 1000.0, win_prob=0.55)
        self.assertGreater(size, 0)

    def test_pos_cap_applied(self):
        # At bankroll=1000, max_pos_pct=0.02 → cap at $20
        size, frac, cap = kelly_size(0.30, 1000.0, max_pos_pct=0.02, win_prob=0.70)
        self.assertLessEqual(size, 20.0)
        # cap flag should indicate pos_cap or market_cap (kelly value would exceed 2%)
        self.assertIn(cap, ("pos_cap", "market_cap", None))

    def test_market_cap_applied(self):
        # market already invested = 95% of max
        size, frac, cap = kelly_size(
            0.50, 1000.0,
            max_market_pct=0.10,
            market_already_invested=95.0,  # $5 remaining
        )
        self.assertLessEqual(size, 5.01)

    def test_negative_kelly_returns_floor(self):
        # Price 0.90 with win_prob=0.55 → negative Kelly
        size, frac, cap = kelly_size(0.90, 1000.0, win_prob=0.55, floor_pct=0.002)
        self.assertEqual(cap, "negative_kelly")
        self.assertAlmostEqual(size, 2.0, places=1)  # 0.2% of 1000

    def test_zero_bankroll_returns_zero(self):
        size, frac, cap = kelly_size(0.65, 0.0)
        self.assertEqual(size, 0.0)
        self.assertEqual(frac, 0.0)

    def test_invalid_price_zero(self):
        size, frac, cap = kelly_size(0.0, 1000.0)
        self.assertEqual(size, 0.0)

    def test_invalid_price_one(self):
        size, frac, cap = kelly_size(1.0, 1000.0)
        self.assertEqual(size, 0.0)

    def test_quarter_kelly_fraction_applied(self):
        # Full Kelly at p=0.55, price=0.50: b=1.0, full_kelly = (0.55*1 - 0.45)/1 = 0.10
        # Quarter Kelly → applied_fraction = 0.25 * 0.10 = 0.025 → $25 on $1000
        size, frac, cap = kelly_size(0.50, 1000.0, kelly_fraction=0.25, win_prob=0.55, max_pos_pct=1.0)
        self.assertAlmostEqual(frac, 0.025, places=3)
        self.assertAlmostEqual(size, 25.0, places=1)

    def test_market_fully_used_returns_zero(self):
        size, frac, cap = kelly_size(
            0.50, 1000.0,
            max_market_pct=0.10,
            market_already_invested=100.0,  # fully used
        )
        self.assertEqual(size, 0.0)

    # ── Simulation: plausibility checks ──────────────────────────────────────

    def test_size_increases_with_lower_price(self):
        # Lower price = longer odds = bigger Kelly bet (all else equal)
        size_30, _, _ = kelly_size(0.30, 1000.0, max_pos_pct=1.0, win_prob=0.60)
        size_70, _, _ = kelly_size(0.70, 1000.0, max_pos_pct=1.0, win_prob=0.60)
        self.assertGreater(size_30, size_70)

    def test_size_bounded_by_pos_cap(self):
        for price in (0.10, 0.30, 0.50, 0.70):
            size, _, _ = kelly_size(price, 10_000.0, max_pos_pct=0.02)
            self.assertLessEqual(size, 200.01, msg=f"price={price}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
