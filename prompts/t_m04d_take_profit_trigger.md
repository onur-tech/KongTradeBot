# T-M04d Implementation: Take-Profit >=95c Trigger

_Fertig: 2026-04-19 — bereit für Server-CC nach T-M04b-Ende_
_Basis: Code-Analyse exit_manager.py + config.py + main.py (read-only SSH)_

---

## KONTEXT

**Was ist das Problem:**
Positionen, die auf >90c laufen, werden nicht automatisch verkauft — obwohl das
fast sicher Gewinn bedeutet. Wuning lief auf 95c+ bevor die Auflösung kam und
wurde manuell geclaimed. Mit Auto-Sell hätte der Bot den Peak verkauft.

**Was existiert bereits:**
- `exit_manager.py` — voll funktionsfähig mit TP1/TP2/TP3 (pnl%-basiert), Trailing-Stop,
  Whale-Follow-Exit. Evaluiert alle 60s.
- `execution_engine.py:636` — `create_and_post_sell_order()` implementiert, mit Retry.
- `main.py:930` — `exit_loop()` verdrahtet Exit-Events mit echtem Sell-Call.
- `ExitState` — persistiert tp1_done/tp2_done/tp3_done pro Position.
- `EXIT_DRY_RUN=true` in .env (aktueller Stand).

**Was fehlt:**
Kein absoluter Preis-Trigger. TP3 feuert bei 100% PnL-Gewinn (z.B. entry 0.40 → 0.80).
Der >=95c-Trigger ist anders: "Preis nahe 1.0 = fast resolved = jetzt raus."
Diese Logik gibt es noch nicht.

**Kritischer Hinweis zu `_execute_exit`:**
Zeile ~290 in exit_manager.py hat:
```python
if not self.cfg.exit_dry_run:
    # Part 2: hier execution_engine.sell_position(pos, shares_to_sell) aufrufen
    pass
```
→ DAS IST EIN STUB. Der echte Sell-Call passiert in `main.py:exit_loop()` nach dem
Event-Return — NICHT in `_execute_exit`. Diesen Stub NICHT anfassen.

---

## PHASE 1: Code-Analyse + Verifikation (15min)

Vor Änderungen sicherstellen:

```bash
# 1. Exit-Loop läuft?
grep -n 'exit_loop\|ExitManager' /root/KongTradeBot/main.py | head -10

# 2. Aktuelle TP-Thresholds:
grep -E 'EXIT_TP|EXIT_TRAIL|EXIT_ENABLED|EXIT_DRY' /root/KongTradeBot/.env

# 3. ExitState-Dataclass:
grep -A5 'class ExitState' /root/KongTradeBot/core/exit_manager.py

# 4. Wie viele Positionen haben aktuell price >= 0.95?
# (manuell via data-api prüfen — keine Codeänderung)
```

**Expected:** EXIT_ENABLED=true, EXIT_DRY_RUN=true, exit_loop alle 60s.
Falls EXIT_DRY_RUN nicht in .env steht: Default in config.py ist `true` — OK.

---

## PHASE 2: Config erweitern (15min)

**Datei: `utils/config.py`**

```python
# In der Config-Dataclass, nach exit_min_hours_to_close:
exit_price_cap_threshold: float = 0.95      # Preis-Trigger absolut (0..1)
exit_price_cap_hold_ticks: int = 2          # Wie viele 60s-Evaluierungen >=Threshold bevor Trigger
exit_price_cap_sell_ratio: float = 1.0      # Komplett-Exit bei Price-Cap
exit_daily_sell_cap_usdc: float = 500.0     # Max USDC-Sell-Volumen pro Tag (Safety)
```

```python
# In Config.from_env(), nach exit_min_hours_to_close-Zeile:
exit_price_cap_threshold=float(os.getenv("EXIT_PRICE_CAP_THRESHOLD", "0.95")),
exit_price_cap_hold_ticks=int(os.getenv("EXIT_PRICE_CAP_HOLD_TICKS", "2")),
exit_price_cap_sell_ratio=float(os.getenv("EXIT_PRICE_CAP_SELL_RATIO", "1.0")),
exit_daily_sell_cap_usdc=float(os.getenv("EXIT_DAILY_SELL_CAP_USDC", "500.0")),
```

