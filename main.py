"""
main.py - KongTrade Bot v0.6
- Telegram Live-Ticker mit /status /pnl /help Commands
- Resolver alle 15 Minuten
- Persistenter State
- market_id wird gespeichert
"""
import asyncio
import atexit
import json
import os
import signal
import sys
import aiohttp
import psutil
from datetime import datetime, timezone, date
from collections import defaultdict

from utils.config import load_config
from utils.logger import setup_logger, get_logger
from utils.balance_fetcher import update_budget_from_chain
from utils.state_manager import save_state, load_state
from utils.tax_archive import log_trade, export_tax_csv, get_summary
from utils.wallet_scout import scout_loop
from utils.latency_monitor import record_fill, latency_report_loop
from core.wallet_monitor import WalletMonitor
from core.risk_manager import RiskManager
from core.execution_engine import ExecutionEngine, OpenPosition
from core.fill_tracker import FillTracker, PendingOrder
from strategies.copy_trading import CopyTradingStrategy, CopyOrder
from claim_all import claim_loop
from telegram_bot import (send, msg_trade, msg_status, msg_startup,
                           msg_shutdown, msg_morning_summary, msg_warning,
                           check_resolved_markets_and_notify, poll_commands,
                           send_morning_report, send_trade_confirmation,
                           should_send_trade_notification, send_startup)

C_RESET  = "\033[0m"
C_CYAN   = "\033[96m"
C_GREEN  = "\033[92m"
C_YELLOW = "\033[93m"
C_RED    = "\033[91m"
C_BLUE   = "\033[94m"
C_PURPLE = "\033[95m"
C_WHITE  = "\033[97m"
C_GRAY   = "\033[90m"
STATE_FILE = "bot_state.json"


def cprint(text, color=C_WHITE):
    print(f"{color}{text}{C_RESET}", flush=True)


def parse_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--status-interval", type=int, default=60)
    parser.add_argument("--export-tax", type=int)
    return parser.parse_args()


def get_category(question):
    q = question.lower()
    if any(w in q for w in ["tennis","open","grand prix","nba","nhl","nfl","soccer","football","baseball","golf","cricket","vs "]):
        return "Sport"
    elif any(w in q for w in ["iran","israel","ukraine","trump","nuclear","war","ceasefire","election","president","nato","china","russia","peace"]):
        return "Geopolitik"
    elif any(w in q for w in ["bitcoin","btc","eth","crypto","price","solana","render","token"]):
        return "Crypto"
    elif any(w in q for w in ["fed","interest rate","inflation","gdp","recession","oil","gold"]):
        return "Makro"
    return "Sonstiges"


def restore_positions(engine):
    if not os.path.exists(STATE_FILE):
        return 0
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        positions_data = state.get("open_positions", [])
        valid_positions = [p for p in positions_data
                           if str(p.get("token_id", "")).strip() not in ("", "0x", "0x0")]
        skipped = len(positions_data) - len(valid_positions)
        if skipped:
            print(f"[RESTORE] {skipped} Positionen ohne token_id übersprungen (stale)", flush=True)
        positions_data = valid_positions
        print(f"[RESTORE] {len(positions_data)} Positionen gefunden...", flush=True)
        restored = 0
        for pos_data in positions_data:
            try:
                closes_at = None
                if pos_data.get("market_closes_at"):
                    try:
                        closes_at = datetime.fromisoformat(pos_data["market_closes_at"].replace("Z", "+00:00"))
                    except Exception:
                        pass
                pos = OpenPosition(
                    order_id=str(pos_data.get("order_id", f"r_{restored}")),
                    market_id=str(pos_data.get("market_id", "")),
                    token_id=str(pos_data.get("token_id", "")),
                    outcome=str(pos_data.get("outcome", "")),
                    market_question=str(pos_data.get("market_question", "")),
                    entry_price=float(pos_data.get("entry_price", 0) or 0),
                    size_usdc=float(pos_data.get("size_usdc", 0) or 0),
                    shares=float(pos_data.get("shares", 0) or 0),
                    source_wallet=str(pos_data.get("source_wallet", "")),
                    tx_hash_entry=str(pos_data.get("tx_hash_entry", "")),
                    market_closes_at=closes_at,
                )
                if pos_data.get("opened_at"):
                    try:
                        pos.opened_at = datetime.fromisoformat(pos_data["opened_at"].replace("Z", "+00:00"))
                    except Exception:
                        pass
                engine.open_positions[pos.order_id] = pos
                engine.stats["total_invested_usdc"] = float(engine.stats.get("total_invested_usdc", 0)) + pos.size_usdc
                restored += 1
            except Exception:
                pass
        print(f"[RESTORE] OK: {restored} Positionen | Engine: {len(engine.open_positions)}", flush=True)
        return restored
    except Exception as e:
        print(f"[RESTORE] Fehler: {e}", flush=True)
        return 0


