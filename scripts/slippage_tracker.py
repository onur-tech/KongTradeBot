#!/usr/bin/env python3
"""
slippage_tracker.py — Misst echte Slippage pro Trade.

Liest:  data/slippage_log.jsonl  (Signal-Zeit vs Fill-Preis Deltas)
Output: data/analysis/slippage_DATUM.json + stdout Tabelle
Warnung wenn avg_slippage > 2¢ für eine Kategorie.
"""

import json
import os
from datetime import date
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
ANALYSIS_DIR = os.path.join(DATA_DIR, "analysis")
SLIPPAGE_FILE = os.path.join(DATA_DIR, "slippage_log.jsonl")

WARN_THRESHOLD_CENTS = 2.0


def size_class(usd: float) -> str:
    if usd < 5:
        return "$0-5"
    elif usd < 15:
        return "$5-15"
    else:
        return "$15-30"


def load_slippage_log() -> list:
    entries = []
    try:
        for line in open(SLIPPAGE_FILE, encoding="utf-8"):
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    except FileNotFoundError:
        print(f"Keine slippage_log.jsonl gefunden: {SLIPPAGE_FILE}")
    return entries


def analyze():
    entries = load_slippage_log()
    live_entries = [e for e in entries if not e.get("dry_run", True)]
    print(f"Slippage-Einträge gesamt: {len(entries)} | Live (nicht dry-run): {len(live_entries)}")

    if not entries:
        print("Keine Daten vorhanden.")
        return {}

    # Alle Einträge analysieren (inkl. dry-run für Kalibrierung)
    by_category: dict = defaultdict(list)
    by_size: dict = defaultdict(list)
    by_wallet: dict = defaultdict(list)

    for e in entries:
        delta = float(e.get("delta_cents") or 0)
        cat = e.get("category") or "Unknown"
        usd = float(e.get("our_size_usdc") or 0)
        wallet = str(e.get("whale_wallet") or "unknown")[:14]
        sc = size_class(usd)

        by_category[cat].append(delta)
        by_size[sc].append(delta)
        by_wallet[wallet].append(delta)

    def stats(values: list) -> dict:
        if not values:
            return {"n": 0, "avg": 0, "max": 0, "min": 0, "total_cost": 0}
        return {
            "n": len(values),
            "avg": round(sum(values) / len(values), 3),
            "max": round(max(values), 3),
            "min": round(min(values), 3),
            "total_cost": round(sum(values), 3),
        }

    cat_stats = {k: stats(v) for k, v in by_category.items()}
    size_stats = {k: stats(v) for k, v in by_size.items()}
    wallet_stats = {k: stats(v) for k, v in by_wallet.items()}

    all_deltas = [float(e.get("delta_cents") or 0) for e in entries]
    overall = stats(all_deltas)

    # Stdout: Nach Kategorie
    print(f"\nSlippage nach Kategorie (N={len(entries)} Trades)")
    print(f"{'Kategorie':<20} {'N':>4} {'Ø Slip':>8} {'Max':>7} {'Min':>7} {'Gesamt-Kosten':>14}  Status")
    print("─" * 78)
    warnings = []
    for cat in sorted(cat_stats.keys()):
        s = cat_stats[cat]
        avg = s["avg"]
        warn = " ⚠️  > 2¢!" if abs(avg) > WARN_THRESHOLD_CENTS else ""
        if warn:
            warnings.append(f"  {cat}: Ø {avg:+.2f}¢")
        print(f"{cat:<20} {s['n']:>4} {avg:>+7.2f}¢ {s['max']:>+6.2f}¢ {s['min']:>+6.2f}¢ "
              f"{s['total_cost']:>+12.2f}¢{warn}")

    # Stdout: Nach Größenklasse
    print(f"\nSlippage nach Trade-Größe")
    print(f"{'Größe':>8} {'N':>4} {'Ø Slip':>8} {'Max':>7} {'Gesamt-Kosten':>14}")
    print("─" * 50)
    for sc in ["$0-5", "$5-15", "$15-30"]:
        if sc in size_stats:
            s = size_stats[sc]
            print(f"{sc:>8} {s['n']:>4} {s['avg']:>+7.2f}¢ {s['max']:>+6.2f}¢ {s['total_cost']:>+12.2f}¢")

    # Gesamtsummary
    print(f"\nGesamt-Slippage: Ø {overall['avg']:+.2f}¢ | "
          f"Max: {overall['max']:+.2f}¢ | "
          f"Gesamt-Kosten: {overall['total_cost']:+.2f}¢ über {overall['n']} Trades")

    if warnings:
        print("\n⚠️  WARNUNGEN (avg_slippage > 2¢):")
        for w in warnings:
            print(w)
    else:
        print("\n✅ Alle Kategorien innerhalb 2¢ Slippage-Schwelle.")

    # Dry-run Anteil
    dry_count = len([e for e in entries if e.get("dry_run", True)])
    live_count = len(entries) - dry_count
    print(f"\nDry-Run: {dry_count} | Live: {live_count}")

    # JSON speichern
    os.makedirs(ANALYSIS_DIR, exist_ok=True)
    out_path = os.path.join(ANALYSIS_DIR, f"slippage_{date.today().isoformat()}.json")
    output = {
        "date": date.today().isoformat(),
        "total_entries": len(entries),
        "live_entries": live_count,
        "dry_run_entries": dry_count,
        "overall": overall,
        "by_category": cat_stats,
        "by_size_class": size_stats,
        "by_wallet": {k: v for k, v in sorted(
            wallet_stats.items(), key=lambda x: abs(x[1]["avg"]), reverse=True)[:10]},
        "warnings": warnings,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"→ Gespeichert: {out_path}")
    return output


if __name__ == "__main__":
    analyze()
