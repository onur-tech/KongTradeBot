# KongTrade — Wallet Registry
_Stand: 21.04.2026 | Aktualisiert nach wallet_performance_report.py_

## Legende
- **ENV-Weight**: Aktiver Multiplier in WALLET_WEIGHTS (.env) — wird beim nächsten Restart geladen
- **Decision**: Letzter manueller Entscheid aus wallet_decisions.jsonl
- **WR / PnL**: Aus trades_archive.json (echte Fills, nur aufgelöste Trades)

---

## ⚠️  Schwache Performer (gesenkt 21.04.2026)

| Wallet | Alias | WR% | PnL | ENV-Weight | Decision | Notiz |
|--------|-------|-----|-----|-----------|----------|-------|
| 0x2005...75ea | RN1 | 38% | -$193 | **0.3x** | REMOVE | Schlechteste echte Wallet, 81 Trades |
| 0xee61...debf | sovereign2013 | 33% | -$23 | **0.2x** | REMOVE | Nur 3 Trades kopiert, HF-8 WR FAIL |

> **Hinweis:** In der Session-Analyse vom 21.04. wurde sovereign2013 irrtümlich als "denizz"
> bezeichnet. Denizz = `0xbaa2...` (separate Wallet, aktuell 0.20x ENV-Weight).

---

## ✅ Aktive Wallets (alle TARGET_WALLETS)

| Wallet | Alias | ENV-Weight | Decision | Trades (kopiert) |
|--------|-------|-----------|----------|-----------------|
| 0x0197...9f3c | majorexploiter | 1.0x | RECAL ↑1.5 | — |
| 0x4924...3782 | April#1 Sports | 0.3x | REVIEW | — |
| 0x0222...8ff7 | HorizonSplendidView | 0.3x | RECAL ↓0.5 | — |
| 0xefbc...f9a2 | reachingthesky | 0.3x | REVIEW | — |
| 0x0B7A...86cf | HOOK | 0.1x | REVIEW | — |
| 0xbaa2...2c73 | denizz | 0.20x | RECAL ↑1.0 | 9 |
| 0xde7b...5f4b | wan123 | 0.05x | RECAL ↓0.5 | — |
| 0x7177...ddef | kcnyekchno | — (default) | RECAL ↑1.0 | — |
| 0xbddf...c684 | Countryside | 0.3x | REVIEW | — |
| 0xde17...0988 | Crypto Spezialist | 0.2x | REVIEW | — |
| 0xd84c...07b9 | BoneReader | 0.2x | REVIEW | — |
| 0xc658...b784 | Erasmus | 0.2x | ADD_TIER_B | — |
| 0x0c0e...434e | TheSpiritofUkraine | 0.2x | ADD_TIER_B | — |
| 0x2005...75ea | RN1 | **0.3x** ← gesenkt | REMOVE | 81 (81 closed) |
| 0xee61...debf | sovereign2013 | **0.2x** ← neu | REMOVE | 3 |

---

## ❌ Entfernt / Inaktiv

| Wallet | Alias | Grund |
|--------|-------|-------|
| 0x7a61...af24 | Gambler1968 | REMOVE — nicht in TARGET_WALLETS |
| 0xdb27...c56e | DrPufferfish | REVIEW — nicht in TARGET_WALLETS |

---

## Änderungshistorie

| Datum | Wallet | Änderung | Grund |
|-------|--------|----------|-------|
| 21.04.2026 | 0x2005...75ea (RN1) | 0.30 → 0.3 (gleich, aber als Absicht markiert) | 38% WR, -$193 PnL über 81 Trades |
| 21.04.2026 | 0xee61...debf (sovereign2013) | neu: 0.2x | 33% WR, -$23, nur 3 Trades, REMOVE-Entscheid vom 19.04. |
| 19.04.2026 | wan123 | 2.5x → 0.5x | negative ROI bestätigt |
| 19.04.2026 | denizz | 0.5x → 1.0x | Post-Bug-Fix Rekalibrierung |

---

_Bot-Neustart erforderlich damit ENV-Weight-Änderungen aktiv werden._
_Noch nicht deployed — warte auf Freigabe._
