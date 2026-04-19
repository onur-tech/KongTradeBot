# Morgen-Plan 2026-04-20 (Montag)

_Erstellt: 2026-04-19 Abend | Für: Ersten Arbeitstag nach intensiver Sonntag-Session_
_Update: 2026-04-19 23:59 — T-M04f bereits deployed (4d0b9bf), Cap sofort erhöhbar_

---

## Lage beim Aufwachen

| Thema | Status |
|-------|--------|
| **Bot** | Live, Exit-Modus aktiv, DRY_RUN=false, EXIT_DRY_RUN=false |
| **Daily-Sell-Cap** | $30 (kann sofort auf $60+ erhöht werden — T-M04f deployed) |
| **Duplicate-Bug** | ✅ BEHOBEN (4d0b9bf, whale_exit_triggered Once-Only-Flag) |
| **T-M08 Phase 1-3** | ✅ DEPLOYED (9f4ba4b/30791e4/9dcd2e0) — Phase 4+5 ausstehend |
| **Heiße Position** | US x Iran ceasefire bei ~78c, Resolution 21.04. |
| **Daily-Summary Timer** | ✅ Aktiv seit 3364181 — erster Alert gestern Abend 20:00 |

---

## Priorisierte Reihenfolge

### PRIO 1 — T-M08 Phase 4: Migration bestehender Positionen (~30 Min) 🔴 KRITISCH

**Warum zuerst:** Ohne Migration haben die 24 existierenden Positionen keinen korrekten
`position_state` im bot_state.json. Phase 5 (Exit-Guard) kann ohne korrekte States nicht sicher arbeiten.

**Prompt:** `prompts/t_m08_phase4_migration.md`
**Server-CC Task** (SSH auf 89.167.29.183)

Kurzfassung:
1. Backup `bot_state.json` mit Timestamp
2. Python-Migrations-Skript via heredoc auf Server schreiben
3. Skript ausführen — Wuning + Busan werden als CLAIMED erkannt
4. STOP-CHECKs: CLAIMED=2, ACTIVE ~11, nicht 0 oder >15
5. Bot-Restart — Log zeigt Positionen mit restaurierten States

**DANN:** Cap $30 → $60 (`EXIT_DAILY_SELL_CAP_USD=60` in `.env` + Restart)

---

### PRIO 2 — T-M08 Phase 5: Exit-Guard Integration (~20-30 Min) 🔴

**Warum:** ExitManager läuft aktuell auf allen 24 Positionen inkl. 13 RESOLVED_LOST.
Ohne Guard entstehen unnötige Sell-Versuche auf bereits abgeschlossene Positionen.

**Prompt:** `prompts/t_m08_phase5_exit_guard_integration.md`
**Voraussetzung:** Phase 4 STOP-CHECKs bestanden

Kurzfassung:
1. `position_state: str = "ACTIVE"` in OpenPosition dataclass (`execution_engine.py`)
2. Guard in `evaluate_all()` direkt nach `_get_or_create_state()`:
   ```python
   position_state = getattr(pos, "position_state", "ACTIVE")
   if position_state in ("RESOLVED_WON", "RESOLVED_LOST", "CLAIMED", "TRADING_ENDED"):
       continue
   ```
3. State-Update im `exit_loop` (main.py:926+) vor `evaluate_all()`
4. Syntax-Check + DRY-RUN-Test
5. Bot-Restart — Log zeigt `[exit_guard] Skip` für RESOLVED-Positionen

---

### PRIO 3 — Cap-Erhöhung $30 → $60 → $100 (~5 Min) 🟡

**Voraussetzungen:**
- `[ ]` T-M08 Phase 4 STOP-CHECKs bestanden
- `[ ]` Bot stabil nach Phase 5 Deployment
- `[ ]` Kein laufendes Exit-Event auf US x Iran

```bash
# Schritt 1: $30 → $60 (sofort nach Phase 4/5)
EXIT_DAILY_SELL_CAP_USD=60   # .env auf Server
sudo systemctl restart kongtrade-bot

# Schritt 2 (nach 1h stabiler Betrieb): $60 → $100
EXIT_DAILY_SELL_CAP_USD=100
```

**Längerfristig:** $100 → $200 wenn 24h stable (nächste Session entscheiden).

---

### PRIO 4 — Beobachtungsphase (~15 Min) 🟡 (Event-getrieben)

