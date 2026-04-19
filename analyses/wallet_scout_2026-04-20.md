# Wallet Scout 2026-04-20

_Scout-Datum: 2026-04-20 | Methode: Exa + polymonit + merlin.trade + cointrenches | Briefing: v1.2_
_Quellen: polymonit April 2026 Leaderboard, All-Time Rankings, Whale-Tracker, merlin.trade, cointrenches.io, 0xinsider.com_

---

## Zusammenfassung

- Kandidaten geprüft: 7 neue Wallets (nicht in unserer aktuellen Liste)
- Hard-Filter bestanden (7/9 für Tier B): 0
- Tier A Empfehlungen: 0
- Tier B Empfehlungen: 0
- Watching (Score < 50 oder HF-Fails): 3
- Sofort abgelehnt: 4

**Fazit:** Kein sofortiger Aufnahme-Kandidat. Hauptgrund: Top-April-Wallets sind entweder
bereits in unserer Liste (majorexploiter, HorizonSplendidView, reachingthesky, denizz)
oder scheitern an HF-6 (Profit-Konzentration), HF-8 (WR < 55%) oder HF-1 (< 50 Trades).
April 2026 war ein Sports-dominierter Monat — passende Wallets haben wir bereits.

---

## Ergebnisse

| Wallet (Alias) | Win Rate | ROI | Trades | Kategorie | HF-Pass | Score | Tier | Empfehlung |
|----------------|----------|-----|--------|-----------|---------|-------|------|------------|
| beachboy4 | ~51% | 1.7% auf Vol | 149 | Sports | 5/9 | 53 | - | WATCHING — HF-3/6/8 FAIL |
| 0x2a2c...9Bc1 | UNKNOWN | UNKNOWN | UNKNOWN | Sports/Mixed | UNKNOWN | - | - | WATCHING — Daten fehlen |
| 432614799197 | UNKNOWN | UNKNOWN | UNKNOWN | Cross-Cat | UNKNOWN | - | - | WATCHING — Daten fehlen |
| Fernandoinfante | UNKNOWN | 3501% (1 Trade) | 35 | Geopolitics | 6/9 | - | - | REJECT — HF-1 FAIL, One-Hit-Wonder |
| SeriouslySirius | 50.3% | +$3.6M | 6.339 | Mixed | 8/9 | - | - | REJECT — HF-8 FAIL (WR 50.3%) |
| k9Q2mX4L8A7ZP3R | UNKNOWN | $535K/$410 Vol | UNKNOWN | Crypto | UNKNOWN | - | - | REJECT — Datenfehler verdächtig |
| immotawizard | UNKNOWN | +$1.84M (1 Trade) | UNKNOWN | Sports | UNKNOWN | - | - | REJECT — unzureichende Daten |

---

## Detailanalyse Top-Kandidaten

