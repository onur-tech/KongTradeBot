# Sell-Feature / Exit-Strategie / Reconciliation — Diagnose (19.04.2026)

**Erstellt:** 2026-04-19 | **Scope:** T-M04 / T-M05 / T-M06 | **Typ:** Phase-0 Diagnose — kein Code-Write

---

## A) Sell-Code-Status

| Komponente | Status | Pfad | Anmerkung |
|-----------|--------|------|-----------|
| `sell_position()` (als Funktion) | ❌ nicht vorhanden | — | Funktion heißt anders |
| `create_and_post_sell_order()` | ✅ vollständig | `core/execution_engine.py:636` | CLOB SELL, analog zu BUY |
| `claim_all.py` | ✅ vorhanden | `claim_all.py` | Separates Script für ConditionalTokens |
| CLOB-Client (py_clob_client) | ✅ integriert | `execution_engine.py:47`, `claim_all.py:67` | Buy + Sell möglich |
| Order-Management (ExitManager) | ✅ vorhanden | `core/exit_manager.py` | TP-Staffel + Trail + Whale-Exit |
| main.py Exit-Sell-Verkabelung | ✅ vorhanden | `main.py:919` | ruft `create_and_post_sell_order()` |

**Zusammenfassung:** Der Bot kann Sell-Orders via CLOB platzieren — die Funktion heißt `create_and_post_sell_order()` (nicht `sell_position`). Der ExitManager evaluiert Positionen und emittiert `ExitEvent`-Objekte. main.py's `exit_loop()` empfängt diese Events und ruft bei `exit_dry_run=False` die echte Sell-Funktion auf.

### Architektur-Pfad Sell (Ist-Zustand):

```
ExitManager.evaluate_all()          ← alle 60s aus main.py exit_loop
  → _check_whale_exit / _check_tp / _check_trail
  → _execute_exit(): LOG + Telegram + ExitEvent emittieren
      [exit_manager.py:265: "Part 2: hier execution_engine.sell_position aufrufen" → pass]
      ↓
main.py exit_loop (Zeile 919):
  if not config.exit_dry_run:
    engine.create_and_post_sell_order(asset_id, shares, min_price)
```

**Wichtige Beobachtung:** `exit_manager.py:265` hat einen `pass`-Placeholder-Kommentar für
"sell_position aufrufen". Das ist irreführend — die eigentliche Sell-Ausführung liegt in
`main.py:919`, NICHT im ExitManager. Der ExitManager ist absichtlich sell-agnostisch.

### Claim vs. Sell — Semantik:

| Operation | Wann | Wie | Datei |
|-----------|------|-----|-------|
| **Sell** (CLOB) | Markt noch aktiv (Preis < 100¢) | `create_and_post_sell_order()` → CLOB Order | `execution_engine.py:636` |
| **Claim** (Redeem) | Markt resolved (Gewinner = 100¢) | `redeem()` via py_clob_client | `claim_all.py` |

---

## B) Existierende Exit-Strategie

### Implementation

- **Datei:** `core/exit_manager.py` (letzte Änderung: Commit `2f71c35`)
- **Funktionen:**
  - `evaluate_all()` — Haupt-Evaluations-Loop, alle offenen Positionen
  - `_check_tp()` — TP-Staffel (3 Level)
  - `_check_trail()` — Trailing-Stop
  - `_check_whale_exit()` — Whale verkauft → Komplett-Exit
  - `_execute_exit()` — ExitEvent erstellen + Log + Telegram-Callback
  - `_should_skip()` — No-Exit-Guards (Wert zu klein / zu nah an Close)
- **Auslöse-Frequenz:** Alle 60 Sekunden (`exit_loop_interval=60`, nicht via .env überschrieben)
- **Integration:** Task `exit_loop()` in `main.py:884` — 6. parallele Async-Task

### Trigger-Bedingungen

