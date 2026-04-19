# KongTrade Bot — Task Tracking
_Stand: 2026-04-19 23:59 Berlin_

**Regeln:**
- Status: ARBEIT | QUEUE | DONE | BLOCKED | IDEE
- Prioritaet: KRITISCH | WICHTIG | NICE-TO-HAVE

## Task-Namespace-Konvention

| Prefix | Quelle | Beschreibung |
|--------|--------|-------------|
| T-DXX | Auto-Doc-Pipeline | Automatisch aus Commits erzeugt (auto_doc.py) |
| T-MXX | Manuell | Aus Chat-Prompts / Session-Planung |
| T-SXX | Strategisch | Langzeit-Roadmap-Items (Quartals-Horizont) |
| T-CXX | Collective | Kollaborations-Items (Alex/Tunay/Dietmar) |

**Regel:** Kein manueller Task bekommt mehr T-DXX. Pipeline und Mensch teilen keinen Namespace.

---

## IN ARBEIT

| ID | Titel | Prio | Notiz |
|----|-------|------|-------|
| T-M08-P4 | T-M08 Phase 4: Migration bestehender Positionen in bot_state.json | KRITISCH | **Prompt ready** (prompts/t_m08_phase4_migration.md) — MORGEN ZUERST |
| T-M08-P5 | T-M08 Phase 5: ExitManager state-aware Guard (evaluate_all) | KRITISCH | **Prompt ready** (prompts/t_m08_phase5_exit_guard_integration.md) — nach Phase 4 |
| T-M04b | Claim-Fix v2: relayer-v2 + RELAYER_API_KEY + signer=PRIVATE_KEY | WICHTIG | Credentials in .env — nach T-M08 |

---

## QUEUE

| ID | Titel | Prio | Notiz |
|----|-------|------|-------|
| Cap-Erhöhung | Daily-Sell-Cap $30 → $60 → $100 | WICHTIG | Sofort möglich nach T-M08 Phase 4 — T-M04f deployed |
| T-M04e | Stop-Loss-Trigger: Trigger B (24h+15c) + Trigger C (Drawdown 30%/40c) in ExitManager | WICHTIG | **Prompt ready** (prompts/t_m04e_stop_loss.md) — nach T-M08 |
| T-M09b | Multiplier: April#1 Sports 2.0x→0.3x + HOOK 2.0x→1.0x | WICHTIG | **Prompt ready** (prompts/t_m09b_multiplier_adjust.md) |
| T-M05 | Dashboard-Zeitstempel-Differenzierung (Trading bis / Resolution / Claim ab) | NICE | Zeitstempel-Research done |
| T-M06 | On-Chain-Reconciliation: Archive gegen live Positionen abgleichen | NICE | Abhängig von T-M04b |
| T-039 | weekly_doku_check.py Script (Freitag 17:00, Telegram-Report fuer Events ohne Doku) | NICE | — |
| T-D105 | Skipped-Signal-Shadow-Tracking: data/all_signals.jsonl + fiktive Performance | WICHTIG | IN PROGRESS — Server-CC |
| T-D106 | On-Chain-Wallet-Discovery-Scan (aktive Polygon-Wallets mit Polymarket-Trades) | WICHTIG | PENDING |
| T-D107 | External-Wallet-Data-API-Integration (predicts.guru-Scraping oder Polymarket-API) | WICHTIG | PENDING |
| T-D108 | Briefing v1.1 Publish + Shadow-DB Schema finalisieren | NICE | PENDING |
| T-D109 | 30-Day-Wallet-Review fuer aktuelle 10 TARGET_WALLETS | WICHTIG | SCHEDULED 2026-05-19 |
| T-M01 | Wallet-Audit v1.0 durchgefuehrt — 3 Wallets entfernt (RN1/Gambler1968/sovereign2013) | DONE | 2026-04-19 |
| T-M02 | Briefing v1.1 Post-Audit-Update — Teile 14/15/16 + HF-5 Hinweis | DONE | 2026-04-19 |
| T-M03 | T-D105 Skipped-Signal-Tracking Phase 1 PoC | IN PROGRESS | Server-CC |
| T-M10 | Builder-Code Integration: POLY_BUILDER_CODE in .env + create_and_post_order() | NICE | analyses/builder_code_setup_2026-04-19.md — erst nach 2 Wochen stabilem Betrieb |
| T-M10b | Scout v2: 9 Hard-Filter in utils/wallet_scout.py implementieren | WICHTIG | WALLET_SCOUT_BRIEFING.md Teil 4 |
| T-M11 | KongScore-Engine: 10 Soft-Score-Kategorien (SC-1 bis SC-10) | WICHTIG | WALLET_SCOUT_BRIEFING.md Teil 5 |
| T-M12 | Tiered System (A/B/C Pools) in core/state_manager integrieren | WICHTIG | Bootstrapping-Modus Toggle |
| T-M13 | Bootstrapping-Modus Toggle in .env (BOOTSTRAPPING_MODE=true/false) | NICE | Erste 90 Tage |
| T-M14 | shadow_wallets.db Schema + Tracking (REJECTED 90d, WATCHING unlimitiert) | WICHTIG | KONG_REVIEW_SYSTEM.md |
| T-M15 | Dashboard-Panel "WalletScout Kandidaten" (Tier A/B/C Übersicht) | NICE | — |
| T-M16 | Dashboard-Panel "Missed-Profit-Metric" (Shadow vs Active) | NICE | KONG_REVIEW_SYSTEM.md Ebene 3 |
| T-M17 | scripts/monthly_wallet_audit.py + systemd Timer (1. jeden Monats 06:00) | WICHTIG | KONG_REVIEW_SYSTEM.md |
| T-M18 | scripts/quarterly_criteria_review.py + Timer (1.4./1.7./1.10./1.1.) | NICE | Claude API + Grok |
| T-M19 | Post-Mortem-Generator (30-Tage-Review → KNOWLEDGE_BASE.md Eintrag) | WICHTIG | KONG_REVIEW_SYSTEM.md |
| T-M20 | Grok-Verifikations-Protokoll (nach Grok-Phase-0, T-S01) | NICE | WALLET_SCOUT_BRIEFING.md Teil 9.3 |
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
| T-028 | Alex/Tunay/Dietmar einladen | GitHub Account KongTradeBot gesperrt (P028) — support.github.com kontaktieren |

