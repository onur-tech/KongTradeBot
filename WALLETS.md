# KongTradeBot — Target Wallets
_Stand: 2026-04-20 | Sync-Commit: Deep-Discovery | Multiplier-Review: T-M09 2026-04-19_

**Dual-Source-Invariante (KB P083):** Jede Multiplier-Änderung erfordert Update in
`strategies/copy_trading.py WALLET_MULTIPLIERS` UND `.env WALLET_WEIGHTS` + Bot-Restart.

---

## Aktive Wallets (10)

### Tier A — Etabliert

| Adresse | Alias | Kategorie | Multiplier | Aufnahme | Quelle | Letzte Review |
|---------|-------|-----------|------------|----------|--------|---------------|
| `0x019782cab5d844f02bafb71f512758be78579f3c` | **majorexploiter** | Sports/UCL | **1.5x** | 17.04.2026 | polymonit | T-M09 2026-04-19 (war 3.0x) |
| `0xefbc5fec8d7b0acdc8911bdd9a98d6964308f9a2` | **reachingthesky** | Politik/Mixed | **1.0x** | 17.04.2026 | wallet_init | 69cf69a 2026-04-19 (Code+.env sync) |
| `0x7177a7f5c216809c577c50c77b12aae81f81ddef` | **kcnyekchno** | Allgemein | **1.0x** | 17.04.2026 | wallet_init | T-M09 2026-04-19 (war 2.0x) |
| `0xbaa2bcb5439e985ce4ccf815b4700027d1b92c73` | **denizz** | Politics/Soccer | **1.0x** | 17.04.2026 | polymonit | T-M09 2026-04-19 (explizit auf 1.0x) |
| `0x02227b8f5a9636e895607edd3185ed6ee5598ff7` | **HorizonSplendidView** | Sports | **0.5x** | 17.04.2026 | predicts.guru | T-M09 2026-04-19 (war 2.0x, 0 Activity) |
| `0xde7be6d489bce070a959e0cb813128ae659b5f4b` | **wan123** | Allgemein | **0.5x** | 17.04.2026 | wallet_init | T-M09 2026-04-19 (war 2.5x, neg. ROI) |

### Tier B — Experimental / Watching

| Adresse | Alias | Kategorie | Multiplier | Aufnahme | Quelle | Letzte Review |
|---------|-------|-----------|------------|----------|--------|---------------|
| `0x63d43bbb87f85af03b8f2f9e2fad7b54334fa2f` | **wokerjoesleeper** | Politik/Macro/Fed | **0.5x** | 20.04.2026 | PANews Biteye | Deep-Discovery 2026-04-20 |
| `0xbacd00c9080a82ded56f504ee8810af732b0ab35` | **ScottyNooo** | Politik/Trump/Iran | **0.3x** | 20.04.2026 | PANews Biteye | Deep-Discovery 2026-04-20 |
| `0xc6587b11a2209e46dfe3928b31c5514a8e33b784` | **Erasmus** | Iran/ME Geopolitics | **0.5x** | 19.04.2026 | polymonit April #4 | Aufnahme-Review b97d9ef |
| `0x0c0e270cf879583d6a0142fc817e05b768d0434e` | **TheSpiritofUkraine** | Politics/Geopolitics | **0.3x** | 19.04.2026 | polymonit April #3 | Aufnahme-Review b97d9ef |
| `0x492442eab586f242b53bda933fd5de859c8a3782` | **April#1 Sports** | Sports | **0.3x ⚠ WATCHING** | 17.04.2026 | predicts.guru | T-M09b 2026-04-19 (war 2.0x) |
| `0x0b7a6030507efe5db145fbb57a25ba0c5f9d86cf` | **HOOK** | Mixed | **1.0x ⚠ WATCHING** | 17.04.2026 | wallet_init | T-M09b 2026-04-19 (war 2.0x) |

---

## Wallet-Details

### majorexploiter — Tier A, 1.5x
- **Adresse:** `0x019782cab5d844f02bafb71f512758be78579f3c`
- **Performance:** 76% WR (intern), Millionen-Profit auf polymonit
- **Kategorie-Korrektur:** Ursprünglich als "Geopolitics" geführt — Bug-Fix (8d9b08a)
  zeigte 100% Sports (UCL). Multiplier von 3.0x auf 1.5x reduziert.
- **Review:** T-M09 2026-04-19, Commit nicht einzeln referenziert

