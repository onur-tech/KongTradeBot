"""
signal_tracker.py — Shadow-Tracking für alle erkannten Signale (COPIED + SKIPPED).

Jedes Signal wird gespeichert unabhängig ob kopiert oder geskippt.
Nach Market-Resolution: theoretische Performance für SKIPPED-Signale berechnen.
"""
import json
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

try:
    import aiohttp
    _AIOHTTP_OK = True
except ImportError:
    _AIOHTTP_OK = False

from utils.logger import get_logger

logger = get_logger("signal_tracker")

_BASE = Path(__file__).parent.parent / "data"
SIGNALS_FILE = _BASE / "all_signals.jsonl"
OUTCOMES_FILE = _BASE / "skipped_signal_outcomes.jsonl"

_CLOB_URL = "https://clob.polymarket.com/markets/{}"


def _normalize_reason(reason: Optional[str]) -> Optional[str]:
    if not reason:
        return None
    r = reason.upper()
    if "MIN_TRADE" in r or "MICRO" in r:
        return "MIN_TRADE_SIZE"
    if "MAX_TRADE" in r:
        return "MAX_TRADE_SIZE"
    if "BUDGET" in r:
        return "BUDGET_CAP"
    if "PREIS" in r or "PRICE" in r or "EXTREMIT" in r:
        return "PRICE_EXTREMITY"
    if "HOURS" in r or "MIN_HOURS" in r or "SCHLIESS" in r or "CLOSE" in r:
        return "TIME_TO_CLOSE"
    if "KILL" in r:
        return "KILL_SWITCH"
    if "DAILY" in r or "TAGES" in r or "VERLUST" in r:
        return "DAILY_LOSS_LIMIT"
    if "VOLUMEN" in r or "VOLUME" in r:
        return "MIN_MARKT_VOLUMEN"
    if "POSITION" in r:
        return "MAX_POSITIONS_TOTAL"
    if "DECAY" in r or "WIN_RATE" in r:
        return "WIN_RATE_DECAY"
    if "BLACKLIST" in r or "KATEGORIE" in r:
        return "CATEGORY_BLACKLIST"
    return reason[:50]


def log_signal(signal, decision: str, reason: Optional[str] = None) -> None:
    """Append signal record to data/all_signals.jsonl. Never raises."""
    try:
        closes_at = None
        mc = getattr(signal, "market_closes_at", None)
        if mc is not None:
            closes_at = mc.isoformat() if hasattr(mc, "isoformat") else str(mc)

        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "tx_hash": signal.tx_hash,
            "wallet": signal.source_wallet,
            "market_id": signal.market_id,
            "token_id": signal.token_id,
            "outcome": getattr(signal, "outcome", ""),
            "side": getattr(signal, "side", "BUY"),
            "price": signal.price,
            "whale_size_usdc": signal.size_usdc,
            "market_question": (getattr(signal, "market_question", "") or "")[:120],
            "market_closes_at": closes_at,
            "decision": decision,
            "skip_reason": _normalize_reason(reason),
            "retroactive": False,
        }
        _BASE.mkdir(parents=True, exist_ok=True)
        with SIGNALS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.debug(f"log_signal silent fail: {exc}")


def _read_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    records = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records


def _read_signals() -> list:
    return _read_jsonl(SIGNALS_FILE)


def _read_outcomes() -> list:
    return _read_jsonl(OUTCOMES_FILE)


async def _fetch_market_status(session, market_id: str, token_id: str) -> dict:
    """Returns {resolved: bool, winning_token_id: str} or {} on error."""
    url = _CLOB_URL.format(market_id)
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
            if resp.status != 200:
                return {}
            data = await resp.json(content_type=None)
            if data.get("active", True):
                return {"resolved": False}
            for token in data.get("tokens", []):
                if float(token.get("price", 0)) >= 0.95:
                    return {"resolved": True, "winning_token_id": token.get("token_id", "")}
            return {"resolved": False}
    except Exception:
        return {}


async def evaluate_skipped_signals(days_back: int = 30) -> list:
    """
    Evaluates SKIPPED signals against resolved markets.
    Appends new outcomes to data/skipped_signal_outcomes.jsonl.
    Returns list of newly evaluated records.
    """
    if not _AIOHTTP_OK:
        logger.warning("aiohttp unavailable — evaluate_skipped_signals skipped")
        return []

    now = datetime.now(timezone.utc)
    cutoff_str = (now - timedelta(days=days_back)).isoformat()
    resolve_buffer_str = (now - timedelta(hours=24)).isoformat()

    signals = _read_signals()
    already_done = {o["tx_hash"] for o in _read_outcomes()}

    candidates = [
        s for s in signals
        if s.get("decision") == "SKIPPED"
        and s.get("ts", "") >= cutoff_str
        and s.get("tx_hash") not in already_done
        and s.get("market_closes_at") is not None
        and s.get("market_closes_at", "9999") < resolve_buffer_str
    ]

    if not candidates:
        logger.info("evaluate_skipped_signals: keine neuen Kandidaten")
        return []

    results = []
    async with aiohttp.ClientSession() as session:
        for sig in candidates:
            status = await _fetch_market_status(session, sig["market_id"], sig["token_id"])
            if not status.get("resolved"):
                continue

            winning_token = status.get("winning_token_id", "")
            signal_correct = winning_token == sig["token_id"]
            price = float(sig.get("price", 0.5))
            theoretical_size = float(sig.get("whale_size_usdc", 0)) * 0.05

            if signal_correct and price > 0:
                theoretical_profit = round(theoretical_size / price - theoretical_size, 4)
            else:
                theoretical_profit = round(-theoretical_size, 4)

            record = {
                "ts_evaluated": now.isoformat(),
                "tx_hash": sig["tx_hash"],
                "market_id": sig["market_id"],
                "token_id": sig["token_id"],
                "outcome": sig.get("outcome", ""),
                "price": price,
                "whale_size_usdc": sig.get("whale_size_usdc", 0),
                "skip_reason": sig.get("skip_reason", ""),
                "market_resolved": True,
                "winning_token_id": winning_token,
                "signal_correct": signal_correct,
                "theoretical_copy_usdc": round(theoretical_size, 4),
                "theoretical_profit_usdc": theoretical_profit,
            }
            _BASE.mkdir(parents=True, exist_ok=True)
            with OUTCOMES_FILE.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            results.append(record)

    logger.info(f"evaluate_skipped_signals: {len(results)} neue Outcomes evaluiert")
    return results