| Bedingung | Variable | Konfigurierter Wert | Wirkung |
|-----------|----------|---------------------|---------|
| TP1 Schwelle | `EXIT_TP1_THRESHOLD` | **30%** (default) | 40% der Shares verkaufen |
| TP2 Schwelle | `EXIT_TP2_THRESHOLD` | **60%** (default) | weitere 40% verkaufen |
| TP3 Schwelle | `EXIT_TP3_THRESHOLD` | **100%** (default) | weitere 15% verkaufen |
| Boost min. Signale | `EXIT_MULTI_SIGNAL_BOOST_MIN` | **3** | TP-Schwellen erhöht |
| TP1 Boost | `EXIT_TP1_THRESHOLD_BOOST` | **50%** | bei ≥3 Signalen |
| TP2 Boost | `EXIT_TP2_THRESHOLD_BOOST` | **90%** | bei ≥3 Signalen |
| TP3 Boost | `EXIT_TP3_THRESHOLD_BOOST` | **150%** | bei ≥3 Signalen |
| Trail Aktivierung | `EXIT_TRAIL_ACTIVATION` | **+0.12 (12¢)** | Trailing-Stop aktiviert sich |
| Trail Abstand (liquid) | `EXIT_TRAIL_DISTANCE_LIQUID` | **0.07 (7¢)** | >$50k Volumen |
| Trail Abstand (thin) | `EXIT_TRAIL_DISTANCE_THIN` | **0.10 (10¢)** | <$50k Volumen |
| Skip wenn nah an Close | `EXIT_MIN_HOURS_TO_CLOSE` | **2** (geändert heute) | Skip wenn <2h bis Close |
| Min. Positions-Wert | `EXIT_MIN_POSITION_USDC` | **$3.00** (default) | unter $3 kein Exit |

**Alle Werte aus config.py-Defaults** — nur `EXIT_MIN_HOURS_TO_CLOSE=2` ist in .env gesetzt.

### EXIT_DRY_RUN-Status

- **In .env:** ❌ NICHT gesetzt
- **Aktueller Wert:** `True` (config.py default: `exit_dry_run: bool = True`)
- **Verhalten bei True:** ExitEvent wird erstellt + geloggt + Telegram-Alert gesendet. **Kein Sell-Order wird platziert.** main.py:915 `if not config.exit_dry_run:` → Zweig nicht betreten.
- **Verhalten bei False:** main.py ruft `engine.create_and_post_sell_order()` → echte CLOB-Order

> ⚠️ `DRY_RUN=false` (Trading LIVE) ≠ `EXIT_DRY_RUN=false` (Exits LIVE).
> Aktuell: Trading läuft live, aber Exits sind noch im Dry-Run-Modus.

### Warum Wuning-Position nicht verkauft wurde

Position: Fajing Sun, +180%, 158h bis Close, Preis ~100¢

**Analyse aller möglichen Ursachen:**

| Bedingung | Greift? | Begründung |
|-----------|---------|-----------|
| EXIT_MIN_HOURS_TO_CLOSE=2h | ❌ nein | 158h > 2h → kein Skip |
| exit_min_position_usdc=$3 | unklar | abhängig vom investierten Betrag |
| **Keine Position in engine.open_positions** | ✅ **Hauptursache** | `bot_state.json` date=None, 0 Positionen |
| exit_dry_run=True | ✅ Zusatzursache | selbst bei vorhandener Position: kein echtes Sell |
| Take-Profit-Trigger fehlt | ❌ FALSCH | TP1/TP2/TP3 bei 30%/60%/100% WÜRDEN feuern bei +180% |

**Root-Cause (zweistufig):**

1. **Primär:** `bot_state.json` speichert Positionen aber stellt sie nach Restart NICHT wieder her.
   `state_manager.py:81-84`: Positionen werden nur geloggt ("informativ"), nicht in `engine.open_positions` geschrieben. Kommentar: *"da wir keinen echten On-Chain Check haben"*. Das ist **By-Design**, aber bedeutet: Bei jedem Restart hat der Bot keine bekannten Positionen. Exit-Loop iteriert über leere Liste.

2. **Sekundär:** `EXIT_DRY_RUN` nicht auf `false` gesetzt → selbst wenn Positionen vorhanden wären, würden Exits nur geloggt, nicht ausgeführt.

**Schlussfolgerung:** T-M04 braucht kein neues Take-Profit-Feature — das existiert bereits. T-M04 braucht:
- (a) Positions-Reconciliation beim Start (On-Chain-Check via data-api → engine wiederherstellen)
- (b) EXIT_DRY_RUN auf false setzen sobald Sell-Funktion validiert ist

### Heutige Exit-Events

- Exit-Events im Log von heute: **0** (grep auf "ExitMgr" und "exit" zeigt keine Einträge)
- Ursache: 0 Positionen in engine.open_positions → exit_loop evaluiert nichts

---

## C) Dashboard-Zeitstempel-Semantik

### Ist-Zustand

Dashboard zeigt "Schliesst in" basierend auf zwei Quellen (Fallback-Kette):
1. `pos.market_closes_at` — gespeichert beim Trade-Eintrag (aus TradeSignal)
2. Gamma API `endDate` — nachgeladen via `_closes_in_label()` + Gamma-Cache

Quell-Code: `dashboard.py:597` und `dashboard.py:703-706`

```python
closes_in_s, closes_in_h = _parse_closes_in(p.get("market_closes_at"))
# Fallback:
end_date_str = (p.get("endDate") or p.get("endDateIso") or p.get("end_date"))
```

