# KongTrade Bot — Task Tracking
_Stand: 2026-04-18 07:30 Berlin_

**Regeln:**
- Status: ARBEIT | QUEUE | DONE | BLOCKED | IDEE
- Prioritaet: KRITISCH | WICHTIG | NICE-TO-HAVE

---

## IN ARBEIT

| ID | Titel | Prio | Notiz |
|----|-------|------|-------|

---

## QUEUE

| ID | Titel | Prio | Notiz |
|----|-------|------|-------|
| T-010 | Balance-Delta SEIT START reparieren | KRITISCH | Portfolio-Snapshot beim Start fehlt (P007) |

| T-012 | Alle 37 Positionen anzeigen (tbl-wrap CSS) | WICHTIG | Braucht Dashboard-Neustart - DONE, aber Restart noetig |
| T-013 | Resolutions Panel aus Portfolio-Cache | WICHTIG | /api/resolutions auf _polymarket_positions (P010) |
| T-015 | P&L HEUTE = Portfolio-Delta seit Mitternacht | WICHTIG | Mitternacht-Snapshot fehlt (P014) |
| T-016 | Balance-Chart auf Portfolio-Total | WICHTIG | SQLite Spalte portfolio_total (P008) |
| T-007 | Telegram-Commands: /balance /health /logs | NICE | telegram_bot.py erweitern |
| T-017 | Per-Wallet-Performance aus Signal-Counter | NICE | Signale tracken (P015) |
| T-018 | Log-Rotation TimedRotatingFileHandler | NICE | Kein Prozess-Neustart noetig (P018) |
| T-019 | WS-Events Counter verbessern | NICE | P013 - bereits deployed |
| T-020 | Timezone Berlin vereinheitlichen | NICE | P016 |

---

## BLOCKED

| ID | Titel | Blocker |
|----|-------|---------|




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
| T-D25 | Auto-Claim Script: $11.29 geclaimed (Brrudi manuell + Script Nacht) | 2026-04-18 |
| T-D26 | Bot-Neustart Nacht-Fixes aktiv (claim_loop, sync, dynamic subscribe) | 2026-04-18 |
| T-D27 | GitHub-Credentials + PAT auf Server gespeichert | 2026-04-18 |
| T-D28 | Public Repo KongTradeBot-Status angelegt + Initial-Push | 2026-04-18 |
| T-D29 | generate_status.py + push_status.sh deployed | 2026-04-18 |
| T-D30 | systemd Timer kongtrade-status-push alle 5min aktiv | 2026-04-18 |
| T-D31 | Defensive Config: Multiplier 0.15->0.05, MAX_POS=15, BLACKLIST, MIN_VOL | 2026-04-18 |
| T-D32 | WALLET_WEIGHTS env-Override in copy_trading.py implementiert | 2026-04-18 |
| T-D33 | Cloudflare Quick Tunnel kongtrade-tunnel.service aktiv | 2026-04-18 |
| T-D34 | tunnel_watcher.py + Timer -> Telegram-Alert bei URL-Aenderung | 2026-04-18 |
| T-D35 | generate_status.py: Dashboard-URL Abschnitt hinzugefuegt | 2026-04-18 |
| T-D36 | P022 struktureller Fix: PID-Lock + atexit + ExecStartPre (3 Ebenen) | 2026-04-18 |
| T-D37 | P026: Watchdog-HB-Fix + MIN_VOL-Bug (vol=0 fuelschlicherweise skip) | 2026-04-18 |
| T-D38 | T-010: token_id-Guard in _verify_order_onchain + restore + recover | 2026-04-18 |
| T-D39 | T-022: Auto-Claim 5min + is_claimable() alle 3 redeemable-Varianten | 2026-04-18 |
| T-D40 | T-006: Duplikat-Wallet-Check — OBSOLETE, 15 unique Eintraege, kein Duplikat | 2026-04-18 |
| T-D41 | Signal-Filter: MIN_TRADE_SIZE 0.50 + MIN_WHALE_SIZE 5.00 reduziert Micro-Noise | 2026-04-18 |
| T-D42 | Dashboard: Compact-Header (80px statt 30% Hoehe) + Countdown-Spalte (T-014) | 2026-04-18 |
| T-D43 | Paket A: tx_hash in tax_archive + Auto-Claim Fehler Telegram-Alert | 2026-04-18 |
| T-D44 | Paket B: Tunnel-Broadcast + Weekly-Tax-Export + Blockpit-Timestamp | 2026-04-18 |
| T-D45 | Dashboard-Verbesserungen: OAuth-Popup-Fix + Schrift +20% + Countdown-Fallbacks | 2026-04-18 |
| T-D46 | Wallet-Scout Historisierung: SQLite + Trend-Analyse + Weekly-Report | 2026-04-18 |
| T-D47 | Telegram Callbacks + Restart-Loop-Fix + Persistent Keyboard | 2026-04-18 |
| T-D48 | Exit-Strategie: TP-Staffel + Trailing-Stop + Whale-Follow-Exit (3 Teile) | 2026-04-18 | → 35c3f43 (Part 1), 5e53632 (Part 2), Part 3 pending |

