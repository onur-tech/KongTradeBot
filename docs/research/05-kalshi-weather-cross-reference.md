# Block 5 — Kalshi Weather-Markets: Cross-Reference & Learnings
*Research-Datum: 2026-04-24 | Quellen: Kalshi Help, EventArb, Trevor Lasn Blog, WSN, Covers, Oddpool*

---

## Kalshi vs. Polymarket: Strukturvergleich

| Dimension | Kalshi | Polymarket |
|-----------|--------|------------|
| Regulierung | CFTC-reguliert (USA) | Keine reguläre Regulierung (Crypto) |
| KYC | ✅ Pflicht (SSN, US-Adresse) | ❌ Kein KYC (nur Wallet) |
| DE/EU-Nutzer | ❌ Faktisch nicht zugänglich | ✅ Zugänglich |
| Fee-Struktur | Flat $1/Trade | Dynamic Taker %, 0% Maker |
| Resolution-Quelle Weather | NWS Daily Climate Report | Airport ASOS/METAR |
| Resolution-Timing | Nächster Morgen (final NWS) | Selber Tag (typisch) |
| DST-Nuance | NWS nutzt local standard time | Unbekannt/variabel |
| Market-Fokus | Granulare Daily Temp, Precipitation | Global + Daily + Macro |
| Liquidity | Moderate (regulatory = institutionell) | Hoch (global retail) |

---

## Resolution-Rules-Unterschiede (KRITISCH für Arb)

### Kalshi: NWS Daily Climate Report
- **Quelle:** National Weather Service (NWS) offizieller täglicher Klimabericht
- **Timing:** Release am nächsten Morgen
- **Besonderheit:** Nutzt **Local Standard Time** (auch während Daylight Saving Time!)
- **Implikation:** Während DST ist der "Daily High" für Kalshi die höchste Temperatur 01:00–12:59 AM des Folgetages (LST), nicht Mitternacht–Mitternacht (local clock)

### Polymarket: ASOS/METAR (Airport Sensor)
- **Quelle:** Direkt vom Flughafen-Sensor (automatisches System)
- **Timing:** Real-Time + Near-Real-Time Auflösung
- **Besonderheit:** Kann durch externe Einflüsse manipuliert werden (Paris-Skandal!)

### Kritische Differenz:
```
Gleicher Markt "NYC Daily High > 75°F" könnte unterschiedlich resolven weil:
- Kalshi: NWS Report (Standardzeit, next-day-final)
- Polymarket: ASOS Sensor (local time, real-time)
→ Edge: Wer die Differenz kennt, kann vor Resolution-Divergenz positionieren
```

---

## Pricing-Vergleich: Polymarket vs. Kalshi für Weather

### Typische Arbitrage-Opportunities
| Szenario | Polymarket YES | Kalshi NO | Total | Profit/Contract |
|----------|---------------|-----------|-------|-----------------|
| Beispiel NYC-Temp >80°F | $0.45 | $0.52 | $0.97 | $0.03 (3%) |
| Beispiel Chicago >70°F | $0.42 | $0.55 | $0.97 | $0.03 (3%) |
| Extreme Event | $0.08 | $0.90 | $0.98 | $0.02 (2%) |

**Fenster:** Sekunden bis Minuten — nicht manuell handelbar

### Fee-Impakt auf Arb-Profitabilität
```
Arb-Spread: $0.03/Contract
Kalshi Fee: $1 flat → bei 100 Contracts = $1 = 0.01/Contract
Polymarket Fee: 1.8% Taker bei $0.45 = $0.0081/Contract
Total Fee: $0.018/Contract
Net Profit: $0.03 - $0.018 = $0.012/Contract → 1.2%

→ Nur bei >100 Contracts/Trade profitabel (Kalshi flat fee)
→ Benötigt Bot + <90s Execution-Fenster
```

---

## Liquidity-Vergleich

| Markt | Polymarket Liquidity | Kalshi Liquidity |
|-------|---------------------|-----------------|
| NYC Daily High | $10–80k | Moderat (institutionell) |
| Chicago Daily | $5–30k | Moderat |
| Miami/Atlanta | $5–20k | Gering |
| Precipitation Monthly | $14–59k | Gut |
| Hurricane Season | $16–336k | Hoch |

**Generalaussage:** Polymarket hat höhere globale Liquidity durch retail-driven open access. Kalshi hat institutionelle Qualität, aber kleinere Market-Größen für granulare Weather.

---

## Arbitrage-Potenzial (theoretisch)