### reachingthesky — Tier A, 1.0x
- **Adresse:** `0xefbc5fec8d7b0acdc8911bdd9a98d6964308f9a2`
- **Performance:** Unklar — ursprünglich als "wan123" fehlgelabelt in alter Doku
- **Hinweis:** Code hatte 2.0x, .env explizit 1.0x (P083-Diskrepanz, 69cf69a gefixt auf 1.0x beidseitig)
- **Nächste Review:** T-D109 2026-05-19

### kcnyekchno — Tier A, 1.0x
- **Adresse:** `0x7177a7f5c216809c577c50c77b12aae81f81ddef`
- **Performance:** 81% WR (extern, unbestätigt), 0 Trades bisher kopiert
- **Hinweis:** Konservative 1.0x wegen fehlender Live-Bestätigung, war 2.0x

### denizz — Tier A, 1.0x
- **Adresse:** `0xbaa2bcb5439e985ce4ccf815b4700027d1b92c73`
- **Performance:** polymonit April Politics #1 +$751k, UCL/Soccer-Spezialist
- **Hinweis:** Explizit auf 1.0x gesetzt (T-M09), vorher DEFAULT 0.5x

### HorizonSplendidView — Tier A, 0.5x (inaktiv)
- **Adresse:** `0x02227b8f5a9636e895607edd3185ed6ee5598ff7`
- **Performance:** 0 Activity-Records via data-api
- **Hinweis:** War 2.0x, auf 0.5x reduziert wegen 0 Activity. Falls permanent inaktiv:
  Kandidat für Entfernung bei T-D109.

### wan123 — Tier A cautious, 0.5x
- **Adresse:** `0xde7be6d489bce070a959e0cb813128ae659b5f4b`
- **Performance:** Negatives ROI-Flag trotz hoher Trade-Frequenz — Moonshot-Pattern
- **Hinweis:** War 2.5x, auf 0.5x reduziert (T-M09). P083-Diskrepanz (war 0.5x Code / 1.0x .env)
  heute gefixt via 69cf69a.

### wokerjoesleeper — Tier B, 0.5x _(neu 20.04.2026)_
- **Adresse:** `0x63d43bbb87f85af03b8f2f9e2fad7b54334fa2f`
- **Performance:** $900K all-time PnL, **+227% ROI auf Deposits**, 81% WR (NO-Bets)
- **Kategorie:** Politik, Makro-Economy, Fed Rates, Iran-Politik
- **Strategie:** 93% NO-Bets auf Low-Probability-Events (Longterm Macro)
- **Polymarket-Rang:** #73 Politik, #7 Economy, #9 Fed Rates
- **Trades/Tag:** ~79/d — verteilt auf lange Makro-Positionen, kein Bot-Muster
- **Joined:** Oktober 2024 | **Predictions:** 42,821
- **HF-0:** ✅ PASS | **HF-7:** ✅ PASS (+227%) | **HF-10:** ✅ PASS (Macro, kein Sport)
- **Quelle:** PANews Biteye Smart Money Artikel 2026-04-01
- **Analyse:** `analyses/deep_discovery_2026-04-20.md`
- **Upgrade-Bedingung:** Auf 1.0x nach 30-Tage-Live-Bestätigung (T-D109 2026-05-19)

### ScottyNooo — Tier B, 0.3x _(neu 20.04.2026, provisional)_
- **Adresse:** `0xbacd00c9080a82ded56f504ee8810af732b0ab35`
- **Performance:** $1.3M all-time PnL, 58.8% WR, Merlin Score 76/100
- **Kategorie:** Politik (Trump, Iran, Ukraine, Geopolitics)
- **Avg Trade:** ~$13,000 (Whale-Level) → bei 0.3x: ~$390 pro kopierten Trade
- **Joined:** Mai 2025 | **Predictions:** ~2,542 (~7/Tag — ideal für Copy-Bot)
- **30d Performance:** $216K auf $3.4M Volume (6.4% monatlich)
- **HF-0:** ✅ PASS | **HF-7:** ❓ PENDING (predicts.guru Deposit-ROI unbekannt) | **HF-10:** ✅ PASS
- **Upgrade-Bedingung:** 0.5x nach predicts.guru Deposit-ROI PASS + 30-Tage-Live
- **WARNUNG:** Deposit-ROI muss via predicts.guru verifiziert werden (bcda-Lektion)
- **Quelle:** PANews Biteye Smart Money Artikel 2026-04-01, Merlin, PolyScope
- **Analyse:** `analyses/deep_discovery_2026-04-20.md`

