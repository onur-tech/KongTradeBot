# KongTradeBot — Handelslogik & Strategie
_Stand: 2026-04-20 | Vollständig überarbeitet_

---

## 1. Philosophie: Lern-Modus (ab 2026-04-20)

**Ziel ist nicht maximaler Portfolio-Schutz sondern maximale Datenpunkte und Feature-Tests.**
Das Portfolio ($1.000) ist Spielkapital zum Lernen.

Prioritäten in dieser Reihenfolge:
1. Jedes neue Feature testen und validieren
2. Daten sammeln: Welche Wallets liefern echten Edge?
3. Bot-Robustheit sicherstellen (Reconnect, State-Recovery, Fallbacks)
4. Profitabilität — ergibt sich aus 1–3

**Warum dieser Ansatz:**
- Mit $1.000 ist kein signifikanter Return möglich — Lernkosten sind akzeptabel
- Feature ohne Live-Test ist wertlos — jeder Trade ist ein Datenpunkt
- Konservative Parameter + wenige Wallets → wenige Datenpunkte → langsames Lernen
- Nach der Lernphase: Parameter anhand echter Daten optimieren

---

## 2. Position-Sizing

Formel:
```
Unsere Größe = Whale-Größe
             × COPY_SIZE_MULTIPLIER (global)
             × Wallet-Multiplier (per-Wallet)
             × Multi-Signal-Boost (1.0–2.0x)
```
Gecapt bei MAX_TRADE_SIZE_USD.

**Aktuelle Config (Lern-Modus, ab 20.04.2026):**

| Parameter | Neu | Alt | Begründung |
|-----------|-----|-----|-----------|
| `COPY_SIZE_MULTIPLIER` | **0.10** | 0.05 | Mehr Exposure für Datenpunkte |
| `MAX_TRADE_SIZE_USD` | 30 | 30 | Unverändert |
| `MAX_POSITIONS_TOTAL` | **30** | 15 | Mehr gleichzeitige Positionen |
| `MIN_MARKT_VOLUMEN_USD` | **20000** | 50000 | Mehr Märkte qualifiziert |
| `MAX_DAILY_LOSS_USD` | **200** | 150 | Höhere Toleranz für Test-Kosten |
| `MIN_TRADE_SIZE_USD` | **0.50** | — | Neu: Verhindern von Dust-Trades |
| `CATEGORY_BLACKLIST` | col1-, por-, ecu-, arg-b- | — | Unverändert |

---

## 3. Multi-Signal-Boost (Schwarmintelligenz)

Wenn mehrere Whales gleichzeitig auf denselben Markt setzen:
- 1 Wallet → 1.0x
- 2 Wallets → 1.5x
- 3+ Wallets → 2.0x

**Herdentrieb-Schutz:** Wenn >50% aller Wallets dieselbe Seite wählen → kein Boost.

**Signal-Buffer:** 60 Sekunden. Signale werden gesammelt, dann in einem Rutsch verarbeitet.

**Basket-Strategie (T-M21, geplant):**
Wenn Wallet ≥3 Signale in 60 Minuten platziert → Buffer bypassen, Basket-Copy bis
BASKET_MAX_POSITIONS=3 mit BASKET_TOTAL_CAP_USD=$15.

---

## 4. Risk Management

**Hart-Limits:**
| Limit | Wert |
|-------|------|
| MAX_TRADE_SIZE_USD | $30 |
| MAX_DAILY_LOSS_USD | $200 (Kill-Switch) |
| MAX_PORTFOLIO_PCT | 50% |
| MAX_POSITIONS_TOTAL | 30 |
| DAILY_CAP_USD | $100 (max Trades pro Tag) |

**Odds-Filter:** nur Trades zwischen 8% und 92% Wahrscheinlichkeit.
**Freshness-Filter:** Signale älter als 5 Min werden ignoriert.
**Market-Budget-Limit:** max $30 pro einzelnem Markt.
**Volumen-Filter:** Märkte unter $20K USD Volumen werden übersprungen.
**Crypto-Daily-Single-Signal-Buffer:** Im Crypto-Sektor wird ein Signal erst bei zweitem
Bestätiger oder nach 24h verarbeitet (Einzel-Wallet-Bounce-Schutz).

---

## 5. Stop-Loss (T-M04e — deployed)

Polymarket-Preise sind binär (0 oder 1 bei Auflösung). Klassischer Stop-Loss (z.B. -20%)
würde schlechter rausdrücken als Abwarten. Stattdessen zwei dynamische Trigger:

