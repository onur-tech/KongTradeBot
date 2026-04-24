# Block 4 — Weather-Forecast-Skill: Ensemble-Modelle & Polymarket-Stationen
*Research-Datum: 2026-04-24 | Quellen: ECMWF, Open-Meteo, Celsi Markets, Polymarket, CNN/Engadget/Bloomberg*

---

## ⚠️ KRITISCHER BREAKING NEWS (23. April 2026)

### Paris Weather-Market-Manipulation — Haartrockner-Betrug

**Was passierte:**
- 6. April + 15. April 2026: Temperatur-Sensor am CDG Airport Paris wurde physisch manipuliert
- Methode: Batterie-Haartrockner am öffentlich zugänglichen Sensor → +4–5°C künstlicher Spike
- Gewinn: ~$34.000 auf ursprünglich <1% Wahrscheinlichkeit
- Reaktion Polymarket: Switched Resolution-Source von CDG zu Le Bourget Airport (19. April)
- Rechtlich: Météo-France hat Strafanzeige erstattet wegen "Manipulation automatisierter Datensysteme"
- Stand: Französische Polizei ermittelt (CNN, Bloomberg, Engadget, Benzinga, 23. April 2026)

**Implikation für KongTrade:**
> Weather-Markets haben ein grundlegendes Resolution-Integrity-Problem. Physische Sensoren an öffentlich zugänglichen Stellen sind manipulierbar. US-ASOS-Stationen (airports) haben ähnliche Zugänglichkeitsprobleme. Dieses Risiko muss in unserem Weather-Plugin berücksichtigt werden.

**Mögliche Schutzmaßnahmen:**
1. Nur Märkte handeln wo multiple Stationen kreuzvalidiert werden
2. Stationen mit echter physischer Sicherheit bevorzugen (Flughafen-Innenbereiche)
3. Anomalie-Detection: wenn Marktpreis unmittelbar vor Resolution stark springt → Exit-Signal

---

## Aktive Polymarket Weather-Markets (April 2026)

### Verfügbare Städte
**USA:** NYC (KJFK?), Chicago, Houston, Miami, Atlanta, Los Angeles, Dallas, Denver, Austin  
**Europa:** London, Paris (Le Bourget, nach CDG-Wechsel), Munich, Milan, Madrid, Helsinki, Amsterdam, Istanbul, Moscow  
**Asien:** Seoul, Tokyo, Singapore, Hong Kong, Shanghai, Beijing, Chengdu, Wuhan, Guangzhou, Taipei, Shenzhen, Chongqing, Busan, Manila, Kuala Lumpur, Jakarta  
**Andere:** Toronto, São Paulo, Lagos, Jeddah, Cape Town, Tel Aviv, Mexico City, Ankara, Wellington  

**Total: 40+ Städte**

### Markt-Volumina (Richtwerte April 2026)
| Markt | Volumen | Typ |
|-------|---------|-----|
| Seoul High-Temp | ~$141k | Daily Temperature |
| Hurricane/Tornado Markets | $16k–$336k | Seasonal |
| Earthquake 7.0+ | $1M–$2M | Event |
| NYC/Chicago/Miami Daily Temp | $10k–$80k est. | Daily |
| Monthly Precipitation (NYC, Seattle, etc.) | $14k–$59k | Monthly |

**Fazit Liquidität:** Daily Temperature-Markets sind liquid genug für unsere Positionsgrößen (≤$500 Ziel-Trade). Bei >$5k müsste man Slippage prüfen.

---

## ECMWF vs. GEFS vs. GFS: Welches Modell für <72h?

### Rangliste für Kurzfrist-Temperatur (24–72h)

| Modell | Organisation | Öffentlich? | Beste Stärke | Schwäche |
|--------|-------------|------------|-------------|---------|
| **ECMWF IFS** | EU, Reading | ✅ seit Okt 2025 via Open-Meteo | Bester Ensemble 0–7 Tage | Globale Gitter, lokal weniger präzise |
| **ECMWF AIFS** | EU (AI-basiert) | ⚠️ Teilweise | 15%+ besseres RMSE bei 1,5 Tagen | Neu, weniger verifiziert |
| **NOAA GEFS** | USA | ✅ Free | Gut für USA-Stationen | Schlechter als ECMWF für Temp |
| **NOAA GFS** | USA | ✅ Free | Deterministisch, schnell | Kein Ensemble, weniger akkurat |
| **FuXi-ENS** | China AI | ❌ | Beste Gesamtskills | Nicht öffentlich |
| **Open-Meteo** | OSS | ✅ Free | Aggregiert alle Modelle | Wrapper, kein eigenes Modell |