### Erasmus — Tier B, 0.5x _(neu 19.04.2026)_
- **Adresse:** `0xc6587b11a2209e46dfe3928b31c5514a8e33b784`
- **Performance:** +$476.597 April (~50% ROI), Portfolio $1.4M, cashPnL +$30.693 offen
- **Kategorie:** Iran/Middle East Geopolitics-Spezialist (82% der Trades)
- **Hard-Filter:** HF-8 WR nicht extern bestätigbar (0xinsider-Wallet-Mismatch)
- **Upgrade-Bedingung:** WR ≥55% nach 30-Tage-Review (T-D109 2026-05-19)
- **Aufnahme-Commit:** b97d9ef | Analyse: analyses/manual_candidates_review_2026-04-19.md

### TheSpiritofUkraine — Tier B, 0.3x _(neu 19.04.2026)_
- **Adresse:** `0x0c0e270cf879583d6a0142fc817e05b768d0434e`
- **Performance:** +$503.690 April (5.7% ROI auf $8.8M), 1.086 Markets, seit Aug 2021
- **Kategorie:** Politics/Geopolitics (57% direkt + ~70-80% inkl. Iran/ME-Overlap)
- **Hard-Filter:** HF-8 WR nicht bestätigt, cashPnL -$40.963 auf $5.45M (nur 0.75%)
- **Upgrade-Bedingung:** WR ≥55% nach 30-Tage-Review (T-D109 2026-05-19)
- **Aufnahme-Commit:** b97d9ef | Analyse: analyses/manual_candidates_review_2026-04-19.md

### April#1 Sports — Tier B, 0.3x ⚠ WATCHING
- **Adresse:** `0x492442eab586f242b53bda933fd5de859c8a3782`
- **Performance:** Extern WR 46.7% (Cointrenches), Lifetime PnL -$9.8M
- **Hard-Filter:** HF-8 FAIL (WR 46.7% < 55%), HF-10 FAIL (HFT-Bot-Muster)
- **Status:** Noch aktiv bei 0.3x — Risiko kalkuliert, kein Trade-Volumen erwartet
- **Nächste Review:** T-D109 2026-05-19 — Entfernung möglich bei gleichem Befund
- **Verifikations-Commit:** 5d7d138 | Analyse: analyses/hook_april_sports_verification_2026-04-19.md
- **KB-Referenz:** P077

### HOOK — Tier B, 1.0x ⚠ WATCHING
- **Adresse:** `0x0b7a6030507efe5db145fbb57a25ba0c5f9d86cf`
- **Performance:** Nur 46 Trades (< HF-1 Minimum von 100), WR diskrepant (38.5% vs. 67%)
- **Status:** 1.0x nach Reduktion von 2.0x — WR-Diskrepanz unklar
- **Nächste Review:** T-D109 2026-05-19 — falls WR ≤45%: Entfernung
- **Verifikations-Commit:** 5d7d138 | Analyse: analyses/hook_april_sports_verification_2026-04-19.md
- **KB-Referenz:** P077

---

## Entfernte Wallets (heute, Audit v1.0)

| Adresse | Alias | Grund | Entfernt |
|---------|-------|-------|---------|
| `0x7a6192ea6815d3177e978dd3f8c38be5f575af24` | **Gambler1968** | 0 kopierte Trades, dauerhaft inaktiv | Commit 7c29ac9, 2026-04-19 |
| `0x2005d16a84ceefa912d4e380cd32e7ff827875ea` | **RN1** | HF-8 FAIL: 26.8% WR + 87% Copy-Volume = Manip-Verdacht | Commit 7c29ac9, 2026-04-19 |
| `0xee613b3fc183ee44f9da9c05f53e2da107e3debf` | **sovereign2013** | HF-8 FAIL: 45% WR (< 55% Minimum) | Commit 7c29ac9, 2026-04-19 |

Vollständige Audit-Dokumentation: `analyses/audit_v1_results_2026-04-19.md`

---

## Dormante Code-Einträge (in WALLET_MULTIPLIERS, NICHT in TARGET_WALLETS)

Diese Wallets sind im Code vorkonfiguriert aber nicht aktiv überwacht:

