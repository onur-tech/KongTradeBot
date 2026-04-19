# T-M08: Position-State-Machine Implementation-Prompt
_Vorbereitet: 2026-04-19 | Basis: analyses/position_state_bug_diagnosis_2026-04-19.md_
_Aufwand: ~3.5h | PRIO: nach T-M04e_
_Review: 2026-04-19 Abend — T-M04a/T-M04d/T-M04f Integration geprüft (siehe Update-Notes unten)_

---

## KONTEXT

**Problem:** Dashboard zeigt 25 Positionen als "Portfolio" — davon 14 faktisch beendet.
- 13 RESOLVED_LOST (redeemable=True, value=0) — erscheinen ewig in der Liste
- 1 RESOLVED_WON (redeemable=True, value>0) — wartete auf Claim
- AKTIV-Zähler soll 11 zeigen, zeigt 25

**Root-Cause (aus Diagnose f20e29e):**
Polymarket Positions-API liefert ALLE Wallet-Positionen — auch resolved. Eine Position
verschwindet erst nach on-chain `redeemPositions()`. Der Bot hat kein Cleanup-Job
und keine State-Klassifizierung.

**Einziger State-Indikator aus Polymarket-API:** `redeemable` (bool) + `currentValue` (float)

---

## PHASE 1: STATE-KLASSIFIZIERUNG IN api_portfolio() (~1h)

**Datei:** `dashboard.py`
**Funktion:** `api_portfolio()` — beginnt ca. Zeile 666

### 1.1 — position_state pro Position ableiten

Nach dem Block wo `redeemable` gesetzt wird (ca. Zeile 708-710), einfügen:

```python
# Position-State Klassifizierung (T-M08)
rd  = result[-1]["redeemable"]
val = result[-1]["current_value"]
if not rd and val > 0.01:
    ps = "ACTIVE"
elif not rd and val <= 0.01:
    ps = "TRADING_ENDED"    # Markt läuft noch, aber Preis = 0 (sehr unwahrscheinlich gewonnen)
elif rd and val > 0.01:
    ps = "RESOLVED_WON"     # redeemable + Wert vorhanden → Claim möglich
else:
    ps = "RESOLVED_LOST"    # redeemable + Wert = 0 → verloren, kein Claim-Nutzen
result[-1]["position_state"] = ps
```

### 1.2 — closes-gray Fix für RESOLVED_LOST Positionen (E1d)

Direkt danach:

```python
# E1d: closes-gray Fix — redeemable+$0 ist immer ENDED, egal was endDate sagt
if ps in ("RESOLVED_WON", "RESOLVED_LOST"):
    result[-1]["closes_in_class"] = "closes-ended"
    if ps == "RESOLVED_LOST" and result[-1]["closes_in_label"] not in ("ENDED", "VERLOREN"):
        result[-1]["closes_in_label"] = "ENDED"
```

### 1.3 — State-Zähler im Response ergänzen

Im `return _cors(jsonify({...}))` Block, neue Felder hinzufügen:

```python
"active_count":       sum(1 for r in result if r["position_state"] == "ACTIVE"),
"trading_ended_count":sum(1 for r in result if r["position_state"] == "TRADING_ENDED"),
"resolved_won_count": sum(1 for r in result if r["position_state"] == "RESOLVED_WON"),
"resolved_lost_count":sum(1 for r in result if r["position_state"] == "RESOLVED_LOST"),
```

Bestehenden `"redeemable_count"` BEHALTEN (für Backward-Kompatibilität).

### STOP-CHECK nach Phase 1:

```bash
curl -s http://localhost:5000/api/portfolio | python3 -c "
import json,sys
d=json.load(sys.stdin)
print('active:', d['active_count'])
print('resolved_lost:', d['resolved_lost_count'])
print('resolved_won:', d['resolved_won_count'])
for p in d['positions'][:5]:
    print(p['market'][:40], '->', p['position_state'])
"
```

**Erwartetes Ergebnis:** `active: 11`, `resolved_lost: 13`, `resolved_won: 0` (Fajing Sun inzwischen geclaimed)

Falls `active_count != 11`: Debug — zeige alle Positionen mit ihren `redeemable` + `current_value` Werten.

---

## PHASE 2: DASHBOARD FRONTEND (~1h)

**Datei:** `templates/` oder die HTML-Section in `dashboard.py` (je nach Struktur)

Suche im Frontend-Code nach `redeemable` und `VERLOREN` — dort ist die aktuelle Logik.