### Quantitative Genauigkeit (ECMWF 2m Temperatur)

| Lead-Time | RMSE (°C) | MAE vs. GFS | Skill vs. Klimatologie |
|-----------|-----------|-------------|----------------------|
| 24h | ~1.0–1.5°C | ECMWF -0.3–0.6°C besser | >90% positiver Skill |
| 48h | ~1.5–2.0°C | ECMWF -0.5–1.0°F besser | ~80–85% positiver Skill |
| 72h | ~2.0–3.0°C | ECMWF deutlich besser | ~70% positiver Skill |
| 7 Tage | ~4–5°C | Beide ähnlich degradiert | ~40–50% |

> ⚠️ Hinweis: Spezifische RMSE-Zahlen von ECMWF nicht direkt aus Verification-Report extrahierbar (dynamische Charts). Werte basieren auf publizierten Ranges aus Nature Scientific Reports, Springer Meteorology & Atmospheric Physics, und Celsi-Vergleich.

**Für Polymarket-Context:** ECMWF schlägt GFS um ~0.5–1.0°C MAE auf 24–48h. Da viele Polymarket-Temp-Märkte 1–2°C Preissprünge sind, ist ECMWF-Accuracy ein realer Edge.

---

## Bias-Risks: Wo ist Polymarket-Mispricing am größten?

### Strukturelle Mispricing-Typen

**1. Extreme-Event-Overpricing (Longshot Bias)**
- Temperaturspitzen >95th Percentil werden von Markt systematisch overpriced (>Forecast)
- Gleicher Longshot-Bias wie in Sportwetten: Seltene Events kosten zu viel
- **Edge:** ECMWF-Ensemble-Spread auf Extremes ist präziser als Marktimplied

**2. Narrative-Driven Mispricing**
- Hitzewelle-Coverage → Markt überkauft "higher than normal" Temp-Tokens
- Cold-Snap-News → "lower than normal" überbewertet
- **Edge:** Ensemble-Kalibrierung schlägt Narrative

**3. Resolution-Station-Unklarheit**
- Trader wissen oft nicht welche Station exakt verwendet wird (CDG vs. Le Bourget war nicht immer klar)
- Forecast für falsche Station → systematisches Mispricing
- **Edge:** Korrekte Station identifizieren + korrekten Forecast nutzen

**4. Model-Consensus-Gap**
- Wenn ECMWF und GFS stark abweichen → Markt mittelt zwischen beiden
- ECMWF is meist besser → wer ECMWF-Only nutzt, hat systematischen Edge
- **Größte Abweichungen:** 48–120h Lead-Time, Konvektiv-Ereignisse

**5. Timing-Mispricing (Daily High-Temp)**
- Markt-Resolution = Daily Maximum Temperature
- Forecast für Daily Max muss korrekt sein (nicht Durchschnitt oder aktuell!)
- Viele Trader verwenden Tages-Durchschnitt → systematischer Fehler
- **Edge:** ECMWF Ensemble Max-Temperature vs. Market implied Daily High

---

## Resolution-Stationen: US-Airports (ASOS/METAR)

Polymarket verwendet Flughafen-Wetterstationen (ASOS = Automated Surface Observing System).

