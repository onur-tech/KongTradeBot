# Discovery Phase 1.6 Report — T-D83
**Erstellt:** 2026-04-19 10:02 UTC

## Scan-Konfiguration
| Parameter | Wert |
|-----------|------|
| Events gescannt | 600 |
| Laufzeit | 11s |

## Kategorie-Statistik
| Kategorie | Märkte (Tokens) | Unique Wallets | HF-10 Skip | Analysiert |
|-----------|----------------|---------------|-----------|-----------|
| geopolitics | 100 | 20 | 9 | 11 |
| politics | 100 | 0 | 0 | 0 |
| tech | 100 | 0 | 0 | 0 |
| culture | 100 | 0 | 0 | 0 |
| macro | 78 | 0 | 0 | 0 |
| sports_ref | 100 | 20 | 4 | 16 |

## Gesamtergebnis
| Kategorie | Anzahl |
|-----------|--------|
| **PASS** | **0** (0 NEU) |
| REVIEW   | 0 |
| FAIL     | 27 |

## Bucket-Split
| Bucket | PASS | REVIEW |
|--------|------|--------|
| Active Traders (3-15/Tag) | 0 | 0 |
| Patient Specialists (0.5-3/Tag) | 0 | 0 |

---
## Kategorie: GEOPOLITICS
PASS: **0** | REVIEW: 0 | FAIL: 11

### Top-5 Kandidaten — geopolitics
| Wallet | Name | Archetyp | Bucket | WR% | G/L | Trades/60d | Alter | Score | Verdict |
|--------|------|---------|--------|-----|-----|-----------|-------|-------|---------|
| `0x57de59...ec79` | 0x57de59 | Generalist | active | 6% | 3.54 | 66 | 10 | 30 | **FAIL** |
| `0xf84646...d6bd` | BVoltar | Patient-Generalist | patient | 5% | -0.59 | 82 | 39 | 20 | **FAIL** |
| `0xcedf6e...18bb` | BDeltaX | Patient-Generalist | patient | 14% | -0.37 | 82 | 38 | 20 | **FAIL** |
| `0x40a7a0...6a79` | Janyce57828072 | Generalist | active | 9% | 0.04 | 0 | 70 | 10 | **FAIL** |
| `0x927228...0ea3` | erwindevisa1 | Generalist | active | 12% | 0.06 | 212 | 63 | 10 | **FAIL** |
---
## Kategorie: SPORTS_REF
PASS: **0** | REVIEW: 0 | FAIL: 16

### Top-5 Kandidaten — sports_ref
| Wallet | Name | Archetyp | Bucket | WR% | G/L | Trades/60d | Alter | Score | Verdict |
|--------|------|---------|--------|-----|-----|-----------|-------|-------|---------|
| `0x646e8b...105f` | rift4 | Sports_ref-Spezialist | unknown | 65% | 0.00 | 13 | 57 | 35 | **FAIL** |
| `0x0c3f03...c16a` | 0x0c3F038E139D | Patient-Sports_ref-Spezialist | patient | 41% | -0.41 | 0 | 28 | 30 | **FAIL** |
| `0x022b8c...f2f3` | 0xNomis | Sports_ref-Spezialist | out_of_range | 28% | ? | 0 | 555 | 20 | **FAIL** |
| `0x47a1b0...f15b` | ProWhale9910 | Sports_ref-Spezialist | active | 13% | -0.78 | 500 | 77 | 20 | **FAIL** |
| `0x07feb3...4d66` | 0x07Feb3b20076 | Sports_ref-Spezialist | active | 34% | -0.39 | 500 | 63 | 20 | **FAIL** |

---
## Top-10 Overall (Cross-Kategorie) — Brrudi Verifikations-Liste
| Rank | Wallet | Name | Kategorie | Archetyp | WR% | G/L | TPD | Score | Verdict |
|------|--------|------|----------|---------|-----|-----|-----|-------|---------|
| 1 | `0x646e8b...105f` | rift4 | sports_ref | Sports_ref-Spezialist | 65% | 0.00 | 0.0 | 35 | **FAIL** |
| 2 | `0x0c3f03...c16a` | 0x0c3F038E139D | sports_ref | Patient-Sports_ref-Spezialist | 41% | -0.41 | 2.2 | 30 | **FAIL** |
| 3 | `0x57de59...ec79` | 0x57de59 | geopolitics | Generalist | 6% | 3.54 | 6.3 | 30 | **FAIL** |
| 4 | `0x022b8c...f2f3` | 0xNomis | sports_ref | Sports_ref-Spezialist | 28% | ? | 0.5 | 20 | **FAIL** |
| 5 | `0x47a1b0...f15b` | ProWhale9910 | sports_ref | Sports_ref-Spezialist | 13% | -0.78 | 11.8 | 20 | **FAIL** |
| 6 | `0xf84646...d6bd` | BVoltar | geopolitics | Patient-Generalist | 5% | -0.59 | 2.1 | 20 | **FAIL** |
| 7 | `0x07feb3...4d66` | 0x07Feb3b20076 | sports_ref | Sports_ref-Spezialist | 34% | -0.39 | 10.8 | 20 | **FAIL** |
| 8 | `0x2ddde3...271a` | siavoshsaif | sports_ref | Sports_ref-Spezialist | 8% | 0.08 | 3.9 | 20 | **FAIL** |
| 9 | `0x6cbd09...5480` | 0x6cbd09 | sports_ref | Sports_ref-Spezialist | 32% | -0.56 | 0.0 | 20 | **FAIL** |
| 10 | `0xfe1fc9...a9b2` | kwaikhossain22 | sports_ref | Sports_ref-Spezialist | 13% | 0.06 | 3.4 | 20 | **FAIL** |

---
## PASS-Kandidaten — Detail
---
## Fail-Breakdown
| Filter | Anzahl FAILs |
|--------|-------------|
| HF-8_winrate | 26 |
| GL_ratio | 25 |
| HF-2_age | 12 |
| HF-1_sample | 10 |

## Gain-Loss Ratio Statistik
| Metrik | Wert |
|--------|------|
| Wallets mit G/L Daten | 26 |
| G/L >= 1.5 (Filter-PASS) | 1 |
| G/L >= 2.0 (0xIcaruss-Benchmark) | 1 |

## Frequenz-Bucket Verteilung
| Bucket | Wallets |
|--------|---------|
| active | 15 |
| unknown | 5 |
| out_of_range | 4 |
| patient | 3 |

## Discovery-Statistik
| Parameter | Wert |
|-----------|------|
| Events gescannt | 600 |
| Qualifying Market-Tokens | 578 |
| Wallets gesammelt (vor HF-10) | 40 |
| HF-10 ausgeschlossen (Bot) | 13 |
| Detailliert analysiert | 27 |
| Laufzeit | 11s |
| API-Calls (geschätzt) | 713 |
| Coverage-Schätzung | ~100% der Top-578k Markt-Trades |

## Bekannte Limitierungen
1. Gain-Loss Ratio basiert auf REDEEM/BUY-Matching — offene Positionen als nicht verloren gezählt (Schätzung).
2. Account-Alter ohne Polygonscan-Key nur via Pagination (1500 Records) bestimmbar.
3. Gamma API volume = Lifetime-Volumen; Nischen-Filter nicht exakt möglich.
4. Culture-Kategorie unterrepräsentiert (nur 4 aktive Märkte gefunden).
5. G/L Ratio < 1.0 möglich wenn REDEEM-usdcSize < BUY-usdcSize (niedrige Gewinn-Preise).

## Phase-2-Aufwand (aktualisiert nach Phase 1.6)
| Komponente | Status | Aufwand |
|------------|--------|---------|
| Kategorie-Scan | ✅ Phase 1.6 | — |
| HFT-Filter HF-10 | ✅ Phase 1.6 | — |
| Gain-Loss Ratio | ✅ Phase 1.6 | — |
| Bucket-Split | ✅ Phase 1.6 | — |
| Account-Alter (Polygonscan) | ❌ | 0.5 Tage (API Key nötig) |
| Win-Rate via Market-Resolution | ❌ | 2 Tage |
| HF-3/4/6/7/9 (predicts.guru) | ❌ | 1 Tag |
| SQLite Cache | ❌ | 0.5 Tage |
| Telegram-Alert bei PASS | ❌ | 0.5 Tage |
| **Gesamt Phase 2** | | **~4.5 Tage** |