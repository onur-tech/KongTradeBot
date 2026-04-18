# KongTrade Bot — Knowledge Base
_Bewährte Erkenntnisse, Bug-Analysen und Workarounds_
_Stand: 2026-04-18_

---

## P001 — Proxy-Deploy Catch-22
**Problem:** Neuer Polymarket-Account kann keine Orders platzieren.
**Root Cause:** Polymarket Proxy-Contract wird erst beim ersten erfolgreichen Trade deployed. Kein Trade → Proxy fehlt → Allowance=0 → Trade scheitert → Kein Trade.
**Fix:** $1 Manual-Trade auf polymarket.com über **Norwegen-VPN** (AirVPN) machen. Finnland wird geblockt, Norwegen funktioniert.

---

## P002 — Magic-Link vs MetaMask signature_type
**Problem:** Alle Orders schlagen mit Auth-Fehler fehl.
**Root Cause:** `signature_type=0` (MetaMask-Standard) wird im ClobClient verwendet. Magic-Link Accounts benötigen `signature_type=1`.
**Fix:** `ClobClient(..., signature_type=1, ...)` — Pflicht für Magic-Link. Ohne dies schlägt jede Order fehl.

---

## P003 — Phantom-Positionen in bot_state.json
**Problem:** Dashboard zeigt Positionen, die nicht auf Polymarket existieren.
**Root Cause:** Bot trackt Orders als "offen" sofort nach Submit, auch wenn Polymarket sie ablehnt. Abgelehnte Orders = Phantom-Positionen.
**Fix:** Nach Neustart `bot_state.json` prüfen, Phantome entfernen. Backup liegt als `bot_state_phantom_backup.json`.

---

## P004 — FillTracker condition_id-Mapping
**Problem:** WebSocket subscribed mit falschen IDs, MATCHED-Events kommen nicht durch. Bot-State zeigt "0 offen".
**Root Cause:** `condition_id` vs `token_id` Verwechslung beim WebSocket-Subscribe. Polymarket User-Channel braucht `condition_id` (Market-Level), nicht `token_id` (Outcome-Level).
**Fix:** In `fill_tracker.py` sicherstellen dass `PendingOrder.condition_id` die Market-Condition-ID enthält, nicht die Token-ID.

---

## P005 — ankr.com RPC liefert $0.00
**Problem:** `balance_fetcher.py` gibt $0.00 zurück, obwohl Wallet ~$28 hat. Bot fällt auf `.env`-Wert zurück.
**Root Cause:** `rpc.ankr.com/polygon` gibt manchmal HTTP 200 mit `result=0x0` zurück (falsche Daten, kein Fehler). Da kein Fehler ausgelöst wird, wird $0.00 sofort zurückgegeben ohne andere RPCs zu probieren.
**Fix:** In `balance_fetcher.py`: wenn `balance_usdc <= 0`, nicht zurückgeben sondern `continue` auf nächsten RPC. Nie auf `.env`-Fallback zurückfallen — immer alle RPCs durchprobieren.

---

## P006 — Duplikat-Wallet in TARGET_WALLETS
**Problem:** Jedes Signal erscheint doppelt in den Logs (`trades_detected` wächst doppelt so schnell wie erwartet).
**Root Cause:** Dieselbe Wallet-Adresse ist zweimal in `TARGET_WALLETS` in `.env` eingetragen (z.B. Copy-Paste-Fehler).
**Fix:** `grep TARGET_WALLETS /root/KongTradeBot/.env` → doppelte Adresse entfernen → Bot neu starten.

---

## P007 — SEIT START / 24H CASH Δ zeigen "—" (Delta-Berechnung broken)
**Problem:** Dashboard Balance-Widget zeigt "—" für "SEIT START" und "24H CASH Δ".
**Root Cause:** `setDelta()` erwartet `d.delta_total` und `d.delta_24h` als Zahlen, aber `/api/balance` berechnet Deltas basierend auf Cash-Balance (nur USDC.e), nicht Portfolio-Total (Cash + Shares). Da Portfolio-Total eine neue Variable ist, fehlt der Vergleichswert für "Seit Start".
**Fix:** In `dashboard.py`: Portfolio-Snapshot beim Start speichern (oder in SQLite `balance_snapshots` als `portfolio_total`). Delta = aktueller Portfolio-Total minus Portfolio-Total beim Sessionstart / vor 24h.

---

## P008 — Balance-Chart zeigt Cash-Verlauf statt Portfolio-Verlauf
**Problem:** Der Balance-Chart im Dashboard visualisiert nur den USDC.e Cash-Verlauf, nicht den Gesamtportfolio-Wert.
**Root Cause:** `db_insert_balance()` speichert nur `config.portfolio_budget_usd` (= Cash), nicht `portfolio_total` (Cash + Shares-Wert).
**Fix:** SQLite `balance_snapshots` um Spalte `portfolio_total` erweitern. `db_insert_balance()` mit Portfolio-Wert aufrufen. Chart-Endpoint `/api/chart` anpassen.

