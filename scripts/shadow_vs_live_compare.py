#!/usr/bin/env python3
"""
shadow_vs_live_compare.py — Vergleicht Shadow Portfolio mit echten Trades.

Liest:  data/shadow_portfolio.json  (virtuelle Trades)
        trades_archive.json          (echte Trades)
Matcht: nach market_id + outcome
Output: data/analysis/shadow_vs_live_DATUM.json + stdout Tabelle
"""

import json
import os
import sys
from datetime import date
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
ANALYSIS_DIR = os.path.join(DATA_DIR, "analysis")


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def classify_group(trade: dict) -> str:
    """Bestimmt Gruppe (Weather-Stadt oder Copy-Kategorie)."""
    kat = (trade.get("kategorie") or "").upper()
    markt = (trade.get("markt") or trade.get("market_question") or trade.get("question") or "").lower()

    if kat == "WEATHER" or "temperature" in markt:
        for city in ["Seoul", "London", "Tokyo", "Paris", "Dubai", "Sydney",
                     "Buenos Aires", "Shanghai", "New York", "Moscow",
                     "Mumbai", "Chicago", "Toronto", "Bangkok", "Karachi"]:
            if city.lower() in markt:
                return f"Weather/{city}"
        return "Weather/Other"
    elif kat in ("GEOPOLITIK", "GEO", "GEOPOLITICS"):
        return "Copy/Geo"
    elif kat in ("SPORT_US", "SPORT", "SOCCER", "TENNIS"):
        return f"Copy/{kat.title()}"
    return f"Copy/{kat or 'Other'}"


