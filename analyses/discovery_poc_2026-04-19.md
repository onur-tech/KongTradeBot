# Discovery PoC Report — T-D83 Phase 1
**Erstellt:** 2026-04-19 09:09 UTC

## Scan-Parameter
| Parameter | Wert |
|-----------|------|
| Globale Trades gescannt | 20 Seiten × 100 = 2000 |
| Unique aktive Wallets (7 Tage) | 1069 |
| Detailliert analysiert | 100 |
| Scan-Dauer | 8s |

## Hard-Filter-Thresholds
| Filter | Schwelle |
|--------|----------|
| HF-1 Sample-Size | ≥ 50 Trades/30d |
| HF-2 Account-Alter | ≥ 60 Tage |
| HF-5 Aktivität | ≤ 14 Tage inaktiv |
| HF-8 Win-Rate | 55% – 75% |

## Ergebnis-Übersicht
| Kategorie | Anzahl |
|-----------|--------|
| PASS (alle verfügbaren HF bestanden) | **13** |
| REVIEW (UNKNOWN-Filter, manuell prüfen) | 30 |
| FAIL (mindestens 1 HF versagt) | 57 |

## Top-10 Kandidaten
| Wallet | Name | WR% | Trades/30d | Alter(d) | PnL | Bereits TARGET | Verdict |
|--------|------|-----|------------|----------|-----|----------------|---------|
| `0x735d3c...ed28` | 0x735d3c... | 74% | 500 | -1 | $-644 | ❌ NEU | **PASS** |
| `0x108e28...5f24` | 0x108e28... | 72% | 500 | -1 | $-381 | ❌ NEU | **PASS** |
| `0x5bc331...7a59` | 0x5bc331... | 71% | 500 | -1 | $-319 | ❌ NEU | **PASS** |
| `0x88ad31...a1f3` | FF1FCVDTY54 | 71% | 500 | -1 | $-3428 | ❌ NEU | **PASS** |
| `0x04437d...ea0f` | 0x04437d... | 71% | 500 | -1 | $-998 | ❌ NEU | **PASS** |
| `0x19bbad...2895` | 0x19bbad... | 70% | 500 | -1 | $-7 | ❌ NEU | **PASS** |
| `0x39c0a4...cc4a` | ShadowSpread | 70% | 500 | -1 | $-386 | ❌ NEU | **PASS** |
| `0x66251f...7a6b` | 0x66251f... | 70% | 244 | -1 | $+29 | ❌ NEU | **PASS** |
| `0xb2c100...f8d5` | gnawty | 68% | 500 | -1 | $-1 | ❌ NEU | **PASS** |
| `0x674887...ee08` | nj23adsknml3 | 67% | 500 | -1 | $-273 | ❌ NEU | **PASS** |

## Neue Kandidaten (nicht in TARGET_WALLETS)
_Wallets die Filter bestehen UND noch nicht monitort werden:_

### unknown (`0x735d3c3b6b4a6bb5cabefcf3cba2f0a887b8ed28`)
- Win-Rate (Schätzung): **74%**
- Trades letzte 30 Tage: **500**
- Account-Alter: **-1 Tage**
- Aktueller cashPnL: **$-644.00**
- HF-1: PASS
- HF-2: UNKNOWN(Pagination-Limit — mind. mehrere Tage alt)
- HF-5: PASS
- HF-8: PASS(74%)
- **Verdict: PASS**

### unknown (`0x108e284c7c75f1c12ca046c8e3f6c62274d25f24`)
- Win-Rate (Schätzung): **72%**
- Trades letzte 30 Tage: **500**
- Account-Alter: **-1 Tage**
- Aktueller cashPnL: **$-381.29**
- HF-1: PASS
- HF-2: UNKNOWN(Pagination-Limit — mind. mehrere Tage alt)
- HF-5: PASS
- HF-8: PASS(72%)
- **Verdict: PASS**

### unknown (`0x5bc331ff6a2f3a679f0c98cca0d92cdda5c47a59`)
- Win-Rate (Schätzung): **71%**
- Trades letzte 30 Tage: **500**
- Account-Alter: **-1 Tage**
- Aktueller cashPnL: **$-319.36**
- HF-1: PASS
- HF-2: UNKNOWN(Pagination-Limit — mind. mehrere Tage alt)
- HF-5: PASS
- HF-8: PASS(71%)
- **Verdict: PASS**

