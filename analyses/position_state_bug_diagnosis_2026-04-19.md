# Position-State-Bug Diagnose (19.04.2026 abends)

_T-M08 Phase 0 — Nur Diagnose, keine Code-Änderung_
_Zweck: Root-Cause verstehen, Implementation-Plan für nächste Session._

---

## Ist-Zustand

**Dashboard Portfolio zeigt: 25 Positionen**

Von den 25 on-chain Positionen (live verifiziert via `/api/portfolio`):

| Kategorie | Anzahl | Beschreibung |
|-----------|--------|-------------|
| **Wirklich aktiv** | **11** | Markt offen, `value > 0`, `redeemable=False` |
| **WON — wartet auf Claim** | **1** | Fajing Sun vs Li Tu, $50.13 claimbar, `redeemable=True` |
| **LOST — nie weggehend** | **13** | `redeemable=True, value=0` — resolved verloren, kein Claim-Nutzen |
| **DEAD (nicht redeemable, $0)** | **0** | — |

**Das heißt: 14 von 25 Positionen sind faktisch beendet.**
Nur 11 sind wirklich aktive Trades. Dashboard zeigt alle 25 als "Portfolio".

**VERLOREN-Positionen (vollständige Liste):**

| Markt | PnL | closes_in_class |
|-------|-----|----------------|
| Atlanta Braves vs. Philadelphia Phillies | -$33.40 | closes-gray ⚠ |
| Tallahassee: Daniil Glinka vs Jack Kennedy | -$15.49 | closes-gray ⚠ |
| Tampa Bay Rays vs. Pittsburgh Pirates | -$19.98 | closes-gray ⚠ |
| Warriors vs. Suns: O/U 219.5 | -$22.07 | closes-ended ✅ |
| Jaguares de Córdoba FC vs. AD Pasto: O/U 4.5 | -$5.58 | closes-ended ✅ |
| Adelaide United FC vs. Macarthur FC: O/U 2.5 | -$8.61 | closes-ended ✅ |
| Jaguares de Córdoba FC vs. AD Pasto: O/U 3.5 | -$13.47 | closes-ended ✅ |
| Spread: Hornets (-3.5) | -$5.29 | closes-ended ✅ |
| Spread: New York Yankees (-2.5) | -$6.57 | closes-ended ✅ |
| Will CA Unión win on 2026-04-17? | -$7.51 | closes-ended ✅ |
| Will AVS Futebol win on 2026-04-17? | -$2.54 | closes-ended ✅ |
| Will AD Pasto win on 2026-04-17? | -$6.88 | closes-ended ✅ |
| Rio Ave FC vs. AVS Futebol: O/U 4.5 | -$1.31 | closes-ended ✅ |

**Gesamtschaden in LOST-Positionen: -$148.70**

⚠ 3 davon haben noch `closes-gray` (endDate-Lookup fehlgeschlagen/zukünftig) — diese zeigen
weder ENDED-Label noch VERLOREN-Label korrekt.

**Zweiter Befund — trades_archive.json:**
- 106 Trades gespeichert, `aufgeloest=False` bei ALLEN 106 (100%)
- `ergebnis=''` bei allen
- `gewinn_verlust_usdc=0.0` bei allen
- → **resolver.py --save wurde NOCH NIE automatisch ausgeführt**

---

## Root-Cause

### Hypothesen-Check

**H1 — Polymarket-API liefert ended Markets noch als "aktiv":** ✅ BESTÄTIGT

Polymarket's on-chain Positions-API gibt alle Wallet-Positionen zurück — unabhängig davon
ob der Markt noch aktiv oder bereits resolved ist. Eine Position verschwindet erst wenn
sie explizit geclaimed/redeemed wurde (on-chain Transaktion nötig).

`redeemable=True` bedeutet: "Markt ist resolved, du kannst redeem() aufrufen."
Bei verlorenen Positionen: `redeemable=True` + `value=0` = resolved verloren.
Diese Positionen bleiben **ewig** im Portfolio bis explizit redempt — auch wenn der Gewinn $0 ist.

