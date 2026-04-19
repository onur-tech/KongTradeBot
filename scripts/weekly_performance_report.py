#!/usr/bin/env python3
"""
scripts/weekly_performance_report.py — Wöchentlicher Per-Wallet-Performance-Report

Freitags 23:55 via systemd-Timer.
Schreibt analyses/wallet_report_YYYY-WW.md + optionaler Telegram-Summary.

Usage:
    python3 scripts/weekly_performance_report.py
    python3 scripts/weekly_performance_report.py --send
    python3 scripts/weekly_performance_report.py --dry-run
    python3 scripts/weekly_performance_report.py --days 30
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

from utils.wallet_performance import (
    compute_all_wallets, compute_by_category, compute_by_timeframe,
)


def _hr(v) -> str:
    return f"{v:.1f}%" if v is not None else "n/a"


def _usdc(v) -> str:
    return f"{v:+.2f}" if v is not None else "n/a"


def build_report(since_days: int = 7) -> str:
    now     = datetime.now(timezone.utc)
    week    = now.isocalendar()[1]
    year    = now.year
    wallets = compute_all_wallets(since_days=since_days)
    active  = [w for w in wallets if w["trades_count"] > 0]

    lines = [
        f"# Wallet Performance Report — KW{week:02d}/{year}",
        f"_Erstellt: {now.strftime('%Y-%m-%d %H:%M UTC')} | Zeitraum: letzte {since_days} Tage_",
        "",
        "## Übersicht",
        "",
        f"- **Aktive Wallets:** {len(active)} / {len(wallets)}",
        f"- **Trades gesamt:** {sum(w['trades_count'] for w in active)}",
        f"- **Unrealisierter PnL:** {sum(w['unrealized_pnl_usdc'] for w in active):+.2f} USDC",
        "",
        "## Wallet-Tabelle",
        "",
        "| Name | Trades | W/L/P | Hit% | ROI% | Net PnL | Unreal. | Slip¢ | Note |",
        "|------|--------|-------|------|------|---------|---------|-------|------|",
    ]

    for w in active:
        wl   = f"{w['wins_count']}/{w['losses_count']}/{w['pending_count']}"
        slip = f"{w['avg_slippage_cents']:.2f}" if w['avg_slippage_cents'] is not None else "n/a"
        low  = " ⚠" if w["low_sample"] else ""
        lines.append(
            f"| {w['name']}{low} | {w['trades_count']} | {wl} "
            f"| {_hr(w['hit_rate'])} | {_hr(w['roi_pct'])} "
            f"| {_usdc(w['net_pnl_usdc'])} | {_usdc(w['unrealized_pnl_usdc'])} "
            f"| {slip} | {w['note']} |"
        )

    if not active:
        lines.append("_Keine aktiven Wallets im Zeitraum._")

    qualified = [w for w in active if w["trades_count"] >= 5]

    if active:
        top = active[0]
        cats = compute_by_category(top["wallet"], since_days)
        if cats:
            lines += [
                "",
                f"## Kategorien: {top['name']}",
                "",
                "| Kategorie | Trades | Hit% | PnL | Unreal. |",
                "|-----------|--------|------|-----|---------|",
            ]
            for cat, d in cats.items():
                lines.append(
                    f"| {cat} | {d['trades']} | {_hr(d['hit_rate'])} "
                    f"| {_usdc(d['pnl'])} | {_usdc(d['unrealized_pnl'])} |"
                )

        tfs = compute_by_timeframe(top["wallet"], since_days)
        tf_labels = {
            "same_day": "Same-Day", "short": "Short (1-3d)",
            "medium": "Medium (4-10d)", "long": "Long (11d+)", "unknown": "Unbekannt",
        }
        if tfs:
            lines += [
                "",
                f"## Zeitfenster: {top['name']}",
                "",
                "| Zeitfenster | Trades | Hit% | PnL | Unreal. |",
                "|-------------|--------|------|-----|---------|",
            ]
            for tf, d in tfs.items():
                lines.append(
                    f"| {tf_labels.get(tf, tf)} | {d['trades']} | {_hr(d['hit_rate'])} "
                    f"| {_usdc(d['pnl'])} | {_usdc(d['unrealized_pnl'])} |"
                )

    if qualified:
        lines += ["", "## Empfehlungen", ""]
        top5 = sorted(qualified, key=lambda x: (x["hit_rate"] or 0, x["unrealized_pnl_usdc"]), reverse=True)[:5]
        lines.append("**✅ Beibehalten / erhöhen:**")
        for w in top5:
            lines.append(f"- {w['name']} — Hit={_hr(w['hit_rate'])}, ROI={_hr(w['roi_pct'])}")

        remove = [w for w in qualified if (w["hit_rate"] or 100) < 40]
        if remove:
            lines += ["", "**❌ Entfernen-Kandidaten (Hit-Rate < 40%):**"]
            for w in remove:
                lines.append(f"- {w['name']} — Hit={_hr(w['hit_rate'])}, Trades={w['trades_count']}")
    else:
        lines += ["", "_Zu wenig qualifizierte Wallets für Empfehlungen (min. 5 Trades)._"]

    lines += ["", "---", "_Auto-generiert von KongTradeBot weekly_performance_report.py_"]
    return "\n".join(lines)


def build_telegram_summary(since_days: int = 7) -> str:
    wallets      = compute_all_wallets(since_days=since_days)
    active       = [w for w in wallets if w["trades_count"] > 0]
    now          = datetime.now(timezone.utc)
    week         = now.isocalendar()[1]
    total_unreal = sum(w["unrealized_pnl_usdc"] for w in active)
    total_trades = sum(w["trades_count"] for w in active)
    qualified    = [w for w in active if w["trades_count"] >= 5]
    top3         = sorted(qualified, key=lambda x: (x["hit_rate"] or 0), reverse=True)[:3] if qualified else active[:3]

    lines = [
        f"📊 *Wallet-Performance KW{week:02d}* ({since_days}d)",
        f"Wallets aktiv: {len(active)} | Trades: {total_trades} | PnL: {total_unreal:+.2f} USDC",
        "",
    ]
    if top3:
        lines.append("🏆 *Top Wallets:*")
        for w in top3:
            lines.append(f"  • {w['name']}: Hit={_hr(w['hit_rate'])}, {w['trades_count']} Trades")

    remove = [w for w in qualified if (w["hit_rate"] or 100) < 40] if qualified else []
    if remove:
        lines += ["", "⚠️ *Entfernen-Kandidaten:* " + ", ".join(w["name"] for w in remove)]

    return "\n".join(lines)


def send_telegram(text: str) -> bool:
    token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("WARN: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID nicht gesetzt")
        return False
    url  = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}).encode()
    try:
        urllib.request.urlopen(url, data=data, timeout=10)
        return True
    except Exception as e:
        print(f"Telegram-Fehler: {e}")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days",    type=int, default=7)
    ap.add_argument("--send",    action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    report = build_report(since_days=args.days)

    if args.dry_run:
        print(report[:2000])
        print("── (truncated) ──")
        return

    now      = datetime.now(timezone.utc)
    week     = now.isocalendar()[1]
    year     = now.year
    out_dir  = BASE_DIR / "analyses"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"wallet_report_{year}-{week:02d}.md"
    out_file.write_text(report, encoding="utf-8")
    print(f"Gespeichert: {out_file}")

    if args.send:
        summary = build_telegram_summary(since_days=args.days)
        ok = send_telegram(summary)
        print("Telegram:", "OK" if ok else "FEHLER")


if __name__ == "__main__":
    main()
