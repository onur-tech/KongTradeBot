"""
Weather Scout v2 — Dynamisches Polymarket-basiertes Wetter-Trading.
Lädt alle aktiven Temperatur-Märkte, geocodiert Städte und prüft Edge
via Ensemble-Forecast (OpenMeteo GFS + ECMWF + MET Norway + Pirate Weather).
"""
import re
import asyncio
import os
import json
import math
import requests
import aiohttp
from datetime import datetime, date
from pathlib import Path
import logging
from core import hrrr_forecast

logger = logging.getLogger("polymarket_bot.weather_scout")

# Minimum confidence for near-threshold cases
MIN_EDGE_PCT = 0.40

# Geocoding-Cache: city_name → (lat, lon)
_coord_cache: dict = {}

# Station config with sigma overrides
_STATIONS_FILE = Path("/root/KongTradeBot/data/polymarket_stations.json")
try:
    _STATIONS: dict = json.loads(_STATIONS_FILE.read_text())
except Exception:
    _STATIONS = {}


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))


def check_metar_lock(icao: str, threshold: float, direction: str) -> dict:
    """
    Prüft ob der aktuelle Tages-Maximalwert aus METAR-Beobachtungen
    eine Markt-Richtung mit hoher Konfidenz bestätigt.

    Nur nach 13:00 UTC sinnvoll (Tageshöchstwert weitgehend bekannt).
    Returns: {"lock": bool, "confidence": float, "observed_max": float, "reason": str}
    """
    import urllib.request as _ureq
    from datetime import datetime as _dt, timezone as _tz
    now_utc = _dt.now(_tz.utc)
    if now_utc.hour < 13:
        return {"lock": False, "reason": "too_early"}
    if not icao:
        return {"lock": False, "reason": "no_icao"}
    url = (f"https://aviationweather.gov/api/data/metar"
           f"?ids={icao}&format=json&hours=12")
    try:
        with _ureq.urlopen(url, timeout=5) as r:
            data = json.loads(r.read())
    except Exception as e:
        return {"lock": False, "reason": str(e)}
    if not data:
        return {"lock": False, "reason": "no_data"}
    temps = [float(o["tmpC"]) for o in data if o.get("tmpC") is not None]
    if not temps:
        return {"lock": False, "reason": "no_temps"}
    observed_max = max(temps)
    if direction == "over" and observed_max >= threshold:
        return {"lock": True, "confidence": 0.88,
                "observed_max": observed_max, "reason": "observed_above"}
    elif direction == "under" and observed_max < threshold:
        return {"lock": True, "confidence": 0.88,
                "observed_max": observed_max, "reason": "observed_below"}
    return {"lock": False, "observed_max": observed_max, "reason": "not_confirmed"}


def bucket_prob(forecast: float, threshold: float, sigma: float) -> float:
    """P(threshold-0.5 < T <= threshold+0.5) under N(forecast, sigma)."""
    lo = (threshold - 0.5 - forecast) / sigma
    hi = (threshold + 0.5 - forecast) / sigma
    return max(0.0, _norm_cdf(hi) - _norm_cdf(lo))

CALIBRATED_CITIES = [
    "Ankara",
    "Atlanta",
    "Austin",
    "Bangkok",
    "Beijing",
    "Berlin",
    "Busan",
    "Chicago",
    "Dallas",
    "Denver",
    "Dubai",
    "Helsinki",
    "Hong Kong",
    "Istanbul",
    "London",
    "Madrid",
    "Miami",
    "Milan",
    "Moscow",
    "Mumbai",
    "NYC",
    "New York",
    "Paris",
    "Seattle",
    "Seoul",
    "Shanghai",
    "Singapore",
    "Sydney",
    "Taipei",
    "Tokyo",
    "Toronto",
    "Warsaw"
]

WEATHER_KEYWORDS = [
    'temperature', 'highest temp', '°f', '°c', 'fahrenheit', 'celsius'
]

_CITY_PATTERN = re.compile(
    r'highest temperature in ([A-Za-z\u00C0-\u017E\s\-]+?)\s+'
    r'(?:be|on|exceed|reach|above|below)',
    re.IGNORECASE
)

_DATE_PATTERN = re.compile(
    r'on\s+(January|February|March|April|May|June|July|August|'
    r'September|October|November|December)\s+(\d{1,2})',
    re.IGNORECASE
)

_MONTH_MAP = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'may': 5, 'june': 6, 'july': 7, 'august': 8,
    'september': 9, 'october': 10, 'november': 11, 'december': 12
}

