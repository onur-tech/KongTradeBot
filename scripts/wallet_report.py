#!/usr/bin/env python3
"""
scripts/wallet_report.py — Per-Wallet-Performance Terminal Report

Usage:
    python3 scripts/wallet_report.py              # Top/Bottom wallets + slippage
    python3 scripts/wallet_report.py --days 7
    python3 scripts/wallet_report.py --wallet 0x...
    python3 scripts/wallet_report.py --json
"""
import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from utils.wallet_performance import (
    compute_wallet_stats, compute_by_category,
    compute_by_timeframe, compute_all_wallets,
    WALLET_NAMES,
)


def _pct(v) -> str:
    return f"{v:+.1f}%" if v is not None else "  n/a "


def _usdc(v) -> str:
    return f"{v:+.2f}" if v is not None else "  n/a"


def _hr(v) -> str:
    return f"{v:.1f}%" if v is not None else " n/a "


def _low(s: dict) -> str:
    return " ⚠" if s.get("low_sample") else "  "


def print_all_wallets(wallets: list[dict]) -> None:
    active = [w for w in wallets if w["trades_count"] > 0]
    inactive = [w for w in wallets if w["trades_count"] == 0]

    print("\n╔══════════════════════════════════════════════════════════════════╗")
    print("║            PER-WALLET PERFORMANCE REPORT                        ║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    if not active:
        print("\n  Keine aktiven Wallets im Zeitraum.\n")
        return

    header = f"{'Name':<22} {'Trades':>6} {'W/L/P':>7} {'Hit%':>6} {'ROI%':>7} {'Net PnL':>9} {'Unreal.PnL':>11} {'Slip¢':>6}"
    sep    = "─" * len(header)
    print(f"\n{'Aktive Wallets':}")
    print(sep)
    print(header)
    print(sep)

    for w in active:
        wl = f"{w['wins_count']}/{w['losses_count']}/{w['pending_count']}"
        slip = f"{w['avg_slippage_cents']:.2f}" if w['avg_slippage_cents'] is not None else "  n/a"
        print(
            f"{w['name']:<22}"
            f" {w['trades_count']:>6}"
            f" {wl:>7}"
            f" {_hr(w['hit_rate']):>6}"
            f" {_pct(w['roi_pct']):>7}"
            f" {_usdc(w['net_pnl_usdc']):>9}"
            f" {_usdc(w['unrealized_pnl_usdc']):>11}"
            f" {slip:>6}"
            f"{_low(w)}"
        )

    print(sep)
    total_invested = sum(w["total_invested_usdc"] for w in active)
    total_unreal   = sum(w["unrealized_pnl_usdc"] for w in active)
    print(f"{'GESAMT':<22} {'':>6} {'':>7} {'':>6} {'':>7} {'':>9} {_usdc(total_unreal):>11}")
    print(f"\n  ⚠ = low sample (<5 trades)")

    if inactive:
        print(f"\nInaktive Wallets ({len(inactive)} ohne Trades):")
        names = [w["name"] for w in inactive]
        print("  " + ", ".join(names))


def print_recommendations(wallets: list[dict]) -> None:
    active = [w for w in wallets if w["trades_count"] >= 5]
    if not active:
        print("\n  Zu wenig Daten für Empfehlungen (min. 5 Trades pro Wallet).\n")
        return

    print("\n╔══════════════════════════════════╗")
    print("║        EMPFEHLUNGEN              ║")
    print("╚══════════════════════════════════╝")

    top = sorted(active, key=lambda x: (x["hit_rate"] or 0, x["unrealized_pnl_usdc"]), reverse=True)[:5]
    print("\n✅ TOP Wallets (beibehalten / erhöhen):")
    for w in top:
        print(f"  {w['name']:<22}  Hit={_hr(w['hit_rate'])}  ROI={_pct(w['roi_pct'])}  Unreal={_usdc(w['unrealized_pnl_usdc'])} USDC")

    bottom = sorted(active, key=lambda x: (x["hit_rate"] or 100, x["unrealized_pnl_usdc"]))[:3]
    remove_candidates = [w for w in bottom if (w["hit_rate"] or 100) < 40]
    if remove_candidates:
        print("\n❌ ENTFERNEN kandidaten (Hit-Rate < 40%):")
        for w in remove_candidates:
            print(f"  {w['name']:<22}  Hit={_hr(w['hit_rate'])}  Trades={w['trades_count']}  Note: {w['note']}")
    else:
        print("\n  Kein Wallet mit Hit-Rate < 40% (genug Daten).")


def print_wallet_detail(wallet: str, since_days: int) -> None:
    stats = compute_wallet_stats(wallet, since_days)
    cats  = compute_by_category(wallet, since_days)
    tfs   = compute_by_timeframe(wallet, since_days)

    name = stats["name"]
    print(f"\n╔══════════════════════════════════╗")
    print(f"║  {name:<32}║")
    print(f"╚══════════════════════════════════╝")
    print(f"  Wallet  : {wallet}")
    print(f"  Trades  : {stats['trades_count']} (W={stats['wins_count']} L={stats['losses_count']} P={stats['pending_count']})")
    print(f"  Hit-Rate: {_hr(stats['hit_rate'])}")
    print(f"  ROI     : {_pct(stats['roi_pct'])}")
    print(f"  Invested: {stats['total_invested_usdc']:.2f} USDC")
    print(f"  Net PnL : {_usdc(stats['net_pnl_usdc'])} USDC")
    print(f"  Unreal. : {_usdc(stats['unrealized_pnl_usdc'])} USDC")
    if stats["avg_slippage_cents"] is not None:
        print(f"  Slippage: {stats['avg_slippage_cents']:.2f}¢ avg ({stats['slippage_trades']} trades)")
    print(f"  Note    : {stats['note']}")

    if cats:
        print("\n  Nach Kategorie:")
        print(f"  {'Kategorie':<18} {'T':>4} {'Hit%':>6} {'PnL':>8} {'Unreal':>8}")
        print("  " + "─" * 46)
        for cat, d in cats.items():
            print(f"  {cat:<18} {d['trades']:>4} {_hr(d['hit_rate']):>6} {_usdc(d['pnl']):>8} {_usdc(d['unrealized_pnl']):>8}")

    if tfs:
        tf_labels = {"same_day": "Same-Day", "short": "Short (1-3d)", "medium": "Medium (4-10d)", "long": "Long (11d+)", "unknown": "Unbekannt"}
        print("\n  Nach Zeitfenster:")
        print(f"  {'Zeitfenster':<16} {'T':>4} {'Hit%':>6} {'PnL':>8} {'Unreal':>8}")
        print("  " + "─" * 44)
        for tf, d in tfs.items():
            label = tf_labels.get(tf, tf)
            print(f"  {label:<16} {d['trades']:>4} {_hr(d['hit_rate']):>6} {_usdc(d['pnl']):>8} {_usdc(d['unrealized_pnl']):>8}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days",   type=int, default=30, help="Lookback in Tagen")
    ap.add_argument("--wallet", default="",          help="Einzelne Wallet-Adresse")
    ap.add_argument("--json",   action="store_true", help="JSON-Output statt Tabellen")
    args = ap.parse_args()

    if args.wallet:
        if args.json:
            print(json.dumps({
                "stats":     compute_wallet_stats(args.wallet, args.days),
                "category":  compute_by_category(args.wallet, args.days),
                "timeframe": compute_by_timeframe(args.wallet, args.days),
            }, ensure_ascii=False, indent=2))
        else:
            print_wallet_detail(args.wallet, args.days)
        return

    wallets = compute_all_wallets(since_days=args.days)

    if args.json:
        print(json.dumps(wallets, ensure_ascii=False, indent=2))
        return

    print(f"\nZeitraum: letzte {args.days} Tage  |  Wallets gesamt: {len(wallets)}")
    print_all_wallets(wallets)
    print_recommendations(wallets)
    print()


if __name__ == "__main__":
    main()
