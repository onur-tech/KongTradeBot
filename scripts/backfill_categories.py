#!/usr/bin/env python3
"""
scripts/backfill_categories.py — Korrigiert Kategorien in trades_archive.json
mit der neuen utils/category.py Logik.

Legt vorher ein Backup an: trades_archive_backup_YYYYMMDD.json
"""
import sys, json, shutil
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.category import get_category

ARCHIVE = Path(__file__).parent.parent / "trades_archive.json"
BACKUP  = ARCHIVE.parent / f"trades_archive_backup_{date.today().strftime('%Y%m%d')}.json"


def main():
    if not ARCHIVE.exists():
        print(f"Archiv nicht gefunden: {ARCHIVE}")
        sys.exit(1)

    trades = json.loads(ARCHIVE.read_text(encoding="utf-8"))
    print(f"Geladene Trades: {len(trades)}")

    shutil.copy2(ARCHIVE, BACKUP)
    print(f"Backup erstellt: {BACKUP.name}")

    old_dist, new_dist = {}, {}
    changed = 0

    for t in trades:
        market = t.get("markt") or t.get("market_question") or ""
        old_cat = t.get("kategorie", "Sonstiges") or "Sonstiges"
        new_cat = get_category(market)

        old_dist[old_cat] = old_dist.get(old_cat, 0) + 1
        new_dist[new_cat] = new_dist.get(new_cat, 0) + 1

        if old_cat != new_cat:
            changed += 1
            t["kategorie"] = new_cat

    ARCHIVE.write_text(json.dumps(trades, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nNeu kategorisiert: {changed} von {len(trades)} Trades")
    print("\nAlte Verteilung:")
    for cat, n in sorted(old_dist.items(), key=lambda x: -x[1]):
        print(f"  {cat:15s}: {n:3d}")
    print("\nNeue Verteilung:")
    for cat, n in sorted(new_dist.items(), key=lambda x: -x[1]):
        print(f"  {cat:15s}: {n:3d}")


if __name__ == "__main__":
    main()
