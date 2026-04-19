# KongTradeBot — Live Status
_Stand: 2026-04-19 23:59 (finale Session-Doku)_
_Nächstes Update: 2026-04-20 Morgen nach T-M08 Phase 4+5_

---

## Bot-Zustand

| Feld | Wert |
|------|------|
| **Running** | ✅ Active (`systemctl is-active kongtrade-bot`) |
| **Soft-Live seit** | 2026-04-19 14:02 (Exit-DRY-RUN deaktiviert) |
| **Letzter Commit Server** | `9dcd2e0` (T-M08 Phase 3: Resolver auto-save) |
| **Letzter Commit Docs** | `0a261e8` (T-M08 Phase 4+5 Prompts) |
| **DRY_RUN** | `false` (Trades live) |
| **EXIT_DRY_RUN** | `false` (Exit-Sells live) |
| **Daily-Sell-Cap** | `$30` (erhöhbar auf $60 nach T-M08 Phase 4 morgen früh) |
| **Duplicate-Bug** | ✅ BEHOBEN (4d0b9bf — whale_exit_triggered Flag) |
| **Dashboard** | Via Cloudflare Tunnel (URL in .env) |
| **Daily-Summary Timer** | ✅ Aktiv 20:00 Berlin (3364181) |
| **State-Machine** | ✅ Läuft (Worker alle 300s — Phase 1-3 deployed) |

---

## Portfolio (Stand: 2026-04-19 ~15:51)

| Metrik | Wert |
|--------|------|
| **Total Portfolio** | ~$866 USDC |
| **Cash** | ~$463 USDC |
| **In Positionen** | ~$403 USDC |
| **Offene Positionen** | 24 (Dashboard), davon ~11 wirklich aktiv |
| **Dashboard-Diskrepanz** | 13 RESOLVED_LOST + 0 WON = 13 faktisch beendet (T-M08 Bug) |

---

## Heutige Realisierungen (19.04.2026)

| Event | Betrag |
|-------|--------|
| Wuning — Manueller Claim | +$50.13 USDC |
| Busan — Manueller Claim | +$39.00 USDC |
| **Gesamt realisiert** | **+$89.13 USDC** |
| Heute P&L (Archive) | ca. -$11.26 (inkl. historische DRY-RUN-Verlierer) |

---

## Aktive Features (deployed, live)

| Feature | Status | Commit |
|---------|--------|--------|
| Position-Restore bei Restart | ✅ Live | 57ff2e7 (T-M04a) |
| Take-Profit-Trigger >=95c + 10min Stability | ✅ Live | e5d64e8 (T-M04d) |
| Claim-Notification via Telegram | ✅ Live | 3a7b4a9 (T-M04b Notification-only) |
| Exit-Events im Archive mit PnL | ✅ Live | 4537924 (log_trade Fix) |
| Multiplier Code+.env sync | ✅ Live | 69cf69a (P083 Fix) |
| Whale-Follow-Exit (Once-Only) | ✅ Live, Duplicate-Bug behoben | 4d0b9bf (T-M04f) |
| Trailing-Stop | ✅ Live | 35c3f43 |
| TP-Staffel (tp1/tp2/tp3) | ✅ Live | 35c3f43 |
| Daily-Summary Telegram 20:00 | ✅ Live | 3364181 |
| Position-State-Machine Phase 1-3 | ✅ Live (Migration Phase 4 ausstehend) | 9dcd2e0 |
| Legacy SELL-Einträge geflagged | ✅ Live | 5980e02 |

---

## Bekannte Bugs (offen)

| Bug | Severity | Diagnose | Fix-Plan |
|-----|----------|---------|---------|
| ~~Duplicate-Trigger (Whale-Exit Loop)~~ | ✅ BEHOBEN | 1fd7ade | 4d0b9bf deployed |
| Position-State (Dashboard OPEN=24 statt ~11) | 🟡 Kosmetisch | f20e29e | T-M08 Phase 4+5 **MORGEN** — Prompts ready |
| Archive-Drift 84.9% Ghost-Einträge | 🟡 Audit-Problem | 442185e | T-M06, nach T-M04b |
| 13 Legacy SELL-Einträge ohne PnL | 🟢 Historisch | 5980e02 | Geflagged, nicht rekonstruierbar |

---

## Wallet-Konfiguration (Stand 69cf69a)

10 aktive TARGET_WALLETS, Code == .env WALLET_WEIGHTS ✅ (vollständig synced)

| Alias | Multiplier | Tier | Status |
|-------|-----------|------|--------|
| majorexploiter | 1.5x | A | Active |
| reachingthesky | 1.0x | A | Active |
| kcnyekchno | 1.0x | A | Active (0 Trades bisher) |
| denizz | 1.0x | A | Active |
| HOOK | 1.0x | B | ⚠ WATCHING (46 Trades, unter HF-1) |
| HorizonSplendidView | 0.5x | A | Inaktiv (0 Activity) |
| wan123 | 0.5x | A | Active (Moonshot-Flag) |
| Erasmus | 0.5x | B | ⚠ NEU 19.04. — 30d Review 19.05. |
| April#1 Sports | 0.3x | B | ⚠ WATCHING (HF-8/10 FAIL) |
| TheSpiritofUkraine | 0.3x | B | ⚠ NEU 19.04. — 30d Review 19.05. |

→ Vollständige Details: `WALLETS.md`

---

## Architektur-Limits (permanent)

| Limit | Grund | Plan |
|-------|-------|------|
| Auto-Claim nicht möglich | Custodial-Architektur P082 (Gnosis Safe + Magic.link) | Notification-System ist korrekter Endzustand |
| Relayer-Claim braucht PRIVATE_KEY | P079 — RelayClient konfiguriert aber T-M04b v2 in Arbeit | T-M04b v2 mit relayer-v2 |

---

## Heiße Positionen (Watch-List)

| Position | Preis | Resolution | Trigger |
|----------|-------|-----------|---------|
| US x Iran permanent peace deal by April | ~78c | 21.04.2026 | T-M04d >=95c feuert wenn Preis steigt |

---

## Nächste Aktionen (MORGEN_PLAN.md)

```
PRIO 1: T-M08 Phase 4 Migration (~30 min) — Prompt: prompts/t_m08_phase4_migration.md
PRIO 2: T-M08 Phase 5 Exit-Guard (~20 min) — Prompt: prompts/t_m08_phase5_exit_guard_integration.md
PRIO 3: Cap-Erhöhung $30 → $60 → $100 nach Phase 4+5 (sofort möglich — Duplicate-Fix deployed)
PRIO 4: US x Iran ceasefire beobachten (78c → 95c = T-M04d feuert, Resolution 21.04)
PRIO 5: Daily-Summary 20:00 prüfen — kam erster Auto-Alert korrekt?
```

---

_Für vollständige Session-Chronologie: `SESSION_RECAPS/2026-04-19.md`_
_Für Task-Queue: `TASKS.md` (IN ARBEIT: T-M04b | QUEUE: T-M04f, T-M04d, T-M04e, T-M08)_
