# T-NEWS: News-Monitor für KongTradeBot
_Erstellt: 2026-04-20 | Status: DESIGN_
_Voraussetzung: T-WS deployed (WebSocket WalletMonitor aktiv)_

---

## Problem

Insider kaufen bei 3 Cent BEVOR Breaking News öffentlich wird.
Wir kaufen DANACH bei 30–50 Cent.

```
Insider-Wallet kauft 3¢ → Preis 3¢
Breaking News veröffentlicht → Preis springt in < 30s auf 50¢
Wir sehen Signal (T-WS) → Preis schon bei 30-50¢
```

**Lösung:** Eigene News-Fühler die vor oder gleichzeitig mit den
Insidern Breaking News erkennen. Mit eigenem Signal kaufen wir bei 3–10¢
statt bei 30–50¢.

---

## Ziel

Breaking News erkennen **BEVOR oder GLEICHZEITIG** mit Insidern.
Preis-Spike bei 3 Cent statt bei 30 Cent kaufen.

**Synergie mit T-M-NEW (AnomalyDetector):**
- T-M-NEW: erkennt Insider-Bewegung NACH dem Kauf (on-chain)
- T-NEWS: erkennt News-Trigger BEVOR oder WÄHREND dem Kauf
- Kombiniert: doppelte Absicherung gegen zu späten Einstieg

---

## Drei Phasen

---

### Phase 1 — Kostenlos, sofort (morgen implementierbar)

#### Phase 1A — Interner Polymarket Preis-Spike-Detektor

Nutzt die bestehende WebSocket-Verbindung (T-WS deployed).
Kein externer API-Key nötig. Sofort einsatzbereit.

**Logik:**
```
Markt springt > 15% in < 60 Sekunden
UND Volumen > $50k in letzten 5 Minuten
UND Markt aktuell zwischen 5–40 Cent (noch günstig genug)
→ Telegram-Alert an Onur: "⚡ SPIKE: [Markt] [Preis] → prüfen"
→ KEIN Auto-Trade — nur manueller Alert
```

Der Spike-Detektor ist ein Frühwarnsystem: Ein Spike OHNE News-Bestätigung
(Tier 1/2) bedeutet wahrscheinlich Insider-Aktivität → Manuell prüfen.

**Implementierung:**

```python
# core/spike_detector.py

import asyncio
import time
from collections import defaultdict

class SpikeDetector:
    def __init__(self, telegram_bot, config):
        self.enabled = os.getenv("SPIKE_DETECTOR_ENABLED", "false").lower() == "true"
        self.threshold_pct = float(os.getenv("SPIKE_THRESHOLD_PCT", "0.15"))  # 15%
        self.window_seconds = int(os.getenv("SPIKE_WINDOW_SECONDS", "60"))
        self.min_volume_usd = float(os.getenv("SPIKE_MIN_VOLUME_USD", "50000"))
        self.max_price_cents = float(os.getenv("SPIKE_MAX_PRICE", "0.40"))  # 40¢
        self.min_price_cents = float(os.getenv("SPIKE_MIN_PRICE", "0.05"))  # 5¢
        self.telegram = telegram_bot
        self.price_history = defaultdict(list)  # market_id → [(timestamp, price)]
        self.alerted_markets = set()  # Duplikat-Schutz

    async def process_price_update(self, market_id: str, 
                                    price: float, volume_usd: float):
        if not self.enabled:
            return

        now = time.time()
        history = self.price_history[market_id]

        # Trim: nur letzten 60s behalten
        history[:] = [(t, p) for t, p in history 
                      if now - t < self.window_seconds]
        history.append((now, price))

        if len(history) < 2:
            return

        # Preis außerhalb Ziel-Range → ignorieren
        if not (self.min_price_cents <= price <= self.max_price_cents):
            return

        # Spike-Check
        oldest_price = history[0][1]
        if oldest_price == 0:
            return

        change_pct = (price - oldest_price) / oldest_price

        if (change_pct >= self.threshold_pct
                and volume_usd >= self.min_volume_usd
                and market_id not in self.alerted_markets):

            self.alerted_markets.add(market_id)
            await self.telegram.send(
                f"⚡ *SPIKE DETECTED*\n"
                f"Markt: `{market_id}`\n"
                f"Preis: {oldest_price:.2f}¢ → {price:.2f}¢ "
                f"(+{change_pct*100:.1f}% in {self.window_seconds}s)\n"
                f"Volumen: ${volume_usd:,.0f}\n"
                f"⚠️ Kein Auto-Trade — manuell prüfen!"
            )
```

**Neue Datei:** `core/spike_detector.py`

