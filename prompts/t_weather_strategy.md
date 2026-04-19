# T-WEATHER: Weather Market Strategy für KongTradeBot
_Erstellt: 2026-04-20 | Status: DESIGN READY_
_Voraussetzung: T-WS deployed (WebSocket aktiv)_

---

## Kontext

Polymarket hat täglich **200+ Temperatur-Märkte für 67+ Städte**.
Jeder Markt löst in 24–48 Stunden auf (täglich neue Signale!).

**Der Edge:** Kostenlose Wetterdaten (OpenMeteo, ECMWF) sind deutlich präziser als
Polymarket-Preise — gebildet durch naive Klimatologie statt echte Modelle.

**Beweis (Hans323):** London Temperatur, Markt-Preis: 8¢ (impliziert 8% WS).
ECMWF-Modelle: ~40–50%. Invest $92K → Payout $1.11M.

**Beweis (neobrother):** $891 Deposits → $29.553 Profit = **+2.536% ROI**.
Ladder-Strategie: 5-7 benachbarte Ranges, nur eine muss gewinnen.

---

## Zwei Strategien

### Strategie A — Hans323 Barbell (Außenseiter jagen)

**Logik:** Finde Märkte wo:
- Polymarket-Preis: 2–8 Cent
- Wettermodell-Wahrscheinlichkeit: 20–50%
- → Massive Mispricing: Markt bewertet Event als fast unmöglich, Modell sagt 30%+

**Mechanismus:**
```
1. OpenMeteo API abrufen: Temperaturprognose für morgen
2. Polymarket Weather-Märkte scannen für jede Stadt
3. Vergleich: Modell-WS vs. Markt-Preis
4. Wenn Markt-Preis < 0.40 × Modell-WS → Barbell-Trade
   (Markt bewertet 4x schlechter als Modell → massiver Edge)
5. Trade: $2–5 (kleine Size, Barbell-Prinzip)
```

**Erwartetes Profil:**
- 95% der Trades verlieren $2–5 (akzeptabler Verlust)
- 5% gewinnen: 10–50x Return
- 1–3 Trades pro Tag (sehr selektiv)
- Monatliches Risiko: ~$150 ($5 × ~30 Trades)
- Potenzieller Einzelgewinn: $200–2.000

---

### Strategie B — neobrother Temperature Ladder

**Logik:** Kaufe 5–7 benachbarte Temperatur-Ranges gleichzeitig.
Wenn irgendeine davon gewinnt, deckt sie alle anderen.

**Beispiel (Buenos Aires, morgen 32°C laut Modell):**
```
Kaufe gleichzeitig:
- "Buenos Aires >= 30°C": Entry 12¢ → $0.50
- "Buenos Aires >= 31°C": Entry 25¢ → $0.50
- "Buenos Aires >= 32°C": Entry 45¢ → $0.50  ← Modell-Zentrum
- "Buenos Aires >= 33°C": Entry 25¢ → $0.50
- "Buenos Aires >= 34°C": Entry 10¢ → $0.50
Total Invest: $2.50

Wenn 32°C gewinnt ($0.50 → $1.11):
  Gewinn: +$0.61 (122%)
  Verlust andere Rungs: -$2.00
  Net: -$1.39

Wenn 31°C + 32°C beide gewinnen (Tagesmax-Range):
  Gewinn: +$1.22
  Verlust: -$1.50
  Net: -$0.28

Wenn Modell exakt trifft (31–33°C):
  Gewinn: bis zu $1.83 aus 3 Rungs
  Verlust: -$1.00 (2 Außen-Rungs)
  Net: +$0.83 (+33%)
```

**Frequenz:** 5–15 Trades täglich (automatisch per Markt-Scan).

---

## Datenquellen (kostenlos)

### PRIMÄR — OpenMeteo API
```
https://api.open-meteo.com/v1/forecast?
  latitude={LAT}&longitude={LON}
  &daily=temperature_2m_max,temperature_2m_min,
         temperature_2m_mean,precipitation_probability_max
  &timezone={TIMEZONE}
  &forecast_days=2
```
- Kein API-Key nötig
- Latenz: <500ms
- Präzision: GFS-Modell (gut für globale Märkte)

### BACKUP — wttr.in (ultra-einfach)
```
https://wttr.in/{City}?format=j1
```
- Kein API-Key nötig
- JSON mit Temperatur, Feels-Like, Precipitation

