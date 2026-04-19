#!/usr/bin/env python3
"""
scripts/backfill_skipped.py — Retroaktives Einlesen von SKIPPED-Signalen aus Bot-Logs.

Parst bot_*.log Dateien der letzten N Tage und extrahiert "⏭️ SKIP" und
"❌ Trade abgelehnt" Zeilen. Schreibt unvollständige Records mit
retroactive=True in data/all_signals.jsonl (kein market_id/token_id = kein
Outcome-Evaluation möglich, aber Zählung und Reason-Breakdown funktioniert).

Usage:
    python3 scripts/backfill_skipped.py
    python3 scripts/backfill_skipped.py --days 14
    python3 scripts/backfill_skipped.py --dry-run
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

SIGNALS_FILE = BASE_DIR / "data" / "all_signals.jsonl"
LOGS_DIR = BASE_DIR / "logs"

# Regex patterns
_SKIP_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*⏭️ SKIP: reason=(\S+)"
)
_REJECT_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*❌ Trade abgelehnt: (.+)$"
)


def _normalize_reason(reason: str) -> str:
    r = reason.upper().strip()
    if "MIN_TRADE" in r or "MICRO" in r or "MINIMUM" in r or "BERECHNETE" in r:
        return "MIN_TRADE_SIZE"
    if "MAX_TRADE" in r:
        return "MAX_TRADE_SIZE"
    if "BUDGET" in r:
        return "BUDGET_CAP"
    if "PREIS" in r or "PRICE" in r or "EXTREMIT" in r or "ODDS" in r or "RANGE" in r:
        return "PRICE_EXTREMITY"
    if "HOURS" in r or "MIN_HOURS" in r or "SCHLIESS" in r or "CLOSE" in r:
        return "TIME_TO_CLOSE"
    if "KILL" in r:
        return "KILL_SWITCH"
    if "DAILY" in r or "TAGES" in r or "VERLUST" in r:
        return "DAILY_LOSS_LIMIT"
    if "VOLUMEN" in r or "VOLUME" in r or "MIN_MARKT" in r:
        return "MIN_MARKT_VOLUMEN"
    if "POSITION" in r:
        return "MAX_POSITIONS_TOTAL"
    if "DECAY" in r or "WIN_RATE" in r:
        return "WIN_RATE_DECAY"
    if "BLACKLIST" in r or "KATEGORIE" in r:
        return "CATEGORY_BLACKLIST"
    return reason[:50]


def _load_existing_retroactive_timestamps() -> set:
    if not SIGNALS_FILE.exists():
        return set()
    seen = set()
    with SIGNALS_FILE.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if rec.get("retroactive"):
                    seen.add(rec["ts"])
            except Exception:
                pass
    return seen


def backfill(days: int = 7, dry_run: bool = False) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    existing_ts = _load_existing_retroactive_timestamps()
    records = []

    log_files = sorted(LOGS_DIR.glob("bot_*.log"))
    for log_file in log_files:
        try:
            file_date_str = log_file.stem.replace("bot_", "")
            file_date = datetime.strptime(file_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if file_date < cutoff - timedelta(days=1):
                continue
        except ValueError:
            pass

        with log_file.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                ts_str = None
                reason = None

                m = _SKIP_RE.match(line)
                if m:
                    ts_str, raw_reason = m.group(1), m.group(2)
                    reason = _normalize_reason(raw_reason)

                if not ts_str:
                    m = _REJECT_RE.match(line)
                    if m:
                        ts_str, raw_reason = m.group(1), m.group(2).strip()
                        reason = _normalize_reason(raw_reason)

                if not ts_str or not reason:
                    continue

                try:
                    dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    if dt < cutoff:
                        continue
                except ValueError:
                    continue

                iso_ts = dt.isoformat()
                if iso_ts in existing_ts:
                    continue

                records.append({
                    "ts": iso_ts,
                    "tx_hash": f"retroactive_{dt.strftime('%Y%m%d%H%M%S')}_{len(records)}",
                    "wallet": "",
                    "market_id": "",
                    "token_id": "",
                    "outcome": "",
                    "side": "BUY",
                    "price": 0.0,
                    "whale_size_usdc": 0.0,
                    "market_question": "",
                    "market_closes_at": None,
                    "decision": "SKIPPED",
                    "skip_reason": reason,
                    "retroactive": True,
                })
                existing_ts.add(iso_ts)

    if not records:
        print(f"Keine neuen retroaktiven Signale gefunden (letzten {days} Tage).")
        return 0

    if dry_run:
        print(f"[DRY-RUN] Würde {len(records)} retroaktive Einträge schreiben:")
        from collections import Counter
        for reason, count in Counter(r["skip_reason"] for r in records).most_common():
            print(f"  {reason}: {count}x")
        return len(records)

    SIGNALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SIGNALS_FILE.open("a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    from collections import Counter
    print(f"✅ {len(records)} retroaktive Einträge geschrieben:")
    for reason, count in Counter(r["skip_reason"] for r in records).most_common():
        print(f"  {reason}: {count}x")
    return len(records)


def main():
    parser = argparse.ArgumentParser(description="Backfill skipped signals from bot logs")
    parser.add_argument("--days", type=int, default=7, help="Tage zurück (default: 7)")
    parser.add_argument("--dry-run", action="store_true", help="Nur anzeigen, nicht schreiben")
    args = parser.parse_args()
    backfill(days=args.days, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