**Neue .env Variablen:**
```env
SPIKE_DETECTOR_ENABLED=true
SPIKE_THRESHOLD_PCT=0.15       # 15% Preisanstieg in SPIKE_WINDOW_SECONDS
SPIKE_WINDOW_SECONDS=60        # Zeitfenster für Spike-Messung
SPIKE_MIN_VOLUME_USD=50000     # Mindestvolumen im Markt
SPIKE_MAX_PRICE=0.40           # Maximaler Marktpreis (40¢) — günstig genug
SPIKE_MIN_PRICE=0.05           # Minimaler Marktpreis (5¢) — nicht Sub-Cent-Schrott
```

**Aufwand Server-CC:** ~2 Stunden

---

#### Phase 1B — RSS-Monitor (Reuters, AP, BBC, Al Jazeera)

Gratis Feeds, keine Anmeldung nötig. Poll alle 30 Sekunden.
Keyword-Matching gegen offene Märkte.

**RSS-Quellen:**
```python
RSS_FEEDS = {
    "Reuters":    "https://feeds.reuters.com/reuters/topNews",
    "USA Today":  "https://rssfeeds.usatoday.com/usatoday-NewsTopStories",
    "BBC World":  "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
}
```

**Keyword-Mapping gegen Polymarket-Märkte:**
```python
KEYWORD_CATEGORIES = {
    "IRAN": [
        "iran", "ceasefire", "tehran", "khamenei", "irgc",
        "hormuz", "nuclear deal", "sanctions", "persian gulf"
    ],
    "TRUMP": [
        "trump", "executive order", "white house", "oval office",
        "mar-a-lago", "tariff", "veto", "pardon"
    ],
    "FED": [
        "federal reserve", "interest rate", "powell", "fomc",
        "rate hike", "rate cut", "inflation", "cpi", "fed meeting"
    ],
    "NBA": [
        "nba", "finals", "playoff", "lakers", "celtics", "warriors",
        "nuggets", "heat", "bucks", "sixers", "knicks"
    ],
    "BITCOIN": [
        "bitcoin", "btc", "sec", "etf", "crypto", "coinbase",
        "blackrock", "spot etf", "blockchain", "cryptocurrency"
    ],
    "UKRAINE": [
        "ukraine", "zelensky", "russia", "moscow", "kyiv",
        "nato", "kremlin", "putin", "war", "ceasefire"
    ],
    "MIDDLE_EAST": [
        "israel", "hamas", "gaza", "hezbollah", "lebanon",
        "syria", "yemen", "saudi", "arab", "middle east"
    ],
}
```

**Implementierung:**

```python
# core/rss_monitor.py

import asyncio
import feedparser
import hashlib
import time
from datetime import datetime, timezone

class RSSMonitor:
    def __init__(self, telegram_bot, market_manager, config):
        self.enabled = os.getenv("RSS_MONITOR_ENABLED", "false").lower() == "true"
        self.poll_interval = int(os.getenv("RSS_POLL_INTERVAL_SECONDS", "30"))
        self.freshness_minutes = int(os.getenv("RSS_FRESHNESS_MINUTES", "10"))
        self.telegram = telegram_bot
        self.market_manager = market_manager
        self.seen_hashes = set()  # Duplikat-Schutz via Artikel-Hash

    async def run(self):
        while True:
            for source_name, feed_url in RSS_FEEDS.items():
                try:
                    await self._check_feed(source_name, feed_url)
                except Exception as e:
                    logger.warning(f"[RSS] {source_name} Fehler: {e}")
            await asyncio.sleep(self.poll_interval)

    async def _check_feed(self, source: str, url: str):
        feed = feedparser.parse(url)

        for entry in feed.entries[:10]:  # Top 10 Artikel
            article_id = hashlib.md5(
                (entry.get("id", "") + entry.get("title", "")).encode()
            ).hexdigest()

            if article_id in self.seen_hashes:
                continue  # Bereits verarbeitet

            # Freshness-Check
            published = entry.get("published_parsed")
            if published:
                age_minutes = (time.time() - time.mktime(published)) / 60
                if age_minutes > self.freshness_minutes:
                    continue  # Zu alt

            self.seen_hashes.add(article_id)
            if len(self.seen_hashes) > 10_000:
                # Trim: älteste entfernen
                self.seen_hashes.pop()

            headline = entry.get("title", "")
            matched = self._match_keywords(headline)

            if matched:
                markets = await self.market_manager.get_open_markets()
                relevant = self._match_markets(headline, markets, matched)
                await self._send_alert(source, headline, relevant, matched)

    def _match_keywords(self, headline: str) -> list[str]:
        """Gibt Liste der gematchten Kategorien zurück."""
        headline_lower = headline.lower()
        matched = []
        for category, keywords in KEYWORD_CATEGORIES.items():
            if any(kw in headline_lower for kw in keywords):
                matched.append(category)
        return matched

    def _match_markets(self, headline: str,
                        markets: list, categories: list) -> list:
        """Matcht Headline gegen offene Polymarket-Märkte."""
        headline_lower = headline.lower()
        relevant = []
        for market in markets:
            market_words = set(market.question.lower().split())
            headline_words = set(headline_lower.split())
            overlap = len(market_words & headline_words)
            if overlap >= 2:  # Mindestens 2 gemeinsame Wörter
                relevant.append({"market": market, "overlap": overlap})
        return sorted(relevant, key=lambda x: x["overlap"], reverse=True)[:3]

    async def _send_alert(self, source: str, headline: str,
                           markets: list, categories: list):
        markets_text = "\n".join([
            f"  • {m['market'].question[:60]}..."
            for m in markets
        ]) or "  (kein direkter Markt-Match)"

        await self.telegram.send(
            f"📰 *RSS NEWS* [Tier 1 — {source}]\n"
            f"_{headline}_\n\n"
            f"🏷️ Kategorien: {', '.join(categories)}\n"
            f"🎯 Relevante Märkte:\n{markets_text}\n"
            f"⏰ {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC"
        )
```