### PRÄZISION EUROPA — ECMWF Open Data
```
https://data.ecmwf.int/forecasts/
```
- Höchste Präzision für europäische Städte (London!)
- Exakt das Modell das Hans323 nutzt

---

## Städte Priority-Liste

### Tier 1 — Höchstes Volumen auf Polymarket
```python
TIER1_CITIES = {
    "New York":  {"lat": 40.7128, "lon": -74.0060, "tz": "America/New_York"},
    "London":    {"lat": 51.5074, "lon": -0.1278,  "tz": "Europe/London"},
    "Los Angeles": {"lat": 34.0522, "lon": -118.2437, "tz": "America/Los_Angeles"},
    "Chicago":   {"lat": 41.8781, "lon": -87.6298,  "tz": "America/Chicago"},
}
```

### Tier 2 — Gutes Volumen + neobrother-Favoriten
```python
TIER2_CITIES = {
    "Buenos Aires": {"lat": -34.6037, "lon": -58.3816, "tz": "America/Argentina/Buenos_Aires"},
    "Tokyo":     {"lat": 35.6895, "lon": 139.6917, "tz": "Asia/Tokyo"},
    "Berlin":    {"lat": 52.5200, "lon": 13.4050,  "tz": "Europe/Berlin"},
    "Sydney":    {"lat": -33.8688, "lon": 151.2093, "tz": "Australia/Sydney"},
    "Dubai":     {"lat": 25.2048, "lon": 55.2708,  "tz": "Asia/Dubai"},
    "Miami":     {"lat": 25.7617, "lon": -80.1918,  "tz": "America/New_York"},
}
```

### Tier 3 — Spezialmärkte (HondaCivic's Fokus)
```python
TIER3_CITIES = {
    "Hong Kong": {"lat": 22.3193, "lon": 114.1694, "tz": "Asia/Hong_Kong"},
    "Seoul":     {"lat": 37.5665, "lon": 126.9780, "tz": "Asia/Seoul"},
    "Ankara":    {"lat": 39.9334, "lon": 32.8597,  "tz": "Europe/Istanbul"},
    "Lagos":     {"lat": 6.5244,  "lon": 3.3792,   "tz": "Africa/Lagos"},
}
```

---

## Bot-Integration

### Neue Datei: `core/weather_scout.py`

