"""Unit tests for core/slippage_check.py — Phase 2.3"""
import sys
import asyncio
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.slippage_check import _compute_vwap, check_slippage


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# ── _compute_vwap unit tests ──────────────────────────────────────────────────

class TestComputeVwap(unittest.TestCase):

    def _book(self, asks=None, bids=None):
        return {"asks": asks or [], "bids": bids or []}

    def test_single_ask_level_exact_fill(self):
        book = self._book(asks=[{"price": "0.65", "size": "200"}])
        # size_usdc=10 fills at 0.65 exactly
        vwap = _compute_vwap(book, "BUY", 10.0)
        self.assertAlmostEqual(vwap, 0.65, places=4)

    def test_two_levels_partial_walk(self):
        book = self._book(asks=[
            {"price": "0.65", "size": "10"},   # 10 * 0.65 = $6.50 USDC
            {"price": "0.70", "size": "100"},  # rest here
        ])
        # $10 total: $6.50 at 0.65 + $3.50 at 0.70
        # shares: 10 + 5 = 15
        # vwap = 10/15 = 0.6667
        vwap = _compute_vwap(book, "BUY", 10.0)
        self.assertIsNotNone(vwap)
        self.assertGreater(vwap, 0.65)
        self.assertLess(vwap, 0.70)

    def test_empty_orderbook_returns_none(self):
        self.assertIsNone(_compute_vwap(self._book(), "BUY", 10.0))

    def test_sell_side_uses_bids(self):
        book = self._book(bids=[{"price": "0.60", "size": "200"}])
        vwap = _compute_vwap(book, "SELL", 10.0)
        self.assertAlmostEqual(vwap, 0.60, places=4)

    def test_zero_price_level_skipped(self):
        book = self._book(asks=[
            {"price": "0", "size": "100"},
            {"price": "0.65", "size": "200"},
        ])
        vwap = _compute_vwap(book, "BUY", 10.0)
        self.assertAlmostEqual(vwap, 0.65, places=4)


# ── check_slippage integration tests ─────────────────────────────────────────

class TestCheckSlippage(unittest.TestCase):

    def _book_at(self, ask_price: float, size_shares: float = 1000.0):
        return {"asks": [{"price": str(ask_price), "size": str(size_shares)}], "bids": []}

    def test_zero_slippage_ok(self):
        book = self._book_at(0.65)
        with patch("core.slippage_check._fetch_orderbook", new=AsyncMock(return_value=book)):
            ok, bps, reason = run(check_slippage("tok1", 0.65, 10.0))
        self.assertTrue(ok)
        self.assertAlmostEqual(bps, 0.0, places=1)

    def test_warn_threshold_allows_but_warns(self):
        # Signal price 0.60, vwap 0.62 → slippage ~333 bps
        book = self._book_at(0.62)
        with patch("core.slippage_check._fetch_orderbook", new=AsyncMock(return_value=book)):
            ok, bps, reason = run(check_slippage("tok1", 0.60, 10.0))
        self.assertTrue(ok)
        self.assertGreater(bps, 300)
        self.assertIn("warn", reason.lower())

    def test_reject_threshold_blocks(self):
        # Signal price 0.60, vwap 0.64 → slippage ~667 bps
        book = self._book_at(0.64)
        with patch("core.slippage_check._fetch_orderbook", new=AsyncMock(return_value=book)):
            ok, bps, reason = run(check_slippage("tok1", 0.60, 10.0))
        self.assertFalse(ok)
        self.assertGreater(bps, 500)

    def test_fail_open_when_orderbook_unavailable(self):
        with patch("core.slippage_check._fetch_orderbook", new=AsyncMock(return_value=None)):
            ok, bps, reason = run(check_slippage("tok1", 0.65, 10.0))
        self.assertTrue(ok)
        self.assertAlmostEqual(bps, 0.0)
        self.assertIn("skipped", reason)

    def test_missing_params_skip(self):
        ok, bps, reason = run(check_slippage("", 0.65, 10.0))
        self.assertTrue(ok)
        self.assertIn("skipped", reason)

    def test_negative_slippage_allowed(self):
        # VWAP better than signal price (favorable fill)
        book = self._book_at(0.63)
        with patch("core.slippage_check._fetch_orderbook", new=AsyncMock(return_value=book)):
            ok, bps, _ = run(check_slippage("tok1", 0.65, 10.0))
        self.assertTrue(ok)
        self.assertLess(bps, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