**Neue Datei:** `core/rss_monitor.py`

**Neue .env Variablen:**
```env
RSS_MONITOR_ENABLED=false      # Erst nach Test auf true setzen
RSS_POLL_INTERVAL_SECONDS=30   # Poll-Frequenz (30s = sicher für RSS)
RSS_FRESHNESS_MINUTES=10       # Artikel älter als 10 Min ignorieren
```

**Aufwand Server-CC:** ~3 Stunden

---

### Phase 2 — $20/Monat, diese Woche

#### TradingNews API Integration

**URL:** https://tradingnews.press  
**Kosten:** $20/Monat  
**Latenz:** sub-200ms (vs RSS: 30–120s)  
**Vorteil:** Speziell für Algo-Trading, WebSocket Streaming,
bereits strukturiert mit `urgency=breaking` Filter

**Warum besser als RSS:**
| Metrik | RSS (Phase 1B) | TradingNews |
|--------|---------------|------------|
| Latenz | 30–120s | <200ms |
| Strukturierung | HTML-Parse nötig | JSON strukturiert |
| Filter | Manuell (Keywords) | urgency=breaking |
| Quellen | 4 Feeds | Reuters+AP+AFP+Bloomberg |
| Kosten | Kostenlos | $20/Monat |

**WebSocket Integration:**
```python
# WebSocket Subscription:
ws = await websockets.connect(
    "wss://api.tradingnews.press/v1/stream",
    extra_headers={"Authorization": f"Bearer {TN_API_KEY}"}
)

# Subscribe:
await ws.send(json.dumps({
    "action": "subscribe",
    "filter": {
        "urgency": ["breaking", "flash"],
        "categories": ["geopolitics", "politics", "macro", "crypto", "sports"]
    }
}))

# Message Format (erwartet):
# {
#   "headline": "Trump announces Iran ceasefire deal",
#   "source": "Reuters",
#   "urgency": "breaking",
#   "category": "geopolitics",
#   "published_at": "2026-04-21T14:23:07Z"
# }
```

**Neue .env Variablen:**
```env
TRADINGNEWS_API_KEY=           # Nach Kauf eintragen
TRADINGNEWS_ENABLED=false      # Nach API-Key auf true
TRADINGNEWS_WS_URL=wss://api.tradingnews.press/v1/stream
```

**Aufwand Server-CC:** ~2 Stunden nach API-Key

---

### Phase 3 — Wenn ROI bewiesen (nach 30 Tagen Daten)

#### Option A: Glint.trade abonnieren ⭐ Empfohlen

Speziell für Polymarket gebaut. Aggregiert: X/Twitter (verifiziert),
News-Wire (Reuters, AP, Bloomberg), Telegram (Tier-System), OSINT.

- Bereits zu Polymarket-Märkten gematcht (kein eigenes Matching nötig)
- **Tier 1/2/3 Reliability-System** (löst Telegram-Schrott-Problem automatisch)
- WebSocket, sofort trading-ready
- Kein eigener Matching-Code nötig

**Tier-System (Glint.trade):**
- Tier 1: Reuters/AP/Bloomberg/offizielle Regierungsaccounts → Auto-Trade OK
- Tier 2: Verifizierte Journalisten, bekannte Crypto-Media → Alert only
- Tier 3: Unbekannte Quellen → ignorieren

