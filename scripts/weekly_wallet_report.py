#!/usr/bin/env python3
"""
weekly_wallet_report.py — Wöchentlicher Wallet-Scout Trend-Report.

Wird von kongtrade-wallet-report.timer (Sonntag 20:00 Berlin) ausgeführt.
Sendet Telegram-Report mit Neueinsteigern, Decay-Kandidaten, Rising Stars.
"""
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.wallet_trends import (
    get_new_entries, get_decay_candidates, get_rising_stars, get_top_stable
)
from utils.logger import get_logger

logger = get_logger("weekly_wallet_report")

SOURCE  = os.getenv("SCOUT_SOURCE", "polymonit")
DAYS    = int(os.getenv("SCOUT_TREND_DAYS", "7"))


def _send_telegram(text: str) -> None:
    token        = os.getenv("TELEGRAM_TOKEN", "")
    chat_ids_raw = os.getenv("TELEGRAM_CHAT_IDS", "")
    if not token or not chat_ids_raw:
        logger.warning("Kein TELEGRAM_TOKEN oder TELEGRAM_CHAT_IDS")
        return
    for cid in [c.strip() for c in chat_ids_raw.split(",") if c.strip()]:
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


def _fmt_addr(addr: str) -> str:
    return f"{addr[:6]}...{addr[-4:]}" if len(addr) > 12 else addr


def _fmt_wr(wr) -> str:
    if wr is None:
        return "?%"
    return f"{wr*100:.0f}%"


def build_report() -> str:
    now = datetime.now(timezone.utc)
    kw  = now.isocalendar()[1]

    lines = [f"📊 <b>Wallet-Scout Wochen-Report KW{kw:02d}</b>",
             f"📅 {now.strftime('%d.%m.%Y %H:%M')} UTC | Quelle: {SOURCE} | {DAYS} Tage"]

    # 1. Neue Einsteiger
    new = get_new_entries(SOURCE, days=DAYS)
    lines.append(f"\n🆕 <b>Neue Top-20 Einsteiger ({len(new)})</b>")
    if new:
        for w in new[:5]:
            lines.append(
                f"  • <b>{w.get('alias') or _fmt_addr(w['wallet_address'])}</b>"
                f" — Platz {w.get('rank','?')}"
                f", WR {_fmt_wr(w.get('win_rate'))}"
                f", P&amp;L ${w.get('pnl_usd') or 0:,.0f}"
            )
    else:
        lines.append("  Keine neuen Einsteiger (Daten noch zu jung — ab 7 Scan-Tagen)")

    # 2. Decay-Kandidaten (Rank gefallen)
    decay = get_decay_candidates(SOURCE, days=DAYS, rank_drop_threshold=5)
    lines.append(f"\n📉 <b>Rank-Verluste &gt;5 Plätze ({len(decay)})</b>")
    if decay:
        for w in decay[:5]:
            lines.append(
                f"  • <b>{w.get('alias') or _fmt_addr(w['wallet_address'])}</b>"
                f" — Platz ↓{w.get('rank_delta','?')} (Best:{w.get('rank_best','?')} → Worst:{w.get('rank_worst','?')})"
            )
    else:
        lines.append("  Keine starken Rank-Verluste")

    # 3. Rising Stars
    stars = get_rising_stars(SOURCE, days=DAYS, roi_improvement_pct=10.0)
    lines.append(f"\n⭐ <b>Rising Stars WR+10pp ({len(stars)})</b>")
    if stars:
        for w in stars[:5]:
            lines.append(
                f"  • <b>{w.get('alias') or _fmt_addr(w['wallet_address'])}</b>"
                f" — WR {_fmt_wr(w.get('wr_old'))} → {_fmt_wr(w.get('wr_new'))}"
                f" (+{w.get('improvement',0):.1f}pp)"
            )
    else:
        lines.append("  Keine Rising Stars (Daten noch zu jung)")

    # 4. Stabil Top-5
    stable = get_top_stable(SOURCE, days=DAYS, top_n=5)
    lines.append(f"\n📈 <b>Stabil Top-5 ({len(stable)})</b>")
    if stable:
        for w in stable[:5]:
            lines.append(
                f"  • <b>{w.get('alias') or _fmt_addr(w['wallet_address'])}</b>"
                f" — ⌀ Platz {w.get('avg_rank',0):.1f}"
                f", ⌀ WR {_fmt_wr(w.get('avg_wr'))}"
            )
    else:
        lines.append("  Noch keine stabilen Daten (braucht 7+ Scan-Tage)")

    lines.append("\n—")
    lines.append("🤖 KongTradeBot Wallet-Scout")
    return "\n".join(lines)


def main():
    logger.info("Wöchentlicher Wallet-Report wird erstellt...")
    report = build_report()
    logger.info(f"Report ({len(report)} Zeichen):\n{report}")
    _send_telegram(report)
    logger.info("Wochen-Report gesendet")


if __name__ == "__main__":
    main()
