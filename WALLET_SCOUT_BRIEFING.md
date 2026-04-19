# WALLET_SCOUT_BRIEFING.md
_Das Herzstück des KongTradeBot_

**Version:** 1.0
**Erstellt:** 2026-04-19
**Status:** ACTIVE

---

## Warum dieses Dokument kritisch ist

Die Wallet-Selektion bestimmt 80% der Performance eines Copy-Trading-Bots.
Technische Perfektion ohne gute Wallet-Auswahl führt zu Verlusten.
Mittelmäßige Technik mit exzellenter Wallet-Auswahl führt zu Gewinnen.

Dieses Dokument ist die verbindliche Regel-Basis für:
- Den WalletScout (automatischer Discovery-Prozess)
- Das KongScore-Bewertungssystem (Ranking der Kandidaten)
- Brrudi's manuelle Approval-Entscheidungen
- Das KongReview-System (regelmäßige Selbstkritik)

Alle Claude-Instanzen (Chat, Server-CC, Windows-CC) MÜSSEN dieses
Dokument bei jeder Wallet-bezogenen Aufgabe konsultieren.

---

## Teil 1: Philosophische Grundlage

Die Regeln in diesem Dokument basieren auf 4 intellektuellen Quellen:

### 1.1 Ray Dalio — Principles

Kernprinzipien die wir anwenden:
- "Diversifikation durch unkorrelierte Bets ist das einzige Free Lunch."
  → Keine zwei Wallets mit >70% Kategorie-Überschneidung
  → Max 3 Wallets in gleicher Hauptkategorie
- "System > Intuition, dokumentierte Regeln > Bauchgefühl."
  → Alle Entscheidungen nach diesem Briefing, keine Ausnahmen
- "Pain + Reflection = Progress. Jeder Fehler muss protokolliert werden."
  → Post-Mortem nach 30 Tagen für jede APPROVED-Wallet
  → Shadow-Tracking für REJECTED-Wallets (90 Tage)

### 1.2 Howard Marks — Memos

Kernprinzipien die wir anwenden:
- "Was jeder weiß, ist nicht mehr wertvoll. Edge kommt von Second-Level-Thinking."
  → Wallets auf öffentlichen Top-10-Listen haben degradierten Edge
  → Wir suchen Nischen-Spezialisten, keine Mainstream-Leaderboard-Wallets
- "Risiko wird erst erkannt nachdem es sich materialisiert hat."
  → Stress-Test-Kriterium: Wallet muss durch mindestens 1 Event-Schock stabil gewesen sein
- "Zyklen sind unvermeidlich."
  → Wir unterscheiden zwischen "ruhiger Periode profitabel" und "turbulente Periode profitabel"

### 1.3 Nassim Taleb — Antifragile/Incerto

Kernprinzipien die wir anwenden:
- "Vermeide Ruin-Risiko um jeden Preis. Überleben > Optimierung."
  → Hard Max-Drawdown-Limit (<30%)
  → Portfolio-Level Stress-Test
- "Black Swans kommen — nicht ob, sondern wann."
  → Drawdown-Survival-Kriterium
- "Via Negativa — entscheide durch Elimination, nicht Optimierung."
  → Hard Filters sind K.O.-Kriterien, nicht Empfehlungen
- "Kleine Positionen, viele davon, mit asymmetrischem Upside."
  → Entry-Zone 20–40¢ bevorzugt (Alpha-Zone mit Convexity)

### 1.4 Eigene Recherche (empirische Ebene)

Basis: 8 externe Quellen (Medium 0xIcaruss 127-Wallet-Studie,
PANews 112k-Wallet-Analyse, polymarketcopybot.com, Ratio Blog,
pm.wiki, polymarket-insider-detector GitHub, Polyburg, prediction-hunt).

Cross-Verified-Findings:
- Median Win-Rate der $100K+ Wallets: 61% (nicht 80–90%)
- Gain-to-Loss-Ratio: 2.1+ (verdienen durch Sizing, nicht Trefferquote)
- Max-Position: 8% Durchschnitt bei Top-Tier
- 87.3% aller Wallets verlieren Geld
- Top-Wallets traden in LOW-volume Nischenmärkten, nicht Top-10

