# Jakgez-Verifikation + Polymarket-Zeitstempel-Semantik (19.04.2026)

_Zweck: (1) Multi-Source-Verifikation des T-D83-Kandidaten jakgez vor Aufnahme-Entscheidung.
(2) Vollständige Zeitstempel-Semantik für Sell-Feature-Implementierung (T-M05)._

---

## Teil 1: Jakgez-Verifikation

### Multi-Source-Check

| Quelle | Verfügbar | Win-Rate | Total Trades | Lifetime PnL | Anmerkung |
|--------|-----------|----------|-------------|-------------|-----------|
| predicts.guru | ❌ Nein | — | — | — | Seite lädt nur JS-Placeholder, keine Daten zugänglich |
| 0xinsider Politics | ❌ Nein | — | — | — | Wallet/Username nicht in Politics-Leaderboard-Liste |
| polymonit.com | ❌ Nein | — | — | — | Login-Wall, kein öffentlicher Wallet-Lookup |
| Polymarket Profile | ✅ Ja | — | 689 predictions | negativ (aktuell -$17.92 today) | Username @jakgez, Join Jan 2026 |
| Polymarket Data-API | ✅ Ja | — | 10 recent trades | — | Letzte Aktivität: MLB Sports, 19.04.2026 |

**Verfügbarkeit: 2/5 Quellen. Win-Rate extern NICHT verifizierbar.**

### Kritischer Befund: Kategorie-Diskrepanz

T-D83 Phase 1.5 hatte `jakgez` als **"Politics-Spezialist (88% Politics-Focus)"** klassifiziert.

Externe Quellen zeigen ein anderes Bild:

| Signal | Quelle | Inhalt |
|--------|--------|--------|
| 0xinsider Politics-Leaderboard | 0xinsider.com | jakgez NICHT vorhanden — kein Politics-Trader |
| Polymarket Profile | polymarket.com | "extensive positions across MLB games and some NBA markets" |
| Data-API letzter Trade | data-api.polymarket.com | MLB Atlanta Braves vs Philadelphia Phillies, O/U 8.5 (19.04.2026) |
| Data-API vorletzter Trade | data-api.polymarket.com | MLB-Slug erkennbar |

**Fazit Diskrepanz:** jakgez ist ein **Sports-Spezialist (MLB/NBA)**, kein Politics-Spezialist.
Die 88%-Politics-Klassifizierung aus dem T-D83-Scan ist falsch oder basiert auf einem veralteten
Datenschnitt. Dies ist ein signifikantes Problem: Wenn die Kategorie-Klassifizierung fehlerhaft ist,
sind alle anderen Metriken (Win-Rate, Drawdown) ebenfalls fragwürdig.

### Konsistenz-Check

| Metrik | T-D83-Angabe | Externe Quellen | Status |
|--------|-------------|----------------|--------|
| Kategorie | Politics 88% | Sports (MLB/NBA) | ❌ WIDERSPRUCH |
| Join-Datum | ~Jan 2026 (94 Tage) | Januar 2026 | ✅ Konsistent |
| Trades gesamt | ≥500 | 689 predictions | ✅ Konsistent |
| Win-Rate 60% | intern geschätzt | Extern: NICHT verifizierbar | ⚠ Unbestätigt |
| cashPnL offen -$1.943 | intern | Extern: Portfolio $253.40, today -$17.92 | ⚠ Teilweise konsistent |
| HFT-Anteil 0% | intern | MLB/NBA Trades bestätigen menschliches Tempo | ✅ Plausibel |

### cashPnL -$1.943 — Interpretation

- Portfolio-Wert aktuell: $253.40
- Offene cashPnL: -$1.943 = **~0.77% des Portfolios**
- Dies ist **unrealisierter Verlust auf offenen Positionen**, nicht realisierter Gesamtverlust
- Bei Sports-Trader mit MLB/NBA-Intraday-Bets: normales Tages-Drawdown-Niveau
- **Bewertung: Nicht dramatisch. Nicht gefährlich. Normaler Schwankungsbereich.**

### Hard-Filter-Re-Check mit erweiterten Daten

| Filter | Status T-D83 | Status mit neuen Daten | Kommentar |
|--------|-------------|----------------------|-----------|
| HF-1: ≥50 resolved Trades | PASS | ✅ PASS | 689 predictions, viele davon resolved |
| HF-2: ≥14 Tage Aktivität | PASS | ✅ PASS | 94 Tage, letzte Trade heute |
| HF-3: Win-Rate ≥50% | PASS (60% est.) | ⚠ UNVERIFIED | 60% nicht extern bestätigt |
| HF-4: Keine Extrempreis-Bets | PASS | ✅ PASS | MLB O/U bei 0.48 — normal |
| HF-5: Letzte Aktivität ≤14 Tage | PASS | ✅ PASS | Trade heute 19.04.2026 |
| HF-6: Max Drawdown <30% | PASS | ⚠ UNVERIFIED | Keine Drawdown-Daten zugänglich |
| HF-7: Profit-Konzentration <20% | PASS | ⚠ UNVERIFIED | Keine Verteilung zugänglich |
| HF-8: Win-Rate <80% | PASS (60%) | ✅ PASS (wenn 60% stimmt) | Kein Insider-Signal |
| HF-9: Kein Last-Minute-Trading | PASS | ⚠ UNVERIFIED | Nicht überprüfbar |
| HF-10: Kein HFT-Bot | PASS | ✅ PASS | Menschliches Trade-Tempo, MLB-Bets |
| Kategorie-Validierung | Politics 88% | ❌ FAIL (Sports ist real) | Scan-Klassifizierung fehlerhaft |

