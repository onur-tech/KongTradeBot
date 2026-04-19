#!/usr/bin/env python3
"""
scripts/weekly_slippage_report.py — Wöchentlicher Slippage-Bericht

Ausgabe: Markdown-Zusammenfassung + optionaler Telegram-Send.
Aufruf:
  python3 scripts/weekly_slippage_report.py           # nur drucken
  python3 scripts/weekly_slippage_report.py --send    # + Telegram
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.slippage_analyzer import (
    compute_weekly_stats,
    compute_by_wallet,
    compute_by_market_category,
    compute_by_signal_type,
    get_today_alert_status,
)
from utils.slippage_tracker import ALERT_THRESHOLD_CENTS


def _row(label: str, val, unit="¢") -> str:
    return f"  {label:<20} {val}{unit}"


def build_report() -> str:
    weekly = compute_weekly_stats(weeks_back=4)
    by_wallet = compute_by_wallet()
    by_cat = compute_by_market_category()
    by_sig = compute_by_signal_type()

    lines = ["# Wöchentlicher Slippage-Report", ""]

    # ── Wöchentliche Zusammenfassung ─────────────────────────────────────────
    lines.append("## Slippage nach Woche (letzte 4 Wochen)")
    if not weekly:
        lines.append("_Keine Live-Trade-Daten vorhanden (nur DRY-RUN?)_")
    else:
        lines.append(f"{'Woche':<12} {'Trades':>6} {'Ø¢':>8} {'Max¢':>8} {'Alert':>6}")
        lines.append("-" * 46)
        for week, st in sorted(weekly.items()):
            alert_flag = "⚠️" if st.get("alert") else "✅"
            lines.append(
                f"{week:<12} {st['count']:>6} {st['mean']:>8.2f} {st['max']:>8.2f} {alert_flag:>6}"
            )
    lines.append("")

    # ── Top-5 Wallets nach Slippage ──────────────────────────────────────────
    lines.append("## Top Wallets (nach Ø-Slippage)")
    if not by_wallet:
        lines.append("_Keine Daten_")
    else:
        for wallet, st in list(by_wallet.items())[:5]:
            lines.append(f"  `{wallet}` — Ø {st['mean']:.2f}¢ ({st['count']} Trades)")
    lines.append("")

    # ── Nach Kategorie ───────────────────────────────────────────────────────
    lines.append("## Slippage nach Kategorie")
    if not by_cat:
        lines.append("_Keine Daten_")
    else:
        for cat, st in by_cat.items():
            lines.append(f"  {cat:<20} Ø {st['mean']:.2f}¢ ({st['count']} Trades)")
    lines.append("")

    # ── Single vs. Multi-Signal ──────────────────────────────────────────────
    lines.append("## Single vs. Multi-Signal")
    for sig_type, st in by_sig.items():
        lines.append(f"  {sig_type:<8} Ø {st['mean']:.2f}¢ ({st['count']} Trades)")
    lines.append("")

    # ── Heute Alert ──────────────────────────────────────────────────────────
    alert = get_today_alert_status()
    status = "⚠️ OVER THRESHOLD" if alert["alert"] else "✅ OK"
    lines.append(f"## Heute ({alert['date']}): {alert['mean_cents']:.2f}¢ ({alert['count']} Trades) — {status}")
    lines.append(f"_Threshold: {ALERT_THRESHOLD_CENTS}¢_")

    return "\n".join(lines)


def send_telegram(text: str) -> None:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    raw_ids = os.getenv("TELEGRAM_CHAT_IDS", "507270873")
    chat_ids = [cid.strip() for cid in raw_ids.split(",") if cid.strip()]
    if not token:
        print("[send_telegram] Kein Token — übersprungen")
        return
    import requests
    for chat_id in chat_ids:
        try:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                timeout=15,
            )
            print(f"[send_telegram] Gesendet an {chat_id}")
        except Exception as e:
            print(f"[send_telegram] Fehler: {e}")


if __name__ == "__main__":
    report = build_report()
    print(report)

    if "--send" in sys.argv:
        # Telegram mag kein Markdown → plain text senden
        plain = report.replace("**", "").replace("# ", "").replace("## ", "\n")
        send_telegram(f"<b>📊 Wöchentlicher Slippage-Report</b>\n<pre>{plain[:3800]}</pre>")
