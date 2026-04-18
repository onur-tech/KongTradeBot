"""
telegram_bot.py v4 - Kong Trading Bot Notifications
"""
import asyncio
import json
import os
import sys
import time
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from typing import Optional

try:
    import anthropic as _anthropic
    _ANTHROPIC_OK = True
except ImportError:
    _ANTHROPIC_OK = False

try:
    import aiohttp
except ImportError:
    print("pip install aiohttp")
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv()

try:
    from strategies.copy_trading import get_wallet_name as _get_wallet_name
except ImportError:
    def _get_wallet_name(addr: str) -> str:
        return addr[:10] + "..." if addr else "Unknown"

TOKEN          = os.getenv("TELEGRAM_TOKEN", "")
ANTHROPIC_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
RAW_IDS  = os.getenv("TELEGRAM_CHAT_IDS", "")
CHAT_IDS = [cid.strip() for cid in RAW_IDS.split(",") if cid.strip()]
ARCHIVE_FILE = "trades_archive.json"
STATE_FILE   = "bot_state.json"
GAMMA_API    = "https://gamma-api.polymarket.com"

CONFIRMATION_TIMEOUT_S = 30  # Sekunden auf Button-Klick warten

# ── Telegram Notification Filter ─────────────────────────────────────────────
# Nur Trades senden die mindestens EINE dieser Bedingungen erfüllen:
# 1. Einsatz >= TELEGRAM_MIN_SIZE_USD
# 2. Multi-Signal-Trade (2+ Wallets) wenn TELEGRAM_ALWAYS_MULTI_SIGNAL=true
# 3. High-Value-Wallet (Multiplikator >= 2.0x) wenn TELEGRAM_ALWAYS_HIGH_WALLET=true
_TG_MIN_SIZE        = float(os.getenv("TELEGRAM_MIN_SIZE_USD", "2"))
_TG_MULTI_SIGNAL    = os.getenv("TELEGRAM_ALWAYS_MULTI_SIGNAL", "true").lower() == "true"
_TG_HIGH_WALLET     = os.getenv("TELEGRAM_ALWAYS_HIGH_WALLET", "true").lower() == "true"
_TG_HIGH_WALLET_PCT = 2.0  # Schwelle ab welchem Multiplikator "High-Value" gilt

# Owner-ID darf Inline-Buttons drücken (Trading-Entscheidungen); alle anderen sind read-only
OWNER_ID = os.getenv("TELEGRAM_OWNER_ID", "")

# ── Mute + Startup Rate-Limit ─────────────────────────────────────────────────
_BOT_DIR            = Path(os.getenv("BOT_DIR", "."))
_MUTE_FILE          = _BOT_DIR / ".mute_until"
_STARTUP_ALERT_FILE = _BOT_DIR / ".last_startup_alert"
_STARTUP_COOLDOWN_S = int(os.getenv("STARTUP_ALERT_COOLDOWN_S", "1800"))


def _is_muted() -> bool:
    if not _MUTE_FILE.exists():
        return False
    try:
        until = datetime.fromisoformat(_MUTE_FILE.read_text().strip())
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < until
    except Exception:
        return False


def _is_startup_allowed() -> bool:
    if not _STARTUP_ALERT_FILE.exists():
        return True
    try:
        return (time.time() - float(_STARTUP_ALERT_FILE.read_text().strip())) > _STARTUP_COOLDOWN_S
    except Exception:
        return True


def _mark_startup_sent():
    try:
        _STARTUP_ALERT_FILE.write_text(str(time.time()))
    except Exception:
        pass


def _fetch_dashboard(endpoint: str) -> Optional[dict]:
    """GET http://localhost:5000{endpoint} → JSON dict. None bei Fehler."""
    import urllib.request
    try:
        url = f"http://localhost:5000{endpoint}"
        with urllib.request.urlopen(url, timeout=3) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"[TG] Dashboard fetch failed {endpoint}: {e}")
        return None


def should_send_trade_notification(
    size: float,
    is_multi_signal: bool = False,
    wallet_multiplier: float = 1.0,
) -> bool:
    """Gibt True zurück wenn der Trade per Telegram gemeldet werden soll."""
    if size >= _TG_MIN_SIZE:
        return True
    if _TG_MULTI_SIGNAL and is_multi_signal:
        return True
    if _TG_HIGH_WALLET and wallet_multiplier >= _TG_HIGH_WALLET_PCT:
        return True
    return False

# Offene Trade-Bestätigungen: order_id → asyncio.Future
_pending_decisions: dict = {}


async def send(text: str, parse_mode: str = "HTML", *, urgent: bool = False) -> bool:
    if not TOKEN or not CHAT_IDS:
        return False
    if not urgent and _is_muted():
        return True
    success = True
    async with aiohttp.ClientSession() as session:
        for chat_id in CHAT_IDS:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
            try:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    if r.status != 200:
                        print(f"[TG] Fehler {chat_id}: {await r.text()}")
                        success = False
            except Exception as e:
                print(f"[TG] Fehler: {e}")
                success = False
    return success