### 2.1 — AKTIV-Badge Zähler

Ändere den AKTIV-Counter von `data.count` auf `data.active_count`:

```javascript
// Vorher:
document.getElementById('active-count').textContent = data.count;

// Nachher:
document.getElementById('active-count').textContent = data.active_count;
```

Suche nach dem Element das die "OPEN" oder "AKTIV" Anzahl anzeigt.
Prüfe zuerst mit `grep -n 'active_count\|open.*count\|count.*open' templates/*.html` (oder equivalent).

### 2.2 — RESOLVED_LOST aus Hauptliste ausblenden

In der JS-Rendering-Funktion für Portfolio-Positionen, filtere RESOLVED_LOST heraus:

```javascript
// In der Schleife die positions rendert:
const activePosns = data.positions.filter(p =>
    p.position_state === "ACTIVE" || p.position_state === "TRADING_ENDED"
);
// Render activePosns statt data.positions für die Haupttabelle
```

### 2.3 — RESOLVED_LOST-Sektion (Verluste)

Unter der Haupttabelle, separate Sektion für RESOLVED_LOST — kollabierbar:

```javascript
const lostPosns = data.positions.filter(p => p.position_state === "RESOLVED_LOST");
if (lostPosns.length > 0) {
    // Render collapsed section "VERLUSTE (N) — click to expand"
    // Jede Row: Markt-Name | Einsatz | PnL | VERLOREN-Badge
    // Kein CLAIM-Button, kein Sell-Button
}
```

### 2.4 — RESOLVED_WON Alert-Badge

```javascript
const wonPosns = data.positions.filter(p => p.position_state === "RESOLVED_WON");
if (wonPosns.length > 0) {
    // Zeige Alert-Badge: "⚡ N CLAIM(S) VERFÜGBAR — $X.XX USDC"
    // CLAIM-Button für jede RESOLVED_WON Position
}
```

### STOP-CHECK nach Phase 2:

- Dashboard öffnen: AKTIV-Zähler = 11 ✅
- VERLUSTE-Sektion sichtbar mit 13 Einträgen ✅
- Keine VERLOREN-Positionen mehr im AKTIV-Bereich ✅
- CLAIM-Alert nur bei RESOLVED_WON (aktuell 0 nach Fajing-Claim) ✅

---

## PHASE 3: RESOLVER AUTO-SAVE (~30min)

**Problem:** `check_resolved_markets_and_notify()` in `telegram_bot.py:815` sendet Telegram-Alert
bei resolved Markets, schreibt aber NICHT `aufgeloest=True` in `trades_archive.json`.
Deshalb: 106 Trades alle `aufgeloest=False`.

### 3.1 — Auto-Save in check_resolved_markets_and_notify()

Suche in `telegram_bot.py` nach:
```python
newly_resolved.append({
```

Direkt VOR dem `newly_resolved.append(...)` Block — nach dem `won`-Check — die Archive-Writes einbauen:

```python
# Auto-Save resolved trades in archive (T-M08 E1c)
try:
    from utils.tax_archive import _load_trades, _save_trades
    arch = _load_trades()
    changed = False
    for t in arch:
        mkt = t.get("market_id", "")
        if mkt == mid and not t.get("aufgeloest"):
            t["aufgeloest"] = True
            t["ergebnis"] = "GEWINN" if won else "VERLUST"
            changed = True
    if changed:
        _save_trades(arch)
        logger.info(f"[resolver] Auto-Save: {mid[:20]} → {'GEWINN' if won else 'VERLUST'}")
except Exception as e:
    logger.warning(f"[resolver] Auto-Save fehlgeschlagen: {e}")
```

**Achtung:** Matcher ist jetzt via `market_id` statt Titel-String — deutlich präziser.
Risiko 3 aus der Diagnose ist damit behoben.

### 3.2 — Manueller Migration-Run

```bash
# SSH auf Server:
cd /root/KongTradeBot
python3 resolver.py --save
```

**Erwartung:** `X Trades als aufgeloest=True markiert` im Output.

### STOP-CHECK nach Phase 3:

```bash
python3 -c "
import json
with open('trades_archive.json') as f: arch = json.load(f)
resolved = [t for t in arch if t.get('aufgeloest')]
print(f'{len(resolved)} / {len(arch)} Trades aufgeloest=True')
"
```

---

## PHASE 4: STATE-AWARE EXIT-TRIGGER INTEGRATION (~30min)

