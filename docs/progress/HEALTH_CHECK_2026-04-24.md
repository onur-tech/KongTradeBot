# Health Check Report — 2026-04-24

**Erstellt:** 2026-04-24 03:25 UTC  
**Bot-Version:** 1.6 (Phase-3-Merge)  
**Branch:** phase-4-copy-trading-port  
**Diagnose-Zeitpunkt:** ~56 Minuten nach letztem Systemd-Restart (02:21 UTC)

---

## 🔴 KRITISCH (Bot handelt falsch / Geld-Risiko)

### K1 — WalletMonitor stirbt zyklisch: Copy-Trading funktioniert NICHT
- WalletMonitor wird alle ~60 Minuten gestoppt und neu gestartet (Muster seit Mitternacht):
  - 00:18, 00:19, 00:20 → Restart
  - 01:18, 01:19, 01:20 → Restart
  - 02:19, 02:20, 02:21 → Restart
  - 03:19, 03:20 → Restart (aktuell)
- Bei jedem Zyklus: `ws_reconnects: 3-4`, dann kompletter Stop mit 0 Trades detected
- `FillTracker WebSocket-Fehler: "unhandled errors in a TaskGroup"` — wiederholt (00:01, 00:25, 00:43, 01:02, 01:25, 02:27)
- **Konsequenz:** Kein einziger Whale-Trade wurde in den letzten ~27h erkannt. Copy-Trading ist de facto tot.

### K2 — Heartbeat seit 33+ Stunden tot → Deadman-Lock aktiv
- `heartbeat.txt` zuletzt modifiziert: **2026-04-22 18:05:51** (33.2h vor Diagnose-Zeitpunkt = 119.121 Sekunden)
- `bot.lock` gesetzt von `deadman_switch` um **03:03 UTC** mit Grund: *"Healthchecks.io — check went down"*
- `data/bot_status.json`: `"status": "EMERGENCY_STOPPED"` (seit 03:03 UTC)
- ABER: `main.py` läuft trotzdem weiter (PID 954133, gestartet 02:21 UTC)
- Bot-Log bestätigt: `[Heartbeat] Started (interval=30s url=https://hc-ping.com/aea164a2-3...)` — Heartbeat-Task startet bei jedem Restart, aber healthchecks.io empfängt offenbar keine Pings mehr (sonst wäre Lock nicht gesetzt worden)
- **Konsequenz:** Deadman-Switch hat ausgelöst wegen fehlendem Ping, aber der Bot ignoriert das Lock und läuft weiter (schlechtes Safety-Verhalten). Außerdem: das `heartbeat.txt`-File selbst wird nicht mehr beschrieben → der Heartbeat-Writer-Task könnte selbst defekt sein.

### K3 — Bot läuft im DRY-RUN obwohl LIVE-Session vorgesehen
- Log 03:20:52: `"Modus: DRY-RUN (kein echtes Trading)"` + `"Execution Engine im DRY-RUN Modus"`
- Ursache unklar: Entweder greift bot.lock → DRY-RUN-Fallback, oder der Bot wurde im DRY-RUN-Modus neu gestartet
- `data/daily_stats.json`: `"today_trades": 1` (1 Trade, aber als Dry-Run gezählt)
- **Konsequenz:** Kein echter Trade wird ausgeführt — aber ob das beabsichtigt oder ein Fehler ist, ist unklar. Wenn der Bot live sein soll, handelt er jetzt im Schatten ohne echte Fills.

### K4 — On-Chain-Verifikation BROKEN (aus letzter LIVE-Session 17. April)
- Fehler: `'dict' object has no attribute 'signature_type'`
- Alle LIVE-Orders der letzten aktiven Session waren **nicht on-chain verifiziert**:
  - `⚠️  Order 0xef3bcc1... nicht on-chain verifiziert!`
  - `⚠️  Order 0xaa481f0... nicht on-chain verifiziert!`
  - `⚠️  Order 0x461c1dd... nicht on-chain verifiziert!`
- CLAUDE.md-Regel: *"Verify fills on-chain (check balance change), do not trust API response alone"* — wird verletzt
- Betrifft Phase 3.4g (`signature_check mit mode-Parameter`) — vermutlich API-Response-Format-Änderung

