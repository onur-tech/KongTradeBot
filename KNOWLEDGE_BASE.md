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

## P029 — T-010: Leere token_id triggert API 400 alle ~3min

**Status:** BEHOBEN (2026-04-18)

**Problem:** Bot loggte alle ~3 Minuten:
`PolyApiException[status_code=400, 'GetBalanceAndAllowance invalid params: assetAddress invalid hex address']`

**Root-Cause:**
`_verify_order_onchain()` wurde mit leerem `token_id=""` aufgerufen.
Ursache: `recover_stale_positions()` und `restore_positions()` injizierten Positionen
aus REST-API-Antworten die kein `token_id`/`asset_id` enthielten.
Watchdog-RestartCooldown 180s erklaert das ~3-Minuten-Intervall der Fehler.

**Fix (3 Ebenen):**
1. `core/execution_engine.py` — Guard in `_verify_order_onchain()`:
   Wenn `token_id` leer/`0x`/`0x0` → `return False` ohne API-Call
2. `main.py restore_positions()` — Filter vor Loop:
   Positionen ohne gueltigen `token_id` werden beim Start uebersprungen
3. `main.py recover_stale_positions()` — Guard pro Order:
   Orders ohne `token_id` → `continue` (kein Inject in `_pending_data`)

**Status:** DEPLOYED (commit feat/T-010+T-022, 2026-04-18)

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

## P032 — Micro-Trade-Noise: 80% aller Trades unter $1, kaum Edge

**Status:** BEHOBEN (2026-04-18)

**Problem:**
Mit COPY_SIZE_MULTIPLIER=0.05 und MIN_TRADE_SIZE_USD=0.01 wurden
Whale-Trades ab $0.20 kopiert. Ergebnis: ~80% aller generierten
Trades hatten eine Groesse unter $1.00 — kaum Edge, hohe Gebueehren-
Belastung relativ zum Trade-Volumen, viele False-Positive-Signale
(Whale-Tests, Positions-Anpassungen, Liquiditaets-Spielereien).

**Root-Cause (2 Ebenen):**
1. Whale-Signal-Ebene: Kleine Whale-Trades ($1-$5) sind oft keine
   echten Signale (Testen, Rebalancing) — sie sollten gar nicht erst
   als Signal verarbeitet werden.
2. Output-Ebene: Nach Multiplikator-Anwendung (0.05x) entstehen
   noch kleinere Trades (z.B. $10 Whale → $0.50 Copy).

**Fix:**
- `MIN_WHALE_TRADE_SIZE_USD=5.00` (neu): Filter in wallet_monitor.py
  direkt nach size_usdc-Extraktion. Whale-Trades unter $5 → kein Signal.
  Log: "Whale-Trade geskipped: $X.XX < MIN_WHALE $5.00 [wallet]"
- `MIN_TRADE_SIZE_USD=0.50` (angehoben von 0.01): Filter in
  risk_manager.py. Berechnete Copy-Groesse unter $0.50 → kein Trade.
  Log: "Micro-Trade geskipped: $X.XX < MIN_TRADE_SIZE $0.50"
- Beide Werte via .env konfigurierbar fuer spaeteres Tuning.

---

## P033 — Steuer-Archiv: tx_hash fehlte in CSV-Export

**Status:** BEHOBEN (2026-04-18)

**Problem:**
`log_trade()` hat `tx_hash` als Parameter akzeptiert, aber `main.py`
hat diesen Parameter nie befuellt — er blieb stets leer string "".
Im CSV-Export fehlte die TX-Hash-Spalte komplett.

**Root-Cause:**
`result.order_id` (aus `ExecutionResult`) war nach erfolgreicher Order
vorhanden, wurde aber nie an `log_trade()` weitergegeben.
Polymarket liefert keinen separaten `transactionHash` im CLOB-Response —
der `order_id` ist die naechstbeste Referenz bis der Fill bestaetigt wird.

**Fix:**
- `main.py`: nach `result.success`, `_tx_hash = f"pending_{result.order_id}"`
  an `log_trade(tx_hash=_tx_hash)` uebergeben. Prefix "pending_" signalisiert
  dass der Blockchain-TX noch nicht bestaetigt ist.