**Kontext (Update 2026-04-19 Abend):**
- T-M04d (Take-Profit >=95c) ist bereits **LIVE** (Commit e5d64e8) — ExitState.price_trigger_done
- T-M04e (Stop-Loss) steht noch aus — wird ExitState.sl_done nutzen
- T-M04f (Whale-Exit Once-Only) ist committed aber noch nicht deployed — ExitState.whale_exit_triggered
- Alle Exit-Trigger nutzen ExitState-Flags, **nicht** position_state aus OpenPosition
- T-M08's Aufgabe in Phase 4: `redeemable`-Guard in ExitManager damit RESOLVED Positionen
  nicht verkauft werden (ergänzt ExitState, ersetzt es nicht)
- Analog-Muster aus T-M04f: Once-Only-Flags in ExitState — T-M08 fügt nur den `redeemable`-Check hinzu

**Datei:** `core/exit_manager.py` oder wo auch immer `_check_price_cap()` und `_check_stop_loss()` landen.

### 4.1 — State-Check vor Exit-Logik

Am Anfang von `_evaluate_position()` (oder equivalent), füge ein:

```python
# Nur ACTIVE Positionen sind sell-bar (T-M08)
# position_state wird von api_portfolio() berechnet; für ExitManager
# ableiten wir es aus den gleichen Feldern die wir haben:
# Wir brauchen redeemable und current_price.
# Wenn redeemable=True → Position ist resolved → KEIN Sell (wäre sinnlos)
if getattr(pos, 'redeemable', False):
    return None  # RESOLVED Position — nicht verkaufen, warten auf Claim/Ignore
```

**WICHTIG:** `redeemable` muss im `OpenPosition`-Dataclass vorhanden sein.

### 4.2 — OpenPosition Dataclass erweitern (falls nötig)

In `core/execution_engine.py`, `OpenPosition` Dataclass:

```python
@dataclass
class OpenPosition:
    # ... bestehende Felder ...
    redeemable: bool = False         # Neu: wird bei Position-Restore gesetzt
    position_state: str = "ACTIVE"   # Neu: ACTIVE | TRADING_ENDED | RESOLVED_WON | RESOLVED_LOST
```

### 4.3 — State beim Position-Restore setzen

In der Position-Restore-Logik (die T-M04a implementierte), beim Laden aus data-api:

```python
# Beim Restore aus Polymarket data-api:
redeemable = bool(any(p.get(k) for k in ("redeemable", "isRedeemable", "is_redeemable")))
cur_val = float(p.get("currentValue") or p.get("value") or 0)
if not redeemable:
    ps = "ACTIVE"
elif redeemable and cur_val > 0.01:
    ps = "RESOLVED_WON"
else:
    ps = "RESOLVED_LOST"
pos.redeemable = redeemable
pos.position_state = ps
```

### STOP-CHECK nach Phase 4:

```bash
# Im Log nach Bot-Restart:
grep "redeemable=True.*SKIP\|RESOLVED.*nicht verkaufen" /var/log/kongtrade/bot_$(date +%F).log | head -5
```

---

## PHASE 5: BACKWARD-KOMPATIBILITÄT & EDGE CASES

### 5.1 — bot_state.json upgrade

`state_manager.py save_state()` speichert Positionen ohne `position_state`. Das ist OK —
beim Laden wird `position_state` via data-api-Pull neu berechnet (T-M04a restore).

**Keine Änderung nötig** — Bestehende `bot_state.json` bleibt kompatibel.

### 5.2 — Fehler-Handling

Falls `_polymarket_positions["data"]` leer ist (API-Ausfall):
- `api_portfolio()` liefert leere Liste → `active_count = 0`
- Dashboard zeigt "0 Positionen" statt falsche Zähler
- Kein Bug, nur temporär leere Anzeige — OK

### 5.3 — Verhältnis zu T-M04 Exit-States (Update 2026-04-19)

T-M04d ist LIVE und nutzt **ExitState** (nicht OpenPosition.position_state):
```python
ExitState.price_trigger_done: bool   # T-M04d ✅ live
ExitState.whale_exit_triggered: bool  # T-M04f ✅ committed
ExitState.sl_done: bool               # T-M04e ⏳ pending
```

T-M08's `position_state` (ACTIVE/TRADING_ENDED/RESOLVED_WON/RESOLVED_LOST) in OpenPosition
ist **orthogonal** zu ExitState-Flags:
- ExitState verfolgt "welche Exits wurden schon ausgelöst"
- position_state verfolgt "in welchem Lifecycle-Status ist die Position"

