# T-X-TWITTER: X/Twitter Trend Monitor Design
_Erstellt: 2026-04-20 | Für: KongTradeBot Intelligence Layer_

---

## Ziel

Trends auf X erkennen BEVOR sie mainstream werden.
Beispiel: Weather-Trading war wochenlang auf X bekannt
bevor wir es entdeckt haben. hans323's London-Temperatur-Trade
wurde auf X diskutiert — wir sahen ihn erst im PANews-Artikel.

**Kritische Edge:** Wer einen Tweet von @NickTimiraos (Fed-Reporter WSJ)
5 Minuten früher sieht als der Markt, hat einen Arbitrage-Vorteil
auf allen Fed/FOMC/Rate-Märkten.

---

## Accounts zu monitoren (Priorität)

### Tier 1 — Muss-Monitor (Marktbewegend)
| Account | Warum | Polymarket-Relevanz |
|---------|-------|-------------------|
| `@Polymarket` | Offizielle Märkte + Ankündigungen | Direkter Markt-Impact |
| `@NickTimiraos` | Fed-Reporter WSJ — *The* Makro-Edge | FOMC/Fed/Zinsen |
| `@elonmusk` | Tweet → sofortige Krypto/Markt-Bewegung | Crypto, Tech, DOGE |
| `@glintintel` | Glint Updates, neue Features | Meta: unser Tool |

### Tier 2 — Wichtig (Wöchentlich)
| Account | Warum | Polymarket-Relevanz |
|---------|-------|-------------------|
| `@spydenuevo` | neobrother (Weather-Trading-Pionier) | Weather-Strategie Insights |
| `@Polymarket_` | Community, neue Trader-Diskussionen | Neue APPROVE-Kandidaten |
| `@AliAbdaal` / Prediction-Market-Accounts | Strategy-Diskussionen | Neue Strategien |
| `@realDonaldTrump` | Trump-Posts → Policy-Trades | Trump/EO/Tariff-Märkte |

### Tier 3 — Discovery (Monatlich)
| Account | Warum |
|---------|-------|
| Polymarket-Leaderboard Trader X-Accounts | Wallet-Entdeckung |
| Weather-Trading-Community | hans323-Strategie-Refinement |
| Iran/Ukraine Expert-Konten | Geopolitik-Edge |

---

## Keywords für Trend-Erkennung

```
# Polymarket-direkt
"polymarket" + any
new wallet strategy site:x.com
"prediction market" edge secret

# Weather Trading
"weather trading" polymarket
"temperature market" polymarket
"hans323" OR "weather trader" polymarket
openmeteo ECMWF polymarket

# Geopolitics (0% Fee — höchste Priorität)
Iran ceasefire deal nuclear
Ukraine peace negotiations
Zelensky Kremlin signal
IRGC Strait Hormuz

# Makro/Fed
NickTimiraos (immer relevanter Post)
FOMC decision leak
"rate cut" OR "rate hike" confirmed
Fed pivot signal

# Crypto
Bitcoin ETF approval
"spot ETF" SEC
Blackrock IBIT
crypto regulation bill

# Meta-Signale (neue Trader-Strategien)
"polymarket insider"
"smart money polymarket"
new whale wallet strategy
```

---

## Empfohlene Lösungen — Kosten-Analyse 2026

### ❌ Option A — Nitter (DEAD)
**Nitter ist seit Februar 2024 tot.** X hat Guest-Accounts deaktiviert.
Kein Open-Source X-Mirror mehr verfügbar.

### ❌ Option B — Offizielle X API
| Tier | Preis | Reads |
|------|-------|-------|
| Free | $0 | Write-only (KEINE Lesezugriffe!) |
| Basic | $200/Monat | 10K reads/Monat |
| Pro | $5.000/Monat | 1M reads |
| Enterprise | ~$42.000/Monat | Full Firehose |
**→ Für uns: viel zu teuer, Free-Tier hat KEINE Reads.**

### ✅ Option C — xAPIs.dev: $9.99/Monat ⭐ GÜNSTIGSTE

| Feature | Wert |
|---------|------|
| Preis | **$9.99/Monat** |
| Latenz | <100ms (claim) |
| Typ | REST API only (kein WebSocket) |
| Accounts | Unbegrenzt (REST polling) |
| Legal | Alternative API (kein offizielles ToS) |

**Für uns:** Nur 10 Accounts, 30s-Polling reicht für Discovery-Layer.
Kein Real-Time, aber ausreichend für unsere Strategie-Früherkennung.

### ✅ Option D — Xquik: $20/Monat ⭐ BESTE VALUE

| Feature | Wert |
|---------|------|
| Preis | **$20/Monat** Basis |
| Reads | $0.00015/Call (33x günstiger als offizielle X API) |
| Webhooks/Monitoring | **KOSTENLOS** (kein Extra-Preis) |
| Endpoints | 122 REST Endpoints |
| Monitoring | Radar-Feature: Keyword-Alerts per Webhook |
| Legal | Alternative API |

**Für uns:** 10 Accounts × 48 Checks/Tag × 30 Tage = 14.400 Calls = **$2.16** zusätzlich.
Monatlich total: ~**$22/Monat**.
Webhooks für Keyword-Alerts → direkt in KongTradeBot integrierbar.

### ✅ Option E — twitterapi.io: $29/Monat (5 Accounts, Real-Time)

| Feature | Wert |
|---------|------|
| Preis | **$29/Monat** (5 Accounts) |
| Latenz | Real-Time Streaming |
| Typ | WebSocket + Webhook |
| Accounts | 5 (Starter-Plan) |
| Extra-Accounts | $5/Monat je Account |

**Für uns:** Tier-1 Accounts (4 Stück) für $29 — ideal für NickTimiraos + Polymarket + Elon + Trump.
Restliche über REST-Polling ergänzen.

