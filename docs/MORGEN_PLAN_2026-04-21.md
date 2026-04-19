# Morgen Plan — 21.04.2026 (Dienstag)
_Erstellt: 2026-04-20 von Windows-CC_

---

## PRIO 1 — US×Iran Resolution (EVENT-GETRIEBEN)

**Status:** Resolution heute Nacht oder morgen früh erwartet.

**Automatisch:** T-M04d feuert bei ≥95¢ → Bot verkauft automatisch.
Kein manueller Eingriff nötig wenn Trigger funktioniert.

**Manuell (Backup):**
1. Telegram-Alert bei WON prüfen
2. polymarket.com öffnen + Norwegen-VPN
3. Position manuell claimen
4. T-M06 Reconciliation läuft danach automatisch

**Monitoring-Befehl (Server-CC):**
```bash
grep "US.*Iran\|Iran.*ceasefire\|CLAIM\|RESOLVE" \
  /root/KongTradeBot/logs/bot_$(date +%Y-%m-%d).log | tail -20
```

---

## PRIO 2 — T-WS WebSocket WalletMonitor

**Status:** Prompt fertig — `prompts/t_ws_websocket_wallet_monitor.md`

**Schritt-für-Schritt:**
1. Windows-CC Push sicherstellen (alle Commits gepusht)
2. Server-CC: Prompt öffnen
3. Server-CC: `pip install websockets>=12.0` (requirements.txt ergänzen)
4. Server-CC: `core/wallet_monitor.py` erweitern:
   - `_run_websocket()` — Haupt-WS-Loop
   - `_heartbeat()` — 10s PING-Task
   - `_process_ws_message()` — Trade-Parsing
5. `.env`: `WALLET_MONITOR_MODE=poll` belassen (erst testen!)
6. DRY_RUN-Test mit `WALLET_MONITOR_MODE=websocket`
7. 48h Beobachtung: Latenz-Logs + Reconnect-Verhalten

**STOP-CHECKs vor Live-Schaltung:**
```bash
# 1. Package vorhanden?
pip show websockets | grep Version

# 2. WS-Verbindung OK?
python3 -c "
import asyncio, websockets, json
async def test():
    async with websockets.connect('wss://ws-subscriptions-clob.polymarket.com/ws/market', open_timeout=10) as ws:
        print('Verbunden!')
        await ws.send(json.dumps({'type': 'ping'}))
        msg = await asyncio.wait_for(ws.recv(), timeout=5)
        print(f'Antwort: {msg[:100]}')
asyncio.run(test())
"
```

**Ergebnis:** Signal-Latenz 10–15s → 1–3s.

---

## PRIO 3 — T-M-NEW Anomalie-Detektor

**Status:** Prompt fertig — `prompts/t_m_new_anomaly_detector.md`

**Abhängigkeit:** Nach T-WS implementieren (Synergie: WS-Feed für AnomalyDetector).

**Schritt-für-Schritt:**
1. T-WS vollständig deployed und stabil (48h)
2. Dann: `core/anomaly_detector.py` implementieren
3. `main.py`: AnomalyDetector als 7. async Task starten
4. Budget-Limit: $2/Signal, $20/Tag (`ANOMALY_DAILY_BUDGET_USD=20`)
5. Kalibrierung: Iran-Ceasefire-Daten als Referenz

**Erste Test-Signale erwartet:** innerhalb 24h nach Deployment.

---

## PRIO 4 — Erste Ergebnisse neue Wallets beobachten

**wokerjoesleeper** (`0x63d43bbb87f85af03b8f2f9e2fad7b54334fa2f`)
- Kategorie: Makro/Fed/Iran — Longterm-Positionen
- ~18 Trades/Tag in aktiven Perioden
- Erste Signale erwartet: wenn Fed/Iran-bezogene Märkte aktiv
- Monitoring: Telegram-Alert bei jedem kopierten Trade

**ScottyNooo** (`0xbacd00c9080a82ded56f504ee8810af732b0ab35`)
- Kategorie: Politik/Trump/Iran — ~7 Trades/Tag
- Aktuelle Positionen: US×Iran Ceasefire, US-Streitkräfte Iran
- Erste Signale erwartet: heute Nacht / morgen früh (Iran aktiv)
- Monitoring: Telegram-Alert

**DrPufferfish** (`0xdb27bf2ac5d428a9c63dbc914611036855a6c56e`)
- Dormant — nur wenn TARGET_WALLETS hinzugefügt nach T-M03 stable
- NBA same-day Exits sind der primäre Wert

**Check-Befehl:**
```bash
grep "wokerjoesleeper\|ScottyNooo\|Signal\|COPY" \
  /root/KongTradeBot/logs/bot_$(date +%Y-%m-%d).log | tail -30
```

---

## PRIO 5 — PANews Biteye Deep-Scan (restliche 20 Wallets)

**Was noch aussteht:**
Aus dem PANews Biteye-Artikel (2026-04-01) sind 26 Wallets dokumentiert.
Heute vertieft gecheckt: wokerjoesleeper + ScottyNooo (beide APPROVE).
Noch nicht gecheckt (predicts.guru + 0xinsider Verify ausstehend):

| Wallet | Adresse | Sektor | PANews PnL |
|--------|---------|--------|-----------|
| cowcat | `0x38e59b36aae31b164200d0cad7c3fe5e0ee795e7` | ME-Longshot | $200K +117% ROI |
| Frank0951 | `0x40471b34671887546013ceb58740625c2efe7293` | Geo+Esports | $290K |
| How.Dare.You | `0x4bbe10ba5b7f6df147c0dae17b46c44a6e562cf3` | Ukraine | $277K |
| middleoftheocean | `0x6c743aafd813475986dcd930f380a1f50901bd4e` | Soccer | $470K |
| ewelmealt | `0x07921379f7b31ef93da634b688b2fe36897db778` | Soccer/La Liga | $860K (19d) |
| EFFICIENCYEXPERT | `0x8c0b024c17831a0dde038547b7e791ae6a0d7aa5` | Esports/LoL | $580K |
| synnet | `0x8e0b7ae246205b1ddf79172148a58a3204139e5c` | Tennis | $290K |
| CKW | `0x92672c80d36dcd08172aa1e51dface0f20b70f9a` | UFC/MLB | $74M Vol |

**Aktion:** predicts.guru ROI auf Deposits für jeden prüfen.
Erst dann APPROVE oder REJECT.

**Review-Ziel:** 2026-05-05

---

## Tagesplan Übersicht

| Zeit | Aktion | Priorität |
|------|--------|-----------|
| Nacht/Früh | US×Iran Resolution warten | PRIO 1 |
| Morgen Früh | Logs prüfen: neue Wallets aktiv? | PRIO 4 |
| Morgen Vor. | T-WS an Server-CC schicken | PRIO 2 |
| Morgen Nach. | T-WS STOP-CHECKs validieren | PRIO 2 |
| Morgen Abend | PANews Biteye restliche Wallets | PRIO 5 |
| Übermorgen | T-M-NEW nach T-WS stabil | PRIO 3 |

---

_Alle Prompts in `prompts/` — Commits bis 2026-04-20: ee9670f gepusht_