---

## DONE
| T-M04f | Duplicate-Trigger-Fix: whale_exit_triggered Once-Only-Flag in ExitState (4d0b9bf) | 2026-04-19 |
| T-M04d | Take-Profit-Trigger >=95c + Hold-Ticks + Daily-Sell-Cap (e5d64e8) | 2026-04-19 |
| T-M08-P1 | T-M08 Phase 1: position_state in api_portfolio() / dashboard.py (9f4ba4b) | 2026-04-19 |
| T-M08-P2 | T-M08 Phase 2: Dashboard-Frontend RESOLVED_LOST-Trennung (30791e4) | 2026-04-19 |
| T-M08-P3 | T-M08 Phase 3: Resolver auto-save via check_resolved_markets_and_notify() (9dcd2e0) | 2026-04-19 |
| Watchdog-Fix | Watchdog Race-Condition-Schutz verbessert (7ed82ac) | 2026-04-19 |
| Daily-Summary | Daily-Summary Timer 20:00 Berlin aktiv (3364181) | 2026-04-19 |
| log_trade-Fix | Exit-Events im Archive mit PnL korrekt (4537924) | 2026-04-19 |
| Legacy-Flag | 13 alte SELL-Einträge ohne tx_hash geflagged (5980e02) | 2026-04-19 |
| RN1-Diagnose | RN1 Zombie-Signal Diagnose: 296 Pre-Audit Entries, 0 Orders, benign (53809e1) | 2026-04-19 |
| P085-KB | KB P085: Multi-Signal-Buffer als emergenter Outlier-Filter dokumentiert | 2026-04-19 |
| T-M09 | Multiplier-Re-Kalibrierung: wan123 2.5x→0.5x, majorexploiter 3.0x→1.5x, denizz 0.5x→1.0x, HorizonSplendidView 2.0x→0.5x, kcnyekchno 2.0x→1.0x | 2026-04-19 |
| T-M07 | Wallet-Aufnahme Tier B: Erasmus 0.5x (Iran/ME) + TheSpiritofUkraine 0.3x (Geopolitics) (b97d9ef) | 2026-04-19 |
| T-M04-Ph0 | T-M04 Phase 0 Diagnose: Sell-Code existiert (636-746), EXIT_DRY_RUN Blocker, Claim-Bug, Position-Restore fehlt, Archive-Drift | 2026-04-19 |
| T-M08-Ph0 | T-M08 Phase 0 Diagnose: 14/25 Positionen beendet aber OPEN, Lifecycle dokumentiert (f20e29e) | 2026-04-19 |
| T-M04b-R | T-M04b Research: RelayClient-Empfehlung, NegRisk-Bifurkation, Implementation-Plan ~2h (82385dc) | 2026-04-19 |
| T-M04a | Position-Restore: engine.open_positions aus Data-API bei Bot-Start (57ff2e7) — 23 Positionen synced | 2026-04-19 |
| T-M04b-Cred | T-M04b Credential-Setup: RELAYER_API_KEY + RELAYER_API_KEY_ADDRESS in .env — Magic.link Key = PRIVATE_KEY bestätigt | 2026-04-19 |
| T-M04b-N | T-M04b Notification-only Zwischenlösung: broken client.redeem() durch Telegram-Alert ersetzt (3a7b4a9) | 2026-04-19 |
| Archive-Cleanup | Archive-Cleanup + Heartbeat-Fix: 18 Trades resolved, Schwelle 180s→360s (8bbdc98) | 2026-04-19 |
| Manual-Claims | Manuelle Claims: Wuning +$50.13 + Busan +$39.00 = +$89.13 USDC realisiert | 2026-04-19 |
| T-M06-Ph0 | T-M06 Phase 0 Diagnose: Archive-Drift 69%, Ghost-Trades, Steuer-Anforderungen (442185e) | 2026-04-19 |
| Builder-Research | Builder Program Research: Self-service API-Key, P076-Korrektur (relayer-v2, RELAYER_API_KEY) (3d3b74f) | 2026-04-19 |
| HOOK-Verif | HOOK + April#1 Sports Verifikation: April#1 Lifetime -$9.8M, Multiplier-Empfehlung dokumentiert (5d7d138) | 2026-04-19 |
| T-D83-P1.6 | T-D83 Phase 1.6: Discovery-Scan + Kategorie-Bug-Fix (63fc7ba, 8d9b08a) | 2026-04-19 |
| T-D104 | Audit v1.0: 3 Wallets entfernt (RN1, Gambler1968, sovereign2013) via HF-8 (7c29ac9) | 2026-04-19 |
| T-D103 | ✨ feat(analytics): Per-Wallet-Performance-Report mit Kategorie- und Zeitfenster-Aufschlüsselung (8689c4e) | 2026-04-19 |
| T-D102 | 🔧 chore: Nacht-Autopilot 18.04: Auto-Claim, Dynamic-Subscribe, Stale-Recovery, WS-Fix, Morning-Report Berlin-Zeit, 13 Bug-Fixes (b1c413a) | 2026-04-18 |
| T-D101 | 🔧 chore: TASKS.md: Nacht-Autopilot Status-Update (T-D15 bis T-D24) (89b5578) | 2026-04-18 |
| T-D100 | 🔹 ops: Konsolidierung Server-State — scripts/, fill_tracker, balance-fix, doku (857d82b) | 2026-04-18 |
| T-D99 | ✨ feat(T-022+T-010): Auto-Claim 5min + robust redeemable-Check + token_id-Guards (5c8cfb5) | 2026-04-18 |
| T-D98 | 📝 docs: T-006 geprueft, keine Duplikate (15 unique Eintraege) (45d60da) | 2026-04-18 |
| T-D97 | ✨ feat(strategy): MIN_TRADE_SIZE + MIN_WHALE_SIZE filter reduce micro-trade noise (f81980e) | 2026-04-18 |
| T-D96 | ✨ feat(dashboard): Layout-Redesign (vertikaler Platz) + Countdown-Spalte fuer offene Positionen (7608025) | 2026-04-18 |
| T-D95 | ✨ feat(tax+claim): tx_hash in archive + claim-error telegram alerts (19c0e63) | 2026-04-18 |
| T-D94 | ✨ feat(tax+ops): weekly-export + tunnel-broadcast + blockpit-timestamp (ff1c7d0) | 2026-04-18 |
| T-D93 | 🐛 fix(ops+dashboard): no-popup push + font+20% + countdown-fallbacks (32f623f) | 2026-04-18 |
| T-D92 | 🐛 fix(tax): frankfurter API URL migration for EUR rates (db69557) | 2026-04-18 |
| T-D91 | 🐛 fix(dashboard): countdown really works for all open positions (bde8d71) | 2026-04-18 |
| T-D90 | ✨ feat(scout): SQLite historization + trend detection + weekly report (b55ecf0) | 2026-04-18 |
| T-D89 | ✨ feat(telegram): inline menu + mute + daily digest + reduced spam (aeec617) | 2026-04-18 |
| T-D88 | 🐛 fix(telegram): API callbacks + persistent keyboard + startup rate-limit (5ec01d8) | 2026-04-18 |
| T-D87 | 🐛 fix(telegram): correct API field names for all callbacks (49a47b8) | 2026-04-18 |
| T-D86 | 🐛 fix(telegram): invest-field, today-snapshot, status-callback (fadb283) | 2026-04-18 |
| T-D85 | 🐛 fix(dashboard): snapshot not created when total=0 (positions not yet loaded) (86742fb) | 2026-04-18 |
| T-D84 | 🐛 fix(telegram): status-orders-fix, multi-signal-dedup, safe-callbacks (26a36c1) | 2026-04-18 |
| T-D83 | ✨ feat(exit): exit_manager module core (1/3) - logic + state + config (35c3f43) | 2026-04-18 |
| T-D82 | ✨ feat(exit): execution integration + telegram alerts + archive (2/3) (5e53632) | 2026-04-18 |
| T-D81 | ✨ feat(exit): tests + docs + deployment (3/3) (2f71c35) | 2026-04-18 |
| T-D80 | 🐛 fix(exit): wallet_monitor.get_recent_sells() implementiert für Whale-Follow-Exit (dd7b1df) | 2026-04-18 |
| T-D79 | 📝 docs: add Claude Code server setup section to SETUP.md (a2ad286) | 2026-04-18 |
| T-D78 | 🐛 fix(execution): AssetType enum statt String für CLOB allowance check (ca37af1) | 2026-04-19 |
| T-D77 | ✨ feat(monitoring): CLOB-Allowance-Health-Check + Telegram-Alerts (72fe533) | 2026-04-19 |
| T-D76 | 🐛 fix(risk): Budget-Cap blockiert neue Trades + Dashboard-Metrik (4b78a23) | 2026-04-19 |
| T-D75 | 🐛 fix(monitoring): CLOB-Balance-Check liest 'balance' statt 'allowance' (d9cbc2a) | 2026-04-19 |
| T-D74 | 🐛 fix(category): US-Sport + Tennis + Soccer Pattern-Matching + Backfill (e9f3cb5) | 2026-04-19 |
| T-D73 | 📝 docs: Strategic Vision + Roadmap-Tasks + Grok-Insight (P052) (d119412) | 2026-04-19 |
| T-D72 | 🐛 fix(errors): error_handler.py - Keine Silent-Fails mehr + Rate-Limited Telegram-Alerts + Dashboard-Endpoint (38741ae) | 2026-04-19 |
| T-D71 | ✨ feat(safety): Kill-Switch persistent mit Auto-Reset + Telegram-Commands (91e4d60) | 2026-04-19 |
| T-D70 | 📝 docs: COLLECTIVE_VISION.md + Peer-Modell + T-C01-10 + P054 + Skill.md Update (647237d) | 2026-04-19 |
| T-D69 | 🐛 fix(watchdog): Race-Condition-Fix - Lock-PID + Heartbeat Check + Rate-Limit (2fffe16) | 2026-04-19 |
| T-D68 | ✨ feat(analytics): Slippage-Tracking pro Trade + Wöchentlicher Report + Dashboard-API (35314c8) | 2026-04-19 |
| T-D67 | 🐛 fix(risk): portfolio_budget_usd includes position values to prevent false Budget-Cap (451c09f) | 2026-04-19 |
| T-D66 | 🐛 fix(dashboard): CLAIM-Button deaktiviert bei verlorenen Positionen ($0.00) (cdd0fb5) | 2026-04-19 |
| T-D65 | ✨ feat(automation): Auto-Doc-Pipeline mit 3-Ebenen-Struktur (85e6e33) | 2026-04-19 |
| T-D64 | ✨ feat(automation): Auto-Doc-Pipeline mit 3-Ebenen-Struktur (85e6e33) | 2026-04-19 |
| T-D63 | 🐛 fix(dashboard): CLAIM-Button deaktiviert bei verlorenen Positionen ($0.00) (cdd0fb5) | 2026-04-19 |
| T-D62 | 🐛 fix(dashboard): CLAIM-Button deaktiviert bei verlorenen Positionen ($0.00) (cdd0fb5) | 2026-04-19 |

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
| T-D22 | CLAIM-Button: redeemable \|\| isRedeemable | 2026-04-18 |
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
| T-D38 | Doku-Initiative: 5 Kerndokumente angelegt (STRATEGY, WALLETS, ARCHITECTURE, BACKTEST_RESULTS, SETUP) | 2026-04-18 |
| T-D39 | GUIDELINES.md: Doku-Pflicht + Commit-Format + Session-Recap institutionalisiert | 2026-04-18 |
| T-010 | Balance-Check-Bug (400 assetAddress invalid hex address) — Fix deployed, verifiziert via /api/logs (P029) | 2026-04-18 |
| T-D40 | Signal-Filter MIN_TRADE_SIZE $0.50 + MIN_WHALE_SIZE $5.00 (f81980e) | 2026-04-18 |
| T-D41 | Dashboard Redesign + Countdown-Spalte "Schließt in" + P038-Fix (7608025) | 2026-04-18 |
| T-D42 | tx_hash im Trades-Archiv für Steuer-Export (19c0e63) | 2026-04-18 |
| T-D43 | Weekly Tax-Export Freitag 23:55 Berlin, Blockpit-kompatibel (ff1c7d0) | 2026-04-18 |
| T-D44 | Frankfurter API Fix: .app → .dev/v1, 3-Layer-Fallback, Hetzner-IP-Block (db69557) | 2026-04-18 |
| T-D45 | WalletScout SQLite Historisierung + Weekly Report Sonntag 20:00 (b55ecf0) | 2026-04-18 |
| T-D46 | Telegram Overhaul: Inline-Menu + Mute-System + Daily Digest + Rate-Limit (aeec617) | 2026-04-18 |
| T-D47 | Dashboard: OAuth-Popup-Fix + Font +20% + Countdown-Fallbacks (32f623f, bde8d71) | 2026-04-18 |
| T-015 | P&L Heute = Portfolio-Delta seit Mitternacht — Fix via Midnight-Snapshot (fadb283, 86742fb) | 2026-04-18 |
| T-014 | Countdown-Spalte "Schließt in" — DONE via P038-Fix (7608025, 32f623f) | 2026-04-18 |
| T-022 | Auto-Claim Intervall 30min -> 5min + alle redeemable-Varianten — DONE (aeec617) | 2026-04-18 |
| T-D48 | Telegram-Bugfixes Wave 1: API-Feldnamen in Callbacks (49a47b8) | 2026-04-18 |
| T-D49 | Telegram-Bugfixes Wave 2: Invest-Feld + Midnight-Snapshot + Status-Callback (fadb283, 86742fb) | 2026-04-18 |
| T-D50 | Telegram-Bugfixes Wave 3: Status-2nd-Call-Site + Multi-Signal-Dedup + Safe-Callbacks (26a36c1) | 2026-04-18 |
| T-D51 | Claude Code auf Server als claudeuser (non-root, passwordless SSH, sudo ACLs) | 2026-04-18 |
| T-D52 | Exit-Strategie: TP-Staffel 40/40/15/5 + Trailing-Stop + Whale-Follow-Exit, DRY-RUN (35c3f43, 5e53632, 2f71c35) | 2026-04-18 |
| T-D53 | A1: AssetType-Enum Fix (ca37af1) | 2026-04-19 |
| T-D54 | A1: CLOB-Allowance-Health-Check + Telegram-Alerts (72fe533) | 2026-04-19 |
| T-D55 | A1: Budget-Cap Enforcement + Dashboard-Metrik (4b78a23, d9cbc2a) | 2026-04-19 |
| T-D56 | A2: US-Sport + Tennis + Soccer Pattern-Matching + Backfill (e9f3cb5) | 2026-04-19 |
| T-D57 | A3: error_handler.py — Keine Silent-Fails + Rate-Limited Alerts (38741ae) | 2026-04-19 |
| T-D58 | B1: Kill-Switch persistent mit Auto-Reset + Telegram-Commands (91e4d60) | 2026-04-19 |
| T-D59 | B2: Watchdog Race-Condition-Fix + Lock-PID + Rate-Limit (2fffe16) | 2026-04-19 |
| T-D60 | C1: Slippage-Tracking + Weekly Report (35314c8) | 2026-04-19 |
| T-D61 | UX-Fix: Dashboard CLAIM-Button deaktiviert bei $0-Positionen, VERLOREN-Label (cdd0fb5) | 2026-04-19 |
| T-C01 | COLLECTIVE_VISION.md angelegt (Peer-Modell, Governance, Roadmap) | 2026-04-19 |
| T-C02 | STRATEGIC_VISION.md angelegt (Langfrist-Roadmap, Tier 1-4, Moat) | 2026-04-19 |
| T-C03 | SKILL.md angelegt (9 Session-URLs + Punkte 10-12 Investment-Frameworks) | 2026-04-19 |
| T-C04 | P052 (Grok API als Twitter-Alternative) in KNOWLEDGE_BASE.md | 2026-04-19 |
| T-C05 | P053 (Skill-System-Audit) in KNOWLEDGE_BASE.md | 2026-04-19 |
| T-C06 | P054 (Peer-Modell Entscheidung) in KNOWLEDGE_BASE.md | 2026-04-19 |

