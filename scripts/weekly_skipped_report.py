#!/usr/bin/env python3
"""
scripts/weekly_skipped_report.py — Wöchentlicher Skipped-Signal-Report.

Freitags 23:55 via systemd-Timer.
Schreibt analyses/skipped_report_YYYY-WW.md + sendet via Telegram.

Usage:
    python3 scripts/weekly_skipped_report.py
    python3 scripts/weekly_skipped_report.py --send
    python3 scripts/weekly_skipped_report.py --dry-run
"""
import argparse
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

from utils.signal_tracker import generate_weekly_report, get_summary_stats


def _send_telegram(text: str) -> bool:
    token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_ids_raw = os.getenv("TELEGRAM_CHAT_IDS", "")
    if not token or not chat_ids_raw:
        print("[Telegram] Kein Token/ChatID — übersprungen")
        return False
    for chat_id in chat_ids_raw.split(","):
        chat_id = chat_id.strip()
        if not chat_id:
            continue
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        }).encode()
        try:
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data=data,
                method="POST",
            )
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            print(f"[Telegram] Fehler für {chat_id}: {e}")
            return False
    return True


def _save_report(text: str) -> Path:
    now = datetime.now(timezone.utc)
    kw = now.isocalendar()[1]
    year = now.year
    analyses_dir = BASE_DIR / "analyses"
    analyses_dir.mkdir(exist_ok=True)
    path = analyses_dir / f"skipped_report_{year}-KW{kw:02d}.md"
    # Strip Telegram HTML for markdown file
    clean = text.replace("<b>", "**").replace("</b>", "**").replace("<i>", "_").replace("</i>", "_")
    # Remove remaining HTML tags
    import re
    clean = re.sub(r"<[^>]+>", "", clean)
    path.write_text(clean, encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true", help="Via Telegram senden")
    parser.add_argument("--dry-run", action="store_true", help="Nur ausgeben, nicht senden/speichern")
    args = parser.parse_args()

    report = generate_weekly_report()
    stats = get_summary_stats(days=7)

    print(report)
    print(f"\n--- Stats ---")
    print(f"Total: {stats['total_signals']} | Kopiert: {stats['copied']} | Geskippt: {stats['skipped']}")
    print(f"Evaluiert: {stats['evaluated']} | Missed Profit: ${stats['missed_profit_usd']:.2f}")

    if args.dry_run:
        print("\n[DRY-RUN] Nichts gespeichert/gesendet.")
        return

    path = _save_report(report)
    print(f"\n✅ Report gespeichert: {path}")

    if args.send:
        ok = _send_telegram(report)
        print(f"{'✅' if ok else '❌'} Telegram {'gesendet' if ok else 'fehlgeschlagen'}")


if __name__ == "__main__":
    main()
