# Sell-Feature / Exit-Strategie Diagnose (19.04.2026 abends)
**Erstellt:** 2026-04-19 | **Scope:** T-M04 | **Typ:** Phase-0 Diagnose — kein Code-Write
**Update:** Abend-Session — Claim-Bug + Heartbeat + Dashboard-Analyse hinzugefügt

---

## A) Claim-Logic

### Wo implementiert
- **`claim_all.py`** (Zeilen 1–198) — eigenständiges Modul
- **Loop-Start:** `main.py:1041` — `claim_loop()` als AsyncTask, Interval 300s (5 Min)
- **Trigger:** `is_claimable(pos)` prüft Felder `redeemable / isRedeemable / is_redeemable` aus Data-API `/positions`

### Auto oder manuell?
**Beides — aber Auto ist kaputt.**

| Pfad | Status |
|------|--------|
| Auto-Claim (`claim_loop`, alle 300s) | ❌ Fehler 100% (Bug: `redeem()` nicht vorhanden) |
| Dashboard „CLAIM ALL"-Button | ❌ Öffnet nur `polymarket.com` im Browser — kein Backend |

### Kritischer Bug: `ClobClient.redeem()` existiert nicht
```
2026-04-19 11:23:23 ERROR polymarket_bot.claim
  redeem fehlgeschlagen für Fajing Sun:
  'ClobClient' object has no attribute 'redeem'
```
`claim_all.py:~85` ruft `client.redeem(condition_id)` — diese Methode existiert in `py_clob_client` **nicht**. `ConditionalTokens.redeem()` ist ein Smart-Contract-Call, kein CLOB-API-Endpoint.

### Warum Wuning nicht auto-geclaimed?
Loop feuert korrekt alle 300s, findet $50.13 redeemable. Schlägt an `client.redeem()` fehl → Exception, keine Ausführung.

### Dashboard `claimAll()` (dashboard.html:954–957)
```javascript
async function claimAll(){
  showToast('Polymarket öffnen → Positions → alle Claims einlösen', 'info');
  window.open('https://polymarket.com', '_blank');
}
```
Kein `POST /api/claim`. Nur Browser-Redirect. `unclaimed_amount` wird korrekt aus Data-API berechnet und angezeigt — Aktion dahinter ist Stub.

---

## B) Exit-Strategie

### Dateien + Funktionen
| Datei | Funktion | Zweck |
|-------|----------|-------|
| `core/exit_manager.py:69` | `ExitManager` | Haupt-Klasse |
| `core/exit_manager.py:147` | `_whale_exit()` | Whale-Follow (höchste Prio) |
| `core/exit_manager.py:169` | `_check_tp()` | TP1/TP2/TP3-Staffel |
| `core/exit_manager.py:192` | `_check_trail()` | Trailing Stop |
| `core/exit_manager.py:228` | `_execute_exit()` | Event + Telegram — KEIN Sell |
| `main.py:884` | `exit_loop()` | Alle 60s alle Positionen evaluieren |
| `main.py:843` | `on_exit_event()` | Callback → ggf. Sell-Order |
| `main.py:915` | Sell-Dispatch | Nur wenn `exit_dry_run=false` |

### Trigger-Bedingungen aktuell (Defaults `utils/config.py:37–56`)

| Trigger | Wert | Sell-Quote | Boost (≥3 Signale) |
|---------|------|------------|---------------------|
| TP1 | +30% | 40% | +50% statt +30% |
| TP2 | +60% | 40% | +90% statt +60% |
| TP3 | +100% | 15% | +150% statt +100% |
| Trail Activation | +12% Gain | — | — |
| Trail Distance (liquid Vol≥50k) | 7% unter Peak | 100% | — |
| Trail Distance (thin Vol<50k) | 10% unter Peak | 100% | — |
| Whale-Follow | Source-Wallet verkauft | 100% | — |

`EXIT_MIN_HOURS_TO_CLOSE=2` in `.env` (Default war 24h).

### EXIT_DRY_RUN Status
```
utils/config.py:39 → exit_dry_run: bool = True   # Hard-coded Default
.env               → EXIT_DRY_RUN nicht gesetzt
```
**Effektiv: `exit_dry_run=TRUE`** — ExitManager evaluiert und emittiert Events + Telegram, aber `create_and_post_sell_order()` wird nie aufgerufen.

### Was passiert bei Trigger?
```
exit_loop (60s) → evaluate_all() → _execute_exit() → ExitEvent (Telegram ✅)
                                                    → on_exit_event() Callback
                                                       → exit_dry_run=false? NEIN → kein Sell
```

### Wuning-Analyse — warum nicht getriggered?

Wuning-Position: Preis ~100¢, +180% PnL, 6d 14h bis Close.

