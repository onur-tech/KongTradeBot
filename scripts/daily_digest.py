"""
scripts/daily_digest.py — Täglicher Abend-Digest 22:00 Berlin
Sendet kompakte Tages-Zusammenfassung an alle Telegram-Chats.
"""
import asyncio
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

import aiohttp

TOKEN    = os.getenv("TELEGRAM_TOKEN", "")
RAW_IDS  = os.getenv("TELEGRAM_CHAT_IDS", "")
CHAT_IDS = [cid.strip() for cid in RAW_IDS.split(",") if cid.strip()]

ARCHIVE_FILE = BASE_DIR / "trades_archive.json"
STATE_FILE   = BASE_DIR / "bot_state.json"


def _load_archive() -> list:
    if not ARCHIVE_FILE.exists():
        return []
    try:
        return json.loads(ARCHIVE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _build_digest() -> str:
    today_str = date.today().isoformat()
    trades = _load_archive()

    today_trades = [t for t in trades if t.get("datum", "") == today_str]
    resolved_today = [t for t in today_trades if t.get("aufgeloest")]
    won  = [t for t in resolved_today if t.get("ergebnis") == "GEWINN"]
    lost = [t for t in resolved_today if t.get("ergebnis") == "VERLUST"]
    pnl  = sum(float(t.get("gewinn_verlust_usdc", 0) or 0) for t in resolved_today)

    # Gesamt-Archiv
    all_resolved = [t for t in trades if t.get("aufgeloest")]
    all_won      = [t for t in all_resolved if t.get("ergebnis") == "GEWINN"]
    win_rate     = round(len(all_won) / len(all_resolved) * 100, 1) if all_resolved else 0
    total_pnl    = sum(float(t.get("gewinn_verlust_usdc", 0) or 0) for t in all_resolved)
    wr_icon      = "🟢" if win_rate >= 55 else "🟡" if win_rate >= 50 else "🔴"

    # Offene Positionen
    state = _load_state()
    positions = state.get("open_positions", [])
    if isinstance(positions, dict):
        positions = list(positions.values())
    open_count    = len(positions)
    open_invested = sum(float(p.get("size_usdc", 0) or 0) for p in positions)

    pnl_sign  = "+" if pnl >= 0 else ""
    tp_sign   = "+" if total_pnl >= 0 else ""
    pnl_icon  = "🟢" if pnl >= 0 else "🔴"
    tp_icon   = "🟢" if total_pnl >= 0 else "🔴"

    lines = [
        f"🌙 <b>ABEND-DIGEST — {date.today().strftime('%d.%m.%Y')}</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📋 Trades heute: <b>{len(today_trades)}</b>",
        f"🎯 Aufgelöst: <b>{len(resolved_today)}</b>  ✅{len(won)} / ❌{len(lost)}",
        f"{pnl_icon} P&L heute: <b>{pnl_sign}${pnl:.2f} USDC</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"💼 Offen: <b>{open_count} Positionen</b> | <b>${open_invested:.2f} USDC</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"{wr_icon} Win Rate gesamt: <b>{win_rate}%</b> ({len(all_won)}W / {len(all_resolved)-len(all_won)}L)",
        f"{tp_icon} P&L gesamt: <b>{tp_sign}${total_pnl:.2f} USDC</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        "🤖 Bot läuft — gute Nacht Brrudi! 🌙",
    ]
    return "\n".join(lines)


async def send_digest():
    if not TOKEN or not CHAT_IDS:
        print("[Digest] Kein Token / keine Chat-IDs konfiguriert")
        return

    text = _build_digest()
    async with aiohttp.ClientSession() as session:
        for chat_id in CHAT_IDS:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
            try:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    if r.status == 200:
                        print(f"[Digest] ✅ an {chat_id} gesendet")
                    else:
                        print(f"[Digest] ❌ Fehler {chat_id}: {await r.text()}")
            except Exception as e:
                print(f"[Digest] Fehler: {e}")


if __name__ == "__main__":
    asyncio.run(send_digest())
