# News Signal Services — Vergleich 2026-04-20
_Erstellt: 2026-04-20 | Für: KongTradeBot T-NEWS Integration_

---

## WICHTIGSTE ERKENNTNIS

**Glint.trade ist kostenlos** (nur 1% auf Gewinne bei Trades via Glint).
Telegram-Alerts mit Keyword-Matching sind direkt integriert — kein Code nötig.
Glint ist von **Polymarket selbst backed** und hat alles was wir brauchen.

**Empfehlung: Glint.trade sofort einrichten (heute, 5 Minuten, kostenlos).**

---

## Vergleichstabelle — Alle 6 Services

| Service | Kosten | Latenz | Quellen | Telegram | API/Webhook | Weather | Bot-Integration | Empfehlung |
|---------|--------|--------|---------|----------|------------|---------|----------------|-----------|
| **Glint.trade** | **Kostenlos** (1% auf Gewinne) | Echtzeit | X + News + TG + OSINT + Flugtracker | ✅ Keyword-Alerts | ❌ Keine eigene API | ✅ (Feed deckt alles) | ✅ Über Telegram-Listener | **⭐ SOFORT** |
| PolySignal.xyz | Early Bird ? | Echtzeit | Reuters/AP/BBC/Bloomberg | ✅ Instant | Coming Soon | ? | Über Telegram | 🟡 Evaluieren |
| PolySignal.info | Free / $29 / $99 | 1-15s | On-Chain Analytics | ❌ (nicht Telegram) | ❌ | ❌ | Export CSV/JSON | 🟡 Ergänzend |
| TradingNews API | $20/Monat | <200ms | Reuters/AP/AFP/Bloomberg | ❌ | ✅ WebSocket | ❌ | ✅ Direkt | 🔵 Phase 2 |
| polymarket-pipeline | Kostenlos | Echtzeit | Twitter/TG/RSS | Selbst bauen | ✅ (Claude API) | ❌ | ✅ Komplett | 🔵 Phase 3 |
| WeatherBot.finance | ? | Täglich | Weather APIs | ? | ? | ✅ | ✅ Open Source | 🟡 Für T-WEATHER |

---

## Glint.trade — Volldetails

### Pricing
```
Keine Subscription-Fees. Keine Premium-Tiers.
Einzige Kosten: 1% Referral-Fee auf GEWINNE (nicht auf Einsatz).
Beispiel: Gewinn $100 → Glint nimmt $1. Verlust → Keine Gebühr.
```

**Das ist das beste Pricing-Modell denkbar für uns** — wir zahlen nur wenn wir gewinnen.
Direkt vergleichbar mit Polymarket's eigenem Fee-Modell.

### Features
| Feature | Details |
|---------|---------|
| **Real-Time Feed** | AI-klassifizierte Signale aus X, News, Telegram, OSINT — gefiltert nach Impact |
| **AI Market Matching** | Jedes Signal automatisch gematcht zu Polymarket-Märkten + Relevanz-Score |
| **Vision Terminal** | 3D-Globus mit globalen Signalen, Militärflug-Tracking, Whale-Positionen |
| **Whale Tracker** | $10K+ Trades, Wallet-Alter, NEW-Badge (<7 Tage), Cluster-Erkennung |
| **Alerts (Telegram)** | Keyword-basiert, Impact-Level Filter (Critical/High/Medium/All) |
| **Inline Trading** | Direkt aus Feed kaufen (1% Gebühr auf Gewinne) |
| **Flight Tracker** | OSINT: Militär- und Privatflüge — Iran/Naher Osten relevant! |

### Glint Telegram-Alerts — So funktioniert es
1. glint.trade/alerts öffnen
2. "Create Alert" → Keywords eingeben
3. Delivery: Telegram auswählen
4. Glint-Bot in Telegram starten (`/start`)
5. Fertig — bei jedem Match kommt sofort eine Nachricht

**Alert-Inhalt:**
- Direct Link zum Signal in Glint
- Matched Polymarket Contract + aktuelle Odds
- Impact Level + Category
- Source + Timestamp
- Signal-Text

**Keyword-Tipps:**
```
Iran: "ceasefire", "Iran deal", IRGC, Khamenei, Hormuz
Trump: "executive order", "Trump tariff", DOGE
Fed: FOMC, "rate cut", "rate hike", Powell
Bitcoin: "Bitcoin ETF", "spot ETF", IBIT, Blackrock
NBA: Finals, Playoff, Conference
Ukraine: Zelensky, "Ukraine ceasefire", Kremlin
```

### Glint Whale Tracker — Für uns besonders wertvoll

| Feature | Relevanz für KongTradeBot |
|---------|--------------------------|
| NEW-Badge (Wallet <7 Tage) | **= T-M-NEW Insider-Signal** — frische Wallets mit großen Bets |
| Cluster-Buying (3+ Wallets) | **= T-M-NEW Koordinations-Signal** |
| $10K+ Threshold | Filtert Noise heraus |
| Wallet Portfolio Modal | Direkt-Check der Trader-Historie |

**Das Glint Whale Tracker ersetzt teilweise T-M-NEW:**
Glint zeigt bereits Cluster-Buying und neue Wallets in Echtzeit.
Unser T-M-NEW sollte KOMPLEMENTÄR sein (automatisiert + höherer Schwellenwert).