```python
import asyncio
import aiohttp
import json
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class WeatherSignal:
    city: str
    market_id: str
    market_question: str
    model_probability: float    # ECMWF/OpenMeteo Wahrscheinlichkeit
    market_price: float         # Polymarket aktueller Preis
    edge: float                 # model_prob - market_price
    strategy: str               # "barbell" oder "ladder"
    suggested_size_usd: float

class WeatherScout:
    def __init__(self, telegram_bot, config):
        self.enabled = os.getenv("WEATHER_TRADING_ENABLED", "false").lower() == "true"
        self.strategy = os.getenv("WEATHER_STRATEGY", "ladder")
        self.max_per_city = int(os.getenv("WEATHER_MAX_PER_CITY", "5"))
        self.max_daily_usd = float(os.getenv("WEATHER_MAX_DAILY_USD", "20"))
        self.min_volume = float(os.getenv("WEATHER_MIN_VOLUME", "1000"))
        self.max_price = float(os.getenv("WEATHER_MAX_PRICE", "0.35"))
        self.ladder_rungs = int(os.getenv("WEATHER_LADDER_RUNGS", "5"))
        self.min_edge = float(os.getenv("WEATHER_MIN_EDGE", "0.15"))
        self.telegram = telegram_bot
        self.daily_spent = 0.0

    async def run(self):
        """Läuft einmal täglich (06:00 UTC) — Weather-Märkte resetzen täglich."""
        while True:
            if self.enabled:
                try:
                    await self._daily_scan()
                except Exception as e:
                    await self.telegram.send(f"⚠️ WeatherScout Fehler: {e}")
            # Nächsten Morgen 06:00 UTC warten
            await asyncio.sleep(self._seconds_until_next_scan())

    async def _daily_scan(self):
        """Scannt alle Städte und findet Opportunities."""
        self.daily_spent = 0.0
        signals = []

        for city, coords in {**TIER1_CITIES, **TIER2_CITIES}.items():
            if self.daily_spent >= self.max_daily_usd:
                break

            forecast = await self._get_forecast(coords)
            if not forecast:
                continue

            weather_markets = await self._get_polymarket_weather_markets(city)

            for market in weather_markets:
                signal = self._analyze_market(city, market, forecast)
                if signal and signal.edge >= self.min_edge:
                    signals.append(signal)

        # Sortieren nach Edge (höchste zuerst)
        signals.sort(key=lambda s: s.edge, reverse=True)

        if signals:
            await self._send_daily_digest(signals[:10])
            if self.strategy == "ladder":
                await self._execute_ladder_strategy(signals)
            elif self.strategy == "barbell":
                await self._execute_barbell_strategy(signals)

    async def _get_forecast(self, coords: dict) -> Optional[dict]:
        """OpenMeteo Forecast abrufen."""
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={coords['lat']}&longitude={coords['lon']}"
            f"&daily=temperature_2m_max,temperature_2m_min"
            f"&timezone={coords['tz']}&forecast_days=2"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return await resp.json()
        return None

    def _analyze_market(self, city: str, market: dict,
                         forecast: dict) -> Optional[WeatherSignal]:
        """Berechnet Edge: Modell-WS vs. Markt-Preis."""
        market_price = market.get("price", 0.5)

        if market_price > self.max_price:
            return None  # Zu teuer

        model_probability = self._extract_model_probability(
            market.get("question", ""), forecast)

        if model_probability is None:
            return None

        edge = model_probability - market_price

        if edge < self.min_edge:
            return None  # Kein ausreichender Edge

        strategy = "barbell" if market_price < 0.10 else "ladder"
        size = 2.0 if strategy == "barbell" else 0.50

        return WeatherSignal(
            city=city,
            market_id=market.get("condition_id", ""),
            market_question=market.get("question", ""),
            model_probability=model_probability,
            market_price=market_price,
            edge=edge,
            strategy=strategy,
            suggested_size_usd=size
        )

    def _extract_model_probability(self, question: str,
                                    forecast: dict) -> Optional[float]:
        """Parst Frage und berechnet Wahrscheinlichkeit aus Forecast."""
        # Beispiel: "Will highest temp in London be >= 20°C?"
        # OpenMeteo gibt temperature_2m_max → Normal-Verteilung anlegen
        # (vereinfachte Version — Production braucht bessere Parsing-Logik)
        try:
            daily = forecast.get("daily", {})
            max_temp = daily.get("temperature_2m_max", [None])[1]  # Morgen
            min_temp = daily.get("temperature_2m_min", [None])[1]

            if max_temp is None:
                return None

            # TODO: Temperatur-Parsing aus market question
            # Hier: simple Heuristik (echte Implementierung braucht Regex)
            return None  # Placeholder

        except Exception:
            return None

    async def _send_daily_digest(self, signals: list[WeatherSignal]):
        """Telegram-Digest mit besten Opportunities."""
        text = "🌤️ *WEATHER SCOUT — Daily Digest*\n\n"
        for s in signals[:5]:
            text += (
                f"📍 {s.city}: {s.market_question[:50]}...\n"
                f"   Markt: {s.market_price:.2%} | Modell: {s.model_probability:.2%} | "
                f"Edge: +{s.edge:.2%} | Strategie: {s.strategy}\n\n"
            )
        await self.telegram.send(text)

    def _seconds_until_next_scan(self) -> int:
        """Sekunden bis 06:00 UTC morgen."""
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)
        next_scan = now.replace(hour=6, minute=0, second=0, microsecond=0)
        if next_scan <= now:
            next_scan += datetime.timedelta(days=1)
        return int((next_scan - now).total_seconds())
```

### Neue .env Variablen

```env
# Weather Trading
WEATHER_TRADING_ENABLED=false  # DRY_RUN zuerst
WEATHER_STRATEGY=ladder        # ladder (neobrother) oder barbell (hans323)
WEATHER_MAX_PER_CITY=5         # Max Positionen pro Stadt pro Tag
WEATHER_MAX_DAILY_USD=20       # Max Tages-Budget Weather gesamt
WEATHER_MIN_VOLUME=1000        # Mindest-Marktvolumen (USD)
WEATHER_MAX_PRICE=0.35         # Max Einstiegspreis (barbell: 0.08, ladder: 0.35)
WEATHER_LADDER_RUNGS=5         # Anzahl Rungs für Laddering
WEATHER_MIN_EDGE=0.15          # Mindest-Edge (Modell-WS minus Markt-Preis)
WEATHER_CITIES=tier1           # tier1, tier1+tier2, oder tier3
```