- `tax_archive.py`: `"TX-Hash"` Spalte in deutschen CSV-Export eingefuegt
  (nach Uhrzeit-Spalte). Wert im Archiv nachtraeglich updatebar via `resolve_trade()`.

---

## P034 — Silent Auto-Claim-Errors: Fehler wurden nur geloggt, kein Telegram-Alert

**Status:** BEHOBEN (2026-04-18)

**Problem:**
Wenn `redeem_position()` scheiterte (z.B. RPC-Timeout, CLOB-Auth-Fehler),
wurde der Fehler nur ins Server-Log geschrieben. Brrudi sah nichts —
Positionen blieben unclaimed bis zum naechsten Loop-Durchlauf.

**Fix:**
- `redeem_position()` gibt jetzt `(bool, str)` zurueck statt nur `bool`.
- `claim_all()` sammelt alle fehlgeschlagenen Positionen in `failed_positions`.
- `claim_loop()` ruft `_send_claim_error_alert(condition_id, error_msg)` pro Fehler.
- Rate-Limit: `CLAIM_ERROR_ALERT_COOLDOWN_S=3600` (env-konfigurierbar) —
  pro `condition_id` max 1 Telegram-Alert pro Stunde.
- Alert-Format: "⚠️ Auto-Claim Fehler: <error> (Position: <cid_short>, Zeit: <utc>)"

---

## P035 — Wöchentlicher Auto-Tax-Export

**Status:** IMPLEMENTIERT (2026-04-18)

**Problem:**
`export_tax_csv()` war nur manuell aufrufbar — keine automatische
Sicherung, Brrudi musste aktiv dran denken.

**Fix:**
- `scripts/weekly_tax_export.py`: ruft `export_tax_csv()` auf,
  verschiebt Dateien in `/root/KongTradeBot/exports/tax_YYYY_KWWW.csv`
  und `blockpit_YYYY_KWWW.csv`, sendet Telegram-Summary an alle Chat-IDs.
- `kongtrade-tax-export.service` + `.timer`: OnCalendar=Fri 23:55 Berlin
- Herunterladen per scp: `scp root@89.167.29.183:/root/KongTradeBot/exports/*.csv .`

**Blockpit-Timestamp-Hinweis:**
Gespeicherte Zeiten sind Server-Lokalzeit (Helsinki ≈ UTC+2 Sommer).
Blockpit-Export formatiert als `YYYY-MM-DDTHH:MM:SSZ` (formal UTC-Flag).
TODO(BLOCKPIT-VERIFY): Falls Blockpit auf korrekte UTC besteht,
muss log_trade() timezone-aware speichern.

**Status:** DEPLOYED (2026-04-18)

---

## P036 — OAuth-Popup trotz embedded PAT — GCM intercepted github.com

**Status:** BEHOBEN (2026-04-18)

**Problem:**
GCM (`credential.helper=manager`) ist systemweit gesetzt und fängt
HTTPS-Requests an github.com ab — selbst wenn PAT in der Remote-URL
eingebettet ist. Kein `~/.gitconfig` existierte zur Überschreibung.

**Fix:**
`git config --global credential.https://github.com.helper ""`

Leerer String in User-Config überschreibt System-Helper für github.com-URLs.
Git liest Credentials dann direkt aus der URL.

---

## P037 — Frankfurter API URL-Migration (.app → .dev/v1), Hetzner-IP-Block

**Status:** BEHOBEN (2026-04-18)

**Problem:**
`api.frankfurter.app` gibt 403 von Hetzner-Helsinki-IP.
Ergebnis: EUR/USD-Kurs fällt auf Fallback 0.92 — zu niedrig
(aktueller Kurs ≈ 0.88), systematische Verzerrung aller EUR-Steuerbeträge.

**Fix (3 Ebenen):**
1. Primary: `https://api.frankfurter.dev/v1/` — gleiche ECB-Quelle,
   neue Domain, kein Hetzner-Block
2. Secondary: ECB direkt via XML
   `https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml`
