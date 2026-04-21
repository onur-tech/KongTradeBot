# KongTrade — Offene Tasks

**Stand:** 21. April 2026

## 🔴 SOFORT (heute)

- [ ] Insider-Scan Pagination-Bug fixen
  ```python
  # in get_resolved_markets(), nach dem Batch-Loop:
  if len(geo_markets) >= 3000 and len(niche_markets) >= 500:
      break
  ```
  Dann laufenden PID 442096 killen und neu starten.

- [ ] GitHub Account entsperren
  → support.github.com → Ticket antworten
  → "Bitte Repo KongTradeBot-Template löschen"

## 🟡 DIESE WOCHE

- [ ] Ersten echten Weather-Trade dokumentieren
  WEATHER_DRY_RUN=false seit heute — Seoul Apr22 Signal war stark.

- [ ] Paris ICAO korrigieren
  Aktuell: LFPG (CDG) | Soll: LFPB (Le Bourget)

- [ ] Latenz-Fenster messen
  Wann updatet Open-Meteo? Wie lange reagiert Polymarket?

## 🟢 NÄCHSTE 2 WOCHEN

- [ ] XGBoost statt Gauss-Modell
  8 kostenlose Features identifiziert, ~50% Edge-Verbesserung erwartet.

- [ ] Live-Insider-Monitor
  frisches Wallet + $5k+ + unter 20¢ + Geopolitik → Telegram-Alert

- [ ] Monatliche Sigma-Neukalibrierung automatisieren
  calc_station_sigma.py als Cron (1x/Monat)

## 📋 QUEUE — Nächste Tasks

| ID | Aufgabe | Priorität | Notiz |
|----|---------|-----------|-------|
| T-029 | KONZEPT.md als 10. Bootstrap-Datei in SKILL.md/GUIDELINES.md verankern | KRITISCH | Chat-Claude muss sie bei jedem Start lesen |
| T-030 | Insider-Scan Checkpoint implementieren (robust, nicht abstürzen) | WICHTIG | War bei 12840/32265 eingefroren, PID 445411 läuft |
| T-031 | GitHub Support kontaktieren: support.github.com (Portal!) | WICHTIG | Template-Repo löschen lassen, Account entsperren |
| T-032 | ICAO-Mapping verifizieren: Resolution-Kriterien aller aktiven Märkte gegen unsere Stationen abgleichen | KRITISCH | Paris LFPB vs LFPG bewiesen, andere unklar |
| T-033 | Sigma kalibrieren für alle 30 Städte (calc_station_sigma.py lokal ausführen) | WICHTIG | 20 Städte noch DEFAULT 1.8, DNS-blockiert auf Server |
| T-034 | Orderbuch-Tiefe-Check vor jedem Weather-Trade (max 20% der verfügbaren Liquidität) | WICHTIG | Tail-Buckets oft nur $200-500 tief |
| T-035 | Saisonale Performance-Analyse der 809 Backtest-Trades | WICHTIG | Sind Winter-Monate schlechter? |
| T-036 | Weather Live-Trading: Nur kalibrierte Städte (Seoul, Dubai, Moscow + sigma>2.5 Städte) | KRITISCH | Unkalibrierte Städte bleiben im Shadow Mode |
| T-037 | wan123 Multiplier auf 0.5x senken | WICHTIG | 90% WR aber -71% ROI bestätigt |
| T-038 | simple_tail_scanner.py --live --save ausführen (erster echter Weather-Trade) | KRITISCH | Script bereit, Toronto oder Seoul bevorzugt |
| T-039 | shadow_vs_live_compare.py — wöchentlich Freitag 09:00 via systemd Timer | WICHTIG | Script erstellt 21.04., wartet auf Shadow-Abschlüsse |
| T-040 | wallet_performance_report.py — wöchentlich Freitag 09:00 | WICHTIG | Script erstellt 21.04. |
| T-041 | auto_sigma_recalibrate.py — wöchentlich Sonntag 08:00 | WICHTIG | Script erstellt 21.04., braucht >3 Weather-Resolutions pro Stadt |
| T-042 | slippage_tracker.py — täglich 09:00 nach WalletScout | NICE | Script erstellt 21.04., 24 Einträge, Ø -0.17¢ (OK) |

## ✅ ERLEDIGT (21. April 2026)

- [x] WEATHER_DRY_RUN=false gesetzt → Weather Trading live
- [x] negRisk Bucket-Logik korrigiert (bucket_prob)
- [x] Weather Backtest: 809 Trades, 67.2% WR, +$1.091
- [x] Sigma-Kalibrierung 30 Städte (empirisch aus 77 Tagen)
- [x] scan_bucket_arbitrage() implementiert
- [x] insider_analysis.py mit Checkpoint + Streaming gebaut
- [x] Shadow Portfolio city-Feld + Penny-Filter gefixt
- [x] Daily Datapoints Cron aktiv (18:05 UTC täglich)
- [x] ICAO-Mapping für 29/30 Städte verifiziert (Paris offen)
- [x] T-033: Sigma-Kalibrierung v2.0 — 2 Jahre ERA5-Archiv, 30 Städte, monatliche Sigma (calc_station_sigma.py)
- [x] T-036: CALIBRATED_CITIES Live-Filter (32 Städte), unkalibrierte → Shadow-Only
- [x] T-037: wan123 Multiplier auf 0.5x (negative ROI bestätigt — war 2.5x)
- [x] Shadow Portfolio: Kapital unbegrenzt ($999,999), alle Kapital-Checks entfernt
- [x] T-D51: Scripts erstellt (shadow_vs_live, wallet_perf, sigma_recal, slippage) — 21.04.2026
- [x] METAR Lock: check_metar_lock() in weather_scout.py, 2× Sizing + 88% Konfidenz
- [x] T-D50: Health Monitor stündlich (health_monitor.py + systemd Timer, Telegram + E-Mail)
