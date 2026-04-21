# Verlust-Analyse — 2026-04-18
**KongTradeBot | Bot-Status: ACTIVE (LIVE-Modus) | Erstellt: 2026-04-18 ~21:10 Berlin**

---

## Datenquellen

| Datei | Letzte Änderung | Relevanz |
|---|---|---|
| `trades_archive.json` | 2026-04-18 00:25 Berlin | Alle 90 Trades (BUYs) |
| `metrics.db` | laufend | USDC-Balance-Timeline |
| `.portfolio_snapshot_2026-04-18.json` | 2026-04-18 18:15 Berlin | Snapshot für Tages-PnL |
| `logs/bot_2026-04-18.log` | laufend | Execution-Events, Filter-Entscheidungen |
| Dashboard `/api/portfolio` | live (Polymarket API) | Unrealized PnL der offenen Positionen |

**Einschränkung**: `trades_archive.json` enthält **keine aufgelösten Trades** (alle 90 Einträge haben `aufgeloest: false`, `gewinn_verlust_usdc: 0.0`). Realisierte PnL-Daten sind daher **nicht verfügbar**. Alle P&L-Zahlen stammen aus dem Dashboard (Polymarket Positions-API = unrealisiert).

---

## 1. TRADE-STATISTIK HEUTE (seit 2026-04-18 00:00 Berlin)

**Quelle: `trades_archive.json` (Datum = 2026-04-18) + `logs/bot_2026-04-18.log`**

| Kennzahl | Wert |
|---|---|
| Gesamt BUY-Trades (ausgeführt) | **11** |
| Gesamt Sells/Resolutions im Archiv | **0** |
| USDC eingesetzt (Archiv) | **$123.10** |
| USDC zurückbekommen (Archiv) | **$0.00** (keine Resolutions im Archiv) |
| Zeitfenster aller Fills | **00:09:50 – 00:25:10 Berlin** (16 Minuten) |
| CopyOrders erstellt (ganzer Tag, lt. Log) | **1.907** |
| Orders tatsächlich gesendet (lt. Log) | **0** (nach 00:25 Berlin) |
| Multi-Signal AUSFÜHRUNG-Events (lt. Log) | **85** |
| Multi-Signal-Orders tatsächlich gefüllt | **0** |

> **Wichtig**: Die 11 Archiv-Trades wurden alle zwischen 00:09 und 00:25 Berlin Zeit ausgeführt — ein 16-Minuten-Burst. Danach: **kein einziger "Order gesendet"-Eintrag** im Log bis 21:10 Berlin, obwohl 1.907 CopyOrders erstellt und vom Risk Manager freigegeben wurden.

---

## 2. VERLUSTE — Top 10 ranked (unrealisiert)

**Quelle: Dashboard `/api/portfolio` (Polymarket Positions-API)**  
**Einschränkung**: Direkte API-Abfrage nicht möglich — Positionen werden aus dem Dashboard-Backend bezogen. Ranking basiert auf trades_archive.json sortiert nach Einsatz × implizitem Verlustrisiko (Preis extrem niedrig = hohes Verlustrisiko, da bereits fast-fertige Märkte).

Die 11 heutigen Trades nach Einsatz und Risikoprofil:

| # | Markt | Outcome | Einsatz | Preis @ Entry | Shares | Wallet | Zeit |
|---|---|---|---|---|---|---|---|
| 1 | Baltimore Orioles vs. Cleveland Guardians | Baltimore Orioles | $24.28 | 0.38 | 63.89 | 0x2005...875ea | 00:11:30 |
| 2 | Baltimore Orioles vs. Cleveland Guardians | Cleveland Guardians | $18.05 | 0.56 | 32.23 | 0x2005...875ea | 00:15:20 |
| 3 | Hornets vs. Magic: O/U 218.5 | Over | $12.76 | 0.47 | 27.15 | 0x2005...875ea | 00:14:10 |
| 4 | Hornets vs. Magic: O/U 218.5 | Under | $12.45 | 0.48 | 25.94 | 0x2005...875ea | 00:09:50 |
| 5 | Tallahassee: Clement Tabur vs Tyler Zink | Clement Tabur | $8.48 | 0.77 | 11.01 | 0xee61...debf | 00:25:00 |
| 6 | Hornets vs. Magic | Hornets | $7.17 | 0.19 | 37.74 | 0x2005...875ea | 00:11:00 |
| 7 | Spread: New York Yankees (-2.5) | New York Yankees | $6.57 | 0.49 | 13.41 | 0xee61...debf | 00:24:30 |
| 8 | Hornets vs. Magic | Hornets | $5.66 | 0.15 | 37.73 | 0x2005...875ea | 00:12:20 |
| 9 | Hornets vs. Magic | Hornets | $5.66 | 0.15 | 37.73 | 0x2005...875ea | 00:25:10 |
| 10 | Kansas City Royals vs. New York Yankees | Kansas City Royals | $5.41 | 0.17 | 31.82 | 0x2005...875ea | 00:10:20 |

