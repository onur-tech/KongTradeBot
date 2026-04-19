# Duplicate-Trigger-Bug Diagnose (19.04.2026)

_T-M04-Fix-Prep — Nur Diagnose, keine Code-Änderung_
_Basis: Activity-Report Commit 99e9b13, Logs 14:13-14:17_

---

## 1. Bug-Ereignis: 14:13 Timeline

### Log-Extrakt (exakt)

```
14:11:40 | INFO    | Budget-Cap überschritten: $538.49 >= $500.92           ← unrelated
14:13:52 | INFO    | 🐋 WHALE EXIT: [polymarke... verkaufte Yes auf 'US x Iran permanent peace deal by April'
14:13:52 | WARNING | Daily-Sell-Cap erreicht: $0.00 + $117.27 > $30.00      ← geblockt
14:14:53 | INFO    | 🐋 WHALE EXIT: [selbe Position]                          ← 61s später
14:14:53 | WARNING | Daily-Sell-Cap erreicht: $0.00 + $117.27 > $30.00
14:15:55 | INFO    | 🐋 WHALE EXIT: [selbe Position]
14:15:55 | WARNING | Daily-Sell-Cap erreicht: $0.00 + $117.27 > $30.00
14:16:56 | INFO    | 🐋 WHALE EXIT: [selbe Position]
14:16:56 | WARNING | Daily-Sell-Cap erreicht: $0.00 + $117.27 > $30.00
14:17:57 | INFO    | 🐋 WHALE EXIT: [selbe Position]
14:17:57 | WARNING | Daily-Sell-Cap erreicht: $0.00 + $117.27 > $30.00
```

### Fakten

| Fakt | Wert |
|------|------|
| **Position** | "US x Iran permanent peace deal by April" — Yes |
| **Trigger** | Whale-Follow-Exit (🐋 `_check_whale_exit()`) |
| **Volumen je Versuch** | $117.27 |
| **Intervall** | exakt 61 Sekunden (= `exit_loop_interval=60` + Laufzeit) |
| **Ergebnis** | Alle 5 geblockt — Daily-Cap $30, `_daily_sell_usdc` bleibt $0.00 |
| **Mode** | LIVE (cap check läuft nur wenn `exit_dry_run=False`) |

**Beobachtung:** `_daily_sell_usdc` bleibt bei $0.00 bei JEDEM Versuch.
→ Die Cap-Blockung verhindert das Sell UND das Inkrement. Der Counter hält kein Gedächtnis.

---

## 2. Root-Cause: Drei zusammenwirkende Faktoren

### Faktor A — Kein `whale_exit_done` Flag in ExitState

```python
# core/exit_manager.py — ExitState Dataclass (Zeile ~49):
@dataclass
class ExitState:
    tp1_done: bool = False         # ✅ vorhanden
    tp2_done: bool = False         # ✅ vorhanden
    tp3_done: bool = False         # ✅ vorhanden
    price_trigger_done: bool = False  # ✅ vorhanden (T-M04d Vorbild)
    # whale_exit_done: bool = False   # ❌ FEHLT
```

`_check_whale_exit()` setzt **keinen State** nach dem Trigger. Jede Evaluierung startet ohne Gedächtnis.

### Faktor B — get_recent_sells() 60-Minuten-Fenster + 60s Cache

```python
# core/wallet_monitor.py — Zeile ~448:
async def get_recent_sells(self, wallet_address: str, minutes: int = 60) -> List[dict]:
    _SELLS_CACHE_TTL = 60  # Sekunden

    cached = self._recent_sells_cache.get(wallet_lower)
    if cached and (now - cached[0]) < 60:
        return cached[1]  # Cache-Hit für 60s

    # ... API-Pull mit cutoff = now - (60 * 60) = letzte 60 Minuten
```

**Was das bedeutet:**
- Whale verkauft um 14:13:00
- Erster exit_loop um 14:13:52 → API-Pull → Sell gefunden → Trigger #1
- 60s Cache TTL → Cache läuft um 14:14:52 ab
- Zweiter exit_loop um 14:14:53 → Cache-Miss → neuer API-Pull → Sell NOCH IMMER im 60-Minuten-Fenster → Trigger #2
- ...
- Dies wiederholt sich bis ca. 15:13 (eine Stunde nach dem Whale-Sell)