async def _send_with_keyboard(text: str, keyboard: dict) -> Optional[int]:
    """Sendet eine Nachricht mit Inline-Keyboard. Gibt message_id zurück oder None."""
    if not TOKEN or not CHAT_IDS:
        return None
    chat_id = CHAT_IDS[0]
    async with aiohttp.ClientSession() as session:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id":      chat_id,
            "text":         text,
            "parse_mode":   "HTML",
            "reply_markup": keyboard,
        }
        try:
            async with session.post(url, json=payload,
                                    timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json()
                if r.status == 200 and data.get("ok"):
                    return data["result"]["message_id"]
        except Exception as e:
            print(f"[TG] send_with_keyboard Fehler: {e}")
    return None


async def _answer_callback_query(callback_id: str, text: str = ""):
    """Beantwortet eine Callback-Query (entfernt Ladeanzeige am Button)."""
    if not TOKEN:
        return
    async with aiohttp.ClientSession() as session:
        url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
        try:
            await session.post(
                url,
                json={"callback_query_id": callback_id, "text": text},
                timeout=aiohttp.ClientTimeout(total=5),
            )
        except Exception:
            pass


async def _edit_message_reply_markup(chat_id: str, message_id: int, text: str):
    """Entfernt Inline-Buttons nach Entscheidung und zeigt den gewählten Text."""
    if not TOKEN:
        return
    async with aiohttp.ClientSession() as session:
        url = f"https://api.telegram.org/bot{TOKEN}/editMessageText"
        try:
            await session.post(
                url,
                json={
                    "chat_id":    chat_id,
                    "message_id": message_id,
                    "text":       text,
                    "parse_mode": "HTML",
                },
                timeout=aiohttp.ClientTimeout(total=5),
            )
        except Exception:
            pass


async def send_trade_confirmation(
    order_id: str,
    market: str,
    outcome: str,
    size: float,
    price: float,
    wallet_name: str,
    category: str = "",
    dry_run: bool = True,
    is_multi_signal: bool = False,
    wallet_multiplier: float = 1.0,
) -> str:
    """
    Sendet Trade-Signal mit 4 Inline-Buttons an Telegram.
    Wartet bis zu CONFIRMATION_TIMEOUT_S Sekunden auf Antwort.

    Gibt zurück: "normal" | "skip" | "double" | "half"
    Standard bei Timeout / gefiltertem Trade: "normal" (Trade läuft durch)
    """
    if not TOKEN or not CHAT_IDS:
        return "normal"

    if not should_send_trade_notification(size, is_multi_signal, wallet_multiplier):
        return "normal"

    cat_emoji = {
        "Sport": "🎾", "Geopolitik": "🌍", "Crypto": "₿",
        "Makro": "📈", "Sonstiges": "ℹ️"
    }.get(category, "📋")
    mode_tag = " [DRY-RUN]" if dry_run else ""

    text = "\n".join([
        f"{cat_emoji} <b>TRADE SIGNAL{mode_tag}</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📌 <b>{market[:55]}</b>",
        f"🎯 {outcome} @ <b>${price:.3f}</b>",
        f"💵 Größe: <b>${size:.2f} USDC</b>",
        f"👛 {wallet_name}",
        "━━━━━━━━━━━━━━━━━━━━",
        f"⏱️ <b>{CONFIRMATION_TIMEOUT_S}s</b> — danach läuft Trade normal durch.",
    ])

    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Normal", "callback_data": f"t:{order_id}:normal"},
            {"text": "⏭️ Skip",   "callback_data": f"t:{order_id}:skip"},
            {"text": "2️⃣ Double", "callback_data": f"t:{order_id}:double"},
            {"text": "½ Half",   "callback_data": f"t:{order_id}:half"},
        ]]
    }

    msg_id = await _send_with_keyboard(text, keyboard)

    # Future registrieren
    loop = asyncio.get_event_loop()
    future: asyncio.Future = loop.create_future()
    _pending_decisions[order_id] = (future, CHAT_IDS[0], msg_id)

    try:
        decision = await asyncio.wait_for(asyncio.shield(future), timeout=CONFIRMATION_TIMEOUT_S)
    except asyncio.TimeoutError:
        decision = "normal"
        if msg_id:
            await _edit_message_reply_markup(
                CHAT_IDS[0], msg_id,
                text + "\n\n⏰ <i>Timeout — wird normal ausgeführt.</i>"
            )
    finally:
        _pending_decisions.pop(order_id, None)

    return decision


def _load_archive() -> list:
    if not os.path.exists(ARCHIVE_FILE):
        return []
    try:
        with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_archive(trades: list):
    with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
        json.dump(trades, f, indent=2, ensure_ascii=False)


def _get_win_rate():
    trades   = _load_archive()
    resolved = [t for t in trades if t.get("aufgeloest")]
    won      = [t for t in resolved if t.get("ergebnis") == "GEWINN"]
    lost     = [t for t in resolved if t.get("ergebnis") == "VERLUST"]
    win_rate = round(len(won) / len(resolved) * 100, 1) if resolved else 0
    return len(won), len(lost), win_rate


def _get_top_positions():
    if not os.path.exists(STATE_FILE):
        return []
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        positions = state.get("open_positions", [])
        with_size = []
        for p in positions:
            size = float(p.get("size_usdc", 0) or 0)
            if size > 1.0:
                with_size.append({
                    "question": p.get("market_question", "")[:45],
                    "outcome":  p.get("outcome", ""),
                    "size":     size,
                })
        return sorted(with_size, key=lambda x: x["size"], reverse=True)[:3]
    except Exception:
        return []


# ── Message Templates ─────────────────────────────────

def msg_trade(market, outcome, size, price, category, source,
              market_id="", time_to_close_hours=None, dry_run=False):
    cat_emoji = {
        "Sport": "🎾", "Geopolitik": "🌍", "Crypto": "₿",
        "Makro": "📈", "Sonstiges": "ℹ️"
    }.get(category, "📋")
    mode_tag = " [DRY-RUN]" if dry_run else ""

    if time_to_close_hours is not None:
        if time_to_close_hours < 1:
            closes = "⏰ Schließt in: <b>&lt;1h</b>"
        elif time_to_close_hours < 24:
            closes = f"⏰ Schließt in: <b>{time_to_close_hours:.0f}h</b>"
        else:
            closes = f"⏰ Schließt in: <b>{time_to_close_hours/24:.0f} Tagen</b>"
    else:
        closes = "⏰ Schließt: <b>bald</b>"

    id_line = f"\n🔑 <code>{market_id[:24]}</code>" if market_id else ""

    lines = [
        f"{cat_emoji} <b>NEUER TRADE{mode_tag}</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📌 <b>{market[:60]}</b>",
        f"✅ Outcome: <b>{outcome}</b>",
        f"💵 Einsatz: <b>${size:.2f}</b> @ ${price:.3f}",
        closes,
        f"👛 Wallet: <b>{_get_wallet_name(source)}</b>{id_line}",
    ]
    return "\n".join(lines)


def msg_order_submitted(order_id, market, outcome, price, size, wallet, dry_run=False):
    """📤 Nach erfolgreichem Submit — Order ist PENDING, warte auf Polymarket-Bestätigung."""
    mode_tag = " [DRY-RUN]" if dry_run else ""
    return "\n".join([
        f"📤 <b>ORDER GESENDET{mode_tag}</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"🎯 <b>{market[:55]}</b>",
        f"💰 {outcome} @ <b>${price:.3f}</b> | <b>${size:.2f} USDC</b>",
        f"🐋 {_get_wallet_name(wallet)}",
        f"🔑 <code>{order_id[:20]}...</code>",
        "━━━━━━━━━━━━━━━━━━━━",
        "⏳ <i>Warte auf Polymarket-Bestätigung...</i>",
    ])


