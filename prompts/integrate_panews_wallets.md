# Server-CC Prompt: PANews Biteye Wallets integrieren
_Erstellt: 2026-04-21 | Für: KongTradeBot Integration_
_Quelle: analyses/panews_biteye_analysis_2026-04-20.md_

---

## Kontext

Wir haben 5 Wallets aus dem PANews Biteye Smart Money Artikel (2026-04-01) als APPROVE klassifiziert.
Diese Wallets sind **noch NICHT** in `TARGET_WALLETS` (.env) oder `WALLET_MULTIPLIERS` (copy_trading.py).
Sie sind in `WALLETS.md` als PANews APPROVE-Queue dokumentiert.

**Multiplier: 0.3x für alle 5** — konservativ wegen fehlender predicts.guru Deposit-ROI Verifikation.
Review-Datum: 2026-05-05 (predicts.guru Verifikation aller 5).

---

## Die 5 Wallets

### 1. cowcat — Middle East Longshot
```
Adresse:    0x38e59b36aae31b164200d0cad7c3fe5e0ee795e7
Alias:      cowcat
Kategorie:  Middle East / Iran Geopolitics Longshot
Multiplier: 0.3x
PnL:        $200,000 all-time
ROI:        +117% (PANews bestätigt)
Win Rate:   39% auf Märkten mit 8% implizierter WS (= 4.9x Edge)
Strategie:  Low-Probability Long-Shots (Iran, ME)
HF-Checks:  HF-0 ✅ ($200K > $10K)  |  HF-7 ✅ (+117%)  |  HF-10 ✅
Synergy:    T-M-NEW AnomalyDetector — cowcat wählt genau die Märkte mit Insider-Mustern
```

### 2. HondaCivic — Weather Specialist
```
Adresse:    0x15ceffed7bf820cd2d90f90ea24ae9909f5cd5fa
Alias:      HondaCivic
Kategorie:  Weather (Temperature) — Hong Kong #1 (100% WR)
Multiplier: 0.3x
PnL:        $48,000 all-time
Win Rate:   85.7% über 3,000+ Positionen
Avg Trade:  $1,478 — bei 0.3x = $443 pro Trade (muss getrimmt werden auf $30 Cap)
Trades/Tag: ~5-8 (temperatur-fokussiert, kein Bot-Muster)
HF-Checks:  HF-0 ✅ ($48K > $10K)  |  HF-7 ⚠ PENDING  |  HF-10 ✅ (<50/Tag)
Synergy:    T-WEATHER — HondaCivic Positionen validieren unsere eigenen Weather-Trades
Polymarket-Fee: Weather = 5% → MIN_EDGE für diesen Wallet auf 15% setzen
```

### 3. EFFICIENCYEXPERT — Esports / League of Legends
```
Adresse:    0x8c0b024c17831a0dde038547b7e791ae6a0d7aa5
Alias:      EFFICIENCYEXPERT
Kategorie:  Esports (#15 overall, #14 LoL)
Multiplier: 0.3x
PnL:        $580,000 all-time
Volume:     $30M
Märkte:     2,700+
HF-Checks:  HF-0 ✅ ($580K)  |  HF-7 ⚠ PENDING  |  HF-10 ✅ (kein Daily-Sports-Bot)
Warnung:    PANews meldet sinkende WR in letzten Monaten — enges Monitoring!
Trade-Länge: 1-2 Tage (kurze Esports-Events) — gut für bot-seitigen Exit
```

### 4. synnet — Tennis Underdogs
```
Adresse:    0x8e0b7ae246205b1ddf79172148a58a3204139e5c
Alias:      synnet
Kategorie:  Tennis (#17 overall, #1 ATP)
Multiplier: 0.3x
PnL:        $290,000 all-time
Win Rate:   31.7%
Avg Entry:  0.30¢ (Außenseiter-Strategie)
EV:         3.2x implizierte Odds × 31.7% = positiver EV
HF-Checks:  HF-0 ✅ ($290K)  |  HF-7 ⚠ PENDING  |  HF-10 ✅
Hinweis:    Longshot-Strategie = viele Verluste, ein Gewinn deckt viele. Drawdown-Phasen normal.
```

### 5. middleoftheocean — Soccer / Football
```
Adresse:    0x6c743aafd813475986dcd930f380a1f50901bd4e
Alias:      middleoftheocean
Kategorie:  Soccer (#99 Sports overall)
Multiplier: 0.3x
PnL:        $470,000 all-time
Win Rate:   83.1% Soccer über 1,700+ Märkte
Strategie:  Medium-Probability (kein Longshot-Gambling)
HF-Checks:  HF-0 ✅ ($470K)  |  HF-7 ⚠ PENDING  |  HF-10 ✅
Vorteil:    Konsistentere Signale als Longshot-Wallets — guter Sports-Slot
```

---

## Aufgabe für Server-CC

### Schritt 1 — strategies/copy_trading.py

Füge alle 5 Wallets in `WALLET_MULTIPLIERS` dict ein:

