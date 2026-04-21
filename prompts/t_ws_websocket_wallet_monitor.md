# T-WS: WebSocket WalletMonitor — Echtzeit statt Poll
_Erstellt: 2026-04-20 | Aufwand: ~1 Woche | Status: DESIGN READY_
_Voraussetzung: T-M08 Phase 3+ vollständig deployed_

---

## Problem

**Aktuell:** WalletMonitor pollt alle 10 Sekunden die Data-API.

```
Whale kauft bei 3¢ → 10s Poll-Delay → Bot sieht Signal → Processing ~3s → Order → 13-15s Latenz
```

Bei Breaking-News-Events (Iran-Ceasefire, Maduro-Capture):
- Insider kaufen bei 3 Cent
- Preis springt in **< 30 Sekunden** auf 50+ Cent
- Mit 13–15s Latenz: wir kaufen bei 30–50 Cent statt 3–10 Cent

**WebSocket:**
```
Whale kauft bei 3¢ → WS-Push < 100ms → Bot sieht Signal → Processing ~2s → Order → 2-3s Latenz
```

Besonders kritisch für den **Anomalie-Detektor (T-M-NEW):**
Ein Signal bei 3 Cent hat 5–10s Zeitfenster bevor die Crowd reagiert.
Mit Poll: zu spät. Mit WebSocket: realistisch.

---

## Polymarket WebSocket Infrastruktur

### Market Channel (Haupt-Feed, kein Auth)

```
wss://ws-subscriptions-clob.polymarket.com/ws/market
```

- Alle Trades + Orderbook-Updates in Echtzeit
- Kein Authentication erforderlich
- Heartbeat: alle 10 Sekunden PING senden (sonst Disconnect)
- Subscribe-Format: JSON mit `type`, `channel`, `auth` (optional), `markets` oder `assets_ids`

### RTDS (Real-Time Data Stream, Auth required)

```
wss://ws-live-data.polymarket.com
```

- Ultra-niedrige Latenz (< 50ms)
- Für Market Maker gedacht
- Auth erforderlich (API Key + Signature)
- **Phase 2 — später evaluieren**

### Server-Geografie

- Polymarket CLOB: AWS eu-west-2 (London)
- Unser Server: Hetzner Helsinki
- Netzwerk-Latenz HEL→LON: **~30ms** (sehr gut)
- Vergleich: USA-Server → LON: 80–120ms

---

## Implementierungsplan

### Phase 1 — Market WebSocket (~1 Woche, Server-CC)

#### VORHER (aktueller Poll-Code in core/wallet_monitor.py):

```python
# Aktueller Code (vereinfacht):
async def run(self):
    while True:
        await asyncio.sleep(self.poll_interval)  # 10s
        for wallet in self.target_wallets:
            trades = await self._fetch_activity(wallet)
            for trade in trades:
                if trade["tx_hash"] not in self.seen_hashes:
                    self.seen_hashes.add(trade["tx_hash"])
                    await self._emit_signal(trade)
```

#### NACHHER (WebSocket in core/wallet_monitor.py):