def msg_order_filled(order_id, market, outcome, price, size, shares, wallet, tx_hash=""):
    """✅ WebSocket MATCHED/CONFIRMED — Order ist gefüllt."""
    tx_line = f'\n🔗 <a href="https://polygonscan.com/tx/{tx_hash}">Polygonscan</a>' if tx_hash else ""
    return "\n".join([
        "✅ <b>ORDER GEFILLT</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"🎯 <b>{market[:55]}</b>",
        f"✅ {outcome} @ <b>${price:.3f}</b> | <b>${size:.2f} USDC</b> → <b>{shares:.2f} Shares</b>",
        f"🐋 {_get_wallet_name(wallet)}{tx_line}",
        f"🔑 <code>{order_id[:20]}...</code>",
    ])


def msg_order_rejected(order_id, market, outcome, size, error_msg=""):
    """❌ WebSocket FAILED oder API 400 — nur echte Rejections, keine Pre-Submit-Skips."""
    reason = f"\n❗ Grund: <i>{error_msg[:120]}</i>" if error_msg else ""
    return "\n".join([
        "❌ <b>ORDER ABGELEHNT</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"🎯 <b>{market[:55]}</b>",
        f"💰 {outcome} | ${size:.2f} USDC{reason}",
        f"🔑 <code>{order_id[:20]}...</code>",
    ])


def msg_order_cancelled(order_id, market, outcome, size):
    """🚫 WebSocket CANCELLATION."""
    return "\n".join([
        "🚫 <b>ORDER GECANCELT</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"🎯 <b>{market[:55]}</b>",
        f"💰 {outcome} | ${size:.2f} USDC",
        f"🔑 <code>{order_id[:20]}...</code>",
    ])


def msg_result(market, outcome, won, size, pnl):
    icon   = "🏆" if won else "💸"
    result = "GEWONNEN" if won else "VERLOREN"
    pnl_str = f"+${pnl:.2f}" if pnl > 0 else f"-${abs(pnl):.2f}"
    lines = [
        f"{icon} <b>MARKT AUFGELÖST — {result}!</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📌 <b>{market[:55]}</b>",
        f"✅ Gesetzt auf: <b>{outcome}</b>",
        f"💵 Einsatz: ${size:.2f}  →  P&L: <b>{pnl_str} USDC</b>",
    ]
    return "\n".join(lines)


def msg_status(
    signals, orders_sent, open_pos, total_invested, pnl, categories, archive_count,
    skipped_min_size=0, rejected_api=0, filled=0, pending=0,
    # legacy compat: old callers pass orders as 2nd arg — treat as orders_sent
):
    cat_lines = []
    for cat, amt in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        if amt > 0:
            bar = "▓" * min(int(amt / 200), 6) + "░" * max(0, 6 - min(int(amt / 200), 6))
            cat_lines.append(f"  {cat}\n  {bar} <b>${amt:.2f}</b>")

    won, lost, win_rate = _get_win_rate()
    wr_icon = "🟢" if win_rate >= 55 else "🟡" if win_rate >= 50 else "🔴"
    wr_total = won + lost
    if wr_total > 0:
        wr_line = f"  ✅ {won}W / ❌ {lost}L\n  {wr_icon} Win Rate: <b>{win_rate}%</b>"
    else:
        wr_line = "  Noch keine aufgelösten Trades"

    bar_pct = min(int(total_invested / 500), 10)
    inv_bar = "🟩" * bar_pct + "⬜" * (10 - bar_pct)

    top_pos = _get_top_positions()
    pos_lines = []
    for p in top_pos:
        pos_lines.append(f"  📌 {p['outcome']} | ${p['size']:.2f} | {p['question']}")
    if not pos_lines:
        pos_lines = ["  —"]

    pnl_icon = "📈" if pnl >= 0 else "📉"
    pnl_sign = "+" if pnl >= 0 else ""

    lines = [
        "╔══════════════════════╗",
        "║  📊 <b>STÜNDL. REPORT</b>  ║",
        "╚══════════════════════╝",
        f"🕐 <b>{datetime.now().strftime('%d.%m.  %H:%M')} Uhr</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"📡 Signale empfangen:    <b>{signals}</b>",
        f"📤 Orders gesendet:      <b>{orders_sent}</b>",
        f"⏭️ Skipped (Min-Size):  <b>{skipped_min_size}</b>",
        f"❌ Rejected (API):       <b>{rejected_api}</b>",
        f"✅ Gefüllt:              <b>{filled}</b>",
        f"⏳ Pending:              <b>{pending}</b>",
        f"⚡ Offen:                <b>{open_pos} Positionen</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "🎯 <b>Win Rate:</b>",
        wr_line,
        "━━━━━━━━━━━━━━━━━━━━━━",
        "💰 <b>Real investiert:</b>",
        f"  {inv_bar}",
        f"  <b>${total_invested:.2f} USDC</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "📂 <b>Kategorien:</b>",
    ]
    lines.extend(cat_lines)
    lines.extend([
        "━━━━━━━━━━━━━━━━━━━━━━",
        "🔝 <b>Größte Positionen:</b>",
    ])
    lines.extend(pos_lines)
    lines.extend([
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"{pnl_icon} P&L heute: <b>{pnl_sign}${pnl:.2f} USDC</b>",
        f"🗄️ Archiv:   <b>{archive_count} Trades</b>",
    ])
    return "\n".join(lines)


def msg_morning_summary(trades_today, resolved, won, lost, pnl, total_trades,
                        portfolio=None, redeemable_str="", closing_today_str=""):
    win_rate = round(won / resolved * 100, 1) if resolved > 0 else 0
    wr_icon  = "🟢" if win_rate >= 55 else "🟡" if win_rate >= 50 else "🔴"
    pnl_icon = "🟢" if pnl >= 0 else "🔴"
    pnl_sign = "+" if pnl >= 0 else ""
    lines = [
        f"☀️ <b>MORGEN-REPORT — {date.today().strftime('%d.%m.%Y')}</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📋 Neue Signale: <b>{trades_today}</b>",
        f"🎯 Aufgelöst:    <b>{resolved}</b>  ✅{won} / ❌{lost}",
        f"  {wr_icon} Win Rate: <b>{win_rate}%</b>",
        f"{pnl_icon} P&L Session: <b>{pnl_sign}${pnl:.2f} USDC</b>",
    ]
    if portfolio:
        lines += [
            "━━━━━━━━━━━━━━━━━━━━",
            f"💼 Portfolio: <b>${portfolio.get('total_value', 0):.2f}</b> ({portfolio.get('count', 0)} Positionen)",
            f"🎰 To-Win Total: <b>${portfolio.get('to_win', 0):.2f}</b>",
        ]
        if portfolio.get('redeemable_count', 0) > 0:
            lines.append(f"💰 <b>CLAIM VERFÜGBAR: ${portfolio.get('redeemable_value', 0):.2f} ({portfolio.get('redeemable_count')}x)</b>")
            if redeemable_str:
                lines.append(redeemable_str)
    if closing_today_str:
        lines += [
            "━━━━━━━━━━━━━━━━━━━━",
            "⏰ <b>Resolutions heute:</b>",
            closing_today_str,
        ]
    lines += [
        "━━━━━━━━━━━━━━━━━━━━",
        f"📦 Archiv gesamt: <b>{total_trades} Trades</b>",
        "🤖 Bot läuft — guten Morgen Brrudi! ☕",
    ]
    return "\n".join(lines)