async def recover_stale_positions(engine, config):
    """
    Beim Bot-Start: REST-API nach offenen Orders befragen und als pending wiederherstellen.
    Verhindert verlorene Positionen nach Neustart wenn WebSocket-Events ausgeblieben sind.
    """
    if config.dry_run:
        return 0
    try:
        url = f"{config.clob_host}/orders?maker_address={config.polymarket_address}&status=LIVE"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return 0
                data = await resp.json()
                orders = data.get("data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                recovered = 0
                for order in orders:
                    order_id = str(order.get("id") or order.get("order_id") or "")
                    if not order_id:
                        continue
                    if order_id in engine.open_positions or order_id in engine._pending_data:
                        continue
                    price = float(order.get("price", 0) or 0)
                    orig_size = float(order.get("original_size", 0) or 0)
                    remaining = float(order.get("remaining_size", orig_size) or orig_size)
                    token_id = str(order.get("token_id", order.get("asset_id", "")) or "")
                    if not token_id.strip() or token_id.strip() in ("0x", "0x0"):
                        print(f"[RECOVER] Order {order_id[:12]}... ohne token_id übersprungen", flush=True)
                        continue
                    engine._pending_data[order_id] = {
                        "order_id": order_id,
                        "market_id": str(order.get("market", order.get("condition_id", "")) or ""),
                        "token_id": token_id,
                        "outcome": str(order.get("outcome", order.get("side", "")) or ""),
                        "market_question": str(order.get("question", order.get("market", "Recovered Order")) or "Recovered Order")[:80],
                        "entry_price": price,
                        "size_usdc": round(orig_size * price, 4),
                        "shares": remaining,
                        "market_closes_at": None,
                        "source_wallet": "",
                        "tx_hash_entry": "",
                    }
                    recovered += 1
                if recovered > 0:
                    print(f"[RECOVER] {recovered} stale Orders aus Polymarket REST wiederhergestellt", flush=True)
                return recovered
    except Exception as e:
        print(f"[RECOVER] Stale-Recovery fehlgeschlagen: {e}", flush=True)
        return 0


def save_positions(engine, monitor, strategy):
    try:
        positions = []
        for order_id, pos in engine.open_positions.items():
            positions.append({
                "order_id":        order_id,
                "market_id":       getattr(pos, "market_id", ""),
                "token_id":        getattr(pos, "token_id", ""),
                "market_question": getattr(pos, "market_question", ""),
                "outcome":         getattr(pos, "outcome", ""),
                "entry_price":     getattr(pos, "entry_price", 0),
                "size_usdc":       getattr(pos, "size_usdc", 0),
                "shares":          getattr(pos, "shares", 0),
                "source_wallet":   getattr(pos, "source_wallet", ""),
                "tx_hash_entry":   getattr(pos, "tx_hash_entry", ""),
                "opened_at":       pos.opened_at.isoformat() if hasattr(pos, "opened_at") and pos.opened_at else datetime.now().isoformat(),
                "market_closes_at": pos.market_closes_at.isoformat() if hasattr(pos, "market_closes_at") and pos.market_closes_at else None,
            })
        state = {
            "version":         "1.6",
            "saved_at":        datetime.now().isoformat(),
            "date":            str(date.today()),
            "open_positions":  positions,
            "seen_tx_hashes":  list(monitor._seen_tx_hashes) if hasattr(monitor, "_seen_tx_hashes") else [],
            "dry_run_counter": getattr(engine, "_dry_run_counter", 0),
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        print(f"[SAVE] OK: {len(positions)} Positionen", flush=True)
    except Exception as e:
        print(f"[SAVE] Fehler: {e}", flush=True)


async def sync_positions_from_polymarket(engine, config):
    """
    T-NIGHT-4: Beim Start alle offenen Positionen von data-api.polymarket.com laden
    und in engine.open_positions synchronisieren. Polymarket ist die Quelle der Wahrheit.
    """
    if config.dry_run:
        return 0
    try:
        proxy = getattr(config, 'polymarket_address', None)
        if not proxy:
            return 0
        url = f"https://data-api.polymarket.com/positions?user={proxy}&sizeThreshold=.01&limit=500"
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    print(f"[SYNC] Data-API HTTP {resp.status}", flush=True)
                    return 0
                positions = await resp.json()
                if not isinstance(positions, list):
                    positions = positions.get("data", []) if isinstance(positions, dict) else []

        synced = 0
        for p in positions:
            size = float(p.get("size") or p.get("shares") or 0)
            if size < 0.001:
                continue
            condition_id = str(p.get("conditionId") or p.get("market") or "")
            token_id = str(p.get("asset_id") or p.get("tokenId") or "")
            outcome = str(p.get("outcome") or p.get("title") or "")
            already = any(pos.market_id == condition_id for pos in engine.open_positions.values())
            if already:
                continue
            avg_price = float(p.get("avgPrice") or p.get("averagePrice") or 0)
            size_usdc = float(p.get("initialValue") or p.get("cost") or round(avg_price * size, 4) or 0)
            synth_id = f"RECOVERED_{condition_id[:20]}_{outcome[:10]}".replace(" ", "_")
            try:
                from core.execution_engine import OpenPosition
                pos = OpenPosition(
                    order_id=synth_id,
                    market_id=condition_id,
                    token_id=token_id,
                    outcome=outcome,
                    market_question=str(p.get("title") or p.get("market") or outcome)[:80],
                    entry_price=avg_price,
                    size_usdc=size_usdc,
                    shares=size,
                    market_closes_at=None,
                    source_wallet="[polymarket-sync]",
                    tx_hash_entry="",
                )
                engine.open_positions[synth_id] = pos
                synced += 1
            except Exception as e:
                print(f"[SYNC] Fehler bei Position {outcome}: {e}", flush=True)

        if synced > 0:
            print(f"[SYNC] {synced} Positionen von Polymarket Data-API synchronisiert", flush=True)
        else:
            print(f"[SYNC] Alle {len(positions)} Polymarket-Positionen bereits im State", flush=True)
        return synced
    except Exception as e:
        print(f"[SYNC] fehlgeschlagen: {e}", flush=True)
        return 0


async def balance_updater(config, interval=300):
    while True:
        try:
            await asyncio.sleep(interval)
            await update_budget_from_chain(config)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"balance_updater Fehler: {e} — weiter")


async def morning_report_sender():
    """Sendet um 08:00 Europe/Berlin einen vollständigen Morgen-Report."""
    while True:
        try:
            # Berechne nächstes 08:00 Uhr Berlin (UTC+2 Sommer / UTC+1 Winter)
            from datetime import timedelta
            now_utc = datetime.now(timezone.utc)
            berlin_offset = timedelta(hours=2)  # CEST (Sommerzeit April)
            now_berlin = now_utc + berlin_offset
            next_8am_berlin = now_berlin.replace(hour=8, minute=0, second=0, microsecond=0)
            if now_berlin >= next_8am_berlin:
                next_8am_berlin += timedelta(days=1)
            sleep_secs = (next_8am_berlin - now_berlin).total_seconds()
            logger.info(f"Morgen-Report in {sleep_secs/3600:.1f}h (um 08:00 Berlin)")
            await asyncio.sleep(sleep_secs)

            summary = get_summary()

            # Portfolio-Daten von Polymarket holen
            portfolio_data = {}
            redeemable_str = ""
            closing_today_str = ""
            try:
                import aiohttp
                proxy = getattr(config, 'polymarket_address', None)
                if proxy:
                    url = f"https://data-api.polymarket.com/positions?user={proxy}&sizeThreshold=.01&limit=500"
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                            if resp.status == 200:
                                positions = await resp.json()
                                if isinstance(positions, list):
                                    total_val = sum(float(p.get("currentValue") or 0) for p in positions)
                                    to_win = sum(float(p.get("toWin") or 0) for p in positions)
                                    redeemable = [p for p in positions if p.get("redeemable") or p.get("isRedeemable")]
                                    portfolio_data = {
                                        "count": len(positions),
                                        "total_value": total_val,
                                        "to_win": to_win,
                                        "redeemable_count": len(redeemable),
                                        "redeemable_value": sum(float(p.get("currentValue") or 0) for p in redeemable),
                                    }
                                    if redeemable:
                                        redeemable_str = "\n".join(
                                            f"  💰 {p.get('outcome','?')[:40]}: ${float(p.get('currentValue',0)):.2f}"
                                            for p in redeemable[:5]
                                        )
                                    # Closing today
                                    import time as _time
                                    now_ts = _time.time()
                                    eod_ts = now_ts + 86400
                                    closing = sorted(
                                        [p for p in positions if p.get("endDate") and float(p.get("endDate") or 0) < eod_ts and float(p.get("endDate") or 0) > now_ts],
                                        key=lambda p: float(p.get("endDate") or 0)
                                    )[:5]
                                    if closing:
                                        from datetime import datetime
                                        closing_today_str = "\n".join(
                                            f"  ⏰ {p.get('outcome','?')[:35]}: {datetime.fromtimestamp(float(p.get('endDate',0)), tz=timezone.utc).strftime('%H:%M UTC')}"
                                            for p in closing
                                        )
            except Exception as pe:
                logger.warning(f"Portfolio-Fetch für Morning-Report fehlgeschlagen: {pe}")

            await send_morning_report(
                trades_today=summary.get("total_trades", 0),
                resolved=summary.get("resolved", 0),
                won=summary.get("won", 0),
                lost=summary.get("lost", 0),
                pnl=summary.get("total_pnl", 0),
                total_trades=summary.get("total_trades", 0),
                portfolio=portfolio_data,
                redeemable_str=redeemable_str,
                closing_today_str=closing_today_str,
            )
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"morning_report_sender Fehler: {e} — weiter")