### Glint API/Webhook — Verfügbarkeit

**Aktuell: Keine öffentliche API von Glint selbst.**

**Alternativer Ansatz:** Glint → Telegram-Alert → unser Bot hört auf den Alert.
```
Glint erkennt Signal → Telegram Alert an Onur
                      → (zukünftig) Telegram Listener → KongTradeBot verarbeitet
```

**Für Webhooks auf Polymarket:** struct.to bietet offizielle Webhooks:
- `trader_whale_trade` → wenn >$10K Trade
- `probability_spike` → wenn Markt springt
- Kostenpflichtig (Preis unbekannt)

---

## PolySignal.xyz — Analyse

### Pricing
"Early Bird Pricing — Lock in your rate for life."
Preis nicht direkt sichtbar (kommt nach E-Mail-Subscribe).
API: "Coming Soon — Early Bird subscribers get first access."

### Features
- 200+ News-Quellen (Reuters, AP, BBC, Bloomberg)
- AI matcht News zu Polymarket-Märkten
- Instant Telegram Delivery
- Tweet-Matching (Coming Soon)

### Bewertung
**Gut aber unklar:** Early Bird Pricing ohne Preis zu nennen ist ein Warning Sign.
Telegram-Integration vorhanden. Aber wir haben Glint kostenlos — warum zahlen?

**Empfehlung:** Nur wenn Glint in einem Sektor Lücken hat (z.B. kein Macro/Fed Coverage).
Erst nach 30 Tagen Glint evaluieren.

---

## PolySignal.info — Analyse

**Achtung: Andere Seite als polysignal.xyz!**

Dies ist ein **Analytics-Service**, kein News-Service:
- Free: Volume Spike + Price Impact Signals, 5-Min Refresh
- Plus $29/Monat: 4 Signaltypen, 1-Min Refresh, 25 Märkte
- Pro $99/Monat: 15s Real-Time, Unlimited Watchlist

**Für uns:** Ergänzend zu Glint (Analytics vs. News).
PolySignal.info = Spike Detection (wie unser geplanter Spike-Detektor).
Vorteil: $0 Kosten im Free Tier. Nachteil: Kein Telegram, nur Web.

---

## TradingNews API ($20/Monat) — Analyse

### Details
- Sub-200ms Latenz (schnellste verfügbare)
- WebSocket Streaming
- Filter: urgency=breaking, categories=geopolitics/politics/macro
- REST + WebSocket Integration
- Speziell für Algo-Trading gebaut

### Bewertung
Beste technische Alternative wenn Glint für Macro-Themen (Fed, Economics) nicht ausreicht.
$20/Monat = akzeptabel wenn ROI positiv.

**Empfehlung: Phase 2 — erst nach 30 Tagen Glint evaluieren ob Lücken vorhanden.**

---

## Unsere Empfehlung: Optimale Kombination

### Budget $0 (sofort)
```
Glint.trade Telegram Alerts
+ RSS Monitor Phase 1B (eigener Code, 30s Poll)
+ Spike Detektor Phase 1A (WebSocket, eigener Code)
```

### Budget $20/Monat (nach 30 Tagen wenn ROI positiv)
```
+ TradingNews API für Macro/Fed News (sub-200ms)
```

### Budget $30/Monat (nach 60 Tagen wenn ROI sehr positiv)
```
+ PolySignal.info Plus ($29/Monat) für Analytics-Signale
  ODER PolySignal.xyz wenn Preis <$20/Monat
```

### Nicht empfohlen (aktuell)
```
❌ Twitter X API ($100/Monat) — zu teuer ohne ROI-Beweis
❌ Struct.to Webhooks — Glint deckt das ab kostenlos
❌ polymarket-pipeline — Implementierungsaufwand vs. Glint kostenlos
```

---

## Integration-Architektur

```
                    GLINT.TRADE
                       │
                   Telegram Alert
                  ↙         ↘
            Onur (manuell)   KongTradeBot Telegram Listener
                              (zukünftig: T-NEWS Phase 3)
                                    │
                             Signal Parser
                                    │
                           Keyword → Market Match
                                    │
                             Auto-Trade (Tier 1)
                             Alert only (Tier 2/3)
```

---

## Polymarket Fee-Struktur (wichtig für T-WEATHER)

Ab März 30, 2026 sind fast alle Kategorien kostenpflichtig:

| Kategorie | Fee-Rate | Peak-Fee (100 shares @50¢) |
|-----------|---------|--------------------------|
| Crypto | 7.2% | $1.80 |
| Economics/Culture/Weather/Other | 5.0% | $1.25 |
| Finance/Politics/Mentions/Tech | 4.0% | $1.00 |
| Sports | 3.0% | $0.75 |
| **Geopolitics** | **0%** | **$0.00 — GRATIS!** |

**Implikation:** Weather-Trades kosten jetzt 5% Fee-Rate → bei $0.50 Einsatz = $0.0625 Gebühr.
Geopolitics-Trades bleiben kostenlos → ideal für unsere Geopolitik-Wallets.

Für T-WEATHER: Weather-Fees müssen in Edge-Berechnung einbezogen werden.
Mindest-Edge: 15% → nach Fees noch ~10% Netto-Edge.

---

_Stand: 2026-04-20 | Alle Preise verifiziert (Glint FAQ + Benzinga + PolySignal.info)_