```bash
# Echtzeit-Log Monitor:
tail -f /root/KongTradeBot/logs/bot_2026-04-20.log | grep -iE 'exit_guard|whale|trigger|sell|cap|state'
```

**Was prüfen:**
- `[ ]` Daily-Summary 20:00 gestern korrekt ausgeliefert? (Telegram-History prüfen)
- `[ ]` Whale-Exit: genau 1x Log wenn Trigger, dann silence ✅ (T-M04f deployed)
- `[ ]` US x Iran ceasefire: Preis ~78c → kein Trigger unter 95c
- `[ ]` Exit-Guard Skip-Messages für 13 RESOLVED_LOST Positionen

---

### PRIO 5 — US x Iran Ceasefire Live-Watch 🟠 (Event-getrieben)

**Position:** "US x Iran permanent peace deal by April"
**Aktueller Preis:** ~78c (Stand Abend 19.04.)
**Resolution:** 21.04.2026 (übermorgen!)

**Wenn Preis ≥90c:** Manuell entscheiden — T-M04d ist deployed (e5d64e8), sollte bei 95c feuern.
**Wenn Market resolved WON:** Telegram-Alert von T-M04b kommt → manuell claimen.

---

## Offene Implementation-Prompts (ready für Server-CC)

| Prompt | Task | Prio | Status |
|--------|------|------|--------|
| `prompts/t_m08_phase4_migration.md` | Phase 4 Migration | 🔴 JETZT | Prompt ready |
| `prompts/t_m08_phase5_exit_guard_integration.md` | Phase 5 Exit-Guard | 🔴 HEUTE | Prompt ready |
| `prompts/t_m04e_stop_loss.md` | Stop-Loss-Trigger | 🟡 Diese Woche | Prompt ready |
| `prompts/t_m08_position_state_implementation.md` | Phase 1-3 Kontext | ✅ DEPLOYED | 9f4ba4b/30791e4/9dcd2e0 |
| `prompts/t_m04f_duplicate_trigger_fix.md` | Duplicate-Fix | ✅ DEPLOYED | 4d0b9bf |

---

## Beobachtungs-Liste (neue Änderungen aus heutiger Session)

**Daily-Summary Timer (3364181):**
- Erster Alert gestern Abend 20:00 — kam er? Welche Daten?
- Format korrekt? Portfolio-Stand + P&L?

**T-M08 Phase 1-3 (9f4ba4b/30791e4/9dcd2e0):**
- Dashboard zeigt noch 24 OPEN — erst nach Phase 4 Migration korrekt
- State-Machine Worker läuft alle 300s — Log prüfen ob State-Updates ankommen

**Erasmus + TheSpiritofUkraine (T-M07, b97d9ef):**
- Erste Signale empfangen? Welche Märkte?
- Multiplier effektiv 1.0x (war .env-Diskrepanz — 69cf69a hat korrigiert)

**Archive-Drift:**
- Bleibt bei ~84.9% bis T-M06 deployed — keine neuen Maßnahmen nötig

---

## Bekannte Dauerhaft-Limitations

| Bug | Status | Plan |
|-----|--------|------|
| Archive-Drift 84.9% | nicht gefixt | T-M06 (nach T-M04b) |
| Position-State-Bug | Phase 1-3 deployed, Phase 4+5 morgen | T-M08 Prompts ready |
| Auto-Claim | Notification-only | P082-Design — so bleibt es |
| Resolver auto-save | Phase 3 deployed (9dcd2e0) | ✅ |

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

---

## Session-End-Checklist (19.04. Abend — alle erledigt ✅)

```
[✅] T-M04f Duplicate-Trigger deployed (4d0b9bf)
[✅] Watchdog-Fix deployed (7ed82ac)
[✅] Daily-Summary Timer deployed (3364181)
[✅] log_trade-Fix deployed (4537924)
[✅] Legacy-Flag deployed (5980e02)
[✅] T-M08 Phase 1-3 deployed (9f4ba4b/30791e4/9dcd2e0)
[✅] T-M08 Phase 4+5 Prompts ready (0a261e8)
[✅] RN1-Diagnose documented (53809e1)
[✅] P085 Multi-Signal-Buffer KB-Eintrag
[✅] WALLETS.md + STATUS.md aktuell (10b186e)
[✅] Bot läuft stabil auf Server
```

---

_Gute Nacht. Morgen: T-M08 Phase 4 Migration zuerst, dann Phase 5 Exit-Guard, dann Cap erhöhen._