async def status_reporter(strategy, risk, engine, config, interval):
    while True:
        await asyncio.sleep(interval)
        r = risk.status()
        s = strategy.get_status()
        e = engine.get_stats()
        positions = engine.get_open_positions_summary()

        total_invested = sum(
            float(str(p.get("invested", "0")).replace("$", "").replace(" USDC", "") or 0)
            for p in positions
        )
        categories = defaultdict(float)
        wallet_counts = defaultdict(int)
        for p in positions:
            amt = float(str(p.get("invested", "0")).replace("$", "").replace(" USDC", "") or 0)
            src = str(p.get("source", "unknown"))[:10]
            wallet_counts[src] += 1
            cat = get_category(p.get("question", ""))
            if cat == "Sport":        categories["🎾 Tennis/Sport"] += amt
            elif cat == "Geopolitik": categories["🌍 Geopolitik"]   += amt
            elif cat == "Crypto":     categories["₿  Crypto"]       += amt
            elif cat == "Makro":      categories["📈 Makro"]         += amt
            else:                     categories["ℹ️  Sonstiges"]    += amt

        max_allowed = config.max_total_invested_usd
        pct_used    = (total_invested / max_allowed * 100) if max_allowed > 0 else 0
        top_wallet  = max(wallet_counts, key=wallet_counts.get) if wallet_counts else "---"
        tax_summary = get_summary()
        pnl         = r["net_pnl_today"]

        bar_filled = int(pct_used / 5)
        bar        = "█" * bar_filled + "░" * (20 - bar_filled)
        bar_color  = C_GREEN if pct_used < 50 else C_YELLOW if pct_used < 80 else C_RED
        pnl_color  = C_GREEN if pnl >= 0 else C_RED

        print(flush=True)
        cprint("╔══════════════════════════════════════════════════════════════╗", C_CYAN)
        cprint(f"║  📊 STATUS  {datetime.now().strftime('%H:%M:%S')}  |  Modus: {e['mode']}", C_CYAN)
        cprint("╠══════════════════════════════════════════════════════════════╣", C_CYAN)
        print(f"{C_CYAN}║{C_RESET}  💰 PnL:      {pnl_color}{pnl:+.2f} USDC{C_RESET}   |   Verlust: {C_YELLOW}${r['daily_loss_usd']:.2f}{C_RESET}/${r['limit_usd']:.2f}", flush=True)
        print(f"{C_CYAN}║{C_RESET}  📡 Signale:  {C_WHITE}{s['signals_received']}{C_RESET}  |  Orders: {C_GREEN}{s['orders_created']}{C_RESET}  |  Skip: {C_GRAY}{s['orders_skipped']}{C_RESET}", flush=True)
        print(f"{C_CYAN}║{C_RESET}  ⚡ Offen:    {C_WHITE}{e['open_positions']}{C_RESET}  |  Filled: {C_GREEN}{e['orders_filled']}{C_RESET}  |  Failed: {C_RED}{e['orders_failed']}{C_RESET}", flush=True)
        print(f"{C_CYAN}║{C_RESET}  🏦 Budget:   {C_WHITE}${config.portfolio_budget_usd:,.0f} USDC{C_RESET}", flush=True)
        print(f"{C_CYAN}║{C_RESET}  📊 Rennen:   {bar_color}{bar}{C_RESET}  {bar_color}${total_invested:.2f}{C_RESET} ({pct_used:.1f}%)", flush=True)
        cprint("╠══════════════════════════════════════════════════════════════╣", C_CYAN)
        for cat, amt in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            if amt > 0:
                print(f"{C_CYAN}║{C_RESET}  {C_BLUE}{cat}{C_RESET}: {C_WHITE}${amt:.2f}{C_RESET}", flush=True)
        if wallet_counts:
            print(f"{C_CYAN}║{C_RESET}  🏆 {C_PURPLE}{top_wallet}...{C_RESET} ({wallet_counts.get(top_wallet,0)} Pos.)", flush=True)
        print(f"{C_CYAN}║{C_RESET}  🗄️  Archiv: {C_GREEN}{tax_summary['total_trades']} Trades{C_RESET}", flush=True)
        if r["kill_switch"]:
            cprint(f"║  🛑 KILL-SWITCH: {r['kill_switch_reason']}", C_RED)
            await send(msg_warning(f"Kill-Switch: {r['kill_switch_reason']}"))
        cprint("╠══════════════════════════════════════════════════════════════╣", C_CYAN)
        cprint("║  📋 Offene Positionen:", C_CYAN)
        for pos in positions[:10]:
            print(f"{C_CYAN}║{C_RESET}  {C_GREEN}{pos['outcome']}{C_RESET} @ {C_WHITE}{pos['entry_price']}{C_RESET} | {C_YELLOW}{pos['invested']}{C_RESET} | {C_GRAY}{pos['question'][:40]}{C_RESET}", flush=True)
        if len(positions) > 10:
            cprint(f"║  ... und {len(positions)-10} weitere", C_GRAY)
        cprint("╚══════════════════════════════════════════════════════════════╝", C_CYAN)

        # Telegram: nur stündlich
        now = datetime.now()
        last = getattr(status_reporter, "_last_telegram", None)
        if last is None or (now - last).seconds >= 3600:
            cat_simple = {k.split()[-1]: v for k, v in categories.items()}
            await send(msg_status(
                signals=s["signals_received"],
                orders_sent=s["orders_created"],
                open_pos=e["open_positions"],
                total_invested=total_invested,
                pnl=pnl,
                categories=cat_simple,
                archive_count=tax_summary["total_trades"],
            ))
            status_reporter._last_telegram = now


