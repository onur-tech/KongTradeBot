# Re-Audit: Abgelehnte Wallets — Profit-First v2.0
_Erstellt: 2026-04-20 | Anlass: WALLET_SCOUT_BRIEFING.md v2.0 Rewrite_
_Quellen: wallet_scout_2026-04-20.md, wallet_scout_learning_2026-04-20.md, drpufferfish_countryside_verification.md_
_Framework: v1.x (HF-8 WR-Gate) → v2.0 (HF-0 Profit-First, HF-8 = Strategie-Analyse)_

---

## Philosophischer Hintergrund

v1.x bewertete Wallets nach **Bot-Kompatibilität** → viele profitable Wallets wurden abgelehnt
weil die *Strategie* nicht zu unserem Bot passte, obwohl die *Profitabilität* klar war.

v2.0 trennt scharf:
- **Primärfrage:** Ist das Wallet profitabel? (HF-0 = einziger K.O.)
- **Sekundärfrage:** Welches Bot-Feature brauche ich? (Bot-Roadmap, nicht Ablehnung)

**Einzige valide Ablehnungsgründe in v2.0:**
1. Negative ROI (HF-7 FAIL)
2. Insider-Typ-A — Pre-Resolution-Information (HF-9 FAIL)
3. Bestätiger HFT-Bot (HF-10 FAIL — cointrenches/polymonit-bestätigt)

---

## Gesamt-Übersicht

| # | Wallet | Alt-Urteil | Profit | HF-0 | Neues Urteil v2.0 | Bot-Req |
|---|--------|-----------|--------|------|-------------------|---------|
| 1 | **beachboy4** | WATCHING (HF-3/6/8 FAIL) | +$4.14M | ✅ | WATCHING — T-M21 | T-M21 |
| 2 | **SeriouslySirius** | REJECT (HF-8 FAIL) | +$3.6M | ✅ | WATCHING — T-M21 | T-M21 |
| 3 | **DrPufferfish** | Shadow C (HF-8 FAIL) | +$6.27M | ✅ | WATCHING — T-M20+T-M03 | T-M20, T-M03 |
| 4 | **Countryside** | WATCHING (HF-8 FAIL) | +$1.57M | ✅ | WATCHING — T-M03 | T-M03 |
| 5 | **gmanas** | REJECT (HF-10 Warning) | +$4.96M | ✅ | WATCHING — HF-10 klären | Verifikation |
| 6 | **statwC00KS** | WATCHING (Daten fehlen) | +$539K | ✅ | WATCHING — WR verifizieren | Verifikation |
| 7 | **Fernandoinfante** | REJECT (HF-1+6 FAIL) | ~$452K | ✅ | WATCHING — zu wenig Trades | Mehr Daten |
| 8 | **immotawizard** | REJECT (Daten fehlen) | ~$1.84M | ✅? | WATCHING — Profil fehlt | Mehr Daten |
| 9 | **0x2a2c53bd** | WATCHING (Daten fehlen) | +$1.57M | ✅ | WATCHING — HF-10 prüfen | Verifikation |
| 10 | **432614799197** | WATCHING (Daten fehlen) | +$4.5M | ✅ | WATCHING — HF-10 prüfen | Verifikation |
| 11 | **distinct-baguette** | REJECT (HF-10 FAIL) | — | ❌ | **REJECT — CONFIRMED** | — |
| 12 | **0xdE17f7144** | REJECT (HF-10 FAIL) | — | ❌ | **REJECT — CONFIRMED** | — |
| 13 | **BoneReader** | REJECT (HF-5 FAIL) | ❓ | ❌? | **REJECT — CONFIRMED** | — |
| 14 | **k9Q2mX4L8A7ZP3R** | REJECT (Datenfehler) | Fehler | ❌ | **REJECT — CONFIRMED** | — |

---

## Gruppe A — Profit-First Upgrade: War REJECT/WATCHING wegen WR, bleibt WATCHING mit Bot-Requirement

