# Weather Traders — Verifikation 2026-04-20
_Erstellt: 2026-04-20 | Quellen: polymarketanalytics.com, predicts.guru, polymonit, BlockBeats, PulsarTech_

---

## Zusammenfassung

| Trader | Adresse | PnL | ROI | Strategie | HF-10 | Empfehlung |
|--------|---------|-----|-----|-----------|-------|-----------|
| **Hans323** | `0x0f37cb80dee49d55b5f6d9e595d52591d6371410` | **$1.1M** | **~1.000%+** | Barbell (Außenseiter 2-8¢) | ✅ PASS (~5/Tag) | **APPROVE 0.3x** |
| **neobrother** | `0x6297b93ea37ff92a57fd636410f3b71ebf74517e` | $29,553 | **+2.536%** | Ladder (68/Tag, automatisiert) | ❌ FAIL (68/Tag) | **REJECT HF-10** |
| automatedAItradingbot | Nicht bestätigt | $1,860 | ? | Weather + Esports (bot) | ❌ FAIL | **REJECT HF-0** |

---

## Trader 1 — Hans323

### Vollständige Adresse
`0x0f37cb80dee49d55b5f6d9e595d52591d6371410` ✅ (42 Zeichen bestätigt)

Quellen:
- polymarketanalytics.com/traders/0x0f37cb80dee49d55b5f6d9e595d52591d6371410 ✅
- polymarket.com/profile/0x0f37cb80dee49d55b5f6d9e595d52591d6371410 ✅

### Polymarket-Profil
| Kennzahl | Wert |
|----------|------|
| Joined | Oktober 2024 |
| Views | 104.1K |
| Positions Value (aktuell) | $27.1K |
| Biggest Win | **$1.0M** |
| Total Predictions | 2,859 |

### Strategie — Nassim Taleb Barbell
Hans323 kauft Temperatur-Märkte bei **2–8 Cent** — Wahrscheinlichkeiten die der Markt als fast unmöglich bewertet.
Bekanntester Trade: London Temperatur, 8% Markt-Wahrscheinlichkeit → echte meteorologische Wahrscheinlichkeit ~40–50%.

**Bestes dokumentiertes Beispiel:**
- Position: London Temperatur (spezifische Range)
- Entry-Preis: **8 Cent** (impliziert 8% Marktwahrscheinlichkeit)
- Invest: **$92,632**
- Meteorologische Modelle: ~40–50% (massive Mispricing!)
- Result: Markt löste auf $1.00 → **$1,110,000 Gewinn**
- ROI dieses Trades: **~1.100%**

**Warum es funktioniert:**
Polymarket-Preis auf Temperatur-Märkte ist oft durch naive Erwartung (Klimatologie/Mittelwert) gebildet.
Wettermodelle (ECMWF, GFS) sind signifikant präziser. Hans323 nutzt diese Informationsasymmetrie.

### HF-Bewertung
| HF | Status | Begründung |
|----|--------|-----------|
| HF-0 | ✅ PASS | $1.1M+ > $10K |
| HF-7 | ✅ PASS | ROI auf Deposits extremst positiv (~1.000%+) |
| HF-9 | ✅ PASS | Weather Markets, kein Insider-Typ-A |
| HF-10 | ✅ PASS | 2,859 Predictions / ~18 Monate = ~5/Tag — kein Bot |

### Trades/Tag Analyse
2,859 Predictions seit Oktober 2024 (18 Monate) = **~5.3 Trades/Tag**.
Dies sind überlegte Barbell-Positionen, nicht automatisiert.
Lange Perioden ohne Trade (wartet auf Mispricing), dann gebündelt.

### Bot-Kompatibilität
**MITTEL.** Primäres Problem: Die mega-profitablen Barbell-Trades sind sehr selten (1–3/Monat mit großem Size).
Bei 5% Multiplier: $92K × 5% = $4.600 pro Barbell-Trade. Unsere Budget-Cap: $30 MAX.
→ **Die Barbell-Mega-Trades können wir nicht proportional kopieren** (zu groß).
→ **Die kleinen Test-Trades (2–5 USD) können wir kopieren** → liefern aber wenig Gewinn.

**Empfehlung:** APPROVE 0.3x — hauptsächlich als Signal-Quelle für T-WEATHER-Inspiration.
Wenn Hans323 in einem Weather-Markt kauft → eigene T-WEATHER-Analyse starten.

---

## Trader 2 — neobrother

### Vollständige Adresse
`0x6297b93ea37ff92a57fd636410f3b71ebf74517e` ✅ (42 Zeichen bestätigt)

Quellen:
- polymarket.com/profile/0x6297b93ea37ff92a57fd636410f3b71ebf74517e ✅
- predicts.guru: $29,553 PnL, +2,536% ROI ✅

### predicts.guru Vollprofil
| Kennzahl | Wert |
|----------|------|
| All-Time PnL | **$29,553** |
| ROI auf Deposits | **+2,536%** |
| Deposits | **$891** |
| Withdrawals | **$23,400** |
| WR (true) | **43.9%** |
| Predictions | 3,221 (aktuell) |
| Trades/Tag | **67.9** |
| Biggest Win | $4,804 (temperature) |
| Rank | 3,845 |
| Risiko-Level | Low |

**predicts.guru AI-Summary:**
> "neobrother turned $891 into $24.8K in pure prediction market edge — 2,536% ROI on 3,223 trades.
> 67.9 trades per day. Win rate 43.9% — below coin flip — but ROI is 2,536%.
> 2,745 markets traded across weather markets everyone else ignores."

