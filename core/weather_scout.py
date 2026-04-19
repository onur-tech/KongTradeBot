"""
Weather Scout — Findet profitable Weather-Market Opportunities.
Vergleicht OpenMeteo Forecast mit Polymarket Preisen.
Strategie: Temperature Laddering (neobrother-Style)
"""
import requests
import json
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Städte mit Koordinaten und Polymarket-Namen
CITIES = {
    "New York": {
        "lat": 40.71, "lon": -74.01,
        "timezone": "America/New_York",
        "unit": "F",  # Fahrenheit für US
        "polymarket_name": "New York"
    },
    "Chicago": {
        "lat": 41.88, "lon": -87.63,
        "timezone": "America/Chicago",
        "unit": "F",
        "polymarket_name": "Chicago"
    },
    "London": {
        "lat": 51.51, "lon": -0.13,
        "timezone": "Europe/London",
        "unit": "C",
        "polymarket_name": "London"
    },
    "Berlin": {
        "lat": 52.52, "lon": 13.41,
        "timezone": "Europe/Berlin",
        "unit": "C",
        "polymarket_name": "Berlin"
    },
    "Helsinki": {
        "lat": 60.17, "lon": 24.94,
        "timezone": "Europe/Helsinki",
        "unit": "C",
        "polymarket_name": "Helsinki"
    },
    "Istanbul": {
        "lat": 41.01, "lon": 28.95,
        "timezone": "Europe/Istanbul",
        "unit": "C",
        "polymarket_name": "Istanbul"
    },
    "Beijing": {
        "lat": 39.91, "lon": 116.39,
        "timezone": "Asia/Shanghai",
        "unit": "C",
        "polymarket_name": "Beijing"
    },
    "Cape Town": {
        "lat": -33.93, "lon": 18.42,
        "timezone": "Africa/Johannesburg",
        "unit": "C",
        "polymarket_name": "Cape Town"
    },
    "Tokyo": {
        "lat": 35.69, "lon": 139.69,
        "timezone": "Asia/Tokyo",
        "unit": "C",
        "polymarket_name": "Tokyo"
    }
}


def get_forecast(lat: float, lon: float,
                 timezone: str) -> dict:
    """Holt OpenMeteo Forecast für Koordinaten."""
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min"
        f"&timezone={timezone}"
        f"&forecast_days=3"
    )
    r = requests.get(url, timeout=10)
    return r.json() if r.ok else {}


def celsius_to_fahrenheit(c: float) -> float:
    return round(c * 9/5 + 32, 1)


def find_weather_markets() -> list:
    """Findet aktive Weather-Märkte auf Polymarket."""
    try:
        # Breite Suche um alle Temperatur-Märkte zu erfassen
        r = requests.get(
            "https://gamma-api.polymarket.com/markets?"
            "limit=200&closed=false&order=volume&ascending=false",
            timeout=15)
        markets = r.json() if r.ok else []
        if isinstance(markets, dict):
            markets = markets.get('markets', [])
        weather_kw = [
            'temperature', 'degrees', 'fahrenheit', 'celsius',
            'rainfall', 'precip', 'snow', '°f', '°c',
            'weather', 'forecast', 'highest temperature'
        ]
        return [m for m in markets
                if any(k in m.get('question', '').lower()
                       for k in weather_kw)]
    except Exception as e:
        logger.error(f"Weather market search error: {e}")
        return []


def analyze_opportunity(city_name: str, forecast_temp: float,
                         unit: str,
                         markets: list) -> list:
    """
    Findet Märkte wo unser Forecast den Preis schlägt.
    Temperature Laddering: kaufe +/- 2°C Rungs um Forecast.
    """
    opportunities = []
    city_lower = city_name.lower()

    for m in markets:
        q = m.get('question', '')
        q_lower = q.lower()
        if city_lower not in q_lower:
            continue

        # Markt-Preis aus letztem Trade oder best bid
        price = float(m.get('lastTradePrice', 0) or 0)
        if price <= 0:
            # Versuche outcomePrices
            outcome_prices = m.get('outcomePrices', [])
            if outcome_prices:
                try:
                    price = float(outcome_prices[0])
                except (ValueError, TypeError):
                    pass
        if price <= 0 or price >= 0.95:
            continue

        volume = float(m.get('volume', 0) or 0)
        if volume < 500:  # Mindest-Liquidität $500
            continue

        # Extrahiere Temperatur-Schwelle aus Markt-Frage
        threshold = _extract_temp_threshold(q, unit)
        if threshold is None:
            continue

        # Edge-Berechnung: wie sicher ist unser Forecast?
        temp_diff = abs(forecast_temp - threshold)
        if temp_diff < 1.0:
            confidence = 0.5  # Zu nah an Schwelle
        elif temp_diff < 3.0:
            confidence = 0.65
        elif temp_diff < 5.0:
            confidence = 0.80
        else:
            confidence = 0.90

        # Kaufen wenn unser Forecast stark YES oder NO deutet
        above_threshold = forecast_temp >= threshold
        if above_threshold and price < confidence:
            edge = confidence - price
            if edge > 0.10:  # Mindest-Edge 10%
                opportunities.append({
                    'market': q,
                    'condition_id': m.get('conditionId', ''),
                    'price': price,
                    'volume': volume,
                    'forecast_temp': forecast_temp,
                    'threshold': threshold,
                    'unit': unit,
                    'direction': 'YES',
                    'confidence': confidence,
                    'edge': edge,
                    'city': city_name,
                    'end_date': m.get('endDate', '')[:10]
                })
        elif not above_threshold and price > (1 - confidence):
            # Kaufe NO wenn Forecast klar unter Schwelle
            no_price = 1 - price
            edge = confidence - no_price
            if edge > 0.10:
                opportunities.append({
                    'market': q,
                    'condition_id': m.get('conditionId', ''),
                    'price': no_price,  # NO-Preis
                    'volume': volume,
                    'forecast_temp': forecast_temp,
                    'threshold': threshold,
                    'unit': unit,
                    'direction': 'NO',
                    'confidence': confidence,
                    'edge': edge,
                    'city': city_name,
                    'end_date': m.get('endDate', '')[:10]
                })

    return sorted(opportunities, key=lambda x: x['edge'], reverse=True)