**Datei: `.env`** (am Server direkt hinzufügen):
```
EXIT_PRICE_CAP_THRESHOLD=0.95
EXIT_PRICE_CAP_HOLD_TICKS=2
EXIT_PRICE_CAP_SELL_RATIO=1.0
EXIT_DAILY_SELL_CAP_USDC=500.0
```

---

## PHASE 3: ExitState + ExitManager erweitern (45min)

**Datei: `core/exit_manager.py`**

### 3a) ExitState erweitern

```python
@dataclass
class ExitState:
    position_key: str
    entry_price: float
    tp1_done: bool = False
    tp2_done: bool = False
    tp3_done: bool = False
    trail_active: bool = False
    highest_price_seen: float = 0.0
    last_evaluated: float = field(default_factory=time.time)
    price_cap_ticks_above: int = 0          # NEU: Zähler für Hold-Requirement
    price_cap_done: bool = False            # NEU: damit nicht doppelt feuert
```

### 3b) Daily-Sell-Cap-Tracker in ExitManager.__init__

```python
def __init__(self, config, wallet_monitor=None, on_exit_event=None):
    self.cfg = config
    self.wallet_monitor = wallet_monitor
    self.on_exit_event = on_exit_event
    self._states: Dict[str, ExitState] = {}
    self._daily_sold_usdc: float = 0.0          # NEU
    self._daily_sold_date: str = ""              # NEU (YYYY-MM-DD)
    self._load_state()
```

### 3c) Neue Methode `_check_price_cap`

```python
def _check_price_cap(
    self,
    pos,
    state: ExitState,
    current_price: float,
) -> bool:
    """
    True wenn Preis >= Threshold für >= hold_ticks aufeinanderfolgende Evaluierungen.
    Verhindert Noise-Trigger durch kurze Preis-Spikes.
    """
    if state.price_cap_done:
        return False
    if current_price >= self.cfg.exit_price_cap_threshold:
        state.price_cap_ticks_above += 1
        if state.price_cap_ticks_above >= self.cfg.exit_price_cap_hold_ticks:
            logger.info(
                f"[ExitMgr] 🎯 PRICE-CAP: {pos.outcome} @ {current_price:.3f} "
                f">= {self.cfg.exit_price_cap_threshold} für {state.price_cap_ticks_above} Ticks"
            )
            return True
    else:
        # Reset wenn Preis wieder fällt (Spike vorbei)
        if state.price_cap_ticks_above > 0:
            logger.debug(
                f"[ExitMgr] Price-Cap Reset: {pos.outcome} @ {current_price:.3f} "
                f"(war {state.price_cap_ticks_above} Ticks)"
            )
        state.price_cap_ticks_above = 0
    return False
```

### 3d) Daily-Sell-Cap-Check in `_execute_exit`

Direkt vor dem Exit-Log einfügen:

```python
async def _execute_exit(self, pos, state, shares_ratio, exit_type, current_price):
    shares_to_sell = round(pos.shares * shares_ratio, 6)
    usdc_received  = round(shares_to_sell * current_price, 4)

    # Daily-Sell-Cap: Reset bei Datumswechsel, dann prüfen
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if self._daily_sold_date != today:
        self._daily_sold_usdc = 0.0
        self._daily_sold_date = today
    if self._daily_sold_usdc + usdc_received > self.cfg.exit_daily_sell_cap_usdc:
        logger.warning(
            f"[ExitMgr] ⛔ DAILY-SELL-CAP erreicht: bereits ${self._daily_sold_usdc:.2f}, "
            f"dieser Exit würde ${usdc_received:.2f} hinzufügen > Cap ${self.cfg.exit_daily_sell_cap_usdc}"
        )
        return None  # Exit abgebrochen

    # ... rest of existing _execute_exit code unchanged ...
    # Am Ende, nach erfolgreichem Execute:
    self._daily_sold_usdc += usdc_received
```

### 3e) Price-Cap in `evaluate_all()` einbauen

In der for-Schleife, NACH dem TP-Check und VOR dem Trail-Check:

