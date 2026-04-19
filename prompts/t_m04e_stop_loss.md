# T-M04e Implementation: Stop-Loss-Trigger

_Fertig: 2026-04-19 — bereit für Server-CC nach T-M04d-Erfolg_
_Basis: Historical-Validation via SSH + Live-Portfolio-Analyse_

---

## KONTEXT

**Das Problem:**

13 von 24 Portfolio-Positionen sind bereits bei 0.0c (`redeemable=True, value=0`).
Sie sind vollständig verloren — kein Stop-Loss kann sie noch retten.
Aber sie zeigen das Muster das wir mit T-M04e vermeiden wollen:

```
Einstieg: 0.25-0.74c (Sports-Märkte, NBA/Baseball/Soccer)
Markt resolved → Preis kollabiert auf 0
Keine automatische Intervention → Totalverlust
```

**Aktuelle Position die NOCH gerettet werden kann:**
- "Trump announces end of military operations" → CurPrice 0.11c, Entry 0.261c, Value $18.95
  - Wenn Trigger bei 0.15c: hätte $25.85 gebracht statt $0 → $6.90 gerettet
  - Wenn Trigger bei 0.20c: hätte $34.46 gebracht → $15.51 gerettet

**Historical-Simulation (16 verlorene Positionen, -$152.10 gesamt):**

| Trigger | Erwartete Rettung | Qualität |
|---------|-------------------|---------|
| A: <=5c absolut, 10min | ~$2-5 | ❌ Zu spät, zu wenig |
| B: <=24h + <=15c | ~$20-35 | ✅ Beste Wirkung |
| C: <=30% Entry (nur >=40c Entry) | ~$8-15 zusätzlich | ✅ Ergänzend |

**Empfehlung: Trigger B + C kombiniert. Trigger A weglassen.**

Begründung für Trigger A-Skip:
- Bei 5c haben 100 Shares einen Wert von $5 — Sell-Order-Kosten kaum den API-Call
- Die meisten Sports-Märkte fallen DIREKT von einem mittleren Preis auf 0 (Resolution)
- Es gibt keine lange "5c-Phase" die zu erkennen wäre

---

## STATUS: T-M04d-Abhängigkeit

**PRÜFEN ZUERST:** Ist T-M04d bereits implementiert?

```bash
cd /root/KongTradeBot && git log --oneline -5 | grep -iE 'price.cap|take.profit|T-M04d'
```

Wenn T-M04d fertig: ExitManager hat bereits `_check_price_cap()` und `ExitState.price_cap_ticks_above`.
→ T-M04e baut darauf auf (gleiche Architektur, umgekehrte Richtung).

Wenn T-M04d NOCH NICHT fertig: T-M04e trotzdem implementierbar — aber Daily-Sell-Cap
muss in diesem Fall auch frisch eingebaut werden (nicht aus T-M04d wiederverwendbar).

---

## PHASE 1: Design-Verifikation (10min, READ-ONLY)

```bash
# Wie viele Positionen aktuell unter 15c?
curl -s "https://data-api.polymarket.com/positions?user=0x700BC51b721F168FF975ff28942BC0E5fAF945eb" | \
python3 -c "
import json,sys
data = json.loads(sys.stdin.read())
low = [(float(p.get('curPrice',0) or 0), float(p.get('currentValue',0) or 0), p.get('title','')[:50]) for p in data if float(p.get('curPrice',0) or 0) > 0 and float(p.get('curPrice',0) or 0) < 0.15]
for cp, cv, t in low: print(str(round(cp,3)), str(round(cv,2)), t)
print('Total low-price positions:', len(low))
"

# ExitState-Struktur prüfen (nach T-M04d):
grep -A12 'class ExitState' /root/KongTradeBot/core/exit_manager.py
```

---

## PHASE 2: Config erweitern (10min)

**Datei: `utils/config.py`**