def generate_weekly_report() -> str:
    """Returns Telegram HTML string for weekly skipped-signal summary."""
    now = datetime.now(timezone.utc)
    cutoff_str = (now - timedelta(days=7)).isoformat()

    signals = _read_signals()
    week_signals = [s for s in signals if s.get("ts", "") >= cutoff_str]
    copied = [s for s in week_signals if s.get("decision") == "COPIED"]
    skipped = [s for s in week_signals if s.get("decision") == "SKIPPED"]
    reasons = Counter(s.get("skip_reason", "UNKNOWN") for s in skipped)

    outcomes = _read_outcomes()
    week_outcomes = [o for o in outcomes if o.get("ts_evaluated", "") >= cutoff_str]
    winners = [o for o in week_outcomes if o.get("signal_correct")]
    losers = [o for o in week_outcomes if not o.get("signal_correct")]
    missed = sum(o.get("theoretical_profit_usdc", 0) for o in winners)
    avoided = sum(abs(o.get("theoretical_profit_usdc", 0)) for o in losers)
    net_missed = missed - avoided

    filter_costs: dict = {}
    for o in week_outcomes:
        if o.get("signal_correct"):
            r = o.get("skip_reason", "UNKNOWN")
            filter_costs[r] = filter_costs.get(r, 0) + o.get("theoretical_profit_usdc", 0)
    worst_filter = max(filter_costs, key=filter_costs.get) if filter_costs else None

    kw = now.isocalendar()[1]
    lines = [
        f"📊 <b>Skipped-Signal Report KW{kw}</b>",
        f"<i>{now.strftime('%d.%m.%Y')}</i>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📡 Signale diese Woche: <b>{len(week_signals)}</b>",
        f"  ✅ Kopiert: <b>{len(copied)}</b>",
        f"  ⏭️ Geskippt: <b>{len(skipped)}</b>",
        "",
        f"🔍 Bereits evaluiert: <b>{len(week_outcomes)}</b>",
        f"  🟢 Gewinner (verpasst): {len(winners)} (+${missed:.2f})",
        f"  🔴 Verlierer (vermieden): {len(losers)} (-${avoided:.2f})",
        f"  📊 Netto: {'🔴' if net_missed > 0 else '🟢'} ${net_missed:+.2f}",
        "",
        "📋 <b>Skip-Gründe:</b>",
    ]
    for reason, count in sorted(reasons.items(), key=lambda x: -x[1])[:8]:
        lines.append(f"  • {reason}: <b>{count}x</b>")
    if worst_filter:
        cost = filter_costs[worst_filter]
        lines.append(f"\n⚠️ Teuerster Filter: <b>{worst_filter}</b> (+${cost:.2f} verpasst)")
    if net_missed > 10:
        lines.append("\n💡 Skipped-Signale waren profitabler als erwartet — Filter überprüfen?")
    return "\n".join(lines)


def get_summary_stats(days: int = 7) -> dict:
    """Returns summary stats dict for the dashboard /api/skipped_signals endpoint."""
    now = datetime.now(timezone.utc)
    cutoff_str = (now - timedelta(days=days)).isoformat()

    signals = _read_signals()
    outcomes = _read_outcomes()

    week_signals = [s for s in signals if s.get("ts", "") >= cutoff_str]
    week_outcomes = [o for o in outcomes if o.get("ts_evaluated", "") >= cutoff_str]

    copied = sum(1 for s in week_signals if s.get("decision") == "COPIED")
    skipped_list = [s for s in week_signals if s.get("decision") == "SKIPPED"]
    reasons = Counter(s.get("skip_reason", "UNKNOWN") for s in skipped_list)

    winners = [o for o in week_outcomes if o.get("signal_correct")]
    losers = [o for o in week_outcomes if not o.get("signal_correct")]
    missed = sum(o.get("theoretical_profit_usdc", 0) for o in winners)
    avoided = sum(abs(o.get("theoretical_profit_usdc", 0)) for o in losers)

    filter_costs: dict = {}
    for o in week_outcomes:
        if o.get("signal_correct"):
            r = o.get("skip_reason", "UNKNOWN")
            filter_costs[r] = filter_costs.get(r, 0) + o.get("theoretical_profit_usdc", 0)

    return {
        "days": days,
        "total_signals": len(week_signals),
        "copied": copied,
        "skipped": len(skipped_list),
        "evaluated": len(week_outcomes),
        "winners": len(winners),
        "losers": len(losers),
        "missed_profit_usd": round(missed, 2),
        "avoided_loss_usd": round(avoided, 2),
        "net_missed_usd": round(missed - avoided, 2),
        "worst_filter": max(filter_costs, key=filter_costs.get) if filter_costs else None,
        "by_reason": dict(reasons.most_common()),
    }