---

## Teil 2: Polymarket-Anpassungen der klassischen Frameworks

**WICHTIG:** Polymarket existiert seit 2020. Klassische Finanzmetriken
müssen angepasst werden. Andernfalls findet der Scout niemanden.

### 2.1 Zeit-Anpassungen

| Klassisch | Polymarket-Anpassung |
|-----------|---------------------|
| 5+ Jahre Track-Record | 3+ Monate monatlich profitabel |
| Mehrere Marktzyklen | Mindestens 1 Event-Schock überlebt |
| 500+ Trades | 50+ resolved Trades |

### 2.2 Sample-Size-Realismus

Statistisch ist 50 Trades die absolute Untergrenze. 100+ ist
aussagekräftiger. Aber auf Polymarket haben nur wenige Wallets
200+ resolved Trades. Deshalb:
- **Minimum:** 50 resolved Trades (Hard Filter)
- **Ideal:** 100+ resolved Trades (Score-Bonus)
- **Exzellent:** 200+ (maximaler Score)

### 2.3 Black-Swan-Adaption

Statt "2008 Crisis überlebt" suchen wir:
- Wallet war aktiv während Khamenei-Death-Market (Feb 2026)
- Wallet war aktiv während Iran-Military-Action-Phase (April 2026)
- Wallet hat Oracle-Resolution-Dispute überlebt
- Wallet hat mindestens eine >15% Drawdown-Episode durchgestanden
  und ist danach zu Höchststand zurückgekehrt

---

## Teil 3: Tiered Kriterien-System

Statt Alles-oder-Nichts verwenden wir ein 3-Tier-System.
Das vermeidet Over-Engineering und erlaubt kontrolliertes Experimentieren.

### Tier A — Core Pool (strenge Kriterien)

- Erfüllt ALLE 9 Hard-Filter
- KongScore >= 70
- Max 5 Wallets gleichzeitig
- Copy-Multiplier: 1.0x (volle Größe)
- Fokus: Dalio-Portfolio-Construction angewendet

### Tier B — Experimental Pool

- Erfüllt 7 von 9 Hard-Filter
- KongScore 50–69
- Max 10 Wallets gleichzeitig
- Copy-Multiplier: 0.3–0.5x (reduziert)
- Markiert als "Lern-Wallets"
- Performance-Review nach 30 Tagen: Tier A, Weiter-Tier-B, oder Raus

### Tier C — Shadow Pool (nur Beobachtung)

- Fast-Approved oder Rejected-Kandidaten
- Copy-Multiplier: 0.0x (NICHT kopiert)
- Werden getrackt und analysiert
- Füttern das KongReview-System
- Unbegrenzte Anzahl

### Bootstrapping-Modus (erste 90 Tage)

In den ersten 90 Tagen des Systems:
- Kriterien sind "Targets", nicht absolute Gates
- Bester Kandidat aus jedem Archetyp kommt in Tier B auch wenn
  nicht alle Filter erfüllt
- Nach 90 Tagen: Daten-basierte Verschärfung möglich

**Begründung:** Perfektes System mit null Wallets wäre schlimmer
als okay-System mit 5 Wallets.

---

## Teil 4: Hard Filters (K.O.-Kriterien)

Alle 9 Filter müssen für Tier A erfüllt sein. Für Tier B 7 von 9.

### HF-1: Mindest-Sample-Size
- **Kriterium:** Mindestens 50 resolved Markets
- **Quelle:** polymarketcopybot.com, pm.wiki, Ratio Blog (alle 3 unabhängig)
- **Begründung:** Unter 50 sind Win-Rate und ROI statistisch bedeutungslos

### HF-2: Mindest-Account-Alter
- **Kriterium:** Account existiert seit mindestens 60 Tagen auf Polymarket
- **Quelle:** Polyclawster-Studie, Anti-Sybil-Praxis
- **Begründung:** 3-Wochen-alter Account mit 200 Trades = fast sicher Bot/Sybil/Washtrading