def msg_warning(reason):
    return "\n".join([
        "⚠️ <b>BOT WARNUNG</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"❗ {reason}",
    ])


def msg_startup(wallets, budget, dry_run):
    mode = "🧪 DRY-RUN (kein echtes Geld)" if dry_run else "💸 LIVE TRADING"
    lines = [
        "🚀 <b>BOT GESTARTET</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"⚙️ Modus: <b>{mode}</b>",
        f"👛 Wallets: <b>{wallets}</b>",
        f"💰 Budget: <b>${budget:,.0f} USDC</b>",
        "🔄 Resolver: alle 15 Minuten",
        "━━━━━━━━━━━━━━━━━━━━",
        "Ihr werdet bei jedem Trade informiert! 📱",
        "Befehle: /status /pnl /help",
    ]
    return "\n".join(lines)


async def send_startup(wallets: int, budget: float, dry_run: bool) -> bool:
    if not _is_startup_allowed():
        print("[TG] Startup-Alert gedrosselt (< 30 min seit letztem)")
        return True
    _mark_startup_sent()
    return await send(msg_startup(wallets, budget, dry_run), urgent=True)


# ── /menu Inline-Keyboard ─────────────────────────────────────────────────────

def _menu_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "📊 Status",      "callback_data": "m:status"},
                {"text": "💼 Portfolio",   "callback_data": "m:portfolio"},
            ],
            [
                {"text": "📅 Heute",       "callback_data": "m:today"},
                {"text": "⚙️ Config",     "callback_data": "m:config"},
            ],
            [
                {"text": "📋 Positionen", "callback_data": "m:positions"},
                {"text": "📡 Archiv",     "callback_data": "m:archive"},
            ],
            [
                {"text": "🔇 Mute 1h",    "callback_data": "m:mute1h"},
                {"text": "🔔 Unmute",     "callback_data": "m:unmute"},
            ],
        ]
    }


_DASHBOARD_ERR = "⚠️ Dashboard aktuell nicht erreichbar. In 1–2 Min erneut versuchen."


async def _handle_menu_callback(action: str, callback_status) -> str:
    """Verarbeitet m:* Callback-Actions und Text-Button-Klicks, gibt Ack-Text zurück."""
    if action == "status":
        await callback_status()
        return "📊 Status gesendet"

    elif action == "portfolio":
        port = _fetch_dashboard("/api/portfolio")
        if not port:
            await send(_DASHBOARD_ERR, urgent=True)
            return "⚠️"
        positions  = port.get("positions", [])
        count      = int(port.get("count", len(positions)))
        total      = sum(float(p.get("current_value", 0) or 0) for p in positions)
        in_pos     = sum(float(p.get("traded", 0) or 0) for p in positions)
        to_win     = sum(float(p.get("to_win", 0) or 0) for p in positions)
        net_pnl    = sum(float(p.get("pnl_usdc", 0) or 0) for p in positions)
        redeemable = sum(1 for p in positions if p.get("redeemable"))
        pnl_sign   = "+" if net_pnl >= 0 else ""
        lines = [
            "💼 <b>PORTFOLIO</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            f"📊 Total: <b>${total:.2f} USDC</b>",
            f"📈 Investiert: <b>${in_pos:.2f}</b> ({count} Positionen{', ' + str(redeemable) + ' claimable' if redeemable else ''})",
            f"🏆 To-Win: <b>${to_win:.2f}</b>",
            f"💰 Net PnL: <b>{pnl_sign}${net_pnl:.2f}</b>",
        ]
        if positions:
            lines += ["━━━━━━━━━━━━━━━━━━━━", "🔝 Top 5:"]
            for i, p in enumerate(sorted(positions, key=lambda x: float(x.get("current_value", 0) or 0), reverse=True)[:5], 1):
                mkt = str(p.get("market", "?"))[:33]
                cur = float(p.get("current_value", 0) or 0)
                inv = float(p.get("traded", 0) or 0)
                lines.append(f"  {i}. {mkt} → <b>${cur:.2f}</b> (inv ${inv:.2f})")
        await send("\n".join(lines), urgent=True)
        return "💼 Portfolio gesendet"

    elif action == "today":
        summary = _fetch_dashboard("/api/summary")
        port    = _fetch_dashboard("/api/portfolio")
        if not summary:
            await send(_DASHBOARD_ERR, urgent=True)
            return "⚠️"
        today_count   = int(summary.get("today_trades", 0))
        # Portfolio-Delta seit Mitternacht (Snapshot-basiert, genauer als nur resolved P&L)
        port_pnl      = float((port or {}).get("today_pnl_portfolio", 0))
        snap_val      = float((port or {}).get("snapshot_value", 0))
        total_val     = float((port or {}).get("total_value", 0))
        resolved_pnl  = float(summary.get("today_pnl", 0))
        pnl_sign = "+" if port_pnl >= 0 else ""
        pnl_icon = "🟢" if port_pnl >= 0 else "🔴"
        lines = [
            f"📅 <b>HEUTE — {date.today().strftime('%d.%m.%Y')}</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            f"📋 Trades: <b>{today_count}</b>",
        ]
        if snap_val > 0:
            lines += [
                f"{pnl_icon} Portfolio-Delta: <b>{pnl_sign}${port_pnl:.2f} USDC</b>",
                f"   Morgen: ${snap_val:.2f} → Jetzt: ${total_val:.2f}",
            ]
        else:
            lines.append(f"💰 Resolved P&L heute: <b>{'+' if resolved_pnl>=0 else ''}${resolved_pnl:.2f}</b>")
        await send("\n".join(lines), urgent=True)
        return "📅 Heute gesendet"

    elif action == "config":
        mute_str = "✅ JA" if _is_muted() else "❌ NEIN"
        lines = [
            "⚙️ <b>BOT-KONFIGURATION</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            f"💵 Min Trade: <b>${_TG_MIN_SIZE:.2f} USD</b>",
            f"📡 Multi-Signal: <b>{'✅' if _TG_MULTI_SIGNAL else '❌'}</b>",
            f"🐋 High-Wallet: <b>{'✅' if _TG_HIGH_WALLET else '❌'} (≥{_TG_HIGH_WALLET_PCT}x)</b>",
            f"🔇 Stumm: <b>{mute_str}</b>",
            f"🌍 Dry-Run: <b>{os.getenv('DRY_RUN', 'false')}</b>",
        ]
        await send("\n".join(lines), urgent=True)
        return "⚙️ Config gesendet"

    elif action == "positions":
        port = _fetch_dashboard("/api/portfolio")
        if not port:
            await send(_DASHBOARD_ERR, urgent=True)
            return "⚠️"
        positions = port.get("positions", [])
        count = int(port.get("count", len(positions)))
        top10 = sorted(positions, key=lambda x: float(x.get("current_value", 0) or 0), reverse=True)[:10]
        lines = [
            f"📋 <b>OFFENE POSITIONEN ({count})</b>",
            "━━━━━━━━━━━━━━━━━━━━",
        ]
        for i, p in enumerate(top10, 1):
            mkt = str(p.get("market", "?"))[:30]
            cur = float(p.get("current_value", 0) or 0)
            inv = float(p.get("traded", 0) or 0)   # traded = Initial-Investment
            pct = float(p.get("pnl_pct", 0) or 0)
            pct_str = f" ({'+' if pct>=0 else ''}{pct:.1f}%)" if inv > 0 else ""
            lines.append(f"  {i}. {mkt} | ${inv:.2f}→<b>${cur:.2f}</b>{pct_str}")
        if not top10:
            lines.append("  —")
        await send("\n".join(lines), urgent=True)
        return "📋 Positionen gesendet"

    elif action == "archive":
        data = _fetch_dashboard("/api/summary")
        if not data:
            won, lost, win_rate = _get_win_rate()
            wr_icon = "🟢" if win_rate >= 55 else "🟡" if win_rate >= 50 else "🔴"
            lines = [
                "🗄️ <b>ARCHIV-STATISTIK</b>",
                "━━━━━━━━━━━━━━━━━━━━",
                f"✅ Gewonnen: <b>{won}</b>  ❌ Verloren: <b>{lost}</b>",
                f"{wr_icon} Win Rate: <b>{win_rate}%</b>",
            ]
        else:
            total_trades = int(data.get("total_trades", 0))
            wins     = int(data.get("wins", 0))
            losses   = int(data.get("losses", 0))
            win_rate = round(float(data.get("win_rate", 0)), 1)
            net_pnl  = float(data.get("pnl", 0))
            wr_icon  = "🟢" if win_rate >= 55 else "🟡" if win_rate >= 50 else "🔴"
            tp_sign  = "+" if net_pnl >= 0 else ""
            lines = [
                "🗄️ <b>ARCHIV-STATISTIK</b>",
                "━━━━━━━━━━━━━━━━━━━━",
                f"📦 Gesamt: <b>{total_trades} Trades</b>",
                f"✅ Gewonnen: <b>{wins}</b>  ❌ Verloren: <b>{losses}</b>",
                f"{wr_icon} Win Rate: <b>{win_rate}%</b>",
                f"💰 PnL: <b>{tp_sign}${net_pnl:.2f} USDC</b>",
            ]
        await send("\n".join(lines), urgent=True)
        return "🗄️ Archiv gesendet"

    elif action == "mute1h":
        until = datetime.now(timezone.utc) + timedelta(hours=1)
        try:
            _MUTE_FILE.write_text(until.isoformat())
        except Exception:
            pass
        await send(f"🔇 Bot stumm bis <b>{until.strftime('%H:%M')} UTC</b>.\nTrades laufen normal weiter.", urgent=True)
        return "🔇 Stumm 1h"

    elif action == "unmute":
        try:
            if _MUTE_FILE.exists():
                _MUTE_FILE.unlink()
        except Exception:
            pass
        await send("🔔 Stummschaltung aufgehoben.", urgent=True)
        return "🔔 Unmuted"

    return "?"


