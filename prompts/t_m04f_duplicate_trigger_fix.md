# T-M04f: Duplicate-Trigger-Fix — whale_exit_triggered Flag
_Vorbereitet: 2026-04-19 | Basis: analyses/duplicate_trigger_bug_diagnosis_2026-04-19.md_
_Aufwand: ~25 Minuten | PRIO: VOR Cap-Erhöhung auf $200_

---

## KONTEXT

**Bug:** Whale-Follow-Exit triggerte um 14:13 exakt 5x in Folge (61s-Intervall) auf dieselbe
Position. Daily-Cap $30 hat gerettet. Bei höherem Cap + API-Fehler: Endlosschleife.

**Root-Cause (aus Diagnose 1fd7ade):**
1. `ExitState` hat kein `whale_exit_triggered` Flag — alle anderen Exits haben es (`tp1_done`, `tp2_done`, `price_trigger_done`)
2. `get_recent_sells(minutes=60)` liefert denselben Whale-Sell 60 Minuten lang → ~59 Re-Trigger möglich
3. Bei Cap-Block gibt `_execute_exit` `None` zurück, ohne Done-Flag zu setzen → nächster Loop-Tick triggert identisch

**Sicherheits-Regel:** Cap NICHT erhöhen bevor dieser Fix deployed.

---

## PHASE 1: ExitState erweitern (~3 Minuten)

**Datei:** `core/exit_manager.py`
**Stelle:** `ExitState` Dataclass, ca. Zeile 49

Füge ein Feld hinzu — **nach `price_trigger_done`:**

```python
@dataclass
class ExitState:
    position_key: str
    entry_price: float
    tp1_done: bool = False
    tp2_done: bool = False
    tp3_done: bool = False
    trail_active: bool = False
    highest_price_seen: float = 0.0
    last_evaluated: float = field(default_factory=time.time)
    price_above_since: float = 0.0
    price_trigger_done: bool = False
    whale_exit_triggered: bool = False   # NEU — Once-Only-Flag (T-M04f)
```

**Backward-Kompatibilität:** `from_dict()` ist bereits robust (Zeile ~66):
```python
@classmethod
def from_dict(cls, d: dict) -> "ExitState":
    known = {f.name for f in cls.__dataclass_fields__.values()}
    return cls(**{k: v for k, v in d.items() if k in known})
```
→ Alter ExitState ohne `whale_exit_triggered` wird problemlos geladen (bekommt Default `False`).
**Keine Migration nötig.**

---

## PHASE 2: evaluate_all() Fix (~10 Minuten)

**Datei:** `core/exit_manager.py`
**Stelle:** `evaluate_all()`, Whale-Exit-Block, ca. Zeile 447

**ERSETZE diesen Block:**

```python
# VORHER (fehlerhaft):
if await self._check_whale_exit(pos):
    event = await self._execute_exit(pos, state, 1.0, "whale_exit", current_price)
    if event:
        events.append(event)
        self._remove_state(pos.market_id, pos.outcome)
    continue
```

**DURCH:**

```python
# NACHHER (T-M04f Fix):
if state.whale_exit_triggered:
    pass  # Already triggered — skip whale check entirely
elif await self._check_whale_exit(pos):
    event = await self._execute_exit(pos, state, 1.0, "whale_exit", current_price)
    state.whale_exit_triggered = True   # Immer setzen — auch bei Cap-Block (event=None)
    state_dirty = True
    if event:
        events.append(event)
        self._remove_state(pos.market_id, pos.outcome)
    continue
```

**Warum `True` auch bei `event=None`:**
- Cap-Block bedeutet Bot hat entschieden zu verkaufen, aber Tages-Limit ist erreicht
- Nächste Loop-Iteration soll NICHT erneut versuchen (Cap wäre immer noch gleich)
- Cap-Reset um Mitternacht → dann sowieso neuer State

**Warum `state_dirty = True`:**
- `_save_state()` persistiert das Flag auf Disk
- Bot-Restart lädt alten State → Flag bleibt `True` → kein Re-Trigger nach Restart

---

## PHASE 3: Verifikation (~10 Minuten)

### 3.1 — Syntaxcheck

```bash
cd /root/KongTradeBot
python3 -c "from core.exit_manager import ExitState, ExitManager; print('OK')"
```