### HF-3: Maximum Drawdown
- **Kriterium:** Max-Drawdown < 30% über gesamten Track-Record
- **Quelle:** polymarketcopybot.com ("most ignored metric — matters most when things go wrong")
- **Begründung:** Wenn wir in Drawdown kopieren, erleben wir Drawdown mit.
  Die meisten Copy-Trader steigen im schlimmsten Moment aus.

### HF-4: Drawdown-Survival
- **Kriterium:** Mindestens 1 Drawdown-Episode >15% überlebt UND zurück zu Höchststand
- **Quelle:** Taleb Antifragilität, Polymarket-angepasst
- **Begründung:** Antifragilität ist unbewiesen wenn kein Stress-Test stattfand

### HF-5: Aktiv in letzten 14 Tagen
- **Kriterium:** Mindestens 3 neue Positionen in letzten 14 Tagen
- **Quelle:** polymarketcopybot.com Staleness-Regel
- **Begründung:** Inaktive Wallets können Strategie geändert haben
- **WICHTIG (v1.1):** Nicht-Aktivität im Bot (0 kopierte Trades) allein ist KEIN
  Removal-Grund vor 30 Tagen Beobachtung. Gründe für 0 Bot-Copies können
  MIN_TRADE_SIZE, Budget-Cap oder Kategorie-Blacklist sein — nicht Wallet-Inaktivität.
  Externe Aktivität (predicts.guru Last-Trade-Date) immer gegenchecken. Siehe Teil 16.

### HF-6: Profit-Konzentration
- **Kriterium:** Keine Einzel-Position > 20% des kumulierten Profits
- **Quelle:** Ratio Blog, Medium 0xIcaruss
- **Begründung:** One-Hit-Wonder sind nicht replizierbar

### HF-7: ROI auf Deposits
- **Kriterium:** Kumulativer ROI auf Deposits > 0%
- **Quelle:** Eigene Erfahrung (wan123-Lektion, 19.04.2026)
- **Begründung:** Hohe Win-Rate mit negativem ROI bedeutet Geldverlust
  trotz häufiger Gewinne (schlechtes Sizing)

### HF-8: Win-Rate-Range
- **Kriterium:** Win-Rate 55–75% ODER >75% MIT Domain-Experte-Signatur
- **Domain-Experte-Signatur:** Haltezeit-Median >3 Tage UND Kategorie-Fokus >70%
  UND keine Last-Minute-Trades
- **Quelle:** polymarket-insider-detector, 0xIcaruss, PANews
- **Begründung:** 80%+ Win-Rate ist fast immer Insider-Typ-A (nicht replizierbar)
  oder Manipulation. Ausnahme: Domain-Experten (Insider-Typ-B) sind Gold wert.

### HF-9: Kein Last-Minute-Trading-Pattern
- **Kriterium:** Weniger als 20% der Trades in den letzten 10 Min vor Resolution
- **Quelle:** polymarket-insider-detector
- **Begründung:** Pre-Resolution-Trading ist Insider-Typ-A. Wir können das nie replizieren.

---

## Teil 5: Soft Scoring (KongScore 0–100)

Zusätzlich zu den Hard-Filtern wird jede Wallet gescored.
Skala: 0–100 Punkte. Tier A braucht >= 70, Tier B >= 50.

| ID | Kriterium | Max Punkte | Framework |
|----|-----------|-----------|-----------|
| SC-1 | Sample-Size (200+ = 20P, 100-199 = 15P, 50-99 = 10P) | 20 | Alle 8 Quellen |
| SC-2 | Kategorie-Fokus (70%+ = 20P, 50-70% = 15P, <50% = 0P) | 20 | Marks (Specialization) |
| SC-3 | Entry-Preis 20-40¢ = 15P, 40-60¢ = 8P, >60¢ = 0P | 15 | Taleb (Asymmetry) |
| SC-4 | ROI:MDD-Ratio (>2.0 = 15P, 1.5-2.0 = 10P, <1.0 = 0P) | 15 | Dalio (Risk-Adjusted) |
| SC-5 | Gain-Loss-Ratio (>2.5 = 10P, 2.0-2.5 = 7P, <1.5 = 0P) | 10 | 0xIcaruss |
| SC-6 | Position-Sizing-Disziplin (<10% = 10P, 10-15% = 5P, >15% = 0P) | 10 | 0xIcaruss |
| SC-7 | Exit-Evidence (aktiv exits = 10P, manchmal = 5P, nie = 0P) | 10 | Ratio Blog |
| SC-8 | Crowdedness-Check (nicht auf Top-10 = 10P, mittel = 5P) | 10 | Marks |
| SC-9 | Stress-Test (durch Event-Schock profitabel = 10P) | 10 | Taleb |
| SC-10 | Scale-In-Pattern (gestaffelte Entries = 5P) Bonus | 5 | Ratio Blog |