### Polymarket-API-Zeitstempel (Ist-Zustand)

Gamma API Market-Felder (getestet 2026-04-19):

| API-Feld | Bedeutung | Beispielwert |
|---------|-----------|-------------|
| `endDate` | Markt-Ende: letzter Zeitpunkt für Orders UND Haupt-Resolution-Zeitpunkt | `2026-07-31T12:00:00Z` |
| `endDateIso` | Wie endDate, nur Date-only | `2026-07-31` |
| `startDate` | Erstellungsdatum des Markts | `2025-05-02T15:48:00Z` |
| `acceptingOrders` | Boolean: Orders noch möglich? | `true` / `false` |
| `acceptingOrdersTimestamp` | Wann Order-Acceptance startete | `2025-05-02T15:47:37Z` |
| `closed` | Boolean: Markt geschlossen | `false` |
| `active` | Boolean: Markt aktiv | `true` |
| `updatedAt` | Letztes API-Update | `2026-04-19T09:41:22Z` |

**Wichtig:** Polymarket Gamma API hat **kein separates `resolutionTime`-Feld** und kein
`acceptingOrdersUntil`-Feld. `endDate` ist der einzige Zeitstempel — er bedeutet gleichzeitig
"Trading-Ende" und "ab wann Resolution möglich".

### Differenzierungsproblem

"Schliesst in" ist mehrdeutig weil `endDate` mehrere Ereignisse mischt:
- Trading-Ende (letzter Order-Zeitpunkt)
- Resolution-Beginn (Wann Outcome bekannt)
- Claim-Zeitpunkt (oft +24-72h nach endDate)

**Konkretes Problem bei Wuning:** Markt `endDate` liegt in 158h. Aber das Match (Fajing Sun) ist **heute faktisch entschieden**. Der `endDate` der Liga-Wette liegt in der Zukunft, unabhängig vom Spielergebnis.

### Differenzierung-Vorschlag (für T-M05)

| Was anzeigen | Welcher Wert | Herkunft |
|-------------|-------------|---------|
| "Trading bis" | `endDate` | Gamma API |
| "Ergebnis bekannt ab" | `endDate` + ~0-24h (Polymarket resolve) | Schätzung |
| "Claim ab" | `endDate` + 24-48h | Schätzung |
| "Markt faktisch entschieden?" | Preis ≥ 0.95 ODER ≤ 0.05 | CLOB Live-Preis |

---

## D) Reconciliation-Status

### Drift-Check

| Metrik | Wert |
|--------|------|
| Archive-Trades gesamt | **99** |
| Archive-Trades mit leerem tx_hash | **90** (91%) |
| Archive-Trades mit "pending_0x..." tx_hash | **9** (9%) |
| Archive-Trades mit bestätigtem tx_hash | **0** (0%) |
| On-Chain-Trades (data-api, Wallet `0x700BC5...`) | **36** |
| Drift (archive − on-chain) | **63** nicht nachvollziehbar |

**Erklärung der Diskrepanz:**
- "pending_0x..." → Trades, bei denen der tx_hash aus der API-Antwort kam, aber nie auf "bestätigt" aktualisiert wurde. 9 solcher Trades. Die Hashes sind real (z.B. `0x5706ca0...`).
- Leere tx_hashes → Trades, die im Archive geloggt wurden BEVOR oder OHNE erfolgreiche On-Chain-Bestätigung. Mögliche Ursachen: Signale wurden geloggt, dann aber die Order abgelehnt/nicht ausgeführt; oder tx_hash-Aktualisierung fehlt im Archivierungs-Code.

### Reconciliation-Code

**Existiert: NEIN.** Grep auf `reconcile`, `sync_onchain`, `check_drift` liefert keine Ergebnisse in der Codebase.

### Position-Restore-Bug (kritisch für Reconciliation)

`utils/state_manager.py:81-82`:
```python
# Positionen werden informativ geloggt aber nicht aktiv wiederhergestellt
# (da wir keinen echten On-Chain Check haben)
for pos in positions:
    logger.info(f"  Wiederhergestellt: {pos['outcome']} @ ...")
```
Positionen werden NICHT in `engine.open_positions` eingetragen. Beim nächsten Restart ist die Liste leer.
`bot_state.json` aktuelle Werte: `date=None`, `open_positions=[]`, `seen_tx_hashes=[]`

---

## E) Empfehlung für Phase 1 (nächste Session)

### Priorisierung

