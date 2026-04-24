"""Tests for core/wallet_decay.py."""
from __future__ import annotations

import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from core.wallet_decay import WalletDecayDecision, WalletDecayMonitor

WALLET = "0x" + "a" * 40


# ---------------------------------------------------------------------------
# Fixture: in-memory / tmp DB
# ---------------------------------------------------------------------------

@pytest.fixture
def db_path(tmp_path) -> str:
    p = str(tmp_path / "test.db")
    conn = sqlite3.connect(p)
    conn.execute("""
        CREATE TABLE trades (
            id INTEGER PRIMARY KEY,
            whale_address TEXT,
            entry_time TEXT,
            pnl REAL,
            pnl_pct REAL
        )
    """)
    conn.commit()
    conn.close()
    return p


def _insert_trades(db_path: str, wallet: str, n: int, pnl: float, pnl_pct: float, days_ago: int = 5):
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    conn = sqlite3.connect(db_path)
    for _ in range(n):
        conn.execute(
            "INSERT INTO trades (whale_address, entry_time, pnl, pnl_pct) VALUES (?, ?, ?, ?)",
            (wallet.lower(), ts, pnl, pnl_pct),
        )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# 1. Insufficient data
# ---------------------------------------------------------------------------

def test_insufficient_data_empty_db(db_path):
    monitor = WalletDecayMonitor(db_path=db_path)
    d = monitor.evaluate(WALLET, 1.5)
    assert d.reason == "insufficient_data"
    assert d.adjusted_multiplier == pytest.approx(1.5)


def test_insufficient_data_four_trades(db_path):
    _insert_trades(db_path, WALLET, n=4, pnl=-10.0, pnl_pct=-0.50)
    monitor = WalletDecayMonitor(db_path=db_path)
    d = monitor.evaluate(WALLET, 2.0)
    assert d.reason == "insufficient_data"
    assert d.adjusted_multiplier == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# 2. Hard downgrade (ROI < -20%)
# ---------------------------------------------------------------------------

def test_hard_downgrade_roi_below_minus20(db_path):
    _insert_trades(db_path, WALLET, n=10, pnl=-5.0, pnl_pct=-0.30)
    monitor = WalletDecayMonitor(db_path=db_path)
    d = monitor.evaluate(WALLET, 1.0)
    assert d.reason == "hard_downgrade_roi_below_minus20"
    assert d.adjusted_multiplier == pytest.approx(0.2)


def test_hard_downgrade_multiplier_scales(db_path):
    _insert_trades(db_path, WALLET, n=10, pnl=-5.0, pnl_pct=-0.25)
    monitor = WalletDecayMonitor(db_path=db_path)
    d = monitor.evaluate(WALLET, 2.0)
    assert d.adjusted_multiplier == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# 3. Soft downgrade ROI < -10%
# ---------------------------------------------------------------------------

def test_soft_downgrade_roi_below_minus10(db_path):
    _insert_trades(db_path, WALLET, n=10, pnl=-3.0, pnl_pct=-0.15)
    monitor = WalletDecayMonitor(db_path=db_path)
    d = monitor.evaluate(WALLET, 2.0)
    assert d.reason == "soft_downgrade_roi_below_minus10"
    assert d.adjusted_multiplier == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# 4. Soft downgrade WR < 40%
# ---------------------------------------------------------------------------

def test_soft_downgrade_wr_below_40(db_path):
    # 3 wins, 7 losses → WR=30%, ROI positive (avoid roi rule triggering first)
    conn = sqlite3.connect(db_path)
    ts = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    for i in range(10):
        pnl = 2.0 if i < 3 else -0.1
        conn.execute(
            "INSERT INTO trades (whale_address, entry_time, pnl, pnl_pct) VALUES (?, ?, ?, ?)",
            (WALLET.lower(), ts, pnl, 0.05 if i < 3 else -0.01),
        )
    conn.commit()
    conn.close()

    monitor = WalletDecayMonitor(db_path=db_path)
    d = monitor.evaluate(WALLET, 1.5)
    assert d.reason == "soft_downgrade_wr_below_40"
    assert d.adjusted_multiplier == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# 5. Healthy (no downgrade)
# ---------------------------------------------------------------------------

