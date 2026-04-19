# T-M06 Phase 0 Diagnose: Reconciliation + Steuer-Export (19.04.2026)

_Nur Diagnose — kein Code-Write._
_Zweck: Root-Cause Archive-Drift verstehen, Reconciliation-Design, Steuer-Anforderungen klären._

---

## A) Archive-Ist-Zustand

### Struktur

**Datei:** `/root/KongTradeBot/trades_archive.json` — 110 Einträge, alle `modus=LIVE`

**Felder pro Trade:**
```
id | datum | uhrzeit | markt | market_id | token_id | outcome | seite
preis_usdc | einsatz_usdc | shares | source_wallet | tx_hash | kategorie
modus | ergebnis | gewinn_verlust_usdc | aufgeloest
```

**Feld-Kompletheit:**

| Feld | Befüllt | Qualität |
|------|---------|---------|
| datum / uhrzeit | 110/110 | ✅ Gut |
| markt | 110/110 | ✅ Gut |
| market_id / token_id | 110/110 | ✅ Gut |
| einsatz_usdc | 110/110 | ✅ Gut |
| kategorie | 110/110 | ✅ Gut |
| tx_hash | 0 confirmed, 20 pending, 90 leer | ❌ Kritisch |
| ergebnis | 18/110 (VERLUST:16, GEWINN:2) | ❌ 92 leer |
| gewinn_verlust_usdc | 18/110 (PnL ≠ 0) | ❌ 92 = 0.0 |
| aufgeloest | 18/110 True | ❌ 92 False |
| seite | BUY: 110/110 | ❌ Kein SELL/CLAIM |
| status | 0/110 (Feld fehlt) | ❌ Fehlt ganz |
| close_date | — | ❌ Fehlt ganz |

**Kritisch fehlende Felder für Steuer:**
- `close_date` — wann wurde die Position geschlossen?
- `actual_fill_price` — `preis_usdc` ist requested price, nicht tatsächlicher Fill-Preis
- SELL/CLAIM-Events — werden komplett nicht geloggt

### tx_hash-Status

```
LEER    (90 Trades = 81.8%): $1,350.38 USDC — Order nie on-chain ausgeführt
PENDING (20 Trades = 18.2%): $  312.59 USDC — Order ausgeführt, Bestätigung fehlte
CONFIRMED (0 Trades =  0%):  $      0 USDC  — Kein einziger Trade bestätigt im Archive
```

**Archive-Summe:** $1,662.98 USDC (davon real on-chain: nur ~$522)

### Aufgelöste Positionen (18)

```
VERLUST: 16 Trades, PnL = -$127.82
GEWINN:  2 Trades (Busan: Leandro Riedi vs Yunchaokete Bu — $18.54 + $5.75)
Total realisiertes PnL: -$127.82 + $24.29 = -$103.53
```

Achtung: Diese 18 wurden via `resolver.py --save` manuell eingetragen.
Der AutoResolver-Loop schreibt `--save` NICHT automatisch.

---

## B) On-Chain-Wahrheit

### Wallet

`POLYMARKET_ADDRESS=0x700BC51b721F168FF975ff28942BC0E5fAF945eb` (ProxyWallet)

### On-Chain-Aktivität (data-api.polymarket.com/trades)

```
Total on-chain Trades: 40
Seiten: BUY: 40, SELL: 0 (API gibt nur BUY-Trades zurück)
USDC tatsächlich gehandelt: $522.12
Datum-Range: 2026-04-17 → 2026-04-19
```

### Drift-Quantifizierung

| Metrik | Archive | On-Chain | Differenz |
|--------|---------|----------|-----------|
| Trade-Anzahl | 110 | 40 | +70 ghost trades |
| USDC-Volumen | $1,662.98 | $522.12 | -$1,140.86 |
| Unique Markets | 39 | ~22 | — |
| Abdeckungsrate | 100% (behauptet) | — | **31% real / 69% phantom** |

**Root-Cause der 70 Ghost Trades:**

Das Archive wird VOR der Auftrags-Bestätigung beschrieben. Wenn der Bot ein Signal
loggt, aber die Order dann aus irgendeinem Grund scheitert (Risk-Manager blockiert,
API-Error, Budget-Cap, Timeout), bleibt der Archive-Eintrag bestehen — aber ohne tx_hash.

```
Signal erkannt
    ↓
Archive-Eintrag geschrieben (einsatz_usdc, markt, etc.)
    ↓
Risk-Manager / Execution-Engine entscheidet
    ↓ (bei Ablehnung)        ↓ (bei Ausführung)
tx_hash bleibt leer      tx_hash = "pending_0x..."
                               ↓
                         Bot crashed / Timeout
                               ↓
                         tx_hash bleibt "pending_"
                         (Bestätigung nie geschrieben)
```

