# KongTrade Tasks
_Stand: 2026-04-26_

## IN ARBEIT
(keine — pre-restart-window aktiv)

## RESTART-PENDING
| ID | Titel | Action |
|----|-------|--------|
| R-01 | Mode-Resolver activate (SKIP/SHADOW/PAPER) | next bot restart |
| R-02 | Heartbeat-File-Write activate | next bot restart |
| R-03 | R4 reconciliation cleans 4 RECOVERED phantoms | next bot restart |

## QUEUE (Priorität absteigend)
| ID | Titel | Prio |
|----|-------|------|
| T-200 | Live-verify SHADOW/PAPER decisions in /api/v2/ops/mode-stats post-restart | KRITISCH |
| T-201 | After 30d shadow data → data-driven promote/keep decisions per category | WICHTIG |
| T-202 | Drift-Detector producer wiring (orphaned since Block A+) | WICHTIG |
| T-203 | trades.db `venue` column for cross-venue support | WICHTIG |
| T-204 | Pre-existing 14 test failures (test_heartbeat, test_phase4, test_reconciliation) | NORMAL |
| T-205 | Merge feat/ui-redesign-v2 → main (after restart-verification) | NORMAL |
| T-100 | Wallet-Audit auf Settlement-WR (25 Wallets) | KRITISCH (alt) |
| T-101 | Phase 5B Sim-Engine (Backtest + Orderbook-Replay + Fill-Sim) | WICHTIG (alt) |
| T-103 | Phase A Live-Test mit €2-5k, 5 Wallets, 30 Tage | KRITISCH (nach Audit) |
| T-104 | Wallet-Archetyp-Klassifizierung (Taleb/Simons/Soros/Fader) | WICHTIG (alt) |
| T-107 | API-Token Bright Data rotieren (Security) | WICHTIG (alt) |

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
