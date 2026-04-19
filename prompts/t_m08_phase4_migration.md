# T-M08 Phase 4: Existing-Positions Migration
_Vorbereitet: 2026-04-19 Abend | Voraussetzung: T-M08 Phase 1-3 deployed_
_Aufwand: ~30-45 Min | PRIO: nach Phase 3 STOP-CHECK bestanden_

---

## KONTEXT

Nach Phase 1-3 kennt der Bot position_state — aber nur für **neue** Positionen die nach
dem Deployment einlaufen. Die 24 existierenden Positionen haben noch keinen korrekten State.

Phase 4 ist eine **einmalige Migration** die alle bestehenden Positionen ihrem korrekten
State zuweist, basierend auf Polymarket data-api Daten.

**Spezialfall:** Wuning + Busan heute manuell geclaimed — erscheinen nicht mehr in
Polymarket on-chain Positionen (redeemPositions() ausgeführt). Sie müssen als CLAIMED erkannt
werden, obwohl es keinen Bot-Trigger gibt.

---

## VOR DEM START

```bash
# Backup bot_state.json (immer!)
cp /root/KongTradeBot/bot_state.json /root/KongTradeBot/bot_state.json.bak.$(date +%F-%H%M)

# Aktuellen Portfolio-Stand holen:
curl -s http://localhost:5000/api/portfolio | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'Positionen total: {d[\"count\"]}')
for p in d['positions']:
    print(f'  {p[\"position_state\"]:15} | {p[\"cur_price_pct\"]:5.1f}c | rd={p[\"redeemable\"]} | {p[\"market\"][:40]}')
"
```

**Erwartung nach Phase 1-3:** Alle Positionen haben bereits `position_state` Field aus
`api_portfolio()`. Phase 4 überträgt diese States in `engine.open_positions` für den
Exit-Guard (Phase 5).

---

## PHASE 4A: State-Mapping Skript schreiben (~15 Min)

Erstelle temporäres Migrations-Skript (einmalig ausführen, danach löschen):

```bash
cat > /tmp/migrate_position_states.py << 'PYEOF'
#!/usr/bin/env python3
"""
T-M08 Phase 4: Einmalige Migrations-Script für Position-States.
Führt aus: python3 /tmp/migrate_position_states.py
"""
import json, sys, urllib.request, os

# --- Konfiguration ---
STATE_FILE = "/root/KongTradeBot/bot_state.json"
PORTFOLIO_API = "http://localhost:5000/api/portfolio"

# --- Portfolio von Dashboard-API holen ---
try:
    with urllib.request.urlopen(PORTFOLIO_API, timeout=10) as r:
        portfolio = json.loads(r.read())
    positions = portfolio.get("positions", [])
    print(f"[migration] {len(positions)} on-chain Positionen von API geladen")
except Exception as e:
    print(f"[ERROR] API nicht erreichbar: {e}", file=sys.stderr)
    sys.exit(1)

# --- State-Map bauen (condition_id -> position_state) ---
state_map = {}
for p in positions:
    cid = p.get("condition_id", "")
    ps  = p.get("position_state", "ACTIVE")
    if cid:
        state_map[cid] = ps

print(f"[migration] State-Map: {json.dumps({k[:12]+'...': v for k,v in state_map.items()}, indent=2)}")

# --- bot_state.json laden ---
if not os.path.exists(STATE_FILE):
    print("[WARNING] bot_state.json nicht gefunden — nichts zu migrieren")
    sys.exit(0)

with open(STATE_FILE, "r") as f:
    state = json.load(f)

open_pos = state.get("open_positions", [])
print(f"[migration] {len(open_pos)} Positionen in bot_state.json")

# --- States zuweisen ---
changed = 0
for pos in open_pos:
    cid = pos.get("market_id", "")
    if cid in state_map:
        old_state = pos.get("position_state", "UNKNOWN")
        new_state = state_map[cid]
        pos["position_state"] = new_state
        pos["redeemable"] = new_state in ("RESOLVED_WON", "RESOLVED_LOST")
        if old_state != new_state:
            print(f"  [update] {pos.get('outcome','?')} @ {pos.get('market_question','')[:40]}: {old_state} -> {new_state}")
            changed += 1
    else:
        # Nicht in on-chain API = wurde bereits claimed oder nie confirmed
        old_state = pos.get("position_state", "UNKNOWN")
        pos["position_state"] = "CLAIMED"
        pos["redeemable"] = False
        if old_state != "CLAIMED":
            print(f"  [claimed] {pos.get('outcome','?')} @ {pos.get('market_question','')[:40]}: nicht mehr in API -> CLAIMED")
            changed += 1

print(f"\n[migration] {changed} Positionen aktualisiert")

# --- Speichern ---
if changed > 0:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print("[migration] bot_state.json gespeichert ✅")
else:
    print("[migration] Keine Änderungen nötig")

# --- Zusammenfassung ---
summary = {}
for pos in open_pos:
    ps = pos.get("position_state", "UNKNOWN")
    summary[ps] = summary.get(ps, 0) + 1
print(f"\n[migration] Finale State-Verteilung: {summary}")
PYEOF
```

