# KongTrade Bot — Knowledge Base
_Format: Problem → Root-Cause → Fix → Status_

## P001 — FillTracker: open_positions immer leer

**Status:** BEHOBEN (18.04.2026)

**Symptom:** Bot platziert Orders, Dashboard zeigt 0 offene Positionen.

**Root-Cause:** FillTracker._subscribe() nutzte Builder-Credentials statt L2-Credentials.
Polymarket User-Channel benötigt L2-Creds via ClobClient.derive_api_key().
Falsche Creds -> silent disconnect -> keine Events -> alles bleibt in pending hängen.

**Referenz:** github.com/Polymarket/clob-client/issues/303

**Fix:** core/fill_tracker.py -> _derive_l2_creds() nutzt ClobClient.derive_api_key().

---

## P002 — dict object has no attribute signature_type

**Status:** BEHOBEN (17.04.2026)

**Root-Cause:** get_balance_allowance() mit plain dict aufgerufen statt BalanceAllowanceParams Objekt.

**Fix:** from py_clob_client.clob_types import BalanceAllowanceParams; params = BalanceAllowanceParams(...)

---

## P003 — Pending Orders nach Neustart verloren

**Status:** BEHOBEN (18.04.2026)

**Root-Cause:** save_positions() speicherte nicht _pending_data, market_closes_at fehlte.

**Fix:** main.py: market_closes_at serialisieren + recover_stale_positions() via REST API beim Start.

---

## P004 — Proxy-Deploy Catch-22

**Status:** DOKUMENTIERT

**Symptom:** Alle Orders scheitern, Proxy nicht deployed.

**Lösung:** $1 Manual-Trade auf polymarket.com über NORWEGEN-VPN (nicht Finnland!).

---

## P005 — Balance-Fetch fehlschlägt (rpc.ankr.com)

**Status:** WORKAROUND

**Root-Cause:** rpc.ankr.com blockiert Hetzner-IP.

**Workaround:** Fallback-RPCs: polygon-bor-rpc.publicnode.com (reliable), polygon-rpc.com, 1rpc.io/matic.

---

## P006 — signature_type=1 Pflicht für Magic-Link

**Status:** DOKUMENTIERT

**Fix:** ClobClient(... signature_type=1). Ohne diesen Parameter -> Auth-Fehler bei allen Orders.

---

## P007 — NegRisk-Märkte (z.B. Maduro Venezuela)

**Status:** DOKUMENTIERT

**Fix:** neg_risk Flag aus Orderbook lesen (_get_market_info), im Log als [NEGRISK] markieren.

---

## P008 — Ghost Trades durch create_order + post_order separat

**Status:** DOKUMENTIERT

**Fix:** Immer create_and_post_order() in EINEM Call. Niemals create_order() + post_order() separat.

---

## Infrastruktur-Quick-Reference

Server:          89.167.29.183 (Hetzner Helsinki)
Bot-Pfad:        /root/KongTradeBot/
Proxy-Wallet:    0x700BC51b721F168FF975ff28942BC0E5fAF945eb
Magic-EOA:       0xd7869A5Cae59FDb6ab306ab332a9340AceC8cbE2
USDC.e Contract: 0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174
Dashboard-URL:   ssh -L 5000:localhost:5000 root@89.167.29.183 -> http://localhost:5000
Bot Log:         /root/KongTradeBot/logs/bot_YYYY-MM-DD.log
State:           /root/KongTradeBot/bot_state.json
Metrics DB:      /root/KongTradeBot/metrics.db

---

## P009 — Dashboard: SEIT START / 24h Δ zeigen "—"

**Status:** OFFEN

**Symptom:** Balance-Widget zeigt "—" für "SEIT START" und "24H CASH Δ".

**Root-Cause:** setDelta() erhält d.delta_total=null — /api/balance berechnet Deltas nur auf Cash-Basis (USDC.e on-chain), nicht auf Portfolio-Total (Cash + Shares). Seit Portfolio-Total neu ist, fehlt der Startvergleichswert.

**Fix:** In dashboard.py: Portfolio-Total-Snapshot beim Sessionstart in SQLite balance_snapshots speichern. delta_total = portfolio_now - portfolio_at_session_start. delta_24h = portfolio_now - portfolio_24h_ago (aus DB).

---

## P010 — Balance-Chart zeigt Cash statt Portfolio-Total

**Status:** OFFEN

**Symptom:** Balance-Chart im Dashboard visualisiert nur USDC.e Cash-Verlauf, nicht Gesamtportfolio.

**Root-Cause:** db_insert_balance() speichert config.portfolio_budget_usd (= Cash). Portfolio-Total (Cash + currentValue aller Shares) wird nicht persistiert.

**Fix:** SQLite balance_snapshots um Spalte portfolio_total REAL erweitern. db_insert_balance() umbenennen auf db_insert_snapshot(cash, portfolio_total). Chart-Endpoint /api/chart anpassen.

---

## P011 — Positionen-Tabelle: Countdown-Spalte fehlt

**Status:** OFFEN

**Symptom:** Kein "SCHLIESST IN"-Countdown in der Open-Positionen-Tabelle.

**Root-Cause:** data-api.polymarket.com/positions liefert endDate (Unix-Timestamp), aber fetchPortfolio() in dashboard.html rendert diese Spalte nicht.

**Fix:** In fetchPortfolio() JS: closes_h = (p.endDate - Date.now()/1000) / 3600. CSS-Klassen: closes-red (<1h), closes-yellow (1-6h), closes-green (>6h).

---

## P012 — "NÄCHSTE RESOLUTIONS" Panel immer leer

**Status:** OFFEN

**Symptom:** Resolutions-Panel leer obwohl 37 Positionen mit endDate vorhanden.