---

## IDEEN

| ID | Idee | Aufwand |
|----|------|---------|
| T-I01 | Telegram-Alert wenn Claim verfuegbar | Klein |
| T-I02 | Stop-Loss per Position (verkaufe wenn -50%) | Mittel |
| T-I03 | Wallet-Blacklist (Win-Rate < 30% -> stoppe Kopieren) | Klein |
| T-I04 | Multi-Bot Support (mehrere Proxy-Wallets) | Sehr hoch |
| T-I05 | Grafana/Prometheus fuer Metriken | Mittel |

## 🚀 STRATEGISCHE ROADMAP-TASKS

### Infrastruktur für Multi-Asset

| ID | Task | Aufwand |
|----|------|---------|
| T-S01 | Grok API Integration als universelles signal_source Modul | Mittel |
| T-S02 | Config-Management zentralisieren (configs/*.yml pro Bot) | Klein |
| T-S03 | Dashboard erweitern um "Bot-Selector" (Polymarket/Manifold/...) | Mittel |
| T-S04 | Mini-PC als Manifold-Shadow-Node aufsetzen | Mittel |
| T-S05 | utils/grok_monitor.py mit X-Search + RSS + Reddit-Clients | Mittel-Groß |

### Neue Bot-Kandidaten (Reihenfolge nach Priorität)

| ID | Task | Aufwand |
|----|------|---------|
| T-S10 | KongFunding — Crypto Futures Funding-Rate Arbitrage | Groß |
| T-S11 | KongCrypto — Solana-Whale-Copy-Trading | Groß |
| T-S12 | KongSentiment — News-triggered Trading via Grok | Sehr Groß |
| T-S13 | KongStock-Insider — SEC EDGAR Monitor (13F, Form 4) | Mittel |
| T-S14 | KongSignals as a Service — B2B Signal-Verkauf | Sehr Groß |

### Meta-Plattform

| ID | Task | Aufwand |
|----|------|---------|
| T-S20 | KongHub Multi-Bot-Dashboard mit zentraler Kapital-Allokation | Groß |
| T-S21 | Gemeinsame Telegram-Integration für alle Bots | Klein |

## T-027 — Template-Repo vorbereiten [DONE]
- /root/template-ready/ vollständig: README, SETUP, ARCHITEKTUR, CONTRIBUTING, .env.example, LICENSE
- Privacy-Audit bestanden, alle sensitiven Daten entfernt
- Warte auf GitHub-Account-Entsperrung für Push

## T-028 — Alex/Tunay/Dietmar einladen [BLOCKED]
- Blocked by: GitHub-Account KongTradeBot gesperrt (P028)
- Action: support.github.com kontaktieren
- Resume: Template-Repo pushen sobald Account entsperrt