---

## P009 — Positionen-Tabelle fehlt Countdown-Spalte "SCHLIESST IN"
**Problem:** Die Open-Positionen-Tabelle im Dashboard zeigt keine Information wann Märkte schließen.
**Root Cause:** `data-api.polymarket.com/positions` liefert `endDate` (Unix-Timestamp) pro Position, aber `fetchPortfolio()` in `dashboard.html` rendert diese Spalte nicht.
**Fix:** In `fetchPortfolio()` JS: `closes_in_h = (p.endDate - Date.now()/1000) / 3600`. CSS-Klassen: `closes-red` (<1h), `closes-yellow` (1-6h), `closes-green` (>6h). Spalte nach "P&L%" einfügen.

---

## P010 — "NÄCHSTE RESOLUTIONS" Panel leer (37 Positionen mit endDate)
**Problem:** Das "Nächste Resolutions"-Panel zeigt keine Einträge, obwohl 37 offene Positionen endDates haben.
**Root Cause:** `/api/resolutions` liest `open_positions` aus `bot_state.json` (Phantom-Daten), nicht aus dem Live-Portfolio-Cache (`_polymarket_positions`). Da bot_state.json nach dem letzten Neustart keine Positionen enthält, ist die Liste leer.
**Fix:** `/api/resolutions` auf `_polymarket_positions["data"]` umstellen. `endDate` aus Polymarket-API-Daten extrahieren, Top 5 nach `endDate` sortieren.

---

## P011 — Service-Health: "WS Events 0" obwohl Bot aktiv ist
**Problem:** Dashboard Service-Health zeigt "WS Events 0 (letzte 5min)" obwohl der Bot Orders produziert und Signale empfängt.
**Root Cause:** `ws_events_min` zählt "CONFIRMED" oder "MATCHED" im Log — aber der Bot hat seit Stunden keine erfolgreichen Orders mehr (Balance-Error). Außerdem fehlt Dynamic-Subscribe: neue Orders werden nicht zum FillTracker gemeldet.
**Fix (kurzfristig):** Auch "NEUER TRADE erkannt" und "Signal" als WS-Aktivität zählen. **Fix (langfristig):** In `execution_engine.py` nach erfolgreicher Order-Submission `fill_tracker.subscribe_market(condition_id)` aufrufen.

---

## P012 — CLAIM-Spalte zeigt "—" für alle redeemable=true Positionen
**Problem:** Die Positionen-Tabelle zeigt "—" in der Claim-Spalte auch wenn `redeemable=true`.
**Root Cause:** Polymarket-API gibt das Feld als `redeemable` oder `isRedeemable` zurück (inkonsistent). `fetchPortfolio()` prüft nur `p.redeemable`, nicht `p.isRedeemable`.
**Fix:** In `dashboard.html` `fetchPortfolio()`: `const claimable = p.redeemable || p.isRedeemable || p.redeemed === false && p.winner;`. Außerdem: `currentValue` aus API prüfen — Button nur anzeigen wenn `currentValue > 0`.

---

## P013 — Positionen-Tabelle zeigt nur 10 von 37 Positionen
**Problem:** Obwohl 37 Positionen geladen werden (`count=37`), zeigt die Tabelle nur ~10.
**Root Cause:** CSS `.tbl-wrap` hat `max-height` und `overflow-y:auto` — die anderen Positionen sind vorhanden aber hinter dem Scroll. Außerdem könnte eine `slice()` im JS die Liste limitieren.
**Fix:** CSS: `.tbl-wrap { max-height: 500px; overflow-y: auto; }` erhöhen auf 800px oder entfernen. JS: kein `slice()` auf `d.positions` anwenden. Optional: Pagination-Buttons.

---

## P014 — P&L HEUTE zeigt +$0.00 (falsche Berechnung)
**Problem:** "P&L HEUTE" in der Session-Stats-Bar zeigt immer $0.00.
**Root Cause:** `api_stats_session()` berechnet P&L nur aus `trades_archive.json` — aufgelösten/geschlossenen Trades. Unrealized P&L (offene Positionen) und Portfolio-Delta seit Mitternacht fehlen.
**Fix:** P&L Heute = `portfolio_total_jetzt` minus `portfolio_total_um_mitternacht`. Portfolio-Snapshot um Mitternacht in SQLite speichern.

---