Das hypothetische PENDING_SELL/SOLD aus dem ursprünglichen Design ist **nicht nötig** —
main.py's exit_loop entfernt Position sofort aus `engine.open_positions` bei erfolgreichem Sell.
Es gibt keinen "Pending"-Zwischenzustand in der aktuellen Architektur.

Dashboard-Frontend filtert `ACTIVE || TRADING_ENDED` → unbekannte States werden
automatisch in AKTIV-Bereich angezeigt (safe default für zukünftige States).

---

## DEPLOYMENT-SEQUENZ

```bash
# Phase 1+2 gemeinsam committen:
git add dashboard.py templates/
git commit -m "feat(dashboard): Position-State-Machine — AKTIV/WON/LOST Klassifizierung (T-M08 E1a-E1d)"

# Phase 3 commit:
git add telegram_bot.py
git commit -m "feat(resolver): Auto-Save aufgeloest=True bei resolved Markets (T-M08 E1c)"

# Phase 4 commit (falls OpenPosition Dataclass geändert):
git add core/execution_engine.py
git commit -m "feat(exit): State-aware Exit-Trigger — kein Sell bei RESOLVED Position (T-M08 E4)"

# Phase 3 Migration manuell:
python3 resolver.py --save
```

---

## CRITICAL STOPS

| Stop | Bedingung | Aktion |
|------|-----------|--------|
| P1-STOP | `active_count` nach Phase 1 ≠ 11 | Debug position_state per Position |
| P2-STOP | Dashboard zeigt immer noch 25 im Zähler | JS-Cache leeren, grep nach Counter-Element |
| P3-STOP | resolver.py --save bricht mit Exception | Prüfe Titel-Matching Logik, nutze market_id statt Titel |
| P4-STOP | Exit-Trigger verkauft RESOLVED-Position | EMERGENCY_STOP — check `pos.redeemable` guard |
| ROLLBACK | bot_state.json korrupt | `cp bot_state.json.bak bot_state.json && systemctl restart kongtrade-bot` |

**Immer vor Start:** `cp bot_state.json bot_state.json.bak.$(date +%F-%H%M)`

---

## VERIFIKATIONS-CHECKLISTE

Nach vollständiger Implementation:

```
[ ] api_portfolio gibt position_state pro Position zurück
[ ] active_count = 11 (oder aktueller Wert)
[ ] resolved_lost_count = 13 (oder aktueller Wert)
[ ] Dashboard AKTIV-Badge zeigt active_count
[ ] VERLUSTE-Sektion zeigt 13 Positionen (kollabiert)
[ ] RESOLVED_LOST hat closes-ended Label (nicht closes-gray)
[ ] resolver Auto-Save: nach 15min Interval → Log "Auto-Save: ... GEWINN/VERLUST"
[ ] Exit-Trigger ignoriert RESOLVED Positionen (kein sell attempt)
[ ] bot_state.json kompatibel (kein Schema-Break)
```

---

## REFERENZEN

| Quelle | Inhalt |
|--------|--------|
| `analyses/position_state_bug_diagnosis_2026-04-19.md` | Vollständige Diagnose, E1a-E4 Plan |
| `dashboard.py:666` | `api_portfolio()` — Einfügestelle E1a |
| `telegram_bot.py:815` | `check_resolved_markets_and_notify()` — Einfügestelle E1c |
| `core/execution_engine.py:132` | `OpenPosition` Dataclass — Einfügestelle E4 |
| `utils/state_manager.py:19` | `save_state()` — keine Änderung nötig |
| KB P075 | Position-State-Bug Dokumentation |
| KB P074 | Bot-Feature-Asymmetrie (Diagnose-Kontext) |
| KB P084 | Duplicate-Trigger-Pattern — Once-Only-Flag (analog für Phase 4) |
| T-M04d `e5d64e8` | Take-Profit live — ExitState.price_trigger_done (Vorbild für Phase 4) |
| T-M04f Prompt | whale_exit_triggered Pattern — Phase 4 Guard analog |

---

## UPDATE-NOTES (2026-04-19 Abend)

| Änderung | Grund |
|---------|-------|
| Phase 4 Intro: T-M04d als "future" korrigiert | T-M04d ist live seit e5d64e8 |
| Phase 5.3: PENDING_SELL-States als deprecated markiert | main.py popped Position sofort bei Sell — kein Pending-State nötig |
| Referenzen ergänzt | T-M04d, T-M04f, KB P084 als Kontext-Quellen |
