#!/usr/bin/env python3
"""
Wallet Check — Weekly Decay Score Report
==========================================
Liest data/wallet_performance.json und sendet
Telegram-Report mit Decay-Kandidaten und Top-Wallets.

Verwendung:
  python3 scripts/wallet_check.py
  python3 scripts/wallet_check.py --dry-run   (kein Telegram)
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

# Root-Pfad hinzufügen
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

WALLET_PERF_FILE = ROOT / "data" / "wallet_performance.json"


def load_wallet_data() -> dict:
    if not WALLET_PERF_FILE.exists():
        return {"wallets": {}}
    try:
        return json.loads(WALLET_PERF_FILE.read_text())
    except Exception as e:
        print(f"[WalletCheck] Fehler beim Laden: {e}")
        return {"wallets": {}}


def analyze_wallets(data: dict) -> dict:
    """Analysiert alle Wallets und erstellt Bericht."""
    wallets = data.get("wallets", {})
    if not wallets:
        return {
            "total_wallets": 0,
            "stars": [],
            "reliable": [],
            "neutral": [],
            "decaying": [],
            "toxic": [],
            "total_pnl": 0.0,
        }

    stars, reliable, neutral, decaying, toxic = [], [], [], [], []

    for wallet, w in wallets.items():
        total = w.get("total_trades", 0)
        if total == 0:
            continue
        wr = w.get("wins", 0) / total
        recent = w.get("recent_outcomes", [])[-10:]
        recent_wr = sum(1 for x in recent if x) / max(len(recent), 1) if recent else wr

        entry = {
            "wallet": wallet,
            "alias": w.get("alias", wallet[:10]),
            "trades": total,
            "win_rate": round(wr, 3),
            "recent_wr": round(recent_wr, 3),
            "pnl": round(w.get("total_pnl", 0), 2),
            "category": w.get("category", "NEUTRAL"),
            "last_trade": w.get("last_trade", ""),
        }

        cat = w.get("category", "NEUTRAL")
        if cat == "STAR":
            stars.append(entry)
        elif cat == "RELIABLE":
            reliable.append(entry)
        elif cat == "TOXIC":
            toxic.append(entry)
        elif cat == "DECAYING":
            decaying.append(entry)
        else:
            neutral.append(entry)

    total_pnl = sum(w.get("total_pnl", 0) for w in wallets.values())

    for lst in (stars, reliable, neutral, decaying, toxic):
        lst.sort(key=lambda x: x["pnl"], reverse=True)

    return {
        "total_wallets": len(wallets),
        "stars": stars,
        "reliable": reliable,
        "neutral": neutral,
        "decaying": decaying,
        "toxic": toxic,
        "total_pnl": round(total_pnl, 2),
    }


def format_telegram_report(analysis: dict) -> str:
    """Formatiert Analyse als Telegram-Nachricht."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"📊 *Weekly Wallet Decay Report*",
        f"_{now}_",
        f"",
        f"*Wallets gesamt:* {analysis['total_wallets']}",
        f"*Gesamt P&L:* ${analysis['total_pnl']:+,.2f}",
        f"",
    ]

    # Decay/Toxic Wallets
    toxic = analysis.get("toxic", [])
    decaying = analysis.get("decaying", [])
    problem_wallets = toxic + decaying

    if problem_wallets:
        lines.append("🚨 *DECAY / TOXIC WALLETS*")
        for w in problem_wallets[:8]:
            emoji = "☠️" if w["category"] == "TOXIC" else "⚠️"
            lines.append(
                f"{emoji} `{w['alias']}` — "
                f"WR {w['win_rate']:.0%} (recent {w['recent_wr']:.0%}) | "
                f"PnL ${w['pnl']:+.0f} | "
                f"{w['trades']} Trades"
            )
        lines.append("")

    # Star Wallets
    stars = analysis.get("stars", [])
    if stars:
        lines.append("⭐ *TOP WALLETS*")
        for w in stars[:5]:
            lines.append(
                f"✅ `{w['alias']}` — "
                f"WR {w['win_rate']:.0%} | "
                f"PnL ${w['pnl']:+.0f} | "
                f"{w['trades']} Trades"
            )
        lines.append("")

    # Reliable
    reliable = analysis.get("reliable", [])
    if reliable:
        lines.append("📈 *RELIABLE WALLETS*")
        for w in reliable[:5]:
            lines.append(
                f"🔵 `{w['alias']}` — "
                f"WR {w['win_rate']:.0%} | "
                f"PnL ${w['pnl']:+.0f} | "
                f"{w['trades']} Trades"
            )
        lines.append("")

    if not problem_wallets and not stars and not reliable:
        lines.append("_Keine ausreichenden Daten für Kategorisierung._")

    return "\n".join(lines)


def send_telegram(text: str) -> bool:
    """Sendet Nachricht via Telegram Bot API."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("[WalletCheck] Kein TELEGRAM_BOT_TOKEN oder TELEGRAM_CHAT_ID")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }).encode()

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())
            if result.get("ok"):
                print("[WalletCheck] Telegram-Nachricht gesendet.")
                return True
            print(f"[WalletCheck] Telegram Fehler: {result}")
            return False
    except Exception as e:
        print(f"[WalletCheck] Telegram-Fehler: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Wallet Decay Score Report")
    parser.add_argument("--dry-run", action="store_true", help="Kein Telegram-Versand")
    args = parser.parse_args()

    data = load_wallet_data()
    analysis = analyze_wallets(data)
    report = format_telegram_report(analysis)

    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)

    if not args.dry_run:
        send_telegram(report)
    else:
        print("\n[DRY-RUN] Kein Telegram-Versand.")


if __name__ == "__main__":
    main()