WU_API_KEY = os.getenv("WU_API_KEY", "6532d6454b8aa370768e63d6ba5a832e")

_WU_STATION_RE = re.compile(
    r'wunderground\.com/history/daily/([a-z]{2})/[^/]+/([A-Z0-9]+)',
    re.IGNORECASE
)


def _parse_wu_station(resolution_source: str) -> tuple:
    """Gibt (station_code, country_code) aus WU-URL zurück."""
    m = _WU_STATION_RE.search(resolution_source or "")
    if m:
        return m.group(2), m.group(1).upper()
    return "", ""


def get_wu_forecast_max(station: str, country: str, target_date) -> float | None:
    """
    Holt stündlichen WU-Forecast für eine Station und berechnet Tages-Maximum.
    Nutzt 48h-Forecast (reicht für Märkte bis übermorgen).
    """
    if not station or not WU_API_KEY:
        return None
    try:
        url = (
            f"https://api.weather.com/v1/location/{station}:9:{country}"
            f"/forecast/hourly/48hour.json?apiKey={WU_API_KEY}&units=m"
        )
        r = requests.get(url, timeout=8, headers={"User-Agent": "KongTradeBot/1.0"})
        if not r.ok:
            return None
        forecasts = r.json().get("forecasts", [])
        target_str = target_date.strftime("%Y-%m-%d") if target_date else None
        temps = []
        for fc in forecasts:
            ts = fc.get("fcst_valid", 0)
            if not ts:
                continue
            fc_date = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
            if target_str and fc_date != target_str:
                continue
            t = fc.get("temp")
            if t is not None:
                temps.append(float(t))
        return round(max(temps), 1) if temps else None
    except Exception as e:
        logger.debug(f"[WeatherScout] WU station {station}: {e}")
        return None


def get_all_polymarket_weather_markets() -> list:
    """Lädt ALLE aktiven Temperatur-Märkte von Polymarket (paginiert)."""
    all_markets = []
    for offset in range(0, 500, 50):
        try:
            r = requests.get(
                'https://gamma-api.polymarket.com/markets',
                params={
                    'limit': 50, 'closed': 'false',
                    'offset': offset, 'order': 'volume', 'ascending': 'false',
                },
                timeout=15,
            )
            if not r.ok:
                break
            batch = r.json()
            if isinstance(batch, dict):
                batch = batch.get('markets', [])
            if not batch:
                break
            all_markets.extend(batch)
        except Exception as e:
            logger.warning(f"[WeatherScout] API-Fehler (offset={offset}): {e}")
            break

    results = []
    for m in all_markets:
        q = m.get('question', '')
        if not any(k in q.lower() for k in WEATHER_KEYWORDS):
            continue

        city_match = _CITY_PATTERN.search(q)
        if not city_match:
            continue
        city = city_match.group(1).strip()

        # Zieldatum aus Frage extrahieren
        target_date = None
        date_match = _DATE_PATTERN.search(q)
        if date_match:
            month = _MONTH_MAP.get(date_match.group(1).lower(), 0)
            day = int(date_match.group(2))
            if month:
                try:
                    target_date = date(datetime.now().year, month, day)
                except ValueError:
                    pass

        unit = 'F' if ('°f' in q.lower() or 'fahrenheit' in q.lower()) else 'C'

        # YES-Preis ermitteln
        outcome_prices = m.get('outcomePrices', [])
        yes_price = None
        try:
            yes_price = float(outcome_prices[0]) if outcome_prices else None
        except (ValueError, TypeError):
            pass
        if yes_price is None:
            yes_price = float(m.get('lastTradePrice', 0) or 0) or None
        if not yes_price or yes_price <= 0.001 or yes_price >= 0.999:
            continue

        volume = float(m.get('volume', 0) or 0)
        if volume < 100:
            continue

        rs = m.get('resolutionSource', '')
        wu_station, wu_country = _parse_wu_station(rs)

        _raw_tids = m.get('clobTokenIds', [])
        if isinstance(_raw_tids, str):
            try:
                import json as _j; _raw_tids = _j.loads(_raw_tids)
            except Exception:
                _raw_tids = []
        results.append({
            'question':      q,
            'city':          city,
            'unit':          unit,
            'condition_id':  m.get('conditionId', ''),
            'yes_price':     round(yes_price, 4),
            'no_price':      round(1 - yes_price, 4),
            'volume':        volume,
            'target_date':   target_date,
            'end_date':      (m.get('endDate') or '')[:10],
            'wu_station':    wu_station,
            'wu_country':    wu_country,
            'resolution_source': rs,
            'token_ids':     _raw_tids,
        })

    results.sort(key=lambda x: x['volume'], reverse=True)
    logger.info(f"[WeatherScout] {len(results)} aktive Temperatur-Märkte gefunden")
    return results