### FF1FCVDTY54 (`0x88ad3166c6cce6a1bf732050749089273252a1f3`)
- Win-Rate (Schätzung): **71%**
- Trades letzte 30 Tage: **500**
- Account-Alter: **-1 Tage**
- Aktueller cashPnL: **$-3428.00**
- HF-1: PASS
- HF-2: UNKNOWN(Pagination-Limit — mind. mehrere Tage alt)
- HF-5: PASS
- HF-8: PASS(71%)
- **Verdict: PASS**

### unknown (`0x04437d41dfd62e838c3e415330797063e0caea0f`)
- Win-Rate (Schätzung): **71%**
- Trades letzte 30 Tage: **500**
- Account-Alter: **-1 Tage**
- Aktueller cashPnL: **$-997.67**
- HF-1: PASS
- HF-2: UNKNOWN(Pagination-Limit — mind. mehrere Tage alt)
- HF-5: PASS
- HF-8: PASS(71%)
- **Verdict: PASS**

### unknown (`0x19bbad7a3809efff764e9f78d85badb2e7a72895`)
- Win-Rate (Schätzung): **70%**
- Trades letzte 30 Tage: **500**
- Account-Alter: **-1 Tage**
- Aktueller cashPnL: **$-6.96**
- HF-1: PASS
- HF-2: UNKNOWN(Pagination-Limit — mind. mehrere Tage alt)
- HF-5: PASS
- HF-8: PASS(70%)
- **Verdict: PASS**

### ShadowSpread (`0x39c0a48cd6e536dc5d655f7ae326632e2402cc4a`)
- Win-Rate (Schätzung): **70%**
- Trades letzte 30 Tage: **500**
- Account-Alter: **-1 Tage**
- Aktueller cashPnL: **$-385.64**
- HF-1: PASS
- HF-2: UNKNOWN(Pagination-Limit — mind. mehrere Tage alt)
- HF-5: PASS
- HF-8: PASS(70%)
- **Verdict: PASS**

### unknown (`0x66251f0ec4928600bf621430a7264852923d7a6b`)
- Win-Rate (Schätzung): **70%**
- Trades letzte 30 Tage: **244**
- Account-Alter: **-1 Tage**
- Aktueller cashPnL: **$+28.83**
- HF-1: PASS
- HF-2: UNKNOWN(Pagination-Limit — mind. mehrere Tage alt)
- HF-5: PASS
- HF-8: PASS(70%)
- **Verdict: PASS**

### gnawty (`0xb2c10095563c5483f297ae53e2306e622a42f8d5`)
- Win-Rate (Schätzung): **68%**
- Trades letzte 30 Tage: **500**
- Account-Alter: **-1 Tage**
- Aktueller cashPnL: **$-0.80**
- HF-1: PASS
- HF-2: UNKNOWN(Pagination-Limit — mind. mehrere Tage alt)
- HF-5: PASS
- HF-8: PASS(68%)
- **Verdict: PASS**

### nj23adsknml3 (`0x674887d1ac838099a48b629dff53f25b7b87ee08`)
- Win-Rate (Schätzung): **67%**
- Trades letzte 30 Tage: **500**
- Account-Alter: **-1 Tage**
- Aktueller cashPnL: **$-273.33**
- HF-1: PASS
- HF-2: UNKNOWN(Pagination-Limit — mind. mehrere Tage alt)
- HF-5: PASS
- HF-8: PASS(67%)
- **Verdict: PASS**


## Win-Rate-Verteilung (alle analysierten Wallets)
| Bereich | Anzahl Wallets |
|---------|----------------|
| 0%-10% | 4 |
| 10%-20% | 5 |
| 20%-30% | 4 |
| 30%-40% | 3 |
| 40%-50% | 6 ← HF-8 Zielbereich |
| 50%-60% | 4 ← HF-8 Zielbereich |
| 60%-70% | 7 ← HF-8 Zielbereich |
| 70%-80% | 12 ← HF-8 Zielbereich |
| 80%-90% | 8 |
| 90%-100% | 16 |

