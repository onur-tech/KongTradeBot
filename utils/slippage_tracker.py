"""
utils/slippage_tracker.py — Slippage pro Trade loggen

Schreibt Einträge nach data/slippage_log.jsonl (append-only).

Slippage = our_price - whale_price (in Cent).
Positiv = wir zahlen mehr als der Whale (Kosten).
In DRY_RUN mode ist filled_price == whale_price → Slippage = 0¢.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DATA_DIR   = Path(__file__).parent.parent / "data"
SLIPPAGE_LOG = DATA_DIR / "slippage_log.jsonl"

ALERT_THRESHOLD_CENTS = 6.0  # Telegram-Alert bei täglichem Mittelwert > 6¢


def log_slippage(
    whale_price: float,
    our_price: float,
    market: str,
    market_id: str,
    outcome: str,
    whale_wallet: str,
    our_size_usdc: float,
    category: str,
    is_multi_signal: bool,
    detection_lag_seconds: float,
    dry_run: bool,
) -> dict:
    """
    Berechnet und loggt Slippage für einen Trade.

    whale_price: Preis des Whales (0.0–1.0)
    our_price:   Unser Fill-Preis (0.0–1.0), in DRY_RUN == whale_price
    detection_lag_seconds: Zeit von Signal-Erkennung bis Order-Submit
    """
    if whale_price <= 0:
        return {}

    delta_cents = (our_price - whale_price) * 100
    delta_bps   = ((our_price - whale_price) / whale_price) * 10_000

    entry = {
        "timestamp":              datetime.now(timezone.utc).isoformat(),
        "market":                 market[:100],
        "market_id":              market_id,
        "outcome":                outcome,
        "whale_wallet":           whale_wallet[:20] + "...",
        "whale_price":            round(whale_price, 4),
        "our_price":              round(our_price, 4),
        "delta_cents":            round(delta_cents, 3),
        "delta_bps":              round(delta_bps, 1),
        "our_size_usdc":          round(our_size_usdc, 4),
        "detection_lag_seconds":  round(detection_lag_seconds, 1),
        "category":               category,
        "is_multi_signal":        is_multi_signal,
        "dry_run":                dry_run,
    }

    _append(entry)
    return entry


def _append(entry: dict) -> None:
    try:
        DATA_DIR.mkdir(exist_ok=True)
        with SLIPPAGE_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        import logging
        logging.getLogger("slippage_tracker").warning(f"Slippage-Log Schreibfehler: {e}")


def load_entries(date_filter: Optional[str] = None) -> list:
    """
    Lädt alle Slippage-Einträge (optional gefiltert nach Datum YYYY-MM-DD).
    Überspringt DRY_RUN-Einträge da die immer 0¢ haben.
    """
    if not SLIPPAGE_LOG.exists():
        return []
    entries = []
    try:
        for line in SLIPPAGE_LOG.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                if e.get("dry_run"):
                    continue  # Dry-Run hat immer 0¢ Slippage → ignorieren
                if date_filter and not e.get("timestamp", "").startswith(date_filter):
                    continue
                entries.append(e)
            except json.JSONDecodeError:
                pass
    except Exception:
        pass
    return entries
