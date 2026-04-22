"""Unit tests for core/reconciliation.py — Phase 2.1"""
import sys
import asyncio
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.reconciliation import ReconciliationLoop


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class FakePos:
    def __init__(self, token_id, outcome="Yes", size_usdc=10.0):
        self.token_id = token_id
        self.outcome = outcome
        self.size_usdc = size_usdc


class FakeEngine:
    def __init__(self, positions: dict):
        self.open_positions = positions


class FakeConfig:
    def __init__(self, address="0xabc"):
        self.polymarket_address = address


class TestReconciliationLoop(unittest.TestCase):

    def _make_loop(self, positions=None, address="0xabc", send=None):
        engine = FakeEngine(positions or {})
        config = FakeConfig(address)
        return ReconciliationLoop(engine, config, send)

    # ── Happy path ────────────────────────────────────────────────────────────

    def test_no_phantoms_when_all_match(self):
        pos = FakePos("tok1")
        loop = self._make_loop({"order1": pos})
        api_tokens = {"tok1", "tok2"}

        async def fake_fetch(addr):
            return api_tokens

        loop._fetch_api_tokens = fake_fetch
        run(loop._reconcile())
        self.assertTrue(loop._last_check_ok)
        self.assertEqual(loop._phantom_total, 0)

    def test_detects_phantom_when_token_absent(self):
        alerts = []
        pos = FakePos("tok_gone")
        loop = self._make_loop({"order_phantom": pos}, send=AsyncMock())

        async def fake_fetch(addr):
            return {"tok_other"}  # tok_gone not here

        loop._fetch_api_tokens = fake_fetch
        run(loop._reconcile())
        self.assertFalse(loop._last_check_ok)
        self.assertEqual(loop._phantom_total, 1)

    def test_recovered_positions_skipped(self):
        """RECOVERED_... synthetic positions must not trigger phantom alerts."""
        pos = FakePos("tok_recovered")
        loop = self._make_loop({"RECOVERED_condXXX_Yes": pos})

        async def fake_fetch(addr):
            return set()  # empty — tok_recovered not here either

        loop._fetch_api_tokens = fake_fetch
        run(loop._reconcile())
        self.assertTrue(loop._last_check_ok)
        self.assertEqual(loop._phantom_total, 0)

    def test_no_address_skips_reconcile(self):
        loop = self._make_loop(address="")
        # _fetch_api_tokens should never be called
        called = []

        async def fake_fetch(addr):
            called.append(addr)
            return set()

        loop._fetch_api_tokens = fake_fetch
        run(loop._reconcile())
        self.assertEqual(called, [])

    def test_api_failure_does_not_raise(self):
        loop = self._make_loop({"order1": FakePos("tok1")})

        async def fake_fetch(addr):
            return None  # simulates network failure

        loop._fetch_api_tokens = fake_fetch
        # Must not raise
        run(loop._reconcile())

    def test_status_returns_dict(self):
        loop = self._make_loop()
        s = loop.status()
        self.assertIn("last_check_ok", s)
        self.assertIn("phantom_total_session", s)

    # ── Cumulative phantom count ───────────────────────────────────────────────

    def test_phantom_count_accumulates(self):
        pos = FakePos("missing")
        loop = self._make_loop({"ord": pos})

        async def fake_fetch(addr):
            return set()

        loop._fetch_api_tokens = fake_fetch
        run(loop._reconcile())
        run(loop._reconcile())
        self.assertEqual(loop._phantom_total, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
