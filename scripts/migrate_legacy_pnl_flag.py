"""
migrate_legacy_pnl_flag.py — Einmalige Migration: pre-4537924 SELL-Eintraege flaggen

Setzt legacy_missing_pnl=True auf allen SELL-Eintraegen die:
- gewinn_verlust_usdc == 0.0 (PnL nicht erfasst)
- vor dem log_trade-Fix (Commit 4537924, 2026-04-19 14:20) entstanden sind
- noch nicht bereits geflagged sind

Kontext: Commit 4537924 fugte realized_pnl-Parameter zu log_trade() hinzu.
Alle Exit-SELL-Eintraege davor haben pnl=0.0 und sind nicht rekonstruierbar.

Ausfuehren: python3 scripts/migrate_legacy_pnl_flag.py
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

ARCHIVE_PATH = Path(__file__).parent.parent / "trades_archive.json"
CUTOFF_DATE = "2026-04-19"
CUTOFF_TIME = "14:20:00"
LEGACY_REASON = "pre-4537924 exit_pipeline, realized_pnl not captured"


def main():
    if not ARCHIVE_PATH.exists():
        print(f"Archive not found: {ARCHIVE_PATH}")
        return

    backup = ARCHIVE_PATH.with_suffix(f".json.backup_migrate_{datetime.now().strftime('%H%M')}")
    shutil.copy(ARCHIVE_PATH, backup)
    print(f"Backup: {backup}")

    with open(ARCHIVE_PATH) as f:
        trades = json.load(f)

    flagged = 0
    for t in trades:
        is_sell = t.get("seite", "").upper() == "SELL"
        pnl_zero = t.get("gewinn_verlust_usdc", 0.0) == 0.0
        already = t.get("legacy_missing_pnl", False)
        datum = t.get("datum", "")
        uhrzeit = t.get("uhrzeit", "")
        before_fix = (datum < CUTOFF_DATE) or (datum == CUTOFF_DATE and uhrzeit < CUTOFF_TIME)
        if is_sell and pnl_zero and not already and before_fix:
            t["legacy_missing_pnl"] = True
            t["legacy_reason"] = LEGACY_REASON
            flagged += 1

    with open(ARCHIVE_PATH, "w") as f:
        json.dump(trades, f, indent=2, ensure_ascii=False)

    print(f"Flagged: {flagged} / {len(trades)} total")
    legacy = [t for t in trades if t.get("legacy_missing_pnl")]
    print(f"Total legacy entries now: {len(legacy)}")


if __name__ == "__main__":
    main()
