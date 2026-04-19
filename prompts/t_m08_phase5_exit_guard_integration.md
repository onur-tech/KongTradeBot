# T-M08 Phase 5: Exit-Guard State-Integration
_Vorbereitet: 2026-04-19 Abend | Voraussetzung: T-M08 Phase 4 Migration bestanden_
_Aufwand: ~20-30 Min | PRIO: nach Phase 4 STOP-CHECK bestanden_

---

## KONTEXT

Nach Phase 4 haben alle Positionen in `bot_state.json` einen korrekten `position_state`.
Phase 5 macht den ExitManager **state-aware**: Exit-Logik (Whale-Exit, Trailing-Stop, TP,
Stop-Loss) läuft nur noch für `ACTIVE` Positionen — RESOLVED, TRADING_ENDED und CLAIMED
werden automatisch übersprungen.

**Bereits deployed (nicht nochmal implementieren):**
- `whale_exit_triggered: bool = False` in ExitState → gesetzt in `_check_whale_exit()` (Commit 4d0b9bf, T-M04f)
- `price_trigger_done: bool = False` in ExitState → gesetzt in TP-Check (Commit e5d64e8, T-M04d)
- `tp1_done`, `tp2_done`, `tp3_done` in ExitState (T-M04d Staffel)

**Phase 5 ergänzt:** `position_state`-Guard **vor** allen Exit-Checks in `evaluate_all()`.

---

## VOR DEM START

```bash
# Backup
cp /root/KongTradeBot/bot_state.json /root/KongTradeBot/bot_state.json.bak.p5.$(date +%F-%H%M)

# Aktuelle evaluate_all() Struktur ansehen:
grep -n 'evaluate_all\|position_state\|whale_exit\|ACTIVE\|RESOLVED' \
  /root/KongTradeBot/core/exit_manager.py | head -40

# ExitState dataclass prüfen:
grep -n 'class ExitState\|whale_exit_triggered\|price_trigger_done\|tp[123]_done' \
  /root/KongTradeBot/core/exit_manager.py
```

---

## PHASE 5A: State-Guard in evaluate_all() (~15 Min)

### Ziel-Struktur in `evaluate_all()`

```python
async def evaluate_all(self, positions: list) -> list[ExitEvent]:
    events = []
    for pos in positions:
        state = self._get_or_create_state(pos.market_id, pos.outcome)

        # ── Phase 5: Position-State-Guard ──────────────────────────────
        position_state = getattr(pos, "position_state", "ACTIVE")
        if position_state in ("RESOLVED_WON", "RESOLVED_LOST", "CLAIMED"):
            continue  # Kein Exit — Position bereits abgeschlossen
        if position_state == "TRADING_ENDED":
            continue  # Kein neuer Sell — Markt geschlossen, kein Preis mehr
        # position_state == "ACTIVE" (oder UNKNOWN/None als Fallback) → weiter
        # ─────────────────────────────────────────────────────────────────

        # ... bestehende Exit-Logik (whale_exit, trailing-stop, TP, stop-loss) ...
```

### Implementierungsschritte

**Schritt 1: Guard einfügen**

```bash
nano /root/KongTradeBot/core/exit_manager.py
```

In `evaluate_all()`, direkt nach `state = self._get_or_create_state(...)`:

```python
        # Phase 5: Position-State-Guard
        position_state = getattr(pos, "position_state", "ACTIVE")
        if position_state in ("RESOLVED_WON", "RESOLVED_LOST", "CLAIMED", "TRADING_ENDED"):
            logger.debug(f"[exit_guard] Skip {pos.outcome[:20]} @ {pos.market_id[:12]}... — State: {position_state}")
            continue
```

**Wichtig:** `RESOLVED_WON` und `RESOLVED_LOST` haben `redeemable=True` — T-M04d's Claim-Trigger
ist separat in `main.py` über die Portfolio-API. ExitManager soll sie **nicht** nochmal anfahren.

**Schritt 2: OpenPosition dataclass erweitern**

`position_state` muss im `OpenPosition`-Objekt verfügbar sein. Prüfen ob bereits vorhanden:

```bash
grep -n 'position_state\|@dataclass' /root/KongTradeBot/core/execution_engine.py | head -20
```

Falls `position_state` noch nicht in `OpenPosition`:

```python
@dataclass
class OpenPosition:
    # ... bestehende Felder ...
    position_state: str = "ACTIVE"   # ← hinzufügen falls nicht vorhanden
    redeemable: bool = False          # ← hinzufügen falls nicht vorhanden
```