def _extract_temp_threshold(question: str, unit: str) -> float | None:
    """Extrahiert Temperatur-Schwelle aus Markt-Frage."""
    import re
    q = question.lower()

    # Pattern: "be 10°C", "be between 50-51°F", "exceed 23°C", "above 20°C"
    patterns = [
        r'be\s+between\s+(\d+)[-–](\d+)',  # "between 50-51°F"
        r'be\s+(\d+(?:\.\d+)?)\s*°',        # "be 10°C"
        r'exceed\s+(\d+(?:\.\d+)?)',         # "exceed 23°C"
        r'above\s+(\d+(?:\.\d+)?)',          # "above 20°C"
        r'below\s+(\d+(?:\.\d+)?)',          # "below 15°C"
        r'(\d+(?:\.\d+)?)\s*°',             # "23°C" anywhere
    ]

    for pattern in patterns:
        m = re.search(pattern, q)
        if m:
            groups = m.groups()
            if len(groups) == 2:  # Range: take midpoint
                return (float(groups[0]) + float(groups[1])) / 2
            return float(groups[0])

    return None


def run_weather_scout() -> list:
    """Haupt-Scouting-Funktion."""
    logger.info("[WeatherScout] Starte Weather Market Scan...")
    markets = find_weather_markets()
    logger.info(f"[WeatherScout] {len(markets)} Weather-Märkte gefunden")

    all_opportunities = []

    for city, config in CITIES.items():
        forecast = get_forecast(
            config['lat'], config['lon'],
            config['timezone'])

        daily = forecast.get('daily', {})
        temps_c = daily.get('temperature_2m_max', [])

        if not temps_c:
            continue

        # Morgen Forecast (Index 1), heute (Index 0)
        tomorrow_c = temps_c[1] if len(temps_c) > 1 else temps_c[0]
        today_c = temps_c[0]

        if config['unit'] == 'F':
            forecast_temp = celsius_to_fahrenheit(tomorrow_c)
            today_temp = celsius_to_fahrenheit(today_c)
        else:
            forecast_temp = round(tomorrow_c, 1)
            today_temp = round(today_c, 1)

        logger.info(
            f"[WeatherScout] {city}: Heute {today_temp}°{config['unit']}, "
            f"Morgen {forecast_temp}°{config['unit']}")

        opps = analyze_opportunity(
            config['polymarket_name'], forecast_temp,
            config['unit'], markets)

        # Auch heute's Märkte prüfen (gleicher Tag)
        opps_today = analyze_opportunity(
            config['polymarket_name'], today_temp,
            config['unit'], markets)

        combined = opps + opps_today
        if combined:
            logger.info(
                f"[WeatherScout] {city}: {len(combined)} Opportunities")
            for o in combined[:3]:
                logger.info(
                    f"  → {o['direction']} {o['market'][:50]} "
                    f"@ {o['price']:.2f} (Edge: {o['edge']:.0%})")
            all_opportunities.extend(combined)

    logger.info(
        f"[WeatherScout] Total: {len(all_opportunities)} Opportunities")
    return all_opportunities


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    opps = run_weather_scout()
    print(f"\n=== Top Weather Opportunities ===")
    for o in opps[:5]:
        print(
            f"  {o['direction']} @ {o['price']:.2f} | "
            f"Edge: {o['edge']:.0%} | Vol: ${o['volume']:.0f} | "
            f"{o['city']} {o['forecast_temp']}°{o['unit']} vs {o['threshold']}° | "
            f"{o['market'][:55]}")
    if not opps:
        print("  (Keine Opportunities — Forecast zu nah an Schwellen)")