---

## STRATEGISCHE ROADMAP (T-S)

| ID | Titel | Prio | Ziel |
|----|-------|------|------|
| T-S01 | Grok API Integration (Sentiment-Filter, $0.20/1M Tokens) | WICHTIG | Q2 2026 |
| T-S02 | Manifold Shadow-Run (Strategie-Validierung vor Polymarket-Deployment) | WICHTIG | Q2 2026 |
| T-S03 | Per-Wallet + Kategorie-PnL Performance-Report | WICHTIG | Q2 2026 |
| T-S04 | Exit-Strategy Live (nach Dry-Run-Analyse 24h) | KRITISCH | Q2 2026 |
| T-S05 | Mini-PC Setup (Manifold Shadow + Lokale Redundanz) | NICE | Q3 2026 |
| T-S06 | Tunay/Alex/Dietmar Onboarding (sobald GitHub-Sperre gelöst) | WICHTIG | Q2 2026 |

---

## COLLECTIVE TASKS (T-C) — Peer-Modell

| ID | Titel | Prio | Notiz |
|----|-------|------|-------|
| T-C07 | STATUS.md Generator: budget_utilization_pct + kill_switch_status + error_count_24h | NICE | scripts/generate_status.py |
| T-C08 | Watchdog-Timer manuell wieder aktivieren | KRITISCH | Wurde deaktiviert wegen Race-Condition |
| T-C09 | Performace-Report-Modul (Per-Wallet + Kategorie-PnL nach Session-Ende) | WICHTIG | — |
| T-C10 | Exit-Strategie Dry-Run-Analyse nach 24h (nächste Session) | KRITISCH | Audit dd7b1df |