---

## PHASE 4B: Migration ausführen (~5 Min)

```bash
cd /root/KongTradeBot
python3 /tmp/migrate_position_states.py
```

**Erwartete Ausgabe:**
```
[migration] 24 on-chain Positionen von API geladen
[migration] State-Map: {...}
[migration] 23 Positionen in bot_state.json
  [update] Yes @ US x Iran permanent peace deal by April ...: UNKNOWN -> ACTIVE
  [update] Yes @ Atlanta Braves vs Philadelphia Phillies...: UNKNOWN -> RESOLVED_LOST
  ...
  [claimed] Yes @ Fajing Sun vs Li Tu...: UNKNOWN -> CLAIMED      ← Wuning, manuell geclaimed
  [claimed] Yes @ Busan: Leandro Riedi vs Yunchaokete Bu...: UNKNOWN -> CLAIMED   ← Busan

[migration] 23 Positionen aktualisiert
[migration] Finale State-Verteilung:
  ACTIVE: ~11
  RESOLVED_LOST: ~13
  CLAIMED: ~2 (Wuning, Busan)
```

---

## PHASE 4C: STOP-CHECKs (~10 Min)

### Check 1: bot_state.json validieren
```bash
python3 -c "
import json
with open('/root/KongTradeBot/bot_state.json') as f: s = json.load(f)
pos = s.get('open_positions', [])
from collections import Counter
states = Counter(p.get('position_state', 'NONE') for p in pos)
print('State-Verteilung:', dict(states))
claimed = [p for p in pos if p.get('position_state') == 'CLAIMED']
print('CLAIMED:', [p.get('market_question','?')[:40] for p in claimed])
"
```

### Check 2: Wuning + Busan als CLAIMED erkannt
```bash
python3 -c "
import json
with open('/root/KongTradeBot/bot_state.json') as f: s = json.load(f)
for p in s.get('open_positions', []):
    if 'Fajing' in p.get('market_question','') or 'Busan' in p.get('market_question',''):
        print(p.get('market_question','')[:50], '->', p.get('position_state'))
"
```
**Erwartung:** Beide zeigen `CLAIMED`

### Check 3: ACTIVE-Count stimmt
```bash
python3 -c "
import json
with open('/root/KongTradeBot/bot_state.json') as f: s = json.load(f)
active = [p for p in s['open_positions'] if p.get('position_state') == 'ACTIVE']
print(f'ACTIVE: {len(active)}')
for p in active: print(f'  {p[\"outcome\"]} @ {p[\"market_question\"][:45]}')
"
```
**Erwartung:** ~11 ACTIVE Positionen

### STOP wenn:
- Wuning oder Busan sind RESOLVED_WON statt CLAIMED (sie erscheinen nicht mehr in API)
- ACTIVE-Count > 15 (zu viele — Klassifizierung falsch)
- ACTIVE-Count = 0 (alle falsch als RESOLVED klassifiziert)
- State-File nicht geschrieben (Permissions?)

---

## PHASE 4D: Bot-Restart mit migriertem State

```bash
sudo systemctl restart kongtrade-bot
sleep 5
journalctl -u kongtrade-bot -n 20 | grep -iE 'position|state|restore|aktiv'
```

**Erwartung:** Log zeigt Positionen mit korrekt restaurierten States:
```
[engine] Position-Restore: ACTIVE | Yes @ US x Iran...
[engine] Position-Restore: RESOLVED_LOST | Yes @ Atlanta Braves...
[engine] Position-Restore: CLAIMED | Yes @ Fajing Sun... (skip Exit-Guard)
```

---

## EDGE CASES

### Manuell geclaime Positionen (Wuning, Busan)
Diese Positionen verschwinden aus der Polymarket API nach `redeemPositions()`.
Das Migrations-Skript erkennt sie als "nicht mehr in on-chain API" und setzt `CLAIMED`.
Das ist korrekt — sie tauchen nicht mehr auf und müssen nicht weiter verfolgt werden.

### RESOLVED_WON ohne Claim (falls vorhanden)
Preis ≈ 99c, redeemable=True → `RESOLVED_WON`. Claim-Notification wird von T-M04b getriggert.
Kein manueller Eingriff durch Migrations-Skript nötig.

### Position im bot_state.json aber nicht in Polymarket API
Kann bei Ghost-Trades aus Archive-Drift vorkommen (KB P078).
Migrations-Skript setzt `CLAIMED` — konservative Wahl: lieber als "done" markieren
als fälschlicherweise als ACTIVE behandeln.

---

## REFERENZEN

| Quelle | Inhalt |
|--------|--------|
| T-M08 Hauptprompt | Phase 1-3 (Voraussetzung) |
| `analyses/position_state_bug_diagnosis_2026-04-19.md` | State-Definitionen, Lifecycle |
| `dashboard.py:666` | api_portfolio() — State-Source für Migration |
| KB P075 | Position-State-Bug |
| KB P078 | Archive-Drift (Ghost-Trade Kontext) |
