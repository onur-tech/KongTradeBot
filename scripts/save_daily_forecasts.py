"""
Speichert täglich Forecasts für alle Polymarket-Stationen.
Läuft 4x täglich nach Modell-Updates: 00:05, 06:05, 12:05, 18:05 UTC
"""
import asyncio, aiohttp, json
from datetime import datetime, timezone
from pathlib import Path

DB_DIR = Path("/root/KongTradeBot/data/forecast_history")
DB_DIR.mkdir(exist_ok=True)

with open("/root/KongTradeBot/data/polymarket_stations.json") as f:
    STATIONS = json.load(f)

async def save():
    now = datetime.now(timezone.utc)
    snapshot = {"timestamp": now.isoformat(), "forecasts": {}}

    async with aiohttp.ClientSession() as s:
        for city, info in STATIONS.items():
            try:
                async with s.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": round(info["lat"],4),
                        "longitude": round(info["lon"],4),
                        "daily": "temperature_2m_max",
                        "forecast_days": 3,
                        "timezone": "auto"
                    },
                    timeout=aiohttp.ClientTimeout(total=8)
                ) as r:
                    d = await r.json()
                snapshot["forecasts"][city] = {
                    "today":    d["daily"]["temperature_2m_max"][0],
                    "tomorrow": d["daily"]["temperature_2m_max"][1],
                    "d2":       d["daily"]["temperature_2m_max"][2],
                    "dates":    d["daily"]["time"][:3],
                    "unit": info["unit"]
                }
                await asyncio.sleep(0.15)
            except Exception as e:
                print(f"{city}: {e}")

    fname = DB_DIR / f"fc_{now.strftime('%Y%m%d_%H%M')}.json"
    fname.write_text(json.dumps(snapshot, indent=2))
    print(f"✅ {len(snapshot['forecasts'])} Städte gespeichert: {fname.name}")

asyncio.run(save())
