# KongTrade Bot — Task Tracking
_Stand: 2026-04-18_

**Regeln:**
- Eine Task pro Zeile mit ID, Titel, Priorität
- Status: 🔄 IN ARBEIT | ⏳ QUEUE | ✅ DONE | 🚫 BLOCKED | 💡 IDEE
- Priorität: 🔴 KRITISCH | 🟡 WICHTIG | 🟢 NICE-TO-HAVE

---

## 🔄 IN ARBEIT

| ID | Titel | Prio | Notiz |
|----|-------|------|-------|
| T-001 | Dashboard Portfolio-Upgrade (fetchPortfolio, /api/portfolio) | 🔴 | Auf Server deployed, aber 13 Follow-up Bugs offen |
| T-005 | KNOWLEDGE_BASE.md + TASKS.md pflegen | 🟡 | Lokal erstellt, noch nicht auf Server gepusht |

---

## ⏳ QUEUE (priorisiert)

### 🔴 Kritisch — Bot kann nicht traden

| ID | Titel | Prio | Notiz |
|----|-------|------|-------|
| T-009 | CLAIM $11.29 auf polymarket.com | 🔴 | Manuell! 4 redeemable Positionen. Bot blockiert bis Cash > $5 |
| T-011 | CLAIM-Button in Positions-Tabelle fixen | 🔴 | `p.redeemable \|\| p.isRedeemable` prüfen (P012) |

### 🟡 Wichtig — Dashboard-Qualität

| ID | Titel | Prio | Notiz |
|----|-------|------|-------|
| T-012 | Alle 37 Positionen anzeigen (nicht nur 10) | 🟡 | CSS max-height erhöhen + kein JS-Slice (P013) |
| T-013 | "NÄCHSTE RESOLUTIONS" Panel aus Portfolio-Cache füllen | 🟡 | /api/resolutions auf _polymarket_positions umstellen (P010) |
| T-014 | Countdown-Spalte "SCHLIESST IN" in Positionen-Tabelle | 🟡 | endDate aus Polymarket-API berechnen (P009) |
| T-015 | P&L HEUTE = Portfolio-Delta seit Mitternacht | 🟡 | Mitternacht-Snapshot in SQLite speichern (P014) |
| T-016 | Balance-Chart auf Portfolio-Total umstellen | 🟡 | db_insert_balance() mit portfolio_total (P008) |
| T-006 | Duplikat-Wallet in TARGET_WALLETS entfernen | 🟡 | grep .env, doppelte Adresse löschen, Bot neu starten (P006) |

### 🟢 Nice-to-Have

| ID | Titel | Prio | Notiz |
|----|-------|------|-------|
| T-007 | Telegram-Commands: /balance /health /logs /restart | 🟢 | telegram_bot.py erweitern |
| T-017 | Per-Wallet-Performance aus Signal-Counter befüllen | 🟢 | Auch nicht-ausgeführte Signale tracken (P015) |
| T-018 | Log-Rotation auf TimedRotatingFileHandler | 🟢 | Prozess-Neustart nicht mehr nötig (P018) |
| T-019 | WS-Events-Counter auf Signale/Trades erweitern | 🟢 | Nicht nur CONFIRMED/MATCHED zählen (P011) |
| T-020 | Timezone Europe/Berlin vereinheitlichen | 🟢 | Server-Logs als UTC labeln oder alle auf CET (P016) |

---

## 🚫 BLOCKED

| ID | Titel | Blocker |
|----|-------|---------|
| T-002 | systemd Services (bot + dashboard) | Benötigt Hetzner-SSH-Zugang + Testzeit |
| T-003 | Cloudflare Tunnel | Benötigt `cloudflared tunnel login` mit Browser-Auth |
| T-008 | GitHub Push | Benötigt GitHub Personal Access Token (PAT) |
| T-021 | Public Status Repo "KongTradeBot-Status" | Abhängig von T-008 (GitHub Token) |

---

## ✅ DONE

| ID | Titel | Datum |
|----|-------|-------|
| T-D01 | Server Setup Hetzner Helsinki | 2026-04-17 |
| T-D02 | Magic-Link Proxy-Deploy via Norwegen-VPN | 2026-04-17 |
| T-D03 | signature_type=1 Fix deployed | 2026-04-17 |
| T-D04 | Min-Size-Check Fix deployed | 2026-04-17 |
| T-D05 | FillTracker condition_id Fix deployed | 2026-04-17 |
| T-D06 | Dashboard live (screen 'dash' :5000) | 2026-04-17 |
| T-D07 | SSH-Key-Login eingerichtet | 2026-04-17 |
| T-D08 | /api/portfolio Endpoint (fetchPortfolio) | 2026-04-18 |
| T-D09 | Dashboard: TOTAL PORTFOLIO VALUE als Hauptzahl | 2026-04-18 |
| T-D10 | Dashboard: Cash + In Positionen Sub-Zahlen | 2026-04-18 |
| T-D11 | Dashboard: CLAIM ALL Button (unclaimed wins) | 2026-04-18 |
| T-D12 | logger.py: propagate=False (Duplikat-Fix) | 2026-04-18 |
| T-D13 | balance_fetcher.py: Skip $0 RPCs, nie .env-Fallback | 2026-04-18 |
| T-D14 | dashboard.py: API-Fehler lesbar übersetzen | 2026-04-18 |
| T-010 | Balance-Check-Bug (400 assetAddress invalid hex address) | 2026-04-18 | Balance-Fix deployed ca. 09:35 UTC, verifiziert via /api/logs (P029) |

---

## 💡 IDEEN

| ID | Idee | Aufwand |
|----|------|---------|
| T-I01 | Auto-Claim via Polymarket SDK wenn redeemable > $5 | Hoch |
| T-I02 | Telegram-Alert wenn Claim verfügbar | Klein |
| T-I03 | Stop-Loss per Position (verkaufe wenn -50%) | Mittel |
| T-I04 | Wallet-Blacklist (stoppe Kopieren wenn Win-Rate < 30%) | Klein |
| T-I05 | Multi-Bot Support (mehrere Proxy-Wallets) | Sehr hoch |