```python
# 2. TP-Staffel (existing)
tp_result = self._check_tp(pos, state, pnl_pct, multi_count)
if tp_result:
    # ... existing code ...

# 2b. Price-Cap-Trigger (NEU) — unabhängig von TP, kann auf verbleibende Shares wirken
if not state.price_cap_done and self._check_price_cap(pos, state, current_price):
    # Price-Sanity: nicht verkaufen wenn Spread verdächtig groß
    # (Proxy: wenn current_price > 0.99 UND Position noch days_to_close > 2h → Warnung)
    hours_left = self._hours_to_resolution(pos)
    if current_price >= 0.99 and hours_left > 2.0:
        logger.warning(
            f"[ExitMgr] ⚠ PRICE-CAP Sanity-Check: {pos.outcome} @ {current_price:.3f} "
            f"aber noch {hours_left:.1f}h bis Close — manuell prüfen!"
        )
        # Trotzdem ausführen, aber warnen (Market könnte illiquid sein)
    event = await self._execute_exit(
        pos, state, self.cfg.exit_price_cap_sell_ratio, "price_cap", current_price
    )
    if event:
        events.append(event)
        state.price_cap_done = True
        state_dirty = True
    continue  # Kein weiterer Check nötig

# 3. Trailing-Stop (existing)
```

### 3f) exit_type "price_cap" in main.py Telegram-Alert

In `main.py` wo `exit_type` für den Alert-Text verwendet wird:

```python
# Suche nach: event.exit_type für Alert-Formatierung
# Füge hinzu:
type_emoji = {
    "tp1": "📊 TP1", "tp2": "📈 TP2", "tp3": "🚀 TP3",
    "trail": "🔻 Trail-Stop", "whale_exit": "🐋 Whale-Exit",
    "price_cap": "🎯 Price-Cap (≥95¢)",  # NEU
    "manual": "✋ Manuell",
}.get(event.exit_type, event.exit_type)
```

---

## PHASE 4: DRY-RUN Test (30min)

### 4a) Bot mit DRY-RUN starten

```bash
# EXIT_DRY_RUN=true bereits in .env
cd /root/KongTradeBot
python3 main.py --live  # oder wie Bot normalerweise gestartet wird
```

**Was zu beobachten ist:**
- Log: `[ExitMgr] 🎯 PRICE-CAP: ... >= 0.95 für 2 Ticks`
- Log: `[EXIT DRY-RUN] SELL ... shares @ asset=...`
- Telegram: Alert mit "🎯 Price-Cap (≥95¢)"
- **Keine echte Order** (DRY-RUN)

**Test-Beschleunigung:** Wenn keine Position aktuell >=0.95, temporär Threshold senken:
```bash
# In .env temporär:
EXIT_PRICE_CAP_THRESHOLD=0.50
EXIT_PRICE_CAP_HOLD_TICKS=1  # sofort triggern
```
→ DRY-RUN-Trigger beobachten, dann auf 0.95 zurücksetzen.

### 4b) Manueller Live-Preis-Check

```bash
ssh claudeuser@89.167.29.183 "python3 -c \"
import json, urllib.request
wallet = '0x700BC51b721F168FF975ff28942BC0E5fAF945eb'
url = f'https://data-api.polymarket.com/positions?user={wallet}'
r = urllib.request.urlopen(url)
pos = json.loads(r.read())
for p in pos:
    price = float(p.get('currentPrice', p.get('price', 0)) or 0)
    if price >= 0.50:
        print(f'{price:.3f} | {p.get(\"title\",\"\")[:50]}')
\""
```

---

## PHASE 5: Einen echten Live-Exit testen (nach DRY-RUN-Erfolg)

**ERST AUSFÜHREN wenn DRY-RUN mehrfach korrekt gefeuert hat.**

### 5a) Kleinste Position mit >=0.95 identifizieren

```bash
# Prüfe welche Positionen aktuell >= 0.95
# Wähle die Position mit kleinstem size_usdc für den ersten echten Test
```

### 5b) Live-Exit aktivieren

```bash
# Nur für Test: EXIT_DRY_RUN auf false
sed -i 's/EXIT_DRY_RUN=true/EXIT_DRY_RUN=false/' /root/KongTradeBot/.env
# Bot neu starten oder reload warten
```

