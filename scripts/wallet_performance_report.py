#!/usr/bin/env python3
"""
wallet_performance_report.py — Per-Wallet Performance seit Bot-Start.

Liest:  trades_archive.json         (alle echten Trades)
        data/wallet_decisions.jsonl  (Multiplier-Historie)
        .env                         (WALLET_WEIGHTS)
Output: data/analysis/wallet_performance_DATUM.json + stdout Tabelle
"""

import json
import os
import re
from datetime import date, datetime
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


def load_env_weights() -> dict:
    """Liest WALLET_WEIGHTS aus .env — Format: wallet:weight,wallet2:weight2"""
    env_path = os.path.join(BASE_DIR, ".env")
    weights = {}
    try:
        for line in open(env_path):
            line = line.strip()
            if line.startswith("WALLET_WEIGHTS="):
                val = line.split("=", 1)[1].strip()
                for pair in val.split(","):
                    parts = pair.strip().split(":")
                    if len(parts) == 2:
                        try:
                            weights[parts[0].strip().lower()] = float(parts[1])
                        except ValueError:
                            pass
    except Exception:
        pass
    return weights


def load_wallet_names() -> dict:
    """Versucht Wallet-Aliases aus .env zu laden."""
    env_path = os.path.join(BASE_DIR, ".env")
    names = {}
    try:
        for line in open(env_path):
            line = line.strip()
            m = re.match(r'^WALLET_(\d+)_NAME=(.+)', line)
            if m:
                names[m.group(1)] = m.group(2).strip()
    except Exception:
        pass
    return names


def shorten(addr: str) -> str:
    if len(addr) > 12:
        return addr[:6] + "..." + addr[-4:]
    return addr


def recommend(win_rate: float, roi: float, trades: int, current_weight: float) -> str:
    if trades < 3:
        return "Zu wenig Daten"
    if roi < -20 or win_rate < 35:
        return "⚠️  ENTFERNEN"
    if roi < -10 or win_rate < 45:
        return "↓ Multiplier senken"
    if roi > 25 and win_rate > 60:
        new = min(3.0, round(current_weight * 1.5, 1))
        return f"↑ auf {new:.1f}x erhöhen"
    if roi > 10 and win_rate > 55:
        return f"✓ {current_weight:.1f}x halten"
    return f"~ {current_weight:.1f}x halten"


def analyze():
    archive_all = load_json(os.path.join(BASE_DIR, "trades_archive.json")) or []
    env_weights = load_env_weights()

    # Wallet-Entscheidungshistorie laden
    decision_log = []
    dlog_path = os.path.join(DATA_DIR, "wallet_decisions.jsonl")
    try:
        for line in open(dlog_path):
            decision_log.append(json.loads(line))
    except Exception:
        pass

    current_multipliers = {}
    for d in decision_log:
        w = d.get("wallet", "").lower()
        if w:
            current_multipliers[w] = d.get("new_multiplier", 1.0)

    closed = [t for t in archive_all if t.get("aufgeloest")]

    stats: dict = defaultdict(lambda: {
        "trades": 0, "wins": 0, "losses": 0,
        "invested": 0.0, "pnl": 0.0,
        "best_pnl": None, "worst_pnl": None,
        "last_trade": None, "trade_sizes": [],
        "name": None,
    })

    for t in closed:
        wallet = (t.get("source_wallet") or "unknown").lower()
        s = stats[wallet]
        s["trades"] += 1
        invested = float(t.get("einsatz_usdc") or 0)
        pnl = float(t.get("gewinn_verlust_usdc") or 0)
        s["invested"] += invested
        s["pnl"] += pnl
        s["trade_sizes"].append(invested)

        if s["best_pnl"] is None or pnl > s["best_pnl"]:
            s["best_pnl"] = pnl
        if s["worst_pnl"] is None or pnl < s["worst_pnl"]:
            s["worst_pnl"] = pnl

        datum = t.get("datum") or ""
        if s["last_trade"] is None or datum > s["last_trade"]:
            s["last_trade"] = datum

        if t.get("ergebnis") == "GEWINN":
            s["wins"] += 1
        else:
            s["losses"] += 1

    rows = []
    for wallet, s in sorted(stats.items(), key=lambda x: x[1]["pnl"], reverse=True):
        win_rate = s["wins"] / s["trades"] * 100 if s["trades"] else 0
        roi = s["pnl"] / s["invested"] * 100 if s["invested"] else 0
        avg_size = sum(s["trade_sizes"]) / len(s["trade_sizes"]) if s["trade_sizes"] else 0
        current_w = current_multipliers.get(wallet, env_weights.get(wallet, 1.0))
        rec = recommend(win_rate, roi, s["trades"], current_w)

        rows.append({
            "wallet": wallet,
            "wallet_short": shorten(wallet),
            "trades": s["trades"],
            "wins": s["wins"],
            "losses": s["losses"],
            "win_rate_pct": round(win_rate, 1),
            "total_pnl_usd": round(s["pnl"], 2),
            "roi_pct": round(roi, 1),
            "avg_trade_size_usd": round(avg_size, 2),
            "best_trade_usd": round(s["best_pnl"], 2) if s["best_pnl"] is not None else 0,
            "worst_trade_usd": round(s["worst_pnl"], 2) if s["worst_pnl"] is not None else 0,
            "current_multiplier": current_w,
            "last_trade": s["last_trade"],
            "recommendation": rec,
        })

    # Stdout-Tabelle
    print(f"Wallet Performance Report — {date.today().isoformat()}")
    print(f"Basis: {len(closed)} abgeschlossene Trades von {len(stats)} Wallets\n")

    header = f"{'Wallet':<14} {'WR%':>5} {'PnL':>7} {'ROI':>7} {'Trades':>7} {'Mult':>6}  Empfehlung"
    print(header)
    print("─" * 75)
    for r in rows:
        wr  = f"{r['win_rate_pct']:.0f}%"
        pnl = f"${r['total_pnl_usd']:+.2f}"
        roi = f"{r['roi_pct']:+.1f}%"
        print(f"{r['wallet_short']:<14} {wr:>5} {pnl:>7} {roi:>7} {r['trades']:>7} "
              f"{r['current_multiplier']:>5.1f}x  {r['recommendation']}")
    print("─" * 75)
    total_pnl = sum(r["total_pnl_usd"] for r in rows)
    total_invested = sum(s["invested"] for s in stats.values())
    overall_wr = sum(s["wins"] for s in stats.values()) / max(1, len(closed)) * 100
    print(f"{'GESAMT':<14} {overall_wr:>4.0f}% ${total_pnl:>+.2f} "
          f"{total_invested > 0 and f'{total_pnl/total_invested*100:+.1f}%' or '  —':>7} "
          f"{len(closed):>7}")

    if not rows:
        print("\nNoch keine abgeschlossenen Trades vorhanden.")

    # JSON speichern
    os.makedirs(ANALYSIS_DIR, exist_ok=True)
    out_path = os.path.join(ANALYSIS_DIR, f"wallet_performance_{date.today().isoformat()}.json")
    output = {
        "date": date.today().isoformat(),
        "total_closed_trades": len(closed),
        "wallets_tracked": len(stats),
        "overall_win_rate_pct": round(overall_wr, 1),
        "total_pnl_usd": round(total_pnl, 2),
        "wallets": rows,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n→ Gespeichert: {out_path}")
    return output


if __name__ == "__main__":
    analyze()