## P015 — Per-Wallet-Performance "Keine Daten" (178 Signale von 11 Wallets)
**Problem:** Das Wallet-Performance-Panel zeigt "Keine Daten" obwohl 178 Signale von 11 verschiedenen Wallets verarbeitet wurden.
**Root Cause:** `api_wallet_performance()` liest aus `trades_archive.json` und filtert nach `aufgeloest=True`. Da keine Trades erfolgreich ausgeführt wurden (Balance-Error seit Stunden), sind keine abgeschlossenen Trades in der Archiv-Datei.
**Fix (kurzfristig):** Auch unaufgelöste Trades anzeigen (= kopierte Signale). **Fix (langfristig):** Wallet-Signal-Counter aus `wallet_monitor.py` in Dashboard integrieren.

---

## P016 — Timezone-Inkonsistenz: Log UTC vs Dashboard Europe/Berlin
**Problem:** Bot-Logs zeigen 00:17 UTC, Dashboard-Header zeigt 02:14 (Berlin). Verwirrend beim Debugging.
**Root Cause:** Python `datetime.now()` gibt Lokalzeit (Server: UTC), aber Dashboard-JS nutzt Browser-Localtime (Europe/Berlin = UTC+2). Beide Quellen korrekt, aber inkonsistent dargestellt.
**Fix:** Entweder alles auf UTC oder alles auf Europe/Berlin. Empfehlung: Server-Zeit im Dashboard explizit als "UTC" labeln, oder in `dashboard.py` alle Timestamps mit `timezone.utc` erzeugen.

---

## P017 — FillTracker L2-Creds Ableitung schlägt fehl
**Problem:** Bei jedem Start: `WARNING: Balance-Check fehlgeschlagen: 'dict' object has no attribute 'signature_type'`.
**Root Cause:** `ClobClient` wird in `execution_engine.py` für Balance-Check mit inkomplettem Objekt initialisiert. Der `funder`-Parameter fehlt oder `signature_type` wird nicht korrekt übergeben.
**Fix:** In `execution_engine.py` Balance-Check-Initialisierung: `client = ClobClient(host=..., key=config.private_key, chain_id=137, signature_type=1, funder=config.polymarket_address)`.

---

## P018 — Bot-Log rotiert nicht (screen-Session mit statischem Datum)
**Problem:** `bot.log` und `bot_2026-04-17.log` wachsen unbegrenzt; nach Mitternacht wird keine neue Log-Datei erstellt.
**Root Cause:** Screen-Session wurde am 17.04. gestartet — `logger.py` berechnet `datetime.now().strftime("%Y-%m-%d")` einmal beim Import. Solange dieselbe Python-Prozess läuft, bleibt der Dateiname statisch.
**Fix:** `TimedRotatingFileHandler` statt `FileHandler` verwenden — rotiert automatisch um Mitternacht ohne Prozess-Neustart.

---

## P019 — Geoblock auf Windows-Bot (lokal)
**Problem:** Lokale Windows-Installation des Bots erhält `403 Trading restricted in your region`.
**Root Cause:** Lokale IP ist nicht von Polymarket für CLOB-API freigegeben. Nur der Hetzner-Server in Helsinki hat eine nicht-geblockte IP.
**Fix:** Lokalen Bot nur für Dry-Run verwenden. Live-Trading ausschließlich auf Hetzner-Server. Alternativ: VPN mit Norwegen-Endpunkt für lokale Tests.

---

## P029 — Balance-Check 400: assetAddress invalid hex address (T-010)
**Problem:** Bot wirft alle ~3 Minuten `PolyApiException[status_code=400, 'GetBalanceAndAllowance invalid params: assetAddress invalid hex address ']`. Portfolio-Wert zeigt $0.00 im Dashboard.
**Root Cause:** `_verify_order_onchain()` ruft `get_balance_allowance(asset_type="CONDITIONAL", token_id=token_id)` auf. `token_id` ist leer (`""`) bei Positionen die aus dem Recovery-Flow (`recover_stale_positions`) oder aus `bot_state.json` restauriert wurden, wenn die REST-API kein `token_id`/`asset_id`-Feld zurückgibt. Die ~3-Minuten-Periode entspricht dem Watchdog-`RESTART_COOLDOWN=180`.
**Fix (deployed 2026-04-18):**
1. `execution_engine.py _verify_order_onchain`: Guard vor API-Call — leeres `token_id` → WARNING + `return False` statt 400-Fehler.
2. `main.py restore_positions`: Filtert Positionen mit leerem `token_id` vor Restore (Stale-Cleanup).
3. `main.py recover_stale_positions`: Filtert Orders ohne `token_id` vor Eintrag in `_pending_data`.
4. Einmaliges Cleanup-Script für bestehende `bot_state.json`: `d['open_positions'] = [p for p in d.get('open_positions', []) if p.get('token_id') and p['token_id'] not in ('', '0x', '0x0')]`
**Status:** DEPLOYED — verifiziert via `/api/logs` ca. 09:35 UTC.