LOCK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.lock")

# ── PID-Lock helpers ──────────────────────────────────────────────────────────

def _remove_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception:
        pass  # best-effort; logger may not be available at atexit time

def _signal_handler(signum, frame):
    _remove_lock()
    sys.exit(0)

def check_and_create_lock():
    """
    PID-aware lock: prüft ob der Prozess der den Lock hält wirklich noch läuft.
    Entfernt stale Locks automatisch, statt mit exit(1) zu scheitern.
    """
    if os.path.exists(LOCK_FILE):
        try:
            old_pid = int(open(LOCK_FILE).read().strip())
            if psutil.pid_exists(old_pid):
                try:
                    proc = psutil.Process(old_pid)
                    cmdline = " ".join(proc.cmdline())
                    if "main.py" in cmdline:
                        # Echte zweite Instanz — legitim abbrechen
                        print("Bot laeuft bereits mit PID " + str(old_pid) + ". Abbruch.")
                        sys.exit(1)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            # PID existiert nicht (oder gehört anderem Prozess) → stale lock
            print(f"⚠️  Stale Lock-Datei (PID {old_pid} tot). Entferne und starte.")
        except (ValueError, OSError):
            print("⚠️  Korrupte Lock-Datei. Entferne und starte.")
        try:
            os.remove(LOCK_FILE)
        except OSError:
            pass

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

    atexit.register(_remove_lock)
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGHUP,  _signal_handler)
    # SIGINT bleibt beim Default (KeyboardInterrupt → finally-Block läuft durch)

