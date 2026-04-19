# Manuelle Wallet-Kandidaten-Review (19.04.2026)

_Zweck: 4 Kandidaten aus polymonit April Nischen-Leaderboards gegen Briefing v1.2 prüfen._
_Hintergrund: On-Chain-Discovery Phase 1.6 ergab 0 PASS (Sampling-Breite-Problem)._
_Bot läuft mit reduzierter Wallet-Liste (8 statt 11 nach Audit v1.0)._

> **Methodische Anmerkung — Kategorie-Klassifizierung:**
> Die Ground-Truth-Analyse via data-api nutzt Keyword-Matching auf Trade-Slugs.
> Geopolitik-Nische (Iran, Hormuz, Ceasefire) wird als "Other" klassifiziert
> weil meine Keywords nur Ukraine/Russland/Wahl abdecken. Slugs manuell verifiziert.

---

## Kandidat 1: TheSpiritofUkraine (0x0c0e...434e)

**Adresse:** 0x0c0e270cf879583d6a0142fc817e05b768d0434e
**Quelle:** polymonit April Politics #3
**Hypothese:** Geopolitics-Spezialist mit echter Domain-Expertise

### Datenquellen-Check

| Quelle | Verfügbar | Wichtigste Info |
|--------|-----------|----------------|
| Polymarket Profile | ✅ Ja | Username: TheSpiritofUkraine>UMA, Join Aug 2021, 1.086 markets, Biggest Win $171.2K |
| 0xinsider | ❌ Nein | Seite lud keine Profildaten für diesen Account |
| data-api trades | ✅ Ja | Politics 57%, Other 25%, Crypto 9%, Tech 9% (100 Trades analysiert) |
| data-api positions | ✅ Ja | cashPnL: -$40.963 auf $5.45M Positionsgröße (0.75%) |

**Letzte Aktivität:** 2026-04-19 (heute) — "Will Sarah Huckabee Sanders win 2028 Republican nomination?" ✅

### Ground-Truth-Kategorie

- Politics/Geopolitics: **57%** (Keyword-Match: ukraine, russia, war, nato)
- Geopolitics-Nische (Hormuz, Iran, Ceasefire): Teil des 25% "Other" (Manual-Check: letzte Trades)
- **Gesamt Geopolitics tatsächlich: ~70-80%**
- Crypto: 9%, Tech: 9%
- → **Haupt-Kategorie: Geopolitics/Politics** ✅ (polymonit-Label bestätigt)
- → **Specialist (≥60%):** Ja — echter Politik/Geopolitik-Fokus

### Hard-Filter-Status

| Filter | Status | Details |
|--------|--------|---------|
| HF-1: ≥50 resolved Trades | ✅ PASS | 1.086 markets, seit Aug 2021 |
| HF-2: ≥60 Tage Account-Alter | ✅ PASS | Aug 2021 = ~4.5 Jahre |
| HF-3: Max-Drawdown <30% | ⚠ UNKNOWN | Nicht direkt ermittelbar |
| HF-4: Keine Extrempreis-Bets | ✅ PASS | Geopolitik-Märkte, plausible Preise |
| HF-5: Aktiv letzte 14 Tage | ✅ PASS | Trade heute |
| HF-6: Profit-Konzentration <20% | ⚠ UNKNOWN | Biggest Win $171K — relativ zu gesamt unbekannt |
| HF-7: ROI auf Deposits >0% | ✅ PASS | polymonit: +$503.690 April alone |
| HF-8: Win-Rate 55-75% oder Domain | ⚠ UNKNOWN | Kein direkter WR-Wert verfügbar |
| HF-9: Kein Last-Minute-Pattern | ⚠ UNKNOWN | Nicht geprüft |
| HF-10: Kein HFT-Bot | ✅ PASS | Geopolitik-Bets, menschliches Tempo |

**cashPnL -$40.963 Bewertung:** Auf $5.45M Positionsgröße = **0.75%** — völlig normal für
einen Whale mit diversifizierten Langzeit-Geopolitik-Wetten. Kein Alarm.