**H2 — Bot-State-Machine hat keinen Cleanup-Job:** ✅ BESTÄTIGT

`resolver.py` ist ein manuelles CLI-Tool. Das Flag `--save` (das `aufgeloest=True` schreibt)
muss explizit übergeben werden. Der Bot hat keinen automatischen Task der regelmäßig
`resolver.py --save` aufruft.

`ResolverLoop` in main.py ruft den Resolver alle 15 Minuten auf — aber nur für Display,
nicht mit `--save`. Deshalb: 106 Trades, alle `aufgeloest=False`.

**H3 — Claim vs. Sell Confusion:** ✅ BESTÄTIGT (Teilaspekt)

13 LOST-Positionen haben `redeemable=True` mit `value=0`. Der CLAIM-Button-Fix (Session 19.04
morgens) zeigt "VERLOREN" statt "$0.00 CLAIM" — das ist visuell korrekt. Aber:
- Die Positionen bleiben in der Portfolio-Gesamtzahl (25)
- Der OPEN-Counter zählt sie mit
- 3 der 13 fehlt sogar das VERLOREN-Label (closes-gray statt closes-ended)

### Warum akkumuliert der Bug?

```
Bot kauft Position
       ↓
open_positions in bot_state.json += 1
       ↓
Position erscheint in Polymarket on-chain API
       ↓
Dashboard /api/portfolio zeigt ALLE on-chain Positionen (25)
       ↓
Markt resolved → position.redeemable=True, value→0
       ↓
Dashboard: CLAIM-Button fix zeigt "VERLOREN" ✅
       ↓
Position bleibt in Portfolio-Zählung (25) ← HIER FEHLT DIE BEREINIGUNG
       ↓
Bot kauft neue Position → 26, 27, 28... ← endlos wachsend
```

**Warum `open_positions` in `bot_state.json` = 0:**

`state_manager.py` Zeile 86: "anderer Tag → frische Positionen, TX-Hashes behalten."
Bei Tagesübergang werden `open_positions` gelöscht. Dadurch zeigt `/api/positions`
immer 0 open — aber `/api/portfolio` zeigt weiterhin die on-chain Positionen.

**Zwei separate Tracking-Systeme ohne Synchronisation:**
1. `bot_state.json → open_positions` → Dashboard `/api/positions` → zeigt 0
2. Polymarket on-chain API → `_polymarket_positions` → Dashboard `/api/portfolio` → zeigt 25

Diese beiden Quellen kennen sich gegenseitig nicht.

---

## Soll-Zustand

### Position-State-Lifecycle

```
[Kauf ausgeführt]
       │
       ▼
    ACTIVE ─────────────────────────────────────── Bedingung: acceptingOrders=True
       │                                           value > 0, redeemable=False
       │
       ├─→ [acceptingOrders=False, nicht resolved]
       │          ↓
       │     TRADING_ENDED ──────────────────────── Dead Zone: weder Sell noch Claim
       │          │
       ▼          ▼
       └─────────→ [Markt resolved]
                       │
                       ├─→ redeemable=True + value > 0.01
                       │         ↓
                       │    RESOLVED_WON ────────── Claim-Button anzeigen
                       │         │
                       │         └─→ [Claim ausgeführt] → CLAIMED (terminal)
                       │
                       └─→ redeemable=True + value ≤ 0.01
                                 ↓
                            RESOLVED_LOST ──────── VERLOREN-Label, kein Claim-Button
                                 │                 Terminal state — aus Zählung raus
                                 └─→ [Redeem on-chain (bringt $0)] → kann gecleaned werden
```

### Dashboard-Kategorien (Soll)

| Tab/Sektion | States | Zähler |
|-------------|--------|--------|
| **AKTIV** | ACTIVE + TRADING_ENDED | Nur diese zählen als "offen" |
| **CLAIM** | RESOLVED_WON | Separate Zählung, Alert wenn > 0 |
| **VERLOREN** | RESOLVED_LOST | Separat, nicht in AKTIV-Zähler |
| **ABGESCHLOSSEN** | CLAIMED | Historisch |

