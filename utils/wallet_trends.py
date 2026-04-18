"""
wallet_trends.py — Trend-Analyse für historische Wallet-Scout-Daten.

Liest aus wallet_scout.db (SQLite) und berechnet:
- Zeitreihen pro Wallet (Rank/ROI/WR über N Tage)
- Decay-Kandidaten (Rank gefallen)
- Neue Einsteiger (noch nicht in früheren Scans)
- Rising Stars (ROI/WR verbessert)
"""

import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

from utils.logger import get_logger

logger = get_logger("wallet_trends")

SCOUT_DB_FILE = os.getenv("WALLET_SCOUT_DB", "data/wallet_scout.db")


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(SCOUT_DB_FILE)
    c.row_factory = sqlite3.Row
    return c


def get_wallet_trend(wallet_address: str, days: int = 14) -> list:
    """
    Zeitreihe der Rank/ROI/WR über N Tage für eine Wallet.
    Gibt Liste von Dicts sortiert nach scan_date aufsteigend zurück.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        with _conn() as c:
            rows = c.execute(
                """SELECT scan_date, source, rank, win_rate, roi_pct, pnl_usd, alias
                   FROM wallet_scout_daily
                   WHERE wallet_address = ? AND scan_date >= ?
                   ORDER BY scan_date ASC""",
                (wallet_address.lower(), cutoff),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning(f"get_wallet_trend fehlgeschlagen: {e}")
        return []


def get_decay_candidates(
    source: str, days: int = 7, rank_drop_threshold: int = 10
) -> list:
    """
    Wallets die in den letzten N Tagen mehr als rank_drop_threshold Plätze
    gefallen sind (ältester Rank vs. neuester Rank im Zeitfenster).
    Gibt Liste von Dicts: {wallet_address, alias, rank_old, rank_new, drop}.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        with _conn() as c:
            rows = c.execute(
                """SELECT wallet_address, alias,
                          MIN(rank) AS rank_best,
                          MAX(rank) AS rank_worst,
                          MAX(rank) - MIN(rank) AS rank_delta,
                          MIN(scan_date) AS first_date,
                          MAX(scan_date) AS last_date
                   FROM wallet_scout_daily
                   WHERE source = ? AND scan_date >= ? AND rank IS NOT NULL
                   GROUP BY wallet_address
                   HAVING rank_delta >= ?
                   ORDER BY rank_delta DESC""",
                (source, cutoff, rank_drop_threshold),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning(f"get_decay_candidates fehlgeschlagen: {e}")
        return []


def get_new_entries(source: str, days: int = 7) -> list:
    """
    Wallets die im letzten Scan-Tag vorhanden sind aber NICHT in
    früheren Scans innerhalb der letzten N Tage.
    Gibt Liste von Dicts: {wallet_address, alias, rank, win_rate, pnl_usd}.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        with _conn() as c:
            # Wallets im neuesten Scan
            latest_date = c.execute(
                "SELECT MAX(scan_date) FROM wallet_scout_daily WHERE source = ?",
                (source,),
            ).fetchone()[0]
            if not latest_date:
                return []
            current = c.execute(
                """SELECT wallet_address, alias, rank, win_rate, pnl_usd
                   FROM wallet_scout_daily
                   WHERE source = ? AND scan_date = ?""",
                (source, latest_date),
            ).fetchall()
            # Wallets in früheren Scans
            historic_addrs = {
                r[0]
                for r in c.execute(
                    """SELECT DISTINCT wallet_address FROM wallet_scout_daily
                       WHERE source = ? AND scan_date >= ? AND scan_date < ?""",
                    (source, cutoff, latest_date),
                ).fetchall()
            }
        return [dict(r) for r in current if r["wallet_address"] not in historic_addrs]
    except Exception as e:
        logger.warning(f"get_new_entries fehlgeschlagen: {e}")
        return []


def get_rising_stars(
    source: str, days: int = 7, roi_improvement_pct: float = 20.0
) -> list:
    """
    Wallets die innerhalb von N Tagen ihre Win-Rate um roi_improvement_pct
    Prozentpunkte (absolut) verbessert haben (ältester vs. neuester Wert).
    Gibt Liste von Dicts: {wallet_address, alias, wr_old, wr_new, improvement}.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        with _conn() as c:
            # Ältesten und neuesten WR-Wert pro Wallet im Fenster
            rows = c.execute(
                """SELECT w1.wallet_address, w1.alias,
                          w1.win_rate AS wr_old, w2.win_rate AS wr_new,
                          (w2.win_rate - w1.win_rate) * 100 AS improvement
                   FROM wallet_scout_daily w1
                   JOIN wallet_scout_daily w2
                     ON w1.wallet_address = w2.wallet_address
                    AND w1.source = w2.source
                   WHERE w1.source = ?
                     AND w1.scan_date = (
                         SELECT MIN(scan_date) FROM wallet_scout_daily
                         WHERE wallet_address = w1.wallet_address
                           AND source = ? AND scan_date >= ?)
                     AND w2.scan_date = (
                         SELECT MAX(scan_date) FROM wallet_scout_daily
                         WHERE wallet_address = w1.wallet_address
                           AND source = ?)
                     AND w2.win_rate IS NOT NULL AND w1.win_rate IS NOT NULL
                   HAVING improvement >= ?
                   ORDER BY improvement DESC""",
                (source, source, cutoff, source, roi_improvement_pct),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning(f"get_rising_stars fehlgeschlagen: {e}")
        return []


def get_top_stable(source: str, days: int = 7, top_n: int = 5) -> list:
    """Wallets die in allen Scans der letzten N Tage unter den Top-N waren."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        with _conn() as c:
            scan_count = c.execute(
                "SELECT COUNT(DISTINCT scan_date) FROM wallet_scout_daily WHERE source = ? AND scan_date >= ?",
                (source, cutoff),
            ).fetchone()[0]
            if scan_count < 2:
                return []
            rows = c.execute(
                """SELECT wallet_address, alias, AVG(rank) AS avg_rank,
                          AVG(win_rate) AS avg_wr, COUNT(*) AS appearances
                   FROM wallet_scout_daily
                   WHERE source = ? AND scan_date >= ? AND rank <= ?
                   GROUP BY wallet_address
                   HAVING appearances = ?
                   ORDER BY avg_rank ASC""",
                (source, cutoff, top_n, scan_count),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning(f"get_top_stable fehlgeschlagen: {e}")
        return []