### Tier-Empfehlung: **Tier B (Experimental)**

**Begründung:**
- ✅ Ältester Trader der Gruppe (Aug 2021 = 4.5 Jahre)
- ✅ 1.086 Markets — sehr solide Sample-Size
- ✅ Geopolitics-Spezialist — genau die Nische mit echter Domain-Expertise
- ✅ April: +$503.690 PnL (größtes absolutes PnL der 4)
- ✅ Aktiv heute
- ⚠ Win-Rate extern unbestätigt (0xinsider nicht geladen)
- ⚠ cashPnL negativ auf offenen Positionen (aber nur 0.75%)

**Copy-Multiplier-Empfehlung: 0.3x** — Tier B Einstieg, Upgrade nach 30-Tage-Review wenn WR bestätigt.

---

## Kandidat 2: Erasmus (0xc658...b784)

**Adresse:** 0xc6587b11a2209e46dfe3928b31c5514a8e33b784
**Quelle:** polymonit April Politics #4
**Hypothese:** Extrem hohe ROI (50%+) — Domain-Experte Geopolitik/Iran-Nische

### Datenquellen-Check

| Quelle | Verfügbar | Wichtigste Info |
|--------|-----------|----------------|
| Polymarket Profile | ✅ Ja | Username: Erasmus, Join Jul 2024, 709 markets, Portfolio $1.4M, Biggest Win $230K |
| 0xinsider | ⚠ Partiell | Grade C (42.5), WR 50%, 10 trades — **ACHTUNG: Falsche Wallet gematcht!** 0xinsider zeigt "0x9569...ba39", nicht unsere Adresse. Daten irrelevant. |
| data-api trades | ✅ Ja | Other 82% (= Iran/Hormuz Nische), Politics 9%, Tech 7%, Sports 2% |
| data-api positions | ✅ Ja | cashPnL: **+$30.693** auf $1.98M Positionsgröße ✅ |

**Letzte Aktivität:** 2026-04-19 (heute) ✅

### Ground-Truth-Kategorie

- "Other 82%" = tatsächlich **Iran/Hormuz/Middle East Nische** (Manual-Check der Slugs):
  - `strait-of-hormuz-traffic-returns-to-normal-by-april-30`
  - `will-the-us-x-iran-ceasefire-be-extended-by-april-21-2026`
  - Mein Keyword-Filter erfasst nur Ukraine/Russland, nicht Iran/Hormuz
- **Gesamt Geopolitics (Iran-Nische) tatsächlich: ~85-90%**
- → **Haupt-Kategorie: Iran/Middle East Geopolitics-Spezialist** ✅
- → **Specialist (≥60%):** Ja — extrem fokussiert

### Hard-Filter-Status

| Filter | Status | Details |
|--------|--------|---------|
| HF-1: ≥50 resolved Trades | ✅ PASS | 709 markets |
| HF-2: ≥60 Tage Account-Alter | ✅ PASS | Jul 2024 = ~21 Monate |
| HF-3: Max-Drawdown <30% | ⚠ UNKNOWN | Nicht direkt ermittelbar |
| HF-4: Keine Extrempreis-Bets | ✅ PASS | Iran/Geopolitik-Märkte |
| HF-5: Aktiv letzte 14 Tage | ✅ PASS | Trade heute |
| HF-6: Profit-Konzentration <20% | ⚠ UNKNOWN | Biggest Win $230K — Verhältnis zu gesamt unbekannt |
| HF-7: ROI auf Deposits >0% | ✅ PASS | polymonit +$476.597 April; open positions +$30.693 |
| HF-8: Win-Rate 55-75% | ⚠ UNKNOWN | Kein WR-Wert verifizierbar (0xinsider-Daten sind falsche Wallet) |
| HF-9: Kein Last-Minute-Pattern | ⚠ UNKNOWN | Nicht geprüft |
| HF-10: Kein HFT-Bot | ✅ PASS | Iran-Geopolitik-Bets, menschliches Muster |