```python
WALLET_MULTIPLIERS = {
    # ... bestehende Einträge ...

    # PANews Biteye — integriert 2026-04-21, Review 2026-05-05
    "0x38e59b36aae31b164200d0cad7c3fe5e0ee795e7": 0.3,  # cowcat — ME Longshot +117% ROI
    "0x15ceffed7bf820cd2d90f90ea24ae9909f5cd5fa": 0.3,  # HondaCivic — Weather 85.7% WR
    "0x8c0b024c17831a0dde038547b7e791ae6a0d7aa5": 0.3,  # EFFICIENCYEXPERT — Esports $580K
    "0x8e0b7ae246205b1ddf79172148a58a3204139e5c": 0.3,  # synnet — Tennis $290K Underdogs
    "0x6c743aafd813475986dcd930f380a1f50901bd4e": 0.3,  # middleoftheocean — Soccer 83.1% WR
}
```

### Schritt 2 — .env

Füge alle 5 Adressen in `TARGET_WALLETS` ein (comma-separated, kein Leerzeichen):
```
TARGET_WALLETS=...,0x38e59b36aae31b164200d0cad7c3fe5e0ee795e7,0x15ceffed7bf820cd2d90f90ea24ae9909f5cd5fa,0x8c0b024c17831a0dde038547b7e791ae6a0d7aa5,0x8e0b7ae246205b1ddf79172148a58a3204139e5c,0x6c743aafd813475986dcd930f380a1f50901bd4e
```

Füge in `WALLET_WEIGHTS` JSON ein (falls vorhanden):
```json
{
  "0x38e59b36aae31b164200d0cad7c3fe5e0ee795e7": 0.3,
  "0x15ceffed7bf820cd2d90f90ea24ae9909f5cd5fa": 0.3,
  "0x8c0b024c17831a0dde038547b7e791ae6a0d7aa5": 0.3,
  "0x8e0b7ae246205b1ddf79172148a58a3204139e5c": 0.3,
  "0x6c743aafd813475986dcd930f380a1f50901bd4e": 0.3
}
```

### Schritt 3 — Verifikation nach Bot-Restart

Nach Restart prüfen ob diese Log-Zeilen erscheinen:
```
[WALLET] cowcat (0x38e5...e5e7) geladen — Multiplier: 0.3x
[WALLET] HondaCivic (0x15ce...d5fa) geladen — Multiplier: 0.3x
[WALLET] EFFICIENCYEXPERT (0x8c0b...7aa5) geladen — Multiplier: 0.3x
[WALLET] synnet (0x8e0b...e5c) geladen — Multiplier: 0.3x
[WALLET] middleoftheocean (0x6c74...d4e) geladen — Multiplier: 0.3x
```

### Schritt 4 — WALLETS.md Update

In `WALLETS.md` PANews APPROVE-Queue: Status von "PENDING" zu "AKTIV (0.3x)" ändern für alle 5.
Tier B Tabelle mit allen 5 erweitern (Datum: 2026-04-21).

---

## Kritische Hinweise

### Dual-Source-Invariante (KB P083)
BEIDE Dateien müssen in sync sein:
- `strategies/copy_trading.py` → WALLET_MULTIPLIERS
- `.env` → TARGET_WALLETS + WALLET_WEIGHTS
Bot-Restart danach zwingend.

### HF-7 PENDING (predicts.guru)
Alle 5 Wallets haben **HF-7 noch nicht bestätigt** (predicts.guru Deposit-ROI).
- cowcat: +117% ROI via PANews — wahrscheinlich positiv, aber nicht via predicts.guru verifiziert
- Die anderen 4: ROI auf Deposits unbekannt

**Daher 0.3x (nicht höher) bis 2026-05-05 Review.**

### HondaCivic — Trade-Size Cap
HondaCivic's avg Trade = $1,478. Bei 0.3x = $443.
Unser `MAX_TRADE_SIZE_USD` begrenzt das automatisch.
Prüfen ob MAX_TRADE_SIZE_USD ≥ $30 (Minimum für sinnvollen Copy).

### EFFICIENCYEXPERT — WR-Monitoring
PANews warnt: "WR zuletzt sinkend."
Falls nach 30 Tagen WR < 50%: Multiplier auf 0.1x reduzieren oder entfernen.

### synnet — Drawdown normal
31.7% WR = viele Verluste. 0.3x × kleine Sizes = begrenzte Downside.
Nicht aufgeben bei 10 aufeinanderfolgenden Verlusten — Longshot-Statistik.

---

## Review-Datum

**2026-05-05:** predicts.guru Deposit-ROI für alle 5 prüfen.
- PASS (ROI positiv auf Deposits): Multiplier bleibt 0.3x, Upgrade auf 0.5x möglich
- FAIL (neg. Deposit-ROI): sofort aus TARGET_WALLETS entfernen (Early-Loss-Selling Pattern)

---

_Quelle: PANews Biteye Artikel 2026-04-01 | Analyse: analyses/panews_biteye_analysis_2026-04-20.md_
