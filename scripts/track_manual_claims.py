#!/usr/bin/env python3
"""
T-M06 Phase 3: Manueller Claim-Tracker.
GET /positions?user=PROXY&closed=true → prüfe gegen Archive
→ fehlende Positionen als MANUAL_CLAIM ins Archive ergänzen.

Archiv-Format: trades_archive.json (JSON-Array, deutsche Feldnamen)
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

BASE_DIR     = Path(__file__).resolve().parent.parent
ARCHIVE_PATH = BASE_DIR / "trades_archive.json"
DATA_API     = "https://data-api.polymarket.com"


def _load_env():
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def get_closed_positions(proxy: str) -> list:
    try:
        r = requests.get(
            f"{DATA_API}/positions?user={proxy}&closed=true&limit=500",
            timeout=10,
            headers={"User-Agent": "KongTradeBot/2.0"},
        )
        return r.json() if r.ok else []
    except Exception as e:
        print(f"[track_claims] API-Fehler: {e}", file=sys.stderr)
        return []


def get_archive_market_ids() -> set:
    if not ARCHIVE_PATH.exists():
        return set()
    try:
        with open(ARCHIVE_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return set()
    return {t.get("market_id", "") for t in data if t.get("market_id")}


def get_next_id() -> int:
    if not ARCHIVE_PATH.exists():
        return 1
    try:
        with open(ARCHIVE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return max((t.get("id", 0) for t in data), default=0) + 1
    except Exception:
        return 1


def track_manual_claims(proxy: str) -> int:
    closed = get_closed_positions(proxy)
    if not closed:
        print("[track_claims] Keine closed Positionen von API (oder API nicht erreichbar)")
        return 0

    known_ids = get_archive_market_ids()
    missing = [p for p in closed if p.get("conditionId", "") not in known_ids]

    if not missing:
        print(f"[track_claims] Keine fehlenden Claims. {len(closed)} closed Positionen geprüft.")
        return 0

    # Load existing archive
    try:
        with open(ARCHIVE_PATH, encoding="utf-8") as f:
            archive_data = json.load(f)
    except Exception:
        archive_data = []

    next_id = get_next_id()
    added = 0
    now = datetime.now()

    for p in missing:
        pnl = float(p.get("cashPnl", 0) or 0)
        entry = {
            "id": next_id,
            "datum": now.strftime("%Y-%m-%d"),
            "uhrzeit": now.strftime("%H:%M:%S"),
            "markt": (p.get("title") or p.get("question") or "")[:100],
            "market_id": p.get("conditionId", ""),
            "token_id": p.get("asset_id") or p.get("tokenId") or "",
            "outcome": p.get("outcome", ""),
            "seite": "CLAIM",
            "preis_usdc": 1.0 if pnl > 0 else 0.0,
            "einsatz_usdc": float(p.get("initialValue") or p.get("cost") or 0),
            "shares": float(p.get("size") or p.get("shares") or 0),
            "source_wallet": "[manual-claim]",
            "tx_hash": "",
            "kategorie": "MANUAL_CLAIM",
            "modus": "LIVE",
            "ergebnis": "GEWINN" if pnl > 0 else "VERLUST",
            "gewinn_verlust_usdc": round(pnl, 4),
            "aufgeloest": True,
            "note": "Manuell via Polymarket UI geclaimed — nachtraeglich erfasst (T-M06 Phase 3)",
        }
        archive_data.append(entry)
        print(f"  [ADDED] {entry['markt'][:55]} → PnL ${entry['gewinn_verlust_usdc']:.2f}")
        next_id += 1
        added += 1

    if added > 0:
        with open(ARCHIVE_PATH, "w", encoding="utf-8") as f:
            json.dump(archive_data, f, indent=2, ensure_ascii=False)
        print(f"\n✅ {added} Manual Claim(s) ins Archive geschrieben")

    return added


if __name__ == "__main__":
    _load_env()
    proxy = os.getenv("POLYMARKET_ADDRESS", "")
    if not proxy:
        print("FEHLER: POLYMARKET_ADDRESS nicht gesetzt", file=sys.stderr)
        sys.exit(1)
    print(f"Checking manual claims for proxy: {proxy[:16]}...")
    n = track_manual_claims(proxy)
    if n == 0:
        print("Keine fehlenden Claims gefunden.")