**AKTIV-Zähler Soll (heute):** 11 (nicht 25)

---

## Implementation-Plan

### E1: Code-Änderungen

**E1a — `/api/portfolio` — Position-State Klassifizierung** _(~1h)_

```python
# In api_portfolio(), nach result-Liste aufbau:
for p in result:
    rd = p.get("redeemable", False)
    val = float(p.get("current_value", 0) or 0)
    if not rd and val > 0.01:
        p["position_state"] = "ACTIVE"
    elif rd and val > 0.01:
        p["position_state"] = "RESOLVED_WON"
    elif rd and val <= 0.01:
        p["position_state"] = "RESOLVED_LOST"
    else:
        p["position_state"] = "TRADING_ENDED"  # fallback

# Zähler korrigieren:
active_count = sum(1 for p in result if p["position_state"] == "ACTIVE")
won_count    = sum(1 for p in result if p["position_state"] == "RESOLVED_WON")
lost_count   = sum(1 for p in result if p["position_state"] == "RESOLVED_LOST")
```

**E1b — Dashboard-Frontend** _(~1h)_
- AKTIV-Badge: nur `position_state == "ACTIVE"` zählen
- VERLOREN-Sektion: `RESOLVED_LOST` getrennt anzeigen (heute schon VERLOREN-Label via JS)
- CLAIM-Alert: `RESOLVED_WON` mit Anzahl und Summe

**E1c — Resolver Auto-Save** _(~30min)_
`ResolverLoop` in main.py: nach Resolver-Aufruf `--save` Flag aktivieren, damit
`aufgeloest=True` und `ergebnis` automatisch in trades_archive.json geschrieben werden.
Derzeit ist das manuelle Voraussetzung für Resolved-Tab in `/api/positions`.

**E1d — `closes-gray` Fix für resolved Positionen** _(~30min)_
3 LOST-Positionen haben `closes-gray` statt `closes-ended` weil endDate-Lookup fehlschlug.
Fix: Wenn `redeemable=True` und `value=0` → unabhängig von endDate immer `closes-ended`.

### E2: Daten-Migration _(~30min)_

- Manuell: `python resolver.py --save` auf Server ausführen
- Ergebnis: 106 Trades gegen Polymarket-API prüfen, resolved ones auf `aufgeloest=True` setzen
- Danach: RESOLVED-Tab in Dashboard zeigt echte Daten

_Achtung: Dies ändert nur das Archiv, nicht die on-chain Portfolio-Anzeige._

### E3: Tests _(~30min)_

- Dashboard nach Fix: AKTIV-Zähler sollte 11 zeigen
- VERLOREN-Sektion: 13 Positionen mit korrekten Labels
- CLAIM-Button: 1 Position (Fajing Sun vs Li Tu, $50.13)
- Resolver Auto-Save: nach 15min Interval → mindestens 1 resolved Position in Archive

### E4: Abhängigkeit zu T-M04 (Sell-Feature)

Sell-Feature braucht zusätzliche States in der State-Machine:

```
ACTIVE → PENDING_SELL → SOLD (wenn Sell-Order gefillt)
ACTIVE → PARTIAL_SELL → PARTIALLY_SOLD (Teilverkauf)
```

**Empfehlung:** T-M08 State-Machine (`position_state` Feld) in **E1a jetzt so designen**
dass T-M04 nur neue States ERGÄNZT, nicht das Modell umbaut:
- Das Feld `position_state` als String einführen (erweiterbar)
- Enum-Werte dokumentieren, nicht hart codieren
- T-M04 kann `PENDING_SELL` / `SOLD` dann ohne Breaking Change hinzufügen

**Reihenfolge:** T-M08 E1a zuerst (State-Feld einführen), dann T-M04 darauf aufbauen.

---

## Risiken und Offene Fragen

### Risiko 1: Polymarket-Positions-API gibt keine State-Info zurück

