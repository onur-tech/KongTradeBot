"""
Überwacht Wallet-Performance über rolling 30-day Window.
Reduziert Wallet-Multiplier automatisch wenn Wallet schlechter wird.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass
class WalletDecayDecision:
    wallet_address: str
    original_multiplier: float
    adjusted_multiplier: float
    reason: str
    stats: dict


class WalletDecayMonitor:
    """
    Decay rules (evaluated in order, first match applies):
    - trades_30d < 5    : no change (insufficient data)
    - roi_30d < -20%   : multiplier × 0.2  [hard downgrade]
    - roi_30d < -10%   : multiplier × 0.5
    - wr_30d  < 0.40   : multiplier × 0.5
    - else             : multiplier unchanged (healthy)
    """

    def __init__(self, db_path: str = "data/kongtrade.db"):
        self.db_path = db_path

    def evaluate(self, wallet_address: str, current_multiplier: float) -> WalletDecayDecision:
        stats = self._load_30d_stats(wallet_address)

        if stats["trades_30d"] < 5:
            return WalletDecayDecision(
                wallet_address, current_multiplier, current_multiplier,
                "insufficient_data", stats
            )

        if stats["roi_30d"] < -0.20:
            adj = max(0.0, current_multiplier * 0.2)
            return WalletDecayDecision(
                wallet_address, current_multiplier, adj,
                "hard_downgrade_roi_below_minus20", stats
            )

        if stats["roi_30d"] < -0.10:
            adj = max(0.0, current_multiplier * 0.5)
            return WalletDecayDecision(
                wallet_address, current_multiplier, adj,
                "soft_downgrade_roi_below_minus10", stats
            )

        if stats["wr_30d"] < 0.40:
            adj = max(0.0, current_multiplier * 0.5)
            return WalletDecayDecision(
                wallet_address, current_multiplier, adj,
                "soft_downgrade_wr_below_40", stats
            )

        return WalletDecayDecision(
            wallet_address, current_multiplier, current_multiplier,
            "healthy", stats
        )

    def _load_30d_stats(self, wallet_address: str) -> dict:
        """Load stats from trade_logger DB. Schema-safe: tries multiple column names."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                row = conn.execute(
                    """SELECT
                        COUNT(*) as n,
                        AVG(CASE WHEN pnl > 0 THEN 1.0 ELSE 0.0 END) as wr,
                        AVG(pnl_pct) as roi_avg
                    FROM trades
                    WHERE whale_address = ? AND entry_time > ?""",
                    (wallet_address.lower(), cutoff),
                ).fetchone()
                return {
                    "trades_30d": row["n"] or 0,
                    "wr_30d": row["wr"] or 0.0,
                    "roi_30d": row["roi_avg"] or 0.0,
                }
            except sqlite3.OperationalError:
                return {"trades_30d": 0, "wr_30d": 0.0, "roi_30d": 0.0}
            finally:
                conn.close()
        except Exception:
            return {"trades_30d": 0, "wr_30d": 0.0, "roi_30d": 0.0}