3. Tertiary: Hardcodierter Fallback 0.92

**Affected file:** `utils/tax_archive.py` — `_fetch_eur_usd_rates()`

---

## P039 — Wallet-Scout Decay-Detection via SQLite-Zeitreihe

**Status:** IMPLEMENTIERT (2026-04-18)

**Problem:**
`wallet_scout.py` sendet nach jedem Scan nur einen Telegram-Report.
Keine persistente Geschichte → keine Trend-Erkennung, kein Decay-Vergleich
über mehrere Tage, kein "neue Einsteiger"-Tracking moeglich.

**Fix:**
- SQLite DB `data/wallet_scout.db` (Tabelle `wallet_scout_daily`)
- PRIMARY KEY (scan_date, wallet_address, source) → idempotent, taeglich ueberschreibbar
- `utils/wallet_trends.py`: Trend-Funktionen (get_wallet_trend,
  get_decay_candidates, get_new_entries, get_rising_stars, get_top_stable)
- `scripts/weekly_wallet_report.py` + systemd Timer (So 20:00 Berlin)
- Dashboard `/api/wallet_trends` Endpoint fuer spaetere Chart-Integration
- DB wird beim ersten Scan automatisch angelegt (mkdir -p + CREATE IF NOT EXISTS)

**Hinweis:**
Erste echte Trends sind nach 7-14 Scan-Tagen sichtbar.
Heute startet die Zeitreihe bei null.

---

## P038 — "Schließt in"-Spalte zeigt "—" für alle offenen Positionen

**Status:** BEHOBEN (2026-04-18)

**Symptom:**
Alle 6 offenen Positionen im Dashboard zeigen "—" in der
"Schließt in"-Spalte statt Countdown. "Nächste Resolutions"
Panel meldet "Keine offenen Positionen mit Deadline".

**Root-Cause (systematisch, kein Edge-Case):**
Die Polymarket Data API (`data-api.polymarket.com/positions`)
liefert `endDate` als reines Datumsfeld: `"2026-04-30"` (kein Zeit-,
kein Timezone-Suffix). `datetime.fromisoformat("2026-04-30")` gibt ein
**naive datetime** zurück (tzinfo=None). Die Subtraktion
`naive_dt - datetime.now(timezone.utc)` wirft dann
`TypeError: can't subtract offset-naive and offset-aware datetimes`.
Dieser Fehler wird von `except Exception: return "—"` abgefangen —
komplett silent.

**Warum nicht Gamma/CLOB-Fallback?**
`p.get("endDate")` im Data-API-Objekt liefert bereits den Wert
`"2026-04-30"` — truthy, daher wird der enddate_map-Fallback nie
erreicht. Der Bug tritt vor der Gamma/CLOB-Abfrage auf.

**Fix (eine Zeile):**
```python
if dt.tzinfo is None:
    dt = dt.replace(tzinfo=timezone.utc)
```
In `_closes_in_label()`, direkt nach `datetime.fromisoformat()`.

**Live-Test-Ergebnis nach Fix:**
- Trump Iran April 21 → "2d 9h" ✅
- Trump enrichment April 30 → "11d 9h" ✅
- US x Iran April 30 → "11d 9h" ✅
- US x Iran April 22 → "3d 9h" ✅
- Strait of Hormuz April 30 → "11d 9h" ✅
- ENDED Märkte → "ENDED" ✅

---

## P040 — Telegram-Spam: Bot-Neustart-Alerts bei jedem Watchdog-Zyklus

**Status:** ✅ BEHOBEN (18.04.2026)

**Symptom:**
Jeder erfolgreiche Bot-Neustart via Watchdog schickte "✅ neu gestartet via systemd" an Telegram.
Da der Watchdog alle 60s läuft und bei Frozen-Erkennung immer neu startet, konnte dies massiv spammen.
Zusätzlich: Bot-Startup-Alert kam bei jedem Restart, auch wenn mehrere Neustarts binnen Minuten passierten.

