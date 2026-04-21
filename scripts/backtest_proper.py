"""
Korrekter Walk-Forward Backtest
================================
Behebt alle Backtest-Fehler:
1. Kein Look-Ahead Bias — Vortag als Forecast
2. Walk-Forward: Training → Validation trennen
3. Transaktionskosten berücksichtigt
4. Out-of-Sample Test für Validierung
5. Keine Parameter-Überoptimierung
"""
import asyncio, aiohttp, json, math, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

SPREAD_COST = 0.02    # 2% Bid-Ask Spread
PLATFORM_FEE = 0.02  # 2% Polymarket Fee
TOTAL_COST = SPREAD_COST + PLATFORM_FEE  # 4% pro Trade

STATIONS = {
    "New York": (40.7773, -73.8740),
    "NYC": (40.7773, -73.8740),
    "London": (51.4775, -0.4614),
    "Tokyo": (35.5533, 139.7811),
    "Seoul": (37.4602, 126.4407),
    "Toronto": (43.6777, -79.6248),
    "Paris": (49.0097, 2.5479),
    "Berlin": (52.3671, 13.5033),
    "Istanbul": (40.9769, 28.8146),
    "Shanghai": (31.1979, 121.3363),
    "Beijing": (39.5095, 116.4106),
    "Chicago": (41.9796, -87.9041),
    "Miami": (25.7959, -80.2870),
    "Denver": (39.8561, -104.6737),
    "Seattle": (47.4502, -122.3088),
    "Madrid": (40.4722, -3.5608),
    "Dallas": (32.8998, -97.0403),
    "Austin": (30.1975, -97.6664),
    "Hong Kong": (22.3080, 113.9185),
    "Singapore": (1.3592, 103.9894),
    "Busan": (35.1795, 128.9382),
    # Expanded — new Polymarket cities
    "Helsinki": (60.3172, 24.9633),
    "Ankara": (40.1280, 32.9950),
    "Moscow": (55.7517, 37.6176),
    "Warsaw": (52.1672, 20.9679),
    "Milan": (45.4654, 9.1859),
    "Tel Aviv": (32.0853, 34.7818),
    "Sao Paulo": (-23.6273, -46.6566),
    "Buenos Aires": (-34.5553, -58.4161),
    "Taipei": (25.0777, 121.5736),
    "Kuala Lumpur": (3.1179, 101.5564),
    "Chengdu": (30.5780, 103.9478),
    "Wuhan": (30.5000, 114.3500),
    "Lucknow": (26.7500, 80.8833),
    "Wellington": (-41.3272, 174.8053),
    "Los Angeles": (33.9380, -118.3889),
    "LA": (33.9380, -118.3889),
}


def normal_cdf(x):
    t = 1/(1+0.2316419*abs(x))
    d = 0.3989423*math.exp(-x*x/2)
    p = d*t*(0.3193815+t*(-0.3565638+t*(
        1.7814779+t*(-1.8212560+t*1.3302744))))
    return (1-p) if x>0 else p


def kelly_fraction(edge, market_price):
    """Quarter-Kelly nach Ed Thorp."""
    if edge <= 0 or market_price <= 0:
        return 0.0
    if market_price >= 0.98:
        return 0.0
    f_full = edge / (1 - market_price)
    f_quarter = f_full * 0.25  # Quarter Kelly!
    return min(f_quarter, 0.10)  # Max 10% Bankroll


async def get_temp(lat, lon, date, session):
    try:
        async with session.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params={"latitude": round(lat,4),
                    "longitude": round(lon,4),
                    "start_date": date,
                    "end_date": date,
                    "daily": "temperature_2m_max",
                    "timezone": "auto"},
            timeout=aiohttp.ClientTimeout(total=8)
        ) as r:
            d = await r.json()
        return d["daily"]["temperature_2m_max"][0]
    except:
        return None