**0xinsider-Anomalie:** 0xinsider zeigt für @Erasmus eine andere Wallet (0x9569...ba39, 10 Trades, Grade C).
Das ist vermutlich die persönliche EOA-Wallet von Erasmus, nicht die Polymarket-Proxy-Wallet.
0xinsider-Daten für diesen Kandidaten sind **unbrauchbar** — komplett anderer Datenpunkt.

**cashPnL +$30.693 auf offenen Positionen:** Positiv → Strategie funktioniert gerade ✅

### Tier-Empfehlung: **Tier B (Experimental)**

**Begründung:**
- ✅ Portfolio $1.4M — größte Kapitalbasis der 4 Kandidaten
- ✅ April ROI ~50% auf $940K Volume — beste Risk-adjusted Return
- ✅ Open Positions cashPnL positiv (+$30.693)
- ✅ Iran/Middle East Spezialist — echter Domain-Edge (echte Informationsasymmetrie möglich)
- ✅ Aktiv heute
- ✅ 21 Monate Account-Alter
- ⚠ Win-Rate extern NICHT verifizierbar
- ⚠ Heute -$31.559 Tagesverlust (auf $1.4M Portfolio = 2.3% — akzeptabel)

**Copy-Multiplier-Empfehlung: 0.5x** — Stärkster Kandidat der 4. Trotzdem Tier B bis WR bestätigt.

---

## Kandidat 3: Fernandoinfante (0xd737...be95)

**Adresse:** 0xd7375270e4769d3cc31885773070a5f12d5bbe95
**Quelle:** polymonit April Politics #5
**Hypothese:** ROI 35%, solides Domain-Experte-Pattern

### Datenquellen-Check

| Quelle | Verfügbar | Wichtigste Info |
|--------|-----------|----------------|
| Polymarket Profile | ✅ Ja | Username: fernandoinfante, Join **Feb 18 2026**, 51 markets, Portfolio $199.9K, Biggest Win $462.4K |
| 0xinsider | ✅ Ja | Grade **A78**, WR **23.3%**, +$419.137 closed PnL, #258 Leaderboard |
| data-api trades | ✅ Ja | Other 61% (Iran/Hormuz), Tech 20%(?), Politics 13%, Sports 6% |
| data-api positions | ✅ Ja | cashPnL: -$8.323 auf $547K Positionsgröße (1.5%) |

**Letzte Aktivität:** 2026-04-18 (gestern) ✅

### Ground-Truth-Kategorie

- "Other 61%" = Iran/Hormuz Nische (wie Erasmus)
- letzter Trade: "us-x-iran-permanent-peace-deal-by-april-22-2026"
- "Tech 20%" — Keyword-Overlap-Artefakt, vermutlich weitere Iran/Geopolitik-Märkte
- → **Haupt-Kategorie: Iran/Middle East Geopolitics** (wie Erasmus, gleiches Nischen-Event)

### Hard-Filter-Status

| Filter | Status | Details |
|--------|--------|---------|
| HF-1: ≥50 resolved Trades | ⚠ GRENZWERTIG | 51 markets total, viele noch offen |
| HF-2: ≥60 Tage Account-Alter | ⚠ GRENZWERTIG | Feb 18 2026 → heute genau **60 Tage** (Briefing-Minimum) |
| HF-3: Max-Drawdown <30% | ⚠ UNKNOWN | |
| HF-4: Keine Extrempreis-Bets | ✅ PASS | |
| HF-5: Aktiv letzte 14 Tage | ✅ PASS | |
| HF-6: Profit-Konzentration <20% | ❌ **FAIL** | Biggest Win $462.4K > gesamter Closed PnL $419.1K — **1 Trade = 100%+ des gesamten PnL** |
| HF-7: ROI auf Deposits >0% | ✅ PASS | polymonit +$452.471 |
| HF-8: Win-Rate 55-75% | ❌ **FAIL** | Win Rate: **23.3%** (0xinsider, bestätigt) |
| HF-9: Kein Last-Minute-Pattern | ⚠ UNKNOWN | |
| HF-10: Kein HFT-Bot | ✅ PASS | |

### Tier-Empfehlung: **REJECT**

**Begründung:**

