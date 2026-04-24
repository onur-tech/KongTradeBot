# Block 2 — GitHub: Competitor-Analyse Polymarket-Bots
*Research-Datum: 2026-04-24 | Quellen: GitHub, DeFiPrime Ecosystem-Guide*

---

## Repo-Tabelle Top-25 (gefiltert auf relevante)

| Repo | Stars | Strategie | Tech | Status | Copy-Eignung |
|------|-------|-----------|------|--------|-------------|
| Polymarket/agents | 3.300 | AI/LLM RAG | Python, LangChain, OpenAI | Aktiv (offiziell) | ⚠️ LLM-basiert, nicht prädiktiv |
| ent0n29/polybot | 476 | Arbitrage + Infra | Java 21, Kafka, ClickHouse | Aktiv | ✅ Beste Infra-Referenz |
| rustyneuron01/Polymarket-Sports-Bot | 105 | ML-Predictions | Python, scikit-learn, ESPN API | Mäßig aktiv | ✅ ML-Edge-Ansatz |
| Drakkar-Software/OctoBot-PM | 65 | Copy + Arbitrage | Python, Docker | Aktiv | ⚠️ Copy noch in Dev |
| GiordanoSouza/pm-copy-bot | 34 | Copy-Trading | Python, Supabase | Niedrig | ❌ Nicht production-ready |
| MrFadiAi/Polymarket-bot | ~20 | Multi-Strategy | Python | Niedrig | ⚠️ Shallow |
| warproxxx/poly-maker | ~50 | Market-Making | Python, GSheets | Mäßig | ❌ Andere Strategie |
| 0xalberto/pm-arbitrage | ~15 | Single/Multi-Arb | Python | Niedrig | ❌ Arbitrage-only |
| PolyBullLabs/5min-15min | ~10 | VWAP/Momentum-Arb | Python | Niedrig | ❌ Short-Term-Arb |
| dev-protocol/pm-copytrading-sport | ~5 | Sports Copy | Python | Inaktiv | ❌ |

**Gesamt Beobachtung:** Kein einziges gefundenes Repository fokussiert auf Weather-Markets. Das ist ein signifikantes Differenzierungsmerkmal für KongTrade.

---

## Strategy-Matrix: Was machen andere anders?

| Dimension | KongTrade (aktuell) | Kompetitoren |
|-----------|--------------------|----|
| Signal-Quelle | Whale-Wallets (On-Chain API) | AI/LLM (agents), ML (rustyneuron), Arb (polybot) |
| Monitoring | HTTP-Polling 10s | Kafka Event-Streaming (polybot), Supabase Realtime |
| Execution | Async Python, CLOB | Java Microservices (polybot), Python CLOB |
| Risk-Management | Eigener RiskManager | Meist keine oder rudimentäre Kontrollen |
| Analytics | State JSON + Logs | ClickHouse + Grafana (polybot), Supabase |
| Weather-Edge | ✅ Geplant (Phase 6) | ❌ Niemand |
| Market-Making | ❌ | poly-maker |
| Arbitrage | ❌ | polybot, OctoBot, PolyBullLabs |

---

## Tech-Insights: Bessere Libraries/Approaches

### 1. Event-Streaming statt Polling (KRITISCH)
**polybot** nutzt **Redpanda Kafka** als Event-Bus: Statt 10s-Polling werden On-Chain-Trades sofort als Events publiziert. Das eliminiert die 4–10s Latenz durch Polling-Offset. 

→ **KongTrade Action-Item:** WebSocket oder Polygon Event-Streaming evaluieren statt HTTP-Polling.

### 2. ClickHouse für Analytics
polybot nutzt ClickHouse als OLAP-Store für Trade-Analytics. Unsere JSON-Flat-Files sind funktional aber nicht queryable.

→ Für Production: SQLite oder DuckDB als leichtgewichtige Alternative.

### 3. AI-Agent-Framework (Polymarket/agents)
3.3k Stars — das offizielle Polymarket AI-Framework. Nutzt LangChain + OpenAI für informierte Entscheidungen via News-RAG. 

→ Relevant für Phase 6+: Weather-Daten als RAG-Input für Claude wäre natürliche Erweiterung.

### 4. ML-Sports-Model (rustyneuron01)
ESPN-API für Live-Spielstand + historische Daten → Logistic Regression + MLP + GradientBoosting → Trade Signal wenn Prediction ≠ Market-Price.

→ **Direkt übertragbar auf Weather:** ECMWF/GEFS-Ensemble-Daten statt ESPN, Polymarket Weather-Markets statt Sports. Architektur ist identisch.

