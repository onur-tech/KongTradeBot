"""
Tägliche Datenpunkt-Sammlung für Weather Backtest.
1. Marktpreise offener Wetter-Märkte (Events-API offset 2700-3600)
2. Forecast für alle Stationen (Open-Meteo)
Nach 30 Tagen: echter Backtest möglich.
"""
import asyncio, aiohttp, json
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB_DIR = Path("/root/KongTradeBot/data/daily_datapoints")
DB_DIR.mkdir(exist_ok=True)

with open("/root/KongTradeBot/data/polymarket_stations.json") as f:
    STATIONS = json.load(f)

def parse_token_ids(raw):
    if isinstance(raw, list): return raw
    if isinstance(raw, str):
        try: return json.loads(raw)
        except: pass
    return []

async def collect():
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    snapshot = {"timestamp": now.isoformat(), "date": today,
                "markets": {}, "forecasts": {}}

    async with aiohttp.ClientSession() as s:

        # 1. Offene Wetter-Märkte: Offset 2700-3600
        print("Lade offene Wetter-Märkte...")
        n_markets = 0
        try:
            for offset in range(2700, 3900, 300):
                async with s.get(
                    "https://gamma-api.polymarket.com/events",
                    params={"limit":300,"tag_slug":"weather",
                            "order":"end_date_max:desc","offset":offset},
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as r:
                    batch = await r.json()
                if not isinstance(batch, list) or not batch:
                    break

                city_lower = {c.lower(): c for c in STATIONS}
                for e in batch:
                    if "highest temperature" not in e.get("title","").lower():
                        continue
                    if e.get("closed", True):
                        continue
                    try:
                        end_dt = datetime.fromisoformat(
                            e.get("endDate","").replace("Z","+00:00"))
                        if end_dt < now:
                            continue
                    except:
                        continue

                    city = next((c for cl, c in city_lower.items()
                                 if cl in e.get("title","").lower()), None)

                    for m in e.get("markets", []):
                        cid = m.get("conditionId","")
                        token_ids = parse_token_ids(m.get("clobTokenIds",""))
                        if not cid or not token_ids:
                            continue

                        price = None
                        try:
                            async with s.get(
                                "https://clob.polymarket.com/prices-history",
                                params={"market": token_ids[0],
                                        "startTs": int(now.timestamp()-3600),
                                        "endTs": int(now.timestamp()),
                                        "fidelity": 60},
                                timeout=aiohttp.ClientTimeout(total=8)
                            ) as r2:
                                ph = await r2.json()
                            hist = ph.get("history",[])
                            if hist:
                                price = float(hist[-1].get("p",0))
                        except:
                            pass

                        snapshot["markets"][cid] = {
                            "city": city,
                            "question": m.get("question",""),
                            "end_date": m.get("endDate",""),
                            "token_ids": token_ids,
                            "price_now": price,
                            "volume": float(m.get("volume","0") or 0)
                        }
                        n_markets += 1
                        await asyncio.sleep(0.1)

                await asyncio.sleep(0.3)

        except Exception as e:
            print(f"  Märkte Fehler: {e}")

        print(f"  {n_markets} Wetter-Märkte gespeichert")

        # 2. Forecasts
        print("Lade Forecasts...")
        for city, info in STATIONS.items():
            try:
                async with s.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={"latitude": round(info["lat"],4),
                            "longitude": round(info["lon"],4),
                            "daily": "temperature_2m_max",
                            "forecast_days": 3, "timezone": "auto"},
                    timeout=aiohttp.ClientTimeout(total=8)
                ) as r:
                    d = await r.json()
                snapshot["forecasts"][city] = {
                    "today":    d["daily"]["temperature_2m_max"][0],
                    "tomorrow": d["daily"]["temperature_2m_max"][1],
                    "d2":       d["daily"]["temperature_2m_max"][2],
                    "dates":    d["daily"]["time"][:3]
                }
                await asyncio.sleep(0.12)
            except:
                pass

        print(f"  {len(snapshot['forecasts'])} Städte Forecast gespeichert")

    fname = DB_DIR / f"dp_{today}.json"
    fname.write_text(json.dumps(snapshot, indent=2))
    print(f"\n✅ Datenpunkt gespeichert: {fname.name}")
    print(f"   Märkte: {len(snapshot['markets'])}")
    print(f"   Forecasts: {len(snapshot['forecasts'])}")

    if snapshot["markets"]:
        print("\nStichprobe (5 Märkte):")
        for cid, v in list(snapshot["markets"].items())[:5]:
            p = v.get("price_now")
            p_str = f"{p:.2f}" if p else "N/A"
            icon = "✅" if p and 0.05 < p < 0.95 else "⚠️"
            print(f"  {icon} {(v.get('city') or '?'):10} "
                  f"{v['question'][:48]:48} {p_str}")

asyncio.run(collect())