def get_coordinates(city: str) -> tuple:
    """Koordinaten via Nominatim (OpenStreetMap). Ergebnis wird gecacht."""
    if city in _coord_cache:
        return _coord_cache[city]
    try:
        r = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={'q': city, 'format': 'json', 'limit': 1},
            headers={'User-Agent': 'KongTradeBot/1.0'},
            timeout=6,
        )
        if r.ok:
            data = r.json()
            if data:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                _coord_cache[city] = (lat, lon)
                return lat, lon
    except Exception as e:
        logger.warning(f"[WeatherScout] Geocoding '{city}': {e}")
    _coord_cache[city] = (None, None)
    return None, None


async def get_ensemble_forecast(lat: float, lon: float,
                                target_date=None) -> tuple:
    """
    Async Ensemble-Forecast: 4 Quellen parallel.
    - OpenMeteo GFS (best_match)
    - OpenMeteo ECMWF (ecmwf_ifs025)
    - MET Norway
    - Pirate Weather (optional, braucht PIRATE_WEATHER_KEY in .env)
    Gibt (avg_temp_celsius, ensemble_confidence) zurück.
    """
    target_str = target_date.strftime('%Y-%m-%d') if target_date else None

    async def _openmeteo(model: str):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": lat, "longitude": lon,
                        "daily": "temperature_2m_max",
                        "forecast_days": 7,
                        "timezone": "auto",
                        "models": model,
                    },
                    timeout=aiohttp.ClientTimeout(total=8),
                ) as r:
                    data = await r.json()
            dates = data.get("daily", {}).get("time", [])
            temps = data.get("daily", {}).get("temperature_2m_max", [])
            if target_str:
                for d, t in zip(dates, temps):
                    if d == target_str and t is not None:
                        return round(float(t), 1), f"OpenMeteo/{model}"
            if len(temps) > 1 and temps[1] is not None:
                return round(float(temps[1]), 1), f"OpenMeteo/{model}"
        except Exception as e:
            logger.debug(f"[WeatherScout] OpenMeteo/{model}: {e}")
        return None, None

    async def _met_norway():
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    f"https://api.met.no/weatherapi/locationforecast/2.0/compact"
                    f"?lat={round(lat, 2)}&lon={round(lon, 2)}",
                    headers={"User-Agent": "KongTradeBot/1.0"},
                    timeout=aiohttp.ClientTimeout(total=8),
                ) as r:
                    data = await r.json()
            timeseries = data.get("properties", {}).get("timeseries", [])
            day_temps = []
            for ts in timeseries:
                if target_str and ts.get("time", "")[:10] != target_str:
                    continue
                temp = (ts.get("data", {})
                          .get("instant", {})
                          .get("details", {})
                          .get("air_temperature"))
                if temp is not None:
                    day_temps.append(float(temp))
            if day_temps:
                return round(max(day_temps), 1), "MET Norway"
        except Exception as e:
            logger.debug(f"[WeatherScout] MET Norway ({lat},{lon}): {e}")
        return None, None

    async def _pirate_weather():
        key = os.getenv("PIRATE_WEATHER_KEY", "")
        if not key:
            return None, None
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    f"https://api.pirateweather.net/forecast/{key}/{lat},{lon}",
                    params={"units": "si", "exclude": "hourly,minutely,alerts"},
                    timeout=aiohttp.ClientTimeout(total=8),
                ) as r:
                    data = await r.json()
            t = data.get("daily", {}).get("data", [{}])[0].get("temperatureHigh")
            if t is not None:
                return round(float(t), 1), "PirateWeather"
        except Exception as e:
            logger.debug(f"[WeatherScout] PirateWeather: {e}")
        return None, None

    # Alle Quellen parallel abfragen
    results = await asyncio.gather(
        _openmeteo("best_match"),
        _openmeteo("ecmwf_ifs025"),
        _met_norway(),
        _pirate_weather(),
    )

    sources = [(name, t) for t, name in results if t is not None]

    if not sources:
        return None, 0.0

    avg_temp = round(sum(t for _, t in sources) / len(sources), 1)
    n = len(sources)
    spread = (max(t for _, t in sources) - min(t for _, t in sources)
              ) if n >= 2 else 0.0

    if n >= 3 and spread < 1.0:
        conf = 0.95
    elif n >= 2 and spread < 1.5:
        conf = 0.90
    elif n >= 2 and spread < 2.5:
        conf = 0.75
    else:
        conf = 0.55

    logger.info(
        f"[WeatherScout] Ensemble ({n} Quellen): "
        f"{[(s, f'{t:.1f}') for s, t in sources]} → "
        f"{avg_temp:.1f}°C conf={conf:.0%} spread={spread:.1f}°")
    return avg_temp, conf


