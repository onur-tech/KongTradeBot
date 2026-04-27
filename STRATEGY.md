# KongTrade Bot — Strategy

## Live-Switch Hard Rules (Single Source of Truth, 27.04.2026)

**Pre-Live MUSS-Bedingungen** (alle 8 erfüllt sein vor T-D105):
- [x] V2-SDK aktiv (`USE_V2_SDK=true`)
- [x] pUSD-Wrap verifiziert (balance reads + allowance + USDC↔pUSD swap path)
- [x] Maker-Only aktiv (~150 bps savings/Trade)
- [x] Skip-Gates aktiv (10–15% schlechte Trades blockiert)
- [x] Sport_US Hard-Blacklist
- [x] Edge-Verifikation grün (PSR(0)>0.95, Sharpe>3, n>100)
- [x] Wallet-Audit reviewed
- [x] Dashboard funktional, Console clean (P059-Hotfix 27.04.)

**Initial-Setup** (Phase D1 — 28.04.2026 15:00 Berlin):
```
Bankroll                 = $80          (20% von Echtkapital $400)
COPY_SIZE_MULTIPLIER     = 0.02
MAX_TRADE_USD            = 8
MAX_POSITIONS_TOTAL      = 5
WHITELIST_CATEGORIES     = Weather*
BLACKLIST_CATEGORIES     = Sport_US, NBA, NFL, MLB, NHL, Crypto, Memes,
                           Politik, Tennis, Soccer
```

**Hard-Stops:**
- $50 / Tag (intraday-loss) → Bot-Stop, Telegram-Alert, Brrudi-Decision
- $120 / Woche → Bot-Stop + Live-Switch-Review (mandatory PnL-Review-Meeting)
- 3 consecutive losses → Pause 60 Min, Re-Audit der letzten 3 Signale

**Scale-Roadmap** (sequentiell, jeder Schritt erfordert vorigen erfüllt):
- 7 Tage stabil + PnL ≥ 0  → Scale auf $200
- 30 Tage stabil + PnL > 0 → Scale auf $660
- $660 stabil 30 Tage      → Cap $5k erlaubt

## Aktuelle Config
Stand: 26.04.2026

```
MAX_PORTFOLIO_PCT     = 0.70   (war 0.50 — erhöht nach vollständiger Kalibrierung)
COPY_SIZE_MULTIPLIER  = 0.15   (bestätigt — bewusst beibehalten)
```

Begründung:
- MAX_PORTFOLIO_PCT 0.50 → 0.70: Nach Kalibrierung und 2 Wochen Live-Betrieb.
  Budget $683 USDC × 70% = $478 max investierbar.
  Aktuell invested $404 → $74 freier Spielraum für neue Trades.
- COPY_SIZE_MULTIPLIER 0.15: Balanciert Rendite vs. Risiko nach $137 Verlust-Erfahrung.
  Entspricht ~$30 Trade-Größe bei $200 Signal.

## Mode-Resolver (Shadow-Mode, ab Restart 26.04.2026)
Ersetzt die alte CATEGORY_BLACKLIST-Substring-Logik durch Drei-Stufen-Routing.
Priorität: SKIP > SHADOW > PAPER (first match wins).

```
SKIP_PREFIXES       = col1-,por-,ecu-,arg-b-      # echter Spam, kein Tracking
SHADOW_CATEGORIES   = Sport_US,Tennis,Soccer       # paper-record, kein Capital
SHADOW_NEW_WALLETS  = true                         # neue Wallets <30 Samples → SHADOW
SHADOW_MIN_SAMPLE   = 30
# alles andere → PAPER (existing dry-run path)
```

## Edge-Erkenntnis (Iter2 Resolution-Match, 26.04.2026)
Bot's Edge ist **Momentum-Capture**, nicht Prediction:

| Kategorie | n   | Pred-Rate | Realized | If Hold | Alpha   |
|-----------|-----|-----------|----------|---------|---------|
| Weather   | 198 | 22.7%     | +$2632   | -$3266  | +$5898  |
| Geopolitik| 32  | 3.1%      | +$103    | -$506   | +$609   |
| Sport_US  | 65  | 33.9%     | -$414    | -$311   | -$103   |
| Tennis    | 33  | 63.6%     | +$48     | +$22    | +$26    |
| Soccer    | 18  | 66.7%     | +$114    | +$115   | -$1     |

Implikation: TP-Exits sind das Profitcenter. Weather/Geopolitik haben extrem
schlechte Prediction-Rate aber massive Alpha — die Exit-Logic fängt
Preisbewegungen ab, lange bevor Resolution. Sport_US versagt auf BEIDEN
Achsen und ist deshalb in SHADOW_CATEGORIES.