```python
# Nach exit_price_cap-Zeilen (T-M04d), oder nach exit_min_hours_to_close:
exit_sl_enabled: bool = True
exit_sl_time_price_hours: float = 24.0      # Trigger B: <= N Stunden bis Close
exit_sl_time_price_cents: float = 0.15      # Trigger B: UND Preis <= X
exit_sl_drawdown_pct: float = 0.30          # Trigger C: Preis <= X% von Entry
exit_sl_drawdown_min_entry: float = 0.40    # Trigger C: nur wenn Entry >= 40c
exit_sl_cooldown_after_entry_min: int = 60  # Nicht innerhalb 60min nach Kauf
exit_sl_min_price_to_sell: float = 0.02     # Nicht unter 2c (Order-Book zu dünn)
exit_sl_max_events_per_hour: int = 3        # Emergency-Rate-Limit
exit_sl_spread_max: float = 0.05            # Sanity: Spread > 5c → überspringen
```

```python
# In Config.from_env():
exit_sl_enabled=os.getenv("EXIT_SL_ENABLED", "true").lower() == "true",
exit_sl_time_price_hours=float(os.getenv("EXIT_SL_TIME_PRICE_HOURS", "24.0")),
exit_sl_time_price_cents=float(os.getenv("EXIT_SL_TIME_PRICE_CENTS", "0.15")),
exit_sl_drawdown_pct=float(os.getenv("EXIT_SL_DRAWDOWN_PCT", "0.30")),
exit_sl_drawdown_min_entry=float(os.getenv("EXIT_SL_DRAWDOWN_MIN_ENTRY", "0.40")),
exit_sl_cooldown_after_entry_min=int(os.getenv("EXIT_SL_COOLDOWN_MINUTES", "60")),
exit_sl_min_price_to_sell=float(os.getenv("EXIT_SL_MIN_PRICE", "0.02")),
exit_sl_max_events_per_hour=int(os.getenv("EXIT_SL_MAX_PER_HOUR", "3")),
exit_sl_spread_max=float(os.getenv("EXIT_SL_SPREAD_MAX", "0.05")),
```

**Datei: `.env`**
```
EXIT_SL_ENABLED=true
EXIT_SL_TIME_PRICE_HOURS=24.0
EXIT_SL_TIME_PRICE_CENTS=0.15
EXIT_SL_DRAWDOWN_PCT=0.30
EXIT_SL_DRAWDOWN_MIN_ENTRY=0.40
EXIT_SL_COOLDOWN_MINUTES=60
EXIT_SL_MIN_PRICE=0.02
EXIT_SL_MAX_PER_HOUR=3
EXIT_SL_SPREAD_MAX=0.05
```

---

## PHASE 3: ExitState + ExitManager erweitern (45min)

**Datei: `core/exit_manager.py`**

### 3a) ExitState ergänzen

```python
@dataclass
class ExitState:
    # ... existing fields ...
    sl_done: bool = False                  # NEU: Stop-Loss ausgelöst (verhindert Doppel)
    entry_timestamp: float = field(default_factory=time.time)  # NEU: für Cooldown
```

### 3b) Rate-Limiter in ExitManager.__init__

```python
def __init__(self, ...):
    # ... existing ...
    self._sl_events_this_hour: int = 0     # NEU
    self._sl_hour_start: float = time.time()  # NEU
```

### 3c) Neue Methode `_check_stop_loss`