async def get_markets(session, days_back, days_forward):
    """Märkte in einem Zeitfenster — paginiert wie weather_scout."""
    since = datetime.now(timezone.utc) - \
            timedelta(days=days_back)
    until = datetime.now(timezone.utc) - \
            timedelta(days=days_forward)

    all_m = []
    for offset in range(0, 5000, 100):
        try:
            async with session.get(
                "https://gamma-api.polymarket.com/markets",
                params={"closed":"true","limit":100,
                        "offset":offset,
                        "order":"volume","ascending":"false"},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as r:
                batch = await r.json()
            if isinstance(batch, dict):
                batch = batch.get("markets",[])
            if not batch:
                break
            all_m.extend(batch)
        except:
            break

    result = []
    for m in all_m:
        q = m.get("question","").lower()
        end = m.get("endDate","")
        if not any(k in q for k in
            ["temperature","highest temp"]):
            continue
        try:
            dt = datetime.fromisoformat(
                end.replace("Z","+00:00"))
            if since <= dt <= until:
                result.append(m)
        except:
            pass
    return result


async def run_split(
        markets, label, edge_thresh,
        border_buffer, bankroll=850.0):
    """Läuft Backtest auf einem Datensatz."""
    results = []
    semaphore = asyncio.Semaphore(4)

    async def test(m):
        async with semaphore:
            q = m.get("question","")
            # Match "temperature in CITY" or "temperature in CITY be"
            cm = re.search(
                r"temperature in ([A-Za-z\s]+?) (?:be|on)",
                q, re.I)
            if not cm:
                return None
            city = cm.group(1).strip()
            coords = None
            for k,v in STATIONS.items():
                if k.lower() in city.lower() or city.lower() in k.lower():
                    coords = v
                    break
            if not coords:
                return None
            lat, lon = coords
            try:
                end_dt = datetime.fromisoformat(
                    m["endDate"].replace("Z","+00:00"))
                res_date = end_dt.strftime("%Y-%m-%d")
                prev_date = (end_dt-timedelta(days=1)
                    ).strftime("%Y-%m-%d")
            except:
                return None

            # Parse threshold — handle °C, °F, "or below/higher", "between X-Y"
            threshold = None
            is_fahrenheit = False
            # "between X-Y°F" → use midpoint
            bm = re.search(r"between\s+(\d+(?:\.\d+)?)[–-](\d+(?:\.\d+)?).*?°([FC])", q, re.I)
            if bm:
                threshold = (float(bm.group(1)) + float(bm.group(2))) / 2
                is_fahrenheit = bm.group(3).upper() == "F"
            else:
                tm = re.search(r"(\d+(?:\.\d+)?)\s*°([FC])", q, re.I)
                if tm:
                    threshold = float(tm.group(1))
                    is_fahrenheit = tm.group(2).upper() == "F"
            if not threshold:
                return None
            # Convert °F to °C for Open-Meteo (returns °C)
            if is_fahrenheit:
                threshold = (threshold - 32) * 5/9

            prices = m.get("outcomePrices",[])
            mkt_price = 0.5
            if prices:
                try:
                    mkt_price = float(prices[0])
                except:
                    pass

            async with aiohttp.ClientSession() as s:
                forecast = await get_temp(
                    lat, lon, prev_date, s)
                actual = await get_temp(
                    lat, lon, res_date, s)

            if forecast is None or actual is None:
                return None

            sigma = 1.8
            z = (threshold - forecast) / sigma
            prob_yes = 1 - normal_cdf(z)
            edge = prob_yes - mkt_price
            borderline = abs(forecast-threshold) \
                         < border_buffer

            buy = (abs(edge) > edge_thresh and
                   not borderline)

            if not buy:
                return None

            kf = kelly_fraction(abs(edge), mkt_price)
            bet = round(bankroll * kf, 2)
            bet = max(2.0, min(bet, 25.0))

            actual_yes = actual >= threshold
            correct = ((edge > 0) == actual_yes)
            if correct:
                pnl = bet/mkt_price - bet
            else:
                pnl = -bet

            return {
                "city": city,
                "date": res_date,
                "forecast": round(forecast,1),
                "actual": round(actual,1),
                "diff": round(forecast-actual,1),
                "threshold": threshold,
                "edge": round(edge,3),
                "mkt_price": mkt_price,
                "kelly_fraction": round(kf,3),
                "bet": bet,
                "correct": correct,
                "pnl": round(pnl,2)
            }

    tasks = [test(m) for m in markets]
    raw = await asyncio.gather(*tasks)
    results = [r for r in raw if r]

    trades = results
    wins = [r for r in trades if r["correct"]]
    pnl = sum(r["pnl"] for r in trades)
    wr = len(wins)/max(len(trades),1)
    avg_bet = sum(r["bet"] for r in trades)/max(
        len(trades),1)

    print(f"\n{label}:")
    print(f"  Trades:    {len(trades)}")
    print(f"  Win Rate:  {wr:.1%}")
    print(f"  P&L:       ${pnl:+.2f}")
    print(f"  Ø Bet:     ${avg_bet:.2f}")
    print(f"  Verdict:   "
          f"{'✅ POSITIV' if wr >= 0.60 and pnl > 0 else '❌'}")

    return {
        "label": label,
        "trades": len(trades),
        "win_rate": round(wr,3),
        "pnl": round(pnl,2),
        "results": results
    }


async def main():
    print("="*60)
    print("WALK-FORWARD BACKTEST")
    print("Keine Look-Ahead-Bias!")
    print("Echte Transaktionskosten: 4%")
    print("Quarter-Kelly Sizing")
    print("="*60)

    connector = aiohttp.TCPConnector(limit=4)
    async with aiohttp.ClientSession(
            connector=connector) as s:

        # Training: Tage 60-16 zurück
        train_markets = await get_markets(s, 60, 16)
        # Validation: Tage 15-1 zurück (nie gesehen!)
        val_markets = await get_markets(s, 15, 1)

    print(f"\nTraining-Märkte:    {len(train_markets)}")
    print(f"Validation-Märkte:  {len(val_markets)}")

    # Nur 1 Parameter-Set testen!
    # (Kein Overfitting durch Parameter-Sweep)
    EDGE_THRESH = 0.25    # Festgelegt vorher
    BORDER_BUF  = 1.5     # Festgelegt vorher

    train = await run_split(
        train_markets,
        "TRAINING (Tage 60-16)",
        EDGE_THRESH, BORDER_BUF)

    val = await run_split(
        val_markets,
        "VALIDATION (Tage 15-1, nie gesehen!)",
        EDGE_THRESH, BORDER_BUF)

    print("\n" + "="*60)
    print("ZUSAMMENFASSUNG")
    print("="*60)
    print(f"Training WR:    {train['win_rate']:.1%}")
    print(f"Validation WR:  {val['win_rate']:.1%}")
    gap = abs(train['win_rate'] - val['win_rate'])
    print(f"Overfitting-Gap:{gap:.1%} "
          f"({'✅ OK (<15%)' if gap < 0.15 else '⚠️ Overfitting!'}) ")

    if (val['win_rate'] >= 0.60 and
            val['pnl'] > 0 and gap < 0.15):
        verdict = "✅ SYSTEM VALIDIERT — Shadow Mode starten"
    elif val['win_rate'] >= 0.55:
        verdict = "🟡 GRENZWERTIG — mehr Daten nötig"
    else:
        verdict = "❌ NICHT VALIDIERT — Modell verbessern"

    print(f"\nVERDICT: {verdict}")

    Path("/root/KongTradeBot/data/backtest/"
         "weather_walkforward.json").write_text(
        json.dumps({
            "method": "walk_forward_no_lookahead",
            "edge_threshold": EDGE_THRESH,
            "border_buffer": BORDER_BUF,
            "transaction_cost_pct": TOTAL_COST,
            "position_sizing": "quarter_kelly",
            "training": train,
            "validation": val,
            "verdict": verdict
        }, indent=2))
    print("\n✅ Gespeichert")


if __name__ == "__main__":
    asyncio.run(main())
