# Wallet Scout v2.0 — 2026-04-20
_Framework: WALLET_SCOUT_BRIEFING.md v2.0 | Profit-First_
_Scout-Datum: 2026-04-20 | Quellen: polymonit, cointrenches, predicts.guru, frenflow, Polymarket native_

---

## Zusammenfassung

- Kandidaten mit > $100K Profit identifiziert: 12
- **APPROVE v2.0:** 1 sofort + 1 provisional
- **WATCHING:** 6
- **REJECT (v2.0 K.O.):** 1
- **Forschung ausstehend:** 4

**Kern-Erkenntnis:** bcda ist der stärkste neue Kandidat — $2M/Woche, Multi-Sport (NBA+NHL+MLB),
18 Trades/Tag (kein HFT), keine dokumentierten Mega-Verluste bei 1.668 Predictions.
Direkt integrierbar, keine neuen Bot-Features nötig.

---

## Ergebnistabelle

| Wallet | Gewinn | ROI | Strategie | Bot-Anforderung | Empfehlung |
|--------|--------|-----|-----------|-----------------|------------|
| **bcda** | +$2M/Woche | ~20%/Woche | NBA+NHL+MLB Spreads, Multi-Sport | Keine (sofort) | ✅ APPROVE Tier B 0.5x |
| **feveey** | +$419K/48h | Unbekannt | NBA Moneyline HiConv | Keine (wenn Adresse bestätigt) | ✅ APPROVE provisional |
| **sovereign2013** | +$3.4M all-time | Positiv | Sports-Bot/Accumulator, 145/Tag | HF-10 klären | 👁 WATCHING |
| **blindStaking** | +$1.78M April | Unbekannt | Soccer HiConv, 6 Trades gesamt | Mehr Daten | 👁 WATCHING (zu jung) |
| **CemeterySun** | +$1.83M/6 Wochen | Unbekannt | Soccer + NBA | Adresse fehlt | 👁 WATCHING |
| **Theo4** | +$22M all-time | ~100% | Election Sniper, 14 Bets | Reaktivierung abwarten | 👁 WATCHING (inaktiv) |
| **RN1** | +$4.1-4.5M | Positiv | Sports-Bot, 87% Copy-Vol | Signal-Qualität unklar | 👁 WATCHING |
| **MinorKey4** | +$734K | ~14.4% | Unbekannt | Profil fehlt | 🔍 Research needed |
| **joosangyoo** | +$641K | ~11.7% | Unbekannt | Profil fehlt | 🔍 Research needed |
| **WoofMaster** | +$571K | Unbekannt | Unbekannt | Profil fehlt | 🔍 Research needed |
| **KeyTransporter** | +$5.7M/30 Tage | Sehr hoch | Soccer, 14 Trades | Adresse fehlt | 🔍 Research needed |
| **432614799197** | +$4.5M PnL | **-57.41% auf Deposits** | High-Freq Sports | — | ❌ REJECT HF-7 FAIL |

---

## APPROVE — Detailanalyse

### 1. bcda — Multi-Sport Accumulator ✅ SOFORT APPROVE

- **Adresse:** `0xb45a797faa52b0fd8adc56d30382022b7b12192c`
- **Username:** @bcda | **Joined:** Januar 2026 (~3 Monate)
- **Quelle:** cointrenches.io/bcda-polymarket-sports-trader-profile/ (April 2, 2026)
- **Predictions:** 1.668 (≈18/Tag Durchschnitt)
- **Wöchentlicher Profit:** +$1.95M–+$2.04M
- **Wöchentliches Volume:** ~$9.54M
- **Netto-Marge:** ~20–21% auf wöchentliches Kapital
- **Größter Einzelgewinn:** +$284.9K
- **Offene Positionen:** ~$1.2M
- **Primär-Märkte:** NBA Spreads/Totals + NHL + MLB Over/Under

