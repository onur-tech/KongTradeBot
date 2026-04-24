# Block 3 — Academic Evidence: Copy-Trading & Prediction-Market-Edge
*Research-Datum: 2026-04-24 | Quellen: arXiv, SSRN, QuantPedia, IOSCO, Oxford JFE*

---

## Key Findings mit Quellen

### Paper 1: The Anatomy of Polymarket (2026)
**Autoren:** Kwok Ping Tsang, Zichao Yang  
**Jahr:** März 2026  
**arXiv:** 2603.03136  

**Kernbefunde:**
- Transaktions-Level-Analyse der 2024-Präsidentschaftswahl auf Polymarket
- Dokumentiert "Emergence of Whale Traders in October" als eigene Phase
- Arbitrage-Abweichungen engten sich im Verlauf ein ("narrowed over time")
- Kyle's Lambda sank um >10x: Markt wurde effizienter über 10 Monate
- Methodik-Innovation: Unterscheidung Minting/Burning/Conversion/Exchange (wichtig für echte PnL-Berechnung)

**Implikation für KongTrade:** Whale-Edge ist episodisch (2024-Wahl), nicht konstant. In Nicht-Wahl-Jahren ist der Markt effizienter, die Edge kleiner.

---

### Paper 2: Political Shocks and Price Discovery in Prediction Markets (2026)
**arXiv:** 2603.03152  

**Kernbefunde:**
- Biden-Rückzug, Debatte, October-Whale-Inflows als diskrete Schocks dokumentiert
- Adverse Selection: Informed Traders imposieren Kosten auf Liquidity Provider
- Cross-Market-Participation nahm zu — Preiseffizienz steigt mit Markttiefe

---

### Paper 3: Unravelling the Probabilistic Forest: Arbitrage in Prediction Markets (2025)
**arXiv:** 2508.03474  

**Kernbefunde:**
- Zwei Formen von Arbitrage dokumentiert: Market Rebalancing + Combinatorial (Multi-Market)
- **Geschätztes extrahiertes Profit: $40M** in analysierten Märkten
- Arbitrage-Chancen existieren, sind aber kurzlebig (Millisekunden bis Sekunden)

---

### Paper 4: Price Formation in Field Prediction Markets (2023)
**Journal:** Journal of Prediction Markets, ScienceDirect  

**Kernbefunde:**
- Prediction-Market-Preise sind gut kalibriert: 30%-Events lösen sich ~30% auf
- Mispricing ist real, aber meist <5–10 Prozentpunkte, und transient
- Mispricing 3–7x/Woche in liquiden Märkten; häufiger in thin markets

---

### Paper 5: IOSCO Online Imitative Trading Practices (2024/2025)
**Quellen:** IOSCOPD776 (Okt 2024), IOSCOPD793 (Jun 2025)  

**Kernbefunde:**
- **Nur 48,5% der Copy-Trading-Follower profitabel** über 90 Tage (Bybit/Binance/MEXC)
- 97% der Lead Trader profitabel — aber nur 48,5% der Follower
- Regulatorische Sorge: Copy-Trading erhöht Risikobereitschaft (Ratchet-Effekt)
- Massenkopieten derselben Leader → Crowded Trades → Amplifikation von Volatilität

---

### Paper 6: Systematic Edges in Prediction Markets (QuantPedia)
**Dokumentierte Edges mit Evidenz:**

| Edge | Evidenz | Stärke |
|------|---------|--------|
| Longshot Bias | Stark; Avg Profit Favorites -3,64%, Outsider -26,08% | ✅ Robust |
| Intra-Exchange Arbitrage | PredictIt 2016: bis 55¢ Profit/Contract | ✅ Historisch |
| Inter-Exchange Arbitrage | Existiert, aber nur Sekunden bis Minuten | ⚠️ Sehr flüchtig |
| Informed Trader Edge | Empirisch für Spezialisten belegt (Wahl-Experten) | ✅ Category-specific |
| Copy-Trading Edge | Keine robuste Evidenz | ❌ Nicht belegt |
| Weather-Market Edge | Keine publizierten Studien | ⁉️ Unerforscht |

---

### Paper 7: Alpha Decay Research (Di Mascio/Lines, SSRN)
**Kernbefund:**
- Alpha-Decay in Trading-Strategien ist dokumentiert und messbar
- Strategies verlieren Edge typischerweise über 6–24 Monate wenn bekannt/kopiert
- "Gap between typical and top-quartile returns reflects survivorship bias rather than attainable outcomes"

---

## Ist Copy-Trading wissenschaftlich belegt profitabel?

**Antwort: NEIN — zumindest nicht unter realistischen Bedingungen.**

### Zusammenfassung der Evidence:

```
Baseline: 50% Follower profitabel (Coin-Flip)
Empirisch: 48,5% profitabel (leicht unter Coin-Flip)
Nach Slippage/Fees: ~45% profitabel (geschätzt)
Fazit: Copy-Trading ohne starken Edge-Filter = langfristiger Kapitalverlust
```

**Ausnahmen die in Evidence erscheinen:**
1. Top-5% der Lead-Trader mit echter Informations-Asymmetrie (z.B. Insider, Domain-Experten)
2. Spezialisierung auf enge Kategorie (z.B. Esports-Experte kopiert Esports-Whale)
3. Früher Einstieg bevor Crowd kopiert (erfordert echte Latenz-Überlegenheit)

---

## Welche Edges sind empirisch nachgewiesen?