**Schritt 3: State-Restore aus bot_state.json**

In `state_manager.py` `restore_state()` — prüfen ob `position_state` beim Restore übernommen wird:

```bash
grep -n 'position_state\|open_positions\|restore\|from_dict\|asdict' \
  /root/KongTradeBot/utils/state_manager.py | head -20
```

Falls `OpenPosition` mit `**dict` konstruiert wird, ist `position_state` automatisch drin
(sobald im Dataclass-Default vorhanden). Falls manuell konstruiert:

```python
# In restore_state() wo OpenPosition-Objekte gebaut werden:
pos = OpenPosition(
    # ... bestehende Felder ...
    position_state=p.get("position_state", "ACTIVE"),
    redeemable=p.get("redeemable", False),
)
```

---

## PHASE 5B: State-Update im Exit-Loop (~5 Min)

`main.py` hat einen `exit_loop` der `evaluate_all()` aufruft und danach Positionen entfernt.
Der Loop muss den aktuellen `position_state` von der Portfolio-API in die OpenPosition-Objekte
schreiben **bevor** `evaluate_all()` aufgerufen wird.

### Ziel-Struktur in `exit_loop` (main.py, ~Zeile 926+)

```python
async def exit_loop():
    while True:
        await asyncio.sleep(60)
        
        # ── Phase 5: Position-States aus API aktualisieren ──────────────
        try:
            portfolio = await get_portfolio_states()  # api_portfolio() via HTTP oder direkt
            state_map = {p["condition_id"]: p.get("position_state", "ACTIVE")
                         for p in portfolio.get("positions", [])}
            for pos in engine.open_positions:
                cid = pos.market_id
                if cid in state_map:
                    pos.position_state = state_map[cid]
                else:
                    pos.position_state = "CLAIMED"  # nicht mehr in API = geclaimed
        except Exception as e:
            logger.warning(f"[exit_loop] State-Update fehlgeschlagen: {e}")
        # ─────────────────────────────────────────────────────────────────
        
        events = await exit_manager.evaluate_all(engine.open_positions)
        # ... restliche exit_loop Logik ...
```

**Alternativ (leichtgewichtiger):** State direkt aus `bot_state.json` lesen statt API-Call,
falls bot_state.json durch Phase 4 bereits korrekt befüllt ist und regelmäßig gespeichert wird.

```python
# Leichtgewichtige Alternative — aus bot_state.json
try:
    with open("bot_state.json") as f:
        saved = json.load(f)
    saved_map = {p["market_id"]: p.get("position_state", "ACTIVE")
                 for p in saved.get("open_positions", [])}
    for pos in engine.open_positions:
        if pos.market_id in saved_map:
            pos.position_state = saved_map[pos.market_id]
except Exception as e:
    logger.warning(f"[exit_loop] State-Restore: {e}")
```

---

## PHASE 5C: STOP-CHECKs (~10 Min)

### Check 1: evaluate_all() Guard syntaktisch korrekt

```bash
cd /root/KongTradeBot
python3 -c "
import ast, sys
with open('core/exit_manager.py') as f: src = f.read()
try:
    ast.parse(src)
    print('✅ exit_manager.py: Syntax OK')
except SyntaxError as e:
    print(f'❌ Syntax Error: {e}')
    sys.exit(1)
"
```

### Check 2: OpenPosition.position_state verfügbar

```bash
python3 -c "
from core.execution_engine import OpenPosition
p = OpenPosition.__dataclass_fields__
print('position_state in OpenPosition:', 'position_state' in p)
print('redeemable in OpenPosition:', 'redeemable' in p)
"
```

**Erwartung:** Beide `True`

### Check 3: DRY-RUN Verifikation — RESOLVED/CLAIMED werden übersprungen

```bash
python3 - << 'EOF'
import asyncio
from core.exit_manager import ExitManager
from core.execution_engine import OpenPosition

async def test():
    em = ExitManager(dry_run=True)
    
    # Test-Position mit RESOLVED_LOST
    pos_resolved = OpenPosition(
        market_id="test123", outcome="Yes",
        entry_price=0.5, size_usdc=10.0, shares=20.0,
        token_id="tok123", order_id="ord123"
    )
    pos_resolved.position_state = "RESOLVED_LOST"
    
    # Test-Position mit ACTIVE
    pos_active = OpenPosition(
        market_id="test456", outcome="Yes",
        entry_price=0.5, size_usdc=10.0, shares=20.0,
        token_id="tok456", order_id="ord456"
    )
    pos_active.position_state = "ACTIVE"
    
    events = await em.evaluate_all([pos_resolved, pos_active])
    print(f"Events: {len(events)} (sollte 0 oder nur für ACTIVE sein)")
    print("✅ Guard funktioniert" if True else "❌ FEHLER")

asyncio.run(test())
EOF
```

