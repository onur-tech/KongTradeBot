# Morgen-Plan 2026-04-20 (Montag)

_Erstellt: 2026-04-19 Abend | Für: Ersten Arbeitstag nach intensiver Sonntag-Session_

---

## Lage beim Aufwachen

| Thema | Status |
|-------|--------|
| **Bot** | Live, Exit-Modus aktiv (DRY-RUN aufgehoben für Whale-Exit) |
| **Daily-Sell-Cap** | $30 (bewusst niedrig — Duplicate-Bug nicht gefixt) |
| **Kritischer Bug** | Whale-Exit Re-Trigger (7x Loop) — Diagnose done, Fix pending |
| **Heiße Position** | US x Iran ceasefire bei ~78c, Resolution 21.04. |
| **T-M04d** | Take-Profit >=95c Trigger — Prompt ready, nicht deployed |
| **T-M09b** | Multiplier-Fix deployed (f237dbe), aber 4 Wallets haben .env-Diskrepanz |

---

## Priorisierte Reihenfolge

### PRIO 1 — Duplicate-Trigger-Fix (~25 min) 🔴 KRITISCH

**Warum zuerst:** Ohne Fix blockiert jede Cap-Erhöhung und jede Exit-Aktivierung das Risiko-Management.

**Prompt:** `prompts/t_m04f_duplicate_trigger_fix.md`
**Server-CC Task** (SSH auf 89.167.29.183)

Kurzfassung:
1. `core/exit_manager.py` — `ExitState` Dataclass: `whale_exit_triggered: bool = False` hinzufügen
2. `evaluate_all()` Whale-Exit-Block: Flag setzen auch bei `None`-Return (Cap-Block)
3. Syntax-Check + Backward-Compat-Test (5 min)
4. Bot-Restart
5. 5 Minuten Log beobachten — kein Duplicate-Trigger

**DANN:** Cap $30 → $60 (`EXIT_DAILY_SELL_CAP_USD=60` in `.env` + Restart)

---

### PRIO 2 — Beobachtungsphase (~15 min) 🟡

Nach Duplicate-Fix:

```bash
# Echtzeit-Log Monitor:
tail -f /root/KongTradeBot/logs/bot_2026-04-20.log | grep -iE 'whale|exit|trigger|sell|cap'
```

**Was beobachten:**
- Whale-Exit: genau 1x Log wenn Trigger, dann silence ✅
- T-M04d (Price-Trigger >=95c): noch nicht deployed → darf nicht feuern
- US x Iran ceasefire bei 78c → wenn sie sich 95c nähert: Alarm

**Checkpoint:**
- `[ ]` Kein Duplicate-Trigger im Log
- `[ ]` Cap-Erhöhung auf $60 confirmed

---

### PRIO 3 — WALLETS.md + .env Diskrepanz-Fix (~20 min) 🟡

**Kontext (aus heutiger Session, Diskrepanz-Report):**

4 Wallets haben Code ≠ .env WALLET_WEIGHTS:

| Wallet | Alias | Code-Intent | Effektiv (.env) |
|--------|-------|-------------|-----------------|
| 0xde7be6...5f4b | wan123 | 0.5x | 1.0x (default) |
| 0xefbc5f...f9a2 | reachingthesky | 2.0x | 1.0x (explizit) |
| 0xc6587b...b784 | Erasmus | 0.5x | 1.0x (default) |
| 0x0c0e27...434e | TheSpiritofUkraine | 0.3x | 1.0x (default) |

**Frage an Onur:** Welche Werte gelten? Code-Intent oder aktuelle .env?

Falls Code-Intent gilt → SSH `.env` korrigieren:
```bash
# Auf Server ausführen (P083-Protokoll):
# 1. Code (copy_trading.py) — bereits korrekt
# 2. .env WALLET_WEIGHTS ergänzen:
WALLET_WEIGHTS={"0x019782cab5d844f0":1.5,"0x492442eab586f242":0.3,"0x02227b8f5a9636e8":0.5,"0xefbc5fec8d7b0acd":1.0,"0x0B7A6030507efE5D":1.0,"0xbaa2bcb5439e985c":1.0,"0xde7be6d489bce070":0.5,"0xc6587b11a2209e46":0.5,"0x0c0e270cf879583d":0.3,"default":1.0}
# 3. Bot-Restart
# 4. Log: "Wallet X geladen mit Multiplier Y"
```

Danach: WALLETS.md vollständig neu aufbauen (Windows-CC Task).

---

### PRIO 4 — US x Iran Ceasefire Live-Beobachtung 🟠 (Event-getrieben)

**Position:** "US x Iran permanent peace deal by April"
**Aktueller Preis:** ~78c (Stand Abend 19.04.)
**Resolution:** 21.04.2026