```python
def _check_stop_loss(
    self,
    pos,
    state: ExitState,
    current_price: float,
    hours_to_resolution: float,
) -> Optional[str]:
    """
    Gibt exit_type-String zurück ("sl_time_price" | "sl_drawdown") oder None.
    Enthält alle Sanity-Checks vor dem eigentlichen Trigger.
    """
    if not self.cfg.exit_sl_enabled:
        return None
    if state.sl_done:
        return None

    # Safety: Minimum-Preis (Order-Book zu dünn unter 2c)
    if current_price < self.cfg.exit_sl_min_price_to_sell:
        logger.debug(
            f"[ExitMgr] SL-Skip {pos.outcome}: Preis {current_price:.3f} < "
            f"Min {self.cfg.exit_sl_min_price_to_sell:.3f} (Order-Book dünn)"
        )
        return None

    # Safety: Cooldown nach Einstieg (keine SL-Trigger in ersten 60min)
    age_minutes = (time.time() - state.entry_timestamp) / 60
    if age_minutes < self.cfg.exit_sl_cooldown_after_entry_min:
        logger.debug(
            f"[ExitMgr] SL-Skip {pos.outcome}: Cooldown aktiv ({age_minutes:.0f}min "
            f"< {self.cfg.exit_sl_cooldown_after_entry_min}min)"
        )
        return None

    # Safety: Rate-Limit (max 3 SL pro Stunde)
    now = time.time()
    if now - self._sl_hour_start > 3600:
        self._sl_events_this_hour = 0
        self._sl_hour_start = now
    if self._sl_events_this_hour >= self.cfg.exit_sl_max_events_per_hour:
        logger.warning(
            f"[ExitMgr] ⛔ SL-Rate-Limit erreicht "
            f"({self._sl_events_this_hour}/{self.cfg.exit_sl_max_events_per_hour} diese Stunde)"
        )
        return None

    # Trigger B: Zeit + Preis kombiniert
    # Wirkung: Sports-Märkte nahe Ablauf mit kollabierendem Preis
    if (0 < hours_to_resolution <= self.cfg.exit_sl_time_price_hours
            and current_price <= self.cfg.exit_sl_time_price_cents):
        logger.info(
            f"[ExitMgr] 🔴 SL-TRIGGER B: {pos.outcome} @ {current_price:.3f} "
            f"(<= {self.cfg.exit_sl_time_price_cents}) mit {hours_to_resolution:.1f}h bis Close"
        )
        return "sl_time_price"

    # Trigger C: Drawdown-basiert (nur für High-Confidence-Entries >= 40c)
    # Wirkung: Starke Reversals bei gut gemeinten High-Price-Entries
    if (state.entry_price >= self.cfg.exit_sl_drawdown_min_entry
            and current_price <= state.entry_price * self.cfg.exit_sl_drawdown_pct):
        logger.info(
            f"[ExitMgr] 🔴 SL-TRIGGER C: {pos.outcome} @ {current_price:.3f} "
            f"<= {self.cfg.exit_sl_drawdown_pct*100:.0f}% von Entry {state.entry_price:.3f} "
            f"(drawdown {(1 - current_price/state.entry_price)*100:.0f}%)"
        )
        return "sl_drawdown"

    return None
```

### 3d) Stop-Loss in `evaluate_all()` einbauen

In der for-Schleife, NACH TP-Check und Price-Cap (T-M04d), VOR Trail-Check:

```python
# 3. Stop-Loss (NEU T-M04e) — unabhängig von TP
sl_type = self._check_stop_loss(pos, state, current_price, hours_to_resolution)
if sl_type:
    event = await self._execute_exit(pos, state, 1.0, sl_type, current_price)
    if event:
        events.append(event)
        state.sl_done = True
        self._sl_events_this_hour += 1
        self._remove_state(pos.market_id, pos.outcome)
        state_dirty = False
    continue

# 4. Trailing-Stop (existing)
```

### 3e) `_execute_exit`: Partial-Fill-Akzeptanz

Im Non-DRY-RUN Pfad in `main.py` (exit_loop), nach dem Sell-Call:

```python
# VORHER (exit_loop nach Stop-Loss-Event):
if result["success"]:
    pos.shares = round(pos.shares - result["shares_sold"], 6)
    if pos.shares <= 0:
        engine.open_positions.pop(ev.position_id, None)
        exit_manager._remove_state(ev.condition_id, ev.outcome)

# NACHHER (Partial-Fill-Akzeptanz):
if result["success"]:
    sold = result["shares_sold"]
    pos.shares = round(pos.shares - sold, 6)
    remaining = result.get("remaining_shares", 0)
    if pos.shares <= 0.001 or remaining <= 0.001:
        engine.open_positions.pop(ev.position_id, None)
        exit_manager._remove_state(ev.condition_id, ev.outcome)
    else:
        # Partial fill — Position bleibt, sl_done = True verhindert Re-Trigger
        logger.info(
            f"[exit_loop] Partial SL-Fill: {sold:.4f} verkauft, "
            f"{remaining:.4f} verbleiben — sl_done gesetzt"
        )
else:
    logger.error(f"[exit_loop] SL-Sell fehlgeschlagen: {result['error']}")
    # sl_done NICHT setzen — nächste Evaluierung kann es erneut versuchen
    state = exit_manager._states.get(f"{ev.condition_id}|{ev.outcome}")
    if state:
        state.sl_done = False
```

### 3f) Telegram-Alert für Stop-Loss

In main.py exit_event-Alert-Formatierung:
```python
type_emoji = {
    # ... existing ...
    "sl_time_price": "⏱ Stop-Loss (Zeit+Preis)",  # NEU
    "sl_drawdown":   "📉 Stop-Loss (Drawdown)",    # NEU
}.get(event.exit_type, event.exit_type)
```