**Alle 11 Märkte sind US-Sport** (NBA: Hornets vs Magic, MLB: 4 Spiele, Tennis: 1). Die Märkte wurden in der **Nacht von 17. auf 18. April** platziert — zu einem Zeitpunkt, als die US-Spiele noch liefen oder gerade endeten.

> **Datenlimit**: Unrealisierte PnL pro Position (aktuelle Marktpreise) ist nur über die Polymarket Positions-API verfügbar (nicht im Archiv). Die Gesamtposition zeigt -$9.69 Tagesverlust auf $205.19 Snapshot-Wert → heutige Positionen sind ~$195.50 wert.

---

## 3. GEWINNE — Top 5 ranked (unrealisiert)

**Quelle: `trades_archive.json` + Dashboard**

Aus den 11 heutigen Archiv-Trades gibt es **keine aufgelösten Trades mit GEWINN-Eintrag**. Die einzige heute-Trade mit relativem Gewinnpotenzial (höchster Entry-Preis = niedrigstes Verlustrisiko):

| # | Markt | Outcome | Einsatz | Preis @ Entry | Wallet | Zeit |
|---|---|---|---|---|---|---|
| 1 | Tallahassee: Clement Tabur vs Tyler Zink | Clement Tabur | $8.48 | **0.77** | 0xee61...debf | 00:25:00 |
| 2 | Milwaukee Brewers vs. Miami Marlins | Miami Marlins | $16.61 | **0.52** | 0x2005...875ea | 00:10:20 |
| 3 | Spread: New York Yankees (-2.5) | New York Yankees | $6.57 | **0.49** | 0xee61...debf | 00:24:30 |
| 4 | Hornets vs. Magic: O/U 218.5 | Over | $12.76 | **0.47** | 0x2005...875ea | 00:14:10 |
| 5 | Hornets vs. Magic: O/U 218.5 | Under | $12.45 | **0.48** | 0x2005...875ea | 00:09:50 |

> **Anmerkung**: "Gewinn" bedeutet hier nur ein günstigerer Entry-Preis (näher 0.50), nicht ein tatsächlich realisierter Gewinn.

---

## 4. KATEGORIE-BREAKDOWN

**Quelle: `trades_archive.json` (alle 90 Trades)**

### Gesamtübersicht (alle Tage)

| Kategorie | Anzahl Trades | Gesamt-Einsatz | PnL | Win-Rate |
|---|---|---|---|---|
| Sonstiges | 71 | $937.63 | n/v (keine Resolutions) | n/v |
| Geopolitik | 11 | $271.83 | n/v | n/v |
| Sport | 8 | $140.92 | n/v | n/v |

**Kritische Kategorisierungs-Anomalie**: Von den 11 heutigen Trades sind **10 als "Sonstiges" kategorisiert** — obwohl sie alle US-Sport-Märkte sind (NBA, MLB, Tennis-Spread). Nur 1 Trade (Tennis Tallahassee) wurde korrekt als "Sport" kategorisiert.

**Faktisch für heute (2026-04-18), nach Markt-Typ:**

| Typ (manuell) | Anzahl | Einsatz | Quelle-Kategorie im Archiv |
|---|---|---|---|
| NBA Basketball (Hornets vs Magic) | 5 Trades | $43.70 | Sonstiges ❌ |
| MLB Baseball (4 Matchups) | 4 Trades | $64.35 | Sonstiges ❌ |
| Tennis ATP/WTA | 1 Trade | $8.48 | Sport ✓ |
| Spread (Yankees -2.5) | 1 Trade | $6.57 | Sonstiges ❌ |

---

## 5. WALLET-PERFORMANCE HEUTE

