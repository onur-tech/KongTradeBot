# KongTradeBot — Backtest & Performance-Tracking
_Stand: 18.04.2026_

## Backtester-Prognose (17.04.2026)

Basis: 3.899 aufgelöste DRY-RUN-Trades über ~2 Tage.

Bei 1000 USD Budget:
- Konservativ: +738 USD/Monat (+73.8% ROI)
- Erwartet: +1229 USD/Monat (+122.9% ROI)
- Optimistisch: +1844 USD/Monat (+184.4% ROI)

Disclaimer: DRY-RUN ohne Slippage, Fill-Fehler, Gas. 
Live-Realität wird niedriger liegen.

## DRY-RUN Baseline (17.04.2026, 10h)

- Trades: ~6416 gesamt (3899 aufgelöst, 2123 offen)
- Win Rate: 61.8%
- P&L: +1097 USD (hypothetisch)

## Live-Performance-Tracking

### 17.04.2026 (Erster Live-Tag)
- Start: 988 USDC.e (nach Proxy-Deploy)
- Ende: ~851 (nach 137 USD Verlust bei illiquiden Märkten)
- Lesson: Defensive Config → Multiplier 0.15 → 0.05

### 18.04.2026
- Start: 629 USDC.e
- Ende: TBD

## Tracking-Metriken (wöchentlich füllen)

| KW | Start | Ende | P&L USD | P&L % | Trades | WR | Best | Worst |
|---|---|---|---|---|---|---|---|---|
| 16/26 | 988 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

## Gegenüberstellung Prognose vs Realität

Nach 2 Wochen Live-Daten:

| Szenario | Prognose/Monat | Realität/Monat | Delta |
|---|---|---|---|
| Konservativ | +738 | TBD | — |
| Erwartet | +1229 | TBD | — |
| Optimistisch | +1844 | TBD | — |

## Hypothesen zu prüfen

1. Slippage: wie viel Prozent Gewinn verschluckt Live-Fill?
2. Wallet-Performance bei Regime-Wechseln (Wochenende, News)
3. wan123-Paradox: bestätigt sich 90% WR + -71% ROI Live?
4. Defensive-Config Trade-Off: weniger Verlust aber auch weniger Upside?

## TODO

- Wöchentliches Snapshot-Script (Freitag) für Tracking-Tabelle
- Per-Wallet-ROI live tracken (T-017)
- Slippage-Metrik: Fill-Preis vs Signal-Preis pro Trade
- Monatliches Prognose-vs-Realität-Review

Ende BACKTEST_RESULTS.md.