```python
import websockets
import json
import asyncio
import os

WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

class WalletMonitor:
    def __init__(self, ...):
        ...
        self.ws_mode = os.getenv("WALLET_MONITOR_MODE", "poll") == "websocket"
        self.ws_heartbeat_interval = int(os.getenv("WS_HEARTBEAT_INTERVAL", "10"))
        self.ws_reconnect_retries = int(os.getenv("WS_RECONNECT_MAX_RETRIES", "5"))
        self.ws_fallback_interval = int(os.getenv("WS_FALLBACK_POLL_INTERVAL", "30"))

    async def run(self):
        if self.ws_mode:
            await self._run_websocket()
        else:
            await self._run_poll()  # Alter Code bleibt als Fallback

    async def _run_websocket(self):
        retries = 0
        while True:
            try:
                await self._websocket_session()
                retries = 0  # Reset bei erfolgreichem Reconnect
            except Exception as e:
                retries += 1
                if retries > self.ws_reconnect_retries:
                    # Fallback auf Poll-Modus
                    logger.warning(f"[WS] {retries} Retries erschöpft → Fallback auf Poll")
                    await self._run_poll_once()
                wait = min(2 ** retries, 60)  # Exponential Backoff, max 60s
                logger.warning(f"[WS] Reconnect in {wait}s...")
                await asyncio.sleep(wait)

    async def _websocket_session(self):
        async with websockets.connect(
            WS_URL,
            ping_interval=None,     # Eigenes Heartbeat-Management
            ping_timeout=None,
            close_timeout=5
        ) as ws:
            logger.info(f"[WS] Verbunden mit {WS_URL}")

            # Subscribe auf Live-Activity für unsere Wallets
            subscribe_msg = {
                "type": "subscribe",
                "channel": "live_activity_by_wallet",
                "wallets": self.target_wallets  # Liste der 42-Zeichen-Adressen
            }
            await ws.send(json.dumps(subscribe_msg))
            logger.info(f"[WS] Subscribed auf {len(self.target_wallets)} Wallets")

            # Heartbeat Task parallel laufen lassen
            heartbeat_task = asyncio.create_task(
                self._heartbeat(ws, self.ws_heartbeat_interval)
            )

            try:
                async for raw_message in ws:
                    await self._process_ws_message(raw_message)
            finally:
                heartbeat_task.cancel()

    async def _heartbeat(self, ws, interval: int):
        """Hält die WebSocket-Verbindung mit regelmäßigen PINGs lebendig."""
        while True:
            await asyncio.sleep(interval)
            try:
                await ws.send(json.dumps({"type": "ping"}))
            except Exception:
                break  # Verbindung tot → outer loop reconnectet

    async def _process_ws_message(self, raw: str):
        """Verarbeitet eingehende WS-Nachricht als TradeSignal."""
        try:
            msg = json.loads(raw)
        except Exception:
            return

        msg_type = msg.get("type", "")

        if msg_type == "pong":
            return  # Heartbeat-Antwort, ignorieren

        if msg_type in ("trade", "activity", "live_trade"):
            # Format variiert — robust parsen
            trade_data = msg.get("data") or msg
            tx_hash = (trade_data.get("transactionHash") or
                       trade_data.get("tx_hash") or
                       trade_data.get("id", ""))

            if not tx_hash or tx_hash in self.seen_hashes:
                return  # Duplikat

            self.seen_hashes.add(tx_hash)
            if len(self.seen_hashes) > 10_000:
                # FIFO-Trim (wie bisheriger Code)
                oldest = next(iter(self.seen_hashes))
                self.seen_hashes.discard(oldest)

            # TradeSignal emittieren — gleiche Logik wie Poll
            await self._emit_signal_from_ws(trade_data)
            logger.info(f"[WS] Signal empfangen: {tx_hash[:16]}... "
                        f"(Latenz ~{int((time.time() - trade_data.get('timestamp', time.time())) * 1000)}ms)")

    async def _run_poll_once(self):
        """Einmaliger Poll-Durchlauf als Fallback wenn WS nicht verfügbar."""
        for wallet in self.target_wallets:
            trades = await self._fetch_activity(wallet)
            for trade in trades:
                tx_hash = trade.get("transactionHash", "")
                if tx_hash and tx_hash not in self.seen_hashes:
                    self.seen_hashes.add(tx_hash)
                    await self._emit_signal(trade)
        await asyncio.sleep(self.ws_fallback_interval)
```

---

## Subscribe-Format Details

Polymarket WS unterstützt mehrere Channel-Typen:

