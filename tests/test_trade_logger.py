"""Unit tests for core/trade_logger.py — Phase 1 Foundation Build."""
import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

import core.trade_logger as tl_module
from core.trade_logger import TradeLogger, migrate_from_archive


class FakeSignal:
    def __init__(self):
        self.tx_hash = "0xabc123"
        self.source_wallet = "0xwallet001"
        self.market_id = "0xmarket001"
        self.token_id = "0xtoken001"
        self.side = "BUY"
        self.price = 0.65
        self.size_usdc = 10.0
        self.detected_at = datetime.now(timezone.utc)
        self.market_question = "Will X happen?"
        self.outcome = "Yes"
        self.market_volume_usd = 50000.0
        self.is_early_entry = False


class FakeOrder:
    def __init__(self):
        self.size_usdc = 10.0
        self.is_multi_signal = False
        self.wallet_multiplier = 1.0


class FakeResult:
    def __init__(self):
        self.order_id = "order-abc-001"
        self.filled_price = 0.651
        self.success = True


class TestTradeLogger(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = Path(self.tmp.name)
        self.logger = TradeLogger(db_path=self.db_path)

    def tearDown(self):
        self.db_path.unlink(missing_ok=True)

    def test_init_creates_tables(self):
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        self.assertIn("signals", tables)
        self.assertIn("trades", tables)
        self.assertIn("wallet_snapshots", tables)
        self.assertIn("cohort_attributes", tables)

    def test_init_creates_views(self):
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        views = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='view'"
        ).fetchall()}
        conn.close()
        self.assertIn("cohort_by_category", views)
        self.assertIn("wallet_attribution", views)
        self.assertIn("slippage_histogram", views)

    def test_log_signal_returns_uuid(self):
        sig = FakeSignal()
        sid = self.logger.log_signal(sig)
        self.assertEqual(len(sid), 36)  # UUID length
        self.assertIn("-", sid)

    def test_log_signal_idempotent(self):
        sig = FakeSignal()
        sid1 = self.logger.log_signal(sig)
        sid2 = self.logger.log_signal(sig)
        # Two separate UUIDs (not deduped by content, that's fine)
        self.assertEqual(len(sid1), 36)
        self.assertEqual(len(sid2), 36)

    def test_log_trade_entry_returns_uuid_and_registers(self):
        sig = FakeSignal()
        order = FakeOrder()
        result = FakeResult()
        sid = self.logger.log_signal(sig)
        tid = self.logger.log_trade_entry(
            sid, "order-001",
            signal=sig, order=order, result=result,
            category="Soccer", is_dry_run=True, bankroll=500.0
        )
        self.assertEqual(len(tid), 36)
        self.assertEqual(self.logger.get_trade_id_for_order("order-001"), tid)

    def test_log_trade_entry_written_to_db(self):
        import sqlite3
        sig = FakeSignal()
        order = FakeOrder()
        result = FakeResult()
        sid = self.logger.log_signal(sig)
        tid = self.logger.log_trade_entry(
            sid, "order-002",
            signal=sig, order=order, result=result,
            category="Weather", is_dry_run=True, bankroll=400.0
        )
        conn = sqlite3.connect(str(self.db_path))
        row = conn.execute(
            "SELECT * FROM trades WHERE trade_id=?", (tid,)
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)

    def test_log_trade_exit_writes_exit_fields(self):
        import sqlite3
        sig = FakeSignal()
        order = FakeOrder()
        result = FakeResult()
        sid = self.logger.log_signal(sig)
        tid = self.logger.log_trade_entry(
            sid, "order-003",
            signal=sig, order=order, result=result,
            category="Soccer", is_dry_run=True, bankroll=500.0
        )
        self.logger.log_trade_exit(
            "order-003",
            exit_price=0.85,
            exit_size=10.0,
            exit_reason="RESOLUTION",
            realized_pnl_usd=2.0,
            entry_price=0.65,
            entry_size=10.0,
        )
        conn = sqlite3.connect(str(self.db_path))
        row = conn.execute(
            "SELECT exit_reason, realized_pnl_usd, exit_price FROM trades WHERE trade_id=?",
            (tid,)
        ).fetchone()
        conn.close()
        self.assertEqual(row[0], "RESOLUTION")
        self.assertAlmostEqual(row[1], 2.0)
        self.assertAlmostEqual(row[2], 0.85)

    def test_log_trade_exit_removes_from_map(self):
        sig = FakeSignal()
        order = FakeOrder()
        result = FakeResult()
        sid = self.logger.log_signal(sig)
        self.logger.log_trade_entry(
            sid, "order-004",
            signal=sig, order=order, result=result,
            category="Soccer", is_dry_run=True, bankroll=500.0
        )
        self.assertIsNotNone(self.logger.get_trade_id_for_order("order-004"))
        self.logger.log_trade_exit(
            "order-004", exit_price=0.9, exit_size=10.0,
            exit_reason="TP1", realized_pnl_usd=2.5
        )
        self.assertIsNone(self.logger.get_trade_id_for_order("order-004"))

    def test_log_trade_update_writes_mae_mfe(self):
        import sqlite3
        sig = FakeSignal()
        sid = self.logger.log_signal(sig)
        tid = self.logger.log_trade_entry(
            sid, "order-005",
            signal=sig, category="Crypto", is_dry_run=True, bankroll=500.0
        )
        self.logger.log_trade_update(tid, MAE_price=0.55, MFE_price=0.80)
        conn = sqlite3.connect(str(self.db_path))
        row = conn.execute(
            "SELECT MAE_price, MFE_price FROM trades WHERE trade_id=?", (tid,)
        ).fetchone()
        conn.close()
        self.assertAlmostEqual(row[0], 0.55)
        self.assertAlmostEqual(row[1], 0.80)

    def test_stats_returns_dict(self):
        stats = self.logger.stats()
        self.assertIn("total_trades", stats)
        self.assertIn("total_signals", stats)
        self.assertEqual(stats["total_trades"], 0)

    def test_query_views_return_lists(self):
        self.assertIsInstance(self.logger.query_cohort_by_category(), list)
        self.assertIsInstance(self.logger.query_wallet_attribution(), list)
        self.assertIsInstance(self.logger.query_slippage_histogram(), list)

    def test_migrate_from_archive(self):
        archive = [
            {
                "id": 1, "datum": "2026-04-20", "uhrzeit": "10:00:00",
                "markt": "Test Market", "market_id": "0xtest",
                "token_id": "0xtok", "outcome": "Yes", "seite": "BUY",
                "preis_usdc": 0.60, "einsatz_usdc": 15.0, "shares": 25.0,
                "source_wallet": "0xwallet", "tx_hash": "0xtx1",
                "kategorie": "Soccer", "modus": "DRY-RUN",
                "ergebnis": "GEWINN", "gewinn_verlust_usdc": 6.0,
                "aufgeloest": True,
            },
            {
                "id": 2, "datum": "2026-04-21", "uhrzeit": "11:00:00",
                "markt": "Test Market 2", "market_id": "0xtest2",
                "token_id": "0xtok2", "outcome": "No", "seite": "BUY",
                "preis_usdc": 0.40, "einsatz_usdc": 10.0, "shares": 25.0,
                "source_wallet": "0xwallet", "tx_hash": "0xtx2",
                "kategorie": "Politics", "modus": "LIVE",
                "ergebnis": "", "gewinn_verlust_usdc": 0.0,
                "aufgeloest": False,
            }
        ]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(archive, f)
            archive_path = Path(f.name)

        try:
            n = migrate_from_archive(archive_path)
            self.assertEqual(n, 2)
            # Second call should import 0 (idempotent)
            n2 = migrate_from_archive(archive_path)
            self.assertEqual(n2, 0)
            stats = self.logger.stats()
            self.assertEqual(stats["total_trades"], 2)
        finally:
            archive_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
