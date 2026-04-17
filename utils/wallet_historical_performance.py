"""
wallet_historical_performance.py — Historische Win-Rate aller TARGET_WALLETS

Quelle: Polymarket Data API (data-api.polymarket.com/activity)
Methode: BUY-Aktivitäten vs. REDEEM-Aktivitäten per conditionId abgleichen
         REDEEM = gewonnene Position eingelöst → WIN
         BUY ohne REDEEM = verloren oder noch offen

Limitation: Nur letzte ~500 BUY + 500 REDEEM Aktivitäten analysiert.
            Ergebnis zeigt "recente" Performance, nicht unbedingt All-Time.

Ausführen: python utils/wallet_historical_performance.py
"""

import asyncio
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

try:
    import aiohttp
except ImportError:
    print("pip install aiohttp")
    sys.exit(1)

# .env laden (falls dotenv vorhanden)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "wallet_historical_performance.json")
ACTIVITY_URL = "https://data-api.polymarket.com/activity"
GURU_URL     = "https://www.predicts.guru/checker/{}"

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
    "0xbddf61af533ff524d27154e589d2d7a81510c684": "Wallet-12",
    "0xde17f7144fbd0eddb2679132c10ff5e74b120988": "Wallet-13",
    "0xd84c2b6d65dc596f49c7b6aadd6d74ca91e407b9": "Wallet-14",
    "0xdb27bf2ac5d428a9c63dbc914611036855a6c56e": "Wallet-15",
}

CATEGORIES = ["Sport", "Geopolitik", "Crypto", "Makro", "Sonstiges"]


def get_category(question: str) -> str:
    q = question.lower()
    if any(w in q for w in ["tennis", "open", "grand prix", "nba", "nhl", "nfl", "soccer",
                              "football", "baseball", "golf", "cricket", "vs "]):
        return "Sport"
    if any(w in q for w in ["iran", "israel", "ukraine", "trump", "nuclear", "war",
                              "ceasefire", "election", "president", "nato", "china",
                              "russia", "peace"]):
        return "Geopolitik"
    if any(w in q for w in ["bitcoin", "btc", "eth", "crypto", "price", "solana",
                              "render", "token", "blockchain"]):
        return "Crypto"
    if any(w in q for w in ["fed", "interest rate", "inflation", "gdp", "recession",
                              "oil", "gold"]):
        return "Makro"
    return "Sonstiges"


def _load_target_wallets() -> list:
    raw = os.getenv("TARGET_WALLETS", "")
    if raw:
        return [w.strip().lower() for w in raw.split(",") if w.strip()]
    return list(WALLET_NAMES.keys())


async def _fetch_activities(session: aiohttp.ClientSession, wallet: str,
                             activity_type: str, limit: int = 500) -> list:
    """Holt Aktivitäten eines bestimmten Typs von der Polymarket Data API."""
    try:
        params = {"user": wallet, "limit": limit, "type": activity_type}
        async with session.get(ACTIVITY_URL, params=params,
                               timeout=aiohttp.ClientTimeout(total=20)) as r:
            if r.status == 429:
                await asyncio.sleep(5)
                return []
            if r.status != 200:
                return []
            data = await r.json()
            return data if isinstance(data, list) else data.get("data", [])
    except Exception:
        return []


