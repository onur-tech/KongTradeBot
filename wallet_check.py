"""
wallet_check.py — Automatische Wallet-Performance Auswertung

Analysiert die Win Rate jeder kopierten Wallet aus dem Archiv.
Empfiehlt welche Wallets ausgetauscht werden sollen.

Täglich/Wöchentlich: python wallet_check.py
Mit Details:         python wallet_check.py --details
"""

import asyncio
import json
import os
import sys
import argparse
from datetime import datetime, date, timedelta
from collections import defaultdict

try:
    import aiohttp
except ImportError:
    print("pip install aiohttp")
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv()

ARCHIVE_FILE = "trades_archive.json"
GAMMA_API    = "https://gamma-api.polymarket.com"
CLOB_API     = "https://clob.polymarket.com"

G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"
C = "\033[96m"; W = "\033[97m"; B = "\033[94m"
P = "\033[95m"; X = "\033[0m"

# Wallet Namen (zur Anzeige)
WALLET_NAMES = {
    "0x7a6192ea6815d3177e978dd3f8c38be5f575af24": "Gambler1968",
    "0x7177a7f5c216809c577c50c77b12aae81f81ddef": "kcnyekchno",
    "0x0b7a6030507efe5db145fbb57a25ba0c5f9d86cf": "HOOK",
    "0xee613b3fc183ee44f9da9c05f53e2da107e3debf": "sovereign2013",
    "0xbaa2bcb5439e985ce4ccf815b4700027d1b92c73": "denizz",
    "0xde7be6d489bce070a959e0cb813128ae659b5f4b": "wan123",
    "0x019782cab5d844f02bafb71f512758be78579f3c": "majorexploiter",
    "0x492442eab586f242b53bda933fd5de859c8a3782": "April#1 Sports",
    "0x02227b8f5a9636e895607edd3185ed6ee5598ff7": "HorizonSplendidView",
    "0xefbc5fec8d7b0acdc8911bdd9a98d6964308f9a2": "reachingthesky",
    "0x2005d16a84ceefa912d4e380cd32e7ff827875ea": "RN1",
}

# Schwellenwerte
WARN_WIN_RATE  = 52.0   # Gelb: unter diesem Wert warnen
KICK_WIN_RATE  = 45.0   # Rot: unter diesem Wert raus empfehlen
MIN_TRADES     = 5      # Mindestanzahl Trades für Auswertung


def load_archive():
    if not os.path.exists(ARCHIVE_FILE):
        print(f"{R}trades_archive.json nicht gefunden!{X}")
        return []
    with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


async def fetch_market(session, market_id):
    """Holt Markt-Status via CLOB API."""
    if not market_id or market_id in ("?", "", "None"):
        return {}
    try:
        url = f"{CLOB_API}/markets/{market_id}"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=6)) as r:
            if r.status == 200:
                return await r.json()
    except Exception:
        pass
    return {}


def normalize_wallet(addr):
    return addr.lower().strip() if addr else ""


def get_wallet_name(addr):
    normalized = normalize_wallet(addr)
    for k, v in WALLET_NAMES.items():
        k_norm = normalize_wallet(k)
        # Exakter Match oder Prefix-Match (gespeicherte Adressen sind manchmal verkürzt)
        if k_norm == normalized or k_norm.startswith(normalized[:12]) or normalized.startswith(k_norm[:12]):
            return v
    return normalized[:12] + "..."


def get_category(question):
    q = question.lower()
    if any(w in q for w in ["tennis","open","grand prix","nba","nhl","nfl","soccer","football","baseball","golf","cricket","vs "," at "]):
        return "Sport"
    elif any(w in q for w in ["iran","israel","ukraine","trump","nuclear","war","ceasefire","election","president","nato","china","russia","peace","hezbollah","hamas"]):
        return "Geopolitik"
    elif any(w in q for w in ["bitcoin","btc","eth","crypto","price","solana","render","token","doge"]):
        return "Crypto"
    elif any(w in q for w in ["fed","interest rate","inflation","gdp","recession","oil","gold","dollar"]):
        return "Makro"
    return "Sonstiges"


def days_ago(n):
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")


