# KongTrade Bot — Status

**Letzte Aktualisierung:** 21. April 2026

## Bot-Status
- **Server:** Hetzner Helsinki (89.167.29.183)
- **Bot:** active (running) ✅
- **DRY_RUN:** false (Copy Trading live)
- **WEATHER_DRY_RUN:** false ✅ (seit 21. April live)
- **Dashboard:** https://kong-trade.com ✅
- **Cron:** 4x täglich aktiv ✅

## Wallet
- **Adresse:** 0x700BC51b721F168FF975ff28942BC0E5fAF945eb
- **Telegram:** Chat-ID 507270873

## Aktuelles Portfolio
- Weather Trading: LIVE (seit 06:47 UTC, WEATHER_MAX_DAILY_USD=$10)
- Shadow Portfolio: 60+ offene WEATHER-Positionen (virtuell)
- Echte Trades: erste Ausführung beim nächsten Scout-Lauf erwartet

## Aktive Prozesse
- kongtrade-bot: PID läuft via systemd
- insider_analysis.py: PID 442096 (Streaming-Version, lädt Märkte)

## Offene Aufgaben
1. Insider-Scan Pagination-Bug fixen (läuft in Endlosschleife)
2. GitHub Account entsperren
3. Paris ICAO von LFPG auf LFPB korrigieren

## Session 22. April 2026 — Nacht-Status

Stand 22:05 Uhr:
- PnL heute: +$245.76
- Gesamt Bot-PnL: +$278.25
- Win Rate: 55.7%
- Total Trades: 204
- Wallet Polymarket: ~$699

Kritisch offen:
- should_trade() Stub (Gate inaktiv)
- Wetter-Stationen kein Cache
- Iran Peace Deal löst ~02:00 Uhr auf
- Budget 136%

Morgen früh prüfen:
1. Iran Auflösung Ergebnis
2. Budget nach Positionen-Cleanup
3. WalletScout Kandidaten
4. Auto-Claim ERR beheben
5. should_trade() final implementieren
