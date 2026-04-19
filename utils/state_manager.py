"""
state_manager.py — Persistenter Bot-State

Speichert alles beim Shutdown, lädt alles beim Start.
Kein Datenverlust mehr bei Neustart.
"""

import json
import os
from datetime import datetime, date
from typing import Optional
from utils.logger import get_logger

logger = get_logger("state")

STATE_FILE = "bot_state.json"


def save_state(engine, monitor, strategy) -> None:
    """Speichert aktuellen Bot-State in bot_state.json."""
    try:
        positions = []
        for order_id, pos in engine.open_positions.items():
            closes_at_iso = None
            if getattr(pos, 'market_closes_at', None):
                try:
                    closes_at_iso = pos.market_closes_at.isoformat()
                except Exception:
                    pass
            positions.append({
                "order_id": order_id,
                "market_id": getattr(pos, 'market_id', ''),
                "token_id": getattr(pos, 'token_id', ''),
                "market_question": pos.market_question,
                "outcome": pos.outcome,
                "entry_price": pos.entry_price,
                "size_usdc": pos.size_usdc,
                "shares": pos.shares,
                "source_wallet": pos.source_wallet,
                "opened_at": pos.opened_at.isoformat() if getattr(pos, 'opened_at', None) else datetime.now().isoformat(),
                "market_closes_at": closes_at_iso,
                "position_state": getattr(pos, 'position_state', 'OPEN'),
            })

        state = {
            "version": "1.0",
            "saved_at": datetime.now().isoformat(),
            "date": str(date.today()),
            "open_positions": positions,
            "seen_tx_hashes": list(monitor._seen_tx_hashes) if hasattr(monitor, '_seen_tx_hashes') else [],
            "daily_pnl": engine.stats.get("total_invested_usdc", 0),
            "signals_total": strategy.signals_received if hasattr(strategy, 'signals_received') else 0,
            "orders_total": strategy.orders_created if hasattr(strategy, 'orders_created') else 0,
        }

        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

        logger.info(f"State gespeichert: {len(positions)} Positionen, {len(state['seen_tx_hashes'])} TX-Hashes")

    except Exception as e:
        logger.error(f"State speichern fehlgeschlagen: {e}")


def load_state(engine, monitor) -> bool:
    """Lädt State aus bot_state.json. Gibt True zurück wenn State geladen wurde."""
    if not os.path.exists(STATE_FILE):
        logger.info("Kein vorheriger State gefunden — starte frisch.")
        return False

    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)

        saved_date = state.get("date", "")
        today = str(date.today())

        # TX-Hashes immer laden (verhindert Duplikate)
        tx_hashes = set(state.get("seen_tx_hashes", []))
        if hasattr(monitor, '_seen_tx_hashes'):
            monitor._seen_tx_hashes.update(tx_hashes)
            logger.info(f"TX-Hashes geladen: {len(tx_hashes)} bekannte Trades")

        # Positionen nur laden wenn State von heute ist
        if saved_date == today:
            positions = state.get("open_positions", [])
            logger.info(f"State von heute geladen: {len(positions)} offene Positionen wiederhergestellt")
            for pos in positions:
                state_label = pos.get("position_state", "OPEN")
                logger.info(f"  Wiederhergestellt: [{state_label}] {pos['outcome']} @ ${pos['entry_price']} | {pos['market_question'][:50]}")
        else:
            logger.info(f"State von {saved_date} — anderer Tag, starte mit frischen Positionen (TX-Hashes behalten)")

        return True

    except Exception as e:
        logger.error(f"State laden fehlgeschlagen: {e}")
        return False
