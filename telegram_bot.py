"""
telegram_bot.py v3 - Kong Trading Bot Notifications
"""
import asyncio
import json
import os
import sys
from datetime import datetime, date, timedelta
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


async def send(text: str, parse_mode: str = "HTML") -> bool:
    if not TOKEN or not CHAT_IDS:
        return False
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
              market_id="", time_to_close_hours=None):
    cat_emoji = {
        "Sport": "🎾", "Geopolitik": "🌍", "Crypto": "₿",
        "Makro": "📈", "Sonstiges": "ℹ️"
    }.get(category, "📋")

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
        f"{cat_emoji} <b>NEUER TRADE</b> [DRY-RUN]",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📌 <b>{market[:60]}</b>",
        f"✅ Outcome: <b>{outcome}</b>",
        f"💵 Einsatz: <b>${size:.2f}</b> @ ${price:.3f}",
        closes,
        f"👛 Wallet: <b>{_get_wallet_name(source)}</b>{id_line}",
    ]
    return "\n".join(lines)


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


def msg_status(signals, orders, open_pos, total_invested, pnl, categories, archive_count):
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
        f"📡 Signale:  <b>{signals}</b>",
        f"✅ Orders:   <b>{orders}</b>",
        f"⚡ Offen:    <b>{open_pos} Positionen</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "🎯 <b>Win Rate:</b>",
        wr_line,
        "━━━━━━━━━━━━━━━━━━━━━━",
        "💰 <b>Im Rennen:</b>",
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


def msg_morning_summary(trades_today, resolved, won, lost, pnl, total_trades):
    win_rate = round(won / resolved * 100, 1) if resolved > 0 else 0
    wr_icon  = "🟢" if win_rate >= 55 else "🟡" if win_rate >= 50 else "🔴"
    pnl_icon = "🟢" if pnl >= 0 else "🔴"
    pnl_sign = "+" if pnl >= 0 else ""
    lines = [
        f"☀️ <b>MORGEN-REPORT — {date.today().strftime('%d.%m.%Y')}</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📋 Neue Trades: <b>{trades_today}</b>",
        f"🎯 Aufgelöst:   <b>{resolved}</b>",
        f"  ✅ Gewonnen: <b>{won}</b>",
        f"  ❌ Verloren: <b>{lost}</b>",
        f"  {wr_icon} Win Rate: <b>{win_rate}%</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"{pnl_icon} P&L heute: <b>{pnl_sign}${pnl:.2f} USDC</b>",
        f"📦 Gesamt Archiv: <b>{total_trades} Trades</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        "🤖 Bot läuft weiter — guten Morgen! ☕",
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


# ── Command Handler ────────────────────────────────────

async def poll_commands(callback_status, callback_resolve):
    if not TOKEN or not CHAT_IDS:
        return

    offset = 0
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
                params = {"timeout": 30, "offset": offset}
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=35)) as r:
                    if r.status != 200:
                        await asyncio.sleep(5)
                        continue
                    data = await r.json()
                    updates = data.get("result", [])

                    for update in updates:
                        offset = update["update_id"] + 1
                        msg = update.get("message", {})
                        text = msg.get("text", "").strip().lower()
                        chat_id = str(msg.get("chat", {}).get("id", ""))

                        if chat_id not in CHAT_IDS:
                            continue

                        if text in ["/status", "/s"]:
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

                        elif text in ["/help", "/h"]:
                            await send("\n".join([
                                "🤖 <b>KONG TRADING BOT — BEFEHLE</b>",
                                "━━━━━━━━━━━━━━━━━━━━",
                                "/status  →  Sofortiger Status Report",
                                "/s       →  Kurzform für /status",
                                "/pnl     →  Aktueller P&L und Win Rate",
                                "/p       →  Kurzform für /pnl",
                                "/add 0x… →  Neue Wallet zu TARGET_WALLETS hinzufügen",
                                "/help    →  Diese Übersicht",
                                "━━━━━━━━━━━━━━━━━━━━",
                                "📱 Status-Report kommt automatisch stündlich.",
                            ]))

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


async def send_morning_report(trades_today, resolved, won, lost, pnl, total_trades):
    """Sendet Morning Report + KI-Analyse an alle konfigurierten Chats."""
    # Standardreport sofort senden
    await send(msg_morning_summary(
        trades_today=trades_today,
        resolved=resolved,
        won=won,
        lost=lost,
        pnl=pnl,
        total_trades=total_trades,
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