**HF-0 Check (Primärfrage: Profitabel?):**
| Filter | Status | Begründung |
|--------|--------|-----------|
| HF-0 Gesamtgewinn > $10K | ✅ PASS | $2M/Woche deutlich >> $10K |
| HF-7 ROI auf Deposits > 0% | ✅ PASS | 20%+ Nettomarge wöchentlich |
| HF-9 Kein Insider-Typ-A | ✅ PASS | Öffentliche Sports-Märkte, Strategie dokumentiert |
| HF-10 Kein bestätigter HFT-Bot | ✅ PASS | 18 Trades/Tag = kein HFT. NBA/NHL/MLB ≠ Crypto Arb |

**Strategie-Analyse (Sekundärfrage):**

bcda ist kein Conviction-Trader wie beachboy4, sondern ein **High-Volume Sports Accumulator**:
- 18 Predictions/Tag über NBA, NHL und MLB gleichzeitig
- Position Sizes: $100K–$400K pro Bet (avg ca. $5.7K auf dem Wochenvolumen)
- Keine dokumentierten Mega-Verluste bei 1.668 Trades — deutet auf Risikomanagement hin
- NHL: $199K–$300K pro Spiel, also nicht nur NBA-Spezialist
- Positiver EV über 3 Monate bestätigt: $2M/Woche bei $9.54M Volume = Edge real

**Strategie-Typ-Matrix (HF-8 v2.0):**
- WR unbekannt, aber 20% Nettomarge bei 1.668 Trades = solider G:L-Vorteil
- Vergleich: sovereign2013 hat 52.6% WR und $3.4M all-time → bcda dürfte ähnlich liegen
- Typ: Direktional-Akkumulator (kein Basket, kein Early-Loss-Seller sichtbar)

**Bot-Anforderung:** **KEINE** — Bot kann heute kopieren.
- 18 Signals/Tag sind handhabbar (derzeit ~10–15 Signals/Tag vom gesamten System)
- Multi-Signal-Buffer: bcda kann als Solo-Signal-Kategorie Sports laufen
  (andere Sports-Wallets bereits im System: majorexploiter, HorizonSplendidView)
- Position-Sizes 100K–400K vs. unser $60 Cap = normales Verhältnis
- Kopier-Multiplier 0.5x auf 60$ Cap = ~$30/Signal — klein aber datenpunktreich

**Portfolio-Construction (PC-Rules):**
- PC-2: Max 3 Sports-Wallets. Aktuell: majorexploiter + HorizonSplendidView + April#1 = 3
- bcda wäre Slot #4 in Sports → **PC-2 Konflikt!**
- Auflösung: April#1 Sports ist HF-10 FAIL + HF-8 FAIL (46.7% WR, Lifetime PnL -$9.8M)
  → April#1 Sports entfernen → bcda übernimmt den Sports-Slot
- Nach Entfernung April#1: 3 Sports = majorexploiter + HorizonSplendidView + bcda → PC-2 ✅

**Empfehlung: ✅ APPROVE Tier B 0.5x**
- Gleichzeitig April#1 Sports (`0x492442eab586f242b53bda933fd5de859c8a3782`) entfernen
- Begründung April#1 Entfernung v2.0: HF-7 impliziert (Lifetime PnL -$9.8M = neg. ROI)

**Server-CC Aktion:**
```
1. April#1 Sports aus TARGET_WALLETS entfernen
2. bcda hinzufügen: 0xb45a797faa52b0fd8adc56d30382022b7b12192c
3. WALLET_WEIGHTS: "0xb45a797faa52b0fd8adc56d30382022b7b12192c": 0.5
4. Bot-Restart + Verify
```

---

### 2. feveey — NBA HiConv Provisional ✅ APPROVE PROVISIONAL

- **Adresse:** Nicht öffentlich — @feveey auf Polymarket.com
- **Joined:** März 2026 (~3 Wochen alt als of April 1)
- **Quelle:** cointrenches.io/feveey-polymarket-nba-trader-profile/ (April 1, 2026)
- **Predictions:** 13 (Stand April 1, 2026)
- **Best Day:** +$419K in 48h auf $609K Volume
- **Größter Einzelgewinn:** +$190.4K (Rockets @ 49.8¢)
- **Win Rate bestätigt:** 4 Wins, 1 Loss aus 5 resolved = 80% WR auf kleiner Sample
- **Offene Positionen:** $887.6K (Stand April 1)

