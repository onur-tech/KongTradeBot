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
from pathlib import Path
import aiohttp
import psutil
from datetime import datetime, timezone, date
from collections import defaultdict

from utils.config import load_config
from utils.logger import setup_logger, get_logger
from utils.balance_fetcher import update_budget_from_chain
from utils.state_manager import save_state, load_state
from utils.tax_archive import log_trade, export_tax_csv, get_summary, get_pnl_today
from utils.wallet_scout import scout_loop
from utils.latency_monitor import record_fill, latency_report_loop
from utils.error_handler import handle_error, set_telegram_sender, safe_call_transparent
from utils.slippage_tracker import log_slippage
from core.wallet_monitor import WalletMonitor
from core.risk_manager import RiskManager
from core.execution_engine import ExecutionEngine, OpenPosition
from core.fill_tracker import FillTracker, PendingOrder
from core.exit_manager import ExitManager, ExitEvent
from core.position_state_worker import PositionStateWorker
from core.anomaly_detector import AnomalyDetector, anomaly_detector_loop
from core.rss_monitor import RSSMonitor
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


from utils.category import get_category


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
                    position_state=str(pos_data.get("position_state", "ACTIVE")),  # T-M08
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
                "position_state":  getattr(pos, "position_state", "ACTIVE"),  # T-M08
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
            # 'asset' is the correct Data-API field for token_id (decimal ERC-1155 ID)
            token_id = str(p.get("asset") or p.get("asset_id") or p.get("tokenId") or "")
            outcome = str(p.get("outcome") or p.get("title") or "")
            already = any(pos.market_id == condition_id for pos in engine.open_positions.values())
            if already:
                continue
            avg_price = float(p.get("avgPrice") or p.get("averagePrice") or 0)
            size_usdc = float(p.get("initialValue") or p.get("cost") or round(avg_price * size, 4) or 0)
            synth_id = f"RECOVERED_{condition_id[:20]}_{outcome[:10]}".replace(" ", "_")
            # Parse endDate for ExitManager time-to-close check
            closes_at = None
            end_date_str = p.get("endDate") or ""
            if end_date_str:
                try:
                    from datetime import timezone as _tz
                    closes_at = datetime.fromisoformat(
                        end_date_str.replace("Z", "+00:00")
                    ).replace(tzinfo=_tz.utc) if "+" not in end_date_str and "Z" not in end_date_str else datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                    if closes_at.tzinfo is None:
                        closes_at = closes_at.replace(tzinfo=_tz.utc)
                except Exception:
                    pass
            try:
                from core.execution_engine import OpenPosition
                # T-M08 Phase 4: position_state aus redeemable-Flag ableiten
                is_redeemable  = bool(p.get("redeemable", False))
                current_val    = float(p.get("currentValue") or 0)
                _pos_state     = "RESOLVED_LOST" if (is_redeemable and current_val == 0) else "ACTIVE"
                pos = OpenPosition(
                    order_id=synth_id,
                    market_id=condition_id,
                    token_id=token_id,
                    outcome=outcome,
                    market_question=str(p.get("title") or p.get("market") or outcome)[:80],
                    entry_price=avg_price,
                    size_usdc=size_usdc,
                    shares=size,
                    market_closes_at=closes_at,
                    source_wallet="[polymarket-sync]",
                    tx_hash_entry="",
                    position_state=_pos_state,
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


async def balance_updater(config, engine=None, interval=300):
    while True:
        try:
            await asyncio.sleep(interval)
            await update_budget_from_chain(config)
            # portfolio_budget_usd = CLOB-Cash + investierter Betrag in Positionen
            # (CLOB allein unterschätzt das Portfolio wenn Cash in Positionen gebunden ist)
            if engine is not None:
                _invested = sum(float(p.size_usdc or 0) for p in engine.open_positions.values())
                config.portfolio_budget_usd += _invested
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


async def status_reporter(strategy, risk, engine, config, interval, state_worker=None):
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
            if cat == "Sport_US":     categories["🏟️ Sport_US"]    += amt
            elif cat == "Tennis":     categories["🎾 Tennis"]       += amt
            elif cat == "Soccer":     categories["⚽ Soccer"]       += amt
            elif cat == "Geopolitik": categories["🌍 Geopolitik"]   += amt
            elif cat == "Crypto":     categories["₿  Crypto"]       += amt
            elif cat == "Makro":      categories["📈 Makro"]         += amt
            elif cat == "Sport":      categories["🎾 Tennis/Sport"] += amt
            else:                     categories["ℹ️  Sonstiges"]    += amt

        max_allowed = config.max_total_invested_usd
        pct_used    = (total_invested / max_allowed * 100) if max_allowed > 0 else 0
        top_wallet  = max(wallet_counts, key=wallet_counts.get) if wallet_counts else "---"
        tax_summary  = get_summary()
        pnl_today    = get_pnl_today()
        pnl          = pnl_today["net_usdc"]

        bar_filled = int(pct_used / 5)
        bar        = "█" * bar_filled + "░" * (20 - bar_filled)
        bar_color  = C_GREEN if pct_used < 50 else C_YELLOW if pct_used < 80 else C_RED
        pnl_color  = C_GREEN if pnl >= 0 else C_RED

        # T-M08 Phase 3: Position-State-Counts aus state_worker
        n_open, n_pending = 0, 0
        pos_states: dict = {}
        if state_worker:
            pos_states  = state_worker.get_all_states()
            raw_pos     = list(engine.open_positions.values())
            for rp in raw_pos:
                st = state_worker.get_state(rp.market_id, rp.outcome)
                if st == "PENDING_CLOSE":
                    n_pending += 1
                else:
                    n_open += 1
        else:
            n_open = len(positions)

        print(flush=True)
        cprint("╔══════════════════════════════════════════════════════════════╗", C_CYAN)
        cprint(f"║  📊 STATUS  {datetime.now().strftime('%H:%M:%S')}  |  Modus: {e['mode']}", C_CYAN)
        cprint("╠══════════════════════════════════════════════════════════════╣", C_CYAN)
        pnl_detail = f"✅{pnl_today['won_count']}×+${pnl_today['won_usdc']:.2f}  ❌{pnl_today['lost_count']}×${pnl_today['lost_usdc']:.2f}"
        print(f"{C_CYAN}║{C_RESET}  💰 PnL heute: {pnl_color}{pnl:+.2f} USDC{C_RESET}  ({pnl_detail})", flush=True)
        print(f"{C_CYAN}║{C_RESET}  📡 Signale:  {C_WHITE}{s['signals_received']}{C_RESET}  |  Orders: {C_GREEN}{s['orders_created']}{C_RESET}  |  Skip: {C_GRAY}{s['orders_skipped']}{C_RESET}", flush=True)
        # T-M08: State-Tabs statt einfacher "Offen"-Zahl
        pending_str = f"  |  🕐 {C_YELLOW}PENDING:{n_pending}{C_RESET}" if n_pending > 0 else ""
        print(f"{C_CYAN}║{C_RESET}  ⚡ Positionen: {C_GREEN}OPEN:{n_open}{C_RESET}{pending_str}  |  Filled: {C_GREEN}{e['orders_filled']}{C_RESET}  |  Failed: {C_RED}{e['orders_failed']}{C_RESET}", flush=True)
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
        # T-M08: PENDING_CLOSE-Positionen zuerst, dann OPEN
        open_label    = f"📋 OPEN ({n_open}):"
        pending_label = f"🕐 PENDING_CLOSE ({n_pending}) — Markt aufgelöst, Claim ausstehend:" if n_pending else None
        cprint(f"║  {open_label}", C_CYAN)
        shown = 0
        for pos in positions[:10]:
            raw = engine.open_positions.get(
                next((oid for oid, p in engine.open_positions.items()
                      if p.outcome == pos.get("outcome") and
                         p.market_question[:40] == pos.get("question", "")[:40]), None),
                None
            )
            pos_state = (state_worker.get_state(raw.market_id, raw.outcome)
                         if state_worker and raw else "OPEN")
            state_icon = "🕐" if pos_state == "PENDING_CLOSE" else "▶"
            state_col  = C_YELLOW if pos_state == "PENDING_CLOSE" else C_GREEN
            print(f"{C_CYAN}║{C_RESET}  {state_icon} {state_col}{pos['outcome']}{C_RESET} @ {C_WHITE}{pos['entry_price']}{C_RESET} | {C_YELLOW}{pos['invested']}{C_RESET} | {C_GRAY}{pos['question'][:38]}{C_RESET}", flush=True)
            shown += 1
        if len(positions) > 10:
            cprint(f"║  ... und {len(positions)-10} weitere", C_GRAY)
        if pending_label:
            cprint(f"║  {pending_label}", C_YELLOW)
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
                pnl_today=pnl_today,
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

    risk             = RiskManager(config)
    engine           = ExecutionEngine(config)
    strategy         = CopyTradingStrategy(config, risk)
    monitor          = WalletMonitor(config)
    anomaly_detector = AnomalyDetector()
    rss_monitor      = RSSMonitor(send_fn=send)

    # KRITISCH: CLOB Client initialisieren (MUSS vor dem ersten Trade-Aufruf erfolgen!)
    await engine.initialize()

    load_state(engine, monitor)
    restored = restore_positions(engine)
    stale = await recover_stale_positions(engine, config)
    synced = await sync_positions_from_polymarket(engine, config)

    # Budget-Cap: Risk Manager mit wiederhergestellten Positionen synchronisieren
    _startup_invested = sum(
        float(pos.size_usdc or 0) for pos in engine.open_positions.values()
    )
    risk.update_total_invested(_startup_invested)
    # portfolio_budget_usd = CLOB-Cash + Positionen → korrekte Gesamtgröße
    config.portfolio_budget_usd += _startup_invested

    # Kategorie-Exposure aus wiederhergestellten Positionen initialisieren
    _startup_cats: dict[str, float] = {}
    for pos in engine.open_positions.values():
        _cat = get_category(getattr(pos, "market_question", "") or "")
        _startup_cats[_cat] = _startup_cats.get(_cat, 0.0) + float(pos.size_usdc or 0)
    if _startup_cats:
        risk.set_category_investments(_startup_cats)
        logger.info(f"[Risk] Kategorie-Exposure geladen: { {k: f'${v:.2f}' for k,v in _startup_cats.items()} }")

    # CLOB-Allowance Startup-Check
    if not config.dry_run:
        _health = await engine.check_clob_allowance_health()
        _allowance = _health.get("allowance_usdc", 0.0)
        if _health.get("critical"):
            await send(
                f"🚨 <b>CLOB-Allowance KRITISCH: ${_allowance:.2f} USDC</b>\n"
                f"⚠️ Min. Trade: ${config.max_trade_size_usd:.2f} — Trades werden fehlschlagen!\n"
                f"💡 Polymarket USDC-Allowance muss aufgefüllt werden."
            )
        elif _health.get("warning_needed"):
            await send(
                f"⚠️ <b>CLOB-Allowance niedrig: ${_allowance:.2f} USDC</b>\n"
                f"Bitte Allowance aufstocken (Max Trade: ${config.max_trade_size_usd:.2f})."
            )

    set_telegram_sender(send)  # error_handler: Telegram-Alerts aktivieren

    # Kill-Switch: Startup-Check — warnen falls noch aktiv nach Restart
    if risk.kill_switch.is_active():
        ks = risk.kill_switch.get_state()
        reset_info = f"Auto-Reset in {ks['auto_reset_in_hours']:.1f}h" if ks.get("auto_reset_in_hours") else "Manueller Reset: /killswitch_reset"
        await send(
            f"🛑 <b>Kill-Switch noch aktiv nach Restart!</b>\n"
            f"📍 Grund: <code>{ks.get('reason', '?')}</code>\n"
            f"⏱️ {reset_info}\n"
            f"⚠️ Keine neuen Trades bis Reset."
        )
        logger.warning(f"Kill-Switch bei Startup aktiv: {ks.get('reason')}")

    await send_startup(len(config.target_wallets), config.portfolio_budget_usd, config.dry_run)
    if restored > 0 or stale > 0:
        msg_parts = []
        if restored > 0:
            msg_parts.append(f"{restored} Positionen aus State")
        if stale > 0:
            msg_parts.append(f"{stale} stale Orders aus REST-API")
        await send(f"♻️ <b>Wiederhergestellt:</b> {', '.join(msg_parts)}")

    _cap_alert_last = [None]  # throttle: max 1 Telegram-Alert pro Stunde

    async def on_copy_order(order: CopyOrder):
        positions = engine.get_open_positions_summary()
        total_invested = sum(
            float(str(p.get("invested", "0")).replace("$", "").replace(" USDC", "") or 0)
            for p in positions
        )
        risk.update_total_invested(total_invested)

        if total_invested >= config.max_total_invested_usd:
            sig = getattr(order, "signal", None)
            market = str(getattr(sig, "market_question", "") or "")[:50]
            logger.warning(
                f"🚫 Budget-Cap überschritten: ${total_invested:.2f} >= "
                f"${config.max_total_invested_usd:.2f} — Trade abgelehnt ({market})"
            )
            now = datetime.now()
            if _cap_alert_last[0] is None or (now - _cap_alert_last[0]).total_seconds() >= 3600:
                _cap_alert_last[0] = now
                await send(
                    f"⚠️ <b>Budget-Cap überschritten</b>\n"
                    f"💰 Investiert: <b>${total_invested:.2f}</b> / ${config.max_total_invested_usd:.2f} "
                    f"({total_invested / max(0.01, config.max_total_invested_usd) * 100:.0f}%)\n"
                    f"📊 {len(positions)} offene Positionen\n"
                    f"⏸️ Neue Trades pausiert bis Positionen schließen."
                )
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
            # T-M06 Phase 1: order_id direkt als Bestätigung — kein pending_-Präfix
            _tx_hash  = _order_id
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
            risk.record_category_investment(cat, float(getattr(order, "size_usdc", 0) or 0))
            record_fill(sig, result)

            try:
                _detected_at = getattr(sig, "detected_at", None)
                _lag = (datetime.now(timezone.utc) - _detected_at).total_seconds() if _detected_at else 0.0
                log_slippage(
                    whale_price=float(getattr(sig, "price", 0) or 0),
                    our_price=float(getattr(result, "filled_price", 0) or getattr(sig, "price", 0) or 0),
                    market=str(getattr(sig, "market_question", "") or ""),
                    market_id=market_id,
                    outcome=str(getattr(sig, "outcome", "") or ""),
                    whale_wallet=str(getattr(sig, "source_wallet", "") or ""),
                    our_size_usdc=float(getattr(order, "size_usdc", 0) or 0),
                    category=cat,
                    is_multi_signal=bool(getattr(order, "is_multi_signal", False)),
                    detection_lag_seconds=_lag,
                    dry_run=config.dry_run,
                )
                # Tages-Alert wenn Ø-Slippage > 6¢
                if not config.dry_run:
                    from utils.slippage_analyzer import get_today_alert_status
                    alert_info = get_today_alert_status()
                    if alert_info.get("alert") and alert_info.get("count", 0) >= 5:
                        await handle_error(
                            Exception(f"Slippage Ø {alert_info['mean_cents']:.1f}¢ > 6¢ ({alert_info['count']} Trades heute)"),
                            context="SLIPPAGE_HIGH",
                            severity="WARNING",
                            telegram_alert=True,
                        )
            except Exception:
                pass

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

    on_copy_order = safe_call_transparent("on_copy_order", "ERROR")(on_copy_order)

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

    # ── T-M03: Whale-Exit-Copy ────────────────────────────────────────────────

    async def on_whale_exit(pos, sell_signal):
        """Sofortiger Exit wenn tracked Wallet ihre Position verkauft hat."""
        wallet_name = get_wallet_name(pos.source_wallet)
        market_short = (pos.market_question or sell_signal.market_question or "")[:60]
        try:
            if config.exit_dry_run:
                logger.info(
                    f"[whale_exit_copy] 🧪 DRY-RUN: würde {pos.outcome} auf "
                    f"'{market_short}' verkaufen ({pos.shares:.4f} shares)"
                )
                log_trade(
                    market_question=market_short,
                    outcome=pos.outcome, side="SELL",
                    price=sell_signal.price,
                    size_usdc=pos.size_usdc, shares=pos.shares,
                    source_wallet=pos.source_wallet,
                    tx_hash=f"whale_exit_{pos.order_id[:12]}",
                    category="exit_whale_exit_copy",
                    market_id=pos.market_id,
                    token_id=pos.token_id,
                    realized_pnl=round((sell_signal.price - pos.entry_price) * pos.shares, 4),
                    mark_resolved=True,
                    is_dry_run=True,
                )
            else:
                result = await engine.create_and_post_sell_order(
                    asset_id=pos.token_id,
                    shares=pos.shares,
                    min_price=max(0.01, sell_signal.price * 0.97),
                    exit_dry_run=False,
                )
                if result["success"]:
                    realized_pnl = round(
                        result["usdc_received"] - pos.size_usdc, 4
                    )
                    log_trade(
                        market_question=market_short,
                        outcome=pos.outcome, side="SELL",
                        price=result.get("filled_price", sell_signal.price),
                        size_usdc=result["usdc_received"],
                        shares=result["shares_sold"],
                        source_wallet=pos.source_wallet,
                        tx_hash=result.get("order_id", ""),
                        category="exit_whale_exit_copy",
                        market_id=pos.market_id,
                        token_id=pos.token_id,
                        realized_pnl=realized_pnl,
                        mark_resolved=True,
                        is_dry_run=False,
                    )
                    engine.open_positions.pop(pos.order_id, None)
                    exit_manager._remove_state(pos.market_id, pos.outcome)
                    logger.info(
                        f"[whale_exit_copy] ✅ Exit erfolgreich: "
                        f"${result['usdc_received']:.2f} | PnL {realized_pnl:+.2f}"
                    )
                else:
                    logger.error(
                        f"[whale_exit_copy] Sell-Order fehlgeschlagen: {result['error']}"
                    )
                    return

            pnl_val = round((sell_signal.price - pos.entry_price) * pos.shares, 2)
            pnl_sign = "+" if pnl_val >= 0 else ""
            dry_tag = "🧪 <b>DRY-RUN</b> " if config.exit_dry_run else ""
            await send("\n".join([
                f"{dry_tag}🐋 <b>WHALE-EXIT KOPIERT</b>",
                "━━━━━━━━━━━━━━━━━━━━",
                f"👛 Wallet: <b>{wallet_name}</b> verkauft",
                f"🏪 {market_short}",
                f"🎯 {pos.outcome} | Entry: ${pos.entry_price:.3f} → Exit: ${sell_signal.price:.3f}",
                f"{'🟢' if pnl_val >= 0 else '🔴'} PnL: <b>{pnl_sign}${pnl_val:.2f}</b>",
            ]))
        except Exception as e:
            logger.error(f"[whale_exit_copy] Fehler: {e}", exc_info=True)

    strategy.get_open_positions = lambda: engine.open_positions
    strategy.on_whale_exit      = on_whale_exit
    monitor.on_whale_sell       = strategy.handle_whale_sell

    # ── Exit-Manager Setup ────────────────────────────────────────────────────

    async def _fetch_live_prices(token_ids: list) -> tuple:
        """Holt Midpoint-Preise + Order-Book-Daten vom CLOB /book Endpoint.
        Returns (prices, order_books) — prices: {tid: midpoint}, order_books: {tid: {"best_bid", "best_ask"}}
        """
        prices = {}
        order_books = {}
        async with aiohttp.ClientSession() as session:
            for tid in token_ids:
                if not tid:
                    continue
                try:
                    url = f"{config.clob_host}/book?token_id={tid}"
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                        if r.status == 200:
                            data = await r.json()
                            bids = data.get("bids", [])
                            asks = data.get("asks", [])
                            best_bid = float(bids[0]["price"]) if bids else 0.0
                            best_ask = float(asks[0]["price"]) if asks else 0.0
                            order_books[tid] = {"best_bid": best_bid, "best_ask": best_ask}
                            if best_bid > 0 and best_ask > 0:
                                prices[tid] = (best_bid + best_ask) / 2
                            elif best_bid > 0:
                                prices[tid] = best_bid
                            elif best_ask > 0:
                                prices[tid] = best_ask
                except Exception as e:
                    logger.debug(f"[exit_loop] Preisfetch fehlgeschlagen {tid[:12]}: {e}")
        return prices, order_books

    async def on_exit_event(event: ExitEvent):
        dry_tag = "🧪 <b>DRY-RUN</b> " if config.exit_dry_run else ""
        type_labels = {
            "tp1": "💰 EXIT: TP1 (40%)",
            "tp2": "💰 EXIT: TP2 (40%)",
            "tp3": "💰 EXIT: TP3 (15%)",
            "trail": "🔻 EXIT: Trailing-Stop",
            "whale_exit": "🚨 WHALE-EXIT",
            "manual": "🖐 EXIT: Manuell",
            "price_trigger": f"📈 AUTO-SELL ≥{config.exit_price_trigger_cents:.0f}¢",
            "sl_time_price": "⏱ Stop-Loss (Zeit+Preis)",
            "sl_drawdown":   "📉 Stop-Loss (Drawdown)",
        }
        label = type_labels.get(event.exit_type, f"EXIT: {event.exit_type}")
        pnl_sign = "+" if event.pnl_usdc >= 0 else ""

        if event.exit_type == "whale_exit":
            lines = [
                f"{dry_tag}🚨 <b>WHALE-EXIT</b>",
                "━━━━━━━━━━━━━━━━━━━━",
                f"🏪 {event.market[:60]}",
                f"🎯 {event.outcome}",
                f"💸 Komplett-Exit: {event.shares_sold:.4f} shares @ ${event.exit_price:.3f} = <b>${event.usdc_received:.2f}</b>",
                f"{'🟢' if event.pnl_usdc >= 0 else '🔴'} PnL: <b>{pnl_sign}${event.pnl_usdc:.2f} ({event.pnl_pct:+.1f}%)</b>",
            ]
        elif event.exit_type == "price_trigger":
            stable_info = f" | {event.minutes_stable:.0f}min stabil" if event.minutes_stable > 0 else ""
            lines = [
                f"{dry_tag}<b>{label}</b>",
                "━━━━━━━━━━━━━━━━━━━━",
                f"🏪 {event.market[:60]}",
                f"🎯 {event.outcome}",
                f"📈 Entry: ${event.entry_price:.3f} → Exit: ${event.exit_price:.3f} ({event.pnl_pct:+.1f}%){stable_info}",
                f"💸 Komplett-Sell: {event.shares_sold:.4f} shares = <b>${event.usdc_received:.2f}</b>",
                f"{'🟢' if event.pnl_usdc >= 0 else '🔴'} PnL: <b>{pnl_sign}${event.pnl_usdc:.2f}</b>",
            ]
        else:
            lines = [
                f"{dry_tag}<b>{label}</b>",
                "━━━━━━━━━━━━━━━━━━━━",
                f"🏪 {event.market[:60]}",
                f"🎯 {event.outcome}",
                f"📈 Entry: ${event.entry_price:.3f} → Exit: ${event.exit_price:.3f} ({event.pnl_pct:+.1f}%)",
                f"💸 Verkauft: {event.shares_sold:.4f} shares @ ${event.exit_price:.3f} = <b>${event.usdc_received:.2f}</b>",
                f"{'🟢' if event.pnl_usdc >= 0 else '🔴'} PnL: <b>{pnl_sign}${event.pnl_usdc:.2f}</b>",
            ]
        await send("\n".join(lines))

    exit_manager = ExitManager(
        config=config,
        wallet_monitor=monitor,
        on_exit_event=on_exit_event,
    )

    # T-M08 Phase 2+5: State-Update-Worker + Startup-Apply
    state_worker = PositionStateWorker(engine, interval=300)
    state_worker.apply_states_to_positions()   # States sofort auf synced Positionen anwenden

    MANUAL_EXIT_QUEUE = Path("manual_exit_queue.json")

    async def _process_manual_exit_queue():
        """Verarbeitet ausstehende manuelle Exit-Requests aus manual_exit_queue.json."""
        if not MANUAL_EXIT_QUEUE.exists():
            return
        try:
            queue = json.loads(MANUAL_EXIT_QUEUE.read_text())
        except Exception:
            return
        if not queue:
            return

        remaining = []
        for req in queue:
            cid    = req.get("condition_id", "")
            reason = req.get("reason", "manual")
            pos    = next((p for p in engine.open_positions.values()
                           if p.market_id == cid), None)
            if not pos:
                logger.warning(f"[ManualExit] Position nicht gefunden: {cid[:20]}")
                continue  # Aus Queue löschen — nicht mehr offen

            token_ids = [pos.token_id] if pos.token_id else []
            live_prices, order_books = await _fetch_live_prices(token_ids)
            current_price = live_prices.get(pos.token_id, pos.entry_price)

            event = await exit_manager._execute_exit(pos, exit_manager._get_or_create_state(pos),
                                                      1.0, reason, current_price)
            if event:
                _pos = pos
                _log_kwargs = dict(
                    market_question=getattr(_pos, "market_question", event.market or cid)[:100],
                    outcome=event.outcome, side="SELL", price=event.exit_price,
                    size_usdc=event.usdc_received, shares=event.shares_sold,
                    source_wallet=getattr(_pos, "source_wallet", ""),
                    category=f"exit_{reason}", market_id=cid,
                    token_id=getattr(_pos, "token_id", ""),
                    realized_pnl=event.pnl_usdc, mark_resolved=True,
                )
                log_trade(**_log_kwargs)
                engine.close_position(event.position_id)
                logger.info(f"[ManualExit] ✅ {cid[:20]} | {reason} | PnL ${event.pnl_usdc:+.2f}")
            else:
                remaining.append(req)  # Nicht ausgeführt → in Queue lassen

        MANUAL_EXIT_QUEUE.write_text(json.dumps(remaining, indent=2))

    async def exit_loop():
        """Wertet offene Positionen alle EXIT_LOOP_INTERVAL Sekunden aus."""
        while True:
            try:
                await asyncio.sleep(config.exit_loop_interval)
                await _process_manual_exit_queue()
                positions = list(engine.open_positions.values())
                if not positions:
                    continue
                token_ids = [p.token_id for p in positions if p.token_id]
                live_prices, order_books = await _fetch_live_prices(token_ids)
                if not live_prices:
                    logger.debug("[exit_loop] Keine Live-Preise verfügbar, skip")
                    continue
                events = await exit_manager.evaluate_all(positions, live_prices, order_books=order_books)
                if events:
                    for ev in events:
                        _pos = engine.open_positions.get(ev.position_id)
                        _log_kwargs = dict(
                            market_question=getattr(_pos, "market_question", ev.market or ev.condition_id)[:100],
                            outcome=ev.outcome,
                            side="SELL",
                            price=ev.exit_price,
                            size_usdc=ev.usdc_received,
                            shares=ev.shares_sold,
                            source_wallet=getattr(_pos, "source_wallet", ""),
                            category=f"exit_{ev.exit_type}",
                            market_id=ev.condition_id,
                            token_id=getattr(_pos, "token_id", ""),
                            realized_pnl=ev.pnl_usdc,
                            mark_resolved=True,
                        )
                        if config.exit_dry_run:
                            # DRY-RUN: Archive mit Marker, kein echter Sell
                            log_trade(**_log_kwargs,
                                      tx_hash=f"exit_{ev.exit_type}_{ev.position_id[:12]}",
                                      is_dry_run=True)
                        else:
                            # T-M06 Phase 1: Ghost-Write Fix — Archive NUR nach bestätigtem Sell
                            pos = engine.open_positions.get(ev.position_id)
                            if pos:
                                result = await engine.create_and_post_sell_order(
                                    asset_id=pos.token_id,
                                    shares=ev.shares_sold,
                                    min_price=ev.exit_price * 0.97,
                                    exit_dry_run=False,
                                )
                                if result["success"]:
                                    log_trade(**_log_kwargs,
                                              tx_hash=result.get("order_id", ""),
                                              is_dry_run=False)
                                    pos.shares = round(pos.shares - result["shares_sold"], 6)
                                    if pos.shares <= 0:
                                        engine.open_positions.pop(ev.position_id, None)
                                        exit_manager._remove_state(ev.condition_id, ev.outcome)
                                else:
                                    logger.error(f"[exit_loop] Sell-Order fehlgeschlagen: {result['error']}")
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"[exit_loop] Fehler: {exc}", exc_info=True)

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
        pnl_today = get_pnl_today()
        await send(msg_status(
            signals=s["signals_received"],
            orders_sent=s["orders_created"],
            open_pos=e["open_positions"],
            total_invested=total_invested,
            pnl=pnl_today["net_usdc"],
            categories=dict(categories),
            archive_count=tax_summary["total_trades"],
            pnl_today=pnl_today,
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

        async def clob_allowance_monitor():
            """Prüft alle 15 Min die CLOB-Allowance. Alert nur bei State-Wechsel."""
            _state = "healthy"  # "healthy" | "warning" | "critical"
            while True:
                try:
                    await asyncio.sleep(900)
                    if config.dry_run:
                        continue
                    health = await engine.check_clob_allowance_health()
                    if "error" in health:
                        continue
                    allowance = health.get("allowance_usdc", 0.0)
                    if health.get("critical"):
                        new_state = "critical"
                    elif health.get("warning_needed"):
                        new_state = "warning"
                    else:
                        new_state = "healthy"
                    if new_state != _state:
                        if new_state == "critical":
                            await send(
                                f"🚨 <b>CLOB-Allowance KRITISCH: ${allowance:.2f} USDC</b>\n"
                                f"Alle Trades blockiert — Polymarket Allowance aufstocken!"
                            )
                        elif new_state == "warning":
                            await send(
                                f"⚠️ <b>CLOB-Allowance niedrig: ${allowance:.2f} USDC</b>\n"
                                f"Bitte bald aufstocken (Max Trade: ${config.max_trade_size_usd:.2f})."
                            )
                        elif new_state == "healthy":
                            logger.info(f"✅ CLOB-Allowance wieder OK: ${allowance:.2f}")
                        _state = new_state
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"clob_allowance_monitor Fehler: {e} — weiter")

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
            asyncio.create_task(status_reporter(strategy, risk, engine, config, args.status_interval, state_worker=state_worker)),
            asyncio.create_task(balance_updater(config, engine=engine, interval=300)),
            asyncio.create_task(morning_report_sender()),
            asyncio.create_task(resolver_loop()),
            asyncio.create_task(scout_loop(config)),
            asyncio.create_task(latency_report_loop()),
            asyncio.create_task(heartbeat_loop()),
            asyncio.create_task(clob_allowance_monitor()),
            asyncio.create_task(fill_tracker.run()),
            asyncio.create_task(claim_loop(config, interval_s=int(os.getenv("AUTO_CLAIM_INTERVAL_S", "300")))),  # Auto-Claim alle 5min (env: AUTO_CLAIM_INTERVAL_S)
            asyncio.create_task(exit_loop()),
            asyncio.create_task(state_worker.run()),   # T-M08 Phase 2
            asyncio.create_task(anomaly_detector_loop(  # T-M-NEW
                anomaly_detector, engine, send,
                interval_seconds=int(os.getenv("ANOMALY_SCAN_INTERVAL_SECONDS", "300"))
            )),
            asyncio.create_task(rss_monitor.run()),     # T-NEWS Phase 1B
            asyncio.create_task(poll_commands(
                callback_status=send_status_now,
                callback_resolve=check_resolved_markets_and_notify,
                kill_switch=risk.kill_switch,
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
