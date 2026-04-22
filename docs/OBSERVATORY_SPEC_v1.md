# Observatory Spec v1.0
**Datum:** 2026-04-22  
**Status:** Design-Phase — Implementation geplant nach Foundation Phase 7 (~Aug 2026)

---

## Überblick

Das Observatory ist ein passives Market-Intelligence-System, das parallel zum Polymarket-Copy-Trading-Bot läuft. Es beobachtet externe Marktphänomene (Funding-Rates, Stablecoin-Pegs, Cross-Platform-Preisdivergenzen, Liquidations-Kaskaden), generiert Telegram-Alerts bei Threshold-Überschreitungen, und informiert ggf. den Circuit-Breaker des Hauptbots.

**4 Observer geplant | 1 integriert | 2 deferred**

---

## Observer #1 — Funding-Rate-Arbitrage [BUILD]

**Kategorie:** Aktive Strategie (read-only Phase 7)  
**Status:** Spec fertig, Implementation ~Sprint 1 Phase 7

### Zusammenfassung
Beobachtung von Funding-Rate-Spreads zwischen Binance, Bybit und OKX auf Perpetual Futures. Bei genügend großem Spread kann delta-neutral über beide Exchanges die Funding-Differenz eingefangen werden. Retail-realistisch 10–30% APR. Integriert den Basis-Trade-View (Perp–Spot-Differenz) als sekundären Datenpunkt (`basis_pct` als zusätzliches Feld).

### Thresholds
| Level   | Bedingung                                      | Aktion              |
|---------|------------------------------------------------|---------------------|
| Observe | Cross-Exchange-Spread > 0.02%/8h (~22% APR)    | loggen              |
| Notable | Spread > 0.05%/8h (~55% APR) für 2+ Perioden   | Telegram-Info       |
| Alert   | Spread > 0.1%/8h (~110% APR)                   | Telegram-Critical   |

### Technische Details
- **Datenquellen:** Binance + Bybit + OKX Public Perp APIs (kein API-Key erforderlich)
- **Symbols:** BTC, ETH, SOL, DOGE, PEPE
- **Polling:** alle 15 Minuten
- **Sekundär:** `basis_pct` (Perp − Spot) als zusätzliches Feld im Funding-Dashboard

---

## Observer #2 — Stablecoin-Depeg-Monitor [BUILD]

**Kategorie:** Risk-Intelligence  
**Status:** Spec fertig, Implementation ~Sprint 1 Phase 7

### Zusammenfassung
Beobachtung aller großen Stablecoins auf Peg-Abweichungen. Bei fiat-backed Stables (USDT/USDC/DAI) häufig Recovery innerhalb 72h → Buy-the-dip-Opportunity. Bei algo-Stables (USDe/USDX) oft terminal (vgl. USDX collapse Nov 2025). Observer dokumentiert beide Kategorien separat, um empirische Entscheidungsgrundlage zu schaffen.

### Thresholds
| Level   | Bedingung                                         | Aktion            |
|---------|---------------------------------------------------|-------------------|
| Normal  | Abweichung < 30 bps                               | nur loggen        |
| Minor   | 30–100 bps für 10+ min                            | loggen            |
| Depeg   | > 100 bps für 15+ min                             | Telegram-Info     |
| Severe  | > 300 bps für 5+ min ODER > 500 bps sofort        | Telegram-Critical |

### Technische Details
- **Datenquellen:** CoinGecko + Binance (Cross-Check, 2 unabhängige Quellen)
- **Symbols:** USDT, USDC, DAI, FRAX, TUSD, USDD, USDe, USDX
- **Polling:** alle 2 Minuten

---

## Observer #3 — Cross-Platform-Arbitrage [BUILD]

**Kategorie:** Aktive Strategie (read-only Phase 7)  
**Status:** Spec fertig, Implementation ~Sprint 2 Phase 7

### Zusammenfassung
Identische Events auf Polymarket und Kalshi haben häufig Preisdivergenzen. Bei Spread > 2.5% nach Fees risiko-reduziertes Arbitrage möglich. Retail-Sweet-Spot: Events mit 7+ Tagen Laufzeit (nicht die 2–7-Sek-Flash-Arbs). LLM-basiertes Event-Matching mit manueller Bestätigung für unsichere Matches.

### Thresholds
| Level   | Bedingung                                                    | Aktion           |
|---------|--------------------------------------------------------------|------------------|
| Observe | Spread > 1pp, alle Events                                    | loggen           |
| Notable | Net-Spread > 2% UND Duration > 7 Tage                       | Telegram-Info    |
| Alert   | Net-Spread > 5% UND Duration > 7d UND Vol > $100k           | Telegram-Critical|

