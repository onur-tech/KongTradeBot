#!/usr/bin/env python3
"""
weekly_tax_export.py — Wöchentlicher Steuer-CSV-Export

Wird von kongtrade-tax-export.timer (Freitag 23:55 Berlin) ausgeführt.
Exportiert steuer_export_<YYYY>.csv + blockpit_import_<YYYY>.csv
in /home/claudeuser/KongTradeBot/exports/ und sendet Telegram-Summary.
"""
import os
import sys
import shutil
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.tax_archive import export_tax_csv, get_summary
from utils.logger import get_logger

logger = get_logger("weekly_tax_export")

EXPORT_DIR = Path(os.getenv("TAX_EXPORT_DIR", "/home/claudeuser/KongTradeBot/exports"))
WORK_DIR   = Path(os.getenv("BOT_DIR", "/home/claudeuser/KongTradeBot"))


def send_telegram_summary(text: str) -> None:
    token = os.getenv("TELEGRAM_TOKEN", "")
    chat_ids_raw = os.getenv("TELEGRAM_CHAT_IDS", "")
    if not token or not chat_ids_raw:
        logger.warning("Kein TELEGRAM_TOKEN oder TELEGRAM_CHAT_IDS — kein Alert")
        return
    import urllib.request, urllib.parse
    chat_ids = [cid.strip() for cid in chat_ids_raw.split(",") if cid.strip()]
    for cid in chat_ids:
        url  = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": cid, "text": text, "parse_mode": "HTML",
        }).encode()
        try:
            urllib.request.urlopen(
                urllib.request.Request(url, data=data, method="POST"), timeout=10
            )
        except Exception as e:
            logger.error(f"Telegram-Fehler an {cid}: {e}")


def main():
    now     = datetime.now(timezone.utc)
    year    = now.year
    kw      = now.isocalendar()[1]

    # Export-Verzeichnis anlegen falls nicht vorhanden
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Export auslösen (läuft im WORK_DIR damit tax_archive die JSON-Datei findet)
    os.chdir(WORK_DIR)
    csv_path = export_tax_csv(year=year)
    if not csv_path:
        logger.error("Kein Export erzeugt — möglicherweise keine Trades für dieses Jahr")
        return

    # Dateien umbenennen und in exports/ verschieben
    for src_name, dst_name in [
        (f"steuer_export_{year}.csv",   f"tax_{year}_KW{kw:02d}.csv"),
        (f"blockpit_import_{year}.csv", f"blockpit_{year}_KW{kw:02d}.csv"),
    ]:
        src = WORK_DIR / src_name
        dst = EXPORT_DIR / dst_name
        if src.exists():
            shutil.move(str(src), str(dst))
            logger.info(f"Exportiert: {dst}")

    # Telegram-Summary
    summary = get_summary(year=year)
    msg = (
        f"📊 <b>Wochen-Export KW{kw:02d} / {year}</b>\n"
        f"Trades gesamt: {summary['live_trades']} LIVE\n"
        f"Investiert: ${summary['total_invested']:.2f}\n"
        f"P&amp;L aufgelöst: ${summary['total_pnl']:.2f}\n"
        f"Win-Rate: {summary['win_rate']}% ({summary['won']}W/{summary['lost']}L)\n"
        f"📁 exports/tax_{year}_KW{kw:02d}.csv + blockpit_{year}_KW{kw:02d}.csv"
    )
    send_telegram_summary(msg)
    logger.info("Wochen-Export abgeschlossen")


if __name__ == "__main__":
    main()