**Grund 1 (Haupt): `engine.open_positions` leer nach Restart.**
`state_manager.py:81–84` loggt Positionen beim Laden, stellt sie aber **nicht** in `engine.open_positions` wieder her (by-design: „kein On-Chain-Check"). Nach Restart evaluiert `exit_loop` eine leere Liste.

**Grund 2: EXIT_DRY_RUN=true.**
Selbst wenn die Position in `open_positions` wäre: kein echter Sell.

**Grund 3: Kein direkter Preis-Trigger (≥95¢).**
TP3 (+100%) wäre bei Entry ~35¢ → 100¢ = +186% gefeuert — aber Grund 1 verhindert es.

---

## C) Sell-Code

### Existiert: JA — `core/execution_engine.py:636–746`

```python
async def create_and_post_sell_order(
    self,
    asset_id: str,
    shares: float,
    min_price: Optional[float] = None,
    exit_dry_run: bool = True,
) -> dict:
```

Vollständig implementiert: Tick-Size-Rounding, `OrderArgs(side=SELL_SIDE)`, `create_and_post_order()` (Single-Call), Retry max 3×, 500ms API-Sync, 3% Slippage-Tolerance.

### CLOB-Client Status
`ClobClient` instanziiert in `execution_engine.initialize()`. `set_api_creds()` gesetzt. Buy + Sell beide fähig — CLOB unterscheidet per `side` in `OrderArgs`.

### Blocker für echte Sell-Ausführung
1. `exit_dry_run=true` (Config-Default, nicht in `.env`)
2. `engine.open_positions` nach Restart leer → kein Candidate für ExitManager
3. Kein Preis-basierter Direkttrigger (≥95¢) — nur PnL%-basiert

---

## D) Dashboard CLAIM ALL

| Aspekt | Befund |
|--------|--------|
| Was macht der Button | Öffnet `polymarket.com` im neuen Tab — Stub |
| Backend-Endpoint | ❌ Keiner (`POST /api/claim` fehlt) |
| Synchron/Async | `async function` ohne echte Async-Arbeit |
| Fehler-Handling | `showToast()` UI-only, kein Error-State |
| `unclaimed_amount` | Korrekt aus Data-API berechnet (Wuning $50.13 ✅) |
| Auto-Claim Hintergrund | Läuft alle 300s, schlägt an `ClobClient.redeem()` fehl |

---

## E) Heartbeat

### Root-Cause der Warnung „274s ago"
**Kein echter Bug — normales Polling-Timing.**

| Parameter | Wert |
|-----------|------|
| Write-Interval | 300s — `main.py:973` |
| Watchdog-Timeout | 600s — `watchdog.py:40` |
| Letztes gemessenes Alter | 232s (< 600s) → **HEALTHY** |

274s = kurz vor nächstem 300s-Write-Cycle. Dashboard liest Timestamp, Bot schreibt noch nicht neu. Normal-Bereich 0–299s. Bei >600s würde Watchdog SIGTERM → SIGKILL → Restart auslösen.

### Fix nötig?
Nein. Optional: Write-Interval auf 60s reduzieren für smoothere Dashboard-Anzeige.

---

## F) Reconciliation

### Archive vs Blockchain

| Metrik | Wert |
|--------|------|
| Archive-Einträge total | 106 |
| Empty `tx_hash` | 90 (84.9%) |
| Pending `tx_hash` (`pending_0x...`) | 16 (15.1%) |
| Confirmed `tx_hash` | 0 (0%) |
| `aufgeloest=true` | 0 (0%) |

**Bot-Wallet:** `0x700BC51b721F168FF975ff28942BC0E5fAF945eb`

**Drift: Massiv.** Kein einziger Trade hat eine bestätigte On-Chain-Tx. `pending_` Prefix = früherer Code-Pfad schrieb Placeholder, der nie durch echte Tx-Hash ersetzt wurde. Konsequenz: PnL-Berechnung und Steuer-Export unbrauchbar.

---

## EMPFEHLUNG Phase 1 (morgen)

### Priorisierung + Aufwand

| Task | Beschreibung | Aufwand | Abhängigkeit |
|------|-------------|---------|-------------|
| **T-M04b** | `claim_all.py` — `redeem()` Bug fixen via Web3 / `redeem_positions()` | 4h | Unabhängig |
| **T-M04a** | `EXIT_DRY_RUN=false` + Position-Restore in `state_manager` (On-Chain-Abgleich via Data-API) | 3h | Basis für alle Exit-Tasks |
| **T-M04d** | Preis-Trigger `≥95¢ → Exit 100%` als neues Config-Feld | 2h | Braucht T-M04a |
| **T-M04e** | Dashboard: echter `POST /api/claim`-Endpoint | 2h | Braucht T-M04b |
| **T-M04c** | Dashboard: manueller Sell-Button (Position + % wählen) | 3h | Braucht T-M04a |

### Reihenfolge
```
1. T-M04b (Claim-Fix)          — Wuning $50 wartet, schneller Win, unabhängig
2. T-M04a (Position-Restore)   — Kernblocker, erst dann echte Exits möglich
3. T-M04d (≥95¢ Trigger)       — 2h nach T-M04a
4. T-M04e (Dashboard Claim)    — UX-Upgrade nach T-M04b
5. T-M04c (Dashboard Sell)     — Nice-to-have, ExitManager ersetzt es
```

### Abhängigkeiten
```
T-M04b ──► T-M04e
T-M04a ──► T-M04d
       ──► T-M04c
```

### Risiken + offene Fragen vor Phase 1

| Frage | Wichtigkeit |
|-------|-------------|
| `redeem()`: `py_clob_client.utils.redeem_positions()` verfügbar? Oder direkt Web3 `ConditionalTokens`-Contract? | 🔴 Kritisch |
| Position-Restore: Nur laufende Positionen via Data-API `/positions`? Oder Archive-Rekonstruktion? | 🟡 Mittel |
| Wuning jetzt manuell claimen? $50.13 liegt auf der Hand — vor Phase-1-Start auf Polymarket sichern | 🔴 Sofortmassnahme |
| `EXIT_DRY_RUN=false` stufenweise: erst Paper → dann Live? | 🟡 Mittel |
| Race-Condition Auto-Claim + Dashboard-Claim (doppeltes Redeem)? | 🟢 Gering |
