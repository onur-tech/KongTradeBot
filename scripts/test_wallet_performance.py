#!/usr/bin/env python3
"""Tests für utils/wallet_performance.py"""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

WALLET = "0x7a6192ea6815d3177e978dd3f8c38be5f575af24"

FAKE_TRADES = [
    {
        "source_wallet": WALLET, "modus": "LIVE",
        "datum": "2026-04-18", "kategorie": "sport_us",
        "einsatz_usdc": "50.00", "ergebnis": "GEWINN",
        "gewinn_verlust_usdc": "30.00", "market_id": "0xaaaa",
    },
    {
        "source_wallet": WALLET, "modus": "LIVE",
        "datum": "2026-04-18", "kategorie": "sport_us",
        "einsatz_usdc": "40.00", "ergebnis": "VERLUST",
        "gewinn_verlust_usdc": "-40.00", "market_id": "0xbbbb",
    },
    {
        "source_wallet": WALLET, "modus": "LIVE",
        "datum": "2026-04-19", "kategorie": "soccer",
        "einsatz_usdc": "30.00", "ergebnis": "",
        "gewinn_verlust_usdc": "", "market_id": "0xcccc",
    },
    {
        "source_wallet": WALLET, "modus": "LIVE",
        "datum": "2026-04-19", "kategorie": "soccer",
        "einsatz_usdc": "20.00", "ergebnis": "GEWINN",
        "gewinn_verlust_usdc": "20.00", "market_id": "0xdddd",
    },
    {
        "source_wallet": WALLET, "modus": "LIVE",
        "datum": "2026-04-19", "kategorie": "geopolitik",
        "einsatz_usdc": "60.00", "ergebnis": "VERLUST",
        "gewinn_verlust_usdc": "-60.00", "market_id": "0xeeee",
    },
]

FAKE_PORTFOLIO = {
    "positions": [
        {"condition_id": "0xcccc", "pnl_usdc": 12.5, "closes_in_label": "5d 3h"},
    ]
}


def _patch_archive(trades=None):
    return patch(
        "utils.wallet_performance._load_archive",
        return_value=(trades if trades is not None else FAKE_TRADES),
    )


def _patch_portfolio(data=None):
    return patch(
        "utils.wallet_performance._load_portfolio_pnl",
        return_value={p["condition_id"]: p for p in (data or FAKE_PORTFOLIO["positions"])},
    )


def _patch_slippage():
    return patch("utils.wallet_performance._load_slippage", return_value={})


class TestComputeWalletStats(unittest.TestCase):

    def test_hit_rate_and_counts(self):
        with _patch_archive(), _patch_portfolio(), _patch_slippage():
            from utils.wallet_performance import compute_wallet_stats
            s = compute_wallet_stats(WALLET, since_days=30)
        self.assertEqual(s["wins_count"], 2)
        self.assertEqual(s["losses_count"], 2)
        self.assertEqual(s["pending_count"], 1)
        self.assertEqual(s["hit_rate"], 50.0)

    def test_roi_calculation(self):
        with _patch_archive(), _patch_portfolio(), _patch_slippage():
            from utils.wallet_performance import compute_wallet_stats
            s = compute_wallet_stats(WALLET, since_days=30)
        # Invested: 50+40+30+20+60 = 200
        # Return: (50+30) + (40-40) + 0 + (20+20) + (60-60) = 120
        # net_pnl = 120 - 200 = -80
        self.assertEqual(s["total_invested_usdc"], 200.0)
        self.assertAlmostEqual(s["net_pnl_usdc"], -80.0, places=2)

    def test_unrealized_pnl_from_portfolio(self):
        with _patch_archive(), _patch_portfolio(), _patch_slippage():
            from utils.wallet_performance import compute_wallet_stats
            s = compute_wallet_stats(WALLET, since_days=30)
        self.assertAlmostEqual(s["unrealized_pnl_usdc"], 12.5, places=2)

    def test_low_sample_flag(self):
        with _patch_archive(FAKE_TRADES[:3]), _patch_portfolio(), _patch_slippage():
            from utils.wallet_performance import compute_wallet_stats
            s = compute_wallet_stats(WALLET, since_days=30)
        self.assertTrue(s["low_sample"])

    def test_empty_wallet(self):
        with _patch_archive([]), _patch_portfolio(), _patch_slippage():
            from utils.wallet_performance import compute_wallet_stats
            s = compute_wallet_stats(WALLET, since_days=30)
        self.assertEqual(s["trades_count"], 0)
        self.assertIsNone(s["hit_rate"])
        self.assertIsNone(s["roi_pct"])
        self.assertTrue(s["low_sample"])


class TestComputeByCategory(unittest.TestCase):

    def test_category_grouping(self):
        with _patch_archive(), _patch_portfolio(), _patch_slippage():
            from utils.wallet_performance import compute_by_category
            cats = compute_by_category(WALLET, since_days=30)
        self.assertIn("sport_us", cats)
        self.assertIn("soccer", cats)
        self.assertIn("geopolitik", cats)
        self.assertEqual(cats["sport_us"]["trades"], 2)
        self.assertEqual(cats["soccer"]["trades"], 2)
        self.assertEqual(cats["geopolitik"]["trades"], 1)

    def test_category_hit_rate(self):
        with _patch_archive(), _patch_portfolio(), _patch_slippage():
            from utils.wallet_performance import compute_by_category
            cats = compute_by_category(WALLET, since_days=30)
        # sport_us: 1 win, 1 loss → 50%
        self.assertEqual(cats["sport_us"]["hit_rate"], 50.0)
        # soccer: 1 win, 0 losses (1 pending) → 100%
        self.assertEqual(cats["soccer"]["hit_rate"], 100.0)


class TestComputeByTimeframe(unittest.TestCase):

    def test_timeframe_bucket_assignment(self):
        with _patch_archive(), _patch_portfolio(), _patch_slippage():
            from utils.wallet_performance import compute_by_timeframe
            tfs = compute_by_timeframe(WALLET, since_days=30)
        # 0xcccc maps to closes_in_label "5d 3h" → "medium"
        # Other trades have no portfolio entry → "unknown"
        self.assertIn("medium", tfs)
        self.assertIn("unknown", tfs)
        self.assertEqual(tfs["medium"]["trades"], 1)


class TestTimeframeBucket(unittest.TestCase):

    def test_same_day(self):
        from utils.wallet_performance import _timeframe_bucket
        self.assertEqual(_timeframe_bucket("0d 8h"), "same_day")

    def test_short(self):
        from utils.wallet_performance import _timeframe_bucket
        self.assertEqual(_timeframe_bucket("3d 2h"), "short")

    def test_medium(self):
        from utils.wallet_performance import _timeframe_bucket
        self.assertEqual(_timeframe_bucket("10d 17h"), "medium")

    def test_long(self):
        from utils.wallet_performance import _timeframe_bucket
        self.assertEqual(_timeframe_bucket("14d 0h"), "long")

    def test_unknown(self):
        from utils.wallet_performance import _timeframe_bucket
        self.assertEqual(_timeframe_bucket("—"), "unknown")
        self.assertEqual(_timeframe_bucket(""), "unknown")


if __name__ == "__main__":
    unittest.main(verbosity=2)