**Root-Cause:** /api/resolutions liest open_positions aus bot_state.json (Phantom-Daten nach Neustart), nicht aus Live-Portfolio-Cache (_polymarket_positions).

**Fix:** /api/resolutions auf _polymarket_positions["data"] umstellen. endDate aus Polymarket-API extrahieren, Top 5 nach endDate sortieren.

---

## P013 — Service-Health: "WS Events 0" trotz aktiver Bot-Aktivität

**Status:** OFFEN

**Symptom:** Dashboard zeigt "WS Events 0 (letzte 5min)" obwohl Bot Signale empfängt.

**Root-Cause 1:** ws_events_min zählt nur "CONFIRMED" und "MATCHED" im Log — die seit Stunden wegen Balance-Error nicht vorkommen.
**Root-Cause 2:** FillTracker.subscribe_market() wird nach neuen Orders nicht aufgerufen (Dynamic Subscribe fehlt).

**Fix 1 (sofort):** Auch "NEUER TRADE erkannt" und "Signal buffered" als Aktivität zählen.
**Fix 2 (T-NIGHT-3):** execution_engine.py: nach create_and_post_order() fill_tracker._subscribe_new_conditions([condition_id]) aufrufen.

---

## P014 — CLAIM-Button zeigt "—" trotz redeemable=true

**Status:** OFFEN

**Symptom:** Positionen-Tabelle Claim-Spalte zeigt "—" für alle 4 redeemable Positionen.

**Root-Cause:** Polymarket-API gibt das Feld inkonsistent zurück: mal "redeemable", mal "isRedeemable", mal "redeemed": false mit "winner": true.

**Fix:** In dashboard.html fetchPortfolio(): const claimable = p.redeemable || p.isRedeemable || (p.redeemed === false && p.winner);

---

## P015 — Positionen-Tabelle zeigt nur ~10 von 37

**Status:** OFFEN

**Symptom:** 37 Positionen geladen (count=37), aber Tabelle zeigt nur ~10.

**Root-Cause:** CSS .tbl-wrap hat max-height + overflow-y:auto. Positionen vorhanden aber hinter Scroll versteckt. Eventuell auch JS-slice() aktiv.

**Fix:** CSS: .tbl-wrap { max-height: 600px; } auf 800px erhöhen oder overflow-y:scroll explizit setzen. JS: kein .slice() auf d.positions anwenden.

---

## P016 — P&L HEUTE zeigt +$0.00

**Status:** OFFEN

**Symptom:** Session-Stats "P&L HEUTE" immer $0.00.

**Root-Cause:** api_stats_session() berechnet P&L nur aus trades_archive.json (aufgelösten Trades). Unrealized P&L und Portfolio-Delta seit Mitternacht fehlen.

**Fix:** P&L Heute = portfolio_total_jetzt minus portfolio_total_um_mitternacht. Mitternacht-Snapshot in SQLite speichern (täglich via cron oder beim ersten DB-Write nach 00:00).

---

## P017 — Per-Wallet-Performance "Keine Daten"

**Status:** OFFEN

**Symptom:** Wallet-Performance-Panel leer trotz 178 Signale von 11 Wallets.

**Root-Cause:** api_wallet_performance() liest aus trades_archive.json, filtert nach aufgeloest=True. Da keine Trades wegen Balance-Error ausgeführt wurden, ist die Archiv-Datei leer.

**Fix (kurzfristig):** Auch nicht-aufgelöste Trades (kopierte Signale) anzeigen.
**Fix (langfristig):** Wallet-Signal-Counter aus wallet_monitor.py in State persistieren.

---

## P018 — Timezone: Log UTC vs Dashboard Europe/Berlin

**Status:** DOKUMENTIERT

**Symptom:** Bot-Logs 00:17 UTC, Dashboard-Header 02:14 (Berlin).

**Root-Cause:** Python datetime.now() = Lokalzeit Server (UTC), Browser-JS = Localtime (Europe/Berlin = UTC+2).

**Fix:** Server-Timestamps explizit als UTC labeln oder alle mit timezone.utc erzeugen. Dashboard: moment.js oder Intl.DateTimeFormat für Anzeige.

---

## P019 — RPC ankr.com liefert $0.00 (gibt nie Fehler zurück)

**Status:** BEHOBEN (18.04.2026)

**Root-Cause:** rpc.ankr.com/polygon antwortet HTTP 200 mit result=0x0 (falsche Daten). Da kein Exception ausgelöst wird, wird $0.00 sofort zurückgegeben ohne andere RPCs zu probieren.

**Fix:** In balance_fetcher.py: if balance_usdc <= 0: continue — nächsten RPC probieren. Niemals auf .env-Fallback zurückfallen.

---

## P020 — Duplicate Log-Zeilen (jede INFO 2x)

**Status:** BEHOBEN (18.04.2026)

**Root-Cause:** setup_logger() erstellt polymarket_bot-Logger mit propagate=True (Standard). Sub-Logger (polymarket_bot.balance etc.) propagieren Events zu polymarket_bot UND zu Root-Logger. Wenn Root-Logger ebenfalls Handlers hat -> Duplikat.

**Fix:** logger.py: nach if logger.handlers: return logger — logger.propagate = False hinzufügen.

---

## P021 — Geoblock auf Windows-lokalem Bot

**Status:** DOKUMENTIERT

**Symptom:** Lokale Windows-Installation erhält 403 "Trading restricted in your region".

**Root-Cause:** Lokale IP ist von Polymarket für CLOB-API geblockt. Hetzner-Helsinki-IP ist freigegeben.

**Fix:** Lokalen Bot nur für DRY_RUN verwenden. Live-Trading ausschließlich auf Hetzner-Server.