def get_forecast_for_date(lat: float, lon: float, target_date) -> tuple:
    """Sync-Wrapper um get_ensemble_forecast. Gibt (temp_c, date_str) zurück."""
    try:
        temp_c, _ = asyncio.run(get_ensemble_forecast(lat, lon, target_date))
    except RuntimeError:
        # Fallback falls bereits ein Event-Loop läuft (sollte in to_thread nicht passieren)
        loop = asyncio.new_event_loop()
        try:
            temp_c, _ = loop.run_until_complete(
                get_ensemble_forecast(lat, lon, target_date))
        finally:
            loop.close()
    date_str = target_date.strftime('%Y-%m-%d') if target_date else "tomorrow"
    return temp_c, date_str


def celsius_to_fahrenheit(c: float) -> float:
    return round(c * 9 / 5 + 32, 1)


# negRisk bucket-arb: buy ALL YES when sum < this threshold
ARB_THRESHOLD = 0.97
# Minimum ROI to report as arb (after gas/spread)
ARB_MIN_ROI = 0.02


def scan_bucket_arbitrage() -> list:
    """
    Scannt alle aktiven Wetter-Events auf negRisk Bucket-Arbitrage.

    negRisk-Eigenschaft: genau ein Bucket löst als YES auf → die
    Summe aller YES-Preise sollte $1.00 betragen. Wenn sie <$1.00
    ist, kann man alle Buckets kaufen und risikolos $1.00 erhalten.

    Gibt eine Liste von Arb-Gelegenheiten zurück, sortiert nach ROI.
    Jeder Eintrag: {city, end_date, sum_yes, spread, roi_pct,
                    buckets: [{question, condition_id, token_id,
                               yes_price, threshold_c, unit}]}
    """
    from datetime import date as _date

    today_str = _date.today().isoformat()
    all_events = []

    for offset in range(3200, 3900, 100):
        try:
            r = requests.get(
                "https://gamma-api.polymarket.com/events",
                params={"tag_slug": "weather", "limit": 100,
                        "offset": offset, "order": "end_date_max:desc"},
                timeout=12,
            )
            if not r.ok:
                break
            batch = r.json()
            if isinstance(batch, dict):
                batch = batch.get("events", [])
            if not batch:
                break
            all_events.extend(batch)
        except Exception as e:
            logger.warning(f"[BucketArb] API-Fehler offset={offset}: {e}")
            break

    logger.info(f"[BucketArb] {len(all_events)} Events geladen")

    arb_opportunities = []

    for ev in all_events:
        title = ev.get("title", "")
        if "temperature" not in title.lower():
            continue

        end_str = (ev.get("endDate") or "")[:10]
        if end_str <= today_str:
            continue

        markets = ev.get("markets", [])
        if not markets:
            continue

        city_m = re.search(
            r"temperature in ([A-Za-z\s]+?)(?:\s+on\b|\s+for\b|$)",
            title, re.IGNORECASE)
        city_name = city_m.group(1).strip() if city_m else title[:20]

        buckets = []
        total_yes = 0.0

        for mkt in markets:
            q = mkt.get("question", "")
            prices_raw = mkt.get("outcomePrices", "[]")
            try:
                prices = (json.loads(prices_raw)
                          if isinstance(prices_raw, str) else prices_raw)
                yes_p = float(prices[0]) if prices else 0.5
            except Exception:
                yes_p = 0.5

            cid = mkt.get("conditionId", "")
            token_ids_raw = mkt.get("clobTokenIds", "[]")
            try:
                tids = (json.loads(token_ids_raw)
                        if isinstance(token_ids_raw, str) else token_ids_raw)
                token_id = tids[0] if tids else ""
            except Exception:
                token_id = ""

            unit = "F" if ("°f" in q.lower() or "fahrenheit" in q.lower()) else "C"

            thr, _ = _extract_threshold_and_direction(q)

            vol = float(mkt.get("volume", 0) or 0)
            buckets.append({
                "question":    q,
                "condition_id": cid,
                "token_id":    token_id,
                "yes_price":   round(yes_p, 4),
                "threshold_c": thr,
                "unit":        unit,
                "volume":      vol,
            })
            total_yes += yes_p

        if len(buckets) < 3:
            continue

        spread = 1.0 - total_yes
        if spread <= ARB_MIN_ROI:
            continue

        roi_pct = spread / total_yes * 100

        # Per-bucket model edge using bucket_prob
        sigma = _STATIONS.get(city_name, {}).get("sigma", 1.8)
        lat, lon = get_coordinates(city_name)
        fc_temp = None
        if lat:
            try:
                end_date_obj = _date.fromisoformat(end_str)
                fc_temp, _ = asyncio.run(
                    get_ensemble_forecast(lat, lon, end_date_obj))
            except RuntimeError:
                loop = asyncio.new_event_loop()
                try:
                    end_date_obj = _date.fromisoformat(end_str)
                    fc_temp, _ = loop.run_until_complete(
                        get_ensemble_forecast(lat, lon, end_date_obj))
                finally:
                    loop.close()
            except Exception:
                pass

        for b in buckets:
            if fc_temp is not None and b["threshold_c"] is not None:
                fc_scaled = (celsius_to_fahrenheit(fc_temp)
                             if b["unit"] == "F" else fc_temp)
                b["model_prob"] = round(
                    bucket_prob(fc_scaled, b["threshold_c"], sigma), 4)
                b["model_edge"] = round(b["model_prob"] - b["yes_price"], 4)
            else:
                b["model_prob"] = None
                b["model_edge"] = None

        arb_opportunities.append({
            "city":       city_name,
            "end_date":   end_str,
            "sum_yes":    round(total_yes, 4),
            "spread":     round(spread, 4),
            "roi_pct":    round(roi_pct, 2),
            "n_buckets":  len(buckets),
            "volume":     float(ev.get("volume", 0) or 0),
            "forecast_c": fc_temp,
            "buckets":    buckets,
        })

    arb_opportunities.sort(key=lambda x: x["roi_pct"], reverse=True)
    logger.info(
        f"[BucketArb] {len(arb_opportunities)} Arb-Märkte gefunden "
        f"(threshold={ARB_THRESHOLD:.0%})")
    return arb_opportunities