### K5 — 12 von 15 Orders failed (letzte LIVE-Session 17. April)
- Fehler-Typ: **100% Order-Size-Fehler**: `Size (0.04) lower than the minimum: 5`
- Betroffene Orders: Sizes 0.04, 0.11, 0.16, 0.21, 0.21, 0.30, 0.53, 3.84, 4.68 USDC
- Alle liegen unter dem Polymarket-Minimum von 5 USDC
- Ursache: `COPY_SIZE_MULTIPLIER` zu niedrig, oder Basis-Trade-Size der Whales zu klein → proportionale Berechnung ergibt Sub-5-USDC Ergebnis
- Status-Display zeigte: `Filled: 3 | Failed: 12 | Budget: $100,000,000 USDC`
- **Das $100M Budget-Display ist ein Sentinel-Wert** (Code-Kommentar: *"Fallback: PORTFOLIO_BUDGET_USD is a 100M sentinel → use 1000 as default"*) — kein Geld-Risiko, aber ein UI-Bug

---

## 🟡 WARN (Funktioniert, aber degradiert)

### W1 — 6 ENDED Positionen noch in open_positions (nicht aufgeräumt)
- `Atlanta Braves vs. Philadelphia Phillies` — PENDING_CLOSE, 3.3h overdue
- `Tallahassee: Daniil Glinka vs Jack Kennedy` — PENDING_CLOSE, 3.3h overdue
- `Tampa Bay Rays vs. Pittsburgh Pirates` — PENDING_CLOSE, 3.3h overdue
- `Will the highest temperature in Busan be 16°C on April 22?` — PENDING_CLOSE, **51.3h overdue**
- `Will the highest temperature in Beijing be 26°C on April 23?` — OPEN, 3.3h overdue
- `Will the highest temperature in Moscow be 7°C on April 23?` — OPEN, 3.3h overdue
- Resolver-Loop sollte diese schließen — tut er aber nicht (oder wird blockiert)

### W2 — 11 Positionen ohne market_closes_at
- Betroffen: Madrid Open (6x), Texas Primary (2x), Elche CF, Predict.fun, John Cornyn
- Kein automatischer Close möglich → bleiben ewig als "OPEN" stehen

### W3 — FillTracker WebSocket wiederholt instabil
- `unhandled errors in a TaskGroup` 5x in der Nacht (00:01, 00:25, 00:43, 01:02, 01:25)
- Reconnect funktioniert (1-4 Sekunden), aber Root Cause unbekannt
- Betrifft Fill-Tracking für LIVE-Orders

### W4 — Health-Monitor sendet Alerts aber SMTP nicht konfiguriert
- `health_monitor.log`: 15+ Alerts `"ALERT gesendet: 2 Probleme"` (zuletzt 3 Probleme)
- `[EMAIL SKIP] Kein SMTP konfiguriert` — Alerts gehen nirgends hin
- Stille Degradierung: System merkt Probleme, kann sie aber nicht eskalieren

### W5 — seen_tx_hashes: 14.782 — überschreitet dokumentierten Cap
- CLAUDE.md: *"Transaction hash dedup set is capped at 10,000 entries (memory management)"*
- Tatsächlich in bot_state.json: **14.782 Hashes** (+ Inkrement nach Restart: 14.789)
- Entweder Cap ist falsch dokumentiert, oder Code-Guard funktioniert nicht

### W6 — service-bot.log: 44 MB unrotiert
- `logs/service-bot.log`: 44 MB (systemd-Journal, nicht täglich rotiert)
- `logs/service-dashboard.log`: 10 MB
- Bei weiterem Wachstum → Disk-Druck in Wochen/Monaten

### W7 — 15 Phantom-Positionen (Reconciliation-Warning)
- `[Reconcile] 15 phantom(s): ['dry_run_3_0x294bc0', 'dry_run_4_0xa3b69f', ...]`
- Alle sind `dry_run_*` IDs — entstanden durch DRY-RUN → LIVE → DRY-RUN Wechsel
- Diese existieren in bot_state.json aber nicht auf der CLOB