**Root-Cause:**
1. `watchdog.py` lud immer `send_telegram('✅ neu gestartet...')` nach Restart — kein Throttle.
2. `HEARTBEAT_MAX_AGE = 180s` zu niedrig — bei kurzer Systemlast feuerte Watchdog zu früh.
3. `send()` in `telegram_bot.py` hatte kein Mute-System.
4. Startup-Alert in `main.py` hatte kein Rate-Limit.

**Fix:**
- `watchdog.py`: Erfolgreiche Restart-Alerts entfernt (nur Fehler-Alert bleibt). `HEARTBEAT_MAX_AGE` 180 → 600s.
- `telegram_bot.py`: 
  - `_is_muted()` / `_MUTE_FILE` (`.mute_until` Datei, ISO-Timestamp).
  - `_is_startup_allowed()` / `_STARTUP_ALERT_FILE` (`.last_startup_alert`, Unix-Timestamp, 30min Cooldown).
  - `send(urgent=False)` — respektiert Mute außer bei `urgent=True`.
  - `send_startup()` — Wrapper mit Rate-Limit-Check.
  - `/menu` Inline-Keyboard (8 Buttons: Status, Portfolio, Heute, Config, Positionen, Archiv, Mute 1h, Unmute).
  - `_TG_MIN_SIZE` Default: 5 → 2 USD.
- `scripts/daily_digest.py` + systemd Timer 22:00 Berlin.

---

## P041 — Telegram-Callbacks lasen local state statt API → immer $0 / 0 Positionen

**Status:** ✅ BEHOBEN (18.04.2026)

**Symptom:**
`/menu → Portfolio` zeigte "0 Positionen | $0.00 USDC" obwohl 18 offene Positionen
mit $213 Value existierten. Alle 6 Menu-Callbacks zeigten leere/falsche Daten.

**Root-Cause:**
`_handle_menu_callback()` las aus `bot_state.json` und `trades_archive.json` auf Disk.
Nach jedem Bot-Restart ist `bot_state.json` initial leer (Positionen werden erst nach
Sync geladen, aber das Keyboard wurde schon vorher gedrückt).

**Fix:**
- `_fetch_dashboard(endpoint)` Helper: `GET http://localhost:5000{endpoint}` (localhost, kein Auth).
- Alle 6 Callbacks auf Dashboard-API umgestellt:
  - STATUS → `callback_status()` (unverändert, zieht Live-Daten)
  - PORTFOLIO → `/api/summary` + `/api/portfolio`
  - HEUTE → `/api/summary`
  - POSITIONEN → `/api/portfolio`
  - ARCHIV → `/api/summary` (Fallback: lokales Archiv)
  - CONFIG → env-Variablen (kein API-Call nötig)
- Fehlerbehandlung: wenn API nicht erreichbar → "Dashboard aktuell nicht erreichbar".

---

## P042 — Bot-Restart-Schleife alle 3 Min (HEARTBEAT_MAX_AGE < heartbeat_loop interval)

**Status:** ✅ BEHOBEN (18.04.2026, via aeec617)

**Symptom:**
Bot sendete alle 2–4 Min "BOT GESTARTET" (Timestamps: 14:34, 14:37, 14:40, 14:43...).
Telegram-Alert kam zuverlässig (Rate-Limit griff korrekt), aber Bot war tatsächlich jedes Mal neu.

**Root-Cause:**
`heartbeat_loop(interval=300)` schreibt Heartbeat alle **300 Sekunden**.
`watchdog.py` hatte `HEARTBEAT_MAX_AGE = 180` Sekunden.
180 < 300 → Watchdog sah nach 180s keine neue Heartbeat-Datei → restartete Bot.
Bot startete neu, Heartbeat wurde sofort geschrieben, dann 300s Pause → wieder Restart.

Cycle: 180s up → Watchdog restart → 180s up → repeat. Genau die 3-Minuten-Abstände.

**Fix:**
`HEARTBEAT_MAX_AGE`: 180 → 600 (> 300 = heartbeat_loop interval).
Fix war in aeec617 enthalten, wurde aber erst ab 15:01:27 (nach Auto-Deploy) aktiv.
Bot stabil seit 15:01:27.