def _open_bucket_arb_in_shadow(arb: dict):
    """Öffnet virtuelle Shadow-Positionen für alle Buckets eines Arb-Markts."""
    try:
        import sys as _sys
        _sys.path.insert(0, "/root/KongTradeBot")
        from core.shadow_portfolio import ShadowPortfolio
        _sp = ShadowPortfolio()
        city = arb["city"]
        n = arb["n_buckets"]
        # Verteile $25 gleichmäßig auf alle Buckets (min $2 pro Bucket)
        per_bucket = round(max(2.0, min(25.0 / n, 5.0)), 2)
        for b in arb["buckets"]:
            if b["yes_price"] < 0.01:
                continue
            _sp.open_position(
                market_id=b["condition_id"],
                question=b["question"],
                outcome="YES",
                entry_price=b["yes_price"],
                invested_usdc=per_bucket,
                strategy="BUCKET_ARB",
                signal_score=min(100, int(arb["roi_pct"] * 5)),
                city=city,
            )
        logger.info(
            f"[BucketArb] Shadow: {n} Positionen für {city} "
            f"@ ROI={arb['roi_pct']:.1f}%")
    except Exception as e:
        logger.warning(f"[BucketArb] Shadow Fehler: {e}")


def _extract_threshold_and_direction(question: str) -> tuple:
    """
    Extrahiert (threshold, direction) aus Markt-Frage.
    direction: 'above' | 'below' | 'equal'
    """
    q = question.lower()

    for p in [
        r'(\d+(?:\.\d+)?)\s*°[fc]?\s*or\s+higher',
        r'(\d+(?:\.\d+)?)\s*°[fc]?\s*or\s+above',
        r'exceed\s+(\d+(?:\.\d+)?)',
        r'above\s+(\d+(?:\.\d+)?)',
    ]:
        m = re.search(p, q)
        if m:
            return float(m.group(1)), 'above'

    for p in [
        r'(\d+(?:\.\d+)?)\s*°[fc]?\s*or\s+lower',
        r'(\d+(?:\.\d+)?)\s*°[fc]?\s*or\s+below',
        r'below\s+(\d+(?:\.\d+)?)',
    ]:
        m = re.search(p, q)
        if m:
            return float(m.group(1)), 'below'

    m = re.search(r'between\s+(\d+(?:\.\d+)?)[-\u2013](\d+(?:\.\d+)?)', q)
    if m:
        return (float(m.group(1)) + float(m.group(2))) / 2, 'equal'

    for p in [r'be\s+(\d+(?:\.\d+)?)\s*°', r'(\d+(?:\.\d+)?)\s*°']:
        m = re.search(p, q)
        if m:
            return float(m.group(1)), 'equal'

    return None, None


