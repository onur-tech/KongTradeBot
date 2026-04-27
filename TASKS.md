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

### Kritisch
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