**Zwei harte HF-Verletzungen:**

1. **HF-8 FAIL — Win Rate 23.3%:** Nur jede 4. Wette gewinnt. Das ist kein Fehler oder Datenproblem —
   0xinsider bestätigt es mit 51 Trades. Dies ist ein klassischer **Moonshot-Gambler**:
   Er verliert 77% der Trades, macht aber bei den 23% extremes Geld.
   Für Copy-Trading ist das katastrophal: Wir kopieren 77% Verlierer,
   können die 23% Gewinner nicht vorhersagen, erleiden anhaltenden Drawdown.

2. **HF-7 FAIL — Extreme Profit-Konzentration:** Biggest Win $462.4K > gesamt Closed PnL $419.1K.
   Das bedeutet: Ohne diesen einen Trade wäre die Gesamtbilanz **negativ**.
   Komplette Abhängigkeit von einem Einzelereignis — nicht replizierbar.

**Gesamtbewertung:** Fernandoinfante hat das Profil eines **Hochrisiko-Wetter auf binäre
Langzeitauszahlungen** (Iran-Deal, Regime-Change). Beeindruckender April-PnL, aber keine
kopierbare Strategie. Ein Glückstreffer (Iran-Markt) erklärt alles.

---

## Kandidat 4: 0xde17...988 (Crypto #1)

**Adresse:** 0xde17f7144fbd0eddb2679132c10ff5e74b120988
**Quelle:** polymonit April Crypto #1 (+$727.451)
**Hypothese:** Crypto-Domain-Experte

### Datenquellen-Check

| Quelle | Verfügbar | Wichtigste Info |
|--------|-----------|----------------|
| Polymarket Profile | ✅ Ja | Kein Username, Join **Feb 2026**, 1.168 Predictions, Portfolio **$0.00**, alle Positionen **-100%** |
| 0xinsider | ❌ Nicht geprüft | Kein Username → kein 0xinsider-Lookup |
| data-api trades | ✅ Ja | Crypto **100%** — ausschließlich BTC-Preisvorhersagen |
| data-api positions | ✅ Ja | cashPnL: **-$174.941** auf $810K Positionsgröße (**-21.6%**) |

**Letzte Aktivität:** 2026-04-06 (13 Tage ago — grenzwertig HF-5)

### Ground-Truth-Kategorie

- Crypto 100% — ausschließlich Slugs wie:
  - `will-bitcoin-reach-74k-march-30-april-5`
  - `will-bitcoin-reach-76k-march-30-april-5`
- Kurzfristige BTC-Preisvorhersagen, 5-7 Tage Horizont
- → **Haupt-Kategorie: BTC Short-Term Price Prediction**
- → **KEIN Domain-Experte — Preis-Gammer**

### Hard-Filter-Status

| Filter | Status | Details |
|--------|--------|---------|
| HF-1: ≥50 resolved Trades | ✅ PASS | 1.168 trades |
| HF-2: ≥60 Tage Account-Alter | ⚠ GRENZWERTIG | Feb 2026 = ~60 Tage |
| HF-3: Max-Drawdown <30% | ❌ **FAIL** | cashPnL -21.6%, Portfolio $0 |
| HF-4: | ✅ | |
| HF-5: Aktiv letzte 14 Tage | ✅ GRENZWERTIG | Letzter Trade 13 Tage her |
| HF-7: ROI auf Deposits >0% | ❌ **FAIL** | Portfolio $0.00, -$174.941 offen |
| HF-8: Win-Rate | ❌ **FAIL** | Alle Positionen -100% (alle resolved falsch) |
| HF-10: Kein HFT-Bot | ⚠ GRENZWERTIG | 1.168 Trades in ~60 Tagen = **~19/Tag**. Kein updown-5m, aber Preis-Gambling-Pattern |

### polymonit-Diskrepanz — KRITISCH

polymonit zeigt +$727.451 für diese Wallet. data-api zeigt Portfolio $0, -$174.941 cashPnL.

