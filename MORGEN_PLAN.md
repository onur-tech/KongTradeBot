# Morgen-Plan 2026-04-21 (Dienstag)

_Erstellt: 2026-04-20 | Nach intensiver Lern- + Implementations-Session_

---

## Lage beim Aufwachen

| Thema | Status |
|-------|--------|
| **Bot** | Live, T-M08 Phase 4+5 deployed, Exit-Guard aktiv |
| **Daily-Sell-Cap** | $60 (erhöht heute) |
| **Externe Lernpunkte** | Alle deployed (polymarket-cli, retry, NEG_RISK, balance_cli) |
| **WALLETS.md** | Korrekte Multiplier synced (T-M09 + T-M07) |
| **US×Iran** | Resolution 21.04. — scharf beobachten! |
| **KB** | P086–P089 dokumentiert (Proxy-Tokens, redeemable-API, CLI-Limits, Retry) |

---

## PRIO 1 — US×Iran Live-Watch 🔴 EVENT-GETRIEBEN

**Position:** "US x Iran permanent peace deal by April"
**Resolution: HEUTE (21.04.2026)!**

```bash
# Preis alle 5min prüfen:
curl -s http://localhost:5000/api/portfolio | python3 -c "
import json, sys
d = json.load(sys.stdin)
for p in d['positions']:
    if 'Iran' in p.get('market',''):
        print(p['market'][:60], '→', p['cur_price_pct'], 'c')
"
```

**Was passieren kann:**
- Preis ≥95c → T-M04d feuert automatisch (e5d64e8 deployed)
- Market resolved WON → Telegram-Alert von T-M04b → manuell claimen via Polymarket UI
- Market resolved LOST → Position wird RESOLVED_LOST, kein Claim nötig

**Bei WON + kein Auto-Alert:** Dashboard aufrufen → CLAIM-Button

---

## PRIO 2 — T-M13: ?redeemable=true in Phase 2 Worker 🟡

**Was:** Phase 2 Worker aktuell nutzt N Gamma-API-Calls für State-Detection.
`?redeemable=true` Endpoint (P087) liefert alle resolved Positionen in 1 Call.

**Server-CC Task:**
```bash
# Prüfen was Phase 2 Worker aktuell macht:
grep -n 'redeemable\|gamma\|state.*worker\|phase2' /root/KongTradeBot/dashboard.py | head -20
```

Dann Worker auf `?redeemable=true` Endpoint umstellen.

---

## PRIO 3 — Wallet-Multiplier .env Sync prüfen 🟡

WALLETS.md zeigt korrekte Multiplier (T-M09 + T-M07, Docs-seitig aktuell).
Aber ist `.env WALLET_WEIGHTS` auf Server auch aktuell?

```bash
# Auf Server prüfen:
grep WALLET_WEIGHTS /root/KongTradeBot/.env
```

**Soll-Werte (P083-Protokoll):**
```
majorexploiter: 1.5x | reachingthesky: 1.0x | kcnyekchno: 1.0x | denizz: 1.0x
HorizonSplendidView: 0.5x | wan123: 0.5x | Erasmus: 0.5x
TheSpiritofUkraine: 0.3x | April#1 Sports: 0.3x | HOOK: 1.0x
```

Falls Diskrepanz: `.env` korrigieren + Bot-Restart + Log-Verify.

---

## PRIO 4 — Cap $60 → $100 (wenn 24h stabil) 🟢

**Voraussetzungen:**
- `[ ]` T-M08 Phase 4+5 stabil (Exit-Guard keine Fehler)
- `[ ]` Mindestens 24h ohne unerwartete Exit-Events
- `[ ]` US×Iran Position abgeschlossen (WON oder LOST)

```bash
# .env auf Server:
EXIT_DAILY_SELL_CAP_USD=100
sudo systemctl restart kongtrade-bot
sleep 5
journalctl -u kongtrade-bot -n 10
```

---

## PRIO 5 — T-M04e Stop-Loss (wenn Zeit) 🟢

**Prompt:** `prompts/t_m04e_stop_loss.md`
**Abhängigkeit:** T-M08 Phase 4+5 stabil

Trigger B: Preis sinkt 15c+ nach 24h Haltezeit
Trigger C: Drawdown 30%/40c gegenüber Entry-Preis

---

## Offene Implementation-Prompts (ready)

| Prompt | Task | Prio |
|--------|------|------|
| `prompts/t_m04e_stop_loss.md` | Stop-Loss-Trigger | 🟡 Diese Woche |
| `prompts/t_m08_phase4_migration.md` | Phase 4 Migration | ✅ Heute erledigt |
| `prompts/t_m08_phase5_exit_guard_integration.md` | Phase 5 Exit-Guard | ✅ Heute erledigt |

---

## Beobachtungs-Liste

**T-M08 Phase 4+5 (heute deployed):**
- Exit-Guard Skip-Messages im Log für 13 RESOLVED_LOST?
- Dashboard zeigt ~11 ACTIVE statt 24?
- bot_state.json: Wuning + Busan als CLAIMED?

**Daily-Summary Timer (3364181):**
- 20:00 Telegram-Alert: kam er? Format korrekt?

**Erasmus + TheSpiritofUkraine:**
- Erste Signale? Gegenseitige Bestätigung via Multi-Signal-Buffer?

---

## Notfall-Prozeduren

### Bot-Stop
```bash
sudo systemctl stop kongtrade-bot
```

### Emergency-Stop für Sells
```bash
# In .env:
EXIT_AUTO_SELL_EMERGENCY_STOP=true
sudo systemctl restart kongtrade-bot
```

### Bot-Restart (nach Code-Änderung)
```bash
sudo systemctl restart kongtrade-bot
sleep 5
journalctl -u kongtrade-bot -n 30
```

---

_Heute entscheidet US×Iran. T-M04d ist live — kein manueller Eingriff nötig wenn Preis ≥95c._