**Mathematisch: bis zu ~59 Trigger-Wiederholungen möglich** (60 Minuten / 1 Minute Loop).

### Faktor C — Cap-Block verhindert kein Re-Trigger

```python
# core/exit_manager.py — evaluate_all(), Zeile ~447:
if await self._check_whale_exit(pos):
    event = await self._execute_exit(pos, state, 1.0, "whale_exit", current_price)
    if event:
        events.append(event)
        self._remove_state(pos.market_id, pos.outcome)  # State entfernt
    # ← HIER FEHLT: else: state.whale_exit_done = True
    continue
```

Wenn `_execute_exit` → `None` (cap geblockt):
- `event` ist `None` → `_remove_state()` wird NICHT aufgerufen
- State bleibt unverändert
- Kein Done-Flag gesetzt
- Position bleibt in `engine.open_positions`
- Nächster Loop: identische Evaluierung → identischer Trigger

### Zusammenfassung Root-Cause

```
Whale verkauft 14:13
       │
       ▼
exit_loop tick (60s) → get_recent_sells(minutes=60) → Sell gefunden
       │
       ▼
_check_whale_exit() → True (kein State-Memory)
       │
       ▼
_execute_exit() → $117.27 Sell
       │
       ├→ Cap $30 → geblockt → return None
       │       └→ KEIN Done-Flag, kein _remove_state → State unverändert
       │
       └→ Cap $200 → erfolgreich → open_positions.pop() → Position entfernt ✅
              (aber: wenn Sell SCHEITERT → gleiche Endlosschleife wie Cap-Block)
       │
       ▼
60 Sekunden warten
       │
       ▼
exit_loop tick → get_recent_sells → Whale-Sell NOCH IM 60-MIN-FENSTER → Trigger #2
       │
       ▼
[wiederholt sich bis 15:13]
```

---

## 3. Code-Evidenz

### _check_whale_exit() — kein State-Write

```python
# core/exit_manager.py — Zeile 154:
async def _check_whale_exit(self, pos) -> bool:
    """True wenn Whale verkauft hat → Komplett-Exit triggern."""
    sells = await self.wallet_monitor.get_recent_sells(pos.source_wallet, minutes=60)
    for sell in sells:
        sell_cid = sell.get("condition_id") or sell.get("market_id", "")
        if sell_cid == pos.market_id:
            logger.info(f"[ExitMgr] 🐋 WHALE EXIT: ...")
            return True  # ← Kein State-Update, nur return
    return False
```

### _execute_exit() — Cap-Check ohne Consequence-Handling

```python
# core/exit_manager.py — Zeile 336:
if not self.cfg.exit_dry_run and not self._check_daily_cap(usdc_received):
    return None  # ← früher Rücksprung, Position wird nicht aus open_positions entfernt
```

### evaluate_all() — fehlende else-Branch

```python
# core/exit_manager.py — Zeile 447:
if await self._check_whale_exit(pos):
    event = await self._execute_exit(pos, state, 1.0, "whale_exit", current_price)
    if event:
        events.append(event)
        self._remove_state(pos.market_id, pos.outcome)
    # ← ELSE fehlt: blocked/failed whale exit → kein Done-Flag
    continue
```

### exit_loop in main.py — Position-Removal nur bei erfolgreichem Live-Sell

```python
# main.py — Zeile ~948:
if not config.exit_dry_run:
    pos = engine.open_positions.get(ev.position_id)
    if pos:
        result = await engine.create_and_post_sell_order(...)
        if result["success"]:
            pos.shares = round(pos.shares - result["shares_sold"], 6)
            if pos.shares <= 0:
                engine.open_positions.pop(ev.position_id, None)  # ← nur hier entfernt
                exit_manager._remove_state(ev.condition_id, ev.outcome)
        else:
            logger.error(f"[exit_loop] Sell-Order fehlgeschlagen: {result['error']}")
            # ← Position bleibt in open_positions → re-trigger nächster Loop
```

---

## 4. Szenario-Simulation: Was wäre bei $200 Cap passiert?

