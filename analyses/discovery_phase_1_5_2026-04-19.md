# Discovery Phase 1.5 Report — T-D83
**Erstellt:** 2026-04-19 09:32 UTC

## Scan-Konfiguration
| Parameter | Wert |
|-----------|------|
| Events gescannt (Gamma API) | 400 |
| Qualifying Markets (HF-10 pre) | 1020 |
| Unique Wallets gesammelt | 181 |
| Nach HF-10 ausgeschlossen | 48 |
| Detailliert analysiert | 32 |
| Scan-Dauer | 21s |

## Kategorien gescannt
| Kategorie | Qualifying Markets | Wallets beigesteuert |
|-----------|------------------|---------------------|
| culture | 160 | 90 |
| macro | 48 | 181 |
| politics | 812 | 181 |

## Ergebnis-Übersicht
| Kategorie | Anzahl |
|-----------|--------|
| PASS | **1** (1 NEU / nicht in TARGET_WALLETS) |
| REVIEW | 0 |
| FAIL | 31 |

## PASS-Kandidaten
| Wallet | Name | Archetyp | WR% | Trades/60d | Alter(d) | cashPnL | TARGET? |
|--------|------|---------|-----|------------|----------|---------|---------|
| `0x9fe535...7936` | jakgez | Politics-Spezialist | 60% | 500 | 94 | $-1943 | ❌ NEU |

### jakgez (`0x9fe53544870879b23a75a2cea0fa35d752cd7936`)
- **Archetyp**: Politics-Spezialist
- **Kategorie-Fokus**: politics — 88% der Category-Trades
- Kategorie-Breakdown: {'politics': 541, 'culture': 50, 'macro': 27}
- Win-Rate (Schätzung): **60%**
- Trades letzte 60 Tage: **500**
- Account-Alter: **94 Tage**
- HFT-Anteil eigener Trades: **0%** (Trades/Tag: 14.4)
- cashPnL: **$-1942.56**
- HF-1: PASS
- HF-2: PASS
- HF-5: PASS
- HF-8: PASS(60%)
- HF-10: PASS
- **Verdict: PASS**


## Fail-Breakdown
| Filter | Anzahl FAILs |
|--------|-------------|
| HF-8_win_rate | 26 |
| HF-2_account_age | 19 |
| HF-1_sample_size | 12 |

## Win-Rate-Verteilung
| Bereich | Wallets |
|---------|---------|
| 0%-10% | 7 |
| 20%-30% | 4 |
| 30%-40% | 1 |
| 40%-50% | 2 ← HF-8 Zielbereich |
| 50%-60% | 5 ← HF-8 Zielbereich |
| 60%-70% | 1 ← HF-8 Zielbereich |
| 80%-90% | 2 |
| 90%-100% | 8 |

## Bekannte Limitierungen
1. **Account-Alter**: Ohne Polygonscan API-Key nur via Aktivitäts-Pagination bestimmbar.
   3×500 Records = max 1500 Events. Sehr aktive Wallets bleiben UNKNOWN.
2. **Gamma API Volume**: Feld enthält Gesamt-Lifetime-Volumen (nicht nur aktiv).
   Nischen-Filter $25k-$3M trifft deshalb teils historische Märkte.
3. **Category-Zuordnung**: Keyword-basiert — False-Positives möglich.
4. **HF-10 Schwelle**: 50% HFT ist konservativ. Legitime Multi-Strategy-Trader könnten ausgeschlossen werden.
5. **Win-Rate-Schätzung**: REDEEM/BUY-Ratio = untere Schranke. Echte WR vermutlich höher.
6. **HF-3,4,6,7,9 fehlen**: Drawdown, Profit-Konzentration, ROI brauchen predicts.guru.

## Phase-2-Machbarkeits-Einschätzung

| Komponente | Phase 1.5 Status | Phase 2 Bedarf |
|------------|-----------------|----------------|
| Kategorie-Scan (Gamma API) | ✅ Implementiert | Mehr Kategorien, Zeitfenster |
| HFT-Filter (HF-10) | ✅ Implementiert | Schwelle tunen |
| Account-Alter | ⚠️ Pagination-basiert | Polygonscan API Key |
| Win-Rate | ⚠️ REDEEM-Schätzung | Market-Resolution API |
| HF-3/4/6/7/9 | ❌ Nicht implementiert | predicts.guru Integration |
| Telegram-Alert | ❌ Nicht implementiert | 0.5 Tage |

**Empfehlung**: Polygonscan API Key (kostenlos) in .env eintragen → HF-2 für alle Wallets lösbar.
Phase 2 Gesamtaufwand: ~4 Tage (reduziert dank Phase 1.5 Erkenntnissen).