"""
backtester.py — Historische Szenario-Analyse auf Basis von trades_archive.json

Szenarien:
  1. Basis           — alle aufgelösten Trades wie sie waren
  2. Odds-Filter     — Preis < 0.15 oder > 0.85 ausschließen
  3. Kategorie-Spez. — pro Wallet nur Kategorien mit >60% historischer Win Rate
  4. Sov 0.5x        — sovereign2013 Einsatz immer halbieren
  5. Kombination     — Odds-Filter + Kategorie-Spez. + Sov 0.5x

Ausgabe: Konsolentabelle + backtest_results.json
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime

ARCHIVE_PATH = os.path.join(os.path.dirname(__file__), "..", "trades_archive.json")
RESULTS_PATH = os.path.join(os.path.dirname(__file__), "..", "backtest_results.json")

# Wallet-Adressen (Präfix-Match reicht)
SOVEREIGN = "0x2005d16a84ceefa912"
DRPUFFERFISH = "0xee613b3fc183ee44f9"

# Kategorien mit Win Rate >60% pro Wallet (aus wallet_category_performance.json)
WALLET_GOOD_CATEGORIES: dict[str, set[str]] = {
    SOVEREIGN:    {"Sport"},           # sovereign2013: 100% in Sport, 10.9% in Sonstiges
    DRPUFFERFISH: {"Sport", "Sonstiges", "Makro", "Geopolitik"},  # 59-80% überall
}


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

def _wallet_key(addr: str) -> str:
    """Normalisiert abgekürzte Wallet-Adressen auf Präfix."""
    return addr[:20]


def _is_sovereign(addr: str) -> bool:
    return addr.startswith(SOVEREIGN[:18])


def _in_good_category(addr: str, kategorie: str) -> bool:
    key = addr[:20]
    for prefix, cats in WALLET_GOOD_CATEGORIES.items():
        if key.startswith(prefix[:18]) or prefix[:18].startswith(key[:18]):
            return kategorie in cats
    return True  # unbekannte Wallets: erlaubt


def _load_trades() -> list[dict]:
    with open(ARCHIVE_PATH, encoding="utf-8") as f:
        all_trades = json.load(f)
    resolved = [t for t in all_trades if t.get("aufgeloest")]
    # Nach Datum + Uhrzeit sortieren
    resolved.sort(key=lambda t: t.get("datum", "") + " " + t.get("uhrzeit", ""))
    return resolved


# ── Statistiken berechnen ─────────────────────────────────────────────────────

def _compute_stats(trades: list[dict]) -> dict:
    if not trades:
        return {
            "trades": 0, "wins": 0, "win_rate_pct": 0,
            "total_pnl": 0, "max_drawdown": 0,
            "best_day": None, "best_day_pnl": 0,
            "worst_day": None, "worst_day_pnl": 0,
        }

    wins = sum(1 for t in trades if t["ergebnis"] == "GEWINN")
    total_pnl = round(sum(t["pnl"] for t in trades), 4)
    win_rate = round(wins / len(trades) * 100, 1) if trades else 0

    # Max Drawdown (Peak-to-Trough auf kumulativem PnL)
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in trades:
        cum += t["pnl"]
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd

    # Tages-PnL
    daily: dict[str, float] = defaultdict(float)
    for t in trades:
        daily[t.get("datum", "unknown")] += t["pnl"]

    best_day  = max(daily, key=daily.get) if daily else None
    worst_day = min(daily, key=daily.get) if daily else None

    return {
        "trades":        len(trades),
        "wins":          wins,
        "win_rate_pct":  win_rate,
        "total_pnl":     total_pnl,
        "max_drawdown":  round(max_dd, 4),
        "best_day":      best_day,
        "best_day_pnl":  round(daily.get(best_day, 0), 4) if best_day else 0,
        "worst_day":     worst_day,
        "worst_day_pnl": round(daily.get(worst_day, 0), 4) if worst_day else 0,
    }


# ── Szenarien ─────────────────────────────────────────────────────────────────

def _apply_scenario(raw: list[dict], odds_filter: bool, cat_filter: bool, sov_half: bool) -> list[dict]:
    result = []
    for t in raw:
        addr     = t.get("source_wallet", "")
        price    = t.get("preis_usdc", 0.5)
        kategorie = t.get("kategorie", "Sonstiges")
        einsatz  = t.get("einsatz_usdc", 0.0)
        pnl_raw  = t.get("gewinn_verlust_usdc", 0.0)

        # Odds-Filter
        if odds_filter and (price < 0.15 or price > 0.85):
            continue

        # Kategorie-Filter
        if cat_filter and not _in_good_category(addr, kategorie):
            continue

        # sovereign2013 Multiplikator
        multiplier = 0.5 if (sov_half and _is_sovereign(addr)) else 1.0

        result.append({
            "datum":    t.get("datum", ""),
            "ergebnis": t.get("ergebnis", ""),
            "pnl":      round(pnl_raw * multiplier, 6),
        })

    return result


def run_backtest() -> dict:
    raw = _load_trades()
    print(f"Geladene Trades: {len(raw)} aufgelöst\n")

    scenarios = {
        "1_Basis":           _apply_scenario(raw, odds_filter=False, cat_filter=False, sov_half=False),
        "2_Odds_Filter":     _apply_scenario(raw, odds_filter=True,  cat_filter=False, sov_half=False),
        "3_Kategorie_Spez":  _apply_scenario(raw, odds_filter=False, cat_filter=True,  sov_half=False),
        "4_Sov_0.5x":        _apply_scenario(raw, odds_filter=False, cat_filter=False, sov_half=True),
        "5_Kombination":     _apply_scenario(raw, odds_filter=True,  cat_filter=True,  sov_half=True),
    }

    results = {}
    for name, trades in scenarios.items():
        results[name] = _compute_stats(trades)

    return results


# ── Ausgabe ───────────────────────────────────────────────────────────────────

def _print_table(results: dict):
    COL = 22
    headers = ["Szenario", "Trades", "Win Rate", "Gesamt P&L", "Max DD", "Bester Tag", "Schlechtester Tag"]
    widths   = [20,          7,        9,           12,           8,        22,            22]

    header_line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    print("=" * len(header_line))
    print(header_line)
    print("=" * len(header_line))

    labels = {
        "1_Basis":          "1. Basis",
        "2_Odds_Filter":    "2. Odds 15-85%",
        "3_Kategorie_Spez": "3. Kat-Spezialisierung",
        "4_Sov_0.5x":       "4. Sov 0.5x",
        "5_Kombination":    "5. Kombination",
    }

    for key, s in results.items():
        best  = f"{s['best_day']} ({s['best_day_pnl']:+.2f}$)"   if s["best_day"]  else "—"
        worst = f"{s['worst_day']} ({s['worst_day_pnl']:+.2f}$)" if s["worst_day"] else "—"
        row = [
            labels.get(key, key),
            str(s["trades"]),
            f"{s['win_rate_pct']}%",
            f"{s['total_pnl']:+.2f}$",
            f"-{s['max_drawdown']:.2f}$",
            best,
            worst,
        ]
        print("  ".join(v.ljust(w) for v, w in zip(row, widths)))

    print("=" * len(header_line))


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    results = run_backtest()

    _print_table(results)

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nErgebnisse gespeichert: backtest_results.json")
    print("\nEmpfehlung:")

    best_key  = max(results, key=lambda k: results[k]["total_pnl"])
    best_pnl  = results[best_key]["total_pnl"]
    basis_pnl = results["1_Basis"]["total_pnl"]
    delta     = best_pnl - basis_pnl

    labels = {
        "1_Basis":          "Basis",
        "2_Odds_Filter":    "Odds-Filter 15-85%",
        "3_Kategorie_Spez": "Kategorie-Spezialisierung",
        "4_Sov_0.5x":       "sovereign2013 auf 0.5x",
        "5_Kombination":    "Kombination aller Filter",
    }
    print(f"  Bestes Szenario: {labels.get(best_key, best_key)}")
    print(f"  P&L: {best_pnl:+.2f}$ vs. Basis {basis_pnl:+.2f}$ (Delta {delta:+.2f}$)")