### 1. SeriouslySirius
- **Adresse:** Nicht dokumentiert (polymonit April Leaderboard)
- **Alt-Urteil:** REJECT — HF-8 FAIL (WR 50.3%)
- **Profit:** +$3.6M all-time | **Trades:** 6,339 | **WR:** 50.3%
- **Kategorie:** Sports/Mixed/Politics

**v1.x Ablehnungsgrund:**
> "HF-8 FAIL: 50.3% Win Rate (unter 55% Minimum). Trotz $3.6M Profit — unser System kann diese Sizing-Strategie nicht replizieren."

**v2.0 Bewertung:**
- HF-0: $3.6M Profit >> $10K → ✅ PASS
- HF-7: Profit positiv (kein ROI-auf-Deposits-Check möglich, aber $3.6M Gesamt ist eindeutig) → ✅ PASS
- HF-9: Keine Insider-Signatur bekannt → ✅ PASS
- HF-10: Kategorie Mixed/Sports, nicht Crypto-HFT → ✅ PASS (vorläufig)
- WR 50.3% = **Sizing/G:L-Strategie** (Typ 3 in Strategie-Matrix)
- 6,339 Trades = exzellente Sample-Size für G:L-Ratio-Tracking

**Wahres Problem:** Bot kann G:L-Ratio-Signale noch nicht proportional skalieren (T-M21 fehlt).

**Neues Urteil v2.0:** ✅ WATCHING (High Priority)
**Bot-Anforderung:** T-M21 (G:L-Ratio-Sizing) — schaltet $3.6M frei
**Review:** 2026-05-19 (T-D109) — bei T-M21-Deployment sofort evaluieren

---

### 2. beachboy4
- **Adresse:** `0xc2e7800b5af46e6093872b177b7a5e7f0563be51`
- **Alt-Urteil:** WATCHING (HF-3 FAIL, HF-6 FAIL, HF-8 FAIL)
- **Profit:** +$4.14M all-time | **Trades:** 149 | **WR:** ~51% | **Joined:** Nov 2025

**v1.x Ablehnungsgrund:**
- HF-3 FAIL: MDD PSG-Villarreal -$7.56M auf einen Bet
- HF-6 FAIL: West Ham-Bet = 84% des Gesamtprofits
- HF-8 FAIL: 51% WR unter 55% Minimum

**v2.0 Bewertung:**
- HF-0: $4.14M Profit >> $10K → ✅ PASS
- HF-7: Deposit-ROI unbekannt, aber $4.14M Profit deutet klar positiv → ✅ vermutet
- HF-9: Strategie vollständig dokumentiert (Buchmacher-Line-Comparison) → ✅ PASS
- HF-10: 149 Trades in 5 Monaten → ✅ PASS
- WR 51% = Sizing-Strategie auf Low-Preis-Favoriten (Entry 68–72¢)
- HF-3 (MDD) bleibt relevant: -$7.56M Verlust auf einen Bet. In v2.0 kein K.O. aber Sizing-Risiko-Hinweis.
- HF-6 (Profit-Konzentration): Signale ohne West Ham-Bet liefern nur $0.66M → mittlere Basis-Performance

**Wahres Problem:**
- Strategie basiert auf extremem Sizing ($3.32M auf einen Bet) — bei unserem $60 Cap replizieren wir nur die Richtung, nicht den Scale
- 51% WR + Sizing = T-M21 required
- Nur 149 Trades = kleines Sample, HF-6 ist Datenproblem nicht Strategie-Problem

**Neues Urteil v2.0:** ✅ WATCHING (Medium Priority)
**Bot-Anforderung:** T-M21 (G:L-Ratio-Sizing), Kategorie Sports
**Review:** 2026-05-19 — Fokus: Gibt es weitere Mega-Bets oder nur Einzel-Event?

---

### 3. DrPufferfish (Re-Audit nach Verifikations-Commit ee67335)
- **Adresse:** `0xdB27Bf2Ac5D428a9c63dbc914611036855a6c56E`
- **Alt-Urteil:** Shadow Tier C (HF-8 FAIL, wahre WR 50.9%, Basket nicht kopierbar)
- **Profit:** +$6.27M all-time | **Trades:** 1,456 | **Wahre WR:** 50.9% (PANews)