### W8 — Watchdog: 3 Restarts in letzter Stunde
- `watchdog_state.json`: 3 Restarts
  - ~02:21 UTC (3x kurz hintereinander)
- Aktuell (03:20) läuft Bot ~57min ohne Crash — Restart-Rate hat sich beruhigt

---

## 🔵 INFO (Beobachtung, kein Fix nötig)

### I1 — Git sauber, Branch korrekt
- `phase-4-copy-trading-port`, letzter Commit `f40177e` (Phase 3 Merge-Doku), clean

### I2 — Wallet-Balance: $421.20 USDC (real, per Polygon-RPC)
- RPC1 (Ankr) gibt $0.00 zurück → Fallback auf publicnode.com
- Max investierbar: $294.84 (70% Portfolio-Budget-Cap aktiv)
- Kein Geld-Verlust durch die Session-Fehler (alle Orders unter 5 USDC abgelehnt = nichts ausgegeben)

### I3 — Circuit-Breaker: Level 0, kein Trigger
- `data/circuit_breaker.json`: `{"level": 0, "triggered_at": "", "reason": ""}`

### I4 — Disk und RAM OK
- Disk: 4.7 GB / 38 GB (13% genutzt)
- RAM: 1.4 GB / 3.7 GB (37%), kein Swap
- CPU: 55% user (davon ~30% Claude-Code-Prozess, ~3% main.py)

### I5 — Weather-Scout aktiv und findet Opportunities
- 11 Opportunities gefunden im letzten Scan (03:20 UTC)
- Nicht-kalibrierte Städte: SHADOW-ONLY (korrekt)
- Kalibrierte Städte: Trades werden aufgegeben

### I6 — TradeLogger-Statistik
- `total_trades: 357`, `total_pnl: +2076.18 USDC`, `live_trades: 259`, `paper_trades: 98`

### I7 — Ankr-RPC liefert $0.00
- Bekanntes intermittierendes Problem (Phase 2 beobachtet), Fallback-RPC greift korrekt

### I8 — $100M Budget-Display ist Sentinel, kein echter Wert
- Code: `"Fallback: PORTFOLIO_BUDGET_USD is a 100M sentinel → use 1000 as default"`
- Tatsächliches Budget aus `balance_cache.json`: $421.20 USDC

---

## Vollständige Ausgabe aller 8 Blöcke

### BLOCK 1 — Bot-Prozess + Heartbeat

```
Fri Apr 24 03:18:25 AM UTC 2026

kongtrade-bot.service: active (running) since 2026-04-24 02:21:40 UTC; 56min ago
  Main PID: 954133 (/usr/bin/python3 main.py)
  Memory: 154.1M | CPU: 1min 41.226s

PROZESSE:
  PID 797    python3 /usr/share/unattended-upgrades/...
  PID 822961 python3 /home/claudeuser/KongTradeBot/scripts/cancel_all_on_death.py  [seit Apr23 06:35]
  PID 822964 python3 dashboard.py  [root, seit Apr23]
  PID 954133 python3 main.py  [seit 02:21 UTC, 2.9% CPU]

bot.lock:
  {"locked_at": "2026-04-24T03:03:00.459680+00:00",
   "reason": "Healthchecks.io — check went down",
   "locked_by": "deadman_switch"}

heartbeat.txt:
  Mtime: 2026-04-22 18:05:51 (33h alt!)
  Inhalt: 2026-04-22T18:05:51.457259+00:00

kongtrade-deadman.service: active (running) since 2026-04-23 06:35:06 UTC; 20h ago
  PID 822961 (cancel_all_on_death.py)
```

### BLOCK 2 — Log-Analyse

```
Logs-Verzeichnis:
  logs/bot.log              407KB  [root, Apr 24 03:20]  ← AKTUELL
  logs/service-bot.log       44MB  [root, Apr 24 03:20]  ← RIESIG
  logs/service-dashboard.log 10MB  [root, Apr 24 03:20]
  logs/health_monitor.log   6.2KB  [Apr 24 03:00]
  bot.log (root-dir)        2.4MB  [Apr 17 21:23]        ← VERALTET

FEHLER-MUSTER aus logs/bot.log (seit 00:00 UTC):
  - WalletMonitor zyklisch gestoppt+restart (alle ~60min)
  - FillTracker WS: "unhandled errors in a TaskGroup" (5x)
  - ws_reconnects: 3-4 pro Zyklus

FEHLER aus bot.log (Root, 17. April — letzte LIVE-Session):
  - 12x PolyApiException: Size lower than minimum: 5
  - 3x On-Chain Verifikation fehlgeschlagen: 'dict' object has no attribute 'signature_type'
  - Status: Filled:3 | Failed:12 (80% Fail-Rate)
```

