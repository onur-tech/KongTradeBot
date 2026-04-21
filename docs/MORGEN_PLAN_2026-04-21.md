# Morgen-Plan — 2026-04-21

## Priorität 1 — X Monitor aktivieren & testen
- `X_MONITOR_ENABLED=true` in .env setzen (jetzt: false)
- Erst prüfen ob `twitterapi.io` Key funktioniert:
  ```bash
  curl -H "X-API-Key: sk-kwspyrBOi..." \
    "https://api.twitterapi.io/twitter/user/last_tweets?userName=Reuters&count=3"
  ```
- Response-Format prüfen und ggf. `analyze()` Tweet-Felder anpassen
- Bot neustarten: `systemctl restart kongtrade-bot`
- Im Telegram: erste X-Signale sollten nach 30s kommen

## Priorität 2 — Weather Trading live schalten
- Aktuell: `WEATHER_DRY_RUN=true`, `WEATHER_MAX_DAILY_USD=10`
- Backtest auswerten: `python3 scripts/weather_backtest.py`
- Wenn Edge > 40% auf ≥2 Märkten: auf LIVE umschalten
- Dashboard → WEATHER Tab → "TOGGLE" Button

## Priorität 3 — Anomaly Detector Feintuning
- Aktuelle Logs checken: `grep ANOMALY bot.log | tail -50`
- Erwartetes Verhalten: alle 5 Min ein "X Märkte nach Filter" Log
- Wenn 0 Märkte: Thresholds weiter senken
  - `ANOMALY_MIN_TRADE_USD=100` (von 500)
  - `ANOMALY_MIN_AGGREGATE_USD=1000` (von 5000)
- Bei zu vielen False-Positives: wieder erhöhen

## Priorität 4 — ScottyNooo Entscheidung
- ScottyNooo: `0x40471b34671887546013ceb58740625c2efe7293` (49.6% WR, 33% ROI)
- Wenn in nächsten 24h weitere Gewinne (check predicts.guru): integrieren mit 0.05x
- .env → TARGET_WALLETS ergänzen, WALLET_WEIGHTS eintragen

## Priorität 5 — Telegram Bridge aktivieren
- `TELEGRAM_API_ID` und `TELEGRAM_API_HASH` auf https://my.telegram.org holen
- In .env eintragen
- `TELEGRAM_BRIDGE_ENABLED=true` setzen
- Session erstellen: `python3 -c "from core.telegram_bridge import create_session; create_session()"`
- GlintAlertsBot Signale werden dann kopiert

## Monitoring-Checks morgen früh
1. `grep "ERROR\|CRITICAL" /root/KongTradeBot/bot.log | tail -20`
2. `grep "WeatherScout.*Opportunity" /root/KongTradeBot/bot.log | tail -10`
3. `grep "ANOMALY.*Signal" /root/KongTradeBot/bot.log | tail -10`
4. Dashboard → WEATHER Tab (neue UI)
5. Telegram → Heutige P&L Summary um 20:00 Uhr

## Offene Tech-Schulden
- `anomaly_detector.execute_signal()`: `place_order()` noch nicht implementiert (nur Alert)
- Wallet P&L: `trades_archive.json` fehlt — Fallback auf all_signals.jsonl
- Weather: `PirateWeather` Key leer — nur 3-Quellen Ensemble aktiv
