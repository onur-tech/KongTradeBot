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

## Wie der Edge funktioniert (8-Schritte, 27.04.2026)

Klarstellung **bevor** der Live-Switch greift: der Edge entsteht aus dem
**eigenen Weather-Scout-Modell**, nicht aus dem Whale-Copy-Pfad. Das
Whale-Copy-Modul ist eine Markt-Auswahl-Heuristik, kein Edge-Generator
— der T-D108.5-Audit hat das bestätigt (Bucket B Whale-Copy-on-Weather:
**0 Trades**, alle 77 Weather-Trades stammen aus dem Scout).

Die acht Schritte des Weather-Scout-Edges:

1. **Modell-Vorhersage** via ECMWF/GFS/MET-Norway/Pirate-Weather Ensemble
   (Open-Meteo API, `core/weather_scout.py::get_ensemble_forecast`).
2. **Bias-Korrektur pro Wetter-Station** — monatliche Korrekturwerte aus
   der `data/polymarket_stations.json` Konfiguration.
3. **Sigma-Kalibrierung** empirisch aus 77 Tagen historischer
   Forecast-vs-Realisation (`_STATIONS` overrides).
4. **Bucket-Wahrscheinlichkeit** — Normalverteilung μ=forecast, σ=kalibriert,
   integriert über Bucket-Grenzen (`bucket_prob` Funktion).
5. **Edge-Vergleich** — `model_p − market_price`, gefiltert auf
   `WEATHER_MIN_EDGE` (default 0.15, env-override möglich).
6. **Tier-Architektur** (`core/weather_tiers.py`): Tier 1/2/3 Schwellen
   nach Stadt-Vertrauen — Tier-1-Städte handeln aggressiver.
7. **Quarter-Kelly Sizing + Caps** — Position-Size nach Kelly/4 mit
   `MAX_TRADE_USD` Hard-Cap.
8. **TP-Logic** — 40/40/15/5-Staffel (TP1 entry+10%, TP2 +25%, TP3 +50%,
   Whale-Exit als Backup). Erklärt warum Bot-Edge "Momentum-Capture"
   statt "Prediction" ist: wir steigen oft VOR Resolution aus.

**Whale-Copy-Pfad** (`strategies/copy_trading_plugin`) liefert
Whale-Signale aus 25 überwachten Wallets. Diese Signale sind das
Markt-Discovery-Tool — sie zeigen WAS der Markt für interessant hält.
Aber im Live-Switch (T-D104) ist der Whale-Copy-Pfad durch die
Whitelist Option Y faktisch deaktiviert (siehe T-D107 + T-D108.5):
keine Whale tradet Weather, also keine Live-Trades aus diesem Pfad.

## Strategie-Komponenten (T-D108.5 Audit, dauerhaft)

77 deduplicateten Lifetime Weather-Trades (post-T-D107.5 dedup):

| Komponente | Trades | PnL | Mean | Note |
|------------|--------|-----|------|------|
| Weather-Scout direkt | 8 | +$609,06 | +$76,13 | aktuelles Logging post-22.04. |
| Multi-Tranche Exits | 69 | +$2.293,80 | +$33,24 | pre-22.04. Logging-Phase |
| Whale-Copy on Weather | **0** | — | — | **Bucket leer** |
| Edge-Case (1 Loss) | 1 | -$1,17 | — | prediction_loss |
| **Total Weather** | **77** | **+$2.888,30** | **+$37,51** | **100% own edge** |

Quersumme: $609 + $2.294 − $1 = $2.902 ≈ deduped $2.888 (Diff $14 = 1 row mit NULL category).

## Realistic Scaling Pfad (Brrudi-genehmigt 27.04.)

| Tag | Bankroll | Hard-Stop | Bedingung |
|-----|----------|-----------|-----------|
| Mo 28.04. | $200 | $40 | Live-Switch initial · T-D104 |
| Di 29.04. | $500 | $100 | Tag 1 sauber, ≥1 Trade gefilled |
| Mi 30.04. | $1.000 | $200 | Tag 2 PnL ≥ -$50 |
| Fr 02.05. | $2.500 | $500 | 3 Tage stabil, Slippage gemessen |
| Mo 05.05. | $5.000 | $1.000 | Real-Sharpe-Schätzung verfügbar |

**Limits & Erwartung:**
- Realistischer Cap: **$20.000–$50.000** (Liquiditäts-getrieben — Polymarket
  Weather-Märkte haben begrenzte Volume-Tiefe pro Bucket).
- Monthly-Estimate bei $5.000 Bankroll, **Real-Sharpe 5**: ~$2.500/Mo
- Monthly-Estimate bei $5.000 Bankroll, **Real-Sharpe 7**: ~$3.500/Mo
- Bei **Real-Sharpe < 3** (Slippage-Schock im Live-Trading): Skalierung
  pausieren, Strategie-Review.

Die Naive-Sharpe der trades.db ist nach T-D107.5 Dedup ~10.51 (Weather-only,
deduped). Im Live-Trading mit echter Slippage + Maker-Fees + on-chain
Confirmation-Latenzen erwarten wir 30–50% Sharpe-Reduktion — also
Real-Sharpe 5–7. Das ist die Basis der Monthly-Estimates oben.

## Trade Classification

Der `edge_type`-Spaltenwert in `trades.db` klassifiziert Trades nach
Exit-Mechanik. Live-Verifikation via `/api/v2/eval/edge-type-distribution`.

| edge_type | Bedeutung | Resolution-Bezug |
|-----------|-----------|------------------|
| `momentum_tp` | TP-Stage-Exit (TP1/TP2/TP3) | unabhängig — exit pre-resolution |
| `momentum_whale` | Whale-Exit als Backup-Trigger | unabhängig — kopiert Whale-Exit |
| `prediction_win` | Position bis Resolution gehalten, korrekt | Resolution für uns |
| `prediction_loss` | Position bis Resolution gehalten, falsch | Resolution gegen uns |
| `still_open` | Position noch nicht resolved | (kein PnL) |
| `momentum_other` | Legacy/Sonstige Exit-Pfade | |

**Glossary** für Glitch-Library / Tooltips (T-211 in TASKS.md):
- **PnL**: Realized Profit / Loss in USD
- **VaR**: Value at Risk — verlierbarer Tagesbetrag mit 95% Konfidenz
- **CVaR**: Conditional VaR — Mean-Loss in den 5% schlimmsten Tagen
- **DD**: Drawdown — peak-to-trough Verlust in Prozent
- **Sharpe**: (mean − risk_free) / std × √252 — annualisiert
- **Wilson**: Wilson-Score-Konfidenzintervall für Win-Rate
- **PSR**: Probabilistic Sharpe Ratio — Wahrscheinlichkeit, dass true Sharpe ≥ Schwelle
- **Kelly**: Optimal-Bet-Size = (p × b − q) / b — wir nutzen Quarter-Kelly
- **Cohort**: Trade-Gruppe nach Kategorie / Zeit / Wallet
- **Counterfactual**: Was wäre passiert wenn man HOLD bis Resolution gemacht hätte
- **edge_type**: siehe Tabelle oben