**Quelle: `trades_archive.json` (Datum 2026-04-18) + `logs/bot_2026-04-18.log`**

| Wallet (Kurzform) | Signals heute (gesamt) | Übernommen (Archiv) | Investiert | PnL |
|---|---|---|---|---|
| 0x2005d...875ea | ≫ (dominant, ganzer Tag) | **9 Trades** | $108.05 | n/v (keine Resolution) |
| 0xee613...debf | aktiv heute | **2 Trades** | $15.05 | n/v |
| Alle anderen | aktiv (lt. Log) | **0 heute** | $0 | — |

**Historisch (alle 90 Trades):**

| Wallet | Alias (Log) | Total Trades | Total Einsatz | % am Portfolio |
|---|---|---|---|---|
| 0x2005d...875ea | sovereign2013* | 74 | $1,003.95 | 74.3% |
| 0xbaa2c...5f4b | RN1* | 9 | $191.39 | 14.2% |
| 0xde7be...5f4b | – | 4 | $115.00 | 8.5% |
| 0x7a619...24 | – | 1 | $25.00 | 1.9% |
| 0xee613...debf | – | 2 | $15.05 | 1.1% |

\* Alias aus `logs/bot_2026-04-18.log` abgeleitet (Log nennt "sovereign2013" und "RN1" für entsprechende Wallets).

---

## 6. FILTER-EFFEKTIVITÄT

**Quelle: `logs/bot_2026-04-18.log` (ganzer Tag 2026-04-18)**

| Filter | Anzahl Ablehnungen | Details |
|---|---|---|
| Odds außerhalb 15-85% Range | **543** | `❌ Trade abgelehnt: Odds außerhalb 15-85% Range` |
| Preis zu extrem (>93% / <7%) | **484** | `❌ Trade abgelehnt: Preis zu extrem` |
| Micro-Trade < MIN_TRADE_SIZE $0.50 | **1.657** | `❌ Trade abgelehnt: Micro-Trade geskipped: $X.XX < MIN_TRADE_SIZE $0.50` |
| Berechnete Größe $0.00 | **32** (geschätzt) | `❌ Trade abgelehnt: Berechnete Größe $0.00 unter Minimum $0.01` |
| **Gesamt Ablehnungen** | **~2.716** | Aus Log |

### Spezifische Filter-Checks:

**a) MIN_VOLUMEN=50000 Check (Minimum Markt-Volumen $50k):**
> Nicht überprüfbar — Markt-Volumendaten fehlen im Archiv. Es gibt keinen Log-Eintrag der Form "Trade abgelehnt: Volumen zu gering", daher ist unklar ob dieser Filter aktiv ist.

**b) CATEGORY_BLACKLIST-Check:**
> Kein CATEGORY_BLACKLIST aktiv laut .env und Log. Alle Kategorien (Sport, Geopolitik, Sonstiges) werden getradet.

**c) Trades < MIN_TRADE_SIZE ($0.50):**
> Filter **aktiv und greift**. Beispiel-Log-Eintrag: `❌ Trade abgelehnt: Micro-Trade geskipped: $0.09 < MIN_TRADE_SIZE $0.50`
> ABER: Risk Manager genehmigt **weiterhin Orders von $0.01–$0.30** (`✅ Trade erlaubt | Größe: $0.01`), die erst in der copy_trading-Schicht abgelehnt werden. Reihenfolge: CopyTrading-Filter kommt NACH Risk Manager für diese Micro-Checks.

**d) Wie kamen die 11 heutigen Trades durch?**
> Alle 11 haben Entry-Preise 0.15–0.77 (innerhalb 15–85% Range) und Größen $5.41–$24.28 (> $0.50). Sie passierten alle Filter korrekt.

---

## 7. TIMING-MUSTER

**Quelle: `trades_archive.json` + `metrics.db` + `logs/`**

### Balance-Verlauf heute (Berlin-Zeit):

| Zeitpunkt | USDC-Balance | Ereignis |
|---|---|---|
| 00:00 Berlin | $64.51 | Start des Tages (von gestern) |
| 00:09–00:25 Berlin | $64.51 → $4.44 | **16-Minuten-Burst**: 11 Trades platziert, -$60.07 cash |
| 00:25 Berlin | $4.44 | Kasse fast leer, keine weiteren Orders möglich |
| 07:16 Berlin | $4.63 | Letzter Fehler "not enough balance: 4.63 → order 17.80 USDC" |
| **08:25 Berlin** | **$629.05** | **Deposit: +$624.42 USDC** |
| 08:25 – 23:00 Berlin | $629.05 | Stabil — **trotz Deposit: 0 neue Orders ausgeführt** |

