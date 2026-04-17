"""
wallet_init.py — Historische Wallet-Daten einmalig holen

Holt Win Rate, Profit und Spezialisierung aller Wallets
von predicts.guru und frenflow.com als Startwerte.

Einmalig ausführen: python wallet_init.py
Danach kombiniert wallet_check.py historische + eigene Daten.
"""

import asyncio
import json
import os
import re
import sys
from datetime import datetime

try:
    import aiohttp
except ImportError:
    print("pip install aiohttp")
    sys.exit(1)

WALLET_FILE = "wallet_history.json"

G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"
C = "\033[96m"; W = "\033[97m"; B = "\033[94m"; X = "\033[0m"

WALLETS = {
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

# Manuelle Fallback-Daten aus Recherche (Stand April 2026)
MANUAL_DATA = {
    "0xee613b3fc183ee44f9da9c05f53e2da107e3debf": {
        "name": "sovereign2013",
        "profit_usd": 3500000,
        "trades": 39797,
        "win_rate": 57.0,
        "volume_usd": 389400000,
        "specialty": "Sport",
        "active_since": "Jul 2025",
        "biggest_win": 179120,
        "source": "frenflow.com",
    },
    "0x019782cab5d844f02bafb71f512758be78579f3c": {
        "name": "majorexploiter",
        "profit_usd": 3700000,
        "trades": 3,
        "win_rate": 76.0,
        "volume_usd": 9400000,
        "specialty": "Sport",
        "active_since": "Feb 2026",
        "biggest_win": 2420000,
        "source": "frenflow.com",
    },
    "0x02227b8f5a9636e895607edd3185ed6ee5598ff7": {
        "name": "HorizonSplendidView",
        "profit_usd": 4016108,
        "trades": 0,
        "win_rate": 65.0,
        "volume_usd": 6493031,
        "specialty": "Sport",
        "active_since": "2025",
        "biggest_win": 0,
        "source": "polymonit.com",
    },
    "0x0b7a6030507efe5db145fbb57a25ba0c5f9d86cf": {
        "name": "HOOK",
        "profit_usd": 34964,
        "trades": 31,
        "win_rate": 71.0,
        "volume_usd": 110000,
        "specialty": "Tech-Events",
        "active_since": "2025",
        "biggest_win": 3610,
        "source": "predicts.guru",
    },
    "0xbaa2bcb5439e985ce4ccf815b4700027d1b92c73": {
        "name": "denizz",
        "profit_usd": 751183,
        "trades": 0,
        "win_rate": 60.0,
        "volume_usd": 5263511,
        "specialty": "Geopolitik/Polytics",
        "active_since": "2025",
        "biggest_win": 0,
        "source": "polymonit.com",
    },
    "0x492442eab586f242b53bda933fd5de859c8a3782": {
        "name": "April#1 Sports",
        "profit_usd": 6289409,
        "trades": 0,
        "win_rate": 65.0,
        "volume_usd": 24467114,
        "specialty": "Sport",
        "active_since": "2026",
        "biggest_win": 0,
        "source": "polymonit.com",
    },
    "0xefbc5fec8d7b0acdc8911bdd9a98d6964308f9a2": {
        "name": "reachingthesky",
        "profit_usd": 3742635,
        "trades": 0,
        "win_rate": 63.0,
        "volume_usd": 0,
        "specialty": "Sport",
        "active_since": "2025",
        "biggest_win": 0,
        "source": "polymonit.com",
    },
    "0x2005d16a84ceefa912d4e380cd32e7ff827875ea": {
        "name": "RN1",
        "profit_usd": 0,
        "trades": 0,
        "win_rate": 0,
        "volume_usd": 0,
        "specialty": "Diversifiziert",
        "active_since": "2026",
        "biggest_win": 0,
        "source": "polymonit.com",
    },
}


async def fetch_predicts_guru(session, address):
    """Holt Wallet-Stats von predicts.guru."""
    try:
        url = f"https://www.predicts.guru/checker/{address}"
        headers = {"User-Agent": "Mozilla/5.0"}
        async with session.get(url, headers=headers,
                               timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status != 200:
                return {}
            text = await r.text()

            # Win Rate extrahieren
            wr_match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*win\s*rate', text, re.IGNORECASE)
            win_rate = float(wr_match.group(1)) if wr_match else 0

            # Profit extrahieren
            pnl_match = re.search(r'\$([0-9,]+(?:\.\d+)?)\s*(?:PnL|profit|P&L)', text, re.IGNORECASE)
            profit = float(pnl_match.group(1).replace(',', '')) if pnl_match else 0

            # Trades extrahieren
            trades_match = re.search(r'(\d+)\s*total\s*trades', text, re.IGNORECASE)
            trades = int(trades_match.group(1)) if trades_match else 0

            if win_rate > 0 or profit > 0:
                return {
                    "win_rate": win_rate,
                    "profit_usd": profit,
                    "trades": trades,
                    "source": "predicts.guru",
                }
    except Exception:
        pass
    return {}


async def fetch_frenflow(session, address):
    """Holt Wallet-Stats von frenflow.com."""
    try:
        # Erst Username suchen
        url = f"https://polymarket.com/profile/{address}"
        headers = {"User-Agent": "Mozilla/5.0"}
        async with session.get(url, headers=headers,
                               timeout=aiohttp.ClientTimeout(total=8)) as r:
            if r.status != 200:
                return {}
            text = await r.text()

            # Username extrahieren
            user_match = re.search(r'"username"\s*:\s*"([^"]+)"', text)
            if not user_match:
                return {}
            username = user_match.group(1)

        # Dann FrenFlow aufrufen
        ff_url = f"https://www.frenflow.com/traders/@{username}"
        async with session.get(ff_url, headers=headers,
                               timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status != 200:
                return {}
            text = await r.text()

            profit_match = re.search(r'\+\$([0-9,.]+[MK]?)\s*Profit', text, re.IGNORECASE)
            profit = 0
            if profit_match:
                p_str = profit_match.group(1).replace(',', '')
                if 'M' in p_str:
                    profit = float(p_str.replace('M', '')) * 1_000_000
                elif 'K' in p_str:
                    profit = float(p_str.replace('K', '')) * 1_000
                else:
                    profit = float(p_str)

            trades_match = re.search(r'(\d[\d,]+)\s*Predictions', text)
            trades = int(trades_match.group(1).replace(',', '')) if trades_match else 0

            if profit > 0:
                return {
                    "profit_usd": profit,
                    "trades": trades,
                    "source": "frenflow.com",
                }
    except Exception:
        pass
    return {}


async def run():
    print(f"\n{C}{'='*65}{X}")
    print(f"{C}  📊 WALLET INIT — Historische Daten laden{X}")
    print(f"{C}  {len(WALLETS)} Wallets werden abgerufen...{X}")
    print(f"{C}{'='*65}{X}\n")

    results = {}

    connector = aiohttp.TCPConnector(limit=3)
    async with aiohttp.ClientSession(connector=connector) as session:
        for address, name in WALLETS.items():
            print(f"  🔍 {W}{name}{X} ({address[:12]}...)", flush=True)

            # Erst manuellen Fallback laden
            data = MANUAL_DATA.get(address, {}).copy()

            # Dann live von predicts.guru versuchen
            live = await fetch_predicts_guru(session, address)
            if live and live.get("win_rate", 0) > 0:
                data.update(live)
                print(f"     {G}✅ Live von predicts.guru: Win Rate {live['win_rate']:.1f}%{X}")
            elif data:
                wr = data.get("win_rate", 0)
                profit = data.get("profit_usd", 0)
                if profit > 0:
                    profit_str = f"${profit/1_000_000:.1f}M" if profit >= 1_000_000 else f"${profit:,.0f}"
                    print(f"     {Y}📋 Manuell: Win Rate {wr:.0f}% | Profit {profit_str}{X}")
                else:
                    print(f"     {Y}📋 Manuell: Noch keine Daten verfügbar{X}")
            else:
                data = {
                    "name": name,
                    "profit_usd": 0,
                    "trades": 0,
                    "win_rate": 0,
                    "specialty": "Unbekannt",
                    "source": "keine Daten",
                }
                print(f"     {R}❌ Keine Daten gefunden{X}")

            data["name"]       = name
            data["address"]    = address
            data["updated_at"] = datetime.now().isoformat()
            results[address]   = data
            await asyncio.sleep(0.5)

    # Speichern
    with open(WALLET_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n{C}{'='*65}{X}")
    print(f"{C}  📋 ZUSAMMENFASSUNG{X}")
    print(f"{C}{'='*65}{X}\n")

    # Tabelle ausgeben
    print(f"  {'Name':<22} {'Win Rate':>10} {'Profit':>12} {'Trades':>8}  Spezialisierung")
    print(f"  {'─'*22} {'─'*10} {'─'*12} {'─'*8}  {'─'*15}")

    for addr, d in sorted(results.items(), key=lambda x: x[1].get("profit_usd", 0), reverse=True):
        wr     = d.get("win_rate", 0)
        profit = d.get("profit_usd", 0)
        trades = d.get("trades", 0)
        spec   = d.get("specialty", "?")[:15]
        name   = d.get("name", "?")[:22]

        wr_color = G if wr >= 60 else Y if wr >= 50 else R if wr > 0 else W
        profit_str = f"${profit/1_000_000:.1f}M" if profit >= 1_000_000 else f"${profit:,.0f}" if profit > 0 else "  —"
        wr_str = f"{wr:.1f}%" if wr > 0 else "  —"

        print(f"  {W}{name:<22}{X} {wr_color}{wr_str:>10}{X} {G}{profit_str:>12}{X} {trades:>8}  {B}{spec}{X}")

    print(f"\n  {G}✅ Gespeichert: {WALLET_FILE}{X}")
    print(f"  {C}wallet_check.py nutzt diese Daten jetzt automatisch!{X}")
    print(f"\n{C}{'='*65}{X}\n")


if __name__ == "__main__":
    asyncio.run(run())
