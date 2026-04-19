# bcda Vollständige Verifikation
_Erstellt: 2026-04-20 | Anlass: Scout v2.0 APPROVE-Empfehlung — kritischer Gegencheck_
_Quellen: 0xinsider, predicts.guru, cointrenches, polymonit, polymarket.com_

---

## ⚠️ KRITISCHER BEFUND: REJECT — HF-7 FAIL

**bcda hat -$2.4M Gesamtverlust bei -89.41% ROI auf Deposits.**
Der cointrenches-Artikel ($2M/Woche) war irreführend — er berichtete über eine einzige Ausnahme-Woche.
**Server-CC darf bcda NICHT integrieren.**

---

## Adresse

**Vollständige Adresse (42 Zeichen bestätigt):**
`0xb45a797faa52b0fd8adc56d30382022b7b12192c`

Bestätigt via: polymarket.com, 0xinsider, cointrenches, predicts.guru — alle übereinstimmend.

---

## Daten-Divergenz: Alle Quellen im Vergleich

| Quelle | All-Time PnL | WR | Volume | Methode |
|--------|-------------|-----|--------|---------|
| cointrenches (April 2, 2026) | "+$2M/Woche" | Unbekannt | $9.54M/Woche | Snapshot einer Ausnahme-Woche |
| polymonit all-time | +$568,301 | Unbekannt | $3,154,673 | Nur Sports-resolved, Partial |
| **0xinsider (comprehensive)** | **-$1,553,910** | **44.3%** | **$86,764,667** | Alle Trades inkl. offene |
| **predicts.guru (comprehensive)** | **-$2,390,000** | **44.6%** | **$59,800,000** | Alle 841 Positionen, ROI auf Deposits |

**Konsens der umfassenden Quellen:**
- 0xinsider und predicts.guru stimmen überein: massive Verluste
- Grade (0xinsider): **F0.0** — schlechteste mögliche Bewertung
- Edge (0xinsider): **-2%** — statistisch verlierend

---

## Predicts.guru — Vollprofil

> **"Deposited $2.7M. Lost $2.4M. Still trading."**
> "Rank 2,159,959 with -$2.39M total PnL across 841 trades — a case study in conviction without edge."

| Kennzahl | Wert |
|----------|------|
| Eingezahlt (Deposits) | $2,700,000 |
| Ausgezahlt (Withdrawals) | $66,000 |
| Aktuelles Portfolio | $228,000 |
| Realisierter Verlust | -$2,390,000 |
| **ROI auf Deposits** | **-89.41%** |
| Win Rate | 44.6% |
| Trades/Tag Durchschnitt | 61/Tag (bestimmte Phasen) |
| Bester Trade | +$285,000 |
| Schlechtester Trade | -$237,000 |
| Offene Positionen | 51 (noch blutend) |

**Leaderboard-Rank predicts.guru: 2,159,959** — deutlich unter Top-Wallets.

---

## 0xinsider — Trader-Profil

| Kennzahl | Wert |
|----------|------|
| Grade | **F0.0** (schlechteste Kategorie) |
| Strategy Type | **Speculator** (nicht Directional/Accumulator) |
| Edge | **-2%** (verlierend) |
| Closed P&L | **-$1,553,910** |
| Unrealized P&L | -$217,123 |
| Win Rate | 44.3% |
| Predictions | 1,537 |
| Volume | $86,764,667 |
| First Trade | 2026-01-02 |

---

## Warum der Cointrenches-Artikel täuschte

**Das Problem:** Cointrenches berichtete am April 2, 2026 über die Woche März 23–30.
In dieser Woche machte bcda tatsächlich $1.95M–$2.04M Gewinn auf $9.54M Volume.

**Was cointrenches NICHT zeigte:**
1. **Keine all-time P&L Zahl** — nur die Gewinn-Seite einer einzelnen Ausnahme-Woche
2. **Keine ROI auf Deposits** — $2.7M eingezahlt, $66K raus
3. **Kein 0xinsider Cross-Check** — -$1.55M all-time
4. **Kein predicts.guru Cross-Check** — -89.41% ROI

**Mechanismus:** bcda hatte in Woche März 23–30 ein statistisches Hoch (wie jeder Verlier-Trader gelegentlich hat). Cointrenches erfasste genau diesen Peak. Der all-time Verlust bleibt davon unberührt.

**Vergleich zu DrPufferfish/Countryside:**
Beim predicts.guru WR-Artefakt haben Wallets hohe WR durch Early-Loss-Selling.
Bei bcda ist das Gegenteil: **44.3% WR ohne Selling-Artefakt** — das ist echte Underperformance.
Kein Selling-Trick, keine Zombie-Orders — bcda ist schlicht ein Verlierer-Wallet.

---

## Nachhaltigkeit des $2M/Woche Claims

**Nein — definitiv nicht nachhaltig.**

- April 2026 Leaderboard Top 10: bcda **nicht vorhanden**
- Gesamte 3 Monate (Jan–April 2026): -$2.4M Nettoverlust
- Die eine gute Woche (März 23–30) ist Ausreißer, nicht Baseline
- WR 44.3% bedeutet statistisch: jede weitere Woche ist im Erwartungswert negativ

