import asyncio
import aiohttp
import json

async def test():
    async with aiohttp.ClientSession() as s:
        r = await s.get(
            "https://gamma-api.polymarket.com/markets",
            params={"q": "San Francisco Giants Cincinnati", "limit": 1}
        )
        d = await r.json()
        item = d[0] if isinstance(d, list) else d
        # Nur relevante Felder zeigen
        fields = ["question", "title", "resolved", "closed", "active", 
                  "endDate", "resolutionSource", "winnerOutcome", 
                  "winner", "resolvedBy", "liquidity"]
        for k in fields:
            if k in item:
                print(f"{k}: {item[k]}")

asyncio.run(test())