#### Option B: polymarket-pipeline forken

**GitHub:** `brodyautomates/polymarket-pipeline` (MIT Lizenz, 231 Stars, Python)

- Nutzt Claude API (haben wir bereits!)
- Twitter optional, RSS als kostenloser Fallback
- ~1 Woche Implementierungsaufwand
- Vollständige Kontrolle über Logik
- Claude analysiert Headline und entscheidet ob Markt betroffen

#### Option C: Twitter X API ($100/Monat)

Nur wenn Phase 1+2 nicht ausreichen und ROI klar positiv.
Insider kommunizieren oft zuerst auf X — Sub-Minute Latenz.

**Entscheidungs-Matrix nach 30 Tagen:**
```
Phase 1+2 erkennbare Signale: > 5 profitable Alerts/Monat?
  → JA: Phase 3 Option A (Glint.trade)
  → NEIN: Phase 2 länger evaluieren
  
Manuelle Prüfung zeigt X-Signale vor Reuters/AP?
  → JA: Option C (Twitter API) evaluieren
  → NEIN: Option A reicht
```

---

## Source Reliability Framework

Inspiriert vom Glint.trade Tier-System:

### TIER 1 — Auto-Trade erlaubt
```
Reuters, AP, AFP, Bloomberg, BBC, Al Jazeera
@WhiteHouse, @StateDept, @POTUS (offizielle US-Gov-Accounts)
@SEC_News, @federalreserve, @ECB (verifizierte Behörden)
Offizielle UN/NATO Pressemitteilungen
```

### TIER 2 — Nur Telegram-Alert, kein Auto-Trade
```
Verifizierte Journalisten (Twitter Blue + >100k Follower)
CoinDesk, CoinTelegraph, The Block (Crypto-Media)
Polymarket Community (polymarket.com/blog, offizielle Updates)
Bekannte Telegram-Kanäle (e.g. Insider Paper mit Track-Record)
```

### TIER 3 — Ignorieren oder manuell prüfen
```
Unbekannte Telegram-Kanäle
Anonymous Twitter/X Accounts
Reddit, Discord, Forums
Unverifizierte "Breaking News" Quellen
```

**WICHTIG:** Kein Auto-Trade auf Tier 2/3 ohne manuellen Check.
Ein Tier-3-Signal das auf einen 3¢-Markt matched = manuell prüfen,
nicht automatisch handeln.

---

## Keyword-Matching Logik (Code-Referenz)

```python
def match_news_to_markets(headline: str,
                           open_markets: list) -> list:
    """
    Matcht News-Headline gegen offene Polymarket-Märkte.
    Gibt Liste betroffener Märkte zurück (sorted by relevance).
    """
    headline_lower = headline.lower()
    matched = []

    for market in open_markets:
        market_keywords = extract_keywords(market.question)
        if any(kw in headline_lower for kw in market_keywords):
            matched.append({
                "market": market,
                "relevance": calculate_relevance(
                    headline, market.question)
            })

    return sorted(matched,
                  key=lambda x: x["relevance"],
                  reverse=True)
```

---

## Telegram-Alert Format

```
⚡ NEWS SIGNAL [TIER 1]
📰 Reuters: "Trump announces Iran ceasefire deal"
🎯 Matched: "US x Iran permanent ceasefire"
💰 Aktuell: YES 21¢ → Ziel 85¢
⏰ 14:23:07 UTC
[Direkt handeln auf Polymarket →]
```

---

## STOP-CHECKs für Server-CC

### Phase 1A — Spike-Detektor
```bash
# 1. SPIKE_DETECTOR_ENABLED gesetzt?
grep SPIKE_DETECTOR /root/KongTradeBot/.env

# 2. Spike-Detektor in main.py als Task registriert?
grep "spike_detector\|SpikeDetector" /root/KongTradeBot/main.py

# 3. Test-Spike simulieren (manuell):
# Preis eines Testmarkts temporär erhöhen und Check abwarten

# 4. Telegram-Alert empfangen?
grep "\[SPIKE\]" /root/KongTradeBot/logs/bot_$(date +%Y-%m-%d).log | tail -5
```