**Trigger B — Zeit-abhängig (deployed):**
- Wenn Position nach 24h noch ≤15¢ → automatisches Close
- Begründung: Markt hat die Position abgelehnt; Kapital freigeben

**Trigger C — Entry-Preis-abhängig (deployed):**
- Wenn Entry-Preis ≥40¢ UND aktueller Preis ≤30% des Entry-Preises → Close
- Beispiel: Einstieg bei 50¢ → Stop bei 15¢

**Nicht angewendet auf:**
- Positionen mit Entry <15¢ (Longshots — Trigger B Konflikt)
- Positionen in letzten 6h vor Marktende (Auflösung abwarten)

---

## 6. Exit-Strategie (T-M03 Whale-Exit-Copy — deployed)

**Prinzip:** Einstieg UND Ausstieg werden kopiert.

Wenn eine getrackte Whale-Wallet eine Position verkauft:
1. Bot erkennt SELL-Signal von der Whale
2. Bot prüft ob wir eine offene Position im selben Markt haben
3. Wenn ja: Bot verkauft unsere Position proportional

**3 Szenarien:**
| Szenario | Whale-Aktion | Bot-Reaktion |
|----------|-------------|-------------|
| Gradual Exit | Whale verkauft 50% | Wir verkaufen 50% |
| Full Exit | Whale verkauft alles | Wir verkaufen alles |
| Flip | Whale dreht Position um | Wir schließen und drehen |

**Wichtig:** Der Whale-Exit-Zeitpunkt ist oft das wertvollste Signal.
DrPufferfish und Countryside sind primär als Exit-Signal-Quellen wertvoll
(ihre Entries sind durch WR-Diskrepanz zweifelhaft, ihre Exits nicht).

---

## 7. Wallet-Kategorien und Tier-System

### Tier A — Etabliert (1.0x–1.5x)
Wallets mit Live-bestätigtem Edge, mehrere Monate Daten.

| Wallet | Kategorie | Stärke |
|--------|-----------|--------|
| majorexploiter | Sports/UCL | 76% WR, Millionen-Profit |
| reachingthesky | Politik/Mixed | Stabil, cross-sector |
| kcnyekchno | Allgemein | 81% WR extern |
| denizz | Politik/Soccer | polymonit April #1 |

### Tier B — Experimental (0.3x–0.5x)
Neu aufgenommene oder noch nicht live-bestätigte Wallets.

| Wallet | Kategorie | Aufnahme-Basis |
|--------|-----------|---------------|
| wokerjoesleeper | Makro/Fed/Iran | $900K, +227% ROI |
| ScottyNooo | Trump/Geo | $1.3M, Merlin 76/100 |
| Erasmus | Iran/ME | polymonit April #4 |
| TheSpiritofUkraine | Geopolitik | polymonit April #3 |

### Sektor-Balance (Ziel)

| Sektor | Wallets | Risiko |
|--------|---------|--------|
| Geopolitik/Politik | 4–6 | ⚠️ HÖCHSTES Risiko — Konzentration vermeiden |
| Sports | 2–3 | Mittel — Saison-abhängig |
| Macro/Economy | 1–2 | Niedrig — längere Haltedauer |
| Crypto | 1 | Hoch — Single-Signal-Buffer aktiv |

**Geopolitik-Konzentrations-Warnung:** >4 Geopolitik-Wallets = korreliertes Risiko.
Ein Breaking-News-Event kann alle gleichzeitig treffen (Iran-Szenario, April 2026).

---

## 8. Wallet-Decay-Score (v2.0 — Profit-First)

**Primär-Filter (einziger K.O.-Filter):**
- Positives All-Time PnL (>$10K) ODER ROI auf Deposits > 10%

**Sekundär-Analyse:**
- Strategie-Typ (Direktional / Akkumulator / Longshot / Scalper)
- WR ist KEIN Gate, aber Indikator für Strategie-Typ
- 0xinsider Grade + Edge → ergänzend, nicht allein entscheidend

**Lebend-Monitoring:**
- >52% WR nach 30 Tagen: Upgrade möglich
- 45–52% WR: beobachten
- <45% WR: Review, Multiplier-Reduktion, ggf. Entfernung

**Kadenz:** T-D109 monatliche Review. Keine Ad-hoc-Entscheidungen ohne 30-Tage-Daten.

---

## 9. Safety-Systeme