**Erwartetes Ergebnis:**
- Log: `✅ SELL ORDER gefüllt: X.XXXX shares @ $0.9X | ID: ...`
- Telegram: Alert mit echtem PnL
- Dashboard: Position verschwindet (oder shares reduziert)
- `exit_state.json`: `price_cap_done: true` für diese Position

### 5c) Nach erstem Live-Exit

```bash
# Sofort prüfen:
tail -50 /root/KongTradeBot/logs/bot_$(date +%Y-%m-%d).log | grep -E 'SELL|price_cap|ExitMgr'
```

---

## CRITICAL STOPS

**STOP und fragen wenn:**

1. `_execute_exit` gibt `None` zurück und der Grund ist unklar (kein Cap-Log)
2. `create_and_post_sell_order` gibt `success=False` zurück mit Fehler != "DRY-RUN"
3. Mehr als 2 Positionen gleichzeitig als Price-Cap triggern (unerwartet)
4. Daily-Sell-Cap wird innerhalb 1 Stunde erreicht (EXIT_DAILY_SELL_CAP_USDC zu niedrig?)
5. Sanity-Warning erscheint: Price >= 0.99 aber Hours > 2.0 → manuell prüfen ob Market-Preis real ist
6. ExitState-Datei korrupt / Migration-Error nach Dataclass-Erweiterung

**Emergency-Stop:**
```bash
# Sofort alle Exits stoppen (ohne Bot-Neustart):
echo "EXIT_ENABLED=false" >> /root/KongTradeBot/.env
# ODER: Bot stoppen
kill $(cat /tmp/bot.pid)  # oder systemctl stop kong-bot
```

---

## DEPLOYMENT (Commits je Phase)

```
Phase 2: feat(config): Exit Price-Cap Threshold + Daily Sell Cap Konfiguration
Phase 3: feat(exit_manager): Price-Cap-Trigger >=95c + Hold-Ticks + Daily-Sell-Cap-Guard
Phase 4: test: DRY-RUN Price-Cap Trigger verifiziert (Logs beifügen)
Phase 5: feat: Price-Cap Live-Exit aktiviert (EXIT_DRY_RUN=false)
```

---

## ABSCHLUSSBERICHT (Server-CC nach Implementation)

1. **DRY-RUN-Trigger erfolgreich?**
   - Screenshot/Log-Output beifügen
2. **Erste Live-Position verkauft?**
   - Position + PnL + TX-Hash
3. **Daily-Sell-Cap getestet?**
   - Temporär auf $1 setzen, prüfen ob Block funktioniert
4. **Telegram-Alert korrekt formatiert?**
   - Screenshot beifügen
5. **Offene Fragen/Probleme?**
   - ExitState-Migration-Issues?
   - Sanity-Warning-Cases?

---

## OFFENE FRAGEN (Onur muss vor Implementation klären)

1. **Hold-Ticks = 2 (2 Minuten) oder mehr?**
   Bei 60s-Evaluierung: HOLD_TICKS=2 bedeutet 2 aufeinanderfolgende 60s-Checks >=0.95 = ~2min Hold.
   Wuning lief viele Stunden auf >95c — 2 Ticks sind sehr aggressiv. Empfehle 10 Ticks (10min) für Noise-Resistenz.
   → Entscheidung: wie viele Minuten bevor wir sicher verkaufen?

2. **Sell 100% oder gestaffelt?**
   Aktuell: `exit_price_cap_sell_ratio=1.0` (alles).
   Alternative: erst 80% bei 0.95, Rest bei 0.99.
   → Empfehle 100% bei 0.95 — wenn der Markt fast resolved ist, braucht man keine Staffel.

3. **Daily-Sell-Cap $500 sinnvoll?**
   Bei aktuell ~$200 Portfolio: $500 Cap = 250% des Portfolios. Eher $100-200?
   → Onur entscheidet basierend auf Komfort-Level.

4. **Soll EXIT_DRY_RUN=false nach Phase 4 permanent?**
   Oder erst nach mehreren Tagen Beobachtung?
   → Empfehle: Erst 24-48h DRY-RUN beobachten, dann live.

5. **Was wenn mehrere Positionen gleichzeitig >=0.95?**
   Daily-Cap verhindert Runaway. Aber: Reihenfolge? Größte zuerst? Kleinste zuerst?
   → Aktuell: Zufällig (List-Reihenfolge). OK für jetzt.
