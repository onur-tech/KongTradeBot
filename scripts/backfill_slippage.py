#!/usr/bin/env python3
"""
scripts/backfill_slippage.py — Slippage-Backfill aus trades_archive.json

HINWEIS: Backfill ist nicht möglich.
trades_archive.json speichert nur den Signal-Preis (whale_price), aber KEINEN
separaten filled_price. Da DRY_RUN immer filled_price == whale_price → slippage=0¢,
und Live-Trades den filled_price nicht separat im Archiv speichern, gibt es
keine Quelldaten für eine nachträgliche Berechnung.

Schlussfolgerung: Slippage-Daten beginnen mit dem Deployment von
utils/slippage_tracker.py (2026-04-19). Historische Daten sind nicht verfügbar.
"""
import sys

print(__doc__)
print("Nichts zu tun — Backfill nicht möglich.")
sys.exit(0)