- systemd Auto-Restart (Server-CC)
- Watchdog 60s + Telegram-Alert bei Heartbeat-Stale
- PID-Lock (3-Ebenen: atexit + SIGTERM + ExecStartPre)
- Persistent State: `bot_state.json` → Stale-Position-Filter
- Claim-Loop alle 30 Min (TODO: auf 5 Min reduzieren, T-M11)
- Log-Rotation: tägliche Logfiles, automatische Archivierung
- Dual-Source-Invariante (KB P083): Multiplier-Änderung immer in BEIDEN:
  `strategies/copy_trading.py WALLET_MULTIPLIERS` + `.env WALLET_WEIGHTS`

---

## 10. Bekannte Limitierungen (bewusste Entscheidungen)

| Feature | Status | Begründung |
|---------|--------|-----------|
| Slippage-Modell | ❌ nicht implementiert | Polymarket Thin Markets — Phase 2 |
| Korrelations-Check | ❌ nicht implementiert | Benötigt Markt-Graph — Phase 3 |
| Kelly-Formel | ❌ nicht implementiert | Benötigt echte Edge-Daten — nach Lernphase |
| Dynamic-Edge-Adjustment | ❌ nicht implementiert | Phase 3 |
| Auto-Claim | ❌ wartend (T-M11) | Benötigt POL für Gas |

---

## 11. Wallet-Kategorien — Detail

### Insider-Wallets (höchste Priorität, T-M-NEW)
Wallets die Positionen auf Geopolitik-Events bei <15¢ platzieren VOR Breaking News.
Beispiel: Iran-Ceasefire April 7, 2026 — $663K auf 4 Wallets bei 2.9–10.3¢.

**Erkennung:** Anomalie-Score ≥5 (T-M-NEW, geplant)
- Fresh wallet (<30 Tage): +2
- <10 Trades historisch: +2
- One-Shot-Pattern: +3
- Cluster 3+ Wallets: +4
- Bet >$200K: +1
- Entry <5¢: +2

### Direktionale Trader (Standard Copy)
Stabile, langfristige Positionen basierend auf Recherche oder Expertise.
Beispiele: denizz, reachingthesky, Erasmus, TheSpiritofUkraine, wokerjoesleeper, ScottyNooo.

### Akkumulatoren / Basket-Trader (T-M21)
Platzieren viele Trades schnell in kurzer Zeit (Burst-Muster).
Beispiele: SeriouslySirius (35/Tag), beachboy4 (40 Wins/Tag burst).
→ Basket-Strategie nötig: Multi-Signal-Buffer-Bypass.

### HFT-Bots (REJECT — HF-10)
>50 Trades/Tag, Sports-Fokus, algorithmisch.
Beispiele: RN1 (107/Tag), April#1 Sports (HFT-Muster).
Copy-Trading technisch unmöglich (zu kleiner Avg-Trade).

---

## 12. Anomalie-Detektor (T-M-NEW — geplant)

Scannt ALLE Polymarket-Trades alle 5 Minuten via `data-api.polymarket.com/activity`.

**Trigger:**
- Single Wallet: >$100K auf Event bei <10¢
- Cluster: 3+ Wallets, >$200K kombiniert auf Event bei <15¢

**Budget:** $2/Signal, $20/Tag Limit.

**Kalibrierung:** Iran-Ceasefire April 7, 2026 ($663K auf 4 neue Wallets bei 2.9–10.3¢).

**Latenz-Ziel:** <5 Sekunden nach Insider-Kauf (mit T-WS).

Prompt-Dokument: `prompts/t_m_new_anomaly_detector.md`

---

## 13. WebSocket WalletMonitor (T-WS — geplant)

**Problem:** Aktuell 10s Poll-Intervall → 13–15s Signal-Latenz.
Bei Breaking-News-Events: Insider kaufen bei 3¢, Preis springt in <30s auf 50¢.
Mit 13–15s Latenz: wir kaufen bei 30–50¢ statt 3–10¢.

**Lösung:** WebSocket `wss://ws-subscriptions-clob.polymarket.com/ws/market`
- Kein Auth erforderlich (Market Channel)
- Push-Latenz: <100ms
- Heartbeat: 10s PING
- Reconnect: Exponential Backoff (max 5 Retries)
- Fallback: HTTP-Poll bei WS-Ausfall

**Ziel-Latenz nach T-WS:** 1–3s statt 13–15s.
**Synergie mit T-M-NEW:** Insider-Erkennung in 1–5s statt 30+ Minuten.

Server-Geografie: Hetzner Helsinki → AWS London ~30ms (optimal).

Prompt-Dokument: `prompts/t_ws_websocket_wallet_monitor.md`

---

_Ende STRATEGY.md | Stand: 2026-04-20_
