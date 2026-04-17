"""Fetch missing 4 wallets and add to wallet_history.json"""
import asyncio, json, re, sys
from datetime import datetime

try:
    import aiohttp
except ImportError:
    print("pip install aiohttp")
    sys.exit(1)

MISSING = {
    "0xbddf61af533ff524d27154e589d2d7a81510c684": "Countryside",
    "0xde17f7144fbd0eddb2679132c10ff5e74b120988": "Crypto Spezialist",
    "0xd84c2b6d65dc596f49c7b6aadd6d74ca91e407b9": "BoneReader",
    "0xdb27bf2ac5d428a9c63dbc914611036855a6c56e": "DrPufferfish",
}

async def fetch_guru(session, address):
    try:
        url = f"https://www.predicts.guru/checker/{address}"
        headers = {"User-Agent": "Mozilla/5.0"}
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=12)) as r:
            if r.status != 200:
                return {}
            text = await r.text()
            wr     = re.search(r"(\d+(?:\.\d+)?)\s*%\s*win\s*rate", text, re.IGNORECASE)
            pnl    = re.search(r"\$([0-9,]+(?:\.\d+)?)\s*(?:PnL|profit|P&L)", text, re.IGNORECASE)
            trades = re.search(r"(\d+)\s*total\s*trades", text, re.IGNORECASE)
            result = {}
            if wr:     result["win_rate"]    = float(wr.group(1))
            if pnl:    result["profit_usd"]  = float(pnl.group(1).replace(",", ""))
            if trades: result["trades"]      = int(trades.group(1))
            if result: result["source"]      = "predicts.guru"
            return result
    except Exception as e:
        print(f"  guru error: {e}")
        return {}

async def fetch_polymarket_buys(session, address):
    try:
        url = "https://data-api.polymarket.com/activity"
        params = {"user": address, "limit": 200, "type": "BUY"}
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as r:
            if r.status != 200:
                return 0
            data = await r.json()
            lst = data if isinstance(data, list) else data.get("data", [])
            return len(lst)
    except Exception as e:
        print(f"  polymarket error: {e}")
        return 0

async def run():
    with open("wallet_history.json", encoding="utf-8") as f:
        history = json.load(f)

    print(f"wallet_history.json geladen: {len(history)} Wallets")
    print()

    async with aiohttp.ClientSession() as session:
        for address, name in MISSING.items():
            print(f"Lade {name} ({address[:14]}...)...", flush=True)
            guru, buy_count = await asyncio.gather(
                fetch_guru(session, address),
                fetch_polymarket_buys(session, address),
            )
            entry = {
                "name":       name,
                "address":    address,
                "profit_usd": guru.get("profit_usd", 0),
                "trades":     guru.get("trades", buy_count),
                "win_rate":   guru.get("win_rate", 0),
                "source":     guru.get("source", "polymarket-api"),
                "updated_at": datetime.now().isoformat(),
            }
            if guru.get("win_rate", 0) > 0:
                print(f"  -> predicts.guru: WR {entry['win_rate']}% | Profit ${entry['profit_usd']:,.0f} | {entry['trades']} Trades")
            else:
                print(f"  -> Keine guru-Daten | {buy_count} BUYs (Polymarket API)")
            history[address] = entry
            await asyncio.sleep(0.8)

    with open("wallet_history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    print(f"\nGespeichert. Jetzt {len(history)} Wallets in wallet_history.json")

if __name__ == "__main__":
    asyncio.run(run())