async def _fetch_guru_stats(session: aiohttp.ClientSession, wallet: str) -> dict:
    """Versucht Gesamt-Stats von predicts.guru zu holen."""
    try:
        url = GURU_URL.format(wallet)
        headers = {"User-Agent": "Mozilla/5.0"}
        async with session.get(url, headers=headers,
                               timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status != 200:
                return {}
            text = await r.text()
            wr = re.search(r'(\d+(?:\.\d+)?)\s*%\s*win', text, re.IGNORECASE)
            pnl = re.search(r'\$([0-9,]+(?:\.\d+)?)\s*(?:PnL|profit)', text, re.IGNORECASE)
            trades = re.search(r'(\d[\d,]*)\s*total\s*trades', text, re.IGNORECASE)
            result = {}
            if wr:
                result["guru_win_rate_pct"] = float(wr.group(1))
            if pnl:
                result["guru_profit_usd"] = float(pnl.group(1).replace(",", ""))
            if trades:
                result["guru_total_trades"] = int(trades.group(1).replace(",", ""))
            return result
    except Exception:
        return {}


def _analyze_wallet(buys: list, redeems: list) -> dict:
    """
    Berechnet per-Kategorie Win Rate durch BUY/REDEEM conditionId Abgleich.

    Wins = conditionIds die in BUY und REDEEM vorkommen.
    Losses = conditionIds die nur in BUY vorkommen (und wahrscheinlich aufgelöst wurden).
    """
    # conditionId → {category, title}
    buy_conditions: dict[str, str] = {}
    buy_by_cat: dict[str, set] = defaultdict(set)

    for a in buys:
        cid = a.get("conditionId", "")
        title = a.get("title", "")
        if cid and title:
            cat = get_category(title)
            buy_conditions[cid] = cat
            buy_by_cat[cat].add(cid)

    redeem_cids: set = set()
    redeem_by_cat: dict[str, set] = defaultdict(set)

    for a in redeems:
        cid = a.get("conditionId", "")
        title = a.get("title", "")
        if cid:
            redeem_cids.add(cid)
            cat = get_category(title) if title else buy_conditions.get(cid, "Sonstiges")
            redeem_by_cat[cat].add(cid)

    categories = {}
    for cat in CATEGORIES:
        all_buys = buy_by_cat.get(cat, set())
        wins     = all_buys & redeem_cids
        # Nur Markets zählen wo wir wissen ob Win oder nicht
        # (alle gekauften conditionIds in dieser Kategorie)
        total = len(all_buys)
        win_count = len(wins)
        categories[cat] = {
            "markets_bought": total,
            "markets_won":    win_count,
            "win_rate_pct":   round(win_count / total * 100, 1) if total > 0 else None,
        }

    total_buys = len(buy_conditions)
    total_wins = len(set(buy_conditions.keys()) & redeem_cids)

    return {
        "total_markets_bought": total_buys,
        "total_markets_won":    total_wins,
        "overall_win_rate_pct": round(total_wins / total_buys * 100, 1) if total_buys > 0 else None,
        "categories":           categories,
        "note": "Win Rate = Märkte mit REDEEM / Märkte gekauft (letzte ~500 BUYs+REDEEMs)",
    }


async def analyze_all_wallets() -> dict:
    wallets = _load_target_wallets()
    print(f"Analysiere {len(wallets)} Wallets von Polymarket API...\n")

    results = {}
    connector = aiohttp.TCPConnector(limit=5)

    async with aiohttp.ClientSession(connector=connector) as session:
        for i, wallet in enumerate(wallets, 1):
            name = WALLET_NAMES.get(wallet, wallet[:10] + "...")
            print(f"[{i:2d}/{len(wallets)}] {name} ({wallet[:14]}...) ", end="", flush=True)

            # BUYs und REDEEMs parallel holen
            buys, redeems, guru = await asyncio.gather(
                _fetch_activities(session, wallet, "BUY"),
                _fetch_activities(session, wallet, "REDEEM"),
                _fetch_guru_stats(session, wallet),
            )

            stats = _analyze_wallet(buys, redeems)
            stats.update(guru)
            stats["wallet"] = wallet
            stats["name"]   = name
            stats["fetched_at"] = datetime.utcnow().isoformat() + "Z"

            wr = stats.get("overall_win_rate_pct")
            wr_str = f"{wr:.1f}%" if wr is not None else "n/a"
            print(f"-> {stats['total_markets_bought']} BUYs | WR: {wr_str}")

            results[name] = stats

            # Kurze Pause um Rate-Limit zu vermeiden
            if i < len(wallets):
                await asyncio.sleep(0.5)

    return results


# ── Ausgabe ───────────────────────────────────────────────────────────────────

def _print_table(results: dict):
    CATS = ["Sport", "Geopolitik", "Crypto", "Makro", "Sonstiges"]
    COL_W = 22

    header = f"{'Wallet':<20}  {'Ges. WR':>8}  " + "  ".join(f"{c:>12}" for c in CATS)
    print("\n" + "=" * len(header))
    print(header)
    print("=" * len(header))

    for name, s in results.items():
        wr = s.get("overall_win_rate_pct")
        wr_str = f"{wr:.1f}%" if wr is not None else "  n/a "

        cat_cols = []
        for cat in CATS:
            c = s["categories"].get(cat, {})
            r = c.get("win_rate_pct")
            n = c.get("markets_bought", 0)
            if r is None or n == 0:
                cat_cols.append(f"{'  —':>12}")
            else:
                cat_cols.append(f"{r:>6.1f}% ({n:>3})")

        row = f"{name[:20]:<20}  {wr_str:>8}  " + "  ".join(cat_cols)
        print(row)

    print("=" * len(header))
    print("\nLegende: WR% (Anzahl gekaufte Märkte) | Win Rate = REDEEM/BUY (letzte ~500)\n")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    results = asyncio.run(analyze_all_wallets())

    _print_table(results)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Gespeichert: wallet_historical_performance.json")

    # Top-Performer je Kategorie
    print("\nTop-Performer per Kategorie (min. 5 Märkte):")
    for cat in ["Sport", "Geopolitik", "Crypto", "Makro", "Sonstiges"]:
        best_name, best_wr, best_n = None, 0.0, 0
        for name, s in results.items():
            c = s["categories"].get(cat, {})
            wr = c.get("win_rate_pct") or 0.0
            n  = c.get("markets_bought", 0)
            if n >= 5 and wr > best_wr:
                best_wr, best_name, best_n = wr, name, n
        if best_name:
            print(f"  {cat:<12}: {best_name} ({best_wr:.1f}% in {best_n} Märkten)")
        else:
            print(f"  {cat:<12}: — (keine Wallet mit >=5 Märkten)")