### Szenario A: Cap $200, Sell API erfolgreich

| Tick | Zeit | daily_sell | Cap-Check | Sell-Result | open_positions |
|------|------|-----------|-----------|-------------|----------------|
| #1 | 14:13:52 | $0.00 | $0+$117.27<$200 ✅ | SUCCESS | Position gepopped ✅ |
| #2 | 14:14:53 | — | Position nicht mehr in open_positions | **Kein Trigger** | — |

**Ergebnis: KEIN Problem.** Einmaliger erfolgreicher Sell + Position entfernt → Loop bricht.

### Szenario B: Cap $200, Sell API scheitert (Network/Slippage)

| Tick | Zeit | daily_sell | Cap-Check | Sell-Result | open_positions |
|------|------|-----------|-----------|-------------|----------------|
| #1 | 14:13:52 | $0.00 | PASS | **FEHLER** | Position bleibt |
| #2 | 14:14:53 | $0.00 | PASS | **FEHLER** | Position bleibt |
| ... | ... | $0.00 | PASS | **FEHLER** | Endlosschleife |

**Ergebnis: Endlosschleife bis Whale-Sell aus 60-Min-Fenster fällt (~59 Fehler-Logs).**

### Szenario C: Cap $30 (IST-Zustand)

| Tick | Zeit | daily_sell | Cap-Check | Sell-Result |
|------|------|-----------|-----------|-------------|
| #1 | 14:13:52 | $0.00 | $0+$117.27>$30 ❌ | CAP BLOCK |
| #2 | 14:14:53 | $0.00 | $0+$117.27>$30 ❌ | CAP BLOCK |
| ... | ... | $0.00 | immer gleich | Endlosschleife |

**Ergebnis: Schutz durch Cap — aber $daily_sell_usdc bleibt $0, da Inkrement erst NACH Cap-Check.**

### Was würde passieren wenn Sell auf bereits-geschlossene Position:

```python
# execution_engine.py — create_and_post_sell_order():
# create_and_post_order() wird mit shares aufgerufen die Position nicht mehr hat
# Polymarket-API würde antworten:
#   - HTTP 400: "Insufficient balance" oder "No position found"
#   - Kein on-chain Effekt (keine Short-Position möglich bei Polymarket CTF)
# Bot würde result["success"]=False loggen → keine Katastrophe
# Aber: Fehler-Spam im Log, Telegram-Alert möglicherweise verstummt
```

**Fazit Szenario-Simulation:** Bei Cap $200 wäre das **wahrscheinlichste Ergebnis** ein einzelner erfolgreicher Sell + automatische Loop-Unterbrechung (da Position entfernt). Katastrophe nur bei API-Fehler oder DRY-RUN-Modus.

**DRY-RUN-spezifischer Bug:** Im DRY-RUN-Modus würde $200-Cap auch nicht schützen, weil cap check nur bei `exit_dry_run=False` läuft. Jeder exit_loop tick würde DRY-RUN-Log produzieren bis 15:13 (~59 Fake-Sell-Events).

---

## 5. Proposed Fix

### Empfehlung: E1 (Once-Only-Flag) als primärer Fix

**Analogie zu T-M04d `price_trigger_done`** — konsistentes Pattern im ExitManager.

**E1 — Minimale Änderung, größte Wirkung:**

```python
# core/exit_manager.py — ExitState Dataclass:
@dataclass
class ExitState:
    # ... bestehende Felder ...
    whale_exit_triggered: bool = False  # NEU: Once-only-Flag

# evaluate_all(), im for-pos-Loop, ERSETZE den whale-exit Block:
if await self._check_whale_exit(pos):
    if state.whale_exit_triggered:
        # Bereits versucht (erfolgreich oder geblockt) — skip
        logger.debug(f"[ExitMgr] Whale-Exit bereits getriggert für {pos.market_question[:30]}, skip")
        continue
    event = await self._execute_exit(pos, state, 1.0, "whale_exit", current_price)
    state.whale_exit_triggered = True   # NEU: immer setzen, egal ob event None oder nicht
    state_dirty = True                   # NEU: State persistieren
    if event:
        events.append(event)
        self._remove_state(pos.market_id, pos.outcome)
    continue
```