**v1.x Ablehnungsgrund:**
- HF-8 FAIL: Wahre WR 50.9% (unter 52% Learning-Threshold)
- Architektur-Inkompatibilität: Basket-Strategie (27 Teams gleichzeitig) nicht replizierbar

**v2.0 Bewertung:**
- HF-0: $6.27M >> $10K → ✅ PASS (höchster Wert aller Kandidaten)
- HF-7: Klar positiv → ✅ PASS
- HF-9: Basket-Hedging mathematisch transparent, kein Insider → ✅ PASS
- HF-10: 6.8 Trades/Tag → ✅ PASS
- WR 50.9% = G:L-Strategie (3.4x Gain:Loss-Ratio) → T-M21
- Basket-Hedging → T-M20 (Bot muss Turnier-Signale bündeln)
- Early-Loss-Selling (Zombie-Orders) → T-M03 (Whale-Exit-Copy)

**Wahres Problem:** Bot fehlen drei Features gleichzeitig (T-M20, T-M21, T-M03).
Sobald **T-M03 live** ist, können zumindest NBA-Einzel-Signale (nicht Basket) kopiert werden.

**Neues Urteil v2.0:** ✅ WATCHING (Highest Value — $6.27M)
**Bot-Anforderungen:** T-M03 (Priorität 1), T-M21 (Priorität 2), T-M20 für vollständige Basket-Strategie
**Review:** 2026-07-20 — nach T-M03-Deployment sofort partiell integrierbar (NBA-Einzel-Signale)

---

### 4. Countryside (Re-Audit nach Verifikations-Commit ee67335)
- **Adresse:** `0xbddf61af533ff524d27154e589d2d7a81510c684`
- **Alt-Urteil:** WATCHING (HF-8 FAIL, wahre WR 48.5–54.7%, Haltezeit < 3h)
- **Profit:** +$1.57M | **ROI auf Deposits:** +19.56% | **WR:** 48.5% (cointrenches) / 54.7% (0xinsider)

**v1.x Ablehnungsgrund:**
- HF-8 FAIL: Haltezeit < 3 Tage (NBA same-day = Stunden)
- WR-Diskrepanz zu widersprüchlich für Approval

**v2.0 Bewertung:**
- HF-0: $1.57M Profit + 19.56% ROI auf Deposits → ✅ PASS
- HF-7: ROI 19.56% → ✅ PASS (stärkster HF-7 aller Kandidaten)
- HF-9: G:L-Ratio-Strategie dokumentiert, kein Insider → ✅ PASS
- HF-10: 4.6 Trades/Tag ("15% human") → ✅ PASS
- WR 48.5–54.7% = G:L-Strategie (1.05x G:L-Ratio, positiver EV wenn WR ≥52%)
- Haltezeit < 3h war HF-8-Kriterium v1.x — in v2.0 ist Haltezeit **kein** K.O.
- Early-Loss-Selling: NBA-Verlierer werden vor Resolution verkauft → T-M03

**EV-Analyse bei WR 54.7%:** +$0.23 EV pro $14-Trade (1.6% EV) — positiv nach Fees.
**EV-Analyse bei WR 48.5%:** -$0.01 EV pro Trade — essentially breakeven.

**Wahres Problem:** WR-Diskrepanz (48.5% vs 54.7%) noch ungelöst. Eigenes Shadow-Tracking nötig.

**Neues Urteil v2.0:** ✅ WATCHING — T-M03 required für korrektes Kopieren
**Bot-Anforderung:** T-M03 (Whale-Exit-Copy), dann T-M21
**Review:** 2026-05-20 (Shadow-Tracking-Ergebnis)

---

## Gruppe B — Daten-getriebene Upgrades: WATCHING bleibt, aber aus anderem Grund