# Persistent Reply Keyboard (kein python-telegram-bot nötig — raw Telegram API JSON)
MAIN_REPLY_KEYBOARD = {
    "keyboard": [
        [{"text": "📊 Status"},     {"text": "💼 Portfolio"}],
        [{"text": "📅 Heute"},      {"text": "🗄️ Archiv"}],
        [{"text": "📋 Positionen"}, {"text": "⚙️ Config"}],
        [{"text": "🔇 Mute 1h"},    {"text": "🔔 Unmute"}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
    "input_field_placeholder": "KongTrade Bot",
}

# Mapping: Button-Text → menu action (muss mit MAIN_REPLY_KEYBOARD übereinstimmen)
_BUTTON_ACTION_MAP = {
    "📊 status":     "status",
    "💼 portfolio":  "portfolio",
    "📅 heute":      "today",
    "🗄️ archiv":    "archive",
    "📋 positionen": "positions",
    "⚙️ config":    "config",
    "🔇 mute 1h":    "mute1h",
    "🔔 unmute":     "unmute",
}


async def _send_with_reply_keyboard(text: str, chat_id: str) -> bool:
    """Sendet eine Nachricht mit dem persistenten Reply-Keyboard."""
    if not TOKEN:
        return False
    async with aiohttp.ClientSession() as session:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id":      chat_id,
            "text":         text,
            "parse_mode":   "HTML",
            "reply_markup": MAIN_REPLY_KEYBOARD,
        }
        try:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as r:
                return r.status == 200
        except Exception as e:
            print(f"[TG] Reply-Keyboard Fehler: {e}")
            return False


def msg_shutdown(total_trades):
    return "\n".join([
        "🛑 <b>BOT GESTOPPT</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📦 Trades archiviert: <b>{total_trades}</b>",
        "State gespeichert ✅",
    ])


# ── Resolver ──────────────────────────────────────────

async def check_resolved_markets_and_notify():
    trades = _load_archive()
    if not trades:
        return

    open_trades = [t for t in trades if not t.get("aufgeloest") and t.get("market_id")]
    if not open_trades:
        return

    markets = {}
    for t in open_trades:
        mid = t.get("market_id", "")
        q   = t.get("markt", "")
        if mid and q:
            if mid not in markets:
                markets[mid] = {"trades": [], "question": q}
            markets[mid]["trades"].append(t)

    newly_resolved = []
    async with aiohttp.ClientSession() as session:
        for mid, group in list(markets.items())[:30]:
            try:
                url = f"{GAMMA_API}/markets/{mid}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                    if r.status != 200:
                        continue
                    market = await r.json()

                prices_raw   = market.get("outcomePrices", '["0.5","0.5"]')
                outcomes_raw = market.get("outcomes", '["Yes","No"]')
                prices   = [float(p) for p in json.loads(prices_raw if isinstance(prices_raw, str) else json.dumps(prices_raw))]
                outcomes = json.loads(outcomes_raw if isinstance(outcomes_raw, str) else json.dumps(outcomes_raw))

                max_price = max(prices)
                if max_price < 0.96:
                    continue

                winner_idx  = prices.index(max_price)
                winner      = outcomes[winner_idx] if winner_idx < len(outcomes) else "?"
                trade_list  = group["trades"]
                our_outcome = trade_list[0].get("outcome", "Yes")
                won         = str(winner).lower().strip() == str(our_outcome).lower().strip()

                total_size   = sum(float(t.get("einsatz_usdc", 0) or 0) for t in trade_list)
                total_shares = sum(float(t.get("shares", 0) or 0) for t in trade_list)
                entry_price  = float(trade_list[0].get("preis_usdc", 0.5) or 0.5)
                if total_shares <= 0 and entry_price > 0:
                    total_shares = total_size / entry_price
                pnl = (total_shares - total_size) if won else -total_size

                newly_resolved.append({
                    "question": group["question"][:55],
                    "outcome": our_outcome,
                    "won": won,
                    "pnl": pnl,
                    "size": total_size,
                    "trades": trade_list,
                })

                for t in trade_list:
                    t["aufgeloest"] = True
                    t["ergebnis"]   = "GEWINN" if won else "VERLUST"
                    sz = float(t.get("einsatz_usdc", 0) or 0)
                    pr = float(t.get("preis_usdc", 0.5) or 0.5)
                    sh = sz / pr if pr > 0 else 0
                    t["gewinn_verlust_usdc"] = round(sh - sz if won else -sz, 4)

            except Exception:
                continue
            await asyncio.sleep(0.2)

    if newly_resolved:
        _save_archive(trades)
        for r in newly_resolved:
            await send(msg_result(
                market=r["question"], outcome=r["outcome"],
                won=r["won"], size=r["size"], pnl=r["pnl"],
            ))
        if len(newly_resolved) > 1:
            wins = [r for r in newly_resolved if r["won"]]
            losses = [r for r in newly_resolved if not r["won"]]
            total_pnl = sum(r["pnl"] for r in newly_resolved)
            pnl_icon  = "🟢" if total_pnl >= 0 else "🔴"
            pnl_sign  = "+" if total_pnl >= 0 else ""
            await send("\n".join([
                "📊 <b>AUFLÖSUNGS-ZUSAMMENFASSUNG</b>",
                "━━━━━━━━━━━━━━━━━━━━",
                f"✅ Gewonnen: <b>{len(wins)}</b>  |  ❌ Verloren: <b>{len(losses)}</b>",
                f"{pnl_icon} Gesamt P&L: <b>{pnl_sign}${total_pnl:.2f} USDC</b>",
            ]))


# ── /add Wallet Helper ────────────────────────────────

def _add_wallet_to_env(address: str) -> tuple:
    """
    Fügt eine neue Wallet-Adresse zu TARGET_WALLETS in der .env-Datei hinzu.
    Gibt (success: bool, message: str) zurück.
    """
    import re as _re

    if not _re.match(r"^0x[0-9a-fA-F]{40}$", address):
        return False, "❌ Ungültige Adresse — Format: <code>0x</code> + 40 Hex-Zeichen"

    address = address.lower()
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if not os.path.exists(env_path):
        env_path = ".env"

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Bereits vorhanden?
        if address in content.lower():
            return False, f"⚠️ Wallet bereits in TARGET_WALLETS:\n<code>{address}</code>"

        # TARGET_WALLETS Zeile finden und erweitern
        if _re.search(r"^TARGET_WALLETS\s*=", content, _re.MULTILINE):
            content = _re.sub(
                r"(^TARGET_WALLETS\s*=\s*)(.*)$",
                lambda m: m.group(1) + m.group(2).rstrip() + ("," if m.group(2).strip() else "") + address,
                content,
                flags=_re.MULTILINE,
            )
        else:
            content += f"\nTARGET_WALLETS={address}\n"

        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content)

        msg = "\n".join([
            "✅ <b>WALLET HINZUGEFÜGT</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            f"<code>{address}</code>",
            "━━━━━━━━━━━━━━━━━━━━",
            "⚠️ Bot-Neustart erforderlich damit die Wallet aktiv wird.",
        ])
        print(f"[TG] /add: Wallet {address[:10]}... zu .env hinzugefügt")
        return True, msg

    except Exception as e:
        return False, f"❌ Fehler beim Schreiben der .env: {e}"


