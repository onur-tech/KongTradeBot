# KongTrade — Strategischer Kompass
_Stand: 21.04.2026 — Maßgebliches Dokument für alle Entscheidungen_
_WICHTIG: Diese Datei hat Vorrang bei Strategie-Fragen_

## Kernprinzip

Jeden Markt separat beurteilen:
1. Gibt es einen nachweisbaren Edge mit konkretem Mechanismus?
2. Welche Methode passt zu diesem spezifischen Markt?
3. Erst dann entscheiden ob und wie wir aktiv werden.

## Das wichtigste Prinzip zu Copy Trading

Copy Trading auf kurzen und dünnen Märkten ist strukturell kaputt.
Auf langen, liquiden Märkten mit frühem Einstieg (20-70%) ist der
Latenz-Nachteil von 4-14 Sekunden vernachlässigbar.

Der echte Wert unserer Kombination — eigenes Modell + Wallet-Bestätigung:
- Schlechte Whales von guten trennen
- Manipulationen erkennen (mehrere unabhängige Wallets nötig)
- Eigenes Modell gibt das Signal. Wallet-Bestätigung gibt die Überzeugung.

Schutzfilter:
- MIN_MARKT_VOLUMEN=50.000 — schützt vor Slippage in dünnen Märkten
- Odds-Filter 15-85% — schützt vor Späteinsteiger-Problem
- Multi-Signal-Boost nur bei 2+ Wallets — schützt vor Manipulation

## Markt-Priorisierung

### Phase 1 — Weather Trading (AKTIV)
Edge-Mechanismus: Trader denken kumulativ P(T>=X), Buckets brauchen P(T∈Bucket).
Kalibrierte Städte (sigma verifiziert): Seoul(3.0), Dubai(2.5), Moscow(2.5),
Mumbai, Chicago, Toronto, Seattle, London, Bangkok, Sydney, Beijing (sigma>2.5)
Unkalibrierte Städte (20 von 30): DEFAULT sigma=1.8 — nur Shadow Trading!
Hans323: $92k → $1.11M (12x), WeatherBot.finance: 58-72% WR bestätigt
Infrastruktur: 75% fertig. Fehlt: ICAO-Verifikation, Orderbuch-Tiefe-Check
Status: WEATHER_DRY_RUN=false seit 21.04.2026

### Phase 2 — Cross-Platform Arbitrage (GEPLANT, 2-3 Wochen)
4-7% risikofreier ROI, Polymarket vs Kalshi, kein eigenes Modell nötig
Haken: Kalshi US-only, separate Infrastruktur nötig

### Phase 3 — Soccer/Football (GEPLANT, 4-6 Wochen)
KeyTransporter: $5.7M in 14 Trades, 69% WR
Pinnacle Odds als Referenz, Dixon-Coles Modell

### Phase 4 — Macro + Crypto (2-3 Monate)
Bloomberg-Konsens vs Polymarket, CME Futures Divergenz

### Phase 5 — Esports + Entertainment (langfristig)
Nische, wenig Konkurrenz, xdd07070: $170→$118k

### Nicht-Priorität (akademisch ineffizient)
US Politics: nur noch via Kalshi-Arb oder Whale+Modell kombiniert
Geopolitik: Insider-Risiko zu hoch, niemals allein

## Entscheidungsfilter für neue Ideen
1. Nachweisbarer Edge (Backtest oder externe Bestätigung)?
2. Passt zur aktuellen Phase der Roadmap?
3. Kompatibel mit bestehender Infrastruktur?
4. In 2 Wochen live testbar?
Wenn Frage 1 oder 2 = Nein → nicht jetzt, als IDEE parken.