---

## IDEEN

| ID | Idee | Aufwand |
|----|------|---------|
| T-I01 | Telegram-Alert wenn Claim verfuegbar | Klein |
| T-I02 | Stop-Loss per Position (verkaufe wenn -50%) | Mittel |
| T-I03 | Wallet-Blacklist (Win-Rate < 30% -> stoppe Kopieren) | Klein |
| T-I04 | Multi-Bot Support (mehrere Proxy-Wallets) | Sehr hoch |
| T-I05 | Grafana/Prometheus fuer Metriken | Mittel |
| T-I06 | Panic-Entry für korrelierte Sell-Offs | Mittel-Groß |
| T-I06a | Missed-Signal-Tracking (data/missed_signals.json — Basis für T-I06) | Klein |
| T-I07 | Sentiment-Bot Phase 0.5 (Free-Tier RSS+Reddit+Telegram, NUR Logging) | Groß |
| T-I08 | Decoy-Detection im Wallet-Scout (Hold-Duration, Hit-Rate-Drop, Exit-Pattern) | Mittel |
| T-I09 | Manifold-Shadow-Run (Paper-Trading-Validierung, utils/manifold_shadow.py) | Mittel |
| T-I10 | Claude-Analyst als Filter-Modul zwischen Signal und Execution | Mittel-Groß |
| T-I11 | Slippage-Tracking: whale vs our entry price delta, weekly report | Klein-Mittel |
| T-I12 | OpenClaw-Evaluation (parked, re-check in 2 Monaten) | Langfristig |