**Lesson:** `HEARTBEAT_MAX_AGE` muss immer > `heartbeat_loop(interval)` sein. Aktuell: 600 > 300 ✅.

---

## P043 — Persistent Reply Keyboard (kein python-telegram-bot nötig)

**Status:** ✅ IMPLEMENTIERT (18.04.2026)

**Anforderung:** Keyboard permanent unten sichtbar — User soll nie `/menu` tippen müssen.

**Lösung:**
Telegram Bot API unterstützt `ReplyKeyboardMarkup` als raw JSON ohne python-telegram-bot Library:
```json
{"keyboard": [[{"text": "📊 Status"}, ...]], "resize_keyboard": true, "is_persistent": true}
```
- `/start` → sendet Begrüßung + Keyboard (Brrudi muss EINMALIG `/start` tippen nach Deploy)
- `/menu` / `/m` → sendet Keyboard erneut (falls ausgeblendet)
- Text-Button-Klicks werden als normale Nachrichten empfangen → `_BUTTON_ACTION_MAP` dispatcht zu `_handle_menu_callback()`
- `python-telegram-bot` NICHT installiert auf Server → Library-Import würde crashen

---

## P044 — Drei Detail-Bugs nach Callback-API-Umstieg (18.04.2026)

**Status:** ✅ BEHOBEN (18.04.2026)

### Bug A — Positionen-Callback: Invest immer $0.00
`p.get("size_usdc")` → Feld existiert nicht in `/api/portfolio`.
API liefert `traded` (= Initial-Investment in USDC).
Fix: `p.get("traded", 0)`. Zeigt jetzt korrekt "$60.00→$66.38 (+10.6%)".

### Bug B — Status-Button: reagiert nicht
`msg_status(orders=s["orders_created"])` → Parameter heißt `orders_sent`.
Python TypeError: unexpected keyword argument 'orders' → Exception → silent fail.
**Betroffen:** sowohl `/status` Befehl als auch stündlicher Status-Reporter (beide seit langem kaputt).
Fix: beide Call-Sites in main.py: `orders=` → `orders_sent=`.

### Bug C — Heute-Callback: P&L immer $0.00
`today_pnl` in `/api/summary` = Summe AUFGELÖSTER Trades heute.
Da heute keine Märkte aufgelöst wurden → 0. (T-015, bereits bekannt)
Fix: Midnight-Snapshot in `dashboard.py`:
- `_get_midnight_snapshot(today_str, current_total)` erstellt `.portfolio_snapshot_YYYY-MM-DD.json`
- `/api/portfolio` gibt `today_pnl_portfolio = total_value - snapshot_value` zurück
- Telegram zeigt: "Portfolio-Delta: +$X.XX USDC (Morgen: $X → Jetzt: $X)"
- Alte Snapshots (> 7 Tage) automatisch gelöscht

---

## P045 — Drei Telegram-Bugs nach Live-Test (18.04.2026)

**Status:** ✅ BEHOBEN (18.04.2026)

### Bug A — Status-Button: zweites `orders=` in send_status_now() übersehen
P044 Fix hatte `orders=` → `orders_sent=` nur in `status_reporter` (line 441) behoben.
`send_status_now()` (line 727) — aufgerufen vom Status-Button — hatte noch `orders=s["orders_created"]`.
Gleiches TypeError → silent fail → kein Response auf Button-Klick.
Fix: `orders=` → `orders_sent=` auch in `send_status_now()`.

### Bug B — Multi-Signal Spam: dieselbe Wallet+Markt-Kombi mehrfach in 15 Min
`_flush_aggregated()` feuert `on_multi_signal` bei jedem Trade-Chunk für dieselbe Kondition.
Cincinnati Reds-Beispiel: Alert um 20:37, 20:48, etc. für identische Wallet+Markt-Kombination.
Fix: Dedup in `on_multi_signal` (main.py):
- Key = `f"{market}|{outcome}|{sorted(wallet_names)}"`
- 15-Min-Cooldown via `.multi_signal_last_alert.json` (root dir)
- Keys älter als 24h werden beim nächsten Alert bereinigt

