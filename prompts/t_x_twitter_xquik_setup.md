# T-X-TWITTER: Xquik Setup — Server-CC Prompt
_Erstellt: 2026-04-21 | Quelle: docs.xquik.com (vollständig gelesen)_

---

## Xquik Pricing — Kritische Einschränkung

| Plan | Preis | Tweets/Mo | **Monitore** |
|------|-------|-----------|-------------|
| Pay-as-you-go | $0.00015/Call | unbegrenzt | ⚠ REST-Polling only |
| **Starter** | **$20/Mo** | 140.000 | **1 Account** |
| Pro | $99/Mo | 770.000 | mehr (unklar) |
| Business | $199/Mo | 1.670.000 | noch mehr |

**WICHTIG:** Starter-Plan = **nur 1 Account** in Echtzeit-Streaming.
Zweiter Monitor → `402 Payment Required`.
Für 6 Accounts (Polymarket + NickTimiraos + Elon + Trump + Glint + spydenuevo)
→ **Pro-Plan $99/Mo nötig** ODER REST-Polling statt Streaming.

**Empfehlung: REST-Polling-Hybrid** (1 Streaming-Monitor + REST für Rest)
- 1 Monitor (Starter $20) → @NickTimiraos (höchste Priorität, Fed-Edge)
- REST-Polling alle 60s für andere Accounts (kostet ~$2/Mo extra)

---

## Setup — 3 Schritte (Onur macht Schritt 1, Server-CC macht 2+3)

### Schritt 1 — Account + Subscription (Onur, 5 Min)

1. Gehe zu: `https://xquik.com`
2. Sign up mit E-Mail → Magic Link kommt → klicken
3. Dashboard → **Billing** → Starter Plan $20/Mo abonnieren
4. Dashboard → **API Keys** → "New Key" → kopieren (nur einmal sichtbar!)
   - Format: `xq_xxxxxxxxxxxxxxxxxxxx`
5. API-Key in `.env` auf Server eintragen:
   ```
   XQUIK_API_KEY=xq_xxxxxxxxxxxxxxxxxxxx
   XQUIK_ENABLED=true
   ```

### Schritt 2 — Monitor + Webhook einrichten (Server-CC)

**NickTimiraos als ersten (und einzigen Echtzeit-) Monitor:**

```bash
# Monitor erstellen
curl -s -X POST https://xquik.com/api/v1/monitors \
  -H "x-api-key: $XQUIK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "NickTimiraos",
    "eventTypes": ["tweet.new", "tweet.quote"]
  }' | python3 -m json.tool

# Webhook registrieren (HTTPS-Endpoint auf unserem Server)
curl -s -X POST https://xquik.com/api/v1/webhooks \
  -H "x-api-key: $XQUIK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://DEINE-SERVER-IP/webhook/x-alert",
    "eventTypes": ["tweet.new", "tweet.quote"]
  }' | python3 -m json.tool

# WICHTIG: "secret" aus Response speichern — nur einmal sichtbar!
# In .env eintragen: XQUIK_WEBHOOK_SECRET=a1b2c3d4...
```

**Account testen:**
```bash
curl -s https://xquik.com/api/v1/account \
  -H "x-api-key: $XQUIK_API_KEY" | python3 -m json.tool
# → monitorsAllowed: 1, monitorsUsed: 1
```

### Schritt 3 — Webhook-Endpoint in dashboard.py / main.py (Server-CC)

```python
# In dashboard.py (Flask) ODER neues core/x_monitor_webhook.py

import hmac, hashlib, json
from flask import request, jsonify

XQUIK_SECRET = os.getenv("XQUIK_WEBHOOK_SECRET", "")

@app.route('/webhook/x-alert', methods=['POST'])
def x_webhook():
    """Empfängt Xquik Tweet-Events für NickTimiraos."""
    # HMAC Verifikation
    sig_header = request.headers.get('X-Xquik-Signature', '')
    expected = 'sha256=' + hmac.new(
        XQUIK_SECRET.encode(),
        request.get_data(),
        hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(sig_header, expected):
        return jsonify({"error": "invalid signature"}), 401

    event = request.json
    tweet_text = event.get('data', {}).get('text', '')
    username = event.get('username', '')
    event_type = event.get('eventType', '')

    # Nur tweet.new und tweet.quote verarbeiten
    if event_type not in ('tweet.new', 'tweet.quote'):
        return jsonify({"ok": True}), 200

    # Keyword-Check für Polymarket-Relevanz
    keywords_fed = ['fomc', 'rate cut', 'rate hike', 'fed ', 'powell', 'inflation']
    keywords_geo = ['iran', 'ceasefire', 'ukraine', 'tariff', 'trump']

    text_lower = tweet_text.lower()
    matched_fed = any(k in text_lower for k in keywords_fed)
    matched_geo = any(k in text_lower for k in keywords_geo)

    if matched_fed or matched_geo:
        category = 'FED' if matched_fed else 'GEO'
        alert_msg = (
            f"⚡ X-ALERT [{category}] @{username}\n"
            f"{tweet_text[:200]}\n"
            f"https://x.com/{username}"
        )
        # Telegram senden (nutzt bestehende send_telegram_alert Funktion)
        import asyncio
        asyncio.run(send_telegram_alert(alert_msg))

    return jsonify({"ok": True}), 200
```