Die 90 EMPTY-Einträge ($1,350 USDC) sind **geblockte oder abgelehnte Signale**,
die trotzdem im Archive landeten. Das ist ein Design-Bug im Signal-Logging.

### Wuning Manual Claim — Ist er im Archive?

**Antwort: NEIN.**

Wuning-Einträge im Archive: 3x PENDING, alle `aufgeloest=False`, `ergebnis=''`, `gewinn_verlust=0.0`

Der manuelle Claim via Polymarket-UI erzeugte:
- On-chain eine Redemption-Transaktion (+$50.13 USDC realisiert)
- Im Archive: **nichts** — kein automatischer Eintrag
- Im data-api.polymarket.com/trades: **nicht sichtbar** (API zeigt nur BUY-Trades, keine Claims)

→ **Manuelle UI-Interventionen driften systematisch.** Das gilt für:
  - Manuell geclaimed Wins (Wuning: +$50.13 fehlt)
  - Manuelle Verkäufe über UI (theoretisch möglich)
  - Alle zukünftigen Claims via T-M04b (RelayClient) bis Reconciliation läuft

---

## C) Manuell vs. Bot-Trades unterscheiden

### Konzept: Timestamp-Cross-Reference

```
On-Chain-Event (timestamp: 1776458262)
    ↓ konvertiert zu Datetime
2026-04-17 08:17:42
    ↓ cross-reference
Bot-Log: suche Trade-Eintrag ±30 Sekunden
    ↓
Gefunden: "Order executed: market_id=..." → source="bot"
Nicht gefunden: → source="manual" | "unknown"
```

### Wuning-Claim als Proof-of-Concept

- Wuning BUY (08:02:30): Bot-Log zeigt `2026-04-19 08:02:30 | INFO | Order executed` → `source="bot"`
- Wuning Claim (heute Mittag via UI): Bot-Log zeigt KEINE Claim-Aktivität für diesen Zeitpunkt → `source="manual"`
- AutoClaim-Log: 198 Einträge heute, alle "Keine redeemable Positionen gefunden" — bestätigt 0 Bot-Claims

### Praktische Umsetzung

```python
# In reconcile_onchain.py:
def classify_source(onchain_ts: int, bot_log_events: list) -> str:
    dt = datetime.fromtimestamp(onchain_ts)
    for log_event in bot_log_events:
        if abs((log_event['timestamp'] - dt).total_seconds()) <= 30:
            return "bot"
    return "manual"
```

**Einschränkung:** Log-Rotation. Ältere Logs müssen vor der Reconciliation verfügbar sein.

---

## D) Steuer-Anforderungen Deutschland

### D1) Rechtliche Einordnung

Polymarket-Prediction-Markets sind juristisch nicht eindeutig klassifiziert.
Konservative Annahme für deutsche Steuerpflicht:

**§ 22 Nr. 3 EStG — Sonstige Einkünfte (Spekulationsgeschäfte)**
- Gilt für Differenzgeschäfte und Glücksspielähnliches
- Voller Einkommensteuersteuersatz (kein Abgeltungssteuervorteil)
- Verlustverrechnung: nur mit gleichartigen Einkünften (§ 22 Nr. 3 EStG)
- **Freigrenze: 256 EUR netto pro Jahr** (nicht 600 EUR — das ist § 23)
- Haltefristen spielen keine Rolle (anders als bei § 23 EStG)

Alternative: § 15 EStG Gewerbebetrieb falls systematisch/wiederholend mit Gewinnerzielungsabsicht.
→ Steuerberater konsultieren vor dem ersten Steuerjahr mit positiver Bilanz.

### D2) Pflichtfelder pro Trade für Steuer

```
KAUF:
- Kaufdatum (Timestamp)
- Markt-Bezeichnung
- Einsatz in USDC
- Einsatz in EUR (Wechselkurs Kaufdatum)
- Kaufkurs USDC/EUR

VERKAUF / CLAIM:
- Schließdatum (Timestamp)
- Erlös in USDC
- Erlös in EUR (Wechselkurs Schließdatum)

BERECHNUNG:
- Gewinn/Verlust USDC = Erlös - Einsatz
- Gewinn/Verlust EUR = Erlös_EUR - Einsatz_EUR
- Haltedauer in Tagen
```

### D3) CSV-Format-Vorschlag

```csv
Datum_Kauf,Uhrzeit_Kauf,Datum_Schliessung,Markt,Outcome,Einsatz_USDC,Erloes_USDC,
PnL_USDC,Kurs_Kauf,Kurs_Schliessung,Einsatz_EUR,Erloes_EUR,PnL_EUR,
Haltedauer_Tage,Kategorie,Source,TX_Hash
```