### Bug C — Silent Button-Crashes: kein Feedback bei Exception
Exceptions in `_handle_menu_callback` propagierten zu `poll_commands` → `except Exception: pass` → kein Telegram-Alert.
Fix: `_safe_callback(name, handler, *args)` in `telegram_bot.py`:
- Fängt Exception, loggt Traceback, sendet Telegram-Alert mit Fehlermeldung
- Gibt `"⚠️ Fehler"` zurück statt re-raise
- Beide Call-Sites (Inline-Keyboard und Text-Button) nutzen `_safe_callback`

---

## P046 — Exit-Strategie Design Decisions (18.04.2026)

**Status:** ✅ IMPLEMENTIERT (18.04.2026) — EXIT_DRY_RUN=true, Observation läuft

### Warum 40/40/15/5 Staffel?
Basiert auf Prevayo-Research und Laika AI Backtests für binäre Prediction-Markets.
- 40% Sicherheits-Take bei +30%: Kapitalsicherung bevor Reversal-Risk steigt
- Zweites 40% bei +60%: Compound-Effekt bei Gewinnern
- 15% bei +100%: Lässt Runner-Anteil (5%) bis Resolution
- 5% "Runner" bis Markt-End: Max-Payout bei Jackpot-Outcomes

Boost-Staffel (3+ Wallets): 50/90/150% Schwellen wegen höherer Conviction bei
multi-wallet Signalen → länger halten macht Sinn.

### Warum 12¢ Trail-Aktivierung (absolut, nicht prozentual)?
Binäre Prediction-Markets handeln 0..1 USDC. Prozentuale Trails scheitern bei:
- Billige Tokens (z.B. 5¢ entry): 10% = 0.5¢ → Trail zu sensibel
- Teure Tokens (z.B. 85¢ entry): 10% = 8.5¢ → nur Margins, kein Edge
12¢ absolut = sinnvoller echter Gewinn bei allen Preisniveaus.
Trail-Distance: 7¢ (liquid ≥$50k Volume) vs 10¢ (thin) — breiterer Trail bei
illiquidem Market wegen höherer Spread-Noise.

### Warum Whale-Exit höchste Priorität?
Smart-Money-Signal überschreibt Zahlen. Wenn die Wallet die wir kopieren verkauft,
weiß sie etwas das wir nicht wissen (Info-Arbitrage, privates Signal).
TP-Schwellen sind historische Statistik; Whale-Signal ist Information.
Sofort 100% raus, kein partial-exit, kein Zögern.

### Warum DRY-RUN-Default?
Drei Gründe:
1. Validierung: Erste 24h beobachten ob Exit-Logik vernünftige Signale produziert
2. Preis-Slippage: SELL auf Polymarket hat andere Dynamics als BUY — braucht Daten
3. Race-Condition: exit_loop + WalletMonitor + FillTracker teilen sich `engine.open_positions`
   → im DRY-RUN keine echten Side-Effects wenn Race-Condition auftritt

Nach 24h Observation: grep exit_loop Logs, prüfe ob TP/Trail-Signale sinnvoll,
dann EXIT_DRY_RUN=false setzen.

### Bekannte Edge-Cases (für Post-Observation Review):
- Partial-Fill bei SELL: `remaining_shares` wird tracked, aber nächster Loop-Cycle
  verkauft nochmal basierend auf `pos.shares` (nicht updated wenn DRY-RUN)
- Race: Whale-Exit + TP1 gleichzeitig → Whale-Exit gewinnt (continue-Statement)
- `market_volumes` kommt aktuell als {} → immer thin-trail (konservativ, gut)
- `get_recent_sells` auf WalletMonitor fehlt noch → Whale-Exit immer skip bis implementiert

---

## P052 — Grok API als Twitter-Alternative (19.04.2026)

Status: VERSTANDEN — Paradigma-Wechsel für Sentiment-Strategie

Kontext: Gestern Abend Sentiment-Bot-Plan basierte auf Twitter API
Basic ($100/Monat, ohne Streaming unbrauchbar) oder TweetStream.io
($139-349/Monat als Mittelweg).