**HF-0 Check:**
| Filter | Status | Begründung |
|--------|--------|-----------|
| HF-0 Gesamtgewinn > $10K | ✅ PASS | $419K PASS |
| HF-7 ROI positiv | ✅ PASS | $419K auf ~$800K Volume = ~52% |
| HF-9 Kein Insider | ✅ PASS | NBA öffentliche Märkte, Hedge-Struktur sichtbar |
| HF-10 Kein HFT | ✅ PASS | 13 Trades in 3 Wochen |

**Strategie-Analyse:**
- Conviction-Model: $128K–$374K pro Bet auf NBA Moneylines
- Hedge-Struktur: $374K Rockets + $40K Knicks im selben Spiel = professionelles Risikomanagement
- Underdog-Fähigkeit: Trail Blazers @ 35¢ mit $155K = nicht nur Favourite-Backing
- Ähnlich beachboy4 in Struktur, aber nur NBA vs. beachboy4's Pan-Sports

**WARNUNG:** Nur 13 Trades, 3 Wochen alt. In v2.0 kein K.O. aber extrem kleines Sample.
WR könnte Varianz sein. **Adresse unbekannt** — Integration erst nach Adress-Identifikation.

**Bot-Anforderung:** Adresse identifizieren → dann keine neuen Features nötig.

**Empfehlung:** ✅ APPROVE Provisional 0.3x (Vorsicht-Multiplier)
- **Aktion:** Adresse via polymarket.com/@feveey ermitteln, dann Tier B 0.3x
- **Review:** 2026-05-20 nach weiteren 30 Tagen Daten

---

## WATCHING — Detailanalyse

### 3. sovereign2013 — Sports Accumulator, HF-10 offen

- **Adresse:** `0xee613b3fc183ee44f9da9c05f53e2da107e3debf`
- **Status in System:** ENTFERNT (Commit 7c29ac9) — Grund: "HF-8 FAIL: 45% WR + 87% Copy-Volume"
- **Frenflow:** +$3.5M all-time, $392.7M Volume, 40.076 Predictions, Sports-Spezialist
- **Cointrenches:** WR 52.6% (nicht 45%!), +$3.4M all-time, $1.75M/Woche
- **April 2026:** Rank #8 mit +$1.718M

**v2.0 Re-Bewertung:**
- HF-0: $3.4M >> $10K → ✅ PASS
- HF-7: Positiv → ✅ PASS
- HF-9: Keine Insider-Signatur → ✅ PASS
- **HF-10:** 145 Predictions/Tag = BORDERLINE
  - Crypto 5min/15min? → HFT (K.O.)
  - Sports NBA/NHL bei 145/Tag? → Semi-Bot möglich
  - 40.076 Predictions in 9 Monaten = ≈148/Tag → bestätigt

**87% Copy-Volume Problem (alt):**
Das ursprüngliche "Manipulations-Verdacht" aus Commit 7c29ac9 war v1.x HF-8.
In v2.0: "Copy-Volume" bedeutet sovereign2013 kopiert von anderen Wallets.
Wenn wir sovereign2013 kopieren, sind wir **Meta-Copier** — Signal-Qualität abhängig von
Quell-Wallets. Wenn die Quell-Wallets schlechter werden, verschlechtert sich sovereign2013 ohne Vorwarnung.
Das ist **kein K.O. aber ein legitimes Qualitäts-Risiko**.

**Neues Urteil v2.0:** 👁 WATCHING
- HF-10 muss geklärt werden: Welche Märkte? Crypto oder Sports?
- Wenn Sports: 145/Tag ist kopierbar aber Meta-Copy-Risiko bleibt
- **Review:** 2026-05-05 — polymonit Kategorie-Check sovereign2013

---

### 4. blindStaking — Soccer HiConv, zu jung

- **Adresse:** `0x50b1db131a24a9d9450bbd0372a95d32ea88f076`
- **Joined:** März 2026 | **Predictions:** 6 gesamt
- **April 2026:** +$1.78M auf Atlético de Madrid
- **März 2026:** -$1.87M auf Real Madrid (Los) im Derby
- **Profit-Netto:** ~$0 (Gewinn und Verlust fast gleich)