### 5. OctoBot Self-Custody-Modell
Keys verlassen nie das lokale Gerät. Wichtig nach den Security-Vorfällen (Polycule, ClawdBot).

→ KongTrade macht das bereits korrekt (lokale PRIVATE_KEY in .env).

---

## Whales in 3+ Repos erwähnt

Kein einziges der analysierten Open-Source-Repos enthält öffentlich einkodierte Wallet-Adressen. Alle verwenden Environment-Variable-Konfiguration. 

**Community-Konsens-Whales** (aus Ecosystem-Guides, nicht Repos):
- **Theo4** — überall erwähnt als #1 Overall
- **weflyhigh** — regelmäßig top-5
- **swisstony** — top-10, aber Arb-Profil

→ Keine Repos liefern neue Wallet-Addressen, die wir noch nicht kennen.

---

## Öffentlich verfügbare Backtest-Ergebnisse

| Repo | Backtest? | Ergebnis |
|------|-----------|---------|
| Polymarket/agents | ❌ Nein | — |
| ent0n29/polybot | ❌ Paper-Mode only | — |
| rustyneuron01/sports | ⚠️ Impliziert (training accuracy) | Nicht öffentlich |
| OctoBot | ⚠️ Paper-Trading-Mode | Keine Zahlen |
| Alle anderen | ❌ | — |

**Wichtige Erkenntnis:** Kein öffentliches Repo zeigt verifizierte Live-Backtest-Renditen. Das macht externe Validierung unserer Strategie schwierig — aber auch: kein Wettbewerber hat einen Beweis, dass sein Ansatz profitabel ist.

---

## Ecosystem-Überblick (Kommerzielle Tools, DeFiPrime-Guide)

### Whale-Tracking (Relevant für Signal-Sourcing)
| Tool | Beschreibung | Relevanz |
|------|-------------|----------|
| Polywhaler | #1 Whale-Tracker, $10k+ Trades, Insider-Alerts | ✅ Monitoring-Alternative |
| Polyburg | 100+ profitable Wallets überwacht | ✅ Wallet-Discovery |
| HashDive | "Smart Scores" -100 bis +100 | ✅ Wallet-Qualifizierung |
| PolyIntel | Real-Time Telegram, Insider-Detection | ✅ Alert-Supplement |
| MobyScreener | Live Feed Top-Trader Buys/Sells | ✅ Monitoring |

### Cross-Venue Arbitrage (Referenz)
| Tool | Funktion |
|------|---------|
| ArbBets | Auto-Arb Polymarket ↔ Kalshi |
| EventArb | Free Kalshi/Polymarket Cross-Calculator |
| Matchr | 1.500+ Märkte Aggregator |

### Analytics
| Tool | Besonderheit |
|------|-------------|
| Betmoar | $110M Volumen, Marktführer Terminal |
| HashDive | Smart Scores für Wallet-Qualifizierung |
| Parsec | Real-Time Flow + Multi-Outcome Dashboards |
| Polymarket Analytics | Goldsky-Infrastructure, 5-Min-Update |

---

## Bewertung: KongTrade vs. Wettbewerber

**Stärken KongTrade:**
- ✅ Vollständiger 4-Step-Pipeline (WalletMonitor → Strategy → Risk → Execution)
- ✅ Echter Risk-Manager mit Kill-Switch, Daily-Loss-Limit
- ✅ State-Persistence mit Duplikat-Prevention
- ✅ Weather-Edge in Pipeline (niemand sonst hat das)
- ✅ Telegram-Reporting + Morning-Report

**Schwächen vs. Wettbewerber:**
- ❌ 10s-Polling statt Event-Streaming (polybot ist hier 4–10s schneller)
- ❌ JSON-Flat-Files statt queryable Storage (ClickHouse/SQLite)
- ❌ Keine ML-Prediction-Komponente (nur Whale-Copy, kein eigenes Modell)
- ❌ Keine Cross-Venue-Arbitrage

**Differenzierungsmerkmal:**
Weather-Edge mit Ensemble-Forecasting ist in keinem der 25 analysierten Repos implementiert. Das ist ein echter First-Mover-Vorteil.

---

## Quellen
- github.com/Polymarket/agents (3.3k ⭐)
- github.com/ent0n29/polybot (476 ⭐)
- github.com/rustyneuron01/Polymarket-Sports-Trading-Bot (105 ⭐)
- github.com/GiordanoSouza/polymarket-copy-trading-bot (34 ⭐)
- github.com/Drakkar-Software/OctoBot-Prediction-Market (65 ⭐)
- defiprime.com/definitive-guide-to-the-polymarket-ecosystem
- polycopybot.app/blog/polymarket-arbitrage-bot-github
