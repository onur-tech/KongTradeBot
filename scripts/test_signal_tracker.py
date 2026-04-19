#!/usr/bin/env python3
"""
scripts/test_signal_tracker.py — Tests für utils/signal_tracker.py

Usage:
    python3 scripts/test_signal_tracker.py
"""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

import utils.signal_tracker as st


def _make_signal(tx_hash="0xabc123", market_id="0xmkt", token_id="0xtok",
                 price=0.35, size_usdc=100.0, outcome="Yes",
                 closes_in_hours=48):
    s = MagicMock()
    s.tx_hash = tx_hash
    s.source_wallet = "0xwallet"
    s.market_id = market_id
    s.token_id = token_id
    s.outcome = outcome
    s.side = "BUY"
    s.price = price
    s.size_usdc = size_usdc
    s.market_question = "Test market?"
    s.market_closes_at = datetime.now(timezone.utc) + timedelta(hours=closes_in_hours)
    return s


class TestLogSignal(unittest.TestCase):

    def test_log_signal_appends_jsonl(self):
        """log_signal schreibt einen validen JSON-Record in die JSONL-Datei."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(st, "_BASE", Path(tmpdir)), \
                 patch.object(st, "SIGNALS_FILE", Path(tmpdir) / "all_signals.jsonl"):
                signal = _make_signal()
                st.log_signal(signal, "SKIPPED", "MIN_TRADE_SIZE")
                lines = (Path(tmpdir) / "all_signals.jsonl").read_text().strip().splitlines()
                self.assertEqual(len(lines), 1)
                rec = json.loads(lines[0])
                self.assertEqual(rec["decision"], "SKIPPED")
                self.assertEqual(rec["skip_reason"], "MIN_TRADE_SIZE")
                self.assertEqual(rec["tx_hash"], "0xabc123")
                self.assertFalse(rec["retroactive"])

    def test_log_signal_copied(self):
        """log_signal schreibt COPIED-Record ohne skip_reason."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(st, "_BASE", Path(tmpdir)), \
                 patch.object(st, "SIGNALS_FILE", Path(tmpdir) / "all_signals.jsonl"):
                signal = _make_signal()
                st.log_signal(signal, "COPIED", None)
                rec = json.loads((Path(tmpdir) / "all_signals.jsonl").read_text().strip())
                self.assertEqual(rec["decision"], "COPIED")
                self.assertIsNone(rec["skip_reason"])

    def test_log_signal_never_raises(self):
        """log_signal darf niemals eine Exception werfen — auch mit ungültigem Signal."""
        broken = MagicMock()
        broken.tx_hash = None
        broken.market_id = object()  # nicht serialisierbar → soll silent fail
        try:
            st.log_signal(broken, "SKIPPED", "TEST")
        except Exception as e:
            self.fail(f"log_signal hat Exception geworfen: {e}")


class TestEvaluateHandlesUnresolved(unittest.TestCase):

    def test_evaluate_handles_unresolved(self):
        """evaluate_skipped_signals überspringt unresolved Markets."""
        import asyncio

        with tempfile.TemporaryDirectory() as tmpdir:
            signals_file = Path(tmpdir) / "all_signals.jsonl"
            outcomes_file = Path(tmpdir) / "skipped_signal_outcomes.jsonl"

            # Signal das vor >24h geschlossen haben sollte
            closed_at = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
            record = {
                "ts": (datetime.now(timezone.utc) - timedelta(hours=31)).isoformat(),
                "tx_hash": "0xtest001",
                "wallet": "0xwallet",
                "market_id": "0xmkt",
                "token_id": "0xtok",
                "outcome": "Yes",
                "side": "BUY",
                "price": 0.35,
                "whale_size_usdc": 100.0,
                "market_question": "Test?",
                "market_closes_at": closed_at,
                "decision": "SKIPPED",
                "skip_reason": "MIN_TRADE_SIZE",
                "retroactive": False,
            }
            signals_file.write_text(json.dumps(record) + "\n")

            with patch.object(st, "_BASE", Path(tmpdir)), \
                 patch.object(st, "SIGNALS_FILE", signals_file), \
                 patch.object(st, "OUTCOMES_FILE", outcomes_file), \
                 patch("utils.signal_tracker._fetch_market_status") as mock_fetch:

                mock_fetch.return_value = {"resolved": False}

                async def run():
                    return await st.evaluate_skipped_signals(days_back=7)

                results = asyncio.run(run())
                self.assertEqual(len(results), 0)
                self.assertFalse(outcomes_file.exists())