```json
// Option A: Wallet-spezifischer Feed (bevorzugt)
{
    "type": "subscribe",
    "channel": "live_activity_by_wallet",
    "wallets": ["0x019782...", "0xefbc5f...", "0x7177a7..."]
}

// Option B: Markt-Feed (für Anomalie-Detektor)
{
    "type": "subscribe",
    "channel": "market",
    "assets_ids": ["71321...", "48291..."]  // Token IDs der Märkte
}

// Option C: Globaler Activity-Feed (alle Trades, hohe Volume)
{
    "type": "subscribe",
    "channel": "live_activity"
    // Kein Filter — ALLES empfangen, dann lokal filtern
}
```

**Empfehlung:** Option A für WalletMonitor, Option C für AnomalyDetector.

---

## .env Variablen

```env
# WebSocket Konfiguration
WALLET_MONITOR_MODE=websocket      # "websocket" | "poll" (default: poll)
WS_RECONNECT_MAX_RETRIES=5         # Max Retries vor Fallback auf Poll
WS_HEARTBEAT_INTERVAL=10           # Sekunden zwischen PINGs (Polymarket trennt nach 10s ohne)
WS_FALLBACK_POLL_INTERVAL=30       # Poll-Intervall wenn WS ausgefallen (Sekunden)
WS_LOG_LATENCY=true                # Latenz pro Signal loggen (für Monitoring)
```

---

## Fallback-Strategie

```
                   ┌─────────────────────────────────────────┐
                   │          WalletMonitor.run()            │
                   └────────────────┬────────────────────────┘
                                    │
                    WALLET_MONITOR_MODE=websocket?
                   ┌────────────────┴────────────────────────┐
                   │ YES                                 NO   │
                   ▼                                     ▼    │
        _run_websocket()                    _run_poll() (alter Code)
                   │
        WS-Verbindung OK?
        ┌───────────┴─────────────┐
        │ OK                  FAIL│
        ▼                         ▼
  Normal WS-Loop          Retry mit Backoff
                                  │
                     Retries > MAX_RETRIES?
                          │
                          ▼
                    _run_poll_once()
                    (30s Interval als Fallback)
                    + Telegram-Alert: "WS ausgefallen, Poll-Fallback aktiv"
```

---

## Anomalie-Detektor Integration (T-M-NEW)

T-M-NEW scannt ALLE Trades auf Insider-Muster, nicht nur unsere Wallets.
Mit WebSocket und Option C (globaler Feed) kann der AnomalyDetector
**alle** Polymarket-Trades in Echtzeit sehen:

```python
# Erweiterter Subscribe für AnomalyDetector:
await ws.send(json.dumps({
    "type": "subscribe",
    "channel": "live_activity"  # Alles
}))

# Dann lokal filtern:
async def _process_ws_message_anomaly(self, raw: str):
    msg = json.loads(raw)
    trade = msg.get("data") or msg
    amount = float(trade.get("usdcSize", 0))
    price = float(trade.get("price", 1.0))
    if amount >= 50_000 and price < 0.15:
        # Potentielles Insider-Signal → AnomalyDetector
        await self.anomaly_detector.process_trade(trade)
```

**Synergie T-WS + T-M-NEW:**
- T-WS: 1-3s Latenz statt 10-15s
- T-M-NEW: Erkennt Insider in < 5s statt 30+ Minuten
- Kombiniert: Wir kaufen bei 5–10 Cent statt 30–50 Cent

---

## STOP-CHECKs für Server-CC

