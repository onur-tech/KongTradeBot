"""
Tracked Per-Kategorie-WR pro Whale.
Signal nur akzeptiert wenn Whale in Kategorie >= CATEGORY_THRESHOLD WR (default 65%).
"""
from __future__ import annotations

import sqlite3
from enum import Enum


class MarketCategory(str, Enum):
    POLITICS = "politics"
    SPORTS = "sports"
    CRYPTO = "crypto"
    WEATHER = "weather"
    MENTIONS = "mentions"
    OTHER = "other"


def classify_market(question: str, tags: list = None) -> MarketCategory:
    """Keyword-based classifier. Simple, deterministic, question takes priority over tags."""
    q = (question or "").lower()
    tag_set = {t.lower() for t in (tags or [])}

    # Question-based matching (priority order)
    if any(k in q for k in ["election", "president", "senate", "trump", "biden", "putin",
                              "resign", "prime minister", "parliament", "govern"]):
        return MarketCategory.POLITICS
    if any(k in q for k in ["vs.", "vs ", "wins on", "championship", "nba", "nfl", "fifa",
                              "nhl", "mlb", "soccer", "football", "basketball", "tennis",
                              "golf", "game", "match", "score", "tournament"]):
        return MarketCategory.SPORTS
    if any(k in q for k in ["bitcoin", "ethereum", "btc", "eth", "sol", "crypto",
                              "blockchain", "defi", "nft", "token"]):
        return MarketCategory.CRYPTO
    if any(k in q for k in ["temperature", "rainfall", "hurricane", "storm",
                              "celsius", "fahrenheit", "weather", "flood"]):
        return MarketCategory.WEATHER
    if any(k in q for k in ["mention", "tweet", "post", "followers"]):
        return MarketCategory.MENTIONS

    # Tag-based fallback
    if tag_set & {"politics", "election"}:
        return MarketCategory.POLITICS
    if tag_set & {"sports"}:
        return MarketCategory.SPORTS
    if tag_set & {"crypto"}:
        return MarketCategory.CRYPTO
    if tag_set & {"weather"}:
        return MarketCategory.WEATHER

    return MarketCategory.OTHER


class WalletCategoryTracker:
    CATEGORY_THRESHOLD: float = 0.65  # whale must have ≥65% WR in category
    MIN_TRADES_IN_CATEGORY: int = 5

    def __init__(self, db_path: str = "data/kongtrade.db"):
        self.db_path = db_path

    def get_category_wr(self, wallet_address: str, category: MarketCategory) -> tuple[float, int]:
        """Returns (win_rate, n_trades) for wallet in category."""
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                row = conn.execute(
                    """SELECT COUNT(*) as n,
                              AVG(CASE WHEN pnl > 0 THEN 1.0 ELSE 0.0 END) as wr
                    FROM trades
                    WHERE whale_address = ? AND market_category = ?""",
                    (wallet_address.lower(), category.value),
                ).fetchone()
                return (row[1] or 0.0, row[0] or 0)
            except sqlite3.OperationalError:
                return (0.0, 0)
            finally:
                conn.close()
        except Exception:
            return (0.0, 0)

    def should_accept_signal(self, wallet_address: str, category: MarketCategory) -> bool:
        """True when whale has enough wins in this category (or insufficient data → benefit of doubt)."""
        wr, n = self.get_category_wr(wallet_address, category)
        if n < self.MIN_TRADES_IN_CATEGORY:
            return True  # too little data → accept
        return wr >= self.CATEGORY_THRESHOLD