### 5. gmanas
- **Quelle:** wallet_scout_learning_2026-04-20.md
- **Alt-Urteil:** REJECT — HF-10 Warning + WR 53% borderline
- **Profit:** +$4.96M | **Trades:** 4,907 | **WR:** 53% | **Rate:** 58.8 Trades/Tag

**v1.x Ablehnungsgrund:**
> "HF-10 WARNUNG: 58.8 Trades/Tag laut predicts.guru"

**v2.0 Bewertung:**
- HF-0: $4.96M >> $10K → ✅ PASS
- HF-10: 58.8 Trades/Tag ist **Warnzeichen** aber kein bestätigter Bot. Muss verifiziert werden:
  - Crypto 5min-Märkte? → Bot-Verdacht hoch
  - Sports/Politik-Märkte? → Aktiver Mensch möglich
  - polymonit/cointrenches Label vorhanden? → Noch nicht gecheckt

**Neues Urteil v2.0:** ✅ WATCHING — HF-10 Verifikation erforderlich
**Bot-Anforderung:** Falls HF-10 PASS: T-M21 (G:L bei WR 53%)
**Review:** Manual check predicts.guru + cointrenches Kategorie-Check

---

### 6. statwC00KS
- **Adresse:** `0x57a8d63731277200ed26cfde9a8a830d94f36933`
- **Alt-Urteil:** WATCHING — ROI auf Deposits unbekannt
- **Profit:** +$539K | **WR:** 96.2% (0xinsider) | **Trades:** 3,204

**v2.0 Bewertung:**
- HF-0: $539K → ✅ PASS (knapp aber eindeutig)
- 96.2% WR bei 3,204 Trades: **Early-Loss-Selling-Artefakt sehr wahrscheinlich** (wie DrPufferfish/Countryside)
  → Wahre WR via cointrenches oder 0xinsider Gesamt-Check unbedingt nötig
- Wenn wahre WR ≥ 52%: sofort integrierbar
- Wenn wahre WR < 48%: G:L-Check nötig

**Neues Urteil v2.0:** ✅ WATCHING — predicts.guru WR-Verifikation Pflicht vor Integration
**Bot-Anforderung:** TBD nach WR-Verifikation
**Review-Deadline:** 2026-05-05 (aus WALLETS.md)

---

### 7. Fernandoinfante
- **Adresse:** `0xd7375270...` (vollständig nicht dokumentiert)
- **Alt-Urteil:** REJECT — HF-1 FAIL (35 Trades < 50), HF-6 FAIL (One-Hit-Wonder)
- **Profit:** ~$452K (Iran-Bet, 3501% auf einen Trade) | **Joined:** Feb 2026

**v2.0 Bewertung:**
- HF-0: $452K >> $10K → ✅ PASS (wenn Daten korrekt)
- HF-7: 3501% ROI = klar positiv → ✅ PASS
- Nur 35 Trades: in v2.0 kein K.O. aber zu wenig Sample für Strategie-Typ-Bestimmung
- Iran-Bet als 97% des Profits: ist Geopolitics-Expertise oder Lucky-Shot?
- Joined Feb 2026 = nur 2 Monate — noch zu jung für Trend-Bestätigung

**Neues Urteil v2.0:** ✅ WATCHING — nicht Integration-ready, aber nicht verworfen
**Bot-Anforderung:** Mehr Daten abwarten (Mindest-Sample: 50 Trades in verschiedenen Kategorien)
**Review:** 2026-06-20 (60 Tage nach Aufnahme in Shadow)

---

### 8. immotawizard
- **Quelle:** wallet_scout_2026-04-20.md
- **Alt-Urteil:** REJECT — One-Trade-Wonder, kein Wallet-Profil
- **Profit:** ~$1.84M (Real Madrid-Bet) | **Trades:** unbekannt

**v2.0 Bewertung:**
- HF-0: $1.84M >> $10K → ✅ PASS (wenn Daten bestätigt)
- Kein Profil auf predicts.guru/polymonit identifizierbar → Adresse unbekannt
- Kann nicht ohne vollständige Adresse evaluiert werden