### Check 4: Bot-Log nach Restart — keine RESOLVED-Exit-Versuche

```bash
sudo systemctl restart kongtrade-bot
sleep 10
journalctl -u kongtrade-bot -n 30 | grep -iE 'exit_guard|RESOLVED|CLAIMED|evaluate_all|skip'
```

**Erwartung:** Log zeigt `[exit_guard] Skip ... — State: RESOLVED_LOST` für alle abgeschlossenen Positionen.

### STOP wenn:
- Syntax Error in exit_manager.py nach Änderung
- `position_state` nicht in OpenPosition dataclass
- Bot-Log zeigt Exit-Versuche für RESOLVED/CLAIMED Positionen
- ACTIVE-Positionen werden fälschlicherweise übersprungen (0 evaluate_all Events total trotz
  aktiver Märkte)

---

## PHASE 5D: Integration-Test mit Live-Daten (~5 Min)

```bash
# 1 Exit-Loop abwarten (60s) und Log beobachten:
journalctl -u kongtrade-bot -f | grep -iE 'exit_guard|evaluate|whale|trailing|tp[123]|position_state'
```

**Erwartete Log-Muster:**
```
[exit_guard] Skip Yes @ Atlanta Braves... — State: RESOLVED_LOST
[exit_guard] Skip Yes @ Fajing Sun... — State: CLAIMED
[exit_manager] evaluate_all: 11 ACTIVE, 13 skipped (RESOLVED_LOST/CLAIMED)
[exit_manager] whale_exit check: Yes @ US x Iran... (ACTIVE)
```

---

## ZUSAMMENFASSUNG: T-M08 Phase 1-5

| Phase | Was | Status |
|-------|-----|--------|
| Phase 1 | `position_state` in `api_portfolio()` | Server-CC |
| Phase 2 | Dashboard-Frontend RESOLVED-Trennung | Server-CC |
| Phase 3 | Resolver auto-save | Server-CC |
| Phase 4 | Migration bestehender Positionen | Prompt ready |
| Phase 5 | ExitManager state-aware Guard | Prompt ready (dieses Dokument) |

**Nach Phase 5:** Dashboard zeigt ~11 ACTIVE (statt 24). ExitManager touched nur ACTIVE.
RESOLVED/CLAIMED Positionen sind dauerhaft inaktiv bis manuell geclaimed oder archiviert.

---

## EDGE CASES

### position_state = None oder UNKNOWN (Legacy)
Guard-Zeile: `if position_state in ("RESOLVED_WON", "RESOLVED_LOST", "CLAIMED", "TRADING_ENDED")`
Alle anderen Werte (None, "UNKNOWN", "ACTIVE") fallen durch → normale Exit-Logik. Sicher.

### RESOLVED_WON mit Claim-Trigger
T-M04d's Claim-Trigger prüft `redeemable=True` in Portfolio-API — er läuft in `main.py`
**separat** vom ExitManager-Loop. Phase 5 deaktiviert nur ExitManager-Sells, nicht den Claim-Trigger.

### TRADING_ENDED vs RESOLVED_LOST
- `TRADING_ENDED`: Markt endet, Preis noch unbekannt (0-1c), keine Resolution. Kein Sell möglich.
- `RESOLVED_LOST`: Resolution confirmed, Preis = 0, redeemable=False. Claim bringt nichts.
Beide: kein Exit-Versuch. Correct.

### Neues Entry während Phase 5
Neue Positionen nach Deployment haben `position_state = "ACTIVE"` (Dataclass-Default).
Kein manueller Eingriff nötig.

---

## REFERENZEN

| Quelle | Inhalt |
|--------|--------|
| T-M08 Hauptprompt | Phase 1-3 (Voraussetzung) |
| `prompts/t_m08_phase4_migration.md` | Phase 4 (direkte Voraussetzung) |
| `core/exit_manager.py` | evaluate_all() — Haupt-Edit dieser Phase |
| `core/execution_engine.py` | OpenPosition dataclass — position_state Feld |
| `utils/state_manager.py` | restore_state() — position_state beim Restore |
| `main.py:926+` | exit_loop — State-Update vor evaluate_all() |
| Commit 4d0b9bf | T-M04f: whale_exit_triggered bereits deployed |
| Commit e5d64e8 | T-M04d: price_trigger_done bereits deployed |