def analyze():
    shadow_path = os.path.join(DATA_DIR, "shadow_portfolio.json")
    archive_path = os.path.join(BASE_DIR, "trades_archive.json")

    shadow_raw = load_json(shadow_path) or {}
    # shadow_portfolio.json ist ein Dict mit 'positions' + 'closed_positions'
    if isinstance(shadow_raw, dict):
        shadow_open = shadow_raw.get("positions", [])
        shadow_closed_list = shadow_raw.get("closed_positions", [])
        shadow_all = shadow_open + shadow_closed_list
    else:
        shadow_all = shadow_raw
        shadow_closed_list = [t for t in shadow_all if t.get("status") not in ("OPEN", "ACTIVE", None)]

    archive_all = load_json(archive_path) or []

    # Nur aufgelöste Trades verwenden
    live_closed = [t for t in archive_all if t.get("aufgeloest")]
    shadow_closed = [t for t in shadow_all if t.get("status") not in ("OPEN", "ACTIVE", None)]

    print(f"Daten: {len(live_closed)} echte abgeschlossene Trades | "
          f"{len(shadow_closed)} Shadow abgeschlossen | "
          f"{len([t for t in shadow_all if t.get('status') in ('OPEN','ACTIVE')])} Shadow offen")

    # Index live nach market_id+outcome
    live_idx = defaultdict(list)
    for t in live_closed:
        key = (t.get("market_id", ""), (t.get("outcome") or "").upper())
        live_idx[key].append(t)

    # Index shadow nach market_id+outcome
    shadow_idx = defaultdict(list)
    for t in shadow_all:
        key = (t.get("market_id", ""), (t.get("outcome") or "").upper())
        shadow_idx[key].append(t)

    # Matched pairs
    matched = []
    for key, live_trades in live_idx.items():
        if key in shadow_idx:
            for lt in live_trades:
                for st in shadow_idx[key]:
                    matched.append((st, lt))

    print(f"Gematchte Paare (Shadow ↔ Live): {len(matched)}")

    # Slippage-Berechnung aus gematchten Trades
    slippage_total = 0.0
    slippage_count = 0
    for st, lt in matched:
        shadow_price = float(st.get("entry_price") or 0)
        live_price = float(lt.get("preis_usdc") or 0)
        if shadow_price > 0 and live_price > 0:
            slippage_total += (live_price - shadow_price) * 100  # in Cent
            slippage_count += 1

    avg_slippage = slippage_total / slippage_count if slippage_count else 0.0

    # Gruppen-Statistiken aus allen Live-Trades
    groups: dict = defaultdict(lambda: {
        "shadow_wins": 0, "shadow_losses": 0, "shadow_invested": 0.0,
        "live_wins": 0, "live_losses": 0, "live_invested": 0.0,
        "live_pnl": 0.0, "shadow_pnl": 0.0, "slippage_sum": 0.0, "slippage_n": 0,
    })

    # Live-Trades nach Gruppe
    for lt in live_closed:
        g = classify_group(lt)
        grp = groups[g]
        invested = float(lt.get("einsatz_usdc") or 0)
        pnl = float(lt.get("gewinn_verlust_usdc") or 0)
        grp["live_invested"] += invested
        grp["live_pnl"] += pnl
        if lt.get("ergebnis") == "GEWINN":
            grp["live_wins"] += 1
        else:
            grp["live_losses"] += 1

    # Shadow-Trades nach Gruppe (alle, auch offene — für WR-Vergleich)
    for st in shadow_all:
        g = classify_group(st)
        grp = groups[g]
        invested = float(st.get("invested_usdc") or 0)
        pnl = float(st.get("pnl") or 0)
        grp["shadow_invested"] += invested
        grp["shadow_pnl"] += pnl
        status = st.get("status", "")
        if status in ("WIN", "GEWINN", "RESOLVED_WIN"):
            grp["shadow_wins"] += 1
        elif status in ("LOSS", "VERLUST", "RESOLVED_LOSS", "EXPIRED"):
            grp["shadow_losses"] += 1

    # Slippage pro Gruppe aus gematchten Trades
    for st, lt in matched:
        g = classify_group(lt)
        sp = float(st.get("entry_price") or 0)
        lp = float(lt.get("preis_usdc") or 0)
        if sp > 0 and lp > 0:
            groups[g]["slippage_sum"] += (lp - sp) * 100
            groups[g]["slippage_n"] += 1

    # Tabelle aufbauen
    rows = []
    for grp_name in sorted(groups.keys()):
        g = groups[grp_name]
        s_total = g["shadow_wins"] + g["shadow_losses"]
        l_total = g["live_wins"] + g["live_losses"]
        s_wr = g["shadow_wins"] / s_total * 100 if s_total else None
        l_wr = g["live_wins"] / l_total * 100 if l_total else None
        s_roi = g["shadow_pnl"] / g["shadow_invested"] * 100 if g["shadow_invested"] else None
        l_roi = g["live_pnl"] / g["live_invested"] * 100 if g["live_invested"] else None
        slip = g["slippage_sum"] / g["slippage_n"] if g["slippage_n"] else None

        rows.append({
            "group": grp_name,
            "shadow_trades": s_total,
            "shadow_wr_pct": round(s_wr, 1) if s_wr is not None else None,
            "shadow_roi_pct": round(s_roi, 1) if s_roi is not None else None,
            "live_trades": l_total,
            "live_wr_pct": round(l_wr, 1) if l_wr is not None else None,
            "live_roi_pct": round(l_roi, 1) if l_roi is not None else None,
            "avg_slippage_cents": round(slip, 2) if slip is not None else None,
        })

    # Stdout-Tabelle
    print()
    print(f"{'Gruppe':<22} {'Shad-WR':>8} {'Shad-ROI':>9} {'Live-WR':>8} {'Live-ROI':>9} {'Slippage':>9} {'Live-Trades':>11}")
    print("─" * 82)
    for r in rows:
        swr  = f"{r['shadow_wr_pct']:.0f}%"   if r["shadow_wr_pct"]  is not None else "  —"
        sroi = f"{r['shadow_roi_pct']:+.1f}%"  if r["shadow_roi_pct"] is not None else "  —"
        lwr  = f"{r['live_wr_pct']:.0f}%"      if r["live_wr_pct"]    is not None else "  —"
        lroi = f"{r['live_roi_pct']:+.1f}%"    if r["live_roi_pct"]   is not None else "  —"
        slip = f"{r['avg_slippage_cents']:+.1f}¢" if r["avg_slippage_cents"] is not None else "  —"
        lt   = str(r["live_trades"]) if r["live_trades"] else "  0"
        print(f"{r['group']:<22} {swr:>8} {sroi:>9} {lwr:>8} {lroi:>9} {slip:>9} {lt:>11}")
    print("─" * 82)
    print(f"Ø Slippage gesamt (gematchte Trades): {avg_slippage:+.2f}¢  "
          f"({slippage_count} Paare verglichen)")

    # JSON speichern
    os.makedirs(ANALYSIS_DIR, exist_ok=True)
    out_path = os.path.join(ANALYSIS_DIR, f"shadow_vs_live_{date.today().isoformat()}.json")
    output = {
        "date": date.today().isoformat(),
        "summary": {
            "live_closed": len(live_closed),
            "shadow_closed": len(shadow_closed),
            "matched_pairs": len(matched),
            "avg_slippage_cents": round(avg_slippage, 3),
        },
        "groups": rows,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n→ Gespeichert: {out_path}")
    return output


if __name__ == "__main__":
    analyze()