### Empfehlung

**Kategorie: WATCHING (Shadow-Track) — mit Revisionsnotiz**

**Begründung:**

Die Hard-Filter selbst sind nicht das Problem — jakgez besteht HF-1/2/4/5/8/10 klar.
Das Problem ist **fehlende externe Verifikation kombiniert mit Kategorie-Diskrepanz:**

1. **Nur 1 von 5 Quellen liefert echte Daten** — predicts.guru, polymarketanalytics.com und
   polymonit.com sind für diese Wallet nicht zugänglich. Externe Win-Rate-Bestätigung unmöglich.

2. **Kategorie-Fehlklassifizierung:** Der Scan sagte Politics (88%), die Realität zeigt Sports (MLB/NBA).
   Das bedeutet: Die Kategorie-Statistiken im Scan-Report sind nicht verlässlich.
   Möglicherweise wurden kurzfristige Spikes (z.B. eine US-Wahl-Spekulation) als Hauptkategorie gewertet.

3. **Sports-Spezialist ist trotzdem interessant:** MLB/NBA mit 60% WR (falls bestätigt) bei 689+ Trades
   wäre ein valider Copy-Trade-Kandidat — aber die Win-Rate muss erst verifiziert werden.

**Nächster Schritt:** In 30 Tagen (2026-05-19) mit echten Resolved-Trade-Zahlen re-evaluieren.
Wenn externe Quellen bis dahin verfügbar werden (predicts.guru), sofort nachholen.

**NICHT aufnehmen in Tier A oder B ohne externe Win-Rate-Bestätigung.**

---

## Teil 2: Polymarket-Zeitstempel-Semantik

_Quellen: Gamma-API Live-Calls (active + closed market), Polymarket-Docs._

### Alle Zeitstempel-Felder

| Feld | Semantik | Wann gesetzt | Beispiel |
|------|----------|-------------|---------|
| `startDate` | Offizieller Marktstart | Bei Erstellung | `2025-05-02T15:48:00Z` |
| `startDateIso` | Wie `startDate`, nur Datum | Bei Erstellung | `2025-05-02` |
| `endDate` | Geplantes Marktende / Resolution-Zieldatum | Bei Erstellung | `2026-07-31T12:00:00Z` |
| `endDateIso` | Wie `endDate`, nur Datum | Bei Erstellung | `2026-07-31` |
| `acceptingOrdersTimestamp` | Wann der Markt **begann** Orders anzunehmen | Bei Aktivierung | `2025-05-02T15:47:37Z` |
| `acceptingOrders` | Boolean: Nimmt der Markt **gerade** Orders an? | Live aktualisiert | `true` / `false` |
| `closedTime` | Wann Trading tatsächlich gestoppt hat | Nur bei closed Märkten | `2020-11-02 16:31:01+00` |
| `deployingTimestamp` | Wann Deployment begann | Intern, bei Erstellung | `2025-05-02T15:47:04Z` |
| `updatedAt` | Letzter DB-Update des Market-Objekts | Laufend | `2026-04-19T09:41:22Z` |
| `createdAt` | Wann Market-Record angelegt wurde | Bei Erstellung | `2025-05-02T15:03:10Z` |

**Nicht vorhanden in Gamma-API:** `resolutionTime`, `acceptingOrdersUntil`, `claimableFrom`

### Wichtige Semantik-Korrekturen

**`acceptingOrdersTimestamp` ≠ "bis wann Orders angenommen werden"**

Geläufige Fehlinterpretation: Man könnte denken, dies gibt an, *bis wann* Sell-Orders möglich sind.
Tatsächlich: Es ist der Zeitpunkt, *ab wann* der Markt Orders annimmt (Market-Start-Signal).
Es gibt **kein `acceptingOrdersUntil`-Feld** in der Gamma-API.

**`closedTime` erscheint nur in geschlossenen Märkten und kann vor `endDate` liegen:**
- Biden-COVID-Markt: `endDate` = 04. Nov 2020, `closedTime` = 02. Nov 2020 (2 Tage früher)
- Trading kann also **vor dem angekündigten endDate** gestoppt werden

**`endDate` = Resolution-Ankündigung, nicht garantiertes Trading-Ende**

### Market-Lifecycle-Diagramm

