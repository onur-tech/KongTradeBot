#!/usr/bin/env python3
"""
T-M06 Phase 2: Täglicher Abgleich Archive vs Polymarket Data-API.
Sendet Reconciliation-Report via Telegram täglich 21:00 (nach Daily-Summary 20:00).

Archiv-Format: trades_archive.json (JSON-Array, deutsche Feldnamen)
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BASE_DIR     = Path(__file__).resolve().parent.parent
ARCHIVE_PATH = BASE_DIR / "trades_archive.json"
PROXY        = os.getenv("POLYMARKET_ADDRESS", "")
DATA_API     = "https://data-api.polymarket.com"


def _load_env():
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def get_onchain_trades(days_back: int = 1) -> list:
    proxy = os.getenv("POLYMARKET_ADDRESS", "")
    if not proxy:
        return []
    since = int((datetime.now(timezone.utc) - timedelta(days=days_back)).timestamp())
    try:
        r = requests.get(
            f"{DATA_API}/activity?user={proxy}&limit=500",
            timeout=10,
            headers={"User-Agent": "KongTradeBot/2.0"},
        )
        if r.ok:
            return [t for t in r.json() if t.get("timestamp", 0) > since]
    except Exception as e:
        print(f"[reconcile] API-Fehler: {e}", file=sys.stderr)
    return []


def get_archive_trades(days_back: int = 1) -> list:
    if not ARCHIVE_PATH.exists():
        return []
    try:
        with open(ARCHIVE_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    since = (datetime.now() - timedelta(days=days_back)).date().isoformat()
    result = []
    for t in data:
        datum = t.get("datum", "")
        if datum and datum >= since:
            result.append(t)
    return result


def reconcile(days_back: int = 1) -> tuple:
    onchain = get_onchain_trades(days_back)
    archive = get_archive_trades(days_back)

    onchain_ids = {
        t.get("transactionHash", "")
        for t in onchain
        if t.get("transactionHash")
    }
    archive_ids = {
        t.get("tx_hash", "")
        for t in archive
        if t.get("tx_hash") and not t["tx_hash"].startswith(("pending_", "exit_", "RECOVERED"))
    }

    ghost_trades = [
        t for t in archive
        if t.get("tx_hash", "").startswith(("pending_", "exit_", "RECOVERED"))
        or not t.get("tx_hash")
    ]
    matched = [
        t for t in archive
        if t.get("tx_hash") and not t["tx_hash"].startswith(("pending_", "exit_", "RECOVERED"))
    ]
    missing_from_archive = [
        t for t in onchain
        if t.get("transactionHash") and t["transactionHash"] not in archive_ids
    ]

    total_archive = len(archive)
    drift_pct = len(ghost_trades) / max(total_archive, 1) * 100

    # Overall stats (alle Einträge)
    try:
        with open(ARCHIVE_PATH, encoding="utf-8") as f:
            all_data = json.load(f)
    except Exception:
        all_data = []
    all_ghost = sum(
        1 for t in all_data
        if not t.get("tx_hash") or str(t.get("tx_hash", "")).startswith(("pending_", "exit_", "RECOVERED"))
    )
    all_drift = all_ghost / max(len(all_data), 1) * 100

    report = (
        f"📊 *Reconciliation Report {datetime.now().strftime('%d.%m.%Y')}*\n\n"
        f"Letzte {days_back}d — Archive: {total_archive} | On-Chain: {len(onchain)}\n\n"
        f"✅ Matched (echte tx_hash): {len(matched)}\n"
        f"👻 Ghost-Trades (kein/fake TX): {len(ghost_trades)}\n"
        f"❓ Fehlt im Archive: {len(missing_from_archive)}\n\n"
        f"Drift-Quote ({days_back}d): {drift_pct:.1f}%\n"
        f"Drift-Quote gesamt: {all_drift:.1f}% (Ziel: <5% neue Trades)"
    )
    return report, ghost_trades, missing_from_archive


if __name__ == "__main__":
    _load_env()
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    report, ghosts, missing = reconcile(days)
    print(report)
    if ghosts:
        print(f"\nGhost-Trades ({min(5, len(ghosts))} von {len(ghosts)} gezeigt):")
        for t in ghosts[:5]:
            print(f"  {t.get('datum','?')} {t.get('uhrzeit','?')[:5]} | "
                  f"{t.get('tx_hash','NO_TX')[:20]} | {t.get('markt','')[:40]}")
    if missing:
        print(f"\nFehlen im Archive: {len(missing)} On-Chain Trades")
        for t in missing[:3]:
            print(f"  {t.get('transactionHash','?')[:20]}... | {t.get('type','?')}")