### BLOCK 3 — Trade-State

```
bot_state.json:
  version: 1.6
  saved_at: 2026-04-24T02:21:40 (beim letzten Restart)
  open_positions: 22
  seen_tx_hashes: 14578 (Cap laut Doku: 10.000)
  dry_run_counter: 1
  
data/bot_status.json:
  {"status": "EMERGENCY_STOPPED",
   "reason": "Healthchecks.io — check went down",
   "stopped_at": "2026-04-24T03:03:00.459337+00:00"}

data/daily_stats.json:
  {"date": "2026-04-24", "today_pnl": 0, "today_trades": 1, "today_wins": 0, "today_losses": 0}

data/balance_cache.json:
  {"balance_usdc": 421.200701, "max_portfolio_pct": 0.7}

data/trades.db (letzte Trades — alle weather-bot):
  id=27: Istanbul NO @0.70, $10 USDC [2026-04-24 02:21:31]
  id=26: Toronto NO  @0.54, $10 USDC [2026-04-23 19:50:44]
  id=25: Toronto NO  @0.81, $10 USDC [2026-04-23 18:50:53]
  ...
  id=17: Madrid Open - Taylor Townsend @0.29, $287 signal [2026-04-22 17:48] ← letzter COPY-Trade

TradeLogger (aus Log):
  total_trades: 357 | closed: 190 | open: 167
  total_pnl: +2076.18 USDC
  live_trades: 259 | paper: 98
```

### BLOCK 4 — ENDED-Positionen

```
ENDED aber noch in open_positions (6):
  [ 51.3h overdue | PENDING_CLOSE] Will the highest temperature in Busan be 16°C on April 22?
  [  3.3h overdue | PENDING_CLOSE] Atlanta Braves vs. Philadelphia Phillies
  [  3.3h overdue | PENDING_CLOSE] Tallahassee: Daniil Glinka vs Jack Kennedy
  [  3.3h overdue | PENDING_CLOSE] Tampa Bay Rays vs. Pittsburgh Pirates
  [  3.3h overdue | OPEN        ] Will the highest temperature in Beijing be 26°C on April 23?
  [  3.3h overdue | OPEN        ] Will the highest temperature in Moscow be 7°C on April 23?

OHNE market_closes_at (11):
  Will John Cornyn win the 2026 Texas Republican Primary?
  Madrid Open: Benjamin Bonzi vs Titouan Droguet (2x)
  Madrid Open: Lorenzo Sonego vs Dusan Lajovic
  Madrid Open: Dayana Yastremska vs Solana Sierra
  Madrid Open: Nikoloz Basilashvili vs Sebastian Ofner (2x)
  Predict.fun FDV above $600M one day after launch?
  Madrid Open: Anhelina Kalinina vs Kamilla Rakhimova
  Will Ken Paxton win the 2026 Texas Republican Primary?
  Will Elche CF vs. Club Atlético de Madrid end in a draw?

AKTIV (noch offen, 5):
  [closes in 140.7h | ACTIVE] Strait of Hormuz traffic returns to normal by end of April?
  [closes in 140.7h | ACTIVE] Iran agrees to end enrichment of uranium by April 30?
  [closes in 140.7h | ACTIVE] Iran agrees to surrender enriched uranium stockpile by April 30?
  [closes in  20.7h | OPEN  ] Will the highest temperature in Toronto be 9°C on April 24?
  [closes in  20.7h | OPEN  ] Will the highest temperature in Istanbul be 18°C on April 24?
```

### BLOCK 5 — Safety-Layer