**Mathematik:** Bei 44.3% WR und angenommener 1:1 G:L-Ratio:
- EV pro Trade = 0.443 × $X - 0.557 × $X = **-11.4% pro Trade**
- Über 1.537 Trades akkumuliert sich das zu -$1.55M → konsistent mit Daten

---

## Insider-Pattern Prüfung

**Kein Insider-Pattern erkennbar bei bcda.**

- Kategorie laut polymonit März: "Elections" (nicht Geopolitics)
- Strategie: Sports-Spreads (NBA, NHL, MLB) — öffentliche Märkte
- ref: gosports (polymarket Referrer) = Sports-Community Herkunft
- Kein Muster von frischen Wallets auf Low-Probability Events
- Keine auffälligen Positionen auf < 10 Cent Events gefunden
- 0xinsider flaggt keinen Insider-Typ-A (nur schlechte Performance)

**HF-9: ✅ PASS (kein Insider) — aber irrelevant wegen HF-7 FAIL**

---

## HF-Bewertung vollständig

| HF | Kriterium | Status | Begründung |
|----|-----------|--------|-----------|
| HF-0 | Gesamtgewinn > $10K | ❌ FAIL | -$2.4M Gesamtverlust |
| HF-7 | ROI auf Deposits > 0% | ❌ **K.O. FAIL** | -89.41% ROI auf $2.7M Deposits |
| HF-9 | Kein Insider-Typ-A | ✅ PASS | Sports-Märkte, kein Early-Bet-Pattern |
| HF-10 | Kein bestätigter HFT-Bot | ✅ PASS | 14-61 Trades/Tag, Sports |

**Zwei K.O.-Filter direkt FAIL: HF-0 + HF-7.**
Beide sind valide Ablehnungsgründe in v2.0.

---

## Erklärungs-Hypothese: Was März 23–30 passiert ist

**Hypothese:** bcda ist ein Gambler mit Sizing-Problem.

- WR 44.3% = systematisch verlierend
- Aber: Positionsgrößen $100K–$400K pro Bet
- In einer Lucky-Streak-Woche können 5–10 Treffer $1.95M produzieren
- Die Verluste der anderen 10–12 Wochen sind -$2.4M netto
- Cointrenches hat genau die 1-in-12-Wochen-Anomalie eingefangen

**Gut-to-Bad-Ratio:** $2M Best-Week / -$2.4M All-Time = der "Best-Week-Artikel"
repräsentiert ~83% des All-Time-Verlusts als positiven Ausreißer. Das ist Varianz, kein Edge.

---

## Verifikations-Lektion für zukünftige Scouts

> **PFLICHT-PROTOKOLL für jeden neuen APPROVE-Kandidaten:**
>
> 1. **0xinsider Fullcheck:** Grade, closed P&L, WR, Edge
> 2. **predicts.guru Fullcheck:** ROI auf Deposits, Rank, narrative Summary
> 3. **Cross-Check Konsens:** Beide Quellen müssen positiv bestätigen
>
> Cointrenches = EXZELLENT für neue Wallets entdecken, GEFÄHRLICH als einzige PnL-Quelle.
> Cointrenches zeigt Peak-Perioden, nicht All-Time-Realität.

**Diese Lektion als KB-Eintrag (vorschlagen):**
> KB P084: "Neue APPROVE-Kandidaten erfordern positives all-time PnL auf BEIDEN:
> 0xinsider (closed P&L > 0) UND predicts.guru (ROI auf Deposits > 0%).
> Cointrenches allein ist kein ausreichender Beweis."

---

## Empfehlung

| Feld | Wert |
|------|------|
| **Adresse** | `0xb45a797faa52b0fd8adc56d30382022b7b12192c` |
| **Bestätigter All-Time PnL** | **-$1,553,910 (0xinsider) / -$2,390,000 (predicts.guru)** |
| **ROI auf Deposits** | **-89.41%** |
| **Zeitraum** | Januar 2026 – April 2026 (3 Monate) |
| **Hauptkategorie** | Sports (NBA/NHL/MLB) — aber verlierend |
| **Nachhaltigkeit** | ❌ NEIN — eine Gewinn-Woche auf Basis von WR 44.3% |
| **Insider-Pattern erkennbar** | ❌ NEIN |
| **Grade (0xinsider)** | F0.0 — schlechteste Kategorie |
| **Empfehlung** | ❌ **REJECT — HF-7 FAIL** |
| **Server-CC kann integrieren** | ❌ **NEIN** |

---

## Konsequenzen für WALLETS.md

**wallet_scout_v2_2026-04-20.md muss korrigiert werden:**
- bcda von "APPROVE Tier B 0.5x" → **REJECT (HF-7 FAIL)**
- April#1 Sports bleibt entfernt (war bereits geplant, unabhängig von bcda)
- Kein Sports-Slot-Tausch nötig

**Neue Suche nach Sports-Replacement:**
- bcda-Slot bleibt leer bis valider Sports-Kandidat gefunden
- Candidates aus Research Queue: CemeterySun, MinorKey4 (beide unverified)

---

_Verifikation mit 3 unabhängigen Quellen durchgeführt (0xinsider + predicts.guru + polymarket.com)_
_Cointrenches-Artikel war Peak-Snapshot, nicht All-Time-Darstellung_