### Strategie — Temperature Laddering
Kauft simultan mehrere benachbarte Temperatur-Ranges:
- Buenos Aires: YES 29°C, 30°C, 31°C, 32°C, 33°C, 34°C+
- Einstiegspreise: **0.2¢ – 15¢** (extrem günstig)
- Wenn eine Rung gewinnt: deckt alle anderen Verluste
- Beispiel: 31°C Gewinn → **+811.78%** deckt alle anderen Rungs

Analog zu Optionen: "Wide Straddle Arbitrage" oder "Grid Trading".

### HF-Bewertung
| HF | Status | Begründung |
|----|--------|-----------|
| HF-0 | ✅ PASS | $29K > $10K |
| HF-7 | ✅ PASS | +2,536% ROI ist außergewöhnlich |
| HF-9 | ✅ PASS | Weather, kein Insider |
| HF-10 | ❌ **FAIL** | **67.9 Trades/Tag** → automatisierter Bot |

### Bot-Kompatibilität
**SEHR GERING.** 67.9 Trades/Tag = algorithmisch. Kein manueller Trader.
Durchschnittlicher Trade-Size: $891 Deposits / 3,221 Trades = **~$0.28 pro Trade**.
Bei 5% Multiplier: $0.014 — weit unter MIN_TRADE_SIZE_USD=$0.50.
Copy-Trading physisch unmöglich.

**Zusätzliches Problem:** Strategie basiert auf simultaner Platzierung aller Ladder-Rungs.
Wir können nicht wissen welche Rung er als "die richtige" sieht — wir würden alle kopieren.

**Empfehlung: REJECT — HF-10 FAIL (68/Tag) + zu kleine Trades.**
neobrother ist Inspiration für T-WEATHER Ladder-Strategie — nicht für Copy-Trading.

---

## Trader 3 — automatedAItradingbot (Bonus)

### Adresse
Polymarket-Profil: polymarket.com/@automatedaitradingbot ✅ (existiert)
Vollständige Adresse: **NICHT BESTÄTIGT** (polymonit zeigt "Wallet address not public")
Polymarket zeigt Profil aber keine 42-Zeichen-Adresse in verfügbaren Suchergebnissen.

### Profil (aus polymonit + polymarket)
| Kennzahl | Wert |
|----------|------|
| All-Time PnL | **~$1,860** (3-Monats-Profit) |
| Biggest Win | $13,200 |
| Predictions | 2,858 |
| Joined | Januar 2025 |
| Bio | "Meteorologist.IT engineer.Automated bot testing" |
| Kategorien | Weather + Esports |

### HF-Bewertung
| HF | Status | Begründung |
|----|--------|-----------|
| HF-0 | ❌ **FAIL** | $1,860 < $10K Schwelle |
| HF-10 | ❌ **FAIL** | 2,858 Predictions / 3 Monate = ~31/Tag, + "automated bot" im Bio |

**Empfehlung: REJECT — HF-0 FAIL ($1,860) + HF-10 FAIL (Bot).**
Interessant als Beobachtungsfall für T-WEATHER Strategie (meteorologist + IT engineer = weather bot).

---

## Weather Trading — Erkenntnisse für T-WEATHER

### Key Insight 1: Informationsasymmetrie
Polymarket preist Temperatur-Märkte mit naiver Klimatologie (historischer Durchschnitt).
ECMWF/GFS Wettermodelle sind deutlich präziser für 24-48h Prognosen.
→ Trader mit echten Wetterdaten haben systematischen Edge.

### Key Insight 2: Zwei orthogonale Strategien
1. **Barbell (Hans323):** Seltene Mega-Trades bei 2-8¢ → schwer zu kopieren, aber hochprofitabel
2. **Ladder (neobrother):** Viele kleine Trades → nicht kopierbar, aber Strategie replizierbar

### Key Insight 3: Buenos Aires als Hidden Gem
Mehrere Quellen nennen Buenos Aires als bevorzugten Markt (neobrother).
Grund: Weniger Konkurrenz als NYC/London, aber gutes Volumen.
→ T-WEATHER sollte Buenos Aires in Tier 2 führen.

### Key Insight 4: $92K auf 8% ist kein Gambling
Hans323's London-Trade war kein Glück: meteorologische Modelle zeigten ~40-50%.
→ T-WEATHER muss echte Wetterdaten integrieren (OpenMeteo, ECMWF), nicht nur Preise.

---

## Empfehlung für WALLETS.md

**Hans323 — APPROVE Tier B, 0.3x**
- Signal-Quelle: wenn Hans323 in Temperatur-Märkten kauft → T-WEATHER analysiert denselben Markt
- Direkt-Copy: nur sinnvoll für kleine Vorpositions-Trades (<$30)
- Barbell-Mega-Trades (>$10K): nicht direkt kopierbar, aber als Signal verwertbar

**neobrother — REJECT (HF-10)**
- Verwendung: Strategie-Vorlage für T-WEATHER Ladder-Implementation

**automatedAItradingbot — REJECT (HF-0)**
- Verwendung: Inspiration (Meteorologist + IT = weather bot concept)

---

_Verifikation: 3 Quellen für Hans323 (polymarketanalytics, polymarket, predictionmarketspicks)_
_Verifikation: 3 Quellen für neobrother (predicts.guru, polymarket, BlockBeats/PulsarTech)_