**Muss (T-M04 — geldkritisch):**
- **T-M04a**: EXIT_DRY_RUN=false in .env setzen NACHDEM T-M04b validiert
- **T-M04b**: Positions-Reconciliation beim Bot-Start — On-Chain-Check via `data-api/positions` → in `engine.open_positions` laden (ersetzt den `pass` in state_manager.py)
- **T-M04c**: Position-Restore in state_manager.py reparieren — aktuell `pass`-artiger Code

**Sollte (T-M04 Erweiterung):**
- **T-M04d**: Dashboard SELL-Button (manueller Trigger direkt aus UI)
- **T-M04e**: Teilverkauf-Support bei aktiven Märkten mit unrealisiertem Gewinn

**Kann warten:**
- **T-M05**: Dashboard-Zeitstempel-Differenzierung (3 Felder statt "Schliesst in")
- **T-M06**: On-Chain-Reconciliation (tx_hash-Bestätigungs-Loop)

### Konflikt-Risiken

| Risiko | Wahrscheinlichkeit | Mitigation |
|--------|-------------------|-----------|
| Race-Condition Auto-Exit vs. Manual-Sell | Hoch | position_lock / asyncio.Lock per position_id in sell_position() |
| EXIT_DRY_RUN Scope unklar | Mittel | Umbenennen: `AUTO_EXIT_ENABLED` + `MANUAL_SELL_ENABLED` — getrennte Flags |
| Claim vs. Sell falsch genutzt | Mittel | Bei `resolved=True` → Claim. Bei `active=True, price≥0.95` → Sell. Dashboard muss korrekt labeln. |
| Positions-Restore zu aggressiv | Niedrig | Nur Positionen vom heutigen Tag + CLOB-Preis-Check (bereits geplant) |
| tx_hash nie auf "confirmed" aktualisiert | Hoch | Archiv nach Execution-Bestätigung aktualisieren (T-M06) |

### Technische Vorbedingungen für T-M04

- [x] CLOB-Client voll funktional (BUY + SELL via `create_and_post_sell_order`)
- [x] ExitManager TP-Trigger vorhanden (30%/60%/100%)
- [ ] Position-Restore on-chain (data-api/positions → engine) — **blockierendes Item**
- [ ] EXIT_DRY_RUN=false validiert — **nach Position-Restore testen**
- [ ] tx_hash Archive-Update nach bestätigtem Sell — für T-M06

### Aufwandsschätzung Phase 1

| Task | Beschreibung | Schätzung |
|------|-------------|-----------|
| T-M04b | On-Chain Position-Restore bei Startup | **3h** |
| T-M04c | state_manager.py Restore-Bug fixen | **1h** |
| T-M04a | EXIT_DRY_RUN=false + Live-Test | **1h** (inkl. Validierung) |
| T-M04d | Dashboard SELL-Button | **3h** |
| T-M04e | Teilverkauf-Support | **2h** |
| T-M05 | Dashboard-Zeitstempel 3-fach | **2h** |
| T-M06 | tx_hash Reconciliation-Loop | **4h** |
| **Gesamt** | | **~16h (3-4 Sessions)** |

**Realistisch für eine Session:** T-M04b + T-M04c + T-M04a = 5h → ein fokussierter Tag.

### Offene Fragen (vor Phase 1 klären)

1. **Position-Restore via data-api/positions:** Das Endpoint gibt `redeemable`, `size`, `outcomeIndex`
   zurück — aber nicht `entry_price`, `shares`, `order_id`. Wie rekonstruiert man `OpenPosition`-Objekte
   vollständig? → Benötigt Abgleich mit `trades_archive.json` (nach tx_hash) oder separates API-Feld.

2. **Fair Sell Price bei Preis ~100¢:** Polymarket CLOB hat bei 99¢-100¢ Märkten sehr wenig
   Market-Maker-Liquidität auf der BUY-Seite. Was ist der erreichbare Fill-Preis? Ist Sell besser
   als Warten auf Claim? → Prüfen via CLOB orderbook für ein konkretes resolved-ähnliches Markt.

3. **EXIT_DRY_RUN Trennung:** Soll manueller Sell-Button im Dashboard immer sofort ausführen
   (unabhängig von EXIT_DRY_RUN)? → Semantik klären: `EXIT_DRY_RUN` betrifft Auto-Exit.
   Manueller Sell braucht eigenes Flag oder Override-Parameter.

### Ist Phase 1 in einer Session machbar?

**T-M04b + T-M04c + T-M04a (Kernpfad):** Ja, in ~5h. **Bedingung:** Offene Frage 1 (Position-Rekonstruktion) muss direkt zu Beginn entschieden werden — entweder partial-reconstruct aus Archive + data-api, oder nur Preis-Check ohne vollständige Position-Objekte.

**Vollumfänglich (inkl. T-M05/T-M06):** Nein, besser auf 2-3 Sessions verteilen.
