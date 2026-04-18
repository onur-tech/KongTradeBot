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

**Status:** DEPLOYED (2026-04-18)
