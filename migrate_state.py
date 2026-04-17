"""
migrate_state.py — Einmalige Migration

Liest alle Trades aus trades_archive.json und erstellt
daraus eine vollständige bot_state.json mit allen offenen Positionen.

Einmalig ausführen: python migrate_state.py
"""

import json
import os
from datetime import datetime, date

TRADE_LOG_FILE = "trades_archive.json"
STATE_FILE = "bot_state.json"


def migrate():
    # trades_archive.json laden
    if not os.path.exists(TRADE_LOG_FILE):
        print(f"FEHLER: {TRADE_LOG_FILE} nicht gefunden!")
        return

    with open(TRADE_LOG_FILE, 'r', encoding='utf-8') as f:
        trades = json.load(f)

    print(f"Gefunden: {len(trades)} Trades in {TRADE_LOG_FILE}")

    # Nur nicht-aufgelöste Trades als offene Positionen übernehmen
    open_trades = [t for t in trades if not t.get("aufgeloest", False)]
    print(f"Davon offen (nicht aufgelöst): {len(open_trades)}")

    positions = []
    tx_hashes = []

    for i, trade in enumerate(open_trades):
        # Fake order_id aus Trade-ID generieren
        order_id = f"dry_run_{trade.get('id', i)}_{str(i).zfill(6)}"

        position = {
            "order_id": order_id,
            "market_id": "",
            "token_id": "",
            "market_question": trade.get("markt", ""),
            "outcome": trade.get("outcome", ""),
            "entry_price": float(trade.get("preis_usdc", 0)),
            "size_usdc": float(trade.get("einsatz_usdc", 0)),
            "shares": float(trade.get("shares", 0)),
            "source_wallet": trade.get("source_wallet", ""),
            "tx_hash_entry": trade.get("tx_hash", ""),
            "opened_at": f"{trade.get('datum', str(date.today()))}T{trade.get('uhrzeit', '00:00:00')}",
            "time_to_close_hours": 0,
        }
        positions.append(position)

        if trade.get("tx_hash"):
            tx_hashes.append(trade["tx_hash"])

    # Alle TX-Hashes aus ALLEN Trades sammeln (auch aufgelöste — für Duplikat-Schutz)
    all_tx_hashes = [t.get("tx_hash", "") for t in trades if t.get("tx_hash")]

    # bot_state.json erstellen
    state = {
        "version": "1.1",
        "saved_at": datetime.now().isoformat(),
        "date": str(date.today()),
        "open_positions": positions,
        "seen_tx_hashes": list(set(all_tx_hashes)),
        "dry_run_counter": len(trades),
        "signals_total": len(trades),
        "orders_total": len(trades),
    }

    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

    # Zusammenfassung
    total_invested = sum(float(p.get("size_usdc", 0)) for p in positions)

    print(f"\n✅ Migration erfolgreich!")
    print(f"   bot_state.json erstellt mit:")
    print(f"   → {len(positions)} offene Positionen")
    print(f"   → ${total_invested:.2f} USDC simuliert investiert")
    print(f"   → {len(all_tx_hashes)} TX-Hashes gespeichert")
    print(f"\nJetzt Bot starten: python main.py")
    print(f"Der Bot lädt alle {len(positions)} Positionen beim Start.")


if __name__ == "__main__":
    migrate()