**Warum `whale_exit_triggered = True` auch bei Cap-Block:**
- Cap-Block bedeutet: Bot hat entschieden zu verkaufen, aber Tages-Limit ist erreicht
- Re-Trigger ist falsch: Wenn morgen früh Cap reset → Whale-Exit von gestern sollte NICHT feuern
- Einmal erkannt = einmal reagiert (auch wenn reaktion geblockt)

### E2 — Cooldown (Alternative, weniger präzise)

Statt "einmal immer" könnte man 60-Minuten-Cooldown setzen:
```python
whale_exit_last_attempt: float = 0.0  # unix ts
# Check: if time.time() - state.whale_exit_last_attempt < 3600: continue
```

**Nachteil:** Wenn Bot neu startet innerhalb der Stunde → frischer State → re-trigger möglich.
E1 ist besser.

### E3 — Defense-in-depth (zusätzlich, nicht statt E1)

In main.py exit_loop, nach fehlgeschlagenem Live-Sell:
```python
else:
    logger.error(f"[exit_loop] Sell-Order fehlgeschlagen: {result['error']}")
    # NEU: nach N Fehlern → ExitState done setzen
    exit_manager._mark_exit_failed(ev.condition_id, ev.outcome)
```

**Empfehlung:** E1 als primärer Fix. E3 als Zukunfts-Robustheit.

### Nicht empfohlen: Nichts tun + Cap erhöhen

Cap erhöht ohne Fix → Szenario A (meist OK) aber Szenario B (API-Fehler) → Fehler-Spam.
Außerdem: DRY-RUN-Modus hat auch ohne Cap den Bug (kein Cap-Check in DRY-RUN).

---

## 6. Aufwand-Schätzung für morgige Implementation

| Task | Datei | Aufwand |
|------|-------|---------|
| `whale_exit_triggered: bool = False` in ExitState | `core/exit_manager.py` | 2 min |
| Flag setzen in `evaluate_all()` (E1) | `core/exit_manager.py` | 5 min |
| `ExitState.from_dict()` ist bereits robust (ignoriert unbekannte Keys) | — | 0 min |
| Test: manuell 2x evaluate_all aufrufen, 2. Trigger darf nicht feuern | Server-SSH | 10 min |
| Commit + Deploy + Bot-Restart | — | 5 min |

**Gesamt: ~25 Minuten** — einfachster möglicher Fix.

---

## 7. Sicherheits-Empfehlung

**Cap $30 HEUTE NACHT belassen. Nicht auf $200 erhöhen.**

Begründung:
- Bug ist bekannt aber nicht gefixt
- DRY-RUN hat keinen Cap-Schutz → endlose Fake-Sell-Events würden Telegram fluten
- Bei Live-Mode Szenario B (API-Fehler) → Endlosschleife mit Fehler-Logs bis 15:13
- Fix ist 25 Minuten Aufwand — morgen früh als erste Aktion, dann Cap erhöhen

**Morgen-Sequenz:**
1. E1 Fix deployen (25 min)
2. Bot-Restart
3. Kurz beobachten (10 min) — kein Duplicate-Trigger im Log
4. Dann: Cap auf $200 setzen

---

## Summary

| Frage | Antwort |
|-------|---------|
| Wie oft triggert? | Bis zu ~59x (60-Min-Fenster / 60s-Loop) |
| Root-Cause | `whale_exit_done` Flag fehlt in ExitState |
| Warum nie inkrement? | Cap blockt vor `_daily_sell_usdc +=` |
| Bei $200 Cap + Erfolg | Nur 1x Trigger (Position entfernt → kein re-trigger) ✅ |
| Bei $200 Cap + API-Fehler | Endlosschleife (bis 60-Min-Fenster abläuft) |
| Bei DRY-RUN + $200 Cap | Endlosschleife (Cap wird in DRY-RUN ignoriert) |
| Fix | E1: `whale_exit_triggered: bool = False` in ExitState |
| Aufwand Fix | ~25 Minuten |
| Cap heute Nacht? | **$30 belassen — morgen erst fixen, dann erhöhen** |
| KB | P084 |