---

## REST-Polling für weitere Accounts (Ergänzung zu Streaming)

Da Starter nur 1 Monitor hat, andere Accounts via REST-Polling:

```python
# core/x_poller.py — 60s-Polling für sekundäre Accounts

import asyncio, httpx, os
from datetime import datetime, timezone

XQUIK_API_KEY = os.getenv("XQUIK_API_KEY")
POLL_ACCOUNTS = ["Polymarket", "glintintel", "spydenuevo"]
SEEN_TWEET_IDS = set()

async def poll_account(username: str, client: httpx.AsyncClient) -> list:
    """Holt neueste Tweets eines Accounts via REST."""
    resp = await client.get(
        f"https://xquik.com/api/v1/timeline/{username}",
        headers={"x-api-key": XQUIK_API_KEY},
        params={"limit": 5}
    )
    if resp.status_code != 200:
        return []
    return resp.json().get("tweets", [])

async def x_poll_loop():
    """60s-Polling für sekundäre Accounts."""
    async with httpx.AsyncClient() as client:
        while True:
            for username in POLL_ACCOUNTS:
                try:
                    tweets = await poll_account(username, client)
                    for tweet in tweets:
                        if tweet["id"] in SEEN_TWEET_IDS:
                            continue
                        SEEN_TWEET_IDS.add(tweet["id"])
                        text = tweet.get("text", "")
                        if "polymarket" in text.lower():
                            await send_telegram_alert(
                                f"📊 X: @{username}\n{text[:200]}"
                            )
                except Exception as e:
                    pass  # Log aber kein Crash
            await asyncio.sleep(60)
```

---

## .env Variablen

```
# X-Twitter Monitor (Xquik)
XQUIK_ENABLED=false                    # true nach Account-Setup
XQUIK_API_KEY=xq_xxxxxxxxxxxxxxxxxxxx
XQUIK_WEBHOOK_SECRET=                  # aus Webhook-Response
XQUIK_MONITOR_PRIMARY=NickTimiraos     # Echtzeit-Monitor (1 erlaubt)
XQUIK_POLL_ACCOUNTS=Polymarket,glintintel,spydenuevo  # 60s-Polling
X_ALERT_KEYWORD_FILTER=true            # nur relevante Tweets weiterleiten
```

---

## Kosten-Kalkulation (Starter $20/Mo)

| Aktion | Kosten |
|--------|--------|
| Subscription | $20.00/Mo |
| 1 Echtzeit-Monitor (NickTimiraos) | inklusive |
| REST-Polling 3 Accounts × 48 Checks/Tag × 30 Tage = 4.320 Calls | ~$0.65 |
| **Total** | **~$20.65/Mo** |

**ROI-Schwelle:** 1 guter Fed-Trade via NickTimiraos-Alert = mind. $5 Gewinn → ROI positiv nach ~4 Monaten.

---

## Webhook Event-Format (Beispiel NickTimiraos Tweet)

```json
{
  "eventType": "tweet.new",
  "username": "NickTimiraos",
  "data": {
    "id": "1893456789012345678",
    "text": "Fed officials signal they are in no rush to cut rates, per sources",
    "author": {
      "id": "216471928",
      "userName": "NickTimiraos",
      "name": "Nick Timiraos"
    },
    "isRetweet": false,
    "isReply": false,
    "isQuote": false,
    "createdAt": "2026-04-21T14:22:00.000Z"
  }
}
```

→ Keyword "rate" matched → Telegram Alert → Onur checkt FOMC-Märkte

---

## Tier-Priorisierung Accounts

| Priorität | Account | Warum | Plan |
|-----------|---------|-------|------|
| **Tier 1** | `@NickTimiraos` | Fed/FOMC-Reporter WSJ — sofortiger Markt-Impact | **Streaming** (1 Monitor) |
| Tier 2 | `@Polymarket` | Neue Märkte, Ankündigungen | REST-Polling 60s |
| Tier 2 | `@glintintel` | Glint-Updates, neue Features | REST-Polling 60s |
| Tier 3 | `@spydenuevo` | neobrother, Weather-Strategien | REST-Polling 60s |
| Tier 3 | `@realDonaldTrump` | Trump-Posts → Policy-Trades | REST-Polling 60s |

**Upgrade-Schwelle:** Wenn NickTimiraos-Edge nachweislich >$50/Mo Gewinn bringt → Pro $99/Mo für 5+ Echtzeit-Monitore.

---

## Retry-Policy (automatisch durch Xquik)

| Versuch | Verzögerung |
|---------|-------------|
| 1 | 1 Sekunde |
| 2 | 2 Sekunden |
| 3 | 4 Sekunden |
| 4 | 8 Sekunden |
| 5 | 16 Sekunden |

Nach 5 Fehlern: Status `exhausted`. Check via: `GET /api/v1/webhooks/{id}/deliveries`

---

_Stand: 2026-04-21 | Quelle: docs.xquik.com (Quickstart + Webhooks Overview)_
_Nächste Prüfung: Nach 30 Tagen — Hat NickTimiraos-Monitor messbare Trades geliefert?_
