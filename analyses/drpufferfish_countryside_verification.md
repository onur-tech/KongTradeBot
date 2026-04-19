# HF-8 Verifikation — DrPufferfish + Countryside
_Erstellt: 2026-04-20 | Windows-CC | Aufgabe: Domain-Experte-Signatur prüfen_
_Quellen: predicts.guru, 0xinsider, cointrenches.io, PANews, Phemex, polymonit_

---

## Ergebnis-Zusammenfassung

| Wallet | Wahre WR | HF-8 | Insider-Risiko | Kopierbarkeit | Empfehlung |
|--------|----------|------|---------------|---------------|------------|
| **DrPufferfish** | ~50.9% | ❌ FAIL | ✅ NIEDRIG | ❌ NICHT KOPIERBAR | Shadow Tier C |
| **Countryside** | 48.5–54.7% | ❌ FAIL / ❓ UNKLAR | ✅ NIEDRIG | ⚠ BEDINGT | WATCHING |

**Keine Integration in TARGET_WALLETS. Keine .env-Änderungen.**

---

## DrPufferfish — Detailanalyse

### Daten-Divergenz: Warum 91% WR falsch ist

| Quelle | WR | Methode | Bewertung |
|--------|-----|---------|-----------|
| predicts.guru | 91–100% | Nur geschlossene/verkaufte Positionen | ❌ IRREFÜHREND |
| 0xinsider (NBA) | 93.5% | NBA-spezifische Auflösungen | ❌ EBENFALLS GEFILTERT |
| Phemex/Jan 2026 | 80.82% | 490 geschlossene Predictions | ❌ NOCH IMMER GEFILTERT |
| PANews (Tiefenanalyse) | **50.9%** | Inkl. Zombie-Orders (alle offenen Positionen) | ✅ WAHRE WR |

**Warum die Diskrepanz?**
PANews-Analyse (Jan 2026, 27.000+ Trades der Top-10-Whales untersucht):
> _"Considering the large number of 'zombie orders' he held, his win rate dropped to 50.9%."_

DrPufferfish verkauft Verlierer FRÜH (Exit vor Resolution) → sie tauchen als "Sells" auf,
nicht als "Losses". predicts.guru zählt nur aufgelöste Positionen → WR erscheint 80–91%.

---

### DrPufferfish Strategie (PANews dekodiert)

**Basket-Hedging:**
> _"Regarding the MLS championship, he simultaneously bet on 27 teams with lower probabilities,
> and the combined probability exceeded 54%. Through this strategy, he transformed low-probability
> events into high-probability ones."_

- Wettet auf 27 Teams gleichzeitig in einem Turnier
- Kombinierte Wahrscheinlichkeit > 54% → mathematisch ein "sicheres" Bet
- Ein Team gewinnt → deckt alle anderen Verluste + Gewinn

**Profit-/Verlust-Management:**
> _"Liverpool: predicted 123 times, ~$1.6M total profit. Average win: $37,200, average loss: $11,000.
> Sold most losing orders early to control losses."_

- Gain:Loss-Ratio: 3.4x (nicht Win-Rate ist der Edge)
- Verlierer werden bei 30–40% Wertverlust verkauft
- Gewinner werden bis zur Resolution gehalten

**Zombie-Orders:**
- 500 offene Positionen (Stand April 2026) vs. nur ~50 resolved
- Viele davon sind wertlose Futures (Celtics @ 4.4¢, Pistons @ 5.2¢)
- Diese werden nie verkauft → schleichen sich durch als "nicht aufgelöst"

---

### HF-8 Check: DrPufferfish

**Wahre WR: 50.9% → UNTER HF-8 Minimum (55% Standard / 52% Learning)**