async def analyze_wallets(details=False, days=7):
    trades = load_archive()
    if not trades:
        return

    cutoff = days_ago(days)

    # Nur aufgelöste Trades mit market_id und source_wallet
    resolved = [
        t for t in trades
        if t.get("aufgeloest")
        and t.get("source_wallet")
        and t.get("ergebnis") in ("GEWINN", "VERLUST")
    ]

    # Nach Zeitraum filtern
    recent = [t for t in resolved if t.get("datum", "") >= cutoff]
    all_time = resolved

    print(f"\n{C}{'='*65}{X}")
    print(f"{C}  👛 WALLET PERFORMANCE CHECK — {date.today().strftime('%d.%m.%Y')}{X}")
    print(f"{C}  Letzte {days} Tage: {len(recent)} aufgelöste Trades{X}")
    print(f"{C}  All-Time: {len(all_time)} aufgelöste Trades{X}")
    print(f"{C}{'='*65}{X}\n")

    # Wallets gruppieren
    wallet_stats = defaultdict(lambda: {
        "recent_wins": 0, "recent_losses": 0,
        "alltime_wins": 0, "alltime_losses": 0,
        "recent_pnl": 0.0, "alltime_pnl": 0.0,
        "categories": defaultdict(int),
        "last_trade": "",
    })

    for t in all_time:
        raw_w = t.get("source_wallet", "")
        # Verkürzte Adressen wiederherstellen (Format: "0xee613b3f...")
        w = normalize_wallet(raw_w.replace("...", ""))
        if not w or len(w) < 6:
            continue
        # Finde die volle Adresse aus WALLET_NAMES
        for full_addr in WALLET_NAMES.keys():
            if normalize_wallet(full_addr).startswith(w[:12]) or w.startswith(normalize_wallet(full_addr)[:12]):
                w = normalize_wallet(full_addr)
                break
        won = t.get("ergebnis") == "GEWINN"
        pnl = float(t.get("gewinn_verlust_usdc", 0) or 0)
        cat = get_category(t.get("markt", ""))

        wallet_stats[w]["alltime_wins"]   += 1 if won else 0
        wallet_stats[w]["alltime_losses"] += 0 if won else 1
        wallet_stats[w]["alltime_pnl"]    += pnl
        wallet_stats[w]["categories"][cat] += 1

        if t.get("datum", "") > wallet_stats[w]["last_trade"]:
            wallet_stats[w]["last_trade"] = t.get("datum", "")

    for t in recent:
        raw_w = t.get("source_wallet", "")
        w = normalize_wallet(raw_w.replace("...", ""))
        if not w or len(w) < 6:
            continue
        for full_addr in WALLET_NAMES.keys():
            if normalize_wallet(full_addr).startswith(w[:12]) or w.startswith(normalize_wallet(full_addr)[:12]):
                w = normalize_wallet(full_addr)
                break
        won = t.get("ergebnis") == "GEWINN"
        pnl = float(t.get("gewinn_verlust_usdc", 0) or 0)
        wallet_stats[w]["recent_wins"]   += 1 if won else 0
        wallet_stats[w]["recent_losses"] += 0 if won else 1
        wallet_stats[w]["recent_pnl"]    += pnl

    keep = []
    warn = []
    kick = []
    new_wallets = []

    # Zeige ALLE bekannten Wallets — auch die ohne Trades
    all_known = list(WALLET_NAMES.keys())
    # Auch Wallets aus Archiv die nicht in WALLET_NAMES sind
    for w in wallet_stats.keys():
        if not any(normalize_wallet(k).startswith(w[:12]) or w.startswith(normalize_wallet(k)[:12]) for k in all_known):
            all_known.append(w)

    for wallet_addr in all_known:
        norm = normalize_wallet(wallet_addr)
        # Finde matching stats
        stats = None
        for k, v in wallet_stats.items():
            if k.startswith(norm[:12]) or norm.startswith(k[:12]):
                stats = v
                break

        name    = get_wallet_name(wallet_addr)
        r_total = stats["recent_wins"] + stats["recent_losses"] if stats else 0
        a_total = stats["alltime_wins"] + stats["alltime_losses"] if stats else 0
        r_wr    = round(stats["recent_wins"] / r_total * 100, 1) if (stats and r_total > 0) else 0
        a_wr    = round(stats["alltime_wins"] / a_total * 100, 1) if (stats and a_total > 0) else 0
        r_pnl   = stats["recent_pnl"] if stats else 0
        top_cat = max(stats["categories"], key=stats["categories"].get) if (stats and stats["categories"]) else "?"

        if r_total == 0:
            status = "new"
            color  = Y
            new_wallets.append((wallet_addr, name, r_total, a_wr, r_pnl))
            print(f"  🆕 {Y}{name:<22}{X}  "
                  f"7d: {Y}  ---  {X}  "
                  f"P&L: {Y}$ 0.00{X}  "
                  f"(0 Trades)  "
                  f"Neu / noch keine Daten")
        elif r_total < MIN_TRADES:
            status = "new"
            color  = Y
            new_wallets.append((wallet_addr, name, r_total, a_wr, r_pnl))
            print(f"  🆕 {Y}{name:<22}{X}  "
                  f"7d: {Y}{r_wr:5.1f}%{X}  "
                  f"P&L: {G if r_pnl>=0 else R}${r_pnl:+7.2f}{X}  "
                  f"({r_total} Trades)  "
                  f"Zu wenig Daten")
        elif r_wr >= WARN_WIN_RATE:
            status = "keep"
            color  = G
            keep.append((wallet_addr, name, r_wr, r_pnl, r_total, top_cat))
            print(f"  ✅ {G}{name:<22}{X}  "
                  f"7d: {G}{r_wr:5.1f}%{X}  "
                  f"P&L: {G}${r_pnl:+7.2f}{X}  "
                  f"({r_total} Trades)  "
                  f"All-Time: {a_wr:.0f}%  {B}{top_cat}{X}")
        elif r_wr >= KICK_WIN_RATE:
            status = "warn"
            color  = Y
            warn.append((wallet_addr, name, r_wr, r_pnl, r_total, top_cat))
            print(f"  ⚠️  {Y}{name:<22}{X}  "
                  f"7d: {Y}{r_wr:5.1f}%{X}  "
                  f"P&L: {R}${r_pnl:+7.2f}{X}  "
                  f"({r_total} Trades)  "
                  f"All-Time: {a_wr:.0f}%  {B}{top_cat}{X}")
        else:
            status = "kick"
            color  = R
            kick.append((wallet_addr, name, r_wr, r_pnl, r_total, top_cat))
            print(f"  ❌ {R}{name:<22}{X}  "
                  f"7d: {R}{r_wr:5.1f}%{X}  "
                  f"P&L: {R}${r_pnl:+7.2f}{X}  "
                  f"({r_total} Trades)  "
                  f"All-Time: {a_wr:.0f}%  {B}{top_cat}{X}")

    # Empfehlungen
    print(f"\n{C}{'='*65}{X}")
    print(f"{C}  📋 EMPFEHLUNGEN{X}")
    print(f"{C}{'='*65}{X}\n")

    if keep:
        print(f"  {G}BEHALTEN ({len(keep)}):{X}")
        for w, name, wr, pnl, n, cat in keep:
            print(f"     {G}✅ {name}{X} — {wr:.1f}% Win Rate, ${pnl:+.2f} P&L")

    if warn:
        print(f"\n  {Y}BEOBACHTEN ({len(warn)}) — 1 Woche Zeit:{X}")
        for w, name, wr, pnl, n, cat in warn:
            print(f"     {Y}⚠️  {name}{X} — nur {wr:.1f}% Win Rate, ${pnl:+.2f} P&L")
            print(f"       → Nächste Woche unter {KICK_WIN_RATE}% = raus")

    if kick:
        print(f"\n  {R}AUSTAUSCHEN ({len(kick)}) — SOFORT:{X}")
        for w, name, wr, pnl, n, cat in kick:
            print(f"     {R}❌ {name}{X} — nur {wr:.1f}% Win Rate, ${pnl:+.2f} P&L")
        print(f"\n  {R}  → .env updaten und neue Wallets von PolyMonit holen!{X}")
        print(f"  {R}  → https://polymonit.com/leaderboard{X}")

    if new_wallets:
        print(f"\n  {Y}ZU NEU FÜR BEWERTUNG ({len(new_wallets)}):{X}")
        for w, name, n, a_wr, a_pnl in new_wallets:
            print(f"     {Y}🆕 {name}{X} — nur {n} Trades bisher (All-Time: {a_wr:.0f}%)")

    # Gesamtbewertung
    total_recent = sum(s["recent_wins"] + s["recent_losses"] for s in wallet_stats.values())
    total_wins   = sum(s["recent_wins"] for s in wallet_stats.values())
    total_pnl    = sum(s["recent_pnl"] for s in wallet_stats.values())
    wr_total     = round(total_wins / total_recent * 100, 1) if total_recent > 0 else 0
    wi           = "🟢" if wr_total >= 55 else "🟡" if wr_total >= 50 else "🔴"

    print(f"\n{C}{'='*65}{X}")
    print(f"{C}  📊 GESAMT — LETZTE {days} TAGE{X}")
    print(f"{C}{'='*65}{X}")
    print(f"  {wi} Win Rate:   {G if wr_total>=55 else R}{wr_total}%{X}")
    print(f"  📦 Trades:    {total_recent}")
    pnl_c = G if total_pnl >= 0 else R
    print(f"  💰 P&L:       {pnl_c}${total_pnl:+.2f} USDC{X}")

    # Nächste Schritte
    print(f"\n{C}  🔄 NÄCHSTE SCHRITTE:{X}")
    print(f"  1. Jeden Freitag: python wallet_check.py")
    print(f"  2. Monatlich neue Top-Wallets: https://polymonit.com/leaderboard")
    print(f"  3. OddsShift für Echtzeit-Tracking: https://oddsshift.com/smart-money")
    print(f"{C}{'='*65}{X}\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Wallet Performance Check")
    p.add_argument("--details", action="store_true", help="Detaillierte Ansicht")
    p.add_argument("--days",    type=int, default=7, help="Zeitraum in Tagen (default: 7)")
    args = p.parse_args()
    asyncio.run(analyze_wallets(details=args.details, days=args.days))