### Zeitliche Verteilung der Verluste:

- **00:09–00:25 Berlin (02:09–02:25 UTC)**: Einziges aktives Handelsfenster heute
- US-Sport-Zeiten: Die Hornets vs. Magic NBA-Partie beginnt typisch 19:30 US Eastern = 01:30 Berlin. Bei Platzierung um 00:09–00:25 Berlin war das Spiel noch **im Gange oder gerade beendet**
- MLB-Spiele (Baltimore, KC, Milwaukee, Yankees): Startzeiten typisch 19:05–20:05 Eastern = 01:05–02:05 Berlin → ebenfalls noch aktiv oder soeben beendet

**Verlust-Burst-Zeitfenster**: Klar identifiziert als **00:09–00:25 Berlin** (100% der heutigen Fills in 16 Minuten). Kein Verlust-Burst abends — da ab 00:25 keine neuen Fills stattfanden.

---

## 8. MULTI-SIGNAL vs. EINZEL-SIGNAL

**Quelle: `logs/bot_2026-04-18.log`**

| Kategorie | Anzahl | Ausgeführt (Archiv) | Ausgeführt (CLOB) |
|---|---|---|---|
| Archiv-Trades heute total | 11 | 11 | 11 (vor 00:25) |
| davon Multi-Signal (2+ Wallets) | 0 | 0 | 0 |
| davon Einzel-Signal | 11 | 11 | 11 |
| Multi-Signal AUSFÜHRUNG-Events heute (Log) | 85 | — | **0** (CLOB-Problem) |
| Einzel-Signal-Orders heute (Log) | ~1.822 | — | **0** (CLOB-Problem) |

**Win-Rate Vergleich (heute)**: Nicht messbar — keine Resolutions im Archiv.

**Historisch (alle 90 Trades)**: Kein aufgelöster Trade → Win-Rate nicht kalkulierbar.

> **Kritisch**: 85 Multi-Signal-Executions wurden heute vom Pipeline ausgelöst (inkl. Tennis ATP Busan, Oeiras 3, Barcelona Open mit je 2 Wallets), aber **kein einziger wurde tatsächlich an das CLOB gesendet** — trotz $629 verfügbarem Cash nach dem Deposit um 08:25.

---

## BEOBACHTUNGEN

1. **Alle 11 heutigen Archiv-Trades wurden in einem 16-Minuten-Fenster (00:09–00:25 Berlin) platziert**, ausschließlich auf US-Sport-Märkte, die zu diesem Zeitpunkt noch liefen oder soeben endeten.

2. **Nach dem Deposit von $624 um 08:25 Berlin wurde bis 21:10 kein einziger Order ans CLOB gesendet**, obwohl 85 Multi-Signal-Executions und 1.907 CopyOrders[LIVE] erzeugt wurden (Quelle: `logs/bot_2026-04-18.log`).

3. **10 von 11 heutigen Sport-Trades sind als "Sonstiges" kategorisiert** statt als "Sport" — betrifft NBA- und MLB-Märkte, die vom Kategorisierungs-Modul nicht erkannt werden.

4. **Wallet 0x2005d...875ea (sovereign2013) ist für 74 von 90 Trades und $1.003 von $1.350 (74%) des gesamten investierten Kapitals verantwortlich** — eine extrem hohe Konzentration auf eine einzige Quell-Wallet.

5. **Das Archiv enthält 0 aufgelöste Trades** (`aufgeloest: false` bei allen 90 Einträgen), obwohl der Resolver-Loop alle 15 Minuten läuft — der tatsächliche realisierte PnL ist daher im Archiv nicht nachvollziehbar und alle Dashboard-PnL-Zahlen stammen aus der Polymarket Live-API (unrealisiert).

---

*Bericht-Basis: `trades_archive.json` (90 Trades, Stand 00:25 Berlin), `metrics.db` (2.500 Balance-Snapshots heute), `logs/bot_2026-04-18.log` (5,0 MB, Stand 21:00 Berlin), `.portfolio_snapshot_2026-04-18.json` (Snapshot 205.19 USDC @ 18:15 Berlin).*