Beispielzeile:
```
2026-04-17,08:15,2026-04-18,Busan: Riedi vs Bu,YES,6.12,18.54,+12.42,
1.08,1.085,5.67,17.08,+11.41,1,Tennis,bot,0x4d9...
```

### D4) EUR-Wechselkurse

**Quelle:** Europäische Zentralbank (EZB) Referenzkurs (offiziell für deutsche Steuer).
- API: `data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A`
- Tagesgranularität ausreichend (USDC ≈ 1:1 USD, keine Kursverzerrung)
- Wichtig: Datum des Kaufs UND Datum des Verkaufs — nicht Durchschnitt

**Aktuelle Approximation:** 1 USDC ≈ 0.92–0.95 EUR (EURUSD ~1.05–1.08)

### D5) Jahresabschluss 31.12.

- Offene Positionen zum 31.12.: **nicht realisiert** → kein Steuer-Ereignis
- Alle Positions die im Steuerjahr geschlossen wurden → realisiert, steuerpflichtig
- Claims = Realisierungszeitpunkt (nicht der Kauf!)

---

## E) Reconciliation-System Design

### E1) Komponenten

#### a) `scripts/reconcile_onchain.py` (neu, ~4h)

```python
"""
Zieht alle on-chain Events via data-api.polymarket.com,
cross-referenziert mit trades_archive.json,
erstellt Diff-Report, optional --apply.
"""

def fetch_onchain_events(wallet: str, limit=500) -> list:
    # GET /trades?user=...&limit=...
    # GET /positions?user=... (für Claim-Events via redeemable-Status)
    pass

def match_to_archive(onchain: list, archive: list) -> dict:
    # Match by: market_id + token_id + timestamp (±60s) + size (~= einsatz)
    # Result: {matched: [], unmatched_onchain: [], ghost_archive: []}
    pass

def classify_source(onchain_ts, bot_log) -> str:
    # "bot" | "manual" | "unknown"
    pass

def generate_diff_report(diff: dict) -> str:
    pass

def apply_diff(diff: dict, archive_path: str):
    # --apply flag: write missing events to archive
    # mark ghost entries with status="GHOST" (not delete — audit trail)
    pass
```

**Wichtig:** data-api `/trades` liefert nur BUY-Trades.
Für Claims: `/positions?user=...` → `redeemable=True` → `current_value` verschwunden = geclaimed.
Für Sells: aktuell nicht via API erkennbar (kein SELL in data-api, Side-Feld immer BUY).

#### b) `scripts/tax_export.py` (neu, ~3h)

```python
"""
Input: trades_archive.json + Jahr
Output: Steuer-CSV (§22 Nr.3 EStG Format)
"""

def fetch_eur_rate(date: str) -> float:
    # EZB API für EURUSD Tagesrate
    pass

def export_tax_year(archive_path: str, year: int, output_path: str):
    # Filter: close_date in year (aufgeloest=True, ergebnis != '')
    # Pro Trade: Einsatz_EUR + Erloes_EUR via EZB-Rate
    # Sum: Total_Gewinn + Total_Verlust + Netto
    pass
```

#### c) systemd-Timer (neu, ~0.5h)

```ini
# /etc/systemd/system/kong-reconcile.timer
[Timer]
OnCalendar=hourly
RandomizedDelaySec=5min

# Telegram-Alert wenn Drift > 5%:
# reconcile_onchain.py --alert-threshold 0.05
```

#### d) Dashboard-Panel (neu, ~2h)

```
Panel: "Daten-Integrität"
├── Archive Trades: 110
├── On-Chain bestätigt: 40
├── Drift: 69% (KRITISCH)
├── Ghost-Trades: 70
└── Letzter Reconciliation: 2026-04-19 14:00
```

```
Panel: "Steuer 2026 (Vorschau)"
├── Realisierte Gewinne YTD: $24.29
├── Realisierte Verluste YTD: $127.82
├── Netto YTD: -$103.53
└── [Steuer-CSV exportieren]
```

### E2) Aufwandsschätzung

| Komponente | Aufwand | Priorität |
|-----------|---------|----------|
| reconcile_onchain.py | ~4h | 🔴 Hoch |
| tax_export.py | ~3h | 🟡 Mittel |
| systemd-Timer | ~0.5h | 🟡 Mittel |
| Dashboard-Panel | ~2h | 🟢 Niedrig |
| Tests + Verifikation | ~1h | 🔴 Nach Code |
| **Gesamt** | **~10.5h** | 2-3 Sessions |

### E3) Abhängigkeiten

```
T-M04b (Claim-Fix via RelayClient)
    ↓ ERST NACH diesem Schritt
T-M06 (Reconciliation) sinnvoll
    ↓ GRUND:
Solange Claims nicht automatisch laufen, zeigt Reconciliation
permanent "WON-Position geclaimed aber nicht im Archive" als Drift.
Das wäre verwirrend und Alert-Spam ohne T-M04b.
```