### 1. beachboy4 — Sports Whale
- **Adresse:** `0xc2e7800b5af46e6093872b177b7a5e7f0563be51`
- **Quellen:** polymonit April #4, merlin.trade, cointrenches.io, polycopy.app
- **Joined:** November 2025 (~5 Monate)
- **Total Trades:** 149 (sehr niedrig für die Performance-Zahlen)
- **All-time Profit:** +$4.14M
- **All-time Volume:** $209.8M (Merlin) → ROI auf Volume: 1.7%
- **April Profit:** +$3,463,973 (Sports Rank #4)
- **Win Rate:** ~51% laut Cointrenches-Analyse (Strategie: Sizing, nicht Trefferquote)
- **Kategorie:** Sports (Football, Basketball) — 95%+ Fokus

**Strategie-Profil:**
Beachboy4 macht Geld nicht durch hohe Win-Rate sondern durch extremes Sizing auf Low-Preis-Favoriten (Entry oft 68–72¢). Ein einziger West Ham-Bet brachte +$3.48M Profit bei $3.32M Einsatz. Die Strategie setzt auf minimale aber echte Pricing-Ineffizienzen gegenüber Buchmacher-Linien ("30–40 bookmaker line comparison").

**Hard-Filter-Bewertung:**
| HF | Kriterium | Status | Begründung |
|----|-----------|--------|-----------|
| HF-1 | ≥ 50 Trades | ✅ PASS | 149 Trades |
| HF-2 | ≥ 60 Tage alt | ✅ PASS | Nov 2025 (~5 Monate) |
| HF-3 | MDD < 30% | ❌ FAIL | PSG Villarreal: -$7.56M single loss. MDD deutlich >30% |
| HF-4 | Drawdown überlebt | ❓ UNKNOWN | Hatte -$2M 35-Tage-Phase, aber zurück? Daten unklar |
| HF-5 | Aktiv letzte 14 Tage | ✅ PASS | April 2026 aktiv |
| HF-6 | Kein >20% Profit-Konzentration | ❌ FAIL | West Ham: +$3.48M von $4.14M Gesamt = 84% eines Trades |
| HF-7 | ROI auf Deposits > 0% | ❓ UNKNOWN | Deposit-Betrag unbekannt (Volume ≠ Deposits) |
| HF-8 | WR 55–75% | ❌ FAIL | ~51% laut Cointrenches (Strategie: Sizing statt WR) |
| HF-9 | Kein Last-Minute-Pattern | ❓ UNKNOWN | Keine Daten zur Trade-Timing-Distribution |
| HF-10 | Kein HFT-Bot | ✅ PASS | 149 Trades in 5 Monaten = kein HFT |

**HF-Ergebnis:** 4 PASS, 3 FAIL, 2 UNKNOWN → Tier B braucht 7/9 → **REJECT für Tier B**

**KongScore (Small-Pool, 5 Kategorien):**
- SC-1 Sample-Size: 18P (149 Trades = 100-199 Range)
- SC-2 Kategorie-Fokus: 25P (Sports 95%+ = >70%)
- SC-3 Entry-Preis: 0P (68–72¢ Entry = weit über 60¢)
- SC-4 ROI:MDD-Ratio: 0P (MDD drastisch, Ratio < 1.0)
- SC-7 Exit-Evidence: 10P (aktiv verkauft vor Resolution)
- **Gesamt: 53/100**

**Empfehlung: WATCHING — nicht kopieren**
Faszinierende Strategie, aber falsch für unser System:
- HF-8 FAIL: 51% WR bedeutet bei unserem Multi-Signal-Buffer würden viele Signale nie bestätigt
- HF-6 FAIL: Ein einziger Bet als 84% des gesamten Profits ist nicht replizierbar
- Entry über 60¢ ist außerhalb unserer bevorzugten Alpha-Zone (20–40¢)
- Drawdown-Risiko extrem: -$7.56M auf einen Bet zeigt Sizing das unsere Positionen vernichten würde

**Wiedereinstiegs-Bedingungen:** Kein Wiedereinstieg vorgesehen. Architektur-Konflikt ist fundamental.

---

### 2. 0x2a2c53bd278c04da9962fcf96490e17f3dfb9bc1 — Volumen-Whale
- **Adresse:** `0x2a2c53bd278c04da9962fcf96490e17f3dfb9bc1` (kein Alias bekannt)
- **Quellen:** polymonit All-Time #3, April 2026 Rank #9
- **April Profit:** +$1,655,942 auf $55,600,358 April-Volumen (3% Marge)
- **All-time Profit:** +$1,574,127 auf $26,348,921 Lifetime-Volumen
- **Win Rate:** UNKNOWN
- **Kategorie:** Sports, broad event markets

**Hard-Filter-Bewertung:**
| HF | Status | Begründung |
|----|--------|-----------|
| HF-1 | ❓ UNKNOWN | Trade-Count nicht verfügbar |
| HF-2 | ❓ UNKNOWN | Account-Alter nicht verfügbar |
| HF-3 | ❓ UNKNOWN | MDD nicht verfügbar |
| HF-5 | ✅ PASS | April 2026 aktiv |
| HF-10 | ❌ WARNUNG | $55.6M Volume in einem Monat = mögliches Market-Maker-Pattern |

**KongScore:** Nicht berechenbar — zu wenig Daten.

**Empfehlung: WATCHING — mehr Research nötig**
Das Volume-zu-Profit-Verhältnis (3%) deutet auf Market-Making oder sehr dünne Margen hin.
Vor Aufnahme: predicts.guru Checker aufrufen, Win-Rate und Trade-Count verifizieren.
HF-10 (HFT-Bot) muss ausgeschlossen werden.

---

### 3. 432614799197 — Cross-Category Wallet
- **Adresse:** `0xdc876e6873772d38716fda7f2452a78d426d7ab6`
- **Quellen:** polymonit April Rank #10, Merlin "Similar Traders"
- **April Profit:** +$1,495,977
- **All-time Profit:** +$4.5M laut Merlin auf $185.5M Volume (2.4% Marge)
- **Kategorie:** Cross-category (Sports, Macro, Politics)

**Empfehlung: WATCHING — mehr Research nötig**
Ähnliches Muster wie 0x2a2c: Sehr hohes Volume, geringe prozentuale Marge.
Cross-category (kein Fokus) = HF-2 Kategorie-Spezialisierung fehlt → SC-2 = 0P.
Win-Rate und Trade-Count unbekannt.

---

## Abgelehnte Kandidaten

| Wallet | Ablehnungsgrund |
|--------|----------------|
| **Fernandoinfante** (`0xd7375270...`) | HF-1 FAIL: 35 Trades < 50 Minimum. HF-6 FAIL: Iran-Bet = 97% des gesamten Profits (One-Hit-Wonder). Joined Feb 2026 = zu jung. |
| **SeriouslySirius** | HF-8 FAIL: 50.3% Win Rate (unter 55% Minimum). Trotz $3.6M Profit — unser System kann diese Sizing-Strategie nicht replizieren. |
| **k9Q2mX4L8A7ZP3R** (`0xd0d605...`) | Datenfehler: $535K Profit auf $410 Volume ist technisch unmöglich. Wahrscheinlich AMM-Arbitrage oder Datenbankfehler. |
| **immotawizard** | One-Trade-Wonder: +$1.84M auf Real Madrid bet. Kein Wallet-Profil identifizierbar. Unzureichende Daten. |

---

## Erkenntnisse aus diesem Scout

### 1. April 2026 war ein Sports-Monat mit schlechtem Timing für uns
Die Top-April-Wallets die wir noch NICHT haben (beachboy4, 0x2a2c, 432614799197) sind alle
Sports-dominiert — aber mit Sizing-Strategien die mit unserem Multi-Signal-Buffer inkompatibel sind.
Wir haben majorexploiter (Sports/UCL) und HOOK (Mixed) bereits. Mehr Sports-Wallets würden
ohne starke Kategorie-Peers im Buffer verpuffen (KB P085).

### 2. "Polymonit-Top-10" ist kein Copy-Trading-Signal mehr
Die April-Top-10 sind mehrheitlich Wallets mit:
- Sehr hohem Volume ($10M–$55M) und sehr dünner %-Marge (1.7–3%)
- Win-Rates unter 55% (kompensiert durch Sizing)
- Profit-Konzentration in 1-3 Mega-Trades

Das ist Wholesale-Arbitrage-Trading, kein Retail-Copy-Trading-Signal.
Marks' Warnung: "Was jeder weiß, ist nicht mehr wertvoll."

### 3. Geopolitics-Cluster bleibt untererforscht
Die Polytics-Leaderboard-Top-5 (denizz, wan123, TheSpiritofUkraine, Erasmus, Fernandoinfante)
sind alle bereits in unserem System (oder abgelehnt). Das ist ein Zeichen dass unser
Wallet-Scout-Fokus auf Geopolitics gut kalibriert ist.

### 4. Data-Quality-Problem: Viele interessante Wallets haben keine öffentlichen Vollprofile
immotawizard, blindStaking, CemeterySun erscheinen in Whale-Trade-Tabellen aber haben keine
polymonit/predicts.guru Profile. Für T-D106 (On-Chain-Discovery-Scan) vormerken.

---

## Nächste Schritte

- [ ] predicts.guru Manual-Check: `0x2a2c53bd278c04da9962fcf96490e17f3dfb9bc1` und `0xdc876e6873772d38716fda7f2452a78d426d7ab6` — Win-Rate und Trade-Count verifizieren
- [ ] beachboy4 in 30-Tage Shadow-Watching aufnehmen: Verfolgen ob MDD-Ereignis wiederholt
- [ ] T-D106 (On-Chain-Discovery-Scan): immotawizard, blindStaking, CemeterySun Adressen identifizieren
- [ ] Nächster Scout: Mai 2026 nach 30-Tage-Review der aktuellen Tier-B-Wallets (Erasmus, TheSpiritofUkraine)
- [ ] Onur Approval: Keine sofortige Aktion nötig

_Scout-Methodik gemäß WALLET_SCOUT_BRIEFING.md v1.2 — Small-Pool-KongScore (5 Kategorien)_
_Quelle: polymonit.com April 2026, merlin.trade, cointrenches.io, 0xinsider.com_
