# KongTrade Foundation-Build Roadmap
_Erstellt: 22. April 2026 | Basis: Strategic Audit 2026-04-22_
_Status: AKTIV — Phase 0 abgeschlossen_

## Ziel
Multi-Glitch-Platform-Foundation sodass spätere Strategy-Plugins eingestöpselt werden können ohne Core-Refactor.

## Arbeitsprinzipien
1. **STOP-FIRST** — Nach jeder Phase Report + Stop. Onur reviewt, gibt Freigabe.
2. **NO-BREAKING-CHANGES** — Bot darf nie länger als 60s down sein. Atomar swappen.
3. **TEST-BEFORE-SWAP** — Unit + Integration Tests vor Produktiv-Swap. Rollback dokumentiert.
4. **AUDIT-CONFORMANCE** — Audit 2026-04-22 gewinnt bei Konflikt. Ausnahmen dokumentiert + freigegeben.
5. **NO-GITHUB** — Lokal committen, tar-Snapshots nach jeder Phase. Pushen wenn GitHub frei.

---

## Phasen-Übersicht

| Phase | Titel | Dauer | Status |
|---|---|---|---|
| 0 | Archiv & Audit-Ground-Truth | Tag 1, 1–2h | ✅ DONE |
| 1 | Trade-Metadaten-Schema | Tag 2–3, 4–8h | ⬜ PENDING |
| 2 | Safety-Layer (6 Module) | Woche 2, 5–7 Tage | ⬜ PENDING |
| 3 | Strategy-Plugin-Interface | Woche 3, 3–5 Tage | ⬜ PENDING |
| 4 | Copy-Trading auf Interface portieren | Woche 4, 3–4 Tage | ⬜ PENDING |
| 5 | Unified Data Warehouse (Postgres) | Woche 5, 4–5 Tage | ⬜ PENDING |
| 6 | Zweites Plugin: Weather-Strategie | Woche 6, 3–4 Tage | ⬜ PENDING |
| 7 | Drittes Plugin ODER Production-Hardening | Woche 7–8 | ⬜ ONUR ENTSCHEIDET |

---

## Phase 0 — Archiv & Audit-Ground-Truth ✅

**Abgeschlossen:** 22.04.2026

Deliverables:
- `docs/AUDIT_2026-04-22.md` — 609 Zeilen, 45 KB, vollständiger Audit
- `docs/AUDIT_INDEX.md` — Index mit Kern-Theses + Verwendungsregeln
- `TASKS.md` — Audit-Roadmap (7/30/90-Tage, 19 Tasks) oben eingefügt
- `SKILL.md` — Regel 13: Audit konsultieren vor jedem Feature/Refactor
- `backups/kongtrade_pre_foundation_20260422_1054.tar.gz` — 4.4 MB, 314 Files

---

## Phase 1 — Trade-Metadaten-Schema

**Ziel:** 40+ Feld SQLite-Schema live. Alle neuen Trades vollständig geloggt.

**Referenz:** AUDIT_2026-04-22.md, Abschnitt "Trade-Metadaten" (Teil C, Abschnitt 1)

**Deliverables:**
- `data/trades.db` — SQLite mit Tabellen: trades, signals, wallet_snapshots, cohort_attributes
- `core/trade_logger.py` — log_signal(), log_trade_entry(), log_trade_update(), log_trade_exit()
- Migration bestehender trades_archive.json (fehlende Felder = NULL)
- 3 Query-Views: cohort_by_category, wallet_attribution, slippage_histogram
- Dashboard-Tab "Cohorts" (einfache Tabelle)

**Acceptance:** Bot 1h live, Tabelle trades hat Einträge, cohort_by_category liefert Ergebnisse, Dashboard-Tab ohne Crash.

---

## Phase 2 — Safety-Layer

**Ziel:** 6 MUST-HAVE-Module aus Audit implementiert.

**Sub-Phasen:**
- 2.1 Reconciliation-Loop (1 Tag)
- 2.2 Signature-Type-Self-Check (0.5 Tag)
- 2.3 Slippage-Pre-Check (1 Tag)
- 2.4 Quarter-Kelly-Sizing (1 Tag)
- 2.5 Circuit-Breaker 3-Level (1.5 Tage)
- 2.6 Dead-Man-Switch (1 Tag) — Onur muss Healthchecks.io-Account anlegen
- 2.7 Hard-Stop mit Thesis-Invalidation (1 Tag)

**Acceptance:** Alle 6 Module aktiv, 1h Smoke-Test, min. 1 simulierter Trigger pro Modul.

---

## Phase 3 — Strategy-Plugin-Interface

**Ziel:** StrategyBase Abstract Base Class + PluginManager + unified_risk + unified_execution.

**Kritisch:** Das ist die wichtigste architektonische Entscheidung der Roadmap. Interface-Design sorgfältig reviewen.

---

## Phase 4 — Copy-Trading portieren

**Ziel:** copy_trading_v2.py als erstes echtes Plugin. 48h Shadow-Run, dann Cutover.

---

## Phase 5 — Unified Data Warehouse

**Ziel:** PostgreSQL 16 lokal, Schema-Migration von SQLite via Alembic, Backup-Cron.

---

## Phase 6 — Weather-Plugin

**Ziel:** weather_v2.py als zweites Plugin. DRY_RUN bis 30 Paper-Trades mit positivem Sharpe.

---

## Phase 7 — Onurs Entscheidung nach Phase 6

- **Option A:** Funding-Rate-Arbitrage (CEX via ccxt) — 2 Wochen
- **Option B:** Production-Hardening (CUSUM, Correlation-Filter, Walk-Forward) — 1–2 Wochen ← Empfohlen
- **Option C:** Feature-Freeze, 4 Wochen Paper-Trade-Akkumulation bis 200 Trades

**Empfehlung:** B → C → A

---

## Golden Rules

- `DRY_RUN=true` bleibt bis Onur explizit Live schaltet
- Jede neue Strategie startet in DRY_RUN-Mode
- Kein Code ohne Tests, kein Deploy ohne Smoke-Test
- Bei Unsicherheit: zurück zu Onur, nicht raten
- GitHub: wenn freigeschaltet → committen + pushen; gesperrt → lokal + tar