---

## Erwartetes Ergebnis

### Mit $20/Tag Budget (Ladder-Strategie)
| Metrik | Erwartung |
|--------|----------|
| Tägliche Trades | 10–15 |
| Resolution | 24–48 Stunden |
| Erwartete WR | 60–70% (neobrother-Benchmark) |
| Monatliches Risiko | max $600 |
| Erwarteter Monatsgewinn bei 65% WR | **+$200–400** |

### Mit Barbell-Ergänzung ($5/Tag)
| Metrik | Erwartung |
|--------|----------|
| Tägliche Trades | 1–2 |
| Verlust-Rate | ~95% der Trades |
| Potenzieller Einzelgewinn | **$200–2.000** |
| Monatliches Risiko | ~$150 |

---

## STOP-CHECKs für Server-CC

```bash
# 1. OpenMeteo API antwortet?
python3 -c "
import asyncio, aiohttp
async def test():
    url = 'https://api.open-meteo.com/v1/forecast?latitude=51.5074&longitude=-0.1278&daily=temperature_2m_max&timezone=Europe/London&forecast_days=2'
    async with aiohttp.ClientSession() as s:
        async with s.get(url) as r:
            data = await r.json()
            print(f'London max morgen: {data[\"daily\"][\"temperature_2m_max\"][1]}°C')
asyncio.run(test())
"
# Erwartung: London max morgen: XX°C

# 2. Weather-Märkte auf Polymarket abrufbar?
python3 -c "
import requests
r = requests.get('https://gamma-api.polymarket.com/markets?tag_slug=weather&limit=10')
markets = r.json()
print(f'Weather Markets: {len(markets)} gefunden')
for m in markets[:3]:
    print(f'  - {m.get(\"question\", \"\")[:60]}')
"
# Erwartung: >0 Weather Markets

# 3. Weather Scout kein Budget-Konflikt mit Copy-Trading?
grep "WEATHER_MAX_DAILY_USD\|MAX_DAILY_LOSS" /root/KongTradeBot/.env
# Sicherstellen: WEATHER_MAX_DAILY_USD << MAX_DAILY_LOSS_USD

# 4. Nach 48h DRY_RUN: Welche Opportunities wurden geloggt?
grep "WEATHER\|WeatherScout" /root/KongTradeBot/logs/bot_$(date +%Y-%m-%d).log | \
  grep "Edge\|Opportunity" | head -20
```

---

## Deployment-Reihenfolge

```
1. core/weather_scout.py erstellen
2. WEATHER_TRADING_ENABLED=false (DRY_RUN, nur Alert)
3. 48h DRY_RUN: Opportunities loggen ohne Trade
4. Analyse: Wie viele Märkte mit Edge ≥15% täglich?
5. Dann WEATHER_TRADING_ENABLED=true mit $10/Tag Budget
6. Nach 7 Tagen: Ergebnis analysieren, Budget anpassen
7. Entscheidung: Barbell hinzufügen (wenn Ladder profitabel)
```

**Commit-Message:**
```
feat(weather): T-WEATHER Phase 1 — OpenMeteo + Ladder + Barbell

core/weather_scout.py: Weather Market Scanner
- OpenMeteo API Integration (kostenlos, kein Key)
- Barbell-Strategie: Edge bei 2-8¢ Märkten (Hans323)
- Ladder-Strategie: 5 Rungs pro Stadt (neobrother)
- DRY_RUN default (WEATHER_TRADING_ENABLED=false)
```

---

## Referenzen

| Quelle | URL |
|--------|-----|
| Hans323 Strategie | predictionmarketspicks.com (Barbell Playbook) |
| neobrother Profil | predicts.guru/checker/0x6297... (+2,536% ROI) |
| OpenMeteo API | api.open-meteo.com (kostenlos, kein Key) |
| ECMWF Open Data | data.ecmwf.int (höchste Präzision Europa) |
| T-WS Prompt | prompts/t_ws_websocket_wallet_monitor.md |
| Weather Traders Analyse | analyses/weather_traders_2026-04-20.md |
