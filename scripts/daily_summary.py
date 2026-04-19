"""
scripts/daily_summary.py — T-M04d Phase 5: Täglicher 20:00 Abend-Summary

Sendet Telegram-Alert mit Bot-Aktivitäts-Zusammenfassung:
  - Buys/Sells heute + Exit-Typ-Aufschlüsselung
  - Realized PnL (Price-Trigger, Whale-Exit, TP-Staffel)
  - Daily-Sell-Cap Status
  - Top-3 und Worst Position (nach CurrentValue)
  - Portfolio-Snapshot

Aufruf:
  python3 scripts/daily_summary.py           # warten bis 20:00 Berlin (Scheduler-Modus)
  python3 scripts/daily_summary.py --now     # sofort senden (Test)
  python3 scripts/daily_summary.py --dry-run # Nachricht ausgeben, nicht senden
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

TOKEN           = os.getenv("TELEGRAM_TOKEN", "")
RAW_IDS         = os.getenv("TELEGRAM_CHAT_IDS", "")
CHAT_IDS        = [cid.strip() for cid in RAW_IDS.split(",") if cid.strip()]
POLYMARKET_ADDR = os.getenv("POLYMARKET_ADDRESS", "")
DAILY_CAP_USD   = float(os.getenv("DAILY_SELL_CAP_USD", "30"))
DRY_RUN         = "--dry-run" in sys.argv
SEND_NOW        = "--now" in sys.argv

ARCHIVE_FILE = BASE_DIR / "trades_archive.json"
STATE_FILE   = BASE_DIR / "bot_state.json"
LOG_FILE     = BASE_DIR / "logs" / f"bot_{date.today().isoformat()}.log"


# ── Datenquellen ──────────────────────────────────────────────────────────────

def _load_archive() -> list:
    try:
        return json.loads(ARCHIVE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _load_bot_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _count_cap_blocked_today() -> int:
    """Zählt Daily-Sell-Cap-Blocks aus dem heutigen Bot-Log."""
    try:
        if not LOG_FILE.exists():
            return 0
        return LOG_FILE.read_text(encoding="utf-8").count("Daily-Sell-Cap erreicht")
    except Exception:
        return 0


async def _fetch_portfolio() -> dict:
    """Holt aktuelle Positionen + Werte von Polymarket Data-API."""
    if not POLYMARKET_ADDR:
        return {}
    url = f"https://data-api.polymarket.com/positions?user={POLYMARKET_ADDR}&sizeThreshold=.01&limit=500"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=12)) as r:
                if r.status == 200:
                    data = await r.json()
                    if isinstance(data, list):
                        return {"positions": data}
    except Exception:
        pass
    return {}


# ── Message-Builder ───────────────────────────────────────────────────────────

def _build_message(portfolio: dict) -> str:
    today_str = date.today().isoformat()
    today_de  = date.today().strftime("%d.%m.%Y")
    trades    = _load_archive()

    today_all  = [t for t in trades if t.get("datum") == today_str]
    buys       = [t for t in today_all if t.get("seite") == "BUY"]
    sells_new  = [t for t in today_all
                  if t.get("seite") == "SELL" and not t.get("legacy_missing_pnl")]
    sells_live = [t for t in sells_new if t.get("modus") == "LIVE"]

    # Exit-Typ-Aufschlüsselung (neue Einträge mit kategorie="exit_*")
    def _exit_sells(typ: str):
        return [t for t in sells_new if t.get("kategorie", "").startswith(f"exit_{typ}")]

    price_trigger_sells = _exit_sells("price_trigger")
    whale_exit_sells    = _exit_sells("whale_exit")
    tp_sells            = [t for t in sells_new
                           if t.get("kategorie", "") in ("exit_tp1", "exit_tp2", "exit_tp3")]
    trail_sells         = _exit_sells("trail")
    cap_blocked         = _count_cap_blocked_today()

    # Realized PnL (nur mark_resolved Einträge mit echtem PnL)
    def _pnl(lst):
        return sum(float(t.get("gewinn_verlust_usdc", 0) or 0) for t in lst)

    total_realized_pnl  = _pnl(sells_new)
    pt_pnl              = _pnl(price_trigger_sells)
    we_pnl              = _pnl(whale_exit_sells)
    tp_pnl              = _pnl(tp_sells)

    # Daily-Cap verbrauch
    cap_used = sum(float(t.get("einsatz_usdc", 0) or 0) for t in sells_live)
    cap_pct  = min(100, round(cap_used / max(0.01, DAILY_CAP_USD) * 100))

    # Offene Positionen (Polymarket API)
    api_positions = portfolio.get("positions", [])
    open_count    = len(api_positions)
    open_value    = sum(float(p.get("currentValue") or 0) for p in api_positions)
    open_invested = sum(float(p.get("initialValue") or float(p.get("cost") or 0)) for p in api_positions)

    # Top-3 + Worst (nach ROI%)
    def _roi(p):
        iv = float(p.get("initialValue") or p.get("cost") or 0)
        cv = float(p.get("currentValue") or 0)
        return (cv - iv) / max(0.001, iv) * 100 if iv > 0 else 0

    if api_positions:
        sorted_pos    = sorted(api_positions, key=_roi, reverse=True)
        top3          = sorted_pos[:3]
        worst         = sorted_pos[-1] if sorted_pos else None
    else:
        top3, worst   = [], None

    # Portfolio-Werte
    total_portfolio   = sum(float(p.get("currentValue") or 0) for p in api_positions)

    pnl_icon  = "🟢" if total_realized_pnl >= 0 else "🔴"
    pnl_sign  = "+" if total_realized_pnl >= 0 else ""
    cap_bar   = "▓" * (cap_pct // 10) + "░" * (10 - cap_pct // 10)

    lines = [
        f"📊 <b>DAILY SUMMARY — {today_de}</b>",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    # Trades
    lines += [
        f"🔄 <b>Trades heute:</b> {len(buys)} Buys | {len(sells_new)} Sells",
        "",
    ]

    # Exit-Aufschlüsselung
    lines += ["💰 <b>Exit-Events:</b>"]
    if price_trigger_sells:
        lines.append(f"   📈 Price-Trigger ≥95¢: {len(price_trigger_sells)}× | {'+' if pt_pnl>=0 else ''}${pt_pnl:.2f}")
    else:
        lines.append("   📈 Price-Trigger ≥95¢: 0× (kein Trigger heute)")
    if whale_exit_sells:
        lines.append(f"   🐋 Whale-Exit: {len(whale_exit_sells)}× | {'+' if we_pnl>=0 else ''}${we_pnl:.2f}")
    if tp_sells:
        lines.append(f"   💰 TP-Staffel (TP1/2/3): {len(tp_sells)}× | {'+' if tp_pnl>=0 else ''}${tp_pnl:.2f}")
    if trail_sells:
        lines.append(f"   🔻 Trailing-Stop: {len(trail_sells)}×")
    if cap_blocked:
        lines.append(f"   🚫 Cap-Blocked: {cap_blocked}× (${DAILY_CAP_USD:.0f} Limit)")
    lines.append("")

    # Realized PnL
    lines += [
        f"{pnl_icon} <b>Realized P&L heute: {pnl_sign}${total_realized_pnl:.2f} USDC</b>",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    # Top-3 und Worst
    if top3:
        lines.append("🏆 <b>Top Positionen (aktuell):</b>")
        for i, p in enumerate(top3, 1):
            roi   = _roi(p)
            name  = (p.get("title") or p.get("outcome") or "?")[:38]
            cv    = float(p.get("currentValue") or 0)
            sign  = "+" if roi >= 0 else ""
            icon  = "🟢" if roi >= 0 else "🔴"
            lines.append(f"   {i}. {icon} {name}")
            lines.append(f"      {sign}{roi:.1f}% | ${cv:.2f}")
        lines.append("")

    if worst and _roi(worst) < -5:
        roi   = _roi(worst)
        name  = (worst.get("title") or worst.get("outcome") or "?")[:38]
        lines += [
            f"📉 <b>Schlechteste Position:</b>",
            f"   🔴 {name}",
            f"   {roi:.1f}%",
            "",
        ]

    # Portfolio
    lines += [
        "━━━━━━━━━━━━━━━━━━━━",
        f"💼 <b>Portfolio-Snapshot:</b>",
        f"   Positionen offen: {open_count}",
        f"   Marktwert: ${total_portfolio:.2f} USDC",
        f"   Eingesetzt: ${open_invested:.2f} USDC",
        "",
    ]

    # Cap-Status
    lines += [
        f"📅 <b>Daily-Sell-Cap:</b> ${cap_used:.2f} / ${DAILY_CAP_USD:.0f} [{cap_bar}] {cap_pct}%",
        "━━━━━━━━━━━━━━━━━━━━",
        "🤖 Bot aktiv | Nächster Report: 08:00 Morgen-Report 🌅",
    ]

    return "\n".join(lines)


# ── Senden ────────────────────────────────────────────────────────────────────

async def send_summary():
    portfolio = await _fetch_portfolio()
    msg       = _build_message(portfolio)

    if DRY_RUN:
        print("=== DRY-RUN — würde senden: ===")
        print(msg)
        return

    if not TOKEN or not CHAT_IDS:
        print("[Summary] Kein Token / keine Chat-IDs konfiguriert")
        print(msg)
        return

    async with aiohttp.ClientSession() as session:
        for chat_id in CHAT_IDS:
            url     = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            payload = {"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}
            try:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    if r.status == 200:
                        print(f"[Summary] ✅ an {chat_id} gesendet")
                    else:
                        body = await r.text()
                        print(f"[Summary] ❌ Fehler {chat_id}: {r.status} {body[:100]}")
            except Exception as e:
                print(f"[Summary] Fehler: {e}")


async def scheduler_loop():
    """Wartet bis 20:00 Berlin, dann sendet — wiederholt täglich."""
    while True:
        now_utc     = datetime.now(timezone.utc)
        berlin_off  = timedelta(hours=2)          # CEST April (UTC+2)
        now_berlin  = now_utc + berlin_off
        target      = now_berlin.replace(hour=20, minute=0, second=0, microsecond=0)
        if now_berlin >= target:
            target += timedelta(days=1)
        secs = (target - now_berlin).total_seconds()
        print(f"[Summary] Nächster Alert: {target.strftime('%d.%m. %H:%M')} Berlin (in {secs/3600:.1f}h)")
        await asyncio.sleep(secs)
        await send_summary()


def main():
    if SEND_NOW or DRY_RUN:
        asyncio.run(send_summary())
    else:
        asyncio.run(scheduler_loop())


if __name__ == "__main__":
    main()