```bash
# 1. websockets Package installiert?
pip show websockets | grep Version
# Erwartung: Version 12.0+

# 2. WS-Verbindung funktioniert?
python3 -c "
import asyncio, websockets, json

async def test():
    url = 'wss://ws-subscriptions-clob.polymarket.com/ws/market'
    async with websockets.connect(url, open_timeout=10) as ws:
        print('Verbunden!')
        await ws.send(json.dumps({'type': 'ping'}))
        msg = await asyncio.wait_for(ws.recv(), timeout=5)
        print(f'Antwort: {msg[:100]}')

asyncio.run(test())
"
# Erwartung: "Verbunden!" + Pong-Antwort

# 3. Subscribe auf Test-Wallet funktioniert?
python3 -c "
import asyncio, websockets, json

async def test():
    url = 'wss://ws-subscriptions-clob.polymarket.com/ws/market'
    async with websockets.connect(url) as ws:
        await ws.send(json.dumps({
            'type': 'subscribe',
            'channel': 'live_activity_by_wallet',
            'wallets': ['0x019782cab5d844f02bafb71f512758be78579f3c']  # majorexploiter
        }))
        print('Subscribed! Warte 15s auf Nachricht...')
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=15)
            print(f'Erster Trade: {msg[:150]}')
        except asyncio.TimeoutError:
            print('Kein Trade in 15s (normal wenn Wallet gerade inaktiv)')

asyncio.run(test())
"

# 4. Latenz messen (nach 24h Betrieb):
grep "\[WS\] Signal empfangen" /root/KongTradeBot/logs/bot_$(date +%Y-%m-%d).log | \
    grep -oP 'Latenz ~\K[0-9]+' | awk '{sum+=$1; count++} END {print "Avg Latenz:", sum/count, "ms"}'
# Ziel: Avg < 3000ms (3 Sekunden)

# 5. Reconnect funktioniert?
# Temporär WS-URL falsch setzen, dann zurück:
grep "WS.*Reconnect\|WS.*Fallback" /root/KongTradeBot/logs/bot_$(date +%Y-%m-%d).log | tail -5
# Erwartung: Reconnect-Logs sichtbar nach Connection-Reset
```

---

## Erwartetes Ergebnis

| Metrik | Poll (aktuell) | WebSocket (nach T-WS) |
|--------|---------------|----------------------|
| Signal-Latenz | 10–15 Sekunden | 1–3 Sekunden |
| Latenz bei Breaking News | 10–15s (oft zu spät) | 1–3s (oft noch günstig) |
| API-Calls pro Stunde | ~3.600 (360 Wallets × 10/min) | ~360 (Heartbeat only) |
| Rate-Limit-Risiko | Mittel | Sehr niedrig |
| Anomalie-Erkennung (T-M-NEW) | 5–30 Min nach Insider-Kauf | 1–5s nach Insider-Kauf |
| Verbindungs-Robustheit | Sehr hoch (HTTP ist robust) | Hoch (mit Fallback auf Poll) |
| Implementation-Aufwand | — | ~1 Woche |

---

## Deployment-Reihenfolge

```
1. pip install websockets>=12.0 (requirements.txt ergänzen)
2. core/wallet_monitor.py: _run_websocket() + _heartbeat() + _process_ws_message()
3. .env: WALLET_MONITOR_MODE=poll BELASSEN (erst testen)
4. Test in DRY_RUN mit WALLET_MONITOR_MODE=websocket
5. 48h Beobachtung: Latenz-Logs prüfen, Reconnects prüfen
6. Wenn stabil: WALLET_MONITOR_MODE=websocket permanent setzen
7. T-M-NEW Integration: AnomalyDetector auf WS-Feed aufschalten
```

**Commit-Message:**
```
feat(monitor): T-WS WebSocket WalletMonitor — 10s Poll → 1-3s Echtzeit

Phase 1: Market-WebSocket mit Wallet-Feed
- live_activity_by_wallet Subscribe für Target-Wallets
- Heartbeat alle 10s (Polymarket-Requirement)
- Exponential-Backoff Reconnect (max 5 Retries)
- Fallback auf HTTP-Poll bei WS-Ausfall
- WS_LOG_LATENCY für Performance-Monitoring
```

---

## Referenzen

| Quelle | Inhalt |
|--------|--------|
| Polymarket CLOB Docs | WebSocket API, Channel-Typen, Auth |
| AWS eu-west-2 | Polymarket Server-Location (London) |
| Hetzner Helsinki | Unser Server (~30ms zu London) |
| retry.py (Commit 058497c) | Exponential Backoff bereits deployed — für WS-Reconnect nutzen |
| T-M-NEW Prompt | AnomalyDetector braucht WS für < 5s Insider-Erkennung |