# ── /position + /cancel Helper ───────────────────────────────────────────────

async def _cmd_position(order_id: str):
    """Zeigt Details zu einer offenen Position."""
    if not order_id:
        await send("❌ Verwendung: /position &lt;order_id&gt;")
        return
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        positions = state.get("open_positions", {})
        # Support both dict (new) and list (legacy)
        if isinstance(positions, dict):
            pos = positions.get(order_id)
        else:
            pos = next((p for p in positions if p.get("order_id") == order_id), None)
        pending = state.get("pending_data", {}).get(order_id)
    except Exception:
        pos, pending = None, None

    if pos:
        lines = [
            "📊 <b>POSITION DETAILS</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            f"📌 {pos.get('market_question', '?')[:55]}",
            f"✅ Outcome: <b>{pos.get('outcome', '?')}</b>",
            f"💵 Einsatz: <b>${float(pos.get('size_usdc', 0)):.2f} USDC</b>",
            f"🎯 Einstieg: <b>${float(pos.get('entry_price', 0)):.3f}</b>",
            f"📈 Anteile: <b>{float(pos.get('shares', 0)):.2f}</b>",
            f"🐋 Wallet: {_get_wallet_name(pos.get('source_wallet', ''))}",
            f"🔑 <code>{order_id[:24]}</code>",
            "━━━━━━━━━━━━━━━━━━━━",
            "Status: <b>OPEN (gefüllt)</b>",
        ]
        await send("\n".join(lines))
    elif pending:
        lines = [
            "⏳ <b>PENDING POSITION</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            f"📌 {pending.get('market_question', '?')[:55]}",
            f"✅ Outcome: <b>{pending.get('outcome', '?')}</b>",
            f"💵 Einsatz: <b>${float(pending.get('size_usdc', 0)):.2f} USDC</b>",
            f"🎯 Preis: <b>${float(pending.get('entry_price', 0)):.3f}</b>",
            f"🔑 <code>{order_id[:24]}</code>",
            "━━━━━━━━━━━━━━━━━━━━",
            "Status: <b>⏳ PENDING — warte auf Polymarket</b>",
        ]
        await send("\n".join(lines))
    else:
        await send(f"❓ Order <code>{order_id[:24]}</code> nicht gefunden (weder offen noch pending).")


