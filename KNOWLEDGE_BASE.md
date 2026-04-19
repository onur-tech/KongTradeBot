# KongTrade Bot — Knowledge Base
_Format: Problem → Root-Cause → Fix → Status_
_Ziel: Dokumentiert jeden gelösten Bug damit er nie wieder stundenlang debuggt werden muss._
_Update: Nach jedem Fix neuen P00X-Eintrag hinzufügen._

---

## P001 — FillTracker: Alle Orders bleiben in pending, open_positions immer leer

**Status:** ✅ BEHOBEN (18.04.2026)

**Symptom:**
Bot platziert echte Orders, Polymarket bestätigt sie, aber das Dashboard zeigt dauerhaft 0 offene Positionen.
 enthält keine Einträge in .

**Root-Cause:**
 sendete die WebSocket-Auth mit Builder-Credentials statt L2-Credentials.
Polymarket User-Channel (wss://ws-subscriptions-clob.polymarket.com/ws/user) erfordert L2-Credentials,
die via  abgeleitet werden müssen.
Mit falschen Creds → silent disconnect ohne Fehlermeldung → keine Events empfangen →
alle Orders bleiben im  Bucket hängen →  bleibt leer.

**Referenz:** github.com/Polymarket/clob-client/issues/303

**Fix:**
 →  Methode nutzt jetzt :

Fallback auf Config-Creds wenn derive fehlschlägt.

**Verification:**
Nach Neustart: WebSocket sollte Events empfangen (log zeigt User-Channel subscribed).
Nach nächster Order: Position erscheint in open_positions (Dashboard Tab OPEN).

---

## P002 — On-Chain Verifikation: 'dict object has no attribute signature_type'

**Status:** ✅ BEHOBEN (17.04.2026)

**Symptom:**

Bei jeder Order, nach dem Submit.

**Root-Cause:**
 rief  mit einem plain dict auf:

py-clob-client erwartet aber ein  Objekt.

**Fix:**
:


---

## P003 — Stale Positionen nach Bot-Neustart verloren

**Status:** ✅ BEHOBEN (18.04.2026)

**Symptom:**
Bot neugestartet.  enthält open_positions aber nach Reload sind Pending-Orders verschwunden.
Orders die im pending-Bucket waren (submitted, noch nicht confirmed) sind nach Neustart weg.

**Root-Cause:**
 in main.py speicherte nur , nicht .
Außerdem wurde  nicht serialisiert → nach Restore fehlten Countdown-Informationen.

**Fix:**
:
1.  → fügt  zur Serialisierung hinzu
2.  → deserialisiert  zurück zu datetime
3. Neue  Async-Funktion → fragt Polymarket REST 
   nach offenen Orders und fügt sie als pending hinzu falls noch nicht im State

---

## P004 — Proxy-Deploy Catch-22 (Magic-Link Account)

**Status:** ✅ DOKUMENTIERT (17.04.2026)

**Symptom:**
Bot startet, alle Orders scheitern mit Allowance-Fehler. Kein Trade möglich.

**Root-Cause:**
Polymarket Proxy-Contract wird erst deployed wenn der ERSTE erfolgreiche Trade stattfindet.
Wenn der allererste Trade scheitert (Geoblock, Allowance=0, etc.) → Proxy nicht deployed →
Allowance=0 → Trade scheitert → Teufelskreis.

**Lösung:**
 Manual-Trade auf polymarket.com über **Norwegen-VPN** (AirVPN) machen.
Finnland-AirVPN funktioniert nicht. Norwegen funktioniert.

---

## P005 — Balance-Fetch schlägt fehl mit RPC rpc.ankr.com

**Status:** ✅ WORKAROUND (17.04.2026)

**Symptom:**

Log zeigt  Balance obwohl 900+ USDC.e on-chain.

**Root-Cause:**
 blockiert oder rate-limited Anfragen von Hetzner-IP.

**Workaround:**
 → Mehrere Fallback-RPCs konfiguriert:
1. https://rpc.ankr.com/polygon (primary, oft flaky)
2. https://polygon-bor-rpc.publicnode.com (reliable)
3. https://polygon-rpc.com
4. https://1rpc.io/matic

Dashboard nutzt direkt  als Primary.

---

## P006 — signature_type=1 Pflicht für Magic-Link Account

**Status:** ✅ DOKUMENTIERT (17.04.2026)

**Symptom:**
Alle Orders scheitern mit Auth-Fehler obwohl Private Key korrekt ist.

**Root-Cause:**
Magic-Link Account erfordert  im ClobClient.
Standard-Wert 0 ist für MetaMask/EOA Wallets.

**Fix:**


---

## P007 — NegRisk-Märkte: NEGRISK-Flag erforderlich

**Status:** ✅ DOKUMENTIERT (17.04.2026)

**Symptom:**
Orders auf bestimmten Märkten (z.B. Maduro Venezuela) scheitern oder werden falsch behandelt.

**Root-Cause:**
Polymarket hat Negative Risk Märkte die spezielle Behandlung brauchen.
Das  Flag kommt vom Orderbook-Endpoint ().

**Fix:**
 liest  aus dem Orderbook und loggt es.
Das Flag wird im Order-Log als  ausgegeben.

---

## P008 — Ghost Trades durch create_order + post_order separat

**Status:** ✅ DOKUMENTIERT (community lesson)

**Symptom:**
Doppelte Orders auf Polymarket, Balance-Inkonsistenzen.

**Root-Cause:**
Wenn  und  in zwei separaten Calls aufgerufen werden,
kann ein Netzwerkfehler zwischen den Calls einen Ghost Trade erzeugen.

**Fix:**
Immer  in einem einzigen Call verwenden.
NIEMALS  +  separat.

---

## 📋 Wallet-Referenz

| Wallet | Name | Multiplier | Notes |
|--------|------|-----------|-------|
| 0x019782... | majorexploiter | 3.0x | 76% Win Rate |
| 0x492442... | April#1 Sports | 2.0x | 65% Win Rate |
| 0x02227b... | HorizonSplendidView | 2.0x | Sports specialist |
| RN1 | RN1 | 0.2x | Kleiner Einsatz |

## 🔑 Infrastruktur-Quick-Reference



---

## P022 -- Stale bot.lock -> Endlos-Crash-Loop (06:29-07:23 UTC, 2026-04-18)

**Status:** BEHOBEN (struktureller Fix 2026-04-18 08:15 UTC)

**Symptom:**
Bot startet ~alle 15s, laeuft 1.5s, Exit-Code 1.
Journalctl: "Main process exited, code=exited, status=1/FAILURE" in Dauerschleife.
service-bot.log enthaelt nur: "Bot laeuft bereits! Lock-Datei: /root/KongTradeBot/bot.lock"
Watchdog erkennt DOWN, versucht Restart -- hilft nicht (Lock bleibt).

**Timeline:**
- 06:17-06:47: Ankr RPC liefert $0.00 (Balance-Fehler, kein CRITICAL geloggt)
- ~06:28: Original-Prozess crashed still (kein Fehler-Log, Journal rotiert)
- 06:29:55: systemd-Restart startet Lock-Loop
- 06:47: Letzter Log-Eintrag des alten Prozesses (bot_2026-04-17.log)
- 07:23: Manuell gefixt -- rm bot.lock + systemctl reset-failed + restart

**Root-Cause:**
Ausloeser: ankr-RPC-Ausfall -> Balance-Fetch haengt/fail-loops ->
Heartbeat-Update stoppt -> Watchdog erkennt stale Heartbeat (>1700s) ->
systemctl restart sendet SIGTERM -> Prozess terminiert OHNE Lock-Cleanup
(atexit/Signal-Handler lief nicht durch, Race-Condition moeglich
bei gleichzeitigem ankr-Timeout-Thread).

**Mechanismus:**
bot.lock wird beim Start gesetzt, aber cleanup() nicht via atexit registriert,
nur via SIGTERM-Handler. Bei hartem Kill oder Startup-Exception BEVOR
Handler registriert ist -> Lock bleibt und blockiert alle Neustarts.

**Fix (sofort):**
  rm -f /root/KongTradeBot/bot.lock
  systemctl reset-failed kongtrade-bot
  systemctl restart kongtrade-bot

**Fix (strukturell -- TODO):**
1. bot.lock Cleanup via atexit.register(cleanup) ZUSAETZLICH zu Signal-Handler
2. bot.lock beim Start pruefen: wenn PID drin tot ist -> automatisch loeschen (PID-Lock)
3. Watchdog: vor restart -> rm bot.lock (eine Zeile hinzufuegen)
4. ankr-RPC Timeout hart auf 5s cappen (kein haengendes Request)



**Struktureller Fix (2026-04-18) — 3-Ebenen-Absicherung:**

Ebene 1 — main.py (check_and_create_lock):
  - Liest PID aus bot.lock, prueft via psutil ob Prozess wirklich existiert
  - Ist PID tot: lock entfernen + normal starten (kein exit(1))
  - atexit.register(_remove_lock): lock wird auch bei unerwarteten Exceptions geloescht
  - signal.SIGTERM + SIGHUP Handler: lock vor exit raeumen
  - Ergebnis: Bot selbst loest stale lock auf

Ebene 2 — watchdog.py (cleanup_stale_lock):
  - Vor jedem systemctl restart: prueft ob PID in bot.lock lebt
  - Wenn tot: lock entfernen BEVOR restart getriggert wird
  - Ergebnis: Watchdog verursacht keine neuen Lock-Loops mehr

Ebene 3 — systemd ExecStartPre:
  - Shell-Check vor jedem Start: lock existiert + PID tot -> rm -f bot.lock
  - Unabhaengig von Python-Code, greift auf OS-Ebene
  - Ergebnis: selbst wenn Ebene 1+2 versagen, startet systemd sauber

Nebenfix: StartLimitBurst 3->10 (verhindert permanent-failed bei schnellen Restarts)

Test-Protokoll:
  kill -9 <BOT_PID>  -> systemd erkennt SIGKILL -> ExecStartPre entfernt stale lock
  -> Bot startet sauber in <26s (15s RestartSec + Startup-Zeit)
  Log: "[systemd] Stale lock removed (PID X tot)"

---

## P023 -- Defensive Config Deployment (2026-04-18, nach $137 Verlust)

**Status:** DEPLOYED

**Kontext:**
Bot hatte COPY_SIZE_MULTIPLIER=0.15 und keine Positions-Limits.
Nach $137 Verlust durch aggressive Orders auf illiquide Maerkte (Kolumbien, Ecuador, etc.)
wurde defensive Config deployed.

**Aenderungen in .env:**
- COPY_SIZE_MULTIPLIER: 0.15 -> 0.05 (3x kleinere Orders)
- MAX_POSITIONS_TOTAL=15 (max gleichzeitig offene Positionen)
- MIN_MARKT_VOLUMEN=50000 (keine Maerkte unter $50k Volumen)
- CATEGORY_BLACKLIST=col1-,por-,ecu-,arg-b- (Kolumbien1, Portugal, Ecuador, Argentinien B)
- WALLET_WEIGHTS=JSON mit per-Wallet Multiplikatoren (env-Override)

**Code-Aenderungen (strategies/copy_trading.py):**
- _load_env_weights() + _apply_env_weights(): merged WALLET_WEIGHTS aus .env
- _process_signal(): 3 neue Checks vor Order-Erstellung:
  0a. CATEGORY_BLACKLIST gegen market_slug
  0b. MIN_MARKT_VOLUMEN gegen signal.market_volume_usd
  0c. MAX_POSITIONS_TOTAL via get_open_positions_count Callback
- Skip-Log: "SKIP: reason=X (slug/wallet)"

**Warum kein harter Revert:** Code-Aenderung minimal, env-Werte leicht anpassbar.

---

## P024 -- Cloudflare Quick Tunnel Setup (trycloudflare.com)

**Status:** AKTIV | systemd kongtrade-tunnel.service

**Problem:** Dashboard (Port 5000) war nur via SSH-Tunnel erreichbar.

**Setup:**
- cloudflared war bereits als arm64-Binary installiert (2026.3.0)
- Kein Account/Login noetig fuer trycloudflare.com Quick Tunnel
- systemd Service: /etc/systemd/system/kongtrade-tunnel.service
  ExecStart: cloudflared tunnel --url http://localhost:5000

**Wichtig - LIMITATION:**
URL aendert sich bei jedem Service-Neustart (zufaellige Subdomain).
Aktuelle URL: siehe journalctl -u kongtrade-tunnel | grep trycloudflare

**Upgrade-Pfad (spaeter):**
Named Tunnel mit fester Subdomain benoetigt:
1. cloudflared tunnel login (Browser-Auth)
2. cloudflared tunnel create kongtrade
3. DNS CNAME bei eigener Domain


---

## P025 -- Dashboard-URL aendert sich bei Tunnel-Restart -> Telegram-Watcher

**Status:** DEPLOYED | kongtrade-tunnel-watcher.timer (alle 5min)

**Problem:**
trycloudflare.com Quick-Tunnel generiert bei jedem Neustart eine neue zufaellige URL.
Brrudi wusste nicht welche URL aktuell gueltig ist.

**Loesung:**
tunnel_watcher.py prueft alle 5min via journalctl ob URL sich geaendert hat.
Bei Aenderung:
  1. Neue URL in .current_tunnel_url speichern
  2. Telegram-Alert an ersten Chat aus TELEGRAM_CHAT_IDS
  3. STATUS.md bekommt beim naechsten Push die neue URL

**Files:**
- /root/KongTradeBot/scripts/tunnel_watcher.py
- /root/KongTradeBot/.current_tunnel_url (aktuelle URL)
- /root/KongTradeBot/.last_tunnel_url (letzte bekannte URL fuer Change-Detection)
- /etc/systemd/system/kongtrade-tunnel-watcher.service + .timer

**Langfristige Loesung:**
Named Tunnel mit eigener Domain -> feste URL ohne Watcher noetig.


---

## P026 -- Watchdog-Heartbeat STALE in STATUS.md (2026-04-18)

**Status:** BEHOBEN

**Symptom:** STATUS.md zeigte "STALE 1175s alt" fuer Watchdog-Heartbeat.

**Root-Causes (2 Probleme):**

1. generate_status.py Schwellwert 120s zu eng:
   heartbeat_loop() in main.py schreibt alle 300s -> Heartbeat bis zu 300s alt.
   Mit Schwellwert 120s -> fast immer "WARNUNG", nach laengerer Pause -> "STALE".
   Fix: Schwellwerte auf 360s (OK) / 700s (WARN) angepasst.

2. systemctl-native Timer-Info als zusaetzliche Quelle:
   get_watchdog_timer_info() liest LastTriggerUSec aus systemctl show.
   Parsing: systemd liefert lesbares Datum ("Sat 2026-04-18 08:35:27 UTC"),
   nicht Unix-Timestamp -> datetime.strptime mit regex.

**Kritischer Nebenbefund (P026b) — MIN_MARKT_VOLUMEN Bug:**
   copy_trading.py skippte ALLE Signale weil market_volume_usd=0 (unbekannt) < 50000.
   WalletMonitor befuellt market_volume_usd nicht -> bleibt 0 (kein None).
   Fix: Bedingung auf `vol > 0 and vol < MIN_MARKT_VOLUMEN_USD` geaendert.
   Betroffen: alle Signale zwischen 08:15 und 08:34 UTC wurden faelschlicherweise geskippt.

**Files geaendert:**
- /root/KongTradeBot/scripts/generate_status.py (Schwellwerte + Timer-Info)
- /root/KongTradeBot/strategies/copy_trading.py (vol>0 Guard)


## P028 — GitHub Account Suspension (2026-04-18)

**Problem:** GitHub-Account  wurde automatisch gesperrt.

**Ursache:** Neuer Account + 2 Repos erstellt + Auto-Push alle 5 Minuten → Bot-Detection ausgelöst.

**Sofortmaßnahmen:**
- Auto-Push-Timer () sofort gestoppt
- Lokale Backups der Template-Files erstellt
- Template-Arbeit lokal abgeschlossen ()

**Status:** Warte auf GitHub Support-Antwort (support.github.com)

**Lesson Learned:**
- Neue GitHub-Accounts langsam warm-laufen lassen (kein sofortiger Auto-Push)
- Mindestens 1 Woche manuell pushen bevor Automation aktiviert wird
- Für Bot-Accounts: Personal Account verwenden und Repo unter Org anlegen

---

## P029 — Balance-Check 400: assetAddress invalid hex address (T-010)
**Problem:** Bot wirft alle ~3 Minuten `PolyApiException[status_code=400, 'GetBalanceAndAllowance invalid params: assetAddress invalid hex address ']`. Portfolio-Wert zeigt $0.00 im Dashboard.
**Root Cause:** `_verify_order_onchain()` ruft `get_balance_allowance(asset_type="CONDITIONAL", token_id=token_id)` auf. `token_id` ist leer (`""`) bei Positionen die aus dem Recovery-Flow (`recover_stale_positions`) oder aus `bot_state.json` restauriert wurden, wenn die REST-API kein `token_id`/`asset_id`-Feld zurückgibt. Die ~3-Minuten-Periode entspricht dem Watchdog-`RESTART_COOLDOWN=180`.
**Fix (deployed 2026-04-18):**
1. `execution_engine.py _verify_order_onchain`: Guard vor API-Call — leeres `token_id` → WARNING + `return False` statt 400-Fehler.
2. `main.py restore_positions`: Filtert Positionen mit leerem `token_id` vor Restore (Stale-Cleanup).
3. `main.py recover_stale_positions`: Filtert Orders ohne `token_id` vor Eintrag in `_pending_data`.
**Status:** DEPLOYED — verifiziert via `/api/logs` ca. 09:35 UTC.

---

## P030 — Inkonsistente Polymarket redeemable-Feldnamen

**Status:** BEHOBEN (2026-04-18)

**Problem:**
Polymarket Data-API liefert den redeemable-Status unter verschiedenen Feldnamen
je nach Endpunkt und API-Version:
- `redeemable` (aeltere Endpunkte)
- `isRedeemable` (neuere Endpunkte, camelCase)
- `is_redeemable` (snake_case Variante, selten)

`claim_all.py` pruefte nur `redeemable` und `isRedeemable` → `is_redeemable` Positionen
wurden nicht geclaimt. `dashboard.py` hatte dasselbe Problem bei der unclaimed-Summe.

**Fix:**
`is_claimable()` Helper-Funktion in `claim_all.py`:
```python
def is_claimable(pos: dict) -> bool:
    return any(pos.get(k) for k in ("redeemable", "isRedeemable", "is_redeemable"))
```
Alle redeemable-Checks in `claim_all.py` und `dashboard.py` nutzen jetzt diese Funktion.

**Bonus:** `AUTO_CLAIM_INTERVAL_S` env-Variable (default 300s / 5min statt 1800s / 30min).

**Status:** DEPLOYED (2026-04-18)

---

## P031 — Server-Remote war auf gesperrtem Account

**Status:** BEHOBEN (2026-04-18)

**Problem:**
Alter GitHub-Account "KongTradeBot" wurde gesperrt. Server-Code lag
lokal als /root/KongTradeBot auf Hetzner mit Remote auf
github.com/KongTradeBot/KongTradeBot.git — kein Push/Pull mehr möglich.

**Symptom:**
- git pull: 403
- Auto-Deploy unmöglich
- Neueste Server-Fixes (scripts/, fill_tracker.py, watchdog.py)
  nie committed — Server war einzige Quelle

**Root-Cause:**
Account-Sperrung unabhängig vom Repo, Account-Reaktivierung nicht planbar.

**Fix:**
1. Neues privates Source-Repo onur-tech/KongTradeBot-src angelegt
2. Server-State konsolidiert: Backup /root/kongtrade-backup-20260418/
3. .gitignore erweitert um Runtime-Files (bot.lock, heartbeat.txt,
   metrics.db, STATUS.md) und Backup-Files (*.bak, *.bak_night, *.server_backup)
4. 13 Files commited (857d82b), inklusive scripts/-Ordner und
   fill_tracker.py die vorher nie in Git waren
5. Remote umgebogen: origin → origin-old, neu origin =
   onur-tech/KongTradeBot-src
6. 217 Objects / 227 KB gepusht
7. Windows-Working-Tree per git reset --hard origin/main synchronisiert

**Lesson:**
Single-Account-Abhängigkeiten für kritische Repos vermeiden.
onur-tech (personal account) ist stabiler wegen weniger Spam-/Automation-Flags.

---

## P033 — Steuer-Archiv: tx_hash fehlte in CSV-Export

**Status:** BEHOBEN (2026-04-18)

**Problem:**
`log_trade()` hat `tx_hash` als Parameter akzeptiert, aber `main.py`
hat diesen Parameter nie befuellt — er blieb stets leer.
Im CSV-Export fehlte die TX-Hash-Spalte komplett.

**Fix:**
- `main.py`: nach `result.success`, `_tx_hash = f"pending_{result.order_id}"`
  an `log_trade(tx_hash=_tx_hash)` uebergeben.
- `tax_archive.py`: `"TX-Hash"` Spalte in deutschen CSV-Export eingefuegt.

---

## P034 — Silent Auto-Claim-Errors: kein Telegram-Alert bei Fehlern

**Status:** BEHOBEN (2026-04-18)

**Fix:**
- `redeem_position()` gibt jetzt `(bool, str)` zurueck.
- `claim_loop()` sendet rate-limitierten Telegram-Alert pro fehlgeschlagener Position.
- `CLAIM_ERROR_ALERT_COOLDOWN_S=3600` (env-konfigurierbar).

---

## P035 — Wöchentlicher Auto-Tax-Export

**Status:** IMPLEMENTIERT (2026-04-18)

**Problem:** `export_tax_csv()` war nur manuell aufrufbar.

**Fix:**
- `scripts/weekly_tax_export.py` + systemd Timer (Freitag 23:55 Berlin)
- Exports nach `/root/KongTradeBot/exports/tax_YYYY_KWWW.csv` + `blockpit_YYYY_KWWW.csv`
- Telegram-Summary an alle Chat-IDs
- Download: `scp root@89.167.29.183:/root/KongTradeBot/exports/*.csv .`

---

## P036 — OAuth-Popup trotz embedded PAT — GCM intercepted github.com

**Status:** BEHOBEN (2026-04-18)

GCM (`credential.helper=manager`) ist systemweit gesetzt und fängt HTTPS-Requests
an github.com ab — selbst wenn PAT in der Remote-URL eingebettet ist.
Kein `~/.gitconfig` existierte zur Überschreibung.

**Fix:** `git config --global credential.https://github.com.helper ""`

Leerer String in User-Config überschreibt System-Helper für github.com-URLs.

---

## P037 — Frankfurter API URL-Migration (.app → .dev/v1), Hetzner-IP-Block

**Status:** BEHOBEN (2026-04-18)

`api.frankfurter.app` gibt 403 von Hetzner-Helsinki-IP → EUR/USD fällt auf Fallback
0.92 (aktueller Kurs ≈ 0.88) → systematische Steuer-Verzerrung.

**Fix (3 Ebenen):**
1. Primary: `https://api.frankfurter.dev/v1/` — gleiche ECB-Quelle, neue Domain
2. Secondary: ECB direkt `https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml`
3. Tertiary: Hardcodierter Fallback 0.92

**Betroffen:** `utils/tax_archive.py` — `_fetch_eur_usd_rates()`

---

## P038 — "Schließt in"-Spalte zeigt "—" für alle offenen Positionen

**Status:** BEHOBEN (2026-04-18)

Polymarket Data API liefert `endDate` als reines Datum `"2026-04-30"` (kein Timezone-Suffix).
`datetime.fromisoformat("2026-04-30")` → naive datetime. Subtraktion naive - aware →
`TypeError` → `except Exception: return "—"` — komplett silent.

**Fix:** `if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)` in `_closes_in_label()`.

---

## P039 — Wallet-Scout Decay-Detection via SQLite-Zeitreihe

**Status:** IMPLEMENTIERT (2026-04-18)

`wallet_scout.py` hatte keine persistente Geschichte → keine Trend-Erkennung.

**Fix:**
- SQLite DB `data/wallet_scout.db` (Tabelle `wallet_scout_daily`)
- PRIMARY KEY (scan_date, wallet_address, source) → idempotent
- `utils/wallet_trends.py`: get_wallet_trend, get_decay_candidates, get_rising_stars
- `scripts/weekly_wallet_report.py` + systemd Timer (So 20:00 Berlin)
- Dashboard `/api/wallet_trends` Endpoint

Erste echte Trends nach 7-14 Scan-Tagen.

---

## P040 — Telegram-Spam: Bot-Neustart-Alerts bei jedem Watchdog-Zyklus

**Status:** ✅ BEHOBEN (18.04.2026)

Jeder Watchdog-Restart schickte "✅ neu gestartet" an Telegram. Startup-Alert kam
bei jedem Neustart ohne Throttle.

**Fix:**
- `watchdog.py`: Erfolgreiche Restart-Alerts entfernt. `HEARTBEAT_MAX_AGE` 180 → 600s.
- `telegram_bot.py`: `_is_muted()` / `_MUTE_FILE`, `_is_startup_allowed()` 30min Cooldown,
  `send(urgent=False)` respektiert Mute, Inline-Menu 8 Buttons, `_TG_MIN_SIZE` 5→2 USD.
- `scripts/daily_digest.py` + systemd Timer 22:00 Berlin.

---

## P041 — Telegram-Callbacks lasen local state statt API → immer $0 / 0 Positionen

**Status:** ✅ BEHOBEN (18.04.2026)

`/menu → Portfolio` zeigte "0 Positionen | $0.00" obwohl 18 Positionen mit $213 Value existierten.
`_handle_menu_callback()` las aus `bot_state.json` (leer nach Restart).

**Fix:** `_fetch_dashboard(endpoint)` → `GET http://localhost:5000{endpoint}`.
Alle 6 Callbacks auf Dashboard-API umgestellt. Fehler-Fallback: "Dashboard nicht erreichbar".

---

## P042 — Bot-Restart-Schleife alle 3 Min (HEARTBEAT_MAX_AGE < heartbeat_loop interval)

**Status:** ✅ BEHOBEN (18.04.2026, via aeec617)

`heartbeat_loop(interval=300)` schreibt alle 300s. `HEARTBEAT_MAX_AGE=180`.
180 < 300 → Watchdog restartete bot jeden Cycle. Genau 3-Min-Abstände.

**Fix:** `HEARTBEAT_MAX_AGE`: 180 → 600 (> 300). **Invariante: MAX_AGE > interval immer!**

---

## P043 — Persistent Reply Keyboard (kein python-telegram-bot nötig)

**Status:** ✅ IMPLEMENTIERT (18.04.2026)

Telegram `ReplyKeyboardMarkup` als raw JSON ohne Library:
`{"keyboard": [...], "resize_keyboard": true, "is_persistent": true}`
- `/start` → Begrüßung + Keyboard (Brrudi einmalig `/start` nach Deploy)
- Text-Button-Klicks → normale Nachrichten → `_BUTTON_ACTION_MAP` → `_handle_menu_callback()`

---

## P044 — Drei Detail-Bugs nach Callback-API-Umstieg (18.04.2026)

**Status:** ✅ BEHOBEN (18.04.2026)

**Bug A:** `p.get("size_usdc")` → Feld nicht in `/api/portfolio`. Fix: `p.get("traded", 0)`.

**Bug B:** `msg_status(orders=s["orders_created"])` → Parameter heißt `orders_sent`. TypeError → silent fail.
Fix: `orders=` → `orders_sent=` (beide Call-Sites in main.py).

**Bug C:** `today_pnl` = nur RESOLVED Trades → immer 0 wenn kein Markt heute resolved.
Fix: Midnight-Snapshot `_get_midnight_snapshot()` in `dashboard.py`. `/api/portfolio` gibt
`today_pnl_portfolio = total_value - snapshot_value`. Snapshots >7 Tage auto-gelöscht.

---

## P045 — Drei Telegram-Bugs nach Live-Test (18.04.2026)

**Status:** ✅ BEHOBEN (18.04.2026, via 26a36c1)

**Bug A:** P044-Fix hatte `orders=` → `orders_sent=` nur in `status_reporter` (line 441) behoben.
`send_status_now()` (line 727, aufgerufen vom Status-Button) hatte noch `orders=`. Fix dort auch.

**Bug B:** Multi-Signal Spam — gleiche Wallet+Markt-Kombi mehrfach in 15 Min.
Fix: Dedup in `on_multi_signal` (main.py): Key = `f"{market}|{outcome}|{sorted_wallets}"`,
15-Min-Cooldown via `.multi_signal_last_alert.json`, 24h-Cleanup.

**Bug C:** Exceptions in `_handle_menu_callback` → `poll_commands except: pass` → kein Alert.
Fix: `_safe_callback(name, handler, *args)` fängt Exception, sendet Telegram-Alert, gibt `"⚠️"` zurück.

---

## P046 — Exit-Strategie Design Decisions (18.04.2026)

**Status:** ✅ IMPLEMENTIERT (18.04.2026) — EXIT_DRY_RUN=true, Observation läuft

### Warum 40/40/15/5 Staffel?
Prevayo-Research + Laika AI Backtests für binäre Prediction-Markets.
- 40% Sicherheits-Take bei +30%: Kapitalsicherung vor Reversal-Risk
- Zweites 40% bei +60%: Compound-Effekt bei Gewinnern
- 15% bei +100%: Runner-Anteil (5%) bis Resolution
- Boost-Staffel (3+ Wallets): 50/90/150% wegen höherer Conviction

### Warum 12¢ Trail-Aktivierung (absolut)?
Binäre Märkte 0..1 USDC — prozentuale Trails scheitern bei billigen/teuren Tokens.
12¢ = sinnvoller Gewinn bei allen Preisniveaus.
Trail-Distance: 7¢ (≥$50k Vol) vs 10¢ (thin) — breiter bei illiquidem Orderbook.

### Warum Whale-Exit höchste Priorität?
Smart-Money-Signal > Zahlen. Wallet verkauft = Information, nicht nur Statistik.
Sofort 100% raus, kein partial-exit.

### Warum DRY-RUN-Default?
(1) Validierung erste 24h. (2) SELL-Slippage-Dynamics noch unbekannt. (3) Race-Condition
exit_loop + WalletMonitor + FillTracker auf `engine.open_positions` im DRY-RUN harmlos.

### Bekannte Edge-Cases
- `wallet_monitor.get_recent_sells` noch nicht implementiert → Whale-Exit immer skip
- `market_volumes` aktuell immer `{}` → immer thin-trail (konservativ)
- Partial-Fill bei SELL: `remaining_shares` tracked, aber `pos.shares` erst bei Live-Exit updated

---

## P047 — OpenClaw-Evaluation: Warum nicht integrieren

**Status:** ENTSCHIEDEN (18.04.2026) — Weg A: Konzepte klauen, Plattform nicht nutzen

OpenClaw (Peter Steinberger), 329k GitHub-Stars. $116k/Tag-Narrativ = Arbitrage mit
riesigem Kapital. Reddit-Test: $42 mit OpenClaw-Setup. Edge halbiert sich 3-6 Monate.

**Eigene Architektur-Analyse:** Watcher, Enricher, Notifier, Executor — 80% bereits vorhanden.
Fehlt nur: zentralisiertes Memory-System.

**Entscheidung:** Konzepte übernehmen (Skill-Manifeste, Dry-Run-First, Structured Signals,
Guarded Execution). Plattform nicht nutzen.

**Grund:** Seit 4. April 2026 Anthropic-Sperre für Subscription-Zugriff aus Third-Party-Tools
→ separater API-Key erforderlich, Zusatzkosten, kein Vorteil zu eigenem Stack.

---

## P048 — Latenz-Argument-Korrektur (iPhone-Chat-Insight)

**Status:** VERSTANDEN (18.04.2026) — Strategie angepasst

**Fehler-Annahme (heute):** "4-11 Min Lag = Edge für uns."
**Richtig:** Lag relevant für HFT-Arbitrage (5-Min-BTC-Märkte), NICHT für Copy-Trading
mit Stunden-/Wochen-Haltedauern.

**Echte Edge-Quellen:**
1. **Wallet-Kuration als Moat:** Weniger bekannte, konsistent profitable Wallets;
   Kategorie-Spezialisten; Brier-Score-Rebalancing
2. **Filter-Edge statt Speed-Edge:** Claude filtert emotionale/Fun/Hedge-Trades raus
3. **Multi-Wallet-Confluence:** 3+ unabhängige Top-Wallets, gleiche Seite, 48h = starkes Signal
4. **Duration-Aware Entry:** Später zu besseren Preisen wenn Whale-Impact abgeklungen

---

## P049 — Copy-Trading-Realitäts-Check (Reddit-Research)

**Status:** VERSTANDEN (18.04.2026) — Risiken im System adressieren

**Reddit 4-Monats-Test ($9.200 Kapital):** Nur 1 von 7 Bots profitabel.
Copy-Trading 8 Wochen → 5 straight losses. Edge-Verfall 60% in 12 Wochen.
Slippage 3-5¢/Trade. 99.49% aller Polymarket-Wallets nie $1.000+ Profit.

**Decoy-Trading real:** Polymarket dokumentierte Sept 2025 "Copytrade Wars" —
Top-Whales platzieren Decoy-Trades (kaufen → warten auf Copier → in Spike verkaufen).

**68%-Win-Rate-Trugschluss:** "Liegt nicht am Signal, sondern an ALLEM dazwischen."
5 Execution-Bugs: Ghost Trades, Fake P&L, Market-Order in thin Orderbook,
Resolution-Window-Race, Balance-Tracking statt Preis als Ground Truth.

**Was uns schützt:** Fill-Verifikation on-chain, Multi-RPC-Fallback, Defensive Config 0.05x,
Auto-Claim via blockchain-state, Wallet-Scout mit Trend-Analyse.

**Was noch fehlt:** Slippage-Tracking (T-I11), Decoy-Detection (T-I08),
Exit-Strategie ✅ erledigt (T-D52).

---

## P050 — Sentiment-Bot-Architektur-Plan

**Status:** DESIGN FINAL (18.04.2026) — Implementation geplant als T-I07

**Problem:** 4-11 Min Lag zwischen News-Signal und Polymarket-Reprice dokumentiert.

**API-Kosten-Research:**
- Twitter Basic: $100/Monat OHNE Streaming (unbrauchbar)
- Twitter Pro: $5.000/Monat (zu teuer)
- TweetStream.io: $139-349/Monat (Polymarket-Detection built-in)
- Free Alternative: RSS + Reddit API + Telegram Public Channels

**Wichtigster LLM-Insight:** LLMs schlecht bei Probability-Estimation, sehr gut bei
Classification. Claude fragen: "Bullish oder bearish für Position X?" statt "Wahrscheinlichkeit?"

**Referenz-Projekte:** foxchain99/polymarket-sentiment-bot (open source),
brodyautomates/polymarket-pipeline (Claude-Klassifikation)

**Phased Approach:**
- Phase 0.5 (T-I07): Free-Tier RSS+Reddit+Telegram, NUR Logging+Info-Alerts, 2 Wochen Validierung
- Phase 1: Alert-Only mit mehr Quellen (wenn >55% Accuracy)
- Phase 2: Semi-Auto high-confidence, small sizes
- Phase 3: Voll integriert

**Risiken:** Fake-News (→ 2-Source-Confirmation), Bot-Konkurrenz (→ Nischen-Märkte <$500k),
API-Kosten (→ Free-Tier-Start).

---

## P051 — Manifold als Paper-Trading-Plattform

**Status:** EVALUATION GEPLANT (18.04.2026) — T-I09

Manifold.markets: Mana (virtuelle Währung, kostenlos), offene API, realistische
Preis-Dynamik durch echte User.

**vs. PolySimulator:** PolySimulator = nur Polymarket-Preise ohne Market-Dynamik.
Manifold = echtes Orderbook, echte Preisbildung.

**Plan:** `utils/manifold_shadow.py` mit identischer Copy-Logik wie KongTradeBot.
4-6 Wochen Kalibrierung. Metriken: Hit-Rate, Brier-Score, ROI.
Strategie-Änderungen erst Manifold-Test → dann Polymarket-Deployment.

**Einschränkung:** Andere User-Basis (kleinere Märkte, weniger Whales). Execution-Logik
ähnlich genug für Validierung der Strategy-Layer.

---

## P052 — Grok API als Twitter-Alternative (19.04.2026)

**Status:** VERSTANDEN — Paradigma-Wechsel für Sentiment-Strategie

**Kontext:** Sentiment-Bot-Plan basierte auf Twitter API Basic
($100/Monat, ohne Streaming unbrauchbar) oder TweetStream.io ($139–349/Monat).

**Update:** Grok 4.1 Fast bietet native X/Twitter-Integration via API-Tool:
- $0.20 / $0.50 pro 1M Tokens (Input/Output)
- 2M Token Context-Window
- Echtzeit-X-Search nativ
- Kein separater Twitter-API-Account nötig

**Kostenrechnung typischer Einsatz:**
- 100 Market-Queries/Tag × 5k Tokens avg = 500k Tokens/Tag
- Monatlich: 15M Tokens = ~$3–15/Monat (statt $139–5000)

**Implikation:**
- T-I07 Sentiment-Bot Phase 0.5 umgeplant: Grok statt RSS als primäre Quelle
- Twitter-API-Pro aus Planung gestrichen
- T-S01: Grok-Integration als universelles Modul für alle zukünftigen Bots

**Architektur-Update:** Grok-Modul wird so gebaut, dass es von ALLEN
zukünftigen Bots genutzt werden kann.

---

## P053 — Skill-System-Audit (19.04.2026)

**Status:** ERLEDIGT — SKILL.md erstellt mit Investment-Frameworks (Punkte 10–12)

**Kontext:** Frage ob Investment-Prinzipien (Dalio, Taleb, Marks) durch
Umstellung auf GitHub-Links "verloren gegangen" sind.

**Befund:** User-Skills sind systemweit in `/mnt/skills/user/` verfügbar
(4 Skills: dalio, marks, taleb, crypto-analyst), aber Chat-Claude greift
nicht automatisch darauf zu wenn Projekt-SKILL.md nur GitHub-Links enthält.

**Lösung:** SKILL.md neu erstellt mit Pflicht-Verweisen auf die 4 User-Skills
(Punkte 10–12). Damit werden Investment-Frameworks bei jeder Session aktiv.

**Implikation für Multi-Asset-Vision:** Bei neuen Asset-Klassen werden
spezialisierte Skills gebaut. Ein generisches "Crypto-Analyst"-Skill reicht
nicht für Funding-Arb oder DEX-Whale-Following.

**Lesson:** Skill-Erweiterungen müssen bei Projekt-Pivots explizit mitgepflegt werden.

---

## P054 — Peer-Modell für Kollaboration (19.04.2026)

**Status:** ENTSCHIEDEN — Peer, nicht Chef

**Kontext:** 4 Personen (Brrudi, Alex, Tunay, Dietmar) bauen parallel ähnliche
Systeme. Frage: Wie koordinieren ohne Hierarchie?

**Entscheidung:**
- Brrudi initiiert Infrastruktur + GUIDELINES
- Alle 4 sind gleichberechtigte Entscheider
- Opt-In statt Opt-Out
- Autonomie vor Konformität

**Implikation:**
- Keine Master-Slave-Architektur
- Kein zentraler Bot-Controller
- Shared Services sind Utilities, nicht Kommando
- Wenn Alex/Tunay/Dietmar nicht teilnehmen wollen: OK

**Lesson:** Bei Familie/Freunden nie Chef spielen. Strukturen so bauen
dass sie OHNE dich weiter funktionieren.

---

## P055 — 138-Restart-Loop Analyse (19.04.2026)

**Status:** ✅ FIXED via B2 (Commit 2fffe16)

**Symptom:** Am 18.04.2026 138 Watchdog-Restarts in 9 Stunden.

**Root Cause — 2-Schichten:**

**Schicht 1 (06:50–16:18 UTC 18.04.):**
- Alte Bot-Session hielt `bot.lock`
- Session blockiert wegen CLOB-Allowance erschöpft ($4.63)
- Watchdog/systemd sahen "failed" und restarteten blind
- Jeder neue Prozess erkannte Lock und beendete sich sofort
- Fail-Loop: Lock da → Exit → Watchdog restart → Lock da → Exit

**Schicht 2 (seit 16:18 UTC 18.04.):**
- Neue stabile Session läuft
- ABER: `sync_positions_from_polymarket()` lädt $342.46 beim Start
- `MAX_PORTFOLIO_PCT=50%` × $629 = $314.53
- Alle Orders silent blockiert im `_safe_call`-Wrapper
- 1065 CopyOrders erstellt, 0 ausgeführt

**Fixes:**
- A1: Budget-Cap blockiert jetzt sichtbar (nicht mehr silent)
- A3: `error_handler.py` ersetzt `_safe_call`
- B2: Watchdog prüft PID + Heartbeat statt blind zu restarten
- Manuell: `MAX_PORTFOLIO_PCT` auf 60% erhöht

**Lessons:**
1. Silent-Fails verstecken kritische Bugs — IMMER sichtbar loggen
2. Watchdog braucht echte Gesundheitsprüfung, nicht nur systemctl-Status
3. Budget-Cap + Lock-File + Watchdog-Trio muss als System gedacht werden

---

## P056 — Kategorie-Erkennung Bug (19.04.2026)

**Status:** ✅ FIXED via A2 (Commit e9f3cb5)

**Symptom:** 79 von 90 Trades im Archiv als "Sonstiges" kategorisiert, obwohl sie
US-Sport (NBA, MLB, NHL) waren.

**Root Cause:** Pattern-Matching nutzte `"vs "` (mit Leerzeichen). Polymarket-Format
ist aber `"vs."` (mit Punkt). Kein Match möglich.

**Fix:**
- 5 Kategorien: `sport_us`, `soccer`, `tennis`, `geopolitik`, `sonstiges`
- Pattern erweitert um US-Sport-Liga-Namen + O/U + Spread
- Backfill: 79 Trades neu kategorisiert
- 44 Unit-Tests

**Neue Verteilung nach Backfill:**
- sport_us: 53 (war 0)
- geopolitik: 14 (war 11)
- soccer: 15 (war 0)
- tennis: 8 (war 0)
- sonstiges: 0 (war 71)

**Lesson:** Pattern-Matching immer mit echten Daten validieren, nicht mit
konstruierten Beispielen.

---

## P057 — Dashboard CLAIM-Button UX-Bug (19.04.2026)

**Status:** ✅ FIXED (Commit cdd0fb5)

**Symptom:** CLAIM-Button war bei allen 12 resolved-verlorenen Positionen
aktiv und klickbar, zeigte aber "$0.00" an. Brrudi klickte mehrmals in
Erwartung "Geld zurück" — nichts passierte.

**Root Cause:** Rendering-Logik in `dashboard.html` prüfte nur `redeemable=true`,
nicht `current_value > 0`. Resolved-verlorene Positionen sind technisch
`redeemable` auf Polymarket-Seite, aber mit Auszahlung $0.

**Fix:** Conditional Rendering mit zusätzlicher Wert-Prüfung (Zeile 923):
- `redeemable && value > 0.01` → CLAIM $X.XX Button (grün, aktiv)
- `redeemable && value <= 0.01` → `<span class="status-lost">VERLOREN</span>` (rot)
- nicht redeemable → `—` (wie bisher)

CSS ergänzt: `.status-lost{color:#ff4444;font-size:0.85em;font-weight:bold;font-family:monospace}`

**Lesson:** UI-States immer mit allen Kombinationen durchspielen.
"redeemable" heißt nicht automatisch "claimable mit Wert > 0".
Claim-Chain auf Polymarket: `resolved → redeemable → payout (kann $0 sein)`

## P060 — Auto-Doc-Pipeline mit 3-Ebenen-Struktur (2026-04-19)
**Status:** FIXED via `85e6e33`
**Scope:** automation

**Root Cause:** Manuelle Doku-Sync kostete 30+ Min pro Bug-Fix-Runde.

**Impact:** Bei heutiger Power-Session (37 Commits) waere Doku-Overhead

**Fix:** 3-Ebenen-Automatik deployed:

**Lesson:** Doku-Aufwand eliminieren durch Struktur am Source (Commit-Message)

## P061 — Per-Wallet-Performance-Report mit Kategorie- und Zeitfenster-Aufschlüsselung (2026-04-19)
**Status:** FIXED via `8689c4e`
**Scope:** analytics

**Root Cause:** Keine Sichtbarkeit in individuelle Wallet-Performance — kein Ranking nach Hit-Rate/ROI, keine Erkennung von underperformenden Wallets.

**Impact:** Blind-Copy aller 15 Wallets ohne Qualitätsdifferenzierung.

**Fix:** wallet_performance.py (compute_wallet_stats, compute_by_category, compute_by_timeframe, compute_all_wallets), dashboard /api/wallet_performance, CLI wallet_report.py, weekly_performance_report.py (freitags 23:55), 13 Tests.

**Lesson:** ROI nur berechenbar wenn min. 1 Trade resolved ist — bei all-pending Wallets resolved_invested≈0 führt zu Division-by-near-Zero. Fix: roi_pct=None wenn (wins+losses)==0, nicht wenn invested>0.