| Domain-Experte-Signatur | Status | Begründung |
|------------------------|--------|-----------|
| Haltezeit-Median > 3 Tage | ✅ PASS | 500 Futures-Positionen (Monate) dominieren den Median |
| Kategorie-Fokus > 70% | ✅ PASS | Sports (NBA + Soccer) ~80% des PnL |
| Keine Last-Minute-Trades | ✅ PASS | Frühe Exits (Verlierer-Verkauf vor Resolution) |

**ABER: Domain-Experte-Signatur ist nur relevant wenn WR > 75%.**
Bei wahrer WR 50.9% ist HF-8 direkt FAIL — weder 55–75% noch >75% erfüllt.

**HF-8 Urteil: ❌ FAIL**
Grund: Wahre Win-Rate 50.9% liegt unter dem absoluten Minimum von 52% (Learning Modus).

---

### Insider-Risiko: DrPufferfish

**NIEDRIG — Kein Insider-Typ-A.**

Strategie ist dokumentiert, mathematisch transparent und nicht auf Vorab-Information angewiesen:
- Basket-Hedging = kombinierte Wahrscheinlichkeit > 50% auf Turnierniveau
- Early-Loss-Selling = mechanisches Risikomanagement
- Liverpool 123x = tiefes Sportexpertenwissen (Insider-Typ-B, legitim)
- Keine auffälligen Positionen kurz vor unerwarteten Ereignissen (nicht getriggert)

**Warum trotzdem NICHT kopierbar?**
Die Strategie erfordert das VOLLSTÄNDIGE BASKET gleichzeitig:
- DrPufferfish setzt $1M auf 27 Teams → Gewinner deckt alles
- Wir kopieren alle 27 als einzelne Signale (à $14 bei 0.3x/0.07/60$-Cap)
- Wenn wir nur 5 von 27 sehen (Multi-Signal-Buffer, Speed-Delay): Basket kaputt
- Selbst wenn alle 27: $14 × 27 = $378 total → Gewinner zahlt ~$70 → Netto -$308

**Ergebnis:** Architektur-Inkompatibilität. Nicht Qualitätsproblem.

---

### Empfehlung: DrPufferfish

**SHADOW TIER C (0.0x Multiplier) — Nicht kopieren, beobachten.**

Wiedereinstiegs-Bedingungen:
- Bot kann Basket-Strategie als Einheit erkennen (T-M20 oder ähnlich: "gleiche Turnier-Signale bündeln")
- Oder: Nur NBA Same-Day Game Signale kopieren (NICHT die Futures/Basket-Bets)
- Review: 2026-07-20 (90-Tage Shadow-Tracking)

---

---

## Countryside — Detailanalyse

### Daten-Divergenz: Drei verschiedene Win-Rates

| Quelle | WR | Predictions | Datum | Methode |
|--------|-----|-------------|-------|---------|
| predicts.guru | 96.7% / 91.96% | ~410 | Aktuell | Nur verkaufte/aufgelöste Positionen |
| 0xinsider | **54.7%** | 786 | Aktuell | Gesamt-Auflösungen |
| cointrenches | **48.5%** | 637 | 03.04.2026 | Alle resolved Predictions |

**Predicts.guru (96.7%)** ist ebenfalls durch early-selling verzerrt.
**0xinsider (54.7%)** und **cointrenches (48.5%)** sind die realistischeren Werte.

---

### Countryside Strategie (cointrenches dekodiert)

**NBA Same-Day Execution Model:**
> _"Position sizes typically run between $200,000 and $700,000 per bet. At 48.5% win rate, the
> model generates profit through positive expectancy on winning positions rather than win rate."_

- Avg Gewinn pro Win: ~$56,600 (+14.2% return auf $400K)
- Avg Verlust pro Loss: ~$53,800 (-13.5% return auf $400K)
- G:L-Ratio: 1.05x — sehr dünn, braucht enorme Volumina
- Netto-Edge: ~$2,800 pro Trade × 637 Trades = $1.78M (stimmt mit all-time überein)