**Neues Urteil v2.0:** WATCHING — kein vollständiges Profil verfügbar
**Bot-Anforderung:** Adresse zuerst über T-D106 (On-Chain-Discovery) identifizieren
**Review:** TBD nach Adressidentifikation

---

### 9. 0x2a2c53bd278c04da9962fcf96490e17f3dfb9bc1
- **Alt-Urteil:** WATCHING — Daten fehlen
- **Profit:** +$1.57M all-time / +$1.65M April 2026 | **Volume:** $55.6M April / $26.3M lifetime

**v2.0 Bewertung:**
- HF-0: $1.57M → ✅ PASS
- April $1.65M > Lifetime $1.57M: Rechnerische Anomalie — April-ROI offenbar höher als Gesamtberechnung.
  Mögliche Erklärung: Wallet hatte frühere Verlustperioden, April war ausnahmsweise stark.
- $55.6M Volume in einem Monat: Market-Maker-Warnsignal (HF-10 prüfen)
- WR und Trade-Count fehlen immer noch

**Neues Urteil v2.0:** ✅ WATCHING — HF-10 ist jetzt der entscheidende Check
**Bot-Anforderung:** TBD nach HF-10 Verifikation
**Review:** predicts.guru Manual-Check ausstehend

---

### 10. 432614799197 (0xdc876e6873772d38716fda7f2452a78d426d7ab6)
- **Alt-Urteil:** WATCHING — Daten fehlen
- **Profit:** +$4.5M all-time | **Volume:** $185.5M (2.4% Marge) | **Kategorie:** Cross-category

**v2.0 Bewertung:**
- HF-0: $4.5M → ✅ PASS
- ROI 2.4% auf Volume = niedrige %-Marge (aber absolut +$4.5M ist valide)
- Cross-category = kein Kategorie-Fokus → SC-2 Score 0P
- Kein WR, kein Trade-Count verfügbar
- $185.5M Volume deutet Market-Maker hin (HF-10 Risiko)

**Neues Urteil v2.0:** ✅ WATCHING — HF-10 + WR Verifikation erforderlich
**Bot-Anforderung:** TBD nach Verifikation
**Review:** predicts.guru Manual-Check ausstehend

---

## Gruppe C — Bestätigte Ablehnungen (v2.0 K.O. valide)

### 11. distinct-baguette
- **Alt-Urteil:** REJECT — HF-10 FAIL
- **Profit:** ~$62K auf $3M Volume (2% Marge)
- **Trades:** 40,952 Märkte

**v2.0 Check:** HF-10 CONFIRMED: 40,952 Märkte = Crypto Arb Bot (polymonit-Label "Crypto Arb Bot").
Kein menschlicher Trader macht 40K Märkte. HF-10 ist valider K.O. in v2.0.

**Neues Urteil v2.0:** ❌ **REJECT — FINAL** — HF-10 FAIL bestätigt

---

### 12. 0xdE17f7144fbd0eddb2679132c10ff5e74b120988
- **Alt-Urteil:** REJECT — HF-10 FAIL
- **Profit:** ~$727K | **Trades:** Hunderte bis Tausende BTC-Trades/Tag

**v2.0 Check:** HF-10 CONFIRMED: cointrenches bestätigt "high-frequency crypto micro trading bot since Feb 2026."
Unabhängige Bestätigung (polymonit + cointrenches) = v2.0 K.O.

**Neues Urteil v2.0:** ❌ **REJECT — FINAL** — HF-10 FAIL bestätigt

---

### 13. BoneReader
- **Adresse:** `0xd84c2b6d65dc596f49c7b6aadd6d74ca91e407b9` (aus WALLETS.md Dormante)
- **Alt-Urteil:** REJECT — HF-5 FAIL, 0% WR (Datenfehler), dormant
- **Profit:** $214K angezeigt aber 0% WR → Datenkonsistenz fraglich

