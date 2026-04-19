# HOOK + April#1 Sports — Externe Verifikation (19.04.2026)

_Zweck: Multiplier-Review für zwei intern als 2.0x markierte Wallets._
_Trigger: Intern gesetzte 2x-Aliases ohne externe WR-Verifikation — Audit-Gap._

---

## April#1 Sports (0x492442eab586f242b53bda933fd5de859c8a3782)

### Quellen

| Quelle | Daten | Vertrauen |
|--------|-------|-----------|
| polymonit | April 2026 Rank #1, +$6,289,409 auf $24.5M Volume | Nur absolut, keine WR |
| cointrenches.com | WR 46.7%, Lifetime PnL **-$9.8M bis -$11.1M**, $185M Total Volume | Hoch |
| data-api Positions | $0 open Portfolio, 0 cashPnL | Direkt on-chain |
| data-api Trades | 98% Sports, 2% Other | Ground Truth |

### Hard-Filter Ergebnis

| Filter | Wert | Status |
|--------|------|--------|
| HF-1 Aktivität | Letzter Trade 16.04.2026 (3 Tage) | ✅ PASS |
| HF-2 Tenure | ~3-4 Monate | ✅ PASS |
| HF-7 Depositscheck | Lifetime PnL -$9.8M trotz April-Peak | ⚠ GRENZFALL |
| HF-8 Win-Rate | **46.7% < 55%** | ❌ FAIL |
| HF-10 HFT-Bot | >100 Trades/Tag, konstant Sports, geringe Frequenz-Varianz | ❌ FAIL |

**Gesamturteil: 2 FAILS → REMOVE oder WATCHING 0.3x**

### Analyse

Das April #1 Ranking täuscht. Das Geschäftsmodell ist nicht Vorhersagequalität,
sondern Positionsgrößen-Arbitrage: $200K–$700K pro NBA-Trade erzeugen absolute
Dollar-Gewinne trotz negativem EV (WR < 50%).

- **Nicht kopierbar bei Retail-Scale:** Bot handelt mit Positionen 200–1000x
  größer als KongBot ($50-$500). Liquiditäts-Regime ist anders.
- **Lifetime negativ:** -$9.8M bestätigt, dass die April-Welle Reversion zu
  erwarten ist, kein Skill-Edge.
- **HFT-Muster:** Sports-Only, mechanisch, hohe Frequenz = HF-10 FAIL.

### Empfehlung

**WATCHING 0.3x** (statt aktuell 2.0x)

Begründung: Wenn mit 2.0x kopiert und Bot schlägt 90%-Serie fehl → überproportionaler
Schaden. Kein Edge nachweisbar. Falls im nächsten 30-Day-Review WR > 55% extern
bestätigt → Upgrade möglich. Derzeit: keine externe Quelle bestätigt WR ≥ 55%.

---

## HOOK (0x0b7a6030507efe5db145fbb57a25ba0c5f9d86cf)

### Quellen

| Quelle | Daten | Vertrauen |
|--------|-------|-----------|
| Polymarket Profil | 46 Predictions, $11,549 Portfolio, +$272 open PnL | Mittel (PolyProfile) |
| 0xinsider | WR 38.5%, 28 Trades gezählt, +$30,779 closed PnL, Grade B61.7 | Mittel |
| predicts.guru (via Exa) | WR 67%, 31 Trades, $34,964 PnL, Rank 4275 | Mittel (Methodologie unklar) |
| data-api Trades | 96% "Other" (Tech/AI), 3% Politics, 1% Sports | Ground Truth Kategorien |

### Hard-Filter Ergebnis

| Filter | Wert | Status |
|--------|------|--------|
| HF-1 Aktivität | Letzter Trade 18.04.2026 (gestern) | ✅ PASS |
| HF-2 Tenure | Feb/Mär 2026, ~60 Tage | ⚠ GRENZFALL (Minimum 60d) |
| HF-5 Kopierbarkeit | Nischen: Tech/AI (DeepSeek V4, China-Taiwan) | ✅ PASS |
| HF-8 Win-Rate | 38.5% (0xinsider) vs 67% (predicts.guru) — **DISKREPANZ** | ⚠ UNKLAR |

**WR-Diskrepanz: 38.5% vs 67% bei 28-31 Trades — Methoden-Unterschied, zu wenig Trades für Signifikanz.**

### Analyse

Positiv:
- Aktiv gestern, positives open PnL (+$272), +$30K closed PnL
- Klare Nische: Tech/AI (nicht generalist), erkennbares Profil
- Portfolio $11.5K zeigt echter User, kein Whale-Bot

Negativ:
- 46 Trades total — zu wenig für statistische Signifikanz (HF-2 borderline)
- WR-Diskrepanz zwischen Quellen unaufgelöst — welche zählt welche Trades?
- 2.0x auf unverifizierten Account mit 46 Trades ist unverhältnismäßiges Risiko
- Nicht in polymonit Top 10 — kein Leistungsnachweis auf großem Sample

### Empfehlung

**REDUCE 2.0x → 1.0x**

Begründung: Kein externer Grund für 2x-Premium. Wenn in 30 Tagen (2026-05-19)
WR > 55% auf ≥ 100 Trades bestätigt → Upgrade auf 1.5x. Derzeit: Tier B 1.0x
bis ausreichend Daten vorhanden.

---

## Übergreifende Erkenntnisse

### Audit-Gap: Interne Aliases ohne Ground-Truth

Beide Wallets hatten 2.0x-Aliases gesetzt ohne externe WR-Verifikation.
Alias `April#1 Sports` klingt wie ein starkes Signal — ist aber nur ein
April-Ranking, kein WR-Beweis.

**Regel (→ P077):** Jedes Multiplier ≥ 1.5x braucht externen WR-Nachweis ≥ 55%
aus mindestens einer unabhängigen Quelle (0xinsider, predicts.guru, cointrenches).

### polymonit-Ranking ≠ Copyable

April #1 auf polymonit (+$6.3M) ist Positionsgrößen-Effekt, kein Skill-Edge.
Zweiter Fall nach 0xde17 (+$727K polymonit, $0 Realität) dass absolute Dollar
komplett irreführen können. → "polymonit = Ausgangspunkt, nie Endpunkt" bestätigt.

---

## Zusammenfassung

| Wallet | Alt | Neu | Grund |
|--------|-----|-----|-------|
| April#1 Sports | 2.0x | 0.3x WATCHING | HF-8 FAIL (WR 46.7%), Lifetime -$9.8M, HFT-Bot |
| HOOK | 2.0x | 1.0x | Sample zu klein (46 Trades), WR-Diskrepanz unaufgelöst |

**Nächster Review beider Wallets: T-D109 — 2026-05-19**