def run_weather_scout() -> list:
    """Haupt-Scouting-Funktion — dynamisch aus Polymarket-Märkten."""
    logger.info("[WeatherScout] Starte dynamischen Weather Market Scan v2...")

    # ── Phase 1: negRisk Bucket-Arbitrage ──────────────────────────────
    arb_opps = scan_bucket_arbitrage()
    all_opportunities = []

    for arb in arb_opps:
        roi = arb["roi_pct"]
        city = arb["city"]
        logger.info(
            f"[BucketArb] ✅ {city} {arb['end_date']} "
            f"sum={arb['sum_yes']:.4f} ROI={roi:.2f}% "
            f"vol=${arb['volume']/1000:.0f}k")
        # Risikofreier Arb → alle Buckets kaufen (Shadow Portfolio)
        _open_bucket_arb_in_shadow(arb)
        # Beste Einzel-Buckets nach Modell-Edge melden
        for b in arb["buckets"]:
            edge = b.get("model_edge") or 0
            if edge > 0.07 and b["yes_price"] >= 0.05:
                all_opportunities.append({
                    "market":      b["question"],
                    "condition_id": b["condition_id"],
                    "city":        city,
                    "price":       b["yes_price"],
                    "direction":   "YES",
                    "edge":        round(edge, 4),
                    "confidence":  b.get("model_prob", 0),
                    "volume":      b["volume"],
                    "forecast_temp": arb.get("forecast_c"),
                    "threshold":   b["threshold_c"],
                    "unit":        b["unit"],
                    "end_date":    arb["end_date"],
                    "strategy":    "BUCKET_ARB",
                    "arb_roi":     roi,
                })

    # ── Phase 2: Einzel-Markt Scouting (bestehende Logik) ──────────────
    markets = get_all_polymarket_weather_markets()
    # city → {'lat', 'lon', 'forecasts': {date_key: temp_c}}
    city_cache: dict = {}
    if not markets:
        all_opportunities.sort(key=lambda x: x['edge'], reverse=True)
        logger.info(f"[WeatherScout] Total: {len(all_opportunities)} Opportunities (nur Arb)")
        return all_opportunities

    for m in markets:
        city       = m['city']
        unit       = m['unit']
        yes_price  = m['yes_price']
        no_price   = m['no_price']
        target_date = m.get('target_date')
        question   = m['question']

        threshold, direction = _extract_threshold_and_direction(question)
        if threshold is None:
            continue

        # Koordinaten mit Cache
        if city not in city_cache:
            lat, lon = get_coordinates(city)
            city_cache[city] = {'lat': lat, 'lon': lon, 'forecasts': {}}
        cd = city_cache[city]
        lat, lon = cd['lat'], cd['lon']
        if not lat:
            continue

        # Ensemble-Forecast mit Date-Cache
        date_key = target_date.isoformat() if target_date else 'tomorrow'
        if date_key not in cd['forecasts']:
            try:
                temp_c, ens_conf = asyncio.run(
                    get_ensemble_forecast(lat, lon, target_date))
            except RuntimeError:
                loop = asyncio.new_event_loop()
                try:
                    temp_c, ens_conf = loop.run_until_complete(
                        get_ensemble_forecast(lat, lon, target_date))
                finally:
                    loop.close()

            # WU-Station als primäre Auflösungsquelle einbeziehen
            wu_station = m.get('wu_station', '')
            wu_country = m.get('wu_country', '')
            if wu_station:
                wu_temp = get_wu_forecast_max(wu_station, wu_country, target_date)
                if wu_temp is not None and temp_c is not None:
                    # WU bekommt doppeltes Gewicht (= tatsächliche Auflösungsquelle)
                    temp_c = round((temp_c + wu_temp * 2) / 3, 1)
                    logger.info(
                        f"[WeatherScout] WU {wu_station}: {wu_temp}°C "
                        f"→ gewichteter Ensemble: {temp_c}°C")
                elif wu_temp is not None:
                    temp_c = wu_temp

            cd['forecasts'][date_key] = (temp_c, ens_conf)
        temp_c, ens_conf = cd['forecasts'][date_key]
        if temp_c is None:
            continue

        # Multi-Model-Gate: mind. 75% Ensemble-Konsens erforderlich
        _min_conf = float(os.getenv("WEATHER_MIN_ENSEMBLE_CONF", "0.75"))
        if ens_conf < _min_conf:
            logger.info(
                f"[WeatherScout] SKIP Multi-Model: {city} "
                f"conf={ens_conf:.0%} < {_min_conf:.0%} — GFS/ECMWF/MET uneinig")
            continue

        forecast_temp = celsius_to_fahrenheit(temp_c) if unit == 'F' else temp_c

        # HRRR Konsens-Check für US-Städte (3km Auflösung, 0-18h Edge)
        if city in hrrr_forecast.HRRR_US_CITIES:
            consensus = hrrr_forecast.hrrr_vs_openmeteo_consensus(
                city=city,
                openmeteo_forecast=forecast_temp,
                threshold=threshold,
                unit=unit
            )
            if not consensus["consensus"]:
                logger.info(
                    f"[WeatherScout] SKIP {city}: "
                    f"HRRR/OpenMeteo kein Konsens "
                    f"(HRRR={consensus['hrrr']:.1f} "
                    f"vs OM={consensus['openmeteo']:.1f})"
                )
                continue

        logger.info(
            f"[WeatherScout] {city}: Forecast {forecast_temp:.1f}°{unit} "
            f"vs {threshold:.1f}° ({direction}) | "
            f"YES={yes_price:.2f} NO={no_price:.2f} | {question[:55]}")

        temp_diff = abs(forecast_temp - threshold)
        if temp_diff < 1.0:
            threshold_conf = MIN_EDGE_PCT
        elif temp_diff < 3.0:
            threshold_conf = 0.65
        elif temp_diff < 5.0:
            threshold_conf = 0.80
        else:
            threshold_conf = 0.90
        # Ensemble-Konfidenz als Obergrenze: schlechte Quellen-Übereinstimmung → weniger aggressiv
        confidence = min(threshold_conf, ens_conf) if ens_conf > 0 else threshold_conf

        opp = None

        if direction == 'above':
            if forecast_temp >= threshold and yes_price < confidence:
                edge = confidence - yes_price
                if edge > 0.07:
                    opp = {'direction': 'YES', 'price': yes_price, 'edge': edge}
            elif forecast_temp < threshold and no_price < confidence:
                edge = confidence - no_price
                if edge > 0.07:
                    opp = {'direction': 'NO', 'price': no_price, 'edge': edge}

        elif direction == 'below':
            if forecast_temp <= threshold and yes_price < confidence:
                edge = confidence - yes_price
                if edge > 0.07:
                    opp = {'direction': 'YES', 'price': yes_price, 'edge': edge}
            elif forecast_temp > threshold and no_price < confidence:
                edge = confidence - no_price
                if edge > 0.07:
                    opp = {'direction': 'NO', 'price': no_price, 'edge': edge}

        elif direction == 'equal':
            # negRisk bucket: P(threshold-0.5 < T <= threshold+0.5)
            sigma = _STATIONS.get(city, {}).get("sigma", 1.8)
            # threshold is already in unit's scale; convert forecast to same
            p_yes = bucket_prob(forecast_temp, threshold, sigma)
            p_no = 1.0 - p_yes
            if p_yes > yes_price and (p_yes - yes_price) > 0.07:
                edge = p_yes - yes_price
                opp = {'direction': 'YES', 'price': yes_price, 'edge': edge}
            elif p_no > no_price and (p_no - no_price) > 0.07:
                edge = p_no - no_price
                opp = {'direction': 'NO', 'price': no_price, 'edge': edge}

        if opp:
            _tids = m.get('token_ids', [])
            _token_id = _tids[0] if opp['direction'] == 'YES' and _tids else (_tids[1] if len(_tids) > 1 else '')
            all_opportunities.append({
                'market':     question,
                'condition_id': m['condition_id'],
                'city':       city,
                'price':      opp['price'],
                'direction':  opp['direction'],
                'edge':       opp['edge'],
                'confidence': confidence,
                'volume':     m['volume'],
                'forecast_temp': forecast_temp,
                'threshold':  threshold,
                'unit':       unit,
                'end_date':   m['end_date'],
                'token_id':   _token_id,
                'shadow_only': city not in CALIBRATED_CITIES,
            })
            logger.info(
                f"[WeatherScout] ✅ Opportunity: {opp['direction']} {city} "
                f"Forecast {forecast_temp:.1f}°{unit} Edge {opp['edge']:.0%} | "
                f"{question[:55]}")
            # Cities without verified sigma → shadow mode only (no live CLOB trade)
            shadow_only = city not in CALIBRATED_CITIES
            if shadow_only:
                logger.info(f"[WeatherScout] SHADOW-ONLY: {city} nicht kalibriert, kein echter Trade")
            # Skip penny markets — no CLOB liquidity
            if opp['price'] < 0.05:
                logger.debug(f"[WeatherScout] Penny skip: {city} {opp['price']:.3f}")
            else:
                # METAR Lock — Beobachteter Tageswert als Confirmation Signal
                _metar_lock = False
                _effective_edge = abs(opp['edge'])
                _bet_multiplier = 1.0
                _icao = _STATIONS.get(city, {}).get("icao", "")
                if _icao and not shadow_only:
                    _metar_dir = "over" if opp['direction'] == "YES" and direction == "above" else \
                                 "under" if opp['direction'] == "YES" and direction == "below" else \
                                 "under" if opp['direction'] == "NO" and direction == "above" else \
                                 "over"
                    _lock_result = check_metar_lock(_icao, threshold, _metar_dir)
                    if _lock_result.get("lock"):
                        _metar_lock = True
                        _effective_edge = max(_effective_edge, 0.88)
                        _bet_multiplier = 2.0
                        logger.info(
                            f"[METAR LOCK] {city} ({_icao}) "
                            f"obs_max={_lock_result.get('observed_max', '?')}°C "
                            f"→ 88% conf, 2× size")

                # Shadow Portfolio — Quarter-Kelly sizing
                try:
                    import sys as _sys
                    _sys.path.insert(0, '/root/KongTradeBot')
                    from core.shadow_portfolio import ShadowPortfolio
                    _sp = ShadowPortfolio()
                    _mkt_price = opp['price']
                    _edge = _effective_edge
                    # Quarter-Kelly: f = edge/(1-p) * 0.25, cap 10%
                    _kf = min((_edge / max(1 - _mkt_price, 0.01)) * 0.25, 0.10) if _edge > 0 else 0
                    _bankroll = _sp.data.get("current_capital", 999_999.0)
                    _bet = round(max(2.0, min(_bankroll * _kf, 25.0)) * _bet_multiplier, 2)
                    _score = round(min(100, int(_edge * 200)))
                    if _metar_lock:
                        _score = max(_score, 88)
                    _sp.open_position(
                        market_id=m['condition_id'],
                        question=m.get('question', city),
                        outcome=opp['direction'],
                        entry_price=_mkt_price,
                        invested_usdc=_bet,
                        strategy="WEATHER" if not _metar_lock else "WEATHER_METAR",
                        signal_score=_score,
                        city=city,
                        end_date=m.get('end_date', ''),
                    )
                except Exception as _e:
                    logger.warning(f"[WeatherScout] Shadow Portfolio Fehler: {_e}")

    all_opportunities.sort(key=lambda x: x['edge'], reverse=True)
    logger.info(f"[WeatherScout] Total: {len(all_opportunities)} Opportunities gefunden")
    return all_opportunities


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)-8s %(message)s")
    if '--markets-only' in sys.argv:
        markets = get_all_polymarket_weather_markets()
        print(f"\nGefunden: {len(markets)} Märkte")
        for m in markets[:15]:
            print(f"  {m['city']:20s} | Vol: ${m['volume']:8.0f} | {m['question'][:65]}")
    else:
        opps = run_weather_scout()
        print(f"\n=== Top Weather Opportunities ({len(opps)}) ===")
        for o in opps[:10]:
            print(
                f"  {o['direction']:3s} {o['city']:15s} "
                f"{o['forecast_temp']:.1f}°{o['unit']} vs {o['threshold']:.1f}° "
                f"Edge {o['edge']:.0%}  Price {o['price']:.2f}  "
                f"Vol ${o['volume']:.0f}")
        if not opps:
            print("  (Keine Opportunities — Preise bereits korrekt eingepreist)")