```
data/circuit_breaker.json:
  {"level": 0, "triggered_at": "", "reason": "", "pause_until": ""}
  → OK, kein Trigger

data/bot_status.json:
  {"status": "EMERGENCY_STOPPED", "reason": "Healthchecks.io — check went down",
   "stopped_at": "2026-04-24T03:03:00.459337+00:00"}

bot.lock:
  {"locked_at": "2026-04-24T03:03:00.459680+00:00",
   "reason": "Healthchecks.io — check went down",
   "locked_by": "deadman_switch"}

kill_switch.py: existiert (utils/kill_switch.py)
.emergency_stop: NICHT vorhanden
kill_switch.json: NICHT vorhanden
data/heartbeat.db: NICHT vorhanden
```

### BLOCK 6 — Dashboard-API

```
Port 5000: HTTP 302 → Login-Redirect (auth-gesichert, OK)
/api/status: {"error": "Unauthorized"} (ohne Token)
dashboard.log: letzter Zugriff Apr 17 22:53 (7 Tage alt)
Port 8888: belegt durch cancel_all_on_death.py (Webhook-Listener)
```

### BLOCK 7 — Git

```
Branch: phase-4-copy-trading-port
Status: clean (no uncommitted changes)
Letzte Commits:
  f40177e docs: Phase 3 gemerged und deployed
  1a2395c Merge phase-3-plugin-refactor
  1ac25a0 docs: Phase 3 abgeschlossen
  75a827e test(integration): Plugin mit Shared-Safety-Layer
  684e8f6 refactor(safety): signature_check mit mode-Parameter (Phase 3.4g)
Branches: main | phase-3-plugin-refactor | phase-4-copy-trading-port
```

### BLOCK 8 — Disk + Resources

```
Disk: 4.7G / 38G (13%) — OK
  /KongTradeBot/: 135M
  /data/:         22M
  /logs/:         85M (44M service-bot.log + 10M service-dashboard.log)
  /backups/:      4.4M

RAM: 1.4G / 3.7G (37%) — OK | kein Swap
CPU: 55% user (30% claude-Prozess, ~3% main.py, ~1.6% dashboard.py)
```

---

## Empfohlene Reihenfolge der Fixes

1. **[K2] Heartbeat debuggen** — Warum kommt der healthchecks.io-Ping nicht an? Netzwerkfehler? Falscher URL? API-Key abgelaufen? → Root-Cause finden. Danach `bot.lock` entfernen und `data/bot_status.json` auf `running` setzen.

2. **[K1] WalletMonitor-Crash-Ursache finden** — Was killed den Monitor nach ~60min? Laut Log: ws_reconnects 3-4x, dann total stop. Ist das ein max-retry-exit? Oder ein unbehandelter Asyncio-Fehler? → logs/service-bot.log vollständig durchsuchen nach Exception vor jedem "WalletMonitor gestoppt".

3. **[K3] DRY-RUN vs LIVE klären** — Ist der aktuelle DRY-RUN gewollt (wegen bot.lock)? Oder soll der Bot live handeln? → Entscheidung treffen, dann entweder Lock lösen oder bewusst im Dry-Run lassen.

4. **[W1] ENDED-Positionen bereinigen** — 6 Positionen aus open_positions entfernen (inkl. Busan 51h overdue). Resolver-Loop prüfen warum er die nicht schließt.

5. **[K4] On-Chain-Verifikation bug fixen** — `'dict' object has no attribute 'signature_type'` in `execution_engine.py` debuggen. Warum kommt ein dict statt des erwarteten Typs?

6. **[K5] MIN_TRADE_SIZE Guard einbauen** — Vor Order-Erstellung sicherstellen dass size_usdc >= 5.0 USDC (Polymarket-Minimum). Aktuell keine Pre-Flight-Validation.

7. **[W7] Phantom dry_run-Positionen** — 15 dry_run_* Einträge aus open_positions/bot_state.json entfernen.

8. **[W4] SMTP konfigurieren oder Health-Monitor deaktivieren** — Alerts gehen ins Nirvana.

---

*Diagnose abgeschlossen. docs/progress/HEALTH_CHECK_2026-04-24.md erstellt.*  
**KRITISCH: 5 Punkte | WARN: 8 Punkte | INFO: 8 Punkte**  
*Warte auf User-Entscheidung welche Fixes priorisiert werden.*