---

## PHASE 4: DRY-RUN Test (20min)

```bash
# EXIT_DRY_RUN=true bereits in .env (oder setzen)
cd /root/KongTradeBot && python3 main.py --live
```

**Erwartetes DRY-RUN-Verhalten:**

Trigger B sollte sofort feuern für:
- "Trump announces end of military operations" (0.11c, wenn < 24h bis Close)
- Alle 0c-Positionen (redeemable=True) werden von SL NICHT angesprochen
  da `current_price=0 < exit_sl_min_price_to_sell=0.02` → SL überspringt sie

**Test-Beschleunigung:**
```bash
# Temporär in .env für aggressiveren Test:
EXIT_SL_TIME_PRICE_CENTS=0.30   # Fängt mehr Positionen
EXIT_SL_TIME_PRICE_HOURS=48     # Mehr Zeit-Fenster
EXIT_SL_COOLDOWN_MINUTES=0      # Kein Cooldown-Skip
```

Erwarteter Log:
```
[ExitMgr] 🔴 SL-TRIGGER B: Yes @ 0.110 (<= 0.300) mit 18.5h bis Close
[EXIT DRY-RUN] SELL 172.3 shares @ asset=0x...
```

---

## PHASE 5: Erster Live-Sell (nach DRY-RUN-Erfolg)

**Kandidat-Suche:**
```bash
curl -s "https://data-api.polymarket.com/positions?user=0x700BC51b721F168FF975ff28942BC0E5fAF945eb" | \
python3 -c "
import json,sys
data = json.loads(sys.stdin.read())
candidates = [(float(p.get('curPrice',0) or 0), float(p.get('currentValue',0) or 0), p.get('title','')[:50])
    for p in data
    if float(p.get('curPrice',0) or 0) > 0.02 and float(p.get('curPrice',0) or 0) < 0.20]
candidates.sort(key=lambda x: x[1])  # Kleinste zuerst
for cp, cv, t in candidates: print(str(round(cp,3)), str(round(cv,2)), t)
"
```

Erste echte Sell auf kleinsten Kandidaten:
```bash
# EXIT_DRY_RUN=false für diesen Test:
sed -i 's/EXIT_DRY_RUN=true/EXIT_DRY_RUN=false/' /root/KongTradeBot/.env
# (Bot-Reload abwarten oder neu starten)
```

Verifikation:
```bash
tail -30 /root/KongTradeBot/logs/bot_$(date +%Y-%m-%d).log | grep -E 'SL|SELL|stop_loss'
# Erwartung: ✅ SELL ORDER gefüllt + Telegram-Alert "⏱ Stop-Loss"
```

---

## PHASE 6: Tuning (nach erstem Live-Sell)

Nach erstem erfolgreichen Live-Sell die Schwellen final setzen:

```bash
# Konservative Produktion-Defaults (zurücksetzen von Test-Werten):
sed -i 's/EXIT_SL_TIME_PRICE_CENTS=.*/EXIT_SL_TIME_PRICE_CENTS=0.15/' /root/KongTradeBot/.env
sed -i 's/EXIT_SL_TIME_PRICE_HOURS=.*/EXIT_SL_TIME_PRICE_HOURS=24.0/' /root/KongTradeBot/.env
sed -i 's/EXIT_SL_COOLDOWN_MINUTES=.*/EXIT_SL_COOLDOWN_MINUTES=60/' /root/KongTradeBot/.env
```

---

## EDGE-CASES (im Code adressiert)

| Edge-Case | Handling |
|-----------|---------|
| Target-Wallet HÄLT Position die bei uns SL triggert | SL feuert unabhängig — Risk-Management über Signal. Config: `EXIT_SL_IGNORE_HELD=false` optional |
| Partial-Fill bei dünnem Order-Book | `sl_done=True` nach Versuch, Rest verbleibt; fehlt Neuerung in sl_done=False bei Fehler |
| News-Spike (großer Move in letzten 5min) | Covered durch `exit_sl_cooldown_after_entry_min=60` nach Einstieg; für spätere Spikes: separater Spike-Detector nötig (T-M04f) |
| Doppel-Trigger (SL + Trail beide bereit) | `continue` nach SL-Execute verhindert Trail-Check |
| Multiple SL in kurzer Zeit | `exit_sl_max_events_per_hour=3` kappt bei Stress-Test |
| Position schon redeemable (0c) | `current_price < exit_sl_min_price_to_sell=0.02` → SL überspringt sie |
| Copy-Trading-Konflikt: Whale hält, wir SL | Standard: unabhängig. Alternativ: `EXIT_SL_SKIP_IF_WHALE_HOLDS=true` als zukünftiger Toggle |
| Cooldown verletzt (Einstieg < 60min) | `age_minutes < cooldown` → Skip, nächste Evaluierung in 60s |

