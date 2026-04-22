# Next-Session Tasks — Stand 2026-04-22

---

## TASK-1: wallet_performance.json Real/Paper-Trennung

### Problem
`wallet_performance.json` mischt echte Trades und DRY-RUN-Trades.
Der `WalletTracker` schreibt bei jedem Exit — egal ob `EXIT_DRY_RUN=false` oder
`DRY_RUN=true` — einen Eintrag ohne Unterscheidung.

**Konkrete Auswirkung:**
Wallets-Tab zeigt z.B. `weather-b: 20 Trades / 100% WR / +$662.45` — alle simuliert.
Diese Zahl ist irreführend und kann nicht für Entscheidungen genutzt werden.

### Geplante Lösung

**Backend — Schema-Erweiterung:**
- `wallet_performance.json` pro Trade ein Feld `"trade_mode": "real" | "paper"`
- `WalletTracker.record_trade()` erhält Parameter `dry_run: bool`, schreibt
  `trade_mode` entsprechend
- Alle Aufrufer von `record_trade()` in `main.py` / `execution_engine.py`
  übergeben `config.dry_run`

**Dashboard — UI:**
- Wallets-Tab Header: Toggle `[Alle] [Real] [Paper]`
- Per-Wallet-Zeile: Win-Rate und P&L reagieren auf Toggle
- API `GET /api/wallets?mode=real|paper|all` (Default: `all`)

**Betroffene Dateien:**
- `core/wallet_tracker.py` — `record_trade()` Signatur + Schreiblogik
- `main.py` — alle `record_trade()`-Aufrufe
- `data/wallet_performance.json` — Migration: bestehende Einträge bekommen
  `"trade_mode": "unknown"` (da Histor nicht rekonstruierbar)
- `dashboard.py` — `/api/wallets` Filter-Parameter
- `dashboard.html` — Toggle-UI

**Priorität:** Mittel — betrifft nur Analyse-Qualität, kein Sicherheitsproblem.

---

## TASK-2: "0 aktiv heute" — falsche Definition im Wallets-Tab

### Problem
Header im Wallets-Tab zeigt `N Wallets | 0 aktiv heute`, obwohl z.B.
62 Trades heute auf Polymarket sichtbar sind.

### Root-Cause
`active_today` (dashboard.py Zeile 1948) = Anzahl Wallets mit `signals_today > 0`.

`signals_today` = log-geparste Signal-Events des **Bots** für diese Wallet heute.
Nach einem Bot-Restart hat der laufende Prozess noch keine neuen Signale gesehen
→ `signals_today = 0` für alle Wallets → `active_today = 0`.

Das misst NICHT "hat diese Wallet heute auf Polymarket gehandelt", sondern
"hat der Bot heute ein Signal von dieser Wallet detektiert".

### Geplante Lösung

**Option A — Label korrigieren (minimal, sofort möglich):**
`"0 aktiv heute"` → `"0 Signale heute (seit Bot-Start)"` — ehrlichere Bezeichnung.

**Option B — Echte Aktivität messen:**
`active_today` aus `all_signals.jsonl` oder `wallet_decisions.jsonl` lesen
(persistente Dateien, überleben Bot-Restart). Zählt Wallets mit mindestens einem
Signal heute, unabhängig vom aktuellen Bot-Prozess.

**Empfehlung:** Option B, da die Zahl für Wallet-Scouting relevant ist.

**Betroffene Dateien:**
- `dashboard.py` — `api_wallets()` ab Zeile 1920: `signals_today` aus
  `all_signals.jsonl` lesen statt aus Log-Parse
- `dashboard.html` — Zeile 1328: ggf. Label anpassen

**Priorität:** Niedrig — kosmetisch, keine funktionale Auswirkung.

---

## Referenz: position_state_drift.md
Siehe `analysis/position_state_drift.md` für die 13 ungetrackten aktiven
Positionen (kein TP/SL-Management) und 8 State-Leichen.

---

## TASK-3: Copy-Trading-Buffer Hard-Crash Duplikat-Risiko

### Befund (2026-04-22)
`_agg_buffer` in `copy_trading.py` ist In-Memory (60s TTL). Primäre Duplikat-
Prüfung läuft über `seen_tx_hashes` (persistent in bot_state.json).

**Risiko:** Bei Hard-Crash (SIGKILL/OOM) vor `save_state()` gehen tx_hashes verloren.
Beim nächsten Start werden dieselben Wallet-Transaktionen nochmal detektiert →
Buffer wird neu befüllt → doppelte Order.

**Warum nicht jetzt gefixed:**
- Copy-Trading-Events sind einmalig (eine Whale-Tx); kein systematisches
  30-Min-Wiederholungs-Pattern wie beim Weather-Scout
- `seen_tx_hashes` überlebt normale Restarts (nur Hard-Crash betroffen)
- Scope für R3-Session klein halten

**Mögliche Lösung:**
`seen_tx_hashes` zwischen Orders sofort schreiben (nicht nur auf Shutdown),
oder `_agg_buffer` mit kurzem TTL (10 Min) persistieren.
