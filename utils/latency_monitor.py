"""
latency_monitor.py — Fill-Qualitätsmessung

Misst pro Trade:
- Latenz: Zeit zwischen Whale-Trade-Erkennung und unserem Kauf
- Slippage: Preisunterschied zwischen Whale-Preis und unserem Fill-Preis

Täglich um 09:00 Telegram-Report.
"""

import asyncio
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from utils.logger import get_logger

logger = get_logger("latency")

LATENCY_FILE = "latency_data.json"
REPORT_HOUR  = 9  # 09:00 Uhr täglich


@dataclass
class FillRecord:
    trade_id:        str    # tx_hash oder fortlaufende ID
    market:          str
    outcome:         str
    whale_price:     float  # Preis den der Whale bezahlt hat
    our_price:       float  # Unser Fill-Preis
    size_usdc:       float
    detected_at:     str    # ISO-String: wann WalletMonitor den Trade erkannte
    filled_at:       str    # ISO-String: wann wir die Order ausgeführt haben
    latency_seconds: float  # filled_at - detected_at
    slippage_pct:    float  # (our_price - whale_price) / whale_price * 100
    dry_run:         bool

    @property
    def slippage_cents(self) -> float:
        """Slippage in Cent (bei $1.00 Markt)."""
        return abs(self.our_price - self.whale_price) * 100


# ── Persistenz ────────────────────────────────────────────────────────────────