**Spezifische Edges:**
- Timberwolves: 3 der Top-15-Wins (spezifische Team-Pricing-Edge)
- Lakers: 4 der Top-15-Wins (konsistenter Read auf LA-Matchups)
- Back-to-back-Wins: März 11+12, März 27+28 = Cluster-Strategie, nicht random

**"15% human" (0xinsider):**
85% der Trades zeigen automatisierte Merkmale. Literal HF-10 wird NICHT getriggert
(nur 4.6 Trades/Tag, positive PnL), aber das Pattern ist besorgniserregend.
Es deutet auf semi-automatisierten Order-Flow hin: Algo identifiziert NBA-Mispricing,
Mensch bestätigt (oder umgekehrt).

---

### HF-8 Check: Countryside

**WR-abhängige Bewertung:**

**Option A: predicts.guru WR 96%** → braucht Domain-Experte-Signatur:
| Kriterium | Status | Begründung |
|-----------|--------|-----------|
| Haltezeit-Median > 3 Tage | ❌ FAIL | NBA Same-Day-Games lösen in Stunden auf! Top-15-Wins alle same-day (Timberwolves, Lakers, Warriors) — kein einziger Futures-Trade |
| Kategorie-Fokus > 70% | ✅ PASS | "Almost all positions are NBA spreads and totals" (cointrenches) |
| Keine Last-Minute-Trades | ❓ UNBEKANNT | Timing-Daten nicht öffentlich, aber same-day model = oft kurz vor Tip-Off |

→ **HF-8 FAIL** wegen Haltezeit < 3 Tage (NBA-Spiele = Stunden, nicht Tage)

**Option B: 0xinsider WR 54.7%** → liegt im 55-75% Bereich, kein Domain-Experte nötig:
- 54.7% barely over 52% learning threshold
- But: 48.5% (cointrenches) contradicts this
→ **HF-8 BORDERLINE** — datenabhängig, zu unsicher für Approval

**Option C: cointrenches WR 48.5%** → unter Minimum:
→ **HF-8 FAIL**

**HF-8 Urteil: ❌ FAIL / ❓ UNKLAR**

Selbst im Best-Case (0xinsider 54.7%) ist die Datenlage zu widersprüchlich für eine Approval.
Schlimmst-Fall (48.5%) ist klares Fail.

---

### Insider-Risiko: Countryside

**NIEDRIG — NBA Statistical Execution Model.**

- Strategie vollständig dokumentiert (cointrenches, 0xinsider, polymonit)
- Edge kommt aus NBA-Markt-Pricing-Ineffizienzen (G:L ratio 1.05x bei großen Volumina)
- Kein Hinweis auf Pre-Resolution-Information
- Lakers/Timberwolves-Edge = Team-spezifisches Analyse-Modell (legitim)
- "15% human" = partiell automatisiert, aber kein klassischer Insider-Typ-A

---

### Kopierbarkeit: Countryside

**Bedingt — Signale sind real, Proporze passen nicht.**

Position Size: $200K–$700K. Unser Copy bei 0.3x auf $60 Cap:
- Unser Trade: ~$14 pro Signal
- Countryside's Trade: ~$400K
- Verhältnis: 0.0035% — wir sind im Staub

Bei echter WR von 54.7% wäre EV pro Trade:
- Win: $14 × (56.6K/400K) = +$1.98
- Loss: $14 × (53.8K/400K) = -$1.88
- EV = 0.547 × $1.98 + 0.453 × (-$1.88) = **+$0.23 pro Trade**

Positiv! Aber 23 Cent EV bei 14$ Einsatz = 1.6% EV. Nach Fees (CLOB ~1%): **kaum Break-Even.**

Wenn WR 48.5%:
- EV = 0.485 × $1.98 + 0.515 × (-$1.88) = $0.96 - $0.97 = **-$0.01 pro Trade**

→ Essentially breakeven or slightly negative.

---

### Empfehlung: Countryside

**WATCHING (0.0x Multiplier) — Kein Bot-Signal, manuelle Beobachtung.**