---

### T-I06 — Panic-Entry für korrelierte Sell-Offs (Detail)
**Trigger:** ≥3 offene Positionen fallen ≥15% in 2h, ≥2 verschiedene Kategorien,
jeweils ≥$10k Daily Volume. Optional: BTC gleichzeitig -3% (Bonus-Confidence).  
**Aktion:** 4h Panic-Mode, pausiert Exits, sucht in `data/missed_signals.json`
nach verpassten Whale-Entries: Whale noch drin + Preis ≥25% unter Whale-Entry +
Resolution >72h. Size 0.025x (halber Multiplier). Max 5 Late-Entries/Event,
max $50 Gesamt, max 1 pro Markt. Kill-Switch bei 50% Daily-Loss-Ausschöpfung.

### T-I07 — Sentiment-Bot Phase 0.5 (Detail)
**Modul:** `utils/sentiment_monitor.py`  
**Sources:** RSS-Feeds (20 kuratierte News-Quellen), Reddit API (r/politics,
r/worldnews, r/CryptoCurrency), Telegram Public Channels.  
**Pipeline:** Poll 2min → Dedup → Market-Matcher → Claude klassifiziert
(direction/materiality/credibility) → Signal in `sentiment_signals.jsonl` →
Telegram-Alert (NUR Info, KEIN Auto-Trade).  
**Phase 0.5 Ziel:** 2 Wochen Signals sammeln, gegen Preis-Bewegungen validieren.
Phase 1+2+3 erst nach >55% Accuracy.