**v2.0 Check:**
- HF-0: Profit unklar (Datenfehler) → ❓ nicht verifizierbar
- HF-5: Dormant / keine recent Activity → bleibt problematisch
- 0% WR = klarer Datenfehler in predicts.guru

**Neues Urteil v2.0:** ❌ **REJECT — CONFIRMED** — Daten-Integrität nicht gegeben, inaktiv
**Notiz:** Falls je reaktiviert: neues vollständiges Profil erforderlich

---

### 14. k9Q2mX4L8A7ZP3R (0xd0d605...)
- **Alt-Urteil:** REJECT — Datenfehler
- **Angezeigt:** $535K Profit auf $410 Volume

**v2.0 Check:** $535K Profit auf $410 Gesamtvolumen ist technisch unmöglich.
Mögliche Ursachen: AMM-Arbitrage-Daten, Datenbankfehler, falsche Wallet-Adresse.

**Neues Urteil v2.0:** ❌ **REJECT — CONFIRMED** — Daten-Integritätsfehler

---

## Prioritäts-Matrix v2.0 (Bot-Feature-Unlocks)

| Priorität | Bot-Feature | Wallet(s) | Wert unlocked |
|-----------|-------------|-----------|---------------|
| 🔴 P1 | **T-M03** (Whale-Exit-Copy) | DrPufferfish, Countryside, beachboy4 | ~$11.98M |
| 🟠 P2 | **T-M21** (G:L-Ratio-Sizing) | SeriouslySirius, beachboy4, gmanas | ~$13.52M |
| 🟡 P3 | **T-M20** (Basket-Bundle) | DrPufferfish (vollständig) | ~$6.27M (bereits in T-M03) |
| 🟢 P4 | **Daten-Verifikation** | statwC00KS, gmanas, 0x2a2c, 432614799197 | TBD |

---

## Offene Verifikations-Actions

| Action | Wallet | Deadline | Methode |
|--------|--------|----------|---------|
| predicts.guru Manual Check | statwC00KS | 2026-05-05 | predicts.guru/checker/0x57a8... |
| cointrenches WR | statwC00KS | 2026-05-05 | cointrenches.io |
| HF-10 Verifikation | gmanas | 2026-05-05 | polymonit Kategorie-Label |
| HF-10 + WR + Trade-Count | 0x2a2c53bd | 2026-05-05 | predicts.guru Manual |
| HF-10 + WR + Trade-Count | 432614799197 | 2026-05-05 | predicts.guru Manual |
| Adresse identifizieren | immotawizard | T-D106 | On-Chain-Discovery |
| Shadow-Track | Countryside | 2026-05-20 | polymonit täglich |
| Shadow-Track | DrPufferfish | 2026-07-20 | polymonit täglich |
| 50 Trades abwarten | Fernandoinfante | 2026-06-20 | polymonit |

---

## Zusammenfassung: Was ändert sich durch v2.0?

| Kategorie | v1.x | v2.0 |
|-----------|------|------|
| Confirmed Rejects | 6 | 4 (nur bestätigte HF-10 FAIL + Datenfehler) |
| WATCHING | 4 | 10 |
| Sofort integrierbar | 0 | 0 (weiterhin 0 — warten auf Bot-Features) |
| Philosophie | Bot-Compatibility-Gate | Profit-First + Bot-Roadmap |
| Größter Benefit | — | SeriouslySirius ($3.6M) + beachboy4 ($4.14M) neu in WATCHING |
| Klärungsgewinn | — | WR ≠ K.O., T-M21 = Schlüssel zu $13.52M |

**Kernaussage:** 2 Wallets (SeriouslySirius $3.6M, beachboy4 $4.14M) wurden unter v1.x wegen WR-Gate
permanent abgelehnt. Unter v2.0 sind sie WATCHING — sobald T-M21 deployed ist, sofort integrierbar.

---

_Basiert auf: wallet_scout_2026-04-20.md, wallet_scout_learning_2026-04-20.md,_
_drpufferfish_countryside_verification.md, WALLET_SCOUT_BRIEFING.md v2.0_