```
deployingTimestamp
       │
       ▼
acceptingOrdersTimestamp ──→ Market-Start (Trading offen)
       │
       │  [Trading-Phase: acceptingOrders = true]
       │
       ▼
   endDate  ──────────────────→ Ziel-Resolution-Datum (angekündigt)
       │
       │  ⚠ Oder: Trading-Stopp VORHER wenn Polymarket manuell schließt
       │
       ▼
  closedTime ────────────────→ Trading tatsächlich gestoppt
  (acceptingOrders = false)
       │
       │  ⚠ DEAD ZONE: Weder Sell noch Claim möglich
       │
       ▼
  [Resolution durch UMA oder Resolver-Adresse]
       │
       ▼
  [Claim verfügbar] ─────────→ Kein explizites Feld! Erkennbar durch:
                                - closedTime gesetzt + outcomePrices = ["0","1"] o.ä.
                                - Bot: resolver.py prüft redeemable-Status
```

### Für unser Dashboard (Empfehlung)

Statt einer einzigen Spalte "Schliesst in" drei semantisch klare Felder:

| Dashboard-Label | Quelle | Bedeutung |
|----------------|--------|-----------|
| **"Trading bis"** | `endDate` (Näherung) | Bis wann Sell via CLOB möglich (kein exaktes Feld vorhanden) |
| **"Resolution"** | `endDate` | Wann Outcome festgestellt wird (selbes Feld, aber andere Bedeutung) |
| **"Claim möglich"** | Abfrage `redeemable` on-chain | Kein Gamma-API-Feld — muss aktiv geprüft werden |

**Live-Check für "Trading noch möglich":** `acceptingOrders` Boolean aus Gamma-API ist der sicherste Indikator.

### Bedeutung für Sell-Feature (T-M05)

| Phase | Gamma-API-Signal | Aktion |
|-------|-----------------|--------|
| Trading offen | `acceptingOrders = true` | Sell via CLOB möglich |
| Dead-Zone | `acceptingOrders = false`, `closedTime` gesetzt, kein Outcome | Weder Sell noch Claim — warten |
| Claim verfügbar | `closed = true` + `outcomePrices` gesetzt + on-chain `redeemable` | Claim ausführen |

**Für Auto-Sell-Implementierung:** Das Bot muss `acceptingOrders` prüfen (Boolean-Field),
**nicht** `endDate` vergleichen. Trading kann vor `endDate` enden — `acceptingOrders`
ist der verlässliche Live-Indikator.

**`endDate` als Fallback-Trigger für Exit-Alert:** Wenn `endDate - now < 24h` → Exit-Warnung.
Aber echte Prüfung immer via `acceptingOrders`.

### Offene Fragen (nach Recherche)

1. **`resolutionTime` existiert nicht in Gamma-API** — wie erkennt der Bot genau wann Resolution erfolgt?
   Aktuell: resolver.py fragt `redeemable`-Status on-chain. Gibt es einen Webhook oder Poll-Endpunkt?

2. **`closedTime` vs. `endDate` Lücke:** Wenn Polymarket trading 2 Tage vor `endDate` stoppt (wie im
   Biden-Fall), können wir das nur retroaktiv erkennen (wenn `acceptingOrders` auf false springt).
   Gibt es ein Event/Webhook-System?

3. **UMA-Resolution-Timing:** `umaResolutionStatuses` ist in beiden Märkten `"[]"` — wann füllt sich dieses
   Feld? Würde den "Dead Zone bis Claim"-Zeitraum präzisieren.

4. **`acceptingOrdersUntil` im CLOB-API?** Gamma-API hat dieses Feld nicht. Möglicherweise gibt es
   market-level Daten direkt via `clob.polymarket.com` — CLOB-API-Dokumentation prüfen.

---

## Teil 3: Zusammenfassung

| Frage | Antwort |
|-------|---------|
| jakgez Empfehlung | **WATCHING** — externe WR-Bestätigung fehlt, Kategorie-Diskrepanz |
| Externe Quellen bestätigen | 0 von 3 (predicts.guru, polymonit, 0xinsider geben keine Daten für jakgez) |
| cashPnL -$1.943 | Normal — ~0.77% des Portfolios, unrealisiert, kein Alarm |
| Kategorie-Befund | ❌ DISCREPANCY: Scan = Politics 88%, Realität = Sports (MLB/NBA) |
| Gamma-API Zeitstempel | 10 Felder dokumentiert, kein `resolutionTime` / `acceptingOrdersUntil` |
| "Trading endet"-Feld | `acceptingOrders` (Boolean, live) — kein Timestamp-Feld vorhanden |
| "Resolution"-Feld | Keines in Gamma-API — on-chain `redeemable` ist der echte Indikator |
| Dead-Zone vorhanden? | ✅ Ja — zwischen `closedTime` und Claim-Verfügbarkeit |
| Sell-Feature: welches Feld? | `acceptingOrders = true` prüfen, NICHT `endDate` vergleichen |
