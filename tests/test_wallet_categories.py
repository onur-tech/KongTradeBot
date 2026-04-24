"""Tests for core/wallet_categories.py."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from core.wallet_categories import MarketCategory, WalletCategoryTracker, classify_market

WALLET = "0x" + "a" * 40


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_path(tmp_path) -> str:
    p = str(tmp_path / "cat_test.db")
    conn = sqlite3.connect(p)
    conn.execute("""
        CREATE TABLE trades (
            id INTEGER PRIMARY KEY,
            whale_address TEXT,
            market_category TEXT,
            pnl REAL
        )
    """)
    conn.commit()
    conn.close()
    return p


def _insert(db_path: str, wallet: str, category: str, pnl: float, n: int = 1):
    conn = sqlite3.connect(db_path)
    for _ in range(n):
        conn.execute(
            "INSERT INTO trades (whale_address, market_category, pnl) VALUES (?, ?, ?)",
            (wallet.lower(), category, pnl),
        )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# classify_market
# ---------------------------------------------------------------------------

def test_classify_politics_question():
    assert classify_market("Who will win the election?") == MarketCategory.POLITICS


def test_classify_politics_trump():
    assert classify_market("Will Trump resign in 2026?") == MarketCategory.POLITICS


def test_classify_sports_nba():
    assert classify_market("Will the Celtics win the NBA championship?") == MarketCategory.SPORTS


def test_classify_sports_vs():
    assert classify_market("Team A vs. Team B — who wins?") == MarketCategory.SPORTS


def test_classify_crypto_bitcoin():
    assert classify_market("Will Bitcoin reach $100k?") == MarketCategory.CRYPTO


def test_classify_crypto_eth():
    assert classify_market("ETH price above $5k?") == MarketCategory.CRYPTO


def test_classify_weather():
    assert classify_market("Will temperature exceed 40°C in Phoenix?") == MarketCategory.WEATHER


def test_classify_mentions():
    assert classify_market("How many tweet mentions will Elon get?") == MarketCategory.MENTIONS


def test_classify_other_fallback():
    assert classify_market("Some completely random market question") == MarketCategory.OTHER


def test_classify_tags_fallback_sports():
    """Tags used when question has no keywords."""
    result = classify_market("Random question", tags=["sports"])
    assert result == MarketCategory.SPORTS


def test_classify_tags_fallback_crypto():
    result = classify_market("Another random question", tags=["crypto"])
    assert result == MarketCategory.CRYPTO


def test_classify_question_overrides_tags():
    """Question keyword takes priority over tags."""
    result = classify_market("Bitcoin price prediction", tags=["sports"])
    assert result == MarketCategory.CRYPTO  # question wins


# ---------------------------------------------------------------------------
# WalletCategoryTracker.get_category_wr
# ---------------------------------------------------------------------------

def test_get_category_wr_empty(db_path):
    tracker = WalletCategoryTracker(db_path=db_path)
    wr, n = tracker.get_category_wr(WALLET, MarketCategory.SPORTS)
    assert n == 0
    assert wr == pytest.approx(0.0)


def test_get_category_wr_correct(db_path):
    _insert(db_path, WALLET, "sports", pnl=5.0, n=7)   # 7 wins
    _insert(db_path, WALLET, "sports", pnl=-3.0, n=3)  # 3 losses
    tracker = WalletCategoryTracker(db_path=db_path)
    wr, n = tracker.get_category_wr(WALLET, MarketCategory.SPORTS)
    assert n == 10
    assert wr == pytest.approx(0.70)


def test_get_category_wr_db_schema_error(tmp_path):
    db_path = str(tmp_path / "bad.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE other (x INTEGER)")
    conn.commit()
    conn.close()
    tracker = WalletCategoryTracker(db_path=db_path)
    wr, n = tracker.get_category_wr(WALLET, MarketCategory.SPORTS)
    assert wr == pytest.approx(0.0)
    assert n == 0


# ---------------------------------------------------------------------------
# WalletCategoryTracker.should_accept_signal
# ---------------------------------------------------------------------------

def test_should_accept_insufficient_trades(db_path):
    """< 5 trades in category → accept (benefit of doubt)."""
    _insert(db_path, WALLET, "sports", pnl=-5.0, n=4)
    tracker = WalletCategoryTracker(db_path=db_path)
    assert tracker.should_accept_signal(WALLET, MarketCategory.SPORTS) is True


def test_should_accept_high_wr(db_path):
    """70% WR in category with 10 trades → accept."""
    _insert(db_path, WALLET, "politics", pnl=1.0, n=7)
    _insert(db_path, WALLET, "politics", pnl=-1.0, n=3)
    tracker = WalletCategoryTracker(db_path=db_path)
    assert tracker.should_accept_signal(WALLET, MarketCategory.POLITICS) is True


def test_should_reject_low_wr(db_path):
    """55% WR in category with 10 trades → reject."""
    _insert(db_path, WALLET, "crypto", pnl=1.0, n=5)
    _insert(db_path, WALLET, "crypto", pnl=-1.0, n=5)
    tracker = WalletCategoryTracker(db_path=db_path)
    assert tracker.should_accept_signal(WALLET, MarketCategory.CRYPTO) is False


def test_should_accept_on_db_error(tmp_path):
    """DB error → treat as insufficient data → accept."""
    db_path = str(tmp_path / "bad.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE other (x INTEGER)")
    conn.commit()
    conn.close()
    tracker = WalletCategoryTracker(db_path=db_path)
    assert tracker.should_accept_signal(WALLET, MarketCategory.SPORTS) is True