Das Feld `redeemable` ist der einzige State-Indikator aus der Polymarket-API.
Es gibt KEIN Feld `market_resolved` oder `market_active` in den Positions-Daten.
→ State-Klassifizierung muss via `redeemable + value` abgeleitet werden (wie E1a).

### Risiko 2: `closes-gray` bei 3 LOST-Positionen

Diese 3 Positionen (Atlanta Braves, Tallahassee, Tampa Bay Rays) haben endDate vermutlich
als laufenden Datum gespeichert oder endDate-Lookup aus Gamma-API liefert nichts.
→ Fix via `redeemable=True + value=0 → force closes-ended` (unabhängig von endDate).

### Risiko 3: Resolver `--save` könnte falsche Märkte matchen

`resolver.py` matcht via `question[:35].lower() in t.get("markt").lower()` — String-Matching.
Risiko: Zwei Märkte mit ähnlichem Titel → falscher Match.
→ Besser: Match via `market_id` / `conditionId` statt Titel. Für E1c prüfen.

### Offene Fragen

1. **Warum hat ResolverLoop keinen `--save` Mode?**
   War das bewusste Design (manuelle Kontrolle) oder vergessen?

2. **Was passiert mit RESOLVED_LOST Positionen on-chain nach E1?**
   Sie bleiben in der Polymarket-API bis `redeemPositions()` gecallt wird (bringt $0).
   Soll der Bot automatisch "leere" Redeems ausführen um die Portfolio-Liste sauber zu halten?
   → Aufwand vs. Nutzen abwägen (jede on-chain Tx kostet Gas).

3. **Position-State Persistenz — wo speichern?**
   Option A: `bot_state.json` um `position_state` per Position erweitern
   Option B: Separates `position_states.json`
   Option C: In `trades_archive.json` als Feld
   → Empfehlung: Option A (bot_state.json), synchronized mit Polymarket-API-Daten.

---

## Aufwandsschätzung Gesamt

| Task | Aufwand | Prio |
|------|---------|------|
| E1a: position_state in /api/portfolio | ~1h | 🔴 Hoch |
| E1b: Frontend AKTIV/VERLOREN/CLAIM Trennung | ~1h | 🔴 Hoch |
| E1c: Resolver Auto-Save | ~30min | 🟡 Mittel |
| E1d: closes-gray Fix für LOST | ~30min | 🟡 Mittel |
| E2: Daten-Migration (manuell resolver --save) | ~15min | 🟢 Sofort möglich |
| E3: Tests | ~30min | 🔴 Nach E1 |
| E4: T-M04 Design-Abstimmung | Keine Zeit, nur Design-Entscheidung | 🟡 |

**Gesamtaufwand: ~3.5-4h** (eine Session)

**Fix-Priorität: MORGEN** — nicht heute (Server-CC arbeitet an T-M04, Race-Condition-Risiko).
E2 (manuell resolver --save) kann sofort in eigener SSH-Session laufen, risikofrei.

---

## Summary

| Frage | Antwort |
|-------|---------|
| ENDED-aber-OPEN Positionen | 13 RESOLVED_LOST + 1 RESOLVED_WON = 14 beendet von 25 |
| Root-Cause (H1/H2/H3) | Alle drei bestätigt — H1 ist Kern, H2+H3 sind Folgeprobleme |
| Gesamtverlust in LOST-Positionen | -$148.70 |
| Soll-Lifecycle dokumentiert | ✅ ACTIVE→TRADING_ENDED→RESOLVED_WON/LOST→CLAIMED |
| Implementation-Plan | ✅ E1a-E1d + E2 Migration + E3 Tests |
| T-M04 Abhängigkeit | `position_state` String-Feld jetzt, T-M04 fügt PENDING_SELL/SOLD hinzu |
| Empfohlener Fix-Zeitpunkt | Morgen (eigene Session, Server-CC nicht parallel) |
| Sofort-Maßnahme möglich | ✅ `python resolver.py --save` manuell ausführen |