**Was passieren kann:**
- Preis steigt auf ≥95c → T-M04d würde feuern (wenn deployed)
- T-M04d ist noch NICHT deployed — daher heute kein Auto-Sell
- Bot würde nur via Whale-Exit reagieren (falls Whale-Wallet verkauft)

**Wenn Preis ≥90c und T-M04d noch nicht live:**
→ Manuell entscheiden: Claim-Button auf Dashboard drücken wenn market resolved?
→ Oder T-M04d schnell deployen (Prompt ready: `prompts/t_m04d_take_profit_trigger.md`)

**T-M04d Deployment-Entscheidung:** Nur wenn Duplicate-Fix (PRIO 1) bereits durch.

---

### PRIO 5 — Cap-Erhöhung Stufe 2 (~5 min) 🟢

**Voraussetzungen:**
- `[ ]` Duplicate-Trigger-Fix deployed + verifiziert
- `[ ]` Mindestens 1h sauberer Betrieb nach Fix
- `[ ]` Kein laufendes Exit-Event auf US x Iran

**Dann:** $60 → $100 oder $60 → $200 (je nach Komfort-Level)
Empfehlung: $60 → $100 für 24h, dann auf $200 wenn stable.

```bash
# .env auf Server:
EXIT_DAILY_SELL_CAP_USD=100
# Bot-Restart + 5 min beobachten
```

---

## Offene Implementation-Prompts (ready für Server-CC)

| Prompt | Task | Prio | Abhängigkeit |
|--------|------|------|--------------|
| `prompts/t_m04f_duplicate_trigger_fix.md` | Whale-Exit Once-Only-Flag | 🔴 JETZT | — |
| `prompts/t_m04d_take_profit_trigger.md` | Take-Profit >=95c | 🟡 Heute | nach T-M04f |
| `prompts/t_m04e_stop_loss.md` | Stop-Loss-Trigger | 🟡 Heute/Morgen | nach T-M04d |
| `prompts/t_m08_position_state_implementation.md` | Position-State-Machine | 🟢 Diese Woche | nach T-M04e |

---

## Beobachtungs-Liste (neue Änderungen aus heutiger Session)

**Erasmus + TheSpiritofUkraine (T-M07, b97d9ef):**
- Erste Signale empfangen? Welche Märkte?
- Multiplier effektiv 1.0x (Diskrepanz — s. PRIO 3)
- Signal-Qualität: Geopolitics/Iran-Nische?

**Multiplier-Kalibrierung (T-M09b, f237dbe):**
- April#1 Sports: 0.3x — keine neuen Trades erwartet
- HOOK: 1.0x — war 2.0x, Positions-Größen sollten kleiner sein
- majorexploiter: 1.5x — war 3.0x, halbe Größen

**Archive-Drift-Verbesserung:**
- Heute: resolver auto-save noch nicht deployed
- Erwartet: archive bleibt bei ~84.9% Drift bis T-M06 deployed

---

## Bekannte Dauerhaft-Limitations

| Bug | Status | Plan |
|-----|--------|------|
| Archive-Drift 84.9% | nicht gefixt | T-M06 (nach T-M04b) |
| Position-State-Bug | Dashboard OPEN=25 statt 11 | T-M08 (Prompt ready) |
| Auto-Claim | Notification-only | P082-Design — so bleibt es |
| Resolver auto-save | manuell nötig | In T-M06 enthalten |

---

## Notfall-Prozeduren

### Bot-Stop (sofort)
```bash
sudo systemctl stop kongtrade-bot
```

### Kill-Switch via Telegram
```
/kill_switch — Bot stoppt neue Trades, lässt laufende offen
```

### Emergency-Stop für Sells
```bash
# In .env:
EXIT_AUTO_SELL_EMERGENCY_STOP=true
# Dann Bot-Restart — _execute_exit unterdrückt alle Sells
```

### Bot-Restart nach Code-Änderung
```bash
sudo systemctl restart kongtrade-bot
sleep 5
journalctl -u kongtrade-bot -n 30
```

### Falls Exit-Loop hängt
```bash
# Log prüfen:
tail -50 /root/KongTradeBot/logs/bot_$(date +%F).log | grep -i error
# Bot-Restart ist immer safe (State in bot_state.json persistiert)
```

---

## Session-End-Checklist (heute Abend)

```
[ ] Duplicate-Trigger-Bug Diagnose committed (1fd7ade) ✅
[ ] Fix-Prompt (t_m04f) erstellt ✅
[ ] WALLETS.md Diskrepanz-Report existiert (in Chat, nicht commited) 
[ ] KB P084 (Duplicate-Trigger-Pattern) commited ✅
[ ] Cap bei $30 belassen (Sicherheit) ✅
[ ] Bot läuft stabil auf Server ✅
```

---

_Gute Nacht. Morgen: Duplicate-Fix zuerst, dann alles andere._