def test_healthy_no_downgrade(db_path):
    # 8 wins, 2 losses, positive ROI
    conn = sqlite3.connect(db_path)
    ts = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    for i in range(10):
        pnl = 5.0 if i < 8 else -1.0
        conn.execute(
            "INSERT INTO trades (whale_address, entry_time, pnl, pnl_pct) VALUES (?, ?, ?, ?)",
            (WALLET.lower(), ts, pnl, 0.1 if i < 8 else -0.05),
        )
    conn.commit()
    conn.close()

    monitor = WalletDecayMonitor(db_path=db_path)
    d = monitor.evaluate(WALLET, 2.0)
    assert d.reason == "healthy"
    assert d.adjusted_multiplier == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# 6. Multiplier never negative
# ---------------------------------------------------------------------------

def test_multiplier_never_negative(db_path):
    _insert_trades(db_path, WALLET, n=20, pnl=-50.0, pnl_pct=-0.90)
    monitor = WalletDecayMonitor(db_path=db_path)
    d = monitor.evaluate(WALLET, 0.1)
    assert d.adjusted_multiplier >= 0.0


# ---------------------------------------------------------------------------
# 7. DB schema error → insufficient_data
# ---------------------------------------------------------------------------

def test_db_schema_error_insufficient_data(tmp_path):
    db_path = str(tmp_path / "bad_schema.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE other_table (x INTEGER)")
    conn.commit()
    conn.close()

    monitor = WalletDecayMonitor(db_path=db_path)
    d = monitor.evaluate(WALLET, 1.0)
    assert d.reason == "insufficient_data"
    assert d.adjusted_multiplier == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# 8. Case-insensitive wallet address
# ---------------------------------------------------------------------------

def test_case_insensitive_wallet(db_path):
    _insert_trades(db_path, WALLET.upper(), n=10, pnl=-5.0, pnl_pct=-0.30)
    monitor = WalletDecayMonitor(db_path=db_path)
    d = monitor.evaluate(WALLET.lower(), 1.0)
    # Should find the trades regardless of case stored
    assert d.stats["trades_30d"] == 10


# ---------------------------------------------------------------------------
# 9. Decision object structure complete
# ---------------------------------------------------------------------------

def test_decision_object_has_all_fields(db_path):
    monitor = WalletDecayMonitor(db_path=db_path)
    d = monitor.evaluate(WALLET, 1.0)
    assert hasattr(d, "wallet_address")
    assert hasattr(d, "original_multiplier")
    assert hasattr(d, "adjusted_multiplier")
    assert hasattr(d, "reason")
    assert hasattr(d, "stats")
    assert "trades_30d" in d.stats
    assert "wr_30d" in d.stats
    assert "roi_30d" in d.stats


# ---------------------------------------------------------------------------
# 10. Reason strings are consistent
# ---------------------------------------------------------------------------

def test_reason_strings_are_known_values(db_path):
    KNOWN_REASONS = {
        "insufficient_data",
        "hard_downgrade_roi_below_minus20",
        "soft_downgrade_roi_below_minus10",
        "soft_downgrade_wr_below_40",
        "healthy",
    }
    monitor = WalletDecayMonitor(db_path=db_path)
    d = monitor.evaluate(WALLET, 1.0)
    assert d.reason in KNOWN_REASONS


# ---------------------------------------------------------------------------
# 11. Only trades within 30 days are counted
# ---------------------------------------------------------------------------

def test_old_trades_ignored(db_path):
    # 10 old bad trades (35 days ago) + 6 recent good ones → should be healthy
    conn = sqlite3.connect(db_path)
    old_ts = (datetime.now(timezone.utc) - timedelta(days=35)).isoformat()
    recent_ts = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    for _ in range(10):
        conn.execute(
            "INSERT INTO trades (whale_address, entry_time, pnl, pnl_pct) VALUES (?, ?, ?, ?)",
            (WALLET.lower(), old_ts, -20.0, -0.50),
        )
    for _ in range(6):
        conn.execute(
            "INSERT INTO trades (whale_address, entry_time, pnl, pnl_pct) VALUES (?, ?, ?, ?)",
            (WALLET.lower(), recent_ts, 5.0, 0.10),
        )
    conn.commit()
    conn.close()

    monitor = WalletDecayMonitor(db_path=db_path)
    d = monitor.evaluate(WALLET, 1.0)
    assert d.stats["trades_30d"] == 6  # only recent trades
    assert d.reason == "healthy"