Update: Grok 4.1 Fast bietet native X/Twitter-Integration via
API-Tool:
- $0.20 / $0.50 pro 1M Tokens (Input/Output)
- 2M Token Context Window (ganze Tweet-Streams verarbeitbar)
- Echtzeit-X-Search nativ
- Kein separater Twitter-API-Account nötig

Kostenrechnung für typischen Einsatz:
- 100 Market-Queries/Tag × 5k Tokens avg = 500k Tokens/Tag
- Monatlich: 15M Tokens = ~$3-15/Monat (statt $139-5000)

Implikation:
- T-I07 Sentiment-Bot Phase 0.5 wird umgeplant: Grok statt RSS als
  primäre Quelle
- Twitter-API-Pro aus der Planung gestrichen
- Neue Task T-S01/T-S05: Grok-Integration als universelles Modul

Architektur-Update: Grok-Modul wird so gebaut, dass es von ALLEN
zukünftigen Bots genutzt werden kann (Polymarket, Crypto, Stocks,
Futures). Kein Bot-spezifisches Twitter-Tracking mehr.

---

## P054 — Peer-Modell für Kollaboration (19.04.2026)

Status: ENTSCHIEDEN — Peer, nicht Chef

Kontext: 4 Personen bauen parallel ähnliche Systeme.
Frage: Wie koordinieren ohne Hierarchie?

Entscheidung:
- Brrudi initiiert Infrastruktur + GUIDELINES
- Alle 4 sind gleichberechtigte Entscheider
- Opt-In statt Opt-Out
- Autonomie vor Konformität

Implikation:
- Keine Master-Slave-Architektur
- Kein zentraler Bot-Controller
- Shared Services sind Utilities, nicht Kommando
- Wenn Alex/Tunay/Dietmar nicht teilnehmen wollen: OK

Lesson: Bei Familie/Freunden nie Chef spielen.
Strukturen so bauen dass sie OHNE dich weiter funktionieren.

## Session 21. April 2026

### K-W01: negRisk Bucket-Logik
**Problem:** P(T≥X) statt P(T∈Bucket) berechnet.
**Fix:** bucket_prob() in weather_scout.py korrigiert.
**Impact:** Win Rate von 95.6% (Artefakt) auf 67.2% (real) korrigiert.

### K-W02: ICAO-Mapping (kritisch)
Paris = LFPB (Le Bourget) NICHT LFPG (CDG)!
London = EGLC (City Airport)
Seoul = RKSI (Incheon)
Toronto = CYYZ (Pearson)
US-Städte = °F! (Chicago KORD, NYC KLGA, Miami KMIA)
TODO: Paris noch nicht korrigiert im Script.

### K-W03: Seoul April-Bias
Open-Meteo unterschätzt Incheon Airport um -5.23°C im April.
Formel: fc_corrected = fc_raw - monthly_bias (bias ist negativ → addiert sich)
Sigma Seoul = 2.3 (empirisch), April-σ = 2.74 (Föhn-Effekte)

### K-W04: Bucket Sum Arbitrage ist illusorisch
Sum < $1.00 sieht nach risikofreiem Gewinn aus.
Realität: Penny-Buckets haben fast keine Liquidität.
Beispiel: Buenos Aires 12.9% ROI = $38 Tiefe = $4.55 maximal.
Keine echte Arb-Möglichkeit bei kleinen Positionen.

### K-W05: Sigma-Kalibrierung (empirisch, 77 Tage)
calc_station_sigma.py berechnet σ aus Residuen (actual - fc_corrected).
Ergebnis: Fast alle Städte σ=1.0–1.5 (ECMWF sehr präzise).
Ausreißer: Seoul=2.3, Toronto=2.2, Denver=2.1, Chicago=1.8.
Moscow/Dubai: waren manuell 2.5 gesetzt, empirisch nur 1.1.
Alle 30 Städte in polymarket_stations.json aktualisiert.

### K-W06: Insider-Wallets sind One-Time-Events
Echter Insider = einmaliges Ereignis, neues Wallet, verschwindet.
Nicht: Wallet langfristig beobachten.
Richtig: MUSTER erkennen (frisches Wallet + groß + niedrig + Geopolitik).