def _load() -> List[dict]:
    if not os.path.exists(LATENCY_FILE):
        return []
    try:
        with open(LATENCY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(records: List[dict]):
    try:
        with open(LATENCY_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Latency-Daten konnten nicht gespeichert werden: {e}")


# ── Recording ─────────────────────────────────────────────────────────────────

def record_fill(signal, result, fill_time: Optional[datetime] = None):
    """
    Wird nach jedem erfolgreichen Trade aufgerufen.

    signal: TradeSignal (hat .detected_at, .price, .market_question, .outcome, .tx_hash)
    result: ExecutionResult (hat .filled_price, .filled_size_usdc, .dry_run)
    fill_time: Zeitpunkt der Ausführung (default: jetzt)
    """
    try:
        if fill_time is None:
            fill_time = datetime.now(timezone.utc)

        detected_at = getattr(signal, "detected_at", fill_time)
        if detected_at.tzinfo is None:
            detected_at = detected_at.replace(tzinfo=timezone.utc)

        latency = (fill_time - detected_at).total_seconds()
        latency = max(0.0, latency)  # Negative Latenz abfangen (Clock-Skew)

        whale_price = float(getattr(signal, "price", 0) or 0)
        our_price   = float(getattr(result, "filled_price", whale_price) or whale_price)
        slippage    = ((our_price - whale_price) / whale_price * 100) if whale_price > 0 else 0.0

        record = FillRecord(
            trade_id=str(getattr(signal, "tx_hash", "") or str(len(_load()) + 1)),
            market=str(getattr(signal, "market_question", "") or "")[:60],
            outcome=str(getattr(signal, "outcome", "") or ""),
            whale_price=whale_price,
            our_price=our_price,
            size_usdc=float(getattr(result, "filled_size_usdc", 0) or 0),
            detected_at=detected_at.isoformat(),
            filled_at=fill_time.isoformat(),
            latency_seconds=round(latency, 2),
            slippage_pct=round(slippage, 4),
            dry_run=bool(getattr(result, "dry_run", True)),
        )

        records = _load()
        records.append(asdict(record))

        # Maximal 10.000 Einträge behalten (älteste löschen)
        if len(records) > 10_000:
            records = records[-10_000:]

        _save(records)

        logger.debug(
            f"Fill recorded: Latenz {latency:.1f}s | "
            f"Slippage {slippage:+.3f}% | {record.market[:40]}"
        )

    except Exception as e:
        logger.warning(f"record_fill fehlgeschlagen: {e}")


# ── Statistiken ───────────────────────────────────────────────────────────────

def get_stats(days: int = 1) -> dict:
    """Berechnet Latenz- und Slippage-Statistiken der letzten N Tage."""
    records = _load()
    if not records:
        return {}

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    recent = [r for r in records if r.get("filled_at", "") >= cutoff]

    if not recent:
        return {}

    latencies = [r["latency_seconds"] for r in recent if "latency_seconds" in r]
    slippages = [r["slippage_pct"]    for r in recent if "slippage_pct"    in r]
    sizes     = [r.get("size_usdc", 0) for r in recent]

    def _safe_avg(lst):
        return round(sum(lst) / len(lst), 3) if lst else 0.0

    return {
        "count":              len(recent),
        "avg_latency_s":      _safe_avg(latencies),
        "min_latency_s":      round(min(latencies), 2) if latencies else 0,
        "max_latency_s":      round(max(latencies), 2) if latencies else 0,
        "avg_slippage_pct":   _safe_avg(slippages),
        "best_fill_pct":      round(min(slippages), 4) if slippages else 0,
        "worst_fill_pct":     round(max(slippages), 4) if slippages else 0,
        "best_fill_cents":    round(min(abs(s) for s in slippages) * 100, 2) if slippages else 0,
        "worst_fill_cents":   round(max(abs(s) for s in slippages) * 100, 2) if slippages else 0,
        "total_volume_usdc":  round(sum(sizes), 2),
        "dry_run_count":      sum(1 for r in recent if r.get("dry_run")),
    }


# ── Telegram-Report ───────────────────────────────────────────────────────────

def build_report_message(stats: dict) -> str:
    if not stats:
        return "📡 <b>LATENZ-REPORT</b>\nNoch keine Fill-Daten vorhanden."

    lat  = stats.get("avg_latency_s", 0)
    slip = stats.get("avg_slippage_pct", 0)
    best = stats.get("best_fill_cents", 0)
    worst = stats.get("worst_fill_cents", 0)
    count = stats.get("count", 0)
    vol   = stats.get("total_volume_usdc", 0)
    dry   = stats.get("dry_run_count", 0)

    slip_icon = "🟢" if abs(slip) < 0.5 else "🟡" if abs(slip) < 2.0 else "🔴"
    lat_icon  = "🟢" if lat < 30 else "🟡" if lat < 60 else "🔴"

    mode_note = f" (davon {dry} DRY-RUN)" if dry > 0 else ""

    lines = [
        "📡 <b>LATENZ-REPORT — LETZTE 24H</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📊 Fills analysiert: <b>{count}</b>{mode_note}",
        f"💵 Volumen: <b>${vol:.2f} USDC</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"{lat_icon} Ø Verzögerung: <b>{lat:.1f}s</b>",
        f"   Min: {stats.get('min_latency_s', 0):.1f}s  |  Max: {stats.get('max_latency_s', 0):.1f}s",
        "━━━━━━━━━━━━━━━━━━━━",
        f"{slip_icon} Ø Slippage: <b>{slip:+.3f}%</b>",
        f"   Beste Fill:     <b>{best:.1f}¢</b>",
        f"   Schlechteste:   <b>{worst:.1f}¢</b>",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    # Bewertung
    if lat < 15 and abs(slip) < 0.5:
        lines.append("✅ <b>Exzellente Fill-Qualität</b>")
    elif lat < 30 and abs(slip) < 1.0:
        lines.append("🟡 <b>Gute Fill-Qualität</b>")
    else:
        lines.append("🔴 <b>Fill-Qualität verbesserungswürdig</b>")

    return "\n".join(lines)


# ── Täglicher Report-Loop ─────────────────────────────────────────────────────

async def latency_report_loop():
    """Sendet täglich um REPORT_HOUR Uhr einen Latenz-Report per Telegram."""
    logger.info(f"LatencyMonitor gestartet — Report täglich um {REPORT_HOUR:02d}:00 Uhr")

    while True:
        try:
            now      = datetime.now()
            next_run = now.replace(hour=REPORT_HOUR, minute=0, second=0, microsecond=0)
            if now >= next_run:
                next_run += timedelta(days=1)

            await asyncio.sleep((next_run - now).total_seconds())

            stats = get_stats(days=1)
            msg   = build_report_message(stats)

            from telegram_bot import send
            await send(msg)
            logger.info(f"Latenz-Report gesendet ({stats.get('count', 0)} Fills)")

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"latency_report_loop Fehler: {e} — weiter in 1h")
            await asyncio.sleep(3600)