### T-I08 — Decoy-Detection im Wallet-Scout (Detail)
Polymarket dokumentierte Sept 2025 "Copytrade Wars".  
**Track:** Average Hold Duration, Position-Size-Stdev, Hit-Rate 30d, Exit-Pattern.  
**Alert bei:** 50%+ kürzere Holds als Baseline, Öffnen/Schließen <24h, Hit-Rate-Drop >30%.  
Sonntag-Digest erweitern. Kritischer Decoy-Score → `data/suspected_decoys.json`
→ Copy-Filter: size halbieren oder skippen.

### T-I10 — Claude-Analyst als Filter-Modul (Detail)
**Modul:** `core/claude_analyst.py`  
**Input:** Signal + Whale-Historie + Market-Info.  
**Output:** action/confidence/reasoning/suggested_stake/kill_conditions. Threshold 0.7.  
Phase 1: Dry-Run (bewertet, ändert nichts). Phase 2: Gatekeeper. Phase 3: eigene Exit-Vorschläge.  
**Kosten:** ~$0.003/Analysis, ~$1.80/Monat bei 20 Signals/Tag.

### T-I11 — Slippage-Tracking (Detail)
Reddit-Tests zeigen 3-5¢ systematische Slippage. Logge bei jedem Copy-Trade:
`whale_entry_price`, `our_entry_price`, `delta_bps`. Wöchentlicher Report Freitag.
Alert wenn Trend >10bps steigt.

