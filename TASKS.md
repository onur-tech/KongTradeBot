# KongTrade Bot — Task Tracking
_Stand: 2026-04-18 08:39 Berlin_

**Regeln:**
- Status: ARBEIT | QUEUE | DONE | BLOCKED | IDEE
- Prioritaet: KRITISCH | WICHTIG | NICE-TO-HAVE

---

## IN ARBEIT

| ID | Titel | Prio | Notiz |
|----|-------|------|-------|
| T-009 | CLAIM $11.29 auf polymarket.com | KRITISCH | Manuell! Bot blockiert bis Cash > $5 |

---

## QUEUE

| ID | Titel | Prio | Notiz |
|----|-------|------|-------|
| T-010 | Balance-Delta SEIT START reparieren | KRITISCH | Portfolio-Snapshot beim Start fehlt (P007) |
| T-011 | Bot-Neustart damit alle Nacht-Fixes aktiv werden | KRITISCH | claim_loop, sync_positions, dynamic subscribe |
| T-012 | Alle 37 Positionen anzeigen (tbl-wrap CSS) | WICHTIG | Braucht Dashboard-Neustart - DONE, aber Restart noetig |
| T-013 | Resolutions Panel aus Portfolio-Cache | WICHTIG | /api/resolutions auf _polymarket_positions (P010) |
| T-014 | Countdown-Spalte SCHLIESST IN | WICHTIG | endDate aus Polymarket-API (P009) |
| T-015 | P&L HEUTE = Portfolio-Delta seit Mitternacht | WICHTIG | Mitternacht-Snapshot fehlt (P014) |
| T-016 | Balance-Chart auf Portfolio-Total | WICHTIG | SQLite Spalte portfolio_total (P008) |
| T-006 | Duplikat-Wallet entfernen | WICHTIG | grep .env, doppelte Adresse loeschen (P006) |
| T-007 | Telegram-Commands: /balance /health /logs | NICE | telegram_bot.py erweitern |
| T-017 | Per-Wallet-Performance aus Signal-Counter | NICE | Signale tracken (P015) |
| T-018 | Log-Rotation TimedRotatingFileHandler | NICE | Kein Prozess-Neustart noetig (P018) |
| T-019 | WS-Events Counter verbessern | NICE | P013 - bereits deployed |
| T-020 | Timezone Berlin vereinheitlichen | NICE | P016 |

---

## BLOCKED

| ID | Titel | Blocker |
|----|-------|---------|
| T-008 | GitHub Push | Braucht GitHub Personal Access Token |
| T-021 | Public Status Repo KongTradeBot-Status | Abhaengig von T-008 |
| T-003 | Cloudflare Tunnel | Braucht cloudflared tunnel login mit Browser |

---

## DONE

| ID | Titel | Datum |
|----|-------|-------|
| T-D01 | Server Setup Hetzner Helsinki | 2026-04-17 |
| T-D02 | Magic-Link Proxy-Deploy via Norwegen-VPN | 2026-04-17 |
| T-D03 | signature_type=1 Fix deployed | 2026-04-17 |
| T-D04 | Min-Size-Check Fix deployed | 2026-04-17 |
| T-D05 | FillTracker condition_id Fix deployed | 2026-04-17 |
| T-D06 | Dashboard live (screen dash :5000) | 2026-04-17 |
| T-D07 | SSH-Key-Login eingerichtet | 2026-04-17 |
| T-D08 | /api/portfolio Endpoint + fetchPortfolio JS | 2026-04-18 |
| T-D09 | Dashboard: TOTAL PORTFOLIO VALUE Hauptzahl | 2026-04-18 |
| T-D10 | Dashboard: Cash + In Positionen Sub-Zahlen | 2026-04-18 |
| T-D11 | Dashboard: CLAIM ALL Button | 2026-04-18 |
| T-D12 | logger.py: propagate=False (Duplikat-Fix) | 2026-04-18 |
| T-D13 | balance_fetcher.py: Skip $0 RPCs | 2026-04-18 |
| T-D14 | dashboard.py: API-Fehler lesbar uebersetzen | 2026-04-18 |
| T-D15 | KNOWLEDGE_BASE.md P009-P021 (13 neue Bugs) | 2026-04-18 |
| T-D16 | Dynamic Subscribe FillTracker nach Orders | 2026-04-18 |
| T-D17 | Stale-Position-Recovery via Polymarket Data-API | 2026-04-18 |
| T-D18 | Auto-Claim alle 30min (claim_all.py) | 2026-04-18 |
| T-D19 | systemd kongtrade-bot.service enabled (Restart=always) | 2026-04-18 |
| T-D20 | Watchdog-Timer aktiviert (alle 60s) | 2026-04-18 |
| T-D21 | Morning-Report 08:00 Berlin + Portfolio-Daten | 2026-04-18 |
| T-D22 | CLAIM-Button: redeemable || isRedeemable | 2026-04-18 |
| T-D23 | Positionen-Tabelle: max-height 600px (alle 37 sichtbar) | 2026-04-18 |
| T-D24 | Commit b1c413a mit allen Nacht-Aenderungen | 2026-04-18 |

---

## IDEEN

| ID | Idee | Aufwand |
|----|------|---------|
| T-I01 | Telegram-Alert wenn Claim verfuegbar | Klein |
| T-I02 | Stop-Loss per Position (verkaufe wenn -50%) | Mittel |
| T-I03 | Wallet-Blacklist (Win-Rate < 30% -> stoppe Kopieren) | Klein |
| T-I04 | Multi-Bot Support (mehrere Proxy-Wallets) | Sehr hoch |
| T-I05 | Grafana/Prometheus fuer Metriken | Mittel |