### ✅ Starke Evidenz:
1. **Longshot Bias** — Favorites sind systematisch underpriced; statistisch robust über Jahrzehnte
2. **Combinatorial Arbitrage** — $40M extrahiert; aber skaliert nicht für kleine Kapital
3. **Informations-Asymmetrie bei Domain-Experten** — Wahl-Forscher, Sports-Statistiker haben reale Edge
4. **Market-Making** — Maker-Rebates auf Polymarket, kein Fee, dokumentiert profitabel aber erfordert Kapital/Infrastruktur

### ⚠️ Moderate Evidenz:
5. **Narrative-Mispricing** — Märkte mit "high narrative appeal" miss-priced um 8–15 Prozentpunkte in Narrativ-Richtung
6. **Low-Liquidity-Mispricing** — Märkte <$100k Volumen zeigen severe mispricing (exploitable aber thin)
7. **Cross-Venue-Mispricing** — Polymarket vs. Kalshi; echte Differenzen existieren, aber kurz

### ❌ Schwache/Keine Evidenz:
8. **Whale-Copy-Trading** — Lead/Follower-Gap ist empirisch negativ (nur 48,5% profitabel)
9. **LLM/AI Prediction** — Keine publizierten Backtest-Ergebnisse die Kosten übertreffen
10. **Social Sentiment** — In Prediction Markets nicht systematisch documentiert

---

## Mythen ohne Beleg

| Mythos | Realität |
|--------|----------|
| "Whale-copying ist Geld drucken" | 48,5% Follower profitabel — nicht anders als Zufall |
| "High Win-Rate = kopierenswert" | Zombie-Orders inflieren Win-Rates; real 50–57% |
| "Leaderboard = alpha" | Survivorship-Bias; Leaderboard rotiert komplett zwischen Zyklen |
| "Mehr Trader = bessere Preise" | Stimmt für Effizienz, macht Copy-Trading-Edge kleiner |
| "AI wird Prediction Markets schlagen" | Bisher keine publizierten Beweise (auch Polymarket/agents ohne Backtest) |
| "Weather ist random — kein Edge" | Gegenteil: ECMWF-Ensemble hat >55% Kalibrierungsgenauigkeit auf 24h |

---

## Survivorship-Bias in Whale-Tracking

**Akademische Bestätigung:**
- "The gap between typical and top-quartile returns reflects survivorship bias rather than attainable outcomes" (Alpha Decay Paper)
- Leaderboard zeigt nur überlebende Wallets — tausende identische Strategien unsichtbar
- 2024-Wahl-Profiteure hatten einmaligen Informationsvorteil (Wahl-Experten, Politikberater)

**Praktische Implikation:**
Wallets die wir heute kopieren, wurden im Kontext 2024-Wahl ausgewählt. Kein Grund anzunehmen, dass die gleichen Wallets 2026 (Midterms, keine Präsidentschaftswahl) führen.

---

## Hindsight-Bias in "Top-Wallet"-Auswahl

**Das Problem:**
1. Wir sehen, wer 2024 gewonnen hat
2. Wir nehmen an, diese Wallets haben Edge
3. Wir kopieren sie 2025/26 in anderen Marktbedingungen
4. Edge war event-specific, nicht generisch

**Akademische Basis:**
Das "Anatomy of Polymarket"-Paper zeigt, dass Whale-Inflows im Oktober 2024 event-specific waren — keine Evidenz für persistente Alpha-Generation in anderen Marktsituationen.

---

## Implikationen für KongTrade-Strategie (konkret)

### 1. Copy-Trading-Component: RISIKOREDUKTION nötig
- **Win-Rate-Filter ist korrekt** (unsere 45%-Hürde in copy_trading.py)
- **Aber:** Win-Rate-Berechnung vermutlich durch Zombie-Orders verzerrt → echte Filter sollten Settlement-basiert sein
- **Kategorie-Check fehlt:** Wallet in Politics → in Non-Election-Year Auto-Downweight

### 2. Weather-Edge: Stärkste ungenutzte Opportunity
- Keine publizierten akademischen Papers zu Weather-Markets (Forschungslücke = Market-Ineffizienz!)
- Ensemble-Forecasts haben nachweislich hohe Kalibrierung (>55% bei 24h) — das IST Edge
- Longshot-Bias gilt auch für Weather: Extreme Events (rare < 10% Preis) sind oft overpriced

### 3. Portfolio-Konstruktion
- IOSCO-Daten: Diversifikation auf 5+ Wallets reduziert Copy-Drawdown
- 3% Cap/Trade + 8% Daily-Loss ist Community-Konsens und deckt sich mit Literatur

### 4. Live-Transition-Empfehlung aus Academic-Evidenz
- Copy-Trading-Komponente: ≤30% des Portfolios (wegen fehlender akademischer Validierung)
- Weather-Komponente: ≤50% wenn deployed (stärkere Edge-Basis)
- Restliche 20%: Cash-Buffer oder Market-Making (wenn Infrastruktur vorhanden)

---

## Quellen
- arXiv:2603.03136 — Tsang & Yang, "Anatomy of Polymarket" (2026)
- arXiv:2603.03152 — "Political Shocks and Price Discovery" (2026)
- arXiv:2508.03474 — "Unravelling Probabilistic Forest: Arbitrage" (2025)
- SSRN:5331995 — Ng, Peng, Tao, Zhou — "Price Discovery in Modern Prediction Markets"
- IOSCOPD776/793 — Online Imitative Trading Practices (2024/2025)
- QuantPedia — "Systematic Edges in Prediction Markets"
- Oxford JFE — "Statistical Predictions of Trading Strategies in Electronic Markets"
- Di Mascio & Lines — "Alpha Decay" (Inalytics/Columbia)