class TestEvaluateResolvedWinner(unittest.TestCase):

    def test_evaluate_handles_resolved_winner(self):
        """evaluate_skipped_signals berechnet positiven Profit für gewonnenes Signal."""
        import asyncio

        with tempfile.TemporaryDirectory() as tmpdir:
            signals_file = Path(tmpdir) / "all_signals.jsonl"
            outcomes_file = Path(tmpdir) / "skipped_signal_outcomes.jsonl"

            closed_at = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
            record = {
                "ts": (datetime.now(timezone.utc) - timedelta(hours=31)).isoformat(),
                "tx_hash": "0xwinner001",
                "wallet": "0xwallet",
                "market_id": "0xmkt",
                "token_id": "0xwintoken",
                "outcome": "Yes",
                "side": "BUY",
                "price": 0.40,
                "whale_size_usdc": 200.0,
                "market_question": "Test winner?",
                "market_closes_at": closed_at,
                "decision": "SKIPPED",
                "skip_reason": "MIN_TRADE_SIZE",
                "retroactive": False,
            }
            signals_file.write_text(json.dumps(record) + "\n")

            with patch.object(st, "_BASE", Path(tmpdir)), \
                 patch.object(st, "SIGNALS_FILE", signals_file), \
                 patch.object(st, "OUTCOMES_FILE", outcomes_file), \
                 patch("utils.signal_tracker._fetch_market_status") as mock_fetch:

                mock_fetch.return_value = {"resolved": True, "winning_token_id": "0xwintoken"}

                async def run():
                    return await st.evaluate_skipped_signals(days_back=7)

                results = asyncio.run(run())
                self.assertEqual(len(results), 1)
                r = results[0]
                self.assertTrue(r["signal_correct"])
                self.assertGreater(r["theoretical_profit_usdc"], 0)
                # theoretical_size = 200 * 0.05 = 10, profit = 10/0.4 - 10 = 15
                self.assertAlmostEqual(r["theoretical_profit_usdc"], 15.0, places=2)


class TestEvaluateResolvedLoser(unittest.TestCase):

    def test_evaluate_handles_resolved_loser(self):
        """evaluate_skipped_signals berechnet negativen Profit für verlorenes Signal."""
        import asyncio

        with tempfile.TemporaryDirectory() as tmpdir:
            signals_file = Path(tmpdir) / "all_signals.jsonl"
            outcomes_file = Path(tmpdir) / "skipped_signal_outcomes.jsonl"

            closed_at = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
            record = {
                "ts": (datetime.now(timezone.utc) - timedelta(hours=31)).isoformat(),
                "tx_hash": "0xloser001",
                "wallet": "0xwallet",
                "market_id": "0xmkt",
                "token_id": "0xlosertoken",
                "outcome": "No",
                "side": "BUY",
                "price": 0.60,
                "whale_size_usdc": 100.0,
                "market_question": "Test loser?",
                "market_closes_at": closed_at,
                "decision": "SKIPPED",
                "skip_reason": "BUDGET_CAP",
                "retroactive": False,
            }
            signals_file.write_text(json.dumps(record) + "\n")

            with patch.object(st, "_BASE", Path(tmpdir)), \
                 patch.object(st, "SIGNALS_FILE", signals_file), \
                 patch.object(st, "OUTCOMES_FILE", outcomes_file), \
                 patch("utils.signal_tracker._fetch_market_status") as mock_fetch:

                mock_fetch.return_value = {"resolved": True, "winning_token_id": "0xother"}

                async def run():
                    return await st.evaluate_skipped_signals(days_back=7)

                results = asyncio.run(run())
                self.assertEqual(len(results), 1)
                r = results[0]
                self.assertFalse(r["signal_correct"])
                self.assertLess(r["theoretical_profit_usdc"], 0)
                # theoretical_size = 100 * 0.05 = 5, loss = -5
                self.assertAlmostEqual(r["theoretical_profit_usdc"], -5.0, places=2)


class TestWeeklyReportFormat(unittest.TestCase):

    def test_weekly_report_format(self):
        """generate_weekly_report gibt Telegram-HTML-String zurück."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(st, "SIGNALS_FILE", Path(tmpdir) / "empty.jsonl"), \
                 patch.object(st, "OUTCOMES_FILE", Path(tmpdir) / "empty2.jsonl"):
                report = st.generate_weekly_report()
                self.assertIn("Skipped-Signal Report", report)
                self.assertIn("Signale diese Woche", report)
                self.assertIn("Kopiert", report)
                self.assertIn("Geskippt", report)
                self.assertIn("<b>", report)


if __name__ == "__main__":
    print("🧪 Running signal_tracker tests...\n")
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
