# T-NEWS Setup — So bekommst du Polymarket Signale
_Erstellt: 2026-04-20 | Für: KongTradeBot T-NEWS Integration_

---

## Option 1 — Glint.trade (kostenlos, 5 Minuten) ⭐ EMPFOHLEN

**Kosten:** Keine Subscription. 1% nur auf Gewinne bei Trades via Glint (nicht auf Einsatz).

### Schritt 1: glint.trade öffnen
Browser → `https://glint.trade`

### Schritt 2: Einloggen
"Get Started" → Sign in with Google (oder Wallet Connect)

### Schritt 3: Feed erkunden
Oben im Menü → **"Feed"** anklicken.
Du siehst AI-klassifizierte Signale aus X, Telegram, News, OSINT — gefiltert nach Impact.
Jedes Signal zeigt: matched Polymarket-Märkte + aktuelle Odds + Relevanz-Score.

### Schritt 4: Vision Terminal (optional)
Menü → **"Terminal"** — 3D Globus mit globalen Signalen, Militärflug-Tracking, Whale-Positionen.
Besonders nützlich für Geopolitik-Monitoring (Iran, Ukraine, Naher Osten).

### Schritt 5: Telegram Alerts einrichten
1. Glint → **"Alerts"** (oder direkt: `https://glint.trade/alerts`)
2. **"Create Alert"** klicken
3. **Keywords eingeben** (siehe Keyword-Liste unten)
4. **Impact Level wählen:** Critical (nur major events) oder High (empfohlen)
5. **Delivery: "Telegram"** auswählen
6. Glint-Bot in Telegram starten: `@GlintTradeBot` → `/start`
7. Fertig — bei jedem Keyword-Match kommt sofort eine Nachricht

### Keyword-Sets für Alerts

**Alert 1 — Geopolitics (0% Fee auf Polymarket!)**
```
Iran, ceasefire, IRGC, Khamenei, Hormuz, Zelensky, Ukraine, Kremlin, Gaza, Netanyahu
```

**Alert 2 — Trump/US-Politik**
```
executive order, Trump tariff, DOGE, Trump deal, sanctions, White House
```

**Alert 3 — Makro/Märkte**
```
FOMC, rate cut, rate hike, Powell, Fed meeting, inflation, CPI, recession
```

**Alert 4 — Crypto**
```
Bitcoin ETF, spot ETF, IBIT, Blackrock, SEC, crypto regulation, halving
```

**Alert 5 — Sports (optional)**
```
NBA Finals, NFL Draft, UFC, Champions League, World Cup
```

### Was du in jedem Alert bekommst
- Direct Link zum Signal in Glint
- Matched Polymarket Contract + aktuelle Odds
- Impact Level + Category
- Source + Timestamp
- Signal-Text

### Schritt 6: Whale Tracker
Menü → **"Whales"**
- Filter: $10K+ Trades
- NEW Badge = Wallet <7 Tage alt (= potenzieller Insider!)
- Cluster: 3+ Wallets gleiche Position = starkes koordiniertes Signal
- Wallet anklicken → Portfolio Modal zeigt komplette Trader-Historie

---

## Option 2 — PolySignal.xyz (Evaluieren nach 30 Tagen)

**Status:** Early Bird Pricing — Preis unbekannt (E-Mail required).
**Features:** 200+ News-Quellen (Reuters/AP/BBC/Bloomberg), AI Market Matching, Telegram Delivery.
**Warum warten:** Glint ist kostenlos. PolySignal.xyz erst evaluieren wenn Glint Lücken zeigt.

**Setup (falls du es jetzt testen willst):**
1. `https://polysignal.xyz` → E-Mail eingeben für Early Bird Access
2. Preis prüfen: nur weiter wenn <$20/Monat UND ROI positiv

---

## Option 3 — TradingNews API ($20/Monat, Phase 2)

**Wann:** Erst nach 30 Tagen Glint — wenn Macro/Fed-News nicht ausreichend abgedeckt.
**Vorteil:** Sub-200ms Latenz, WebSocket, speziell für Algo-Trading gebaut.

**Setup für KongTradeBot:**
```python
# .env hinzufügen:
TRADINGNEWS_API_KEY=your_key_here
TRADINGNEWS_ENABLED=true

# core/rss_monitor.py Phase 2 Erweiterung
WS_URL = "wss://api.tradingnews.com/v1/stream"
FILTER = {"urgency": "breaking", "categories": ["geopolitics", "politics", "macro"]}
```

**Quellen:** Reuters, AP, AFP, Bloomberg, 200+ Publishers.
**Registrierung:** `https://tradingnews.io` → API Key nach Registrierung.

---

## Option 4 — RSS Monitor (kostenlos, selbst bauen)

**Diese Woche implementieren** als Backup zu Glint.

**Quellen (alle kostenlos):**
```
Reuters:    https://feeds.reuters.com/reuters/topNews
AP:         https://rsshub.app/apnews/topics/apf-topnews
BBC:        https://feeds.bbci.co.uk/news/world/rss.xml
Al Jazeera: https://www.aljazeera.com/xml/rss/all.xml
```

**Implementierung:** `core/rss_monitor.py` — 30s Poll, Keyword-Filter, MD5 Dedup, Freshness <10min.
(Details im Prompt: `prompts/t_news_monitor.md` → Phase 1B)

---

## Empfohlene Reihenfolge

```
HEUTE (5 Min):
└── Glint.trade Alerts einrichten (Steps 1-6 oben)
    → 5 Keyword-Sets erstellen
    → Telegram-Bot verbinden

DIESE WOCHE:
└── RSS Monitor Phase 1B bauen (core/rss_monitor.py)
└── Spike Detector Phase 1A bauen (core/spike_detector.py)

NACH 30 TAGEN:
└── Prüfen: Hat Glint Lücken bei Macro/Fed?
    JA → TradingNews API ($20/Monat) testen
    NEIN → weiter kostenlos mit Glint + RSS

NACH 60 TAGEN:
└── PolySignal.info Plus ($29/Monat) evaluieren?
    → Nur wenn ROI sehr positiv
```

---

## Integration mit KongTradeBot (Zukunft)

```
JETZT (manuell):
Glint Telegram Alert → du liest → du entscheidest → manueller Trade

PHASE 2 (automatisiert):
Glint Telegram Alert → KongTradeBot Telegram Listener
                        → Signal Parser (Keyword + Market Match)
                        → Auto-Trade wenn Tier 1 Signal
                        → Alert only wenn Tier 2/3

PHASE 3 (vollautomatisch):
polymarket-pipeline → Claude API Klassifikation
                    → Direkt in KongTradeBot Signal Queue
```

---

## Polymarket Fees — wichtig für Signal-Bewertung

| Kategorie | Fee-Rate | Implikation |
|-----------|---------|------------|
| **Geopolitics** | **0%** | Priorisieren! Glint Geo-Alerts = beste ROI |
| Sports | 3.0% | Min. Edge >3% für positiven EV |
| Finance/Politics/Tech | 4.0% | Min. Edge >4% nötig |
| Economics/Weather/Other | 5.0% | Min. Edge >5% nötig |
| Crypto | 7.2% | Nur bei sehr klarem Signal |

---

_Stand: 2026-04-20 | Glint.trade ist von Polymarket gebackt — stabiler als Third-Party Services_