**Total möglich: 125 Punkte (inkl. Bonus)**

---

## Teil 6: Red Flags (automatische Disqualifikation)

### RF-1: Sybil-Cluster
Mehrere Wallets mit gemeinsamer Funding-Quelle auf Polygon.
Quelle: polymarket-insider-detector (GitHub).

### RF-2: Volumen-Mover
Wallet-Positionen bewegen Preise um >5% in Märkten mit <$50k Volumen.
Copy-Trader werden zur Exit-Liquidität.
Quelle: Ratio Blog.

### RF-3: Sudden-Spike-nach-Inaktivität
Nach 30+ Tagen inaktiv, plötzlich 50+ Trades in einem Tag.
Wahrscheinlich Bot-Take-Over oder Insider-Info.

### RF-4: Cross-Category-Generalist
Gewinnt gleichmäßig in 5+ unverwandten Kategorien ohne erkennbaren Fokus.
Indiziert generischen Insider (Typ A) oder Manipulation.

### RF-5: Win-Rate-Collapse
Letzte 30 Tage Win-Rate >15 Punkte niedriger als historischer Durchschnitt.
Strategie degradiert oder Edge weg.

---

## Teil 7: Green Flags (Bonus-Aufmerksamkeit)

### GF-1: Domain-Experte-Signatur (Prime Target)
- Kategorie-Fokus >70%
- Mediane Haltezeit >3 Tage
- Konsistent 20–40¢ Entries
- Win-Rate 65–75%
→ Höchste Priorität, sofort in Review-Pipeline

### GF-2: ROI:MDD > 2.0
Außergewöhnlich gute Risk-Adjusted Returns.

### GF-3: Stabile Aktivität >3 Monate
Keine Aussetzer, gleichmäßiger Aktivitätslevel.

### GF-4: Beidseitiger Gewinner
Gewinnt auf YES und NO gleichermäßen (nicht nur eine Seite).

---

## Teil 8: Portfolio-Construction-Regeln (Dalio)

Nicht nur einzelne Wallets — auch deren Kombination matters.

### PC-1: Korrelations-Limit
Keine zwei APPROVED-Wallets mit >70% Überschneidung der Kategorien.

### PC-2: Kategorie-Diversifikation
Maximum 3 Wallets pro Haupt-Kategorie (Politik, Crypto, Sport, Geopolitik).

### PC-3: Archetyp-Diversität
Mindestens 2 verschiedene Archetypen im APPROVED-Pool:
- Politik-Spezialist
- Crypto-Spezialist
- Sport-Short-Term
- Geopolitik-Long-Term
- Contrarian

### PC-4: Ruin-Szenario-Test
Bei jeder Approval-Entscheidung explizit prüfen:
> "Wenn ALLE APPROVED-Wallets gleichzeitig ihren Max-Drawdown erleben,
> überleben wir das finanziell?"

Wenn nein → Reduziere Anzahl oder Position-Größen.

---

## Teil 9: Discovery-Strategie

### 9.1 Problem mit Mainstream-Leaderboards

Polymonit-Leaderboard zeigt öffentlich Top-Wallets.
Tausende Copy-Trader sehen dasselbe → Edge verduennt, Decoy-Trading-Wars entstehen.

### 9.2 Unsere nicht-Mainstream-Quellen (Roadmap)

| Phase | Zeitraum | Quelle |
|-------|---------|--------|
| 1 | Heute | Polymonit-Leaderboard (Baseline) |
| 2 | Q2 2026 | Direkte On-Chain-Analyse (Polygon, Wallets die NIE auf Leaderboard) |
| 3 | Q3 2026 | Grok-API: X/Twitter Nischen-Communities + On-Chain-Verifizierung |
| 4 | Q4 2026 | Discord, Reddit, Market-Maker-Detection via Bid-Ask-Analyse |