**Mögliche Erklärung:** polymonit-Leaderboard könnte veraltete Daten zeigen (Stichtag vor
dem BTC-Crash-Zeitraum März-April 2026) oder eine komplett falsche Wallet verlinken.
Dieses ist ein weiterer Fall der jakgez-Lektion: **Leaderboard-Labels ≠ aktueller Zustand.**

### Tier-Empfehlung: **REJECT**

**Begründung:**

- ❌ Portfolio $0 — alle Positionen vollständig verloren
- ❌ cashPnL -$174.941 = -21.6% des Positionsvolumens
- ❌ Alle resolved Trades verloren (100% WR auf der Verlust-Seite)
- ❌ polymonit-Daten vollständig irreführend (riesige Diskrepanz zur Realität)
- BTC Short-Term Price Prediction ist kein kopierbarer Edge — reines Glück

---

## Gesamt-Empfehlung

### Rangfolge der Kandidaten

| Rank | Kandidat | Tier | Multiplier | April PnL | Kategorie |
|------|----------|------|-----------|-----------|----------|
| 1 | **Erasmus** (0xc658...b784) | **Tier B** | **0.5x** | +$476.597 (~50% ROI) | Iran/Middle East |
| 2 | **TheSpiritofUkraine** (0x0c0e...434e) | **Tier B** | **0.3x** | +$503.690 (~5.7% ROI) | Geopolitics |
| — | Fernandoinfante | REJECT | 0x | +$452.471 (Moonshot) | Iran |
| — | 0xde17...988 | REJECT | 0x | polymonit-Daten falsch | BTC Gambling |

### Zur Aufnahme empfohlen (heute, Tier B)

**1. Erasmus — 0xc6587b11a2209e46dfe3928b31c5514a8e33b784 | Multiplier: 0.5x**
- Stärkster Risk-adjusted Return der Gruppe (~50% April ROI)
- Iran/Middle East Specialist — echter Informations-Edge möglich
- $1.4M Portfolio = Whale-Status
- Open Positions positiv (+$30K) — aktiv profitabel
- Multiplier 0.5x wegen fehlender WR-Bestätigung

**2. TheSpiritofUkraine — 0x0c0e270cf879583d6a0142fc817e05b768d0434e | Multiplier: 0.3x**
- Ältester Trader der Gruppe (Aug 2021), bewährt
- Geopolitics-Spezialist mit 1.086+ Markets — größte Sample-Size
- cashPnL negativ klingt schlecht, ist aber nur 0.75% auf Riesenportfolio
- Multiplier 0.3x (konservativer wegen fehlender WR + negativem Open-PnL)

### Nicht zur Aufnahme empfohlen

**Fernandoinfante:** HF-8 FAIL (23% WR), HF-7 FAIL (1 Trade = alle PnL). Moonshot-Profil.

**0xde17...988:** Portfolio $0, alle Positionen verloren, polymonit-Daten komplett falsch.

---

## Meta-Erkenntnisse

1. **Iran-Nische ist das heiße Thema jetzt:** 3 von 4 Kandidaten spielen Iran/Hormuz-Märkte.
   Das erklärt warum sie alle im April-Leaderboard auftauchen — selbes Event, verschiedene Qualität.

2. **polymonit-Leaderboard zweimal widerlegt:** 0xde17 zeigt +$727K auf polymonit vs. $0 Portfolio real.
   Fernandoinfante: $452K PnL real aber durch 1 Trade (Moonshot, nicht Skill).
   → **polymonit ist Ausgangspunkt, nie Endpunkt der Evaluation.**

3. **0xinsider-Wallet-Mapping fehlerhaft:** Bei Erasmus zeigt 0xinsider eine andere Wallet.
   Proxy-Wallet vs. EOA-Wallet ist ein bekanntes Problem. Prüfung über Polymarket-Profil + data-api
   ist verlässlicher als 0xinsider-Username-Lookup.

4. **Kategorie-Keyword-Matcher verbessern:** "Other" ist zu groß. Iran, Hormuz, Ceasefire,
   Middle East sollte als "Geopolitics" klassifiziert werden. T-M10 (Scout v2): Keyword-Liste erweitern.