Wiedereinstiegs-Bedingungen:
1. WR-Diskrepanz (48.5% vs 54.7%) durch eigenes Shadow-Tracking klären (30 Tage)
2. "15% human" Pattern auflösen: Ist es Algo-unterstütztes Menschentrading oder volles Bot-System?
3. Wenn 30-Tage Shadow-WR ≥ 56%: Tier B Integration mit 0.3x erwägen
4. Review: 2026-05-20

---

## Gemeinsame Erkenntnis: Das predicts.guru WR-Problem

**Beide Wallets demonstrieren dasselbe strukturelle Problem:**

predicts.guru zeigt artifizielle WR weil:
1. Early-Loss-Selling: Verlierer werden vor Resolution verkauft → tauchen als "Sells" auf, nicht "Losses"
2. Zombie-Orders: Unaufgelöste Positionen zählen nicht in WR
3. Selektion: Nur "echte" Resolutions gezählt, gekippte Exits nicht

**Implikation für zukünftige Scouts:**
> **predicts.guru WR > 80% ist ein Warn-Signal, kein Beweis.**
> Cross-Check mit cointrenches, 0xinsider oder PANews-Tiefenanalyse PFLICHT bevor Approval.

Neue Faustregel (KB-Kandidat): **WR-Verifikation erfordert ≥2 unabhängige Quellen mit gleicher Methode.**

---

## Portfolio-Construction Check (Dalio PC-Regeln)

Falls DrPufferfish ODER Countryside später approved werden (nach besseren Daten):

**PC-2 Konflikt — Max 3 Wallets pro Kategorie Sports:**
| Aktuell in Sports | Kategorie | Multiplier |
|------------------|-----------|------------|
| majorexploiter | Sports/UCL | 1.5x |
| HorizonSplendidView | Sports | 0.5x |
| reachingthesky | Politik/Mixed | 1.0x (anteilig Sports) |
| April#1 Sports | Sports | 0.3x |

Kapazität: Noch **1 Sports-Slot** frei (PC-2: max 3 → majorexploiter + HorizonSplendidView + April#1 = 3).
→ Nur EINER von DrPufferfish / Countryside könnte aufgenommen werden.

**PC-1 Konflikt — DrPufferfish + Countryside:**
Beide NBA-fokussiert → >70% Kategorie-Überschneidung → würden sich gegenseitig sperren.

---

## Nächste Schritte

| Aktion | Datum | Verantwortlich |
|--------|-------|----------------|
| Shadow-Track Countryside via polymonit (30 Tage) | 2026-05-20 | Windows-CC |
| Shadow-Track DrPufferfish (Basket-Pattern validieren) | 2026-07-20 | Windows-CC |
| KB-Eintrag: predicts.guru WR-Verzerrung | Heute | Windows-CC |
| Nächster Scout: statwC00KS predicts.guru verifizieren | 2026-05-05 | Windows-CC |

---

## Referenzen

| Quelle | Inhalt |
|--------|--------|
| PANews "In-depth analysis of 27,000 trades by top 10 whales" | DrPufferfish wahre WR 50.9%, Basket-Strategie, Early-Selling |
| cointrenches.io/countryside-polymarket-wallet-all-time-profile | Countryside wahre WR 48.5%, Top-15-Wins, NBA same-day Model |
| 0xinsider.com/polymarket/@Countryside | WR 54.7%, "15% human", 786 Predictions |
| predicts.guru/checker/0xdB27... | DrPufferfish displayed 91% WR (Early-Sell-Artefakt) |
| predicts.guru/checker/0xbddf... | Countryside displayed 96% WR (Early-Sell-Artefakt) |
| phemex.com DrPufferfish Jan 2026 | 80.82% WR auf 490 closed predictions (gleiche Verzerrung) |
| WALLET_SCOUT_BRIEFING.md HF-8 | Domain-Experte-Signatur Kriterien |