### 9.3 Grok-Verifikations-Protokoll

**VERIFIKATIONS-REGEL:** Keine Wallet wird direkt aus X-Quelle approved.
X-Hinweise werden nur als Discovery-Signal genutzt. Die Approval erfolgt
IMMER nach Hard-Filter + KongScore.
**Begründung:** X-Content ist voll mit Manipulation und Werbung.
Brrudi-Instruktion (19.04.2026): "Quellen müssen halbwegs verifiziert sein."

Wenn Grok eine Wallet via X-Post vorschlägt:
1. Wallet-Adresse gegen Polygon-Blockchain verifizieren
2. Hard-Filter-Check wie bei polymonit-Kandidaten
3. KongScore berechnen
4. Kreuzprüfung: Andere unabhängige Quellen? X-Account glaubwürdig?
5. Erst nach ALLEN Checks in Tier B oder Tier A

---

## Teil 10: Post-Mortem-Protokoll

### 10.1 Nach 30 Tagen Approval

Jede APPROVED-Wallet wird nach 30 Tagen schriftlich reviewed:
- Haben die KongScore-Zahlen gestimmt?
- Wo war Performance besser/schlechter als erwartet?
- Wurde ein Hard-Filter oder Soft-Score falsch kalibriert?
- Was haben wir gelernt?

Der Review wird automatisch in KNOWLEDGE_BASE.md archiviert.

### 10.2 Nach 90 Tagen Review

Tier-Bewertung:
- Tier B Wallets: Reif für Tier A? Oder raus?
- Tier A Wallets: Noch in Top-Form? Oder Tier B?

### 10.3 Quarterly Criteria Review

Siehe separates Dokument: KONG_REVIEW_SYSTEM.md

---

## Teil 11: Versionierung

### Version 1.0 (2026-04-19) — Initial
- Basis-Briefing nach 4 Frameworks + 8-Quellen-Recherche
- 9 Hard-Filter, 10 Soft-Score-Kategorien
- 3-Tier-System
- Bootstrapping-Modus für erste 90 Tage
- Integration der Polymarket-Anpassungen
- Grok-Verifikations-Protokoll (Roadmap)

### Version 1.1 (2026-04-19) — Post-Audit-Erkenntnisse
Änderungen basierend auf erstem Audit (3 Wallets entfernt, 10 beobachtet):
- Teil 14 hinzugefügt: Skipped-Signal-Feedback-Loop
- Teil 15 hinzugefügt: Discovery-Gap — Wallet-Universum außerhalb TARGET_WALLETS
- Teil 16 hinzugefügt: Beobachtungs-Zeitraum-Regel (30 Tage Minimum)
- HF-5 Hinweis ergänzt: Nicht-Aktivität im Bot ≠ Wallet-Inaktivität

Format zukünftiger Versionen: 1.x für Kriterien-Anpassungen;
Major-Release 2.0 für grundlegende Systemänderungen.

---

## Teil 14: Skipped-Signal-Feedback-Loop

_Erkenntnis aus Audit v1.0 (19.04.2026)_

**Problem:** Bot filtert Signale aus ohne die Konsequenz zu messen.
Welche Filter sind zu streng? Wie viel Profit wird durch MIN_TRADE_SIZE,
Budget-Cap oder Kategorie-Blacklist verhindert? Survivorship Bias
in der Auswertung ohne Messung.

**Implementation:** T-D105 Skipped-Signal-Tracker
- `data/all_signals.jsonl` speichert jedes erkannte Signal (inkl. Skip-Grund)
- Nach Market-Resolution: fiktive Performance berechnen
- Weekly-Report zeigt welcher Filter am meisten gekostet hat

**Regel:** Kein Filter ist "settled" solange seine Schatten-Kosten
nicht gemessen werden.

---

## Teil 15: Discovery-Gap

_Erkenntnis aus Audit v1.0 (19.04.2026)_