### Warum existiert die Arb?
1. **Verschiedene Trader-Populationen:** Retail (Polymarket) vs. US-Institutionell (Kalshi)
2. **Verschiedene Resolution-Regeln:** NWS vs. ASOS → gelegentliche Divergenz möglich
3. **Liquiditäts-Asymmetrie:** Kalshi kann Polymarket nicht effizient folgen
4. **Speed-Arbitrage:** Neue Information (Wetterupdate) trifft erst einen Markt

### Warum wir es nicht handeln können:
1. **KYC-Hürde:** Kalshi erfordert US-Identität (SSN) → für DE-Nutzer nicht zugänglich
2. **Execution-Fenster:** Sekunden → unser 10s-Polling würde jedes Fenster verpassen
3. **Capital-Binding:** Beide Seiten gleichzeitig financieren benötigt 2x Kapital

---

## Was wir von Kalshi lernen (ohne es zu handeln)

### 1. NWS als Ground-Truth-Signal
Kalshi vertraut NWS Daily Climate Report → das ist die "offizielle" Temperatur.  
**Für uns:** NWS-Daten als zweite Resolution-Validation neben ASOS einplanen.

### 2. DST-Awareness in Temperature-Modellen
Während Sommerzeit kann ein NWS-"Daily High" eine andere Zeitperiode abdecken als intuitiv angenommen.  
**Für uns:** Wenn wir ECMWF-Forecast für "Daily Max" berechnen, müssen wir exakt wissen ob Kalshi/Polymarket local-clock oder LST verwendet.

### 3. Resolution-Divergenz als Edge
Wenn Polymarket per ASOS auflöst und Kalshi per NWS → gelegentlich verschiedene Werte.  
**Für uns:** Dies ist ein potentieller Hedge-Signal: wenn unsere Forecast-Modelle NWS-Wert besser als Polymarket-Implied vorhersagen → Edge.

### 4. Kalshi-Pricing als Mispricing-Detector
Kalshi-Preise repräsentieren institutionelleren Konsens.  
**Für uns:** Wenn Oddpool.com oder EventArb große Polymarket-Kalshi-Divergenz zeigt → potentieller Einstieg in Polymarket gegen Kalshi als Benchmark.

### 5. Institutional-Grade Calibration
Kalshi (CFTC-reguliert) zieht professionellere Trader an → möglicherweise besser kalibrierte Preise.  
**Implikation:** Systematische Richtungs-Divergenz Polymarket ↔ Kalshi zeigt wo Polymarket mispriced ist.

---

## Verfügbare Arbitrage-Tools (für Monitoring, nicht Trading)

| Tool | Funktion | Zugänglich für uns |
|------|---------|-------------------|
| Oddpool.com | Real-Time Polymarket ↔ Kalshi Preisvergleich | ✅ |
| EventArb.com | Arb-Kalkulator | ✅ |
| ArbBets | AI-gestützte Arb-Detection | ✅ (Monitoring) |
| Dune Analytics Arb-Dashboard | On-Chain Arb-Tracking | ✅ |

**Empfehlung:** Oddpool.com als passiven Mispricing-Monitor einsetzen, auch wenn wir die Arb nicht aktiv handeln. Wenn Polymarket-Kalshi-Divergenz für eine Stadt >5% → erhöhte Aufmerksamkeit für unsere Forecast-Positionen dort.

---

## Kalshi-spezifische Learnings für Weather-Plugin

```
Phase-6-Checklist (aus Kalshi-Research):
□ NWS Daily Climate Report als zweite Datenquelle einbinden
□ DST-aware Zeitberechnung für "Daily Maximum" implementieren
□ Oddpool.com API (falls vorhanden) für Kalshi-Preisvergleich
□ Weather-Plugin-Resolution-Check: welche exakte Quelle nutzt Polymarket pro Markt?
□ Anomalie-Alarm wenn Polymarket stark von Kalshi-implied abweicht
```

---

## Fazit: Cross-Reference-Wert für KongTrade

**Direkte Nutzung (Arb):** ❌ Nicht möglich (KYC)  
**Indirekter Nutzen:**
1. ✅ NWS als Resolution-Ground-Truth verstehen
2. ✅ Kalshi-Pricing als institutioneller Benchmark
3. ✅ Oddpool als Mispricing-Frühwarnsystem
4. ✅ Resolution-Divergenz-Edge theoretisch verstanden
5. ✅ DST-Nuance für Forecast-Kalibrierung

---

## Quellen
- Kalshi Weather Markets Help Center
- Trevor Lasn: "How Prediction Market Arbitrage Works"
- EventArb.com: Arb Calculator
- Oddpool.com: Real-Time Odds Comparison
- WSN.com: Kalshi vs Polymarket 2026
- Covers.com: Prediction Sites Comparison
- Leviathan News (X/Twitter): Arb spreads 12–20%/Mo claim