**Exception:** `reconcile_onchain.py --dry` (nur Report, kein Apply) kann unabhängig gebaut werden.

---

## F) Beantwortet: Onur's Fragen

### "Wenn ich auf Polymarket manuell verkaufe — geht das in unsere Steuertabelle?"

**Antwort: NEIN — aktuell nicht.**

Manuelle Sells über Polymarket-UI:
1. Erzeugen eine on-chain Transaktion
2. Erscheinen NICHT in Archive (Bot schreibt nur eigene Orders)
3. Erscheinen NICHT in data-api `/trades` (API zeigt nur BUY, kein SELL)
4. Wären nur via Polygon-Blockchain direkt nachverfolgbar (PolygonScan, moralis.io)

→ Ohne Reconciliation-System fallen manuelle Trades komplett durchs Raster.

### "Wuning heute manuell geclaimed — landet das im Archive?"

**Antwort: NEIN — landet nicht automatisch.**

- AutoClaim-Loop lief heute 198 Mal: immer "Keine redeemable Positionen"
  (Bug: client.redeem() existiert nicht + Redeemable-Detection funktioniert nicht)
- Wuning 3x im Archive: alle `aufgeloest=False`, `ergebnis=''`, `gewinn_verlust=0.0`
- $50.13 realisierter Gewinn fehlt komplett im Archive
- Für Steuer 2026: dieser Trade muss manuell nachgetragen werden

### "Steuer-Export aktuell möglich?"

**Antwort: NEIN — Daten zu lückenhaft.**

Gründe:
1. 92 von 110 Trades ohne ergebnis/PnL (aufgeloest=False)
2. Keine close_date für irgendeine Position
3. Wuning +$50.13 Claim fehlt komplett
4. 70 Ghost-Trades müssen bereinigt werden (sonst falsche Einsatz-Summe)
5. Keine EUR-Kurse vorhanden

**Manuell berechenbares Minimum (heute):**
- Realisierte Verluste: -$127.82 (16 VERLUST-Positionen via resolver.py)
- Realisierte Gewinne: +$24.29 (2 GEWINN via resolver.py) + $50.13 (Wuning, manuell)
- Netto: **-$53.40** realisiert (sehr grob)
- Ghost-Trade-Bereinigung fehlt

---

## G) Empfehlung

### MVP-Scope (1 Session, ~5-6h)

**Schritt 1 — Sofort (heute, 15min):**
```bash
python resolver.py --save  # 18 → ~40+ Positionen resolved, ergebnis befüllt
```

**Schritt 2 — Nächste Session (nach T-M04b):**
- `reconcile_onchain.py --dry` bauen (nur Report, kein Apply)
- Ghost-Trade-Markierung (status="GHOST" für EMPTY-tx_hash-Einträge ohne on-chain-Match)

**Schritt 3 — Übernächste Session:**
- `tax_export.py` mit EZB-Kursen
- Wuning-Claim manuell als GEWINN nachtragen

### Priorisierung vs. anderen Tasks

```
T-M04b (Claim-Fix)   → ZUERST (sofort wertschöpfend, ~2h)
T-M08 Ph1 (Dashboard) → DANN (macht Drift sichtbar, ~3.5h)
T-M06 (Reconciliation) → DANACH (~10.5h, 2-3 Sessions)
```

### Was morgen machbar?

Wenn T-M04b fertig:
- `reconcile_onchain.py --dry` Report: ~1.5h
- Ghost-Trade-Markierung in Archive: ~0.5h
- Gesamt: ~2h als "Reconciliation Phase 1"

Steuer-Export 2026 vollständig: erst wenn mindestens 80% der Positionen
via auto-resolver aufgelöst wurden (nach ResolverLoop-Fix in T-M08).

---

## Summary

| Frage | Antwort |
|-------|---------|
| Archive-Drift konkret | 70 Ghost-Trades, $1,140 Phantom-Volumen (69% nicht real) |
| Wuning-Claim im Archive | ❌ NEIN — manuell nachtragen erforderlich |
| Steuer-Export aktuell möglich | ❌ NEIN — Daten zu lückenhaft |
| Root-Cause Drift | Signal-Logging VOR Ausführungsbestätigung + kein Cleanup für geblockte Orders |
| Reconciliation MVP | ~5h (nach T-M04b), Report + Ghost-Markierung |
| Steuer-Export vollständig | ~3h (nach Reconciliation + ResolverLoop-Fix) |
| Abhängigkeit T-M04b | ✅ Bestätigt — Reconciliation sinnlos ohne funktionierenden Claim |
| Sofort-Maßnahme | `python resolver.py --save` manuell auf Server |