### T-I12 — OpenClaw-Evaluation (parked)
OpenClaw (Peter Steinberger), 329k GitHub-Stars. Unsere Architektur hat 80% davon.
Re-Evaluation in ~2 Monaten. Entscheidung heute: **Weg A** (Konzepte klauen,
Plattform nicht nutzen). Seit 4. April 2026 Anthropic-Subscription-Sperre →
separater API-Key nötig, Zusatzkosten. Siehe P047.

---

## 📝 SESSION-LOGS

### Session 2026-04-18 (Samstag)

**Fokus:** Infrastructure + Telegram-Stabilisierung + Exit-Strategie-Design

**Major Milestones:**
- Server-CC eingerichtet (claudeuser, non-root)
- 6 Telegram-Callback-Bugs gefixt in 3 Commit-Waves
- Passwordless SSH aktiviert
- Exit-Strategie designed (40/40/15/5 + Trailing + Whale-Exit)
- 7 neue strategische Tasks definiert (T-I06 bis T-I12)

**Portfolio-Stand (Abend):**
Total: ~$195 USDC | Net PnL: -$177 cumulative (Lerngeld, $1k Einsatz)
18 offene Positionen, 12 claimable. Sport-Resolutions heute
haben -$120+ beigetragen. Brrudi hat entschieden: kein Panic-Mode, Fokus auf Fundamentals.

**Lessons für nächste Sessions:**
- TASKS.md IMMER zu Session-Start lesen (Source of Truth)
- Doku-Updates gehen über CC, nicht Brrudi manuell
- Latenz-Argument gilt nicht für Copy-Trading-Märkte mit langen Haltedauern
- Reasoning-Quality > Speed für unsere Strategie