### Phase 1B — RSS-Monitor
```bash
# 1. feedparser installiert?
pip show feedparser | grep Version

# 2. Reuters-Feed erreichbar?
python3 -c "
import feedparser
f = feedparser.parse('https://feeds.reuters.com/reuters/topNews')
print(f'OK: {len(f.entries)} Artikel, Top: {f.entries[0].title[:60]}')
"
# Erwartung: OK + Artikel-Titel

# 3. Keyword-Match-Test:
python3 -c "
from core.rss_monitor import RSSMonitor
r = RSSMonitor(None, None, None)
print(r._match_keywords('Trump announces Iran ceasefire deal'))
# Erwartung: ['IRAN', 'TRUMP']
"

# 4. Kein Duplikat-Alert bei gleichem Artikel?
grep "RSS.*Reuters.*zweimal\|DUPLICATE" /root/KongTradeBot/logs/bot_$(date +%Y-%m-%d).log
# Erwartung: leer (kein Duplikat)

# 5. Freshness-Filter: Artikel > 10 Min alt ignoriert?
grep "RSS.*SKIP.*alt\|freshness" /root/KongTradeBot/logs/bot_$(date +%Y-%m-%d).log | tail -3
```

### Phase 2 — TradingNews API
```bash
# 1. API-Key vorhanden?
grep TRADINGNEWS_API_KEY /root/KongTradeBot/.env | grep -v "^$"

# 2. WS-Verbindung OK?
python3 -c "
import asyncio, websockets, json
async def test():
    url = 'wss://api.tradingnews.press/v1/stream'
    headers = {'Authorization': 'Bearer ' + os.getenv('TRADINGNEWS_API_KEY')}
    async with websockets.connect(url, extra_headers=headers) as ws:
        print('Verbunden!')
        msg = await asyncio.wait_for(ws.recv(), timeout=10)
        print(f'Erste Nachricht: {msg[:100]}')
asyncio.run(test())
"

# 3. Latenz messen:
grep "TradingNews.*Latenz\|TN.*ms" /root/KongTradeBot/logs/bot_$(date +%Y-%m-%d).log | tail -5
# Ziel: < 200ms
```

---

## Deployment-Reihenfolge

```
1. Phase 1A: Spike-Detektor (core/spike_detector.py)
   → Sofort morgen, ~2h Server-CC, kostenlos
   → SPIKE_DETECTOR_ENABLED=true

2. Phase 1B: RSS-Monitor (core/rss_monitor.py)
   → Übermorgen, ~3h Server-CC, kostenlos
   → RSS_MONITOR_ENABLED=true

3. 7 Tage Beobachtung:
   → Wie viele echte Alerts? Wie viele False Positives?
   → False-Positive-Rate > 30%? → Keyword-Mapping verfeinern

4. Phase 2: TradingNews API ($20/Monat)
   → API-Key kaufen (tradingnews.press)
   → ~2h Integration, sub-200ms Latenz
   → TRADINGNEWS_ENABLED=true

5. 30 Tage ROI-Analyse:
   → Alerts die zu rechtzeitigen Einsteigen führten?
   → Ja → Phase 3 evaluieren (Glint.trade oder polymarket-pipeline)
   → Nein → Phase 1+2 weiter optimieren
```

**Commit-Message:**
```
feat(monitor): T-NEWS Phase 1A+1B — Spike-Detektor + RSS-Monitor

Phase 1A: WebSocket Preis-Spike-Detektor (15% in 60s, kein Auto-Trade)
Phase 1B: RSS-Monitor Reuters/AP/BBC/Al Jazeera (30s Poll, Keyword-Match)
Tier 1/2/3 Source Reliability Framework
TradingNews API Phase 2 vorbereitet (.env Vars)
```

---

## Erwartetes Ergebnis

| Szenario | Einstieg | Mit T-NEWS |
|----------|----------|-----------|
| Ohne T-NEWS | 30–50¢ (nach Spike) | — |
| Phase 1A (Spike-Alert) | 20–35¢ (manuell schnell) | −30% vs. ohne |
| Phase 1B (RSS <120s) | 10–25¢ (kurz nach News) | −50% vs. ohne |
| Phase 2 (TradingNews <200ms) | 5–15¢ (fast gleichzeitig) | −70% vs. ohne |
| Phase 3 (Glint/Twitter) | 3–10¢ (vor/mit Insidern) | −90% vs. ohne |

---

## Referenzen

| Quelle | URL | Relevanz |
|--------|-----|---------|
| TradingNews API | https://tradingnews.press | Phase 2 — $20/Monat |
| polymarket-pipeline | github.com/brodyautomates/polymarket-pipeline | Phase 3 Option B |
| Glint.trade | glint.trade | Phase 3 Option A |
| feedparser Python | pypi.org/project/feedparser | Phase 1B |
| T-WS Prompt | prompts/t_ws_websocket_wallet_monitor.md | Voraussetzung |
| T-M-NEW Prompt | prompts/t_m_new_anomaly_detector.md | Synergie |