| Adresse | Alias | Multiplier | Status |
|---------|-------|------------|--------|
| `0xbddf61af533ff524d27154e589d2d7a81510c684` | **Countryside** | 3.0x | **HF-8 FAIL** — wahre WR 48.5% (cointrenches), Haltezeit < 3h (NBA same-day). Shadow bis 2026-05-20. |
| `0xdb27bf2ac5d428a9c63dbc914611036855a6c56e` | **DrPufferfish** | 3.0x | **HF-8 FAIL** — wahre WR 50.9% (PANews), Basket-Strategie nicht kopierbar. Shadow bis 2026-07-20. |
| `0xd84c2b6d65dc596f49c7b6aadd6d74ca91e407b9` | BoneReader | 1.5x | Historisch — nicht in TARGET_WALLETS |
| `0xde17f7144fbd0eddb2679132c10ff5e74b120988` | Crypto Spezialist | 2.0x | REJECTED 19.04 (Portfolio $0, alle Positionen verloren) |

**Verifikation 2026-04-20 (HF-8 Scout):**
- Beide Wallets haben **artifiziell hohe predicts.guru WR** durch Early-Loss-Selling + Zombie-Orders
- predicts.guru WR > 80% = Warn-Signal, NICHT Beweis — immer Kreuzcheck mit cointrenches/0xinsider
- Analyse: `analyses/drpufferfish_countryside_verification.md`
- Keine .env-Änderungen — beide bleiben außerhalb TARGET_WALLETS

→ Bei nächstem Code-Cleanup: Einträge kommentieren oder entfernen.

---

## Nächste Review

**T-D109 — 30-Day Wallet Review: 2026-05-19**

Schwerpunkte:
- **wokerjoesleeper:** 30-Tage-Live-Bestätigung → Upgrade auf 1.0x wenn aktiv
- **ScottyNooo:** predicts.guru Deposit-ROI verifizieren → wenn PASS: Upgrade auf 0.5x
- Erasmus + TheSpiritofUkraine: WR bestätigen (30 Tage Live-Daten)
- HOOK: WR-Diskrepanz auflösen → behalten oder entfernen
- April#1 Sports: 30-Tage-Performance → behalten (0.3x) oder entfernen
- HorizonSplendidView: Activity-Check → inaktiv seit 19.04?
- **Countryside Shadow-Review:** 30-Tage-WR via cointrenches/0xinsider (≥56% = Integration)
- **statwC00KS:** predicts.guru Full-Check + ROI auf Deposits (NBA #18, 96.2% WR, 3.204 Trades)

**2026-05-05 — Watching-Queue Check:**
- cowcat (`0x38e59b36aae31b164200d0cad7c3fe5e0ee795e7`): predicts.guru ROI → wenn PASS: APPROVE 0.3x
- Frank0951 (`0x40471b34671887546013ceb58740625c2efe7293`): predicts.guru ROI → wenn PASS: APPROVE 0.3x
- middleoftheocean (`0x6c743aafd813475986dcd930f380a1f50901bd4e`): predicts.guru + HF-10 Check
- ewelmealt (`0x07921379f7b31ef93da634b688b2fe36897db778`): 90-Tage-Shadow (Feb 2026 start) → ersten Check Mai 2026

**Shadow-Watch Dormante Wallets:**
- Countryside: Review 2026-05-20 — WR-Diskrepanz klären, "15% human" Pattern
- DrPufferfish: Review 2026-07-20 — Basket-Strategie, kopierbar wenn Bot Basket-Bündelung kann

**Entscheidungs-Kriterien (HF-8):** WR < 45% → sofort entfernen. WR 45-55% → weiter beobachten. WR ≥55% → Upgrade möglich.

---

## Dual-Source-Protokoll (KB P083)

Jede Multiplier-Änderung erfordert:
```
1. strategies/copy_trading.py → WALLET_MULTIPLIERS Dict (Versionierung)
2. .env → WALLET_WEIGHTS JSON (Runtime-Effekt, .env gewinnt)
3. Bot-Restart
4. Verifikation: Log "Wallet X geladen mit Multiplier Y"
```

Aktueller Sync-Status: ✅ VOLLSTÄNDIG (Stand: 69cf69a, 2026-04-19)

## Quellen für neue Kandidaten

- https://polymonit.com/leaderboard
- https://predicts.guru
- https://oddsshift.com/smart-money
- https://www.frenflow.com/traders

Veto-Check immer via data-api (`/trades?user=0x...`) — polymonit-Daten nie direkt vertrauen (KB P073).