**Problem:** Briefing prüft nur bestehende TARGET_WALLETS.
Polymarket hat ~300.000 Wallets. Nur 15 zu auditieren ist nur die halbe Wahrheit.
Es könnten bessere Kandidaten existieren die der alte Scout nie vorgeschlagen hat.

**Lösung in Phasen:**

| Phase | Zeitraum | Quelle |
|-------|---------|--------|
| 1 | Aktuell | Polymonit-Leaderboard als Basis-Scout |
| 2 | T-D106 | On-Chain-Discovery-Scan aller aktiven Polygon-Wallets mit Polymarket-Trades |
| 3 | Q3 2026 | Grok/X-basiertes Nischen-Discovery |

**Regel:** Audit ohne Discovery ist Wartung. Audit MIT Discovery ist Strategie.

---

## Teil 16: Beobachtungs-Zeitraum-Regel

_Erkenntnis aus Audit v1.0 (19.04.2026)_

**Problem:** Nicht-aktive Wallets dürfen nicht voreilig entfernt werden.
4 Tage Bot-Betrieb sind statistisch bedeutungslos. 0 kopierte Bot-Trades
kann viele Ursachen haben die nichts mit der Wallet-Qualität zu tun haben.

**Regel:** Entfernung wegen Inaktivität erfordert MINDESTENS:
1. 30 Tage Beobachtungsfenster
2. Wallet hatte Chance in mindestens 2 verschiedenen Markt-Kategorien zu agieren
3. Kein externes Signal dass Wallet generell aktiv ist
   (via predicts.guru Last-Trade-Date check)

**Wallets mit 0 Bot-Copies aber externer Aktivität** bleiben im Watching-Status.

**Mögliche Gründe für 0 Bot-Copies (kein Removal-Grund):**
- MIN_TRADE_SIZE filtert Whale-Trades heraus
- Budget-Cap blockiert neue Orders
- Trade-Kategorien auf Blacklist
- Wallet wochenend-inaktiv (Sportereignisse)
- Wallet agiert in anderen Märkten als der Bot verfolgt

---

## Teil 12: Quellen-Register

### Externe Polymarket-Recherche (8 Quellen)
1. Medium — 0xIcaruss "Tracked Every Wallet That Made $100K+" (2026-03-12)
2. PANews — "Deconstructing 112,000 Polymarket addresses" (2026-03-10)
3. PANews — "Who is the real god on Polymarket?" (2026-01-13)
4. polymarketcopybot.com — "How to Evaluate a Polymarket Trader" (2026-02-28)
5. Ratio Blog — "7 Red Flags That Will WRECK Your Copy Trading" (2026-03-02)
6. pm.wiki — "How to Track Profitable Wallets" (2026-03-09)
7. GitHub — suislanchez/polymarket-insider-detector
8. Polyburg Blog — "Reading Confidence From Bets" (2026-01-23)

### Framework-Quellen
9. Ray Dalio — Principles (Life and Work)
10. Howard Marks — Oaktree Memos, "The Most Important Thing"
11. Nassim Nicholas Taleb — Incerto (Antifragile, Black Swan, Fooled by Randomness)

### Interne Quellen
12. Brrudi's eigene Erfahrung Tage 1–4 (April 2026)
13. wan123-Lektion (hohe Win-Rate, negativer ROI)
14. KNOWLEDGE_BASE.md P001–P057

---

## Teil 13: Disziplin-Regeln

### D-1: Änderungen nur bei signifikanten Daten
Kriterien werden nur angepasst wenn Shadow-Daten 3 Monate in Folge
in gleiche Richtung zeigen. Keine Überreaktion auf Einzelfälle.

### D-2: Override-Verbot
Keine manuelle Approval ohne KongScore-Check. Wenn Brrudi "Bauchgefühl"
hat: Wallet in Tier B, nicht Tier A, und Post-Mortem nach 30 Tagen.

### D-3: Versionierung ist Pflicht
Jede Kriterien-Änderung geht durch Git-Commit mit Begründung.
Rollback muss jederzeit möglich sein.

### D-4: Transparenz
Alle Approval-Entscheidungen werden dokumentiert in: `data/wallet_decisions.jsonl`
- Datum, KongScore, Hard-Filter-Bestehen, Tier, kurze Begründung
