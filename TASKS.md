# TASKS — Kong Trading Bot
_Single Source of Truth für alle offenen/erledigten Aufgaben_
_Letzte Aktualisierung: 2026-04-18 00:00 UTC_

## 🔴 IN ARBEIT (gerade in Bearbeitung)
- [ ] T-001 | Dashboard Ultimate-Upgrade | gestartet: 2026-04-17 22:00 | ETA: 2026-04-19
  - Balance-Widget (on-chain), Positions 3-Tabs (pending/open/resolved), Balance-Chart
  - Resolutions-Panel, Per-Wallet-Performance, Service-Health-Widget
  - Log-Filter, Wallet-Multiplier-Reorganisation, Was-wäre-wenn-Simulator, Mobile-Responsive
  - Backend: 9 neue API-Endpoints + SQLite metrics.db
- [ ] T-005 | KNOWLEDGE_BASE.md auf Server anlegen und pflegen | gestartet: 2026-04-17 23:00

## 🟡 QUEUE (angenommen, noch nicht gestartet)
- [ ] T-002 | systemd-Services für Bot + Dashboard + Watchdog | in Auftrag gegeben: 2026-04-17
- [ ] T-003 | Cloudflare Tunnel mit Zero-Trust-Auth für öffentliches Dashboard | in Auftrag gegeben: 2026-04-17 | BLOCKED: erfordert Browser-Login (cloudflared tunnel login)
- [ ] T-004 | Stale-Position-Recovery beim Bot-Start (via REST /orders) | in Auftrag gegeben: 2026-04-17
- [ ] T-006 | Duplikat-Wallet in TARGET_WALLETS entfernen (jede Zeile erscheint 2x im Log) | in Auftrag gegeben: 2026-04-18
- [ ] T-007 | Telegram-Commands implementieren (/balance, /health, /logs, /restart) | in Auftrag gegeben: 2026-04-18
- [ ] T-008 | GitHub-Push aller heutigen Änderungen (dashboard.py, dashboard.html, main.py, KNOWLEDGE_BASE.md) | in Auftrag gegeben: 2026-04-18

## 🟢 DONE (neueste oben)
- [x] T-D07 | TASKS.md Anlage (dieser Auftrag) | fertig: 2026-04-18 00:00 | Dateien: TASKS.md
- [x] T-D06 | FillTracker L2-Credentials-Fix (derive_api_key()) | fertig: 2026-04-17 23:36 | Dateien: core/fill_tracker.py
- [x] T-D05 | Dashboard v1 deployed (dashboard.py + dashboard.html + kongtrade-dashboard.service) | fertig: 2026-04-17 22:00 | Dateien: dashboard.py, dashboard.html
- [x] T-D04 | Telegram-Bot Overhaul (msg_order_submitted/filled/rejected) | fertig: 2026-04-17 | Dateien: core/telegram_bot.py
- [x] T-D03 | signature_type Bug-Fix in execution_engine | fertig: 2026-04-17 | Dateien: core/execution_engine.py
- [x] T-D02 | Min-Size + Tick-Size dynamischer Pre-Submit-Check | fertig: 2026-04-17 | Dateien: core/execution_engine.py
- [x] T-D01 | FillTracker WebSocket-basiertes Fill-Tracking | fertig: 2026-04-17 | Dateien: core/fill_tracker.py

## ❌ BLOCKED (wartet auf Brrudi oder externes)
- [ ] T-003 | Cloudflare Tunnel | blocker: `cloudflared tunnel login` erfordert Browser-Interaktion — Brrudi muss im Terminal selbst einloggen: `ssh root@89.167.29.183` dann `cloudflared tunnel login`

## 📋 IDEEN (nice-to-have, später)
- T-I01 | Auto-Resolver bei Markt-Close (cronjob statt manuellem resolver.py)
- T-I02 | PnL-Push via Telegram täglich 8 Uhr (bereits Morning Report, erweitern)
- T-I03 | Mehrere Bots parallel (verschiedene Wallets/Multiplikatoren) verwalten
- T-I04 | Web-UI für Wallet-Konfiguration (kein .env-Edit nötig)
- T-I05 | Automatisches bot_state.json Cleanup bei Phantom-Positionen

---

## REGELN (für Claude Code)
1. JEDER neue Auftrag von Brrudi → sofort in QUEUE mit nächster freier T-Nummer
2. Wenn Arbeit beginnt → IN ARBEIT verschieben
3. Wenn fertig → DONE mit geänderten Dateien
4. Wenn blockiert → BLOCKED mit Grund
5. Nach JEDEM Status-Wechsel: git commit + push
6. Am Ende jeder Antwort kurze Statuszeile: "📋 Aktuell: X in Arbeit, Y in Queue, Z blocked. Aktueller: T-XXX <name>"

## Quick Reference
```bash
# Status lesen
ssh root@89.167.29.183 "cat /root/KongTradeBot/TASKS.md"

# Live-Log
ssh root@89.167.29.183 "tail -f /root/KongTradeBot/logs/bot_$(date +%Y-%m-%d).log"
```
