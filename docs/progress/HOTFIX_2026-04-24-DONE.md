# Hotfix 2026-04-24 — Deadman Recovery DONE

**Abgeschlossen:** 2026-04-24 03:40 UTC  
**Branch:** hotfix-2026-04-24-deadman-recovery → merged to main  
**Tests:** 128/128 ✅

---

## Fixes

| # | Fix | Status | Commit |
|---|-----|--------|--------|
| 1 | Emergency-Mode entsperrt (bot.lock + bot_status.json → OK) | ✅ | `00c99e6` |
| 2 | heartbeat.txt Pfad: live_engine/ → ROOT/ + INFO-Logging + sofortiger Start-Write | ✅ | `171ccc2` |
| 3 | WalletMonitor: WS-Protokoll-Ping aktiviert (ping_interval=20s, ping_timeout=15s) | ✅ | `36d84ea` |
| 4 | signature_type: defensiver BalanceAllowanceParams-Guard in _verify_order_onchain | ✅ | `2e74419` |
| 5 | Kelly-Sizer: orders_below_minimum-Counter + MIN_ORDER_USDC env-var konfigurierbar | ✅ | `59afd4a` |

---

## Root-Cause Analyse

**Eigentlicher Root-Cause (eine Kette):**

1. **Phase-3-Refactor** verschob `main.py` in `live_engine/`
2. `heartbeat_loop()` nutzte `os.path.dirname(__file__)` = `live_engine/` als Pfad
3. `heartbeat.txt` wurde in `live_engine/heartbeat.txt` geschrieben statt ROOT
4. `kongtrade-watchdog.timer` (läuft alle 60s) prüft ROOT `heartbeat.txt`
5. Watchdog sah ROOT `heartbeat.txt` als >10min stale → erzwang `systemctl restart` alle 60s
6. Dadurch: WalletMonitor startet/stoppt im 60s-Zyklus, jedes Mal 0 Trades detected
7. Während der erzwungenen Neustarts: HC.io-Pings für >Grace-Period unterbrochen
8. HC.io sendet Emergency-Webhook → `data/bot_status.json` = EMERGENCY_STOPPED + `bot.lock` gesetzt

**Fix 2 löst damit alle Symptome:**
- heartbeat.txt jetzt korrekt in ROOT (watchdog happy)
- Watchdog erzwingt keine ungewollten Neustarts mehr
- WalletMonitor bleibt dauerhaft verbunden
- HC.io empfängt kontinuierliche Pings → kein Emergency-Webhook mehr

---

## Validation

| Check | Ergebnis |
|-------|----------|
| Tests nach Merge | **128/128 grün** |
| Bot-Status 90s nach Start | **active (running)** |
| heartbeat.txt nach Start | **frisch (2s nach Start geschrieben)** |
| bot_status.json | **OK** |
| bot.lock | **nicht vorhanden** |
| Errors in Log | **keine** |
| DRY-RUN Mode | **bestätigt** (kein echtes Trading) |
| Dashboard (kong-trade.com) | **HTTP 302** (Login-Redirect, OK) |
| Weather-Scout | **aktiv**, 11 Opportunities gefunden |

---

## Offene Punkte (nicht in diesem Hotfix)

| # | Problem | Prio |
|---|---------|------|
| W1 | 6 ENDED Positionen noch in open_positions (Busan 51h overdue) | Mittel |
| W2 | 11 Positionen ohne market_closes_at → kein Auto-Close | Mittel |
| W7 | 15 Phantom dry_run-Positionen (Reconciliation Warning) | Niedrig |
| W4 | SMTP nicht konfiguriert → Health-Monitor-Alerts versacken | Niedrig |
| W5 | seen_tx_hashes: 14.782 > dokumentierter Cap 10.000 | Info |
| W6 | service-bot.log 44MB unrotiert | Info |

---

## Empfohlene nächste Schritte

1. **Monitor:** 24h beobachten ob watchdog-Restarts aufgehört haben (watchdog_state.json sollte keine neuen Einträge zeigen)
2. **ENDED-Positionen cleanen:** `resolver.py` manuell laufen lassen für die 6 abgelaufenen Positionen
3. **Phantom-Positionen:** dry_run_* Einträge aus bot_state.json entfernen (manuell oder via `utils/kill_switch.py unlock`)
4. **SMTP konfigurieren:** Für health_monitor E-Mail-Alerts
5. **Log-Rotation:** service-bot.log via logrotate konfigurieren

---

*Hotfix 2026-04-24 abgeschlossen.*