### K-W07: Polygonscan Key
Key: IAYXP5NMRQCUHWF3T3346U277JD1YDUJD6
In .env und hardcoded im Script. Aktiv seit letztem Run.

### K-W08: Insider-Analyse Pagination-Bug
Streaming-Version lädt Endlos-Seiten wenn geo/niche-Bucket voll sind.
Fix benötigt: break wenn beide Buckets voll (geo>=3000 AND niche>=500).
Zeile in get_resolved_markets() nach dem Batch-Loop einfügen:
  if len(geo_markets) >= 3000 and len(niche_markets) >= 500: break

### K-W09: GitHub Support
Repo KongTradeBot-Template enthält inappropriate contents → löschen.
Kontakt: support.github.com Portal (nicht per Email).

---

## P030 — Lock-File Race Condition (Cascade-Loop 19.-21.04.2026)
Status: ✅ BEHOBEN

Symptom: 532 von 665 Bot-Starts fehlgeschlagen.
Bot lief 2 Tage in permanentem Crash-Loop.
Root-Cause: main() ohne atexit-Cleanup →
bot.lock blieb nach Crash zurück →
nächster Start: "Bot läuft bereits!" → Exit.
Fix: check_and_create_lock() mit atexit +
SIGTERM-Handler. Heartbeat 300s → 60s.
Impact: 2 Tage Signalausfall, trotzdem +$67
durch bestehende Positionen.

---

## P031 — Weather Loop markets not defined (Recurring)
Status: ✅ BEHOBEN

Symptom: 109+ Fehler akkumuliert,
"name 'markets' is not defined" alle ~10s.
Root-Cause: markets-Variable in mehreren
Weather-Loops ohne vorherige Definition nach
Code-Refactoring.
Fix: get_all_polymarket_weather_markets()
vor jeder Nutzung von markets eingefügt.

---

## P032 — Budget-Cap blockierte alle Trades seit 19.04.
Status: ✅ BEHOBEN

Symptom: Alle neuen Trades abgelehnt seit April 19.
Root-Cause: RECOVERED_-Positionen ($538 invested)
blockierten Budget-Cap (max $500).
48h-Guard für RECOVERED_ verhinderte Cleanup.
Fix: 48h-Guard für RECOVERED_ entfernt,
$180 freigegeben.

---

## P033 — Weather Execution komplett fehlte (seit Bot-Start)
Status: ✅ BEHOBEN — 21.04.2026

Symptom: Bot fand täglich 20+ Opportunities,
handelte aber nie einen einzigen Weather-Trade.
WEATHER_DRY_RUN=false war korrekt gesetzt —
trotzdem 0 echte Trades seit Bot-Start.

Root-Cause: weather_loop() in main.py hatte
keinen Execution-Code. Nur Telegram-Alert +
Shadow-Portfolio. on_copy_order() wurde nie
aufgerufen. Außerdem: Opportunity-Dicts hatten
kein token_id-Feld (nötig für TradeSignal),
weil get_all_polymarket_weather_markets() die
clobTokenIds aus der Gamma API nicht
weitergereicht hat.

Fix (3 Teile):
1. weather_scout.py: clobTokenIds aus Gamma API
   in token_ids-Feld übernommen.
2. weather_scout.py: token_id zu jedem
   Opportunity-Dict (YES=token[0], NO=token[1]).
3. main.py weather_loop(): Nach Telegram-Summary
   live_opps filtern (nicht shadow_only + hat
   token_id) → TradeSignal + CopyOrder bauen
   → on_copy_order() routen (Budget-Check +
   Telegram-Confirmation + Execution).

Erster echter Weather-Trade: 21.04.2026 ~12:06 UTC
  Paris NO @ 34¢ (Order 0xaa64...ec8e)
  Dallas YES @ 22¢ (Order 0x7bc1...40ff)

Wichtig: Immer prüfen ob weather_loop() nach
run_weather_scout() auch on_copy_order() aufruft.
