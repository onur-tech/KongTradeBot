# Weather Trades — Live Tracking

> Stand: 2026-04-27 19:52 UTC | Bot DRY-RUN seit 17.04.2026
> Quelle: `trades.db` deduped via T-D107.5 dedup-Heuristik (market_id + datetime(exit_ts) + realized_pnl_usd)
> Filter: `category='Weather'` OR market matches temperature/snow/rain/°C/°F

## Summary

| Metric | Wert |
|---|---|
| Total Trades | 77 |
| Wins | 72 |
| Losses | 5 |
| Zeros | 0 |
| Win-Rate | 93.5% |
| Net PnL | +2.888.30 |
| Mean/Trade | +37.51 |
| Median | +14.97 |
| Best | +281.71 |
| Worst | -2.65 |
| StDev | 56.66 |
| Sharpe (annualisiert, naive) | 10.51 |

## Komplette Liste

| # | Entry | Exit | Markt | Side | E-Px | X-Px | Size | PnL | Reason | Edge |
|---|-------|------|-------|------|------|------|------|-----|--------|------|
| 1 | 21.04 14:17 | 21.04 14:17 | (no signal-link) | SELL | 0.500 | 0.500 | $11.64 | +10.47 | TP1 | momentum_tp |
| 2 | 21.04 14:17 | 21.04 14:17 | (no signal-link) | SELL | 0.500 | 0.500 | $8.63 | +8.17 | TP1 | momentum_tp |
| 3 | 21.04 14:18 | 21.04 14:18 | (no signal-link) | SELL | 0.500 | 0.500 | $6.98 | +5.82 | TP2 | momentum_tp |
| 4 | 21.04 14:18 | 21.04 14:18 | (no signal-link) | SELL | 0.500 | 0.500 | $5.18 | +4.71 | TP2 | momentum_tp |
| 5 | 21.04 18:29 | 21.04 18:29 | (no signal-link) | SELL | 0.500 | 0.500 | $11.27 | +7.66 | TP1 | momentum_tp |
| 6 | 21.04 18:31 | 21.04 18:31 | (no signal-link) | SELL | 0.500 | 0.500 | $6.76 | +3.16 | TP2 | momentum_tp |
| 7 | 21.04 20:59 | 21.04 20:59 | (no signal-link) | SELL | 0.500 | 0.500 | $92.74 | +92.18 | TP1 | momentum_tp |
| 8 | 21.04 21:01 | 21.04 21:01 | (no signal-link) | SELL | 0.500 | 0.500 | $55.64 | +55.09 | TP2 | momentum_tp |
| 9 | 21.04 21:02 | 21.04 21:02 | (no signal-link) | SELL | 0.500 | 0.500 | $12.52 | +12.31 | TP3 | momentum_tp |
| 10 | 21.04 23:16 | 21.04 23:16 | (no signal-link) | SELL | 0.500 | 0.500 | $31.73 | +30.73 | TP1 | momentum_tp |
| 11 | 21.04 23:17 | 21.04 23:17 | (no signal-link) | SELL | 0.500 | 0.500 | $19.04 | +18.04 | TP2 | momentum_tp |
| 12 | 21.04 23:47 | 21.04 23:47 | (no signal-link) | SELL | 0.500 | 0.500 | $31.73 | +30.73 | TP1 | momentum_tp |
| 13 | 21.04 23:48 | 21.04 23:48 | (no signal-link) | SELL | 0.500 | 0.500 | $19.04 | +18.04 | TP2 | momentum_tp |
| 14 | 22.04 14:10 | 22.04 14:10 | Will the highest temperature in Paris be 19°C on A… | BUY | 0.110 | 0.485 | $10.00 | +14.18 | TP1 | momentum_tp |
| 15 | 22.04 00:17 | 22.04 00:17 | (no signal-link) | SELL | 0.500 | 0.500 | $31.73 | +30.73 | TP1 | momentum_tp |
| 16 | 22.04 00:17 | 22.04 00:17 | (no signal-link) | SELL | 0.500 | 0.500 | $7.93 | +7.23 | TP1 | momentum_tp |
| 17 | 22.04 00:18 | 22.04 00:18 | (no signal-link) | SELL | 0.500 | 0.500 | $19.04 | +18.04 | TP2 | momentum_tp |
| 18 | 22.04 00:25 | 22.04 00:25 | (no signal-link) | SELL | 0.999 | 0.999 | $141.75 | +140.36 | PRICE_TRIGGER | momentum_tp |
| 19 | 22.04 00:47 | 22.04 00:47 | (no signal-link) | SELL | 0.500 | 0.500 | $31.73 | +30.73 | TP1 | momentum_tp |
| 20 | 22.04 00:47 | 22.04 00:47 | (no signal-link) | SELL | 0.500 | 0.500 | $20.57 | +20.08 | TP1 | momentum_tp |
| 21 | 22.04 00:47 | 22.04 00:47 | (no signal-link) | SELL | 0.500 | 0.500 | $7.93 | +7.23 | TP1 | momentum_tp |
| 22 | 22.04 00:48 | 22.04 00:48 | (no signal-link) | SELL | 0.500 | 0.500 | $19.04 | +18.04 | TP2 | momentum_tp |
| 23 | 22.04 05:50 | 22.04 05:50 | (no signal-link) | SELL | 0.500 | 0.500 | $12.34 | +11.85 | TP2 | momentum_tp |
| 24 | 22.04 05:50 | 22.04 05:50 | (no signal-link) | SELL | 0.500 | 0.500 | $7.93 | +7.23 | TP1 | momentum_tp |
| 25 | 22.04 05:52 | 22.04 05:52 | (no signal-link) | SELL | 0.500 | 0.500 | $50.00 | +46.00 | TP1 | momentum_tp |
| 26 | 22.04 05:53 | 22.04 05:53 | (no signal-link) | SELL | 0.500 | 0.500 | $30.00 | +26.00 | TP2 | momentum_tp |
| 27 | 22.04 05:54 | 22.04 05:54 | (no signal-link) | SELL | 0.500 | 0.500 | $6.75 | +5.25 | TP3 | momentum_tp |
| 28 | 22.04 06:47 | 22.04 06:47 | (no signal-link) | SELL | 0.500 | 0.500 | $181.82 | +177.82 | TP1 | momentum_tp |
| 29 | 22.04 06:50 | 22.04 06:50 | (no signal-link) | SELL | 0.500 | 0.500 | $109.09 | +105.09 | TP2 | momentum_tp |
| 30 | 22.04 06:57 | 22.04 06:57 | (no signal-link) | SELL | 0.500 | 0.500 | $24.55 | +23.05 | TP3 | momentum_tp |
| 31 | 22.04 06:57 | 22.04 06:57 | (no signal-link) | SELL | 0.500 | 0.500 | $28.57 | +24.57 | TP1 | momentum_tp |
| 32 | 22.04 06:59 | 22.04 06:59 | (no signal-link) | SELL | 0.500 | 0.500 | $17.14 | +13.14 | TP2 | momentum_tp |
| 33 | 22.04 07:09 | 22.04 07:09 | (no signal-link) | SELL | 0.500 | 0.500 | $51.28 | +47.28 | TP1 | momentum_tp |
| 34 | 22.04 07:10 | 22.04 07:10 | (no signal-link) | SELL | 0.500 | 0.500 | $30.77 | +26.77 | TP2 | momentum_tp |
| 35 | 22.04 07:12 | 22.04 07:12 | (no signal-link) | SELL | 0.500 | 0.500 | $6.92 | +5.42 | TP3 | momentum_tp |
| 36 | 22.04 07:25 | 22.04 07:25 | (no signal-link) | SELL | 0.500 | 0.500 | $15.38 | +11.38 | TP1 | momentum_tp |
| 37 | 22.04 07:26 | 22.04 07:26 | (no signal-link) | SELL | 0.500 | 0.500 | $68.97 | +64.97 | TP1 | momentum_tp |
| 38 | 22.04 07:26 | 22.04 07:26 | (no signal-link) | SELL | 0.500 | 0.500 | $9.23 | +5.23 | TP2 | momentum_tp |
| 39 | 22.04 07:27 | 22.04 07:27 | (no signal-link) | SELL | 0.500 | 0.500 | $41.38 | +37.38 | TP2 | momentum_tp |
| 40 | 22.04 07:30 | 22.04 07:30 | (no signal-link) | SELL | 0.500 | 0.500 | $9.31 | +7.81 | TP3 | momentum_tp |
| 41 | 22.04 07:40 | 22.04 07:40 | (no signal-link) | SELL | 0.500 | 0.500 | $15.38 | +11.38 | TP1 | momentum_tp |
| 42 | 22.04 07:41 | 22.04 07:41 | (no signal-link) | SELL | 0.500 | 0.500 | $9.23 | +5.23 | TP2 | momentum_tp |
| 43 | 22.04 08:02 | 22.04 08:02 | (no signal-link) | SELL | 0.500 | 0.500 | $16.67 | +12.67 | TP1 | momentum_tp |
| 44 | 22.04 08:04 | 22.04 08:04 | (no signal-link) | SELL | 0.500 | 0.500 | $10.00 | +6.00 | TP2 | momentum_tp |
| 45 | 22.04 08:30 | 22.04 08:30 | (no signal-link) | SELL | 0.500 | 0.500 | $285.71 | +281.71 | TP1 | momentum_tp |
| 46 | 22.04 08:32 | 22.04 08:32 | (no signal-link) | SELL | 0.500 | 0.500 | $171.43 | +167.43 | TP2 | momentum_tp |
| 47 | 22.04 08:35 | 22.04 08:35 | (no signal-link) | SELL | 0.500 | 0.500 | $38.57 | +37.07 | TP3 | momentum_tp |
| 48 | 22.04 09:55 | 22.04 09:55 | (no signal-link) | SELL | 0.500 | 0.500 | $7.13 | -2.42 | WHALE_EXIT | momentum_whale |
| 49 | 22.04 12:07 | 22.04 12:07 | (no signal-link) | SELL | 0.500 | 0.500 | $8.16 | -1.63 | WHALE_EXIT | momentum_whale |
| 50 | 22.04 14:11 | 22.04 14:11 | (no signal-link) | SELL | 0.500 | 0.500 | $10.91 | +6.91 | TP2 | momentum_tp |
| 51 | 22.04 23:11 | 22.04 23:11 | (no signal-link) | SELL | 0.999 | 0.999 | $24.98 | +14.97 | PRICE_TRIGGER | momentum_tp |
| 52 | 23.04 10:46 | 23.04 10:46 | Will the highest temperature in Warsaw be 13°C on … | BUY | 0.031 | 0.485 | $10.00 | +60.52 | TP1 | momentum_tp |
| 53 | 23.04 14:48 | 23.04 14:49 | Will the highest temperature in Hong Kong be 22°C … | BUY | 0.130 | 0.485 | $10.00 | +11.38 | TP1 | momentum_tp |
| 54 | 23.04 10:47 | 23.04 10:47 | (no signal-link) | SELL | 0.500 | 0.500 | $38.71 | +34.71 | TP2 | momentum_tp |
| 55 | 23.04 10:48 | 23.04 10:48 | (no signal-link) | SELL | 0.500 | 0.500 | $8.71 | +7.21 | TP3 | momentum_tp |
| 56 | 23.04 14:07 | 23.04 14:07 | (no signal-link) | SELL | 0.500 | 0.500 | $17.86 | +7.86 | WHALE_EXIT | momentum_whale |
| 57 | 23.04 14:50 | 23.04 14:50 | (no signal-link) | SELL | 0.500 | 0.500 | $9.23 | +5.23 | TP2 | momentum_tp |
| 58 | 23.04 17:18 | 23.04 17:18 | (no signal-link) | SELL | 0.500 | 0.500 | $7.35 | -2.65 | WHALE_EXIT | momentum_whale |
| 59 | 23.04 21:29 | 23.04 21:29 | (no signal-link) | SELL | 0.500 | 0.500 | $9.26 | -0.74 | WHALE_EXIT | momentum_whale |
| 60 | 24.04 06:08 | 24.04 06:09 | Will the highest temperature in Tokyo be 19°C on A… | BUY | 0.036 | 0.485 | $10.00 | +51.56 | TP1 | momentum_tp |
| 61 | 24.04 06:10 | 24.04 06:10 | (no signal-link) | SELL | 0.500 | 0.500 | $33.33 | +29.33 | TP2 | momentum_tp |
| 62 | 24.04 06:11 | 24.04 06:11 | (no signal-link) | SELL | 0.500 | 0.500 | $7.50 | +6.00 | TP3 | momentum_tp |
| 63 | 25.04 01:06 | 25.04 01:06 | Will the highest temperature in Seattle be between… | BUY | 0.017 | 0.485 | $10.00 | +113.65 | TP1 | momentum_tp |
| 64 | 25.04 01:07 | 25.04 01:07 | (no signal-link) | SELL | 0.500 | 0.500 | $70.59 | +66.59 | TP2 | momentum_tp |
| 65 | 25.04 01:08 | 25.04 01:08 | (no signal-link) | SELL | 0.500 | 0.500 | $15.88 | +14.38 | TP3 | momentum_tp |
| 66 | 25.04 02:21 | 25.04 02:21 | (no signal-link) | SELL | 0.999 | 0.999 | $179.82 | +169.82 | PRICE_TRIGGER | momentum_tp |
| 67 | 25.04 05:37 | 25.04 05:37 | (no signal-link) | SELL | 0.999 | 0.999 | $36.33 | +32.33 | TP1 | momentum_tp |
| 68 | 25.04 05:43 | 25.04 05:43 | (no signal-link) | SELL | 0.999 | 0.999 | $21.80 | +17.80 | TP2 | momentum_tp |
| 69 | 25.04 07:38 | 25.04 07:38 | (no signal-link) | SELL | 0.500 | 0.500 | $12.50 | +8.50 | TP1 | momentum_tp |
| 70 | 25.04 07:45 | 25.04 07:45 | (no signal-link) | SELL | 0.500 | 0.500 | $7.50 | +3.50 | TP2 | momentum_tp |
| 71 | 25.04 12:41 | 25.04 12:41 | (no signal-link) | SELL | 0.500 | 0.500 | $7.41 | +3.41 | TP1 | momentum_tp |
| 72 | 26.04 07:11 | 26.04 07:12 | Will the highest temperature in Taipei be 30°C on … | BUY | 0.030 | 0.485 | $10.00 | +62.67 | TP1 | momentum_tp |
| 73 | 26.04 07:13 | 26.04 07:13 | (no signal-link) | SELL | 0.500 | 0.500 | $40.00 | +36.00 | TP2 | momentum_tp |
| 74 | 26.04 07:14 | 26.04 07:14 | (no signal-link) | SELL | 0.500 | 0.500 | $9.00 | +7.50 | TP3 | momentum_tp |
| 75 | 26.04 08:47 | 26.04 08:47 | (no signal-link) | SELL | 0.999 | 0.999 | $101.90 | +91.90 | PRICE_TRIGGER | momentum_tp |
| 76 | 26.04 17:44 | 22.04 12:00 | (no signal-link) | BUY | 0.027 | 0.000 | $1.17 | -1.17 | RESOLUTION | prediction_loss |
| 77 | 27.04 09:04 | 27.04 09:05 | Will the highest temperature in London be 13°C on … | BUY | 0.007 | 0.485 | $10.00 | +281.71 | TP1 | unknown |