### 3.2 — Backward-Compat-Test (ExitState ohne neues Feld laden)

```python
python3 -c "
from core.exit_manager import ExitState
# Simuliere alten State ohne whale_exit_triggered
old_dict = {
    'position_key': 'test|Yes',
    'entry_price': 0.55,
    'tp1_done': False,
    'tp2_done': False,
    'tp3_done': False,
    'trail_active': False,
    'highest_price_seen': 0.0,
    'last_evaluated': 1713523200.0,
    'price_above_since': 0.0,
    'price_trigger_done': False,
    # 'whale_exit_triggered' fehlt absichtlich
}
state = ExitState.from_dict(old_dict)
print('whale_exit_triggered:', state.whale_exit_triggered)  # Muss False sein
print('OK — Backward-Compat bestätigt')
"
```

### 3.3 — DRY-RUN Verifikation

```bash
# Bot läuft bereits — im Log nach Whale-Exit suchen:
tail -f /root/KongTradeBot/logs/bot_$(date +%F).log | grep -iE 'whale|exit_triggered'

# Erwartung bei Trigger:
# [ExitMgr] 🐋 WHALE EXIT: ...           (erster Trigger — normal)
# [ExitMgr] whale_exit bereits getriggert, skip   (alle weiteren — fix wirkt)
```

Oder zusätzlich diesen Debug-Log in `evaluate_all()` einbauen:

```python
if state.whale_exit_triggered:
    logger.debug(f"[ExitMgr] whale_exit bereits getriggert für {pos.market_question[:30]}, skip")
    pass  # skip
```

### 3.4 — Erfolgs-Kriterium

```
[ ] python3 -c "..." gibt 'OK' zurück
[ ] from_dict Test: whale_exit_triggered = False bei altem State
[ ] Im Log nach Bot-Restart: kein Duplicate-Trigger auf gleicher Position
[ ] Falls Whale-Exit feuert: genau 1x Log, dann silence
```

---

## CRITICAL STOPS

| Stop | Bedingung | Aktion |
|------|-----------|--------|
| SYNTAX-STOP | Import-Fehler nach Edit | Rollback via `git diff` + re-edit |
| COMPAT-STOP | from_dict wirft Exception | `known`-Filter prüfen — Zeile 67 |
| LOGIC-STOP | Flag wird nie True | `state_dirty = True` vergessen? |

**Kein Bot-Restart nötig während Fix** — Änderungen werden nach Restart aktiv.
Bot kann während des Edits weiterlaufen.

---

## DEPLOYMENT

```bash
git add core/exit_manager.py
git commit -m "fix(exit): whale_exit_triggered Once-Only-Flag — verhindert Re-Trigger (T-M04f)

Root-Cause: _check_whale_exit() hatte kein State-Memory. Bei Cap-Block oder
DRY-RUN feuerte der Whale-Exit bis zu 59x (60-Min-Sell-Fenster / 60s-Loop).

Fix: whale_exit_triggered Flag in ExitState — wird auch bei Cap-Block gesetzt.
Analog zu price_trigger_done (T-M04d). Backward-kompatibel via from_dict.

Refs: KB P084, analyses/duplicate_trigger_bug_diagnosis_2026-04-19.md"

sudo systemctl restart kongtrade-bot
```

---

## NACH DEM FIX

1. Bot-Restart abwarten (5–10s)
2. Log auf Fehler prüfen: `journalctl -u kongtrade-bot -n 50`
3. 5 Minuten beobachten
4. **Dann:** Cap $30 → $60 via `.env EXIT_DAILY_SELL_CAP_USD=60` + Restart
5. **NICHT** direkt auf $200 — erst 24h stabiler Lauf

---

## REFERENZEN

| Quelle | Inhalt |
|--------|--------|
| `analyses/duplicate_trigger_bug_diagnosis_2026-04-19.md` | Vollständige Root-Cause, Code-Evidenz, Szenario-Sim |
| `core/exit_manager.py:49` | ExitState Dataclass |
| `core/exit_manager.py:447` | evaluate_all() Whale-Exit-Block |
| `core/exit_manager.py:154` | `_check_whale_exit()` (keine Änderung hier) |
| KB P084 | Duplicate-Trigger-Pattern (allgemeines Prinzip) |
