# KongTradeBot — Wallet-Portfolio
_Stand: 18.04.2026_

## Aktive Target-Wallets (11)

Vollständige Adressen in .env TARGET_WALLETS. 
Multiplier in WALLET_WEIGHTS (env-Override).

| # | Adresse (kurz) | Alias | Multiplier | Performance | Quelle |
|---|---|---|---|---|---|
| 1 | 0x7a6192...af24 | Gambler1968 | 1.0x | TBD | wallet_init.py |
| 2 | 0x7177a7...dDEf | kcnyekchno | 1.0x | TBD | wallet_init.py |
| 3 | 0x0B7A60...86cf | HOOK | 1.0x | TBD | wallet_init.py |
| 4 | 0xee613b...debf | denizz | 0.5x | Geopolitik | Original-Doku |
| 5 | 0xbaa2bc...2c73 | denizz | 0.5x | Geopolitik | wallet_init.py |
| 6 | 0xde7be6...5f4b | sovereign2013 | 0.3x | 45-49% WR | Decay-Kategorie |
| 7 | 0x019782...9f3c | majorexploiter | 3.0x | 76% WR, Mio-Profit | Polymonit |
| 8 | 0x492442...3782 | April#1 Sports | 2.0x | 65% WR, Sport | Predicts.guru |
| 9 | 0x02227b...8ff7 | HorizonSplendidView | 2.0x | Sport | Predicts.guru |
| 10 | 0xefbc5f...f9a2 | wan123 | 2.5x | 90% WR ABER -71% ROI | Beobachten |
| 11 | 0x2005d1...75ea | RN1 | 0.2x | Klein | wallet_init.py |

## Wallet-Kategorien

### High-Conviction (3.0x)
- **majorexploiter** — 76% WR, Millionen-Profit
- Historisch: DrPufferfish (92% WR), Countryside (96% WR) — nicht aktiv

### Strong (2.0-2.5x)
- April#1 Sports, HorizonSplendidView — Sport-Profis
- wan123 (2.5x) — PARADOX: 90% WR, aber -71% ROI
  Action: Multiplier runter auf 0.5x wenn Live-Daten bestätigen

### Standard (1.0x)
- Mehrere Adressen ohne Alias, Performance TBD

### Low-Conviction (0.3-0.5x)
- denizz (0.5x) — Geopolitik, wenig Historie
- sovereign2013 (0.3x) — Decay-Zone

## Review-Historie

| Datum | Änderung | Grund |
|---|---|---|
| 17.04.2026 | wan123 auf "beobachten" | 90% WR aber -71% ROI |
| 18.04.2026 | Defensive Config: effektiv x0.05 statt x0.15 | 137 USD Verlust |

## Review-Kadenzen

- Täglich 09:00 — WalletScout automatisch
- Freitag — wallet_check.py Decay-Report (offen als Task)
- Monatlich — Manuelle Review

## Quellen für neue Kandidaten

- https://polymonit.com/leaderboard
- https://oddsshift.com/smart-money
- https://predicts.guru
- https://www.frenflow.com/traders

## Regel für neue Wallets

1. Mindestens 3 Monate Historie, >60% WR, positive ROI
2. Initial-Multiplier: 1.0x
3. Nach 2 Wochen live: Multiplier justieren
4. <45% WR über 1 Woche → raus

## Offene Punkte

- Performance für #1, #2, #3 nachtragen (Gambler1968, kcnyekchno, HOOK)
- wan123-Entscheidung treffen (0.5x wenn Live-Daten -71% ROI bestätigen)
- Per-Wallet-P&L-Tracking implementieren (T-017)

## Daten-Diskrepanz

HINWEIS: wallet_init.py mappt 0xee613b auf sovereign2013 —
wurde hier auf denizz gesetzt basierend auf Original-Doku.
Zu verifizieren via Polymarket-UI Wallet-Lookup wenn Brrudi mal Zeit hat.

Ende WALLETS.md.