## Lehren

### Der/die Loss(es)

- **22.04 09:55** · (no signal-link)
  - Side SELL, Entry 0.500 → Exit 0.500, Size $7.13
  - **PnL: -2.42**
  - Exit-Reason: `WHALE_EXIT` · Edge-Type: `momentum_whale`
  - Counterfactual HOLD-PnL: +7.13

- **22.04 12:07** · (no signal-link)
  - Side SELL, Entry 0.500 → Exit 0.500, Size $8.16
  - **PnL: -1.63**
  - Exit-Reason: `WHALE_EXIT` · Edge-Type: `momentum_whale`
  - Counterfactual HOLD-PnL: -8.16

- **23.04 17:18** · (no signal-link)
  - Side SELL, Entry 0.500 → Exit 0.500, Size $7.35
  - **PnL: -2.65**
  - Exit-Reason: `WHALE_EXIT` · Edge-Type: `momentum_whale`
  - Counterfactual HOLD-PnL: -7.35

- **23.04 21:29** · (no signal-link)
  - Side SELL, Entry 0.500 → Exit 0.500, Size $9.26
  - **PnL: -0.74**
  - Exit-Reason: `WHALE_EXIT` · Edge-Type: `momentum_whale`
  - Counterfactual HOLD-PnL: +9.26

