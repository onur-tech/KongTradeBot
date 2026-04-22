# KongBot — Handover für neuen Chat
_Stand: 2026-04-22 (Nacht)_

## SOFORT WICHTIG
- Bot ist jetzt auf DRY-RUN / Paper-Modus
- Echter Wallet-Stand: ~$683 von $1.000
- Echter Verlust: -$317 (-31.7%)
- Bot-interner PnL +$278 ist IRREFÜHREND

## WARUM AUF PAPER UMGESTELLT
- Iran Peace Deal YES: großer Verlust
- should_trade() Gate lief auf Fallback (inaktiv)
- Weather-Stationen laden nicht (kein Cache)
- Zu früh für echtes Geld — System nicht kalibriert

## SYSTEM-STATUS
- Server: Hetzner Helsinki 89.167.29.183
- Dashboard: kong-trade.com
- Bot: /root/KongTradeBot/ (systemd)
- DRY_RUN=true ← NEU
- WEATHER_DRY_RUN=true ← NEU

## WAS GEBAUT WURDE (diese Woche)
- Tier-Architektur (Tier 1/2/3)
- Quarter-Kelly YES/NO
- Multi-Model Ensemble Gate
- Seoul Seasonal Bias
- HRRR via Herbie
- Kalshi Scraper
- Shadow Portfolio v2 (10x/5x Mirror)
- Performance Tracking (deposits.json)
- KongBot Terminal Dashboard
- News Tab (RSS BBC/AP/NYT)
- 14/14 Tests grün

## OFFENE BUGS (kritisch)
1. should_trade() → Fallback-Stub aktiv (Gate filtert nichts)
2. Weather-Stationen "kein Cache" → API-Endpoint Problem
3. Wallet Performance Tab lädt nicht
4. Sell/Claim Buttons fehlen im neuen Dashboard
5. Logo immer noch zu klein
6. Auto-Claim Resolver zeigt ERR

## VERLUST-ANALYSE (147 aufgelöste Trades)
Win Rate: 59.9% | Gesamt P&L intern: +$660.04

### P&L nach Kategorie
| Kategorie     | P&L      | WR  | Trades |
|---------------|----------|-----|--------|
| Sport_US      | -$423    | 21% | 53     |
| MANUAL_CLAIM  | -$26     |  0% |  3     |
| Tennis        | +$63     | 67% | 12     |
| Soccer        | +$114    | 62% | 16     |
| exit_tp1      | +$399    |100% | 25     |
| exit_tp2      | +$241    |100% | 15     |
| exit_price_trigger | +$140 |100% | 1    |

**Fazit: Sport_US ist das Problem. -$423 bei WR 21%.**
Haupttäter: Hornets vs Magic (4x kopiert, ~-$80), Baltimore Orioles (3x, ~-$63)

### Top 5 Verluste
1. -$25.00 | Atlanta Braves vs. Philadelphia Phillies
2. -$24.28 | Baltimore Orioles vs. Cleveland Guardians
3. -$22.07 | Warriors vs. Suns: O/U 219.5
4. -$21.51 | Hornets vs. Magic (1/4)
5. -$21.14 | Hornets vs. Magic (2/4)

### Top 5 Gewinne
1. +$140.36 | Seoul Temp 12°C
2. +$92.18  | Seoul Temp 12°C (Shadow)
3. +$55.09  | Seoul Temp 12°C (Shadow)
4. +$42.67  | Iran Peace Deal YES
5. +$39.77  | Tennis: Soto vs Prado

### Wallet Performance
| Wallet          | P&L      | WR  | Note           |
|-----------------|----------|-----|----------------|
| ...827875ea     | -$192.89 | 38% | RN1 — RAUSWURF |
| [manual-claim]  | -$25.92  |  0% | Claim-Fehler   |
| ...07e3debf     | -$23.11  | 33% | klein          |
| [polymarket-sync]| +$901.96| 93% | Star-Wallet    |

## STRATEGIE
Polymarket Copy Trading + Weather Trading.
Ziel: 55%+ Win Rate, Break-Even bei $1.000.
Aktuell Paper-Modus bis System kalibriert.

## NÄCHSTE SCHRITTE
1. should_trade() Stub komplett fixen
2. Sport_US Kategorie-Filter einbauen (WR <40% → blockieren)
3. Duplicate-Copy Prevention (max 1x pro Markt)
4. Weather-Stationen API debuggen
5. 30+ Paper-Trades sammeln und auswerten
6. Erst wenn WR > 57% über 30 Trades → wieder LIVE
7. RN1 aus Wallet-Liste entfernen (38% WR, -$192)
8. GitHub Support (Account gesperrt seit 18.04.)

## WALLET-ARCHITEKTUR
25 Wallets aktiv. Multiplier:
- majorexploiter: 3.0x
- April#1 Sports: 2.0x
- HorizonSplendidView: 2.0x
- beachboy4: 0.15x
- KeyTransporter: 0.05x
- RN1: 0.3x (RAUSWERFEN!)
- alle anderen: 0.05-0.3x

## WICHTIGE DATEIEN
- /root/KongTradeBot/.env (Secrets)
- /root/KongTradeBot/data/deposits.json
- /root/KongTradeBot/trades_archive.json
- /root/KongTradeBot/data/shadow_portfolio.json
- /root/KongTradeBot/TASKS.md
- /root/KongTradeBot/STATUS.md
