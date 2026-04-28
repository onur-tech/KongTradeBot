# KongTrade Tasks
_Stand: 2026-04-27_

## IN ARBEIT
(keine)

## RESTART-PENDING
| ID | Titel | Action |
|----|-------|--------|
| R-04 | Stop-Loss Trigger D (drawdown ≥50% AND >24h to close) | next bot restart |
| R-05 | Trend-Monitor Phase 1 (siehe T-220 Voraussetzungen) | next bot restart, nach watchlist + scrape_account |

## QUEUE (Priorität absteigend)

### Post-Live — Track-Aufgaben (T-D109/110/111)
| ID | Titel | Prio | Notiz |
|----|-------|------|-------|
| T-D109 | **Track A — Datenintegrität** (Tag 1-3 post-live): migrate_from_archive() UPDATE-Pfad statt INSERT, 8 historische Duplikate aus DB entfernen, audit_v1.1 mit migrate-consistency-check | KRITISCH (post-live) | T-D107.5 root-cause; PNL_INFLATION 21.3% bleibt FAIL bis dann |
| T-D110 | **Track B — Stub-Endpoints füllen** (Tag 3-7, T-215): /api/v2/eval/{recent-trades,trades,today}, markets/news/intel sub-tabs | NORMAL | data_audit Check 4 → OK wenn fertig |
| T-D111 | **Track C — Hardening** (Tag 5-7): max_dd_pct → echte Berechnung, mempool-watcher enable/raus, schema-rename still_open→unresolved, Cloudflare-URL aus generate_status.py, kong-trade.com/v2/* → / 301-Redirect | NORMAL | |

### Kritisch — V2-Cutover 2026-04-28 (alle erfordern GO via Telegram von Brrudi)
| ID | Titel | Prio | Notiz |
|----|-------|------|-------|
| T-D101 | Phase B1 Pre-Cutover-Verify — code/packages/staging-smoke clean | KRITISCH | 28.04. 09:00 Berlin · GO erforderlich |
| T-D102 | Phase C1 V2-Activation: USE_V2_SDK=true in .env, bot-restart DRY_RUN=true | KRITISCH | 28.04. 13:30 Berlin (post-cutover ~11 UTC) · GO erforderlich |
| T-D103 | Phase C2 pUSD-Wrap-Verify: balance reads, allowance, USDC→pUSD swap path | KRITISCH | 28.04. 13:45 Berlin · GO erforderlich |
| T-D104 | Phase D1 Live-Config: $80 Bankroll, COPY_SIZE_MULTIPLIER 0.02, MAX_TRADE_USD 8, Weather-only | KRITISCH | 28.04. 15:00 Berlin · GO erforderlich |
| T-D105 | Phase D2 Live-Restart: MODE=live DRY_RUN=false MAKER_ONLY=true | KRITISCH | 28.04. 15:05 · GO erforderlich + Brrudi-aktive-Aufsicht |
| T-D106 | Phase D3 60-Min Post-Live-Monitoring: Daily-Stop $50, watch maker-fills, latency, slippage | KRITISCH | 28.04. 15:05–16:05 · live-watch |

### Kritisch (laufend)
| ID | Titel | Prio | Notiz |
|----|-------|------|-------|
| T-200 | Live-verify SHADOW/PAPER decisions in /api/v2/ops/mode-stats post-restart | KRITISCH | nach 24h Whale-Signals beobachten |
| T-210 | `/eval/slippage` HTTP 500 fixen | KRITISCH | aktive Regression — wirft Error in UI |
| T-100 | Wallet-Audit auf Settlement-WR (25 Wallets) | KRITISCH (alt) | |
| T-103 | Phase A Live-Test mit €2-5k, 5 Wallets, 30 Tage | KRITISCH (nach Audit) | |

### Wichtig
| ID | Titel | Prio | Notiz |
|----|-------|------|-------|
| T-211 | `glitch_matrix.json` Glossary füllen (PnL, VaR, DD, CVaR, Sharpe, Wilson, PSR, Kelly, Cohort, edge_type, Counterfactual) | WICHTIG | schaltet System→Library + tooltip-Pattern frei |
| T-212 | `/eval/edge-type-distribution` toter Endpoint wire-up — case in eval.js fehlt | WICHTIG | Endpoint liefert echte 498b Daten, ungenutzt |
| T-213 | nginx `alias /root/KongTradeBot/public_status.json` → falscher Pfad (`/home/claudeuser/...`); `/status.json` returns 404 | WICHTIG | 1-Zeilen-Fix in /etc/nginx/sites-enabled/kongtrade |
| T-214 | `generate_status.py` HTTP 401 vom Cloudflare-Tunnel — STATUS.md zeigt "Dashboard nicht erreichbar" | WICHTIG | Tunnel hat eigene basic_auth-Layer; Skript braucht header oder lokalen Endpoint |
| T-220 | Trend-Monitor Phase 1 Activation — blockt auf: (a) 50-Account-Watchlist, (b) `scrape_account()` gegen Datasets-API trigger+poll | WICHTIG | siehe Telegram 27.04.03:25 für 3 Pfade |
| T-201 | After 30d shadow data → data-driven promote/keep decisions per category | WICHTIG | |
| T-202 | Drift-Detector producer wiring (orphaned since Block A+) | WICHTIG | |
| T-203 | trades.db `venue` column for cross-venue support | WICHTIG | |
| T-101 | Phase 5B Sim-Engine (Backtest + Orderbook-Replay + Fill-Sim) | WICHTIG (alt) | |
| T-104 | Wallet-Archetyp-Klassifizierung (Taleb/Simons/Soros/Fader) | WICHTIG (alt) | |
| T-107 | API-Token Bright Data rotieren (Security) | WICHTIG (alt) | |

### Normal
| ID | Titel | Prio | Notiz |
|----|-------|------|-------|
| T-215 | Markets/News/Intel Tabs: stub `{items:[]}` durch "coming soon" UI ersetzen ODER Backend liefern | NORMAL | 12/40 Sub-Endpoints |
| T-216 | Risk-Sub-Tabs (var, cvar, dd) konsolidieren auf funktionierendes `/risk/portfolio` | NORMAL | 3 leere `{}` |
| T-217 | tooltip system: `data-tooltip` pattern auf 7 sichtbaren Termen (PnL, VaR, DD, CVaR, Counterfactual, Sharpe, Wilson) — depends on T-211 | NORMAL | |
| T-204 | Pre-existing 14 test failures (test_heartbeat, test_phase4, test_reconciliation) | NORMAL | |
| T-205 | Merge feat/ui-redesign-v2 → main (after restart-verification) | NORMAL | |
| T-218 | Mode-resolver autoflush-Frequenz: in 615s nur 3× gefeuert statt 10× — diagnose | NORMAL | funktional, max 60s state-lag |

## DONE 2026-04-27
- T-D90 Domain migration: nginx basic_auth (kongview/kong-view2026) + V1 entfernt aus public, V2 primary @ kong-trade.com
- T-D91 Auth-Strategy Layer 1-5: write-protection (@localhost_only), rate-limit (60r/m), robots.txt+meta noindex, basic_auth removal, Tests A-E grün
- T-D92 Mode-Resolver live-cache-bump fix + SHADOW_MIN_SAMPLE 5→3 (1× Restart, 9 wallets prewarmed/86 entries)
- T-D93 Stop-Loss Trigger D (drawdown ≥50% AND >24h-to-close) in exit_manager.py + config (EXIT_SL_FAR_*)
- T-D94 Manual stop-loss (real) für 3 Iran/Hormuz RECOVERED positions: -$135.96 realized, capital freed $142.72
- T-D95 UI-Audit Track C: 40 Sub-Endpoints kartiert (17 live / 17 stub / 5 leer / 1 broken), reports/ui_audit_2026-04-27.md
- T-D96 STATUS.md drift fix: hard reset /root/status-repo (2103 stale auto-commits), push_status.sh komplett neu (fetch+ff-only-merge, fail-loud)
- T-D97 CAPABILITIES.md + services/trend_monitor/ skeleton + systemd unit (dormant, daemon-reload'd)
- T-D98 Doku-Sync: KB neuer Eintrag (P059), STATUS push, TASKS update, STRATEGY Live-Switch Hard Rules
- T-D99 Hotfix eval.js Syntax-Bug (`\\'shadow\\'` → `&#39;shadow&#39;`) + Cache-Busting `?v={{ asset_ver }}` für JS+CSS
- T-D100 Phantom-503 root-cause: nginx-Rate-Limit Zone "kongtrade" durch JS-Crash-Retry-Storm — kein Backend-Crash, kein Cloudflare (gibt's nicht in der Architektur)

## DONE 2026-04-26
- T-D70 Block C — UI redesign V2 deployed at /v2/ (Cyberpunk-Matrix, 9 tabs × 40 sub-tabs)
- T-D71 Iter1 — 15 data-verified UI bug fixes (5 commits)
- T-D72 Recovery R0-R4 — 4 OVERDUE RECOVERED resolved against gamma-api, -$70 booked
- T-D73 Postmortem-2 — hide reconciled phantoms in positions+resolutions endpoints
- T-D74 Shadow-Mode S1-S5 — SKIP/SHADOW/PAPER mode_resolver, replaces CATEGORY_BLACKLIST
- T-D75 Iter2 A — DB-schema renovation: 12 new columns, 433 rows backfilled
- T-D76 Iter2 B — resolution_tracker.py daemon + systemd timer (hourly)
- T-D77 Iter2 C — Cohort Sharpe + Wilson CI, counterfactual_pnl_hold, 6 new endpoints
- T-D78 Iter2 D — UI: Resolution-Match + Counterfactual sub-tabs + service-health fix
- T-D79 Iter2 E — pytest suite (28/28 green on touched modules)
- T-D80 Pre-restart fixes — /ops/services dict format + still_open edge_type
- T-D81 Backups: trades.db.pre-restart-26-04-2026.bak, bot_state.json.bak

## DONE 2026-04-24
- T-D50 Phase 3 Plugin-Interface merged
- T-D51 Phase 4 Copy-Trading-Plugin + YAML-Config merged
- T-D52 Phase 5A Signal-Scoring + Wallet-Decay + Categories merged
- T-D53 Bright Data Integration merged
- T-D54 5 Hotfixes (Heartbeat, WS-Reconnect, Kelly-Min-Size, sig_type, Emergency-Stop)
- T-D55 Marktrecherche V2 (7 Blöcke) auf research-share
- T-D56 GitHub-Account entsperrt (Wick-Case abgeschlossen)
- T-D57 Auto-Sync Post-Commit-Hook installiert

## T-D139 — Paper-Mirror Self-Health Check-D + Whale-Pfad-Test

**Owner:** Brrudi-decision morgen
**Priority:** medium (paper läuft jetzt; alarm-coverage-Lücke)
**Created:** 2026-04-28 22:00 Berlin (post T-D138 deploy)

### Context
T-D138 deployed paper-mirror (commits d3b1c90 + fe53266). Live-verified:
- Weather-Scout-Pfad triggert paper-mirror ✓ (Manila + London Entries 21:37/21:38)
- TP1-Exit funktioniert nach shares-bug fix ✓ (Manila +$24.57 21:40:53)
- Rollback env-toggle verified bidirectional ✓ (T-D138-V2 cross-check)

### Open Items
1. **Whale-Copy-Pfad noch ungetestet:** when a tracked-wallet opens a position,
   does paper-mirror.log_signal_as_paper() also fire? Theoretically yes (same
   on_copy_order hook), but no observation yet. Mock-signal test recommended.

2. **Alarm-Lücke:** Self-Health-Daemon (T-D133) watches decision-stillness
   but NOT paper-stillness specifically. If paper_exit_loop crashes mid-
   session, only service-bot.log catches it. Add Check-D:
   - "If `mode='paper'` insert-rate < 1/hour during active weather-scouts → WARN"
   - Insert into services/self_health.py alongside existing checks A-C.

3. **Daily-Report Erweiterung:** services/daily_summary.py shows live + paper
   PnL side-by-side, but no "Paper-Mirror health" section (last entry/exit
   timestamp, n entries last 24h vs expected 20-50, etc.).

### Files to touch (preview)
- `services/self_health.py` — add `_check_paper_stillness()` ~30 LOC
- `services/daily_summary.py` — add Paper-Health section ~20 LOC
- (optional) test script for mock-whale-signal trigger

## T-D139-V2 — CALIBRATED_CITIES filter blocks paper-mirror (HIGH priority)

**Owner:** Brrudi-decision morgen
**Priority:** HIGH (closes pace-gap to pre-28.04)
**Created:** 2026-04-28 22:15 Berlin (post T-D138-FOLLOWUP cross-check)

### Finding
`live_engine/main.py:1665` filtert `live_opps = [o for o in opportunities if not o.get('shadow_only') and o.get('token_id')]` BEVOR signals auf `on_copy_order` (und damit paper_mirror) treffen. Heute Abend: 32 SHADOW-ONLY blocks vs 10 calibrated → ~70% aller Weather-Opportunities erreichen paper-mirror nicht.

Pre-28.04 lief der entire Bot in DRY_RUN — kein equivalentes Filter-Gate. Daher Paper sah ALLE Cities, nicht nur calibrated.

### Fix-Skizze
In weather_loop (line ~1660), VOR der `live_opps = [...]`-Filterung:

```python
# T-D139-V2 — Paper-Mirror sieht ALLE opportunities, nicht nur calibrated
if paper_mirror.is_enabled():
    for opp in opportunities:
        try:
            # Build minimal CopyOrder for paper-only signal
            from core.wallet_monitor import TradeSignal
            from strategies.copy_trading_plugin import CopyOrder
            sig = TradeSignal(
                tx_hash=f"weather_paper_{opp['condition_id'][:14]}_{ts_short}",
                source_wallet="[weather-bot]",
                market_id=opp['condition_id'],
                token_id=str(opp.get('token_id', '')),
                side="BUY",
                price=float(opp['price']),
                size_usdc=paper_mirror.paper_size_usd(),
                market_question=opp.get('market', opp.get('city', '')),
                outcome=opp['direction'],
            )
            order = CopyOrder(signal=sig, size_usdc=paper_mirror.paper_size_usd(), dry_run=True)
            paper_mirror.log_signal_as_paper(order)
        except Exception as e:
            logger.warning(f"[Weather-Paper] {opp.get('city','?')}: {e}")

# (existing line 1665) live_opps filter applies only to LIVE pipeline
live_opps = [o for o in opportunities if not o.get('shadow_only') ...]
```

Effekt: Paper-Mirror trifft auf ALLE Weather-Opportunities (auch uncalibrated cities), Live-Pipeline bleibt unverändert auf calibrated.

### Test
Nach Deploy:
- Erwartung Paper-Entries/Tag: 30-50 (matching pre-28.04)
- Live-Trades unverändert (CALIBRATED_CITIES schützt weiterhin echtes Geld)

### Risk
- Low: nur additiv im weather_loop, try/except-Wrap, paper-mirror eigene DB-Spalte
- Bot-Restart nötig

### Schema-Verbesserung (parallel, MEDIUM priority)
Partial TP1/TP2/TP3 Exits sollten als SEPARATE trades.db Rows (matching pre-28.04 Schema), nicht UPDATE der Entry-Row. ~50 LOC in paper_mirror.paper_exit_loop. Verbessert Stats-Genauigkeit, kein PnL-Effekt.