| Stadt | Station Code | Bekannte Märkte |
|-------|-------------|-----------------|
| New York City | KJFK (Kennedy) | ✅ Aktiv |
| Chicago | KORD (O'Hare) | ✅ Aktiv |
| Boston | KBOS | ✅ Aktiv |
| Los Angeles | KLAX | ✅ Aktiv |
| Miami | KMIA | ✅ Aktiv |
| Atlanta | KATL | ✅ Aktiv |
| Dallas | KDFW | ✅ Aktiv |
| Houston | KIAH | ✅ Aktiv |
| Denver | KDEN | ✅ Aktiv |
| Paris | Le Bourget (LFPB) | ✅ Seit 19. April 2026 (vorher CDG/LFPG) |

**ASOS-Daten verfügbar:** aviationweather.gov/data/metar (öffentlich, alle US-Stationen)  
**Update-Frequenz:** Jede Stunde, manchmal häufiger bei Sonderbeobachtungen

---

## Ensemble-Modelle: Verfügbarkeit in Public APIs

| Quelle | ECMWF IFS | GEFS | Auflösung | Latenz | Kosten |
|--------|-----------|------|-----------|--------|--------|
| **Open-Meteo** | ✅ seit Okt 2025 | ✅ | 9km nativ | ~2–4h nach Init | Kostenlos (non-commercial) |
| **open-meteo.com API** | ✅ | ✅ | 9km | Real-time | Free bis 10k/Tag |
| **ECMWF Charts** | ✅ | ❌ | Charts only | — | Free |
| **NOAA NOMADS** | ❌ | ✅ | 0.25° | ~1–2h | Free |
| **Meteomatics** | ✅ | ✅ | 1km | Real-time | Kommerziell |
| **DTN/Spire** | ✅ | ✅ | 1km | Real-time | Sehr teuer |
| **Windy API** | ✅ | ✅ | — | Real-time | $35/Mo |

**Empfehlung für KongTrade Phase 6:** Open-Meteo ist die beste Free-Option — ECMWF auf 9km nativ, beide Ensemble-Systeme, Python-SDK verfügbar.

---

## Mispricing-Ranking: Welche Stationen haben den stärksten Edge?

Basierend auf:
- Forecast-Unsicherheit (Edge = wo Forecast besser als Market)
- Liquidität (genug Volume für unsere Trades)
- Manipulations-Risiko (je öffentlicher die Station, desto höher)
- Seasonal-Volatilität (mehr Unsicherheit = mehr Mispricing)

| Rang | Stadt/Station | Edge-Basis | Liquidität | Manip-Risiko | Empfehlung |
|------|---------------|------------|------------|-------------|------------|
| 1 | Chicago (KORD) | High seasonal vol, Ensemble dominiert | Gut | Niedrig (Airfield) | ✅ Priorität |
| 2 | NYC (KJFK) | High activity, Ensemble-Kalibrierung klar | Gut | Niedrig | ✅ Priorität |
| 3 | Boston (KBOS) | Winter-Surprises häufig | Mittel | Niedrig | ✅ |
| 4 | Denver (KDEN) | High Elevation = Forecast schwieriger | Mittel | Niedrig | ✅ |
| 5 | Dallas (KDFW) | Extremes möglich, hohe Variabilität | Mittel | Niedrig | ⚠️ |
| 6 | Miami (KMIA) | Geringes saisonales Delta, flache Curve | Gut | Niedrig | ⚠️ |
| 7 | Seoul, Tokyo | Gute Liquidity, gute Forecasts | Hoch | Niedrig | ⚠️ Nicht-US Risiko |
| 8 | Paris (Le Bourget) | Manipulation-Risiko durch aktuelle Events | Mittel | ⚠️ HOCH | ❌ Temporär vermeiden |
| 9 | Andere EU-Stationen | Unbekannte Resolution-Details | Variabel | Unbekannt | ❌ Erst validieren |

---

## Zusammenfassung: Weather-Edge Realitätscheck

### Was wir haben (Edge-Basis):
- ✅ ECMWF-Ensemble via Open-Meteo ist kostenlos und besser als Markt-Konsens
- ✅ RMSE ~1–2°C auf 24–48h: realer Informations-Vorteil vs. Marktpreise
- ✅ Kein anderer Polymarket-Bot nutzt Ensemble-Forecasting (laut GitHub-Analyse)
- ✅ Longshot-Bias bei Extremen ist dokumentiert und exploitable

### Was wir beachten müssen (Risiken):
- ⚠️ Paris-Skandal: Resolution-Integrität ist gefährdet — Stationen müssen auf Manipulation-Risiko geprüft werden
- ⚠️ Forecast-Bias: Systematische Fehler in bestimmten Wetterlagen (Inversionswetterlagen, konvektive Events)
- ⚠️ Resolution-Station-Klarheit: Immer dokumentieren, welche Station exakt Polymarket verwendet
- ⚠️ Tages-Maximum statt Durchschnitt: Korrekte Ziel-Variable im Forecast sicherstellen

---

## Quellen
- ECMWF Quality of Forecasts: ecmwf.int
- Open-Meteo: open-meteo.com (Free ECMWF seit Okt 2025)
- Celsi Markets: GFS vs. ECMWF Accuracy Blog
- Engadget/Bloomberg/CNN: Paris Weather Manipulation (April 23, 2026)
- Polymarket Weather Markets: polymarket.com/weather
- Nature Scientific Reports: ECMWF short-term prediction accuracy improvement by deep learning
- aviationweather.gov: METAR data (alle US-ASOS-Stationen)