### ✅ Option F — Xanguard: $49/Monat (25 Accounts, Telegram-Integration)

| Feature | Wert |
|---------|------|
| Preis | **$49/Monat** |
| Latenz | **<500ms** (WebSocket) |
| Accounts | 25 Accounts |
| Module | 4: Tweets + Follow/Unfollow + Profile-Changes + Community |
| Delivery | **Telegram direkt** (kein Code nötig!) |
| Webhooks | ✅ |

**Für uns:** Telegram-Delivery ist perfekt — direkt in unseren KongTrade Intelligence Chat.
25 Accounts decken alle Tier-1 + Tier-2 Accounts ab.

### Option G — TweetStream: $139/Monat (Polymarket built-in!)

| Feature | Wert |
|---------|------|
| Preis | **$139/Monat** (Basic, jährlich $139/Monat) |
| Latenz | Real-Time WebSocket |
| Accounts | 50 |
| Besonderheit | **Polymarket-Erkennung built-in!** |
| OCR | ✅ (Screenshots automatisch lesen) |

**Für uns:** Teuerste Option aber einzige mit nativem Polymarket-Matching.
Tweet enthält Polymarket-Link → sofortiger Alert. Erst nach ROI-Beweis sinnvoll.

---

## Empfehlung: Optimaler Start

### Budget $0 (sofort)
```
twikit (Python, Open Source)
+ Eigenes 30s-Polling auf Tier-1 Accounts
+ Keine API-Keys nötig (inoffiziell — Legal-Risiko beachten)
```

### Budget $22/Monat (Phase 1, ab sofort)
```
Xquik $20/Monat
+ Webhooks kostenlos
+ 10 Accounts per Radar-Monitoring
+ Keyword-Alerts → KongTrade Intelligence Telegram-Gruppe
```

### Budget $49/Monat (Phase 2, nach 30 Tagen ROI-Nachweis)
```
Xanguard $49/Monat
+ 25 Accounts
+ Telegram built-in (0 Code)
+ <500ms Latenz für NickTimiraos-Trades
```

### Budget $139/Monat (Phase 3, nach positivem ROI-Beweis)
```
TweetStream $139/Monat
+ Polymarket-Erkennung built-in
+ OCR für Screenshot-Trades
```

---

## Bot-Integration

### Xanguard → Telegram → KongTradeBot (Phase 2)

```
@NickTimiraos tweetet "Fed hält Zinsen"
       │ <500ms
  Xanguard erkennt → Telegram Alert an "KongTrade Intelligence"
       │
  KongTradeBot Telegram Listener
       │
  Keyword-Check: FOMC / rate / Powell
       │
  Market Match via Gamma-API
       │
  Alert an Onur (Tier 2) ODER Auto-Trade (Tier 1 Geopolitics)
```

### Xquik + Webhook → KongTradeBot (Phase 1)

```python
# core/x_monitor.py
import httpx
import asyncio

XQUIK_API_KEY = os.getenv("XQUIK_API_KEY")
MONITORED_ACCOUNTS = [
    "NickTimiraos", "Polymarket", "glintintel",
    "spydenuevo", "elonmusk", "realDonaldTrump"
]

async def setup_x_radar():
    """Einmalig: Xquik Radar für alle Accounts + Keywords einrichten."""
    headers = {"Authorization": f"Bearer {XQUIK_API_KEY}"}
    payload = {
        "accounts": MONITORED_ACCOUNTS,
        "keywords": ["polymarket", "FOMC", "ceasefire", "Iran", "weather trading"],
        "webhook": "https://your-server/webhook/x-alert"
    }
    async with httpx.AsyncClient() as client:
        await client.post("https://api.xquik.io/v1/radar", json=payload, headers=headers)

async def handle_x_alert(tweet: dict):
    """Verarbeitet eingehenden Xquik Webhook-Alert."""
    text = tweet.get("text", "")
    account = tweet.get("author", {}).get("username", "")
    
    if account == "NickTimiraos":
        # Fed-Reporter → hohe Priorität
        await send_telegram_alert(f"🏦 FED SIGNAL: @NickTimiraos\n{text}")
    elif "polymarket" in text.lower():
        await send_telegram_alert(f"📊 X: @{account}\n{text}")
```

### .env Variablen

```
X_MONITOR_ENABLED=false          # true wenn Phase 1 aktiv
XQUIK_API_KEY=your_key_here      # von xquik.io
XANGUARD_API_KEY=your_key_here   # falls Phase 2
X_MONITOR_TIER=1                 # 1=Xquik, 2=Xanguard, 3=TweetStream
X_ALERT_MIN_TIER=2               # nur Tier 1/2 Accounts auto-alerting
```

---

## Kosten-Nutzen

| Service | Kosten | Latenz | Accounts | Empfehlung |
|---------|--------|--------|---------|-----------|
| xAPIs.dev | $9.99/Mo | <100ms | unlimitiert | Backup/Test |
| **Xquik** | **$22/Mo** | REST | 10+ | **Phase 1** |
| twitterapi.io | $29/Mo | Real-Time | 5 | Alternative |
| **Xanguard** | **$49/Mo** | <500ms | 25 | **Phase 2** |
| TweetStream | $139/Mo | Real-Time | 50 | Phase 3 |

**Fazit:** Xquik ($22/Monat) für Anfang. Upgrade auf Xanguard wenn NickTimiraos-Edge bestätigt.
TweetStream erst wenn wir ROI von X-Monitoring nachweisen können.

---

_Stand: 2026-04-20 | Nitter ist tot (Feb 2024), offizielle X API ist unerschwinglich_
_Nächste Prüfung: 2026-05-20 — Hat X-Monitoring nachweislich Polymarket-Edge geliefert?_