### Technische Details
- **Datenquellen:** Polymarket Gamma API + Kalshi v2 API
- **Kategorien:** Politics, Macro, Sports, Crypto, Culture
- **Polling:** 15 Min Standard, 5 Min bei Hi-Vol-Events

---

## Observer #4 — Liquidation-Cascade-Indicator [BUILD]

**Kategorie:** Circuit-Breaker-Signal (direkte Integration)  
**Status:** Spec fertig, Implementation ~Sprint 3 Phase 7

### Zusammenfassung
Nicht als Trading-Strategie, sondern als Market-Regime-Signal das den Copy-Trading-Circuit-Breaker informiert. WebSocket-Streams von Binance und Bybit liefern Echtzeit-Liquidationen. Rolling-1h-Summen klassifizieren Marktstress in 4 Regime, die Position-Sizing im Copy-Trading dynamisch anpassen.

### Thresholds (Rolling 1h)
| Regime   | Bedingung             | Size-Faktor | Aktion                              |
|----------|-----------------------|-------------|-------------------------------------|
| NORMAL   | < $10M/h              | × 1.0       | —                                   |
| ELEVATED | $10–50M/h             | × 0.7       | —                                   |
| STRESS   | $50–200M/h            | × 0.5       | Telegram-Info                       |
| CASCADE  | > $200M/15min         | × 0.0       | Trading-Pause 60 Min + Critical     |

### Technische Details
- **Datenquellen:** Binance + Bybit WebSocket (Live-Stream, kein API-Key)
- **Symbols:** BTC, ETH, SOL, DOGE, PEPE
- **Circuit-Breaker-Integration:** JA (direkte Size-Anpassung via `circuit_breaker.py`)

---

## Observer #5 — Basis-Trade [INTEGRATED]

**Kategorie:** In Observer #1 integriert  
**Status:** Kein separater Build

### Zusammenfassung
Mathematisch äquivalent zu Funding-Rate-Arbitrage. Basis (Perp − Spot) konvergiert über Funding-Zahlungen zur Expiry. Separate Observation redundant. In Observer #1 als zusätzliches Feld `basis_pct` integriert und im Funding-Dashboard als sekundärer View gezeigt.

- **Thresholds:** siehe Observer #1 (Funding-Rate-Arbitrage)
- **Datenquellen:** in Observer #1 enthalten

---

## Observer #6 — Yield / Governance [DEFERRED]

**Kategorie:** Externe Tools überlegen  
**Status:** Dokumentiert, kein in-house Build geplant

### Zusammenfassung
Observer-Pattern ungeeignet für semi-stabile Asset-Klasse mit qualitativen Risiken (Smart-Contract-Exploits, Impermanent Loss, Protokoll-Rugs). Externe Tools sind hier überlegen: DefiLlama Yields, APY.vision, De.Fi.

- **Thresholds:** n/a
- **Datenquellen:** externe Tools (DefiLlama, APY.vision, De.Fi)
- **Re-Evaluation:** nach Polymarket-Validation (200+ Trades, PSR > 0.95) UND Bankroll > $10k

---

## Observer #7 — Airdrop-Farming [DEFERRED]

**Kategorie:** Externe Tools überlegen  
**Status:** Dokumentiert, kein in-house Build geplant

### Zusammenfassung
Erfordert aktive on-chain Teilnahme (Bridges, Swaps, Governance-Votes), nicht passive Observation. Externe Tracker abdecken dies besser: Drop.wtf, Earni.fi, DefiLlama Airdrops. Bei späterer Aktivierung dedicated farming-Wallet empfohlen (niemals mit Trading-Kapital mischen).

- **Thresholds:** n/a
- **Datenquellen:** externe Tools (Drop.wtf, Earni.fi, DefiLlama Airdrops)
- **Re-Evaluation:** nach Bankroll > $5k UND mental-bandwidth frei

---

## Implementation-Roadmap

| Sprint | Observer                          | Phase       |
|--------|-----------------------------------|-------------|
| 7.1    | Funding-Rate-Arbitrage (#1)       | ~Aug 2026   |
| 7.1    | Stablecoin-Depeg-Monitor (#2)     | ~Aug 2026   |
| 7.2    | Cross-Platform-Arbitrage (#3)     | ~Sep 2026   |
| 7.3    | Liquidation-Cascade-Indicator (#4)| ~Okt 2026   |
| —      | Basis-Trade (#5)                  | in #1 enthalten |
| —      | Yield/Governance (#6)             | deferred    |
| —      | Airdrop-Farming (#7)              | deferred    |

**Erste Re-Evaluation:** 90 Tage nach Go-Live Phase 7