## Fail-Breakdown (warum Wallets scheitern)
| Filter | Anzahl FAILs |
|--------|-------------|
| HF-8_win_rate | 53 |
| HF-2_account_age | 9 |
| HF-1_sample_size | 4 |

## Top-10 FAILs (beste Win-Rate, trotzdem rausgefallen)
| Wallet | Name | WR% | Trades/30d | Alter(d) | Fail-Grund |
|--------|------|-----|------------|----------|-----------|
| `0x83904a...3773` | saygolani | 98% | 500 | ? | HF-8_win_rate |
| `0x20d178...75db` | huli2026 | 98% | 500 | ? | HF-8_win_rate |
| `0xfcddf1...b8ac` | B8aC | 98% | 500 | ? | HF-8_win_rate |
| `0xc032f7...28c5` | Poopol | 97% | 500 | ? | HF-8_win_rate |
| `0xf73539...ee3a` | Bringmemoreluc | 97% | 500 | ? | HF-8_win_rate |
| `0x26b773...b7f1` | kaikaia | 94% | 340 | ? | HF-8_win_rate |
| `0x8858aa...8641` | prefortune | 94% | 500 | ? | HF-8_win_rate |
| `0x7e62ac...3f0e` | winnercrypto | 93% | 144 | 22 | HF-2_account_age, HF-8_win_rate |
| `0x279146...53f9` | BriannaDuffy | 93% | 500 | ? | HF-8_win_rate |
| `0x962980...ee15` | turaxmaniac | 93% | 500 | ? | HF-8_win_rate |

## Bekannte Limitierungen
1. **API Pagination-Limit (500)**: HF-Trader (BTC/ETH 5-min-Märkte) haben >500 Trades/Tag — ältester sichtbarer Record von heute → Account-Alter nicht bestimmbar. Fix: Pagination oder anderen Age-Endpoint. Aktuell → UNKNOWN statt FAIL.
2. **Stream dominiert von HFT-Bots**: BTC/ETH 5-min Up/Down Märkte machen Großteil des globalen Trade-Streams aus. Diese Wallets sind nicht sinnvoll zu kopieren. Phase 2: Filter nach market_slug excludiert *-updown-5m-*.
3. **Win-Rate-Schätzung ungenau**: REDEEM/BUY-Ratio unterschätzt echte WR — nicht alle Verliererpositionen haben explizite SELL-Events. Nur untere Schranke der echten WR.
4. **Sample-Bias**: Nur Wallets aus den letzten 7 Tagen im globalen Stream erfasst — Wallets die gerade pausieren werden nicht gesehen.
5. **HF-3, HF-4, HF-6, HF-7, HF-9 nicht auswertbar**: Drawdown, Profit-Konzentration, ROI auf Deposits, Last-Minute-Betting brauchen predicts.guru oder vollständige Handelshistorie.
6. **Rate-Limiting**: 300 Calls für 100 Wallets. Skalierung auf 1000+ braucht Caching-Layer.

## Phase-2-Machbarkeits-Einschätzung

**API funktioniert** ✅ — Discovery via globalem Trade-Stream ist machbar.

| Komponente | Aufwand | Machbarkeit |
|------------|---------|-------------|
| Globaler Scan (1000 Wallets) | 1 Tag | ✅ Hoch |
| SQLite-Cache für Scan-Ergebnisse | 0.5 Tage | ✅ Hoch |
| Echte Win-Rate via Market-Resolution | 2 Tage | ⚠️ Mittel (API-Limit) |
| predicts.guru HF-3/4/6/9 Integration | 1 Tag | ⚠️ Mittel (Scraping) |
| Automatisierung + Telegram-Alerts | 0.5 Tage | ✅ Hoch |
| **Gesamt Phase 2** | **~5 Tage** | **Machbar** |

**Empfehlung Phase 2**: SQLite-Cache + tägl. Scan von 500 Wallets + manuelle Freigabe per Telegram-Button bevor neue Wallet in TARGET_WALLETS aufgenommen wird.