# T-GLINT: Glint.trade Integration Design
_Erstellt: 2026-04-21 | Status: DESIGN — kein Code nötig bis Glint API verfügbar_

---

## API-Status (Stand 2026-04-21)

**Glint hat KEINE öffentliche API.**

Aus der offiziellen Dokumentation (`docs.glint.trade`):
> "Glint's API is under development."

| Kanal | Status | Für uns nutzbar? |
|-------|--------|-----------------|
| REST API | ❌ "Coming Soon" — kein Datum | Nein |
| WebSocket | ❌ Nur intern (Feed auto-update) | Nein |
| Discord Webhook | ✅ User-konfigurierbar (eigene Server) | Ja (Discord-Pfad) |
| Telegram Bot | ✅ `@GlintTradeBot` — Alerts, `/settings` | Ja (Telegram-Pfad) |
| Programmatic | ❌ Keine Bot-Commands für externe Integration | Nein |

---

## Einziger nutzbarer Integrationspfad: Telegram Listener

```
Glint erkennt Signal
       │
  Telegram Alert → @GlintTradeBot → Onurs Telegram
                                         │
                              ┌──────────┴──────────┐
                              │                     │
                         Manuell              KongTradeBot
                        (sofort)           Telegram Listener
                                           (zukünftig, Phase 3)
                                                    │
                                            Signal Parser
                                                    │
                                        Keyword → Market Match
                                                    │
                                        Auto-Trade (Tier 1)
                                        Alert (Tier 2/3)
```

---

## Phase 1 — Manuell (JETZT, 0 Code)

**Setup:** Glint Telegram Alerts einrichten (→ `docs/T_NEWS_SETUP_ANLEITUNG.md`)

Onur liest Alerts manuell → manuelle Trades via Polymarket-App.

**Keyword-Sets konfiguriert in:** `docs/T_NEWS_SETUP_ANLEITUNG.md`

---

## Phase 2 — Telegram Listener (T-NEWS Phase 3)

### Voraussetzungen
1. Glint Alert an Onurs persönliches Telegram konfiguriert
2. KongTradeBot als MTProto-Client (nicht Bot-API) implementiert
3. Bot liest ALLE eingehenden Nachrichten von @GlintTradeBot

### Glint Alert-Format (Beispiel)
```
🚨 CRITICAL SIGNAL
📌 Iran nuclear ceasefire talks confirmed
💹 Matched: "Will Iran agree to ceasefire by June?"
   Current: YES 23¢ | NO 77¢
📊 Impact: CRITICAL | Category: Geopolitics
🔗 Source: Reuters @reuters (verified)
⏰ 14:32 UTC
[View on Glint →]
```

### Signal Parser Design (`core/glint_parser.py`)

```python
import re
from dataclasses import dataclass

@dataclass
class GlintSignal:
    impact: str          # CRITICAL / HIGH / MEDIUM
    category: str        # Geopolitics, Politics, Crypto, ...
    headline: str
    market_text: str     # Matched Polymarket question
    yes_price: float     # Current YES odds (¢)
    no_price: float      # Current NO odds (¢)
    source: str
    timestamp: str
    tier: int            # 1/2/3 basierend auf Impact + Category

GLINT_PATTERNS = {
    "impact":   r"Impact: (CRITICAL|HIGH|MEDIUM)",
    "category": r"Category: (\w+)",
    "matched":  r'Matched: "(.+?)"',
    "yes":      r"YES (\d+)¢",
    "no":       r"NO (\d+)¢",
    "source":   r"Source: (.+?) \(",
}

def parse_glint_alert(text: str) -> GlintSignal | None:
    """Parse incoming Glint Telegram alert into structured signal."""
    data = {}
    for key, pattern in GLINT_PATTERNS.items():
        match = re.search(pattern, text)
        if not match:
            return None
        data[key] = match.group(1)
    
    tier = _classify_tier(data["impact"], data["category"])
    return GlintSignal(
        impact=data["impact"],
        category=data["category"],
        headline=text.split("\n")[1] if "\n" in text else "",
        market_text=data["matched"],
        yes_price=float(data["yes"]) / 100,
        no_price=float(data["no"]) / 100,
        source=data["source"],
        timestamp=data.get("timestamp", ""),
        tier=tier,
    )

def _classify_tier(impact: str, category: str) -> int:
    """Tier 1 = Auto-Trade, Tier 2/3 = Alert only."""
    if impact == "CRITICAL" and category == "Geopolitics":
        return 1  # 0% Polymarket Fee + CRITICAL
    if impact in ("CRITICAL", "HIGH") and category in ("Politics", "Finance"):
        return 2
    return 3
```

### Tier-Logik

| Tier | Bedingung | Aktion |
|------|-----------|--------|
| **1** | CRITICAL + Geopolitics (0% Fee) | Auto-Trade wenn Market-Match gefunden |
| **2** | CRITICAL/HIGH + Politics/Finance | Telegram-Alert an Onur, kein Auto-Trade |
| **3** | Alles andere | Nur Log |

### Market Matching (`core/glint_matcher.py`)

```python
async def find_polymarket_match(signal: GlintSignal) -> str | None:
    """
    Sucht auf Polymarket nach einem passenden offenen Markt.
    Glint liefert Market-Text → wir suchen via search-API.
    """
    # Polymarket Gamma API search
    url = f"https://gamma-api.polymarket.com/markets?search={quote(signal.market_text[:50])}"
    markets = await fetch_json(url)
    
    for market in markets:
        if market["active"] and market["volume"] > 20000:
            return market["conditionId"]
    return None
```

### Telegram-Listener Integration in main.py

```python
# In main.py async tasks:
async def glint_listener_task():
    """MTProto client — liest Glint-Alerts aus Telegram."""
    from telethon import TelegramClient, events
    
    client = TelegramClient("glint_session", API_ID, API_HASH)
    await client.start()
    
    @client.on(events.NewMessage(from_users="GlintTradeBot"))
    async def handler(event):
        signal = parse_glint_alert(event.raw_text)
        if signal and signal.tier == 1:
            market_id = await find_polymarket_match(signal)
            if market_id:
                await process_glint_signal(signal, market_id)
        elif signal and signal.tier == 2:
            await send_telegram_alert(
                f"⚡ GLINT {signal.impact}: {signal.headline}\n"
                f"Market: {signal.market_text}"
            )
    
    await client.run_until_disconnected()
```

### .env Variablen (Phase 2)

```
GLINT_LISTENER_ENABLED=false      # true wenn Phase 2 aktiv
TELEGRAM_API_ID=your_api_id       # von my.telegram.org
TELEGRAM_API_HASH=your_api_hash
GLINT_AUTO_TRADE_TIER=1           # nur Tier 1 auto-traden
GLINT_MAX_TRADE_USD=10            # max $10 pro Glint-Signal
```

---

## Phase 3 — Wenn Glint API verfügbar

Sobald Glint "API (Coming Soon)" released:

**Erwartetes API-Design** (basierend auf Glint Features):
```
GET /api/signals?impact=critical&category=geopolitics&limit=50
GET /api/whales?min_size=10000&new_wallet=true
GET /api/markets/{market_id}/signals
POST /api/alerts (Create alert programmatisch)
WebSocket: wss://api.glint.trade/v1/stream
```

**Dann:** Direkte WebSocket-Integration statt Telegram-Umweg.

---

## Discord Webhook Alternative

Falls du Discord nutzt (Backup zu Telegram):

```
Glint → Alerts → Delivery: Discord Webhook
Discord Server Settings → Integrations → Webhooks → URL kopieren
Glint Alert Settings → Webhook URL einfügen
```

**Für Bot-Integration via Discord:**
```python
# discord.py oder direkte Webhook-Listener
# Ähnliche Parser-Logik wie Telegram
```

---

## Whale Tracker — Manueller Workflow (kein API nötig)

Glint Whale Tracker zeigt:
- $10K+ Trades in Echtzeit
- NEW Badge = Wallet <7 Tage (T-M-NEW Synergie!)
- Cluster-Buying (3+ Wallets gleiche Position)

**Workflow bis Phase 2:**
1. Glint → Whales → Filter: NEW + >$10K
2. Wallet-Adresse notieren
3. Manuell in T-M-NEW Anomaly-Detector einpflegen ODER
4. Direkt via Polymarket-App kopieren

---

## Empfehlung

| Phase | Wann | Aufwand |
|-------|------|---------|
| **Phase 1** (manuell) | JETZT | 0 |
| **Phase 2** (Telegram Listener) | Nach T-WS + T-M-NEW | ~4h |
| **Phase 3** (API) | Wenn Glint API released | ~2h Update |

**Priorität: Phase 2 erst nach T-WS (WebSocket Monitor) implementieren.**
T-WS liefert die MTProto-Telegram-Infrastruktur die Phase 2 mitnutzen kann.

---

_Stand: 2026-04-21 | Glint API: "Coming Soon" ohne Datum_
_Nächste Prüfung: docs.glint.trade/api bei T-D109 (2026-05-19)_