# ─────────────────────────────────────────────────────────────────────────────


async def main():
    args = parse_args()
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    setup_logger(level=log_level)
    logger = get_logger("main")

    if args.export_tax:
        filename = export_tax_csv(year=args.export_tax)
        if filename:
            summary = get_summary(args.export_tax)
            print(f"Steuer-CSV: {filename} | Trades: {summary['total_trades']} | P&L: ${summary['total_pnl']:.2f}")
        return

    # Lock file: prevent multiple instances running simultaneously
    if os.path.exists(LOCK_FILE):
        print(f"\n❌ Bot läuft bereits! Beende den anderen Prozess zuerst.")
        print(f"   (Lock-Datei: {LOCK_FILE})")
        print(f"   Falls der Bot abgestürzt ist: Datei manuell löschen und neu starten.\n")
        sys.exit(1)
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

    config = load_config()
    if args.live:
        config.dry_run = False

    await update_budget_from_chain(config)

    print(flush=True)
    cprint("╔══════════════════════════════════════════════════════════════╗", C_CYAN)
    cprint("║    🚀 POLYMARKET COPY TRADING BOT v0.6 + TELEGRAM           ║", C_CYAN)
    cprint("╚══════════════════════════════════════════════════════════════╝", C_CYAN)

    risk     = RiskManager(config)
    engine   = ExecutionEngine(config)
    strategy = CopyTradingStrategy(config, risk)
    monitor  = WalletMonitor(config)

    # KRITISCH: CLOB Client initialisieren (MUSS vor dem ersten Trade-Aufruf erfolgen!)
    await engine.initialize()

    load_state(engine, monitor)
    restored = restore_positions(engine)
    stale = await recover_stale_positions(engine, config)
    synced = await sync_positions_from_polymarket(engine, config)

    await send_startup(len(config.target_wallets), config.portfolio_budget_usd, config.dry_run)
    if restored > 0 or stale > 0:
        msg_parts = []
        if restored > 0:
            msg_parts.append(f"{restored} Positionen aus State")
        if stale > 0:
            msg_parts.append(f"{stale} stale Orders aus REST-API")
        await send(f"♻️ <b>Wiederhergestellt:</b> {', '.join(msg_parts)}")

    async def on_copy_order(order: CopyOrder):
        positions = engine.get_open_positions_summary()
        total_invested = sum(
            float(str(p.get("invested", "0")).replace("$", "").replace(" USDC", "") or 0)
            for p in positions
        )
        if total_invested >= config.max_total_invested_usd:
            return

        # ── Telegram Inline-Button Bestätigung (30s Fenster) ─────────────────
        sig = getattr(order, "signal", None)
        order_id = str(getattr(sig, "tx_hash", "") or id(order))[:16]
        cat = get_category(getattr(sig, "market_question", "") or "")
        from strategies.copy_trading import get_wallet_name as _gwn
        decision = await send_trade_confirmation(
            order_id         = order_id,
            market           = str(getattr(sig, "market_question", "") or ""),
            outcome          = str(getattr(sig, "outcome", "") or ""),
            size             = float(getattr(order, "size_usdc", 0) or 0),
            price            = float(getattr(sig, "price", 0) or 0),
            wallet_name      = _gwn(str(getattr(sig, "source_wallet", "") or "")),
            category         = cat,
            dry_run          = config.dry_run,
            is_multi_signal  = getattr(order, "is_multi_signal", False),
            wallet_multiplier= getattr(order, "wallet_multiplier", 1.0),
        )

        if decision == "skip":
            logger.info(f"Trade per Telegram ÜBERSPRUNGEN: {order_id}")
            return

        if decision == "double":
            from dataclasses import replace as _replace
            order = _replace(order, size_usdc=order.size_usdc * 2)
            logger.info(f"Trade per Telegram VERDOPPELT: ${order.size_usdc:.2f}")
        elif decision == "half":
            from dataclasses import replace as _replace
            order = _replace(order, size_usdc=order.size_usdc / 2)
            logger.info(f"Trade per Telegram HALBIERT: ${order.size_usdc:.2f}")

        result = await engine.execute(order)
        if result and not result.success and not result.dry_run:
            error_msg = str(getattr(result, 'error', '') or '')
            sig_market = str(getattr(order.signal, 'market_question', '') or '')[:50]
            if '403' in error_msg or 'geoblock' in error_msg.lower() or 'restricted' in error_msg.lower():
                await send(
                    f"🚫 <b>GEOBLOCK — Order abgelehnt</b>\n"
                    f"📍 <i>{sig_market}</i>\n"
                    f"🌍 Polymarket blockiert diese Region (Türkei).\n"
                    f"⚡ <b>Lösung: VPN aktivieren (US/NL/DE) → Bot neu starten</b>"
                )
            else:
                await send(
                    f"❌ <b>Order fehlgeschlagen</b>\n"
                    f"📍 <i>{sig_market}</i>\n"
                    f"🔴 Fehler: <code>{error_msg[:200]}</code>"
                )
        if result and result.success:
            sig       = getattr(order, "signal", None)
            cat       = get_category(getattr(sig, "market_question", "") or "")
            market_id = str(getattr(sig, "market_id", "") or "")
            token_id  = str(getattr(sig, "token_id", "")  or "")

            _order_id = str(result.order_id or "")
            _tx_hash  = f"pending_{_order_id}" if _order_id else ""
            log_trade(
                market_question=str(getattr(sig, "market_question", "Unknown") or "Unknown")[:100],
                outcome=str(getattr(sig, "outcome", "")),
                side=str(getattr(sig, "side", "")),
                price=float(getattr(sig, "price", 0) or 0),
                size_usdc=float(getattr(order, "size_usdc", 0) or 0),
                shares=float(getattr(order, "size_usdc", 0) or 0) / max(float(getattr(sig, "price", 1) or 1), 0.0001),
                source_wallet=str(getattr(sig, "source_wallet", "")),
                tx_hash=_tx_hash,
                category=cat,
                is_dry_run=config.dry_run,
                market_id=market_id,
                token_id=token_id,
            )
            logger.info(f"Trade | {cat} | {market_id[:12] if market_id else 'n/a'}")
            risk.record_market_investment(market_id, float(getattr(order, "size_usdc", 0) or 0))
            record_fill(sig, result)

            time_to_close = getattr(sig, "time_to_close_hours", None)
            trade_size = float(getattr(order, "size_usdc", 0) or 0)
            if should_send_trade_notification(
                trade_size,
                is_multi_signal=getattr(order, "is_multi_signal", False),
                wallet_multiplier=getattr(order, "wallet_multiplier", 1.0),
            ):
                await send(msg_trade(
                    market=str(getattr(sig, "market_question", "") or ""),
                    outcome=str(getattr(sig, "outcome", "") or ""),
                    size=trade_size,
                    price=float(getattr(sig, "price", 0) or 0),
                    category=cat,
                    source=str(getattr(sig, "source_wallet", "") or ""),
                    market_id=market_id,
                    time_to_close_hours=time_to_close,
                ))

    _MULTI_SIGNAL_DEDUP_FILE = os.path.join(os.path.dirname(__file__), ".multi_signal_last_alert.json")
    _MULTI_SIGNAL_COOLDOWN_S = 15 * 60  # 15 Minuten

    async def on_multi_signal(count: int, names: str, outcome: str, market: str, multiplier: float):
        sorted_wallets = ",".join(sorted(names.split(" + ")))
        dedup_key = f"{market}|{outcome}|{sorted_wallets}"
        now = time.time()

        try:
            dedup = json.loads(Path(_MULTI_SIGNAL_DEDUP_FILE).read_text()) if Path(_MULTI_SIGNAL_DEDUP_FILE).exists() else {}
        except Exception:
            dedup = {}

        last_sent = dedup.get(dedup_key, 0)
        if now - last_sent < _MULTI_SIGNAL_COOLDOWN_S:
            return  # Rate-limit: dieselbe Kombination bereits vor <15 Min gesendet

        dedup[dedup_key] = now
        # Alte Keys (>24h) bereinigen
        dedup = {k: v for k, v in dedup.items() if now - v < 86400}
        try:
            Path(_MULTI_SIGNAL_DEDUP_FILE).write_text(json.dumps(dedup))
        except Exception:
            pass

        emoji = "🔥🔥" if count >= 3 else "🔥"
        await send(
            f"{emoji} <b>MULTI-SIGNAL ({count} Wallets, {multiplier}x Größe)!</b>\n"
            f"👥 {names}\n"
            f"📊 kaufen alle <b>{outcome}</b>\n"
            f"🏪 {market}"
        )

    async def on_wallet_warning(name: str, overall_wr: float, recent_wr: float,
                                old_mult: float, new_mult: float):
        await send("\n".join([
            "📉 <b>WALLET TREND-DECLINE ERKANNT</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            f"👤 Wallet: <b>{name}</b>",
            f"📊 Gesamt Win Rate: <b>{overall_wr:.0%}</b>",
            f"📉 Letzte 20 Trades: <b>{recent_wr:.0%}</b>",
            f"⚖️  Multiplikator: <b>{old_mult}x → {new_mult}x</b> (halbiert)",
            "━━━━━━━━━━━━━━━━━━━━",
            "⚠️ Wallet noch aktiv — aber mit reduzierter Größe.",
        ]))

    async def on_herd_alert(count: int, total: int, names: str, outcome: str, market: str):
        pct = count / max(1, total) * 100
        await send("\n".join([
            f"🐑 <b>HERDENTRIEB ERKANNT ({count}/{total} = {pct:.0f}% Wallets)</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            f"🏪 Markt: <b>{market}</b>",
            f"🎯 Seite: <b>{outcome}</b>",
            f"👥 Wallets: <b>{names}</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            "⚠️  Kein Größen-Boost — Trade wird mit normalem Einsatz ausgeführt.",
        ]))

    strategy.on_copy_order     = on_copy_order
    strategy.on_multi_signal   = on_multi_signal
    strategy.on_wallet_warning = on_wallet_warning
    strategy.on_herd_alert     = on_herd_alert
    monitor.on_new_trade       = strategy.handle_signal

    async def resolver_loop():
        while True:
            try:
                await asyncio.sleep(900)  # 15 Minuten
                await check_resolved_markets_and_notify()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"resolver_loop Fehler: {e} — weiter")

    async def send_status_now():
        r = risk.status()
        s = strategy.get_status()
        e = engine.get_stats()
        positions = engine.get_open_positions_summary()
        total_invested = sum(
            float(str(p.get("invested", "0")).replace("$", "").replace(" USDC", "") or 0)
            for p in positions
        )
        categories = defaultdict(float)
        for p in positions:
            amt = float(str(p.get("invested", "0")).replace("$", "").replace(" USDC", "") or 0)
            cat = get_category(p.get("question", ""))
            categories[cat] += amt
        tax_summary = get_summary()
        await send(msg_status(
            signals=s["signals_received"],
            orders_sent=s["orders_created"],
            open_pos=e["open_positions"],
            total_invested=total_invested,
            pnl=r["net_pnl_today"],
            categories=dict(categories),
            archive_count=tax_summary["total_trades"],
        ))

    try:
        async def heartbeat_loop(interval: int = 300):
            """Writes heartbeat.txt every 5 minutes so watchdog.py can detect offline state."""
            heartbeat_file = os.path.join(os.path.dirname(__file__), "heartbeat.txt")
            while True:
                try:
                    with open(heartbeat_file, "w", encoding="utf-8") as f:
                        f.write(datetime.now(timezone.utc).isoformat())
                except Exception as e:
                    logger.warning(f"Heartbeat write failed: {e}")
                await asyncio.sleep(interval)

        # FillTracker: WebSocket-basiertes Fill-Tracking (verhindert Phantom-Positionen)
        fill_tracker = FillTracker(config)
        fill_tracker.register_callbacks(
            on_matched=engine.on_order_matched,
            on_failed=engine.on_order_failed,
            on_cancelled=engine.on_order_cancelled,
        )
        engine.set_fill_tracker(fill_tracker)  # Dynamic subscribe nach Orders

        tasks = [
            asyncio.create_task(monitor.start()),
            asyncio.create_task(status_reporter(strategy, risk, engine, config, args.status_interval)),
            asyncio.create_task(balance_updater(config, interval=300)),
            asyncio.create_task(morning_report_sender()),
            asyncio.create_task(resolver_loop()),
            asyncio.create_task(scout_loop(config)),
            asyncio.create_task(latency_report_loop()),
            asyncio.create_task(heartbeat_loop()),
            asyncio.create_task(fill_tracker.run()),
            asyncio.create_task(claim_loop(config, interval_s=int(os.getenv("AUTO_CLAIM_INTERVAL_S", "300")))),  # Auto-Claim alle 5min (env: AUTO_CLAIM_INTERVAL_S)
            asyncio.create_task(poll_commands(
                callback_status=send_status_now,
                callback_resolve=check_resolved_markets_and_notify,
            )),
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Shutdown...")
        save_positions(engine, monitor, strategy)
        await monitor.stop()
        summary = get_summary()
        await send(msg_shutdown(total_trades=summary["total_trades"]))
        cprint(f"\nSession beendet | {summary['total_trades']} Trades", C_GREEN)
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)


if __name__ == "__main__":
    asyncio.run(main())