---

## CRITICAL STOPS

**STOP und fragen wenn:**

1. SL-Rate-Limit in erster Stunde schon erreicht → Schwellen zu aggressiv
2. Alle 24 Positionen triggern gleichzeitig (falsche Konfiguration)
3. `result["success"]=False` mit `error != "DRY-RUN"` — Order-Submission Fehler
4. `hours_to_resolution=0` für alle Positionen → `_hours_to_resolution()` defekt
5. Exit feuert auf Positionen mit Entry < 2 Tage → Cooldown funktioniert nicht

**Emergency-Stop:**
```bash
echo "EXIT_SL_ENABLED=false" >> /root/KongTradeBot/.env
# ODER:
echo "EXIT_ENABLED=false" >> /root/KongTradeBot/.env  # Stoppt alle Exits
```

---

## DEPLOYMENT (Commits je Phase)

```
Phase 2: feat(config): Stop-Loss Config (Trigger B+C, Rate-Limit, Sanity-Checks)
Phase 3: feat(exit_manager): Stop-Loss-Trigger T-M04e (sl_time_price + sl_drawdown)
Phase 4: test: DRY-RUN Stop-Loss verifiziert (Log-Output beifügen)
Phase 5: feat: Stop-Loss Live-Sell aktiviert (EXIT_DRY_RUN=false)
Phase 6: fix(config): Produktions-Schwellen finalisiert
```

---

## ABSCHLUSSBERICHT (Server-CC nach Implementation)

1. **DRY-RUN erfolgreich?** Welche Positionen haben Trigger B/C ausgelöst?
2. **Erster Live-Sell?** Position + Preis + USDC erhalten + TX-Hash
3. **Rate-Limit-Test?** Kurz auf 1 setzen, prüfen ob Block funktioniert
4. **Partial-Fill simuliert?** Manuell shares_to_sell > available setzen
5. **Telegram-Alert korrekt?** Screenshot "⏱ Stop-Loss (Zeit+Preis)"
6. **Offene Fragen:** `EXIT_SL_IGNORE_HELD` implementiert? Spike-Cooldown nötig?

---

## OFFENE FRAGEN (Onur entscheidet vor Implementation)

1. **Trigger-C aktivieren oder nur Trigger B?**
   Trigger C (<=30% von Entry bei >=40c Entry) feuert auf Positionen wie "Will AD Pasto" (Entry 0.74c).
   Von unseren 16 Verlusten: ~3 Positionen hätten Trigger C getroffen.
   Empfehle: Trigger B + C beide an. Trigger C ist konservativ (nur High-Entry-Positionen).

2. **15c Trigger-B-Schwelle oder eher 10c?**
   Bei 15c: Trump-Operations-Position würde jetzt NICHT mehr triggern (0.11c < 0.15c, aber schon unterhalb)
   → Hat 0.11c noch Sell-Wert? 172 Shares × $0.11 = $18.95 — ja, noch nicht leer.
   Bei 10c: vorsichtiger, weniger False-Positives.
   Empfehle: 0.15c für Starter, dann auf Basis echter Fills tunen.

3. **Cooldown 60min oder 120min?**
   Bei sehr dynamischen Märkten (Iran-Deals) können Positionen schnell >50% fallen.
   60min Cooldown ist Kompromiss zwischen "zu früh aussteigen" und "zu spät".

4. **Was tun mit den 13 bereits-0c-REDEEMABLE Positionen?**
   Stop-Loss kann sie nicht retten (Preis = 0). T-M04b (Auto-Claim) würde sie auflösen.
   → Für SL irrelevant, aber Prompt hier als Hinweis: Diese werden von SL übersprungen (< 2c-Guard).