async def _cmd_cancel(order_id: str):
    """Schreibt Cancel-Request für eine PENDING Order."""
    if not order_id:
        await send("❌ Verwendung: /cancel &lt;order_id&gt;")
        return
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        pending = state.get("pending_data", {}).get(order_id)
    except Exception:
        pending = None

    if not pending:
        await send(f"⚠️ <code>{order_id[:24]}</code> ist nicht PENDING — nur Pending-Orders können storniert werden.")
        return

    cancel_file = os.path.join(os.path.dirname(os.path.abspath(STATE_FILE)), "cancel_requests.json")
    try:
        existing = []
        if os.path.exists(cancel_file):
            with open(cancel_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
        if order_id not in existing:
            existing.append(order_id)
        with open(cancel_file, "w", encoding="utf-8") as f:
            json.dump(existing, f)
        await send("\n".join([
            "🚫 <b>CANCEL ANGEFORDERT</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            f"🔑 <code>{order_id[:24]}</code>",
            f"📌 {pending.get('market_question', '?')[:50]}",
            "━━━━━━━━━━━━━━━━━━━━",
            "⏳ Bot storniert beim nächsten Check.",
        ]))
    except Exception as e:
        await send(f"❌ Cancel fehlgeschlagen: {e}")


# ── Command Handler ────────────────────────────────────

_DECISION_LABELS = {
    "normal": "✅ Normal — Trade läuft durch",
    "skip":   "⏭️ Skip — Trade abgelehnt",
    "double": "2️⃣ Double — Trade 2x größer",
    "half":   "½ Half — Trade halb so groß",
}


async def poll_commands(callback_status, callback_resolve):
    if not TOKEN or not CHAT_IDS:
        return

    offset = 0
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
                # Kurzes Timeout damit Callback-Queries schnell ankommen
                params = {"timeout": 5, "offset": offset}
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    if r.status != 200:
                        await asyncio.sleep(5)
                        continue
                    data = await r.json()
                    updates = data.get("result", [])

                    for update in updates:
                        offset = update["update_id"] + 1

                        # ── Callback-Query (Inline-Button-Klick) ──────────────
                        cb = update.get("callback_query")
                        if cb:
                            cb_id      = cb.get("id", "")
                            cb_data    = cb.get("data", "")
                            cb_chat_id = str(cb.get("message", {}).get("chat", {}).get("id", ""))
                            cb_msg_id  = cb.get("message", {}).get("message_id")
                            cb_from_id = str(cb.get("from", {}).get("id", ""))

                            if cb_chat_id in CHAT_IDS and cb_data.startswith("t:"):
                                # Read-only check: nur Owner darf Buttons drücken
                                if OWNER_ID and cb_from_id != OWNER_ID:
                                    await _answer_callback_query(cb_id, "⚠️ Nur Onur darf Trades steuern")
                                    continue

                                parts = cb_data.split(":")
                                if len(parts) == 3:
                                    _, order_id, decision = parts
                                    pending = _pending_decisions.get(order_id)
                                    if pending:
                                        future, chat_id_reg, msg_id_reg = pending
                                        if not future.done():
                                            future.set_result(decision)
                                        label = _DECISION_LABELS.get(decision, decision)
                                        await _answer_callback_query(cb_id, label)
                                        # Buttons aus Nachricht entfernen
                                        mid = msg_id_reg or cb_msg_id
                                        if mid:
                                            await _edit_message_reply_markup(
                                                cb_chat_id, mid,
                                                f"<b>Entschieden:</b> {label}"
                                            )
                                    else:
                                        await _answer_callback_query(cb_id, "⚠️ Signal bereits abgelaufen")

                            elif cb_chat_id in CHAT_IDS and cb_data.startswith("m:"):
                                action = cb_data[2:]
                                ack = await _handle_menu_callback(action, callback_status)
                                await _answer_callback_query(cb_id, ack)
                            continue

                        # ── Text-Kommandos ────────────────────────────────────
                        msg = update.get("message", {})
                        text = msg.get("text", "").strip().lower()
                        chat_id = str(msg.get("chat", {}).get("id", ""))

                        if chat_id not in CHAT_IDS:
                            continue

                        if text in ["/start"]:
                            await _send_with_reply_keyboard(
                                "🤖 <b>KongTrade Bot bereit!</b>\nNutze die Buttons unten für Status, Portfolio etc.",
                                chat_id,
                            )

                        elif text in ["/menu", "/m"]:
                            await _send_with_reply_keyboard(
                                "🤖 <b>KongTrade Bot — Menü</b>",
                                chat_id,
                            )

                        elif text in ["/status", "/s"]:
                            await callback_status()

                        elif text in ["/pnl", "/p"]:
                            won, lost, win_rate = _get_win_rate()
                            wr_icon = "🟢" if win_rate >= 55 else "🟡" if win_rate >= 50 else "🔴"
                            trades = _load_archive()
                            total_pnl = sum(
                                float(t.get("gewinn_verlust_usdc", 0) or 0)
                                for t in trades if t.get("aufgeloest")
                            )
                            pnl_sign = "+" if total_pnl >= 0 else ""
                            await send("\n".join([
                                "💰 <b>AKTUELLER P&L</b>",
                                "━━━━━━━━━━━━━━━━━━━━",
                                f"✅ Gewonnen: <b>{won}</b>",
                                f"❌ Verloren: <b>{lost}</b>",
                                f"{wr_icon} Win Rate: <b>{win_rate}%</b>",
                                "━━━━━━━━━━━━━━━━━━━━",
                                f"📊 Gesamt P&L: <b>{pnl_sign}${total_pnl:.2f} USDC</b>",
                            ]))

                        elif text.startswith("/add "):
                            parts = text.split(maxsplit=1)
                            addr  = parts[1].strip() if len(parts) == 2 else ""
                            ok, result_msg = _add_wallet_to_env(addr)
                            await send(result_msg)

                        elif text.startswith("/position ") or text.startswith("/pos "):
                            parts = text.split(maxsplit=1)
                            order_id = parts[1].strip() if len(parts) == 2 else ""
                            await _cmd_position(order_id)

                        elif text.startswith("/cancel "):
                            parts = text.split(maxsplit=1)
                            order_id = parts[1].strip() if len(parts) == 2 else ""
                            if OWNER_ID and str(msg.get("from", {}).get("id", "")) != OWNER_ID:
                                await send("⚠️ Nur Onur darf Orders stornieren.")
                            else:
                                await _cmd_cancel(order_id)

                        elif text.lower() in _BUTTON_ACTION_MAP:
                            action = _BUTTON_ACTION_MAP[text.lower()]
                            await _handle_menu_callback(action, callback_status)

                        elif text in ["/help", "/h"]:
                            await send("\n".join([
                                "🤖 <b>KONG TRADING BOT — BEFEHLE</b>",
                                "━━━━━━━━━━━━━━━━━━━━",
                                "/menu    →  Interaktives Menü mit Buttons",
                                "/m       →  Kurzform für /menu",
                                "/status  →  Sofortiger Status Report",
                                "/s       →  Kurzform für /status",
                                "/pnl     →  Aktueller P&L und Win Rate",
                                "/p       →  Kurzform für /pnl",
                                "/position &lt;order_id&gt;  →  Details zu einer Position",
                                "/cancel &lt;order_id&gt;   →  PENDING-Order manuell stornieren",
                                "/add 0x…  →  Neue Wallet zu TARGET_WALLETS hinzufügen",
                                "/help    →  Diese Übersicht",
                                "━━━━━━━━━━━━━━━━━━━━",
                                "Buttons: ✅ Normal  ⏭️ Skip  2️⃣ Double  ½ Half",
                                "━━━━━━━━━━━━━━━━━━━━",
                                "📱 Morning Report: täglich 08:00, Digest: 22:00 Berlin",
                            ]), urgent=True)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[TG] Command-Fehler: {e}")
                await asyncio.sleep(10)


# ── KI-Analyse (Morning Report) ───────────────────────

def _compute_wallet_trends_7d() -> dict:
    """Berechnet Wallet-Performance der letzten 7 Tage aus dem Trade-Archiv."""
    trades = _load_archive()
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    recent = [t for t in trades if t.get("datum", "") >= cutoff]

    wallets: dict = {}
    for t in recent:
        w = t.get("source_wallet", "unknown")
        if w not in wallets:
            wallets[w] = {"trades": 0, "won": 0, "lost": 0, "pnl": 0.0}
        wallets[w]["trades"] += 1
        if t.get("aufgeloest"):
            pnl = float(t.get("gewinn_verlust_usdc", 0) or 0)
            wallets[w]["pnl"] += pnl
            if t.get("ergebnis") == "GEWINN":
                wallets[w]["won"] += 1
            else:
                wallets[w]["lost"] += 1

    for stats in wallets.values():
        resolved = stats["won"] + stats["lost"]
        stats["resolved"] = resolved
        stats["win_rate"] = round(stats["won"] / resolved * 100, 1) if resolved > 0 else None
        stats["pnl"] = round(stats["pnl"], 2)

    return wallets


async def generate_ai_analysis(wallet_trends: dict) -> str:
    """Ruft Claude API auf und liefert eine Wallet-Trendanalyse auf Deutsch."""
    if not _ANTHROPIC_OK or not ANTHROPIC_KEY:
        return ""

    if not wallet_trends:
        return "Keine Trades in den letzten 7 Tagen — keine Analyse möglich."

    lines = []
    for wallet, s in wallet_trends.items():
        wr = f"{s['win_rate']}%" if s["win_rate"] is not None else "n/a"
        sign = "+" if s["pnl"] >= 0 else ""
        name = _get_wallet_name(wallet)
        lines.append(
            f"  {name}: {s['trades']} Trades | {s['resolved']} aufgelöst"
            f" | Win Rate: {wr} | P&L: {sign}{s['pnl']:.2f} USDC"
        )

    data_str = "\n".join(lines)
    prompt = (
        f"Letzte 7 Tage — Wallet Performance:\n{data_str}\n\n"
        "Analysiere diese Daten in maximal 5 prägnanten Bullet Points:\n"
        "• Welche Wallets performen gut oder schlecht?\n"
        "• Auffällige Trends?\n"
        "• Konkrete Empfehlungen (Multiplier anpassen, Wallet stoppen o.ä.)?"
    )

    try:
        client = _anthropic.AsyncAnthropic(api_key=ANTHROPIC_KEY)
        response = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=400,
            system=(
                "Du bist ein prägnanter Trading-Analyst für den KongTrade Bot. "
                "Antworte ausschließlich auf Deutsch. Maximal 5 Bullet Points, keine Einleitung."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        return next((b.text for b in response.content if b.type == "text"), "")
    except Exception as e:
        return f"KI-Analyse nicht verfügbar: {e}"


async def send_morning_report(trades_today, resolved, won, lost, pnl, total_trades, portfolio=None, redeemable_str="", closing_today_str=""):
    """Sendet Morning Report + KI-Analyse an alle konfigurierten Chats."""
    # Standardreport sofort senden
    await send(msg_morning_summary(
        trades_today=trades_today,
        resolved=resolved,
        won=won,
        lost=lost,
        pnl=pnl,
        total_trades=total_trades,
        portfolio=portfolio,
        redeemable_str=redeemable_str,
        closing_today_str=closing_today_str,
    ))

    # KI-Analyse asynchron nachladen und senden
    wallet_trends = _compute_wallet_trends_7d()
    analysis = await generate_ai_analysis(wallet_trends)

    if analysis:
        ai_msg = "\n".join([
            "🤖 <b>KI-ANALYSE — LETZTE 7 TAGE</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            analysis,
            "━━━━━━━━━━━━━━━━━━━━",
            f"📊 {len(wallet_trends)} Wallet(s) analysiert",
        ])
        await send(ai_msg)


# ── Test ──────────────────────────────────────────────

async def test():
    print(f"[TG] Sende Test an {len(CHAT_IDS)} Empfänger...")
    ok = await send("\n".join([
        "✅ <b>VERBINDUNGSTEST ERFOLGREICH!</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        "🤖 KongTrade Bot v3 ist aktiv.",
        f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
        "━━━━━━━━━━━━━━━━━━━━",
        "✅ /status — Sofortiger Report",
        "✅ /pnl — P&L anzeigen",
        "✅ /help — Alle Befehle",
        "━━━━━━━━━━━━━━━━━━━━",
        "Ihr werdet ab jetzt über alle Trades informiert! 🚀",
    ]))
    if ok:
        print("[TG] ✅ Test erfolgreich!")
    else:
        print("[TG] ❌ Fehler. Token/Chat-ID prüfen.")


if __name__ == "__main__":
    if "--test" in sys.argv:
        asyncio.run(test())
    else:
        print("Verwendung: python telegram_bot.py --test")