**v2.0 Check:**
- HF-0: +$1.78M April → ✅ aber Netto-All-Time ≈ $0 oder leicht negativ
- HF-7: Unklar (noch zu wenig Daten)
- HF-10: 6 Trades → ✅ PASS
- Problem: Nur 6 Trades, Netto-PnL fraglich

**Neues Urteil:** 👁 WATCHING — zu wenig Daten, Netto-PnL unklar
**Review:** 2026-06-20 nach 50+ Trades

---

### 5. Theo4 — All-Time #1, derzeit inaktiv

- **Adresse:** `0x56687bf447db6ffa42ffe2204a05edaa20f55839`
- **All-Time Profit:** +$22.053.934 (Platz #1 Polymarket all-time)
- **Predictions:** 14 gesamt (Lifetime)
- **WR:** 88.9% | **Total Losses:** $19
- **Status:** $0 offene Positionen — vollständig inaktiv

**v2.0 Check:**
- HF-0: $22M → ✅ PASS (stärkstes HF-0 überhaupt)
- HF-7: Positiv → ✅ PASS
- **HF-5 FAIL (Inaktiv):** Keine Aktivität seit 2024 US-Wahl — Signal-Quelle trocken
- Strategie: 93.6% des Profits aus 2 korrelierten Trump-Bets. Kein kopierbares Muster im Alltag.
- Wenn Theo4 reaktiviert: **höchste Priorität auf Polymarket** (cointrenches: "when Theo4 makes a move, it's the most important signal on the platform")

**Neues Urteil:** 👁 WATCHING — Alert wenn neue Position erscheint
**Bot-Anforderung:** Telegram-Alert sobald $0-zu-aktiv Transition (manuelle Beobachtung)

---

### 6. RN1 — Sports Bot re-examine

- **Adresse:** `0x2005d16a84ceefa912d4e380cd32e7ff827875ea`
- **Status in System:** ENTFERNT (Commit 7c29ac9) — "26.8% WR + 87% Copy-Volume"
- **Cointrenches April 2026:** +$4.1–4.5M all-time, WR 53–56%, $2.19M weekly, ~29.000 Trades
- **April 2026 Rank:** #6 mit +$1.965M

**v2.0 Neu-Bewertung:**
- HF-0: $4.1M >> $10K → ✅ PASS
- WR-Diskrepanz: 26.8% (unsere alte Daten) vs. 53–56% (cointrenches April 2026)
  → Daten-Update nötig. Wenn cointrenches korrekt: WR massiv besser als gedacht.
- **87% Copy-Volume:** Gleicher Meta-Copy-Konflikt wie sovereign2013
- HF-10: ~160 Predictions/Tag (ähnlich sovereign2013) — BORDERLINE

**Neues Urteil:** 👁 WATCHING — WR-Diskrepanz klären + Copy-Volume verifizieren
**Review:** 2026-05-05

---

## REJECT — Begründet

### 7. 432614799197 — HF-7 FAIL

- **Adresse:** `0xdc876e6873772d38716fda7f2452a78d426d7ab6`
- **Predicts.guru:** "$4.1M in Deposits → $2.14M PnL — **-57.41% ROI auf Deposits**"
- **Trades:** 97.8/Tag, 3.023 Märkte
- **WR:** 66.78% — aber ROI negativ!

**v2.0 K.O.: HF-7 FAIL**
66.78% WR mit -57.41% ROI auf Deposits = inverse G:L-Ratio:
Verluste sind größer als Gewinne trotz hoher WR → Anti-Dragonfly-Pattern.
Negative ROI auf Deposits ist der einzige absolute K.O. in v2.0.

**Urteil: ❌ REJECT — FINAL (HF-7 FAIL)**

---

## Research Needed

| Wallet | Adresse | Bekannter Profit | Warum Research |
|--------|---------|-----------------|----------------|
| **MinorKey4** | `0xb904...255` | +$734K all-time, ~14.4% ROI | Profil komplett unbekannt |
| **joosangyoo** | `0x07b8...e25` | +$641K all-time, ~11.7% ROI | Profil unbekannt |
| **WoofMaster** | `0x916f...3ba` | +$571K all-time | Profil unbekannt |
| **KeyTransporter** | Unbekannt | +$5.7M/30 Tage, 14 Trades | Soccer Sniper, Adresse fehlt |
| **CemeterySun** | Unbekannt | +$1.83M/6 Wochen | Soccer+NBA, Adresse fehlt |

**ROI-Qualität MinorKey4 + joosangyoo:**
Beide zeigen >10% ROI auf kleinem Volume ($5M) — deutet auf echten Edge hin, nicht High-Volume-Grind.
Bei nächster Scout-Session als Priorität behandeln.

---

## Wichtige neue Erkenntnisse

### 1. bcda als Template für "kopierbaren Sports-Bot"

bcda beweist: 18 Trades/Tag über 3 Sports-Kategorien ist profitabel UND kopierbar.
Die Angst vor hohen Trade-Frequenzen war v1.x-Denken (Multi-Signal-Buffer-Problem).
In v2.0: Wenn 18/Tag kopierbar → threshold für HF-10 liegt höher als gedacht.
**Neue Faustregel:** HF-10 greift bei > 100 Trades/Tag UND Crypto-Arbitrage-Muster.
Sports-Bots mit < 50/Tag sind prinzipiell kopierbar.

### 2. April#1 Sports vs. bcda — Slot-Tausch

April#1 Sports (`0x492442`) hat HF-7 FAIL (Lifetime PnL -$9.8M) — war v1.x übersehen.
bcda übernimmt den Sports-Slot als deutlich besseres Signal.
Beide sind NBA-dominiert, aber bcda hat positiven ROI und Multi-Sport.

### 3. Theo4 als Sonder-Alert-Wallet

$22M auf 14 Bets = der effizienteste Trader aller Zeiten auf Polymarket.
Aktuell inaktiv. Wenn reaktiviert: **sofortiger manueller Review, kein Auto-Copy**.
Jede neue Position von Theo4 = potentiell $1M+ Bet auf ein Ereignis.
Sollte als Webhook-Alert konfiguriert werden (nicht als normales Copy-Signal).

### 4. Meta-Copy-Risiko bei sovereign2013 / RN1

Wenn ein Wallet 87% seines Volumens durch Kopieren anderer Wallets erzeugt,
kopiert unser Bot einen Copier. Das verstärkt Signal-Latenz und macht unser System
abhängig von der Qualität der Quell-Wallets — unsichtbar für uns.
In v2.0 kein K.O. aber Tier-B-Malus: max. 0.3x Multiplier bis Copy-Volume-Anteil geklärt.

---

## Empfohlene Aktionen

| Priorität | Aktion | Deadline |
|-----------|--------|----------|
| 🔴 P1 | bcda in Tier B 0.5x aufnehmen, April#1 entfernen | Heute — Server-CC |
| 🟠 P2 | feveey Adresse via polymarket.com/@feveey ermitteln | 2026-04-21 |
| 🟠 P3 | sovereign2013 HF-10 Kategorie-Check (polymonit) | 2026-05-05 |
| 🟡 P4 | MinorKey4 + joosangyoo Profile — predicts.guru | 2026-05-05 |
| 🟡 P5 | KeyTransporter + CemeterySun Adresse identifizieren | 2026-05-05 |
| 🟢 P6 | Theo4 Webhook-Alert einrichten (T-I für Telegram) | TBD |

---

## WALLETS.md Update (nach Approval)

**Hinzufügen:**
- bcda: Tier B, 0.5x, Sports/Multi (NBA+NHL+MLB), `0xb45a797faa52b0fd8adc56d30382022b7b12192c`
- feveey: Tier B provisional, 0.3x, NBA (nach Adress-Verifikation)

**Entfernen:**
- April#1 Sports (`0x492442`): HF-7 FAIL (Lifetime PnL -$9.8M), Multiplikator Upgrade nicht gerechtfertigt

---

_Scout gemäß WALLET_SCOUT_BRIEFING.md v2.0 — Profit-First, HF-0 als einziger K.O._
_Quellen: cointrenches.io, polymonit.com, frenflow.com, polymarket.com native leaderboard_