- **26.04 17:44** · (no signal-link)
  - Side BUY, Entry 0.027 → Exit 0.000, Size $1.17
  - **PnL: -1.17**
  - Exit-Reason: `RESOLUTION` · Edge-Type: `prediction_loss`
  - Counterfactual HOLD-PnL: -1.17

### Top 5 Wins — Pattern

| # | Stadt | Entry-Date | Side | Entry-Px | Exit-Px | PnL | Edge |
|---|-------|------------|------|----------|---------|-----|------|
| 1 | (no signal-link) | 22.04 08:30 | SELL | 0.500 | 0.500 | +281.71 | momentum_tp |
| 2 | London | 27.04 09:04 | BUY | 0.007 | 0.485 | +281.71 | unknown |
| 3 | (no signal-link) | 22.04 06:47 | SELL | 0.500 | 0.500 | +177.82 | momentum_tp |
| 4 | (no signal-link) | 25.04 02:21 | SELL | 0.999 | 0.999 | +169.82 | momentum_tp |
| 5 | (no signal-link) | 22.04 08:32 | SELL | 0.500 | 0.500 | +167.43 | momentum_tp |

### Bottom 3 (least profitable, may include 0 or losses)

| # | Stadt | Entry-Date | Side | Entry-Px | Exit-Px | PnL | Edge |
|---|-------|------------|------|----------|---------|-----|------|
| 1 | (no signal-link) | 22.04 12:07 | SELL | 0.500 | 0.500 | -1.63 | momentum_whale |
| 2 | (no signal-link) | 22.04 09:55 | SELL | 0.500 | 0.500 | -2.42 | momentum_whale |
| 3 | (no signal-link) | 23.04 17:18 | SELL | 0.500 | 0.500 | -2.65 | momentum_whale |

## Methodik-Note

- **Dedup**: ein Trade = (market_id × datetime(exit_ts) × realized_pnl_usd). Doppelt-INSERT-Bug aus `migrate_from_archive` (T-D107.5) entfernt 6 Profit-Spiegel-Rows aus dem Weather-Set.
- **Sharpe naive**: pro-Trade `mean/std × √252`. Korrekt wäre per-Trading-Day Aggregation; das Resultat hier ist obere Schranke.
- **Counterfactual-PnL** (`counterfactual_pnl_hold`): was hätte ein passive HOLD bis Resolution gebracht. Zeigt: Edge ist Momentum-Capture, nicht Prediction.
- **Live-Switch-Relevanz**: Diese 77 Trades sind die Empirie hinter T-D104. Whitelist Option Y (deployed T-D107) erlaubt morgen NUR diese Kategorie.