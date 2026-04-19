# Wallet-Audit v1.0 — Ergebnisse (19.04.2026)

**Durchgeführt von:** Brrudi (manuell)
**Grundlage:** WALLET_SCOUT_BRIEFING.md v1.0
**Commit:** 7c29ac9

---

## Zusammenfassung

Erster Audit der bestehenden TARGET_WALLETS gegen
WALLET_SCOUT_BRIEFING.md v1.0 Hard-Filter. 3 Wallets entfernt
aufgrund klarer Win-Rate-Verletzungen (HF-8).

---

## Audit-Kontext

Erst mögliche Auswertung nach 4 Tagen Bot-Betrieb.
Datengrundlage beschränkt: 97 Trades insgesamt, 0 resolved.

Auswertung basierte auf:
- `trades_archive.json` (lokale Trade-Historie)
- predicts.guru Win-Rate-Werte (extern, aus Code-Kommentaren)
- WALLET_MULTIPLIERS Konfiguration

---

## Entfernte Wallets

### RN1 (0x2005d16a84ceefa912d4e380cd32e7ff827875ea)
- **Win-Rate:** 27% (predicts.guru)
- **Hard-Filter:** HF-8 FAIL (erforderlich 55–75%)
- **Kopierte Trades:** 80 von 97 (87% Volume)
- **Unrealized PnL:** -$1.025
- **Status:** REMOVED 19.04.2026 — Commit 7c29ac9

**Haupterkenntnis:** RN1 war systematischer Verlust-Generator.
Das Briefing hätte diese Wallet nie approved. Manueller Audit
bestätigt Wirksamkeit der Kriterien.

### Gambler1968 (0x7a61...f24)
- **Win-Rate:** 45%
- **Hard-Filter:** HF-8 FAIL
- **Kopierte Trades:** 1
- **Status:** REMOVED 19.04.2026

### sovereign2013 (0xee61...debf)
- **Win-Rate:** 49%
- **Hard-Filter:** HF-8 FAIL
- **Kopierte Trades:** 3
- Bereits auf 0.3x Multiplier gestraft, Entfernung aber konsequenter
- **Status:** REMOVED 19.04.2026

---

## Wallets unter Beobachtung (KEINE Entfernung)

9–10 Wallets mit 0 kopierten Trades bleiben unter Beobachtung.
4 Tage sind statistisch unbedeutend. Entscheidung erst nach
30+ Tagen Aktivitätsfenster.

**Gründe warum 0 Trades:**
- Möglicherweise wochenend-inaktiv
- Andere Filter (MIN_TRADE_SIZE, Budget-Cap) haben geblockt
- Trade-Kategorien geblacklistet

**Wallets unter Beobachtung:**

| Wallet | Externe Win-Rate | Nächster Review |
|--------|-----------------|-----------------|
| majorexploiter | 76% | 2026-05-19 |
| April#1 Sports | 65% | 2026-05-19 |
| HorizonSplendidView | — | 2026-05-19 |
| reachingthesky | — | 2026-05-19 |
| HOOK | — | 2026-05-19 |
| kcnyekchno | 81% | 2026-05-19 |
| Countryside | 92% | 2026-05-19 |
| Crypto Spezialist | 66% | 2026-05-19 |
| BoneReader | 72% | 2026-05-19 |
| DrPufferfish | 92% | 2026-05-19 |

**Nächster Review:** 2026-05-19 (30 Tage)

---

## Vollständig evaluierbare Filter

Audit v1.0 prüfte faktisch nur 2 von 9 Hard-Filtern:

| Filter | Status | Datenquelle |
|--------|--------|-------------|
| HF-5 Aktiv 14d | Teilweise ✓ | trades_archive.json |
| HF-8 Win-Rate | ✓ geprüft | predicts.guru |
| HF-1 Sample-Size | ❌ UNKNOWN | predicts.guru Trade-Count fehlt |
| HF-2 Account-Alter | ❌ UNKNOWN | Polygon-Daten nicht abgerufen |
| HF-3 Max-Drawdown | ❌ UNKNOWN | keine historischen Daten |
| HF-4 Drawdown-Survival | ❌ UNKNOWN | keine historischen Daten |
| HF-6 Profit-Konzentration | ❌ UNKNOWN | 0 resolved Trades |
| HF-7 ROI-Deposits | ❌ UNKNOWN | 0 resolved Trades |
| HF-9 Last-Minute-Pattern | ❌ UNKNOWN | Zeitstempel-Analyse fehlt |

**Vollständiger Audit** erfordert Integration einer
Wallet-Analyse-API (predicts.guru-Scraping oder direkte
On-Chain-Analyse via Polygon). Siehe T-D107 (neu).

---

## Nicht-dokumentierte Skipped Signals

Onurs Beobachtung: Bot skippt viele Signale (MIN_TRADE_SIZE,
Budget-Cap, Kategorie-Blacklist), aber die verschwinden im Log.
Wir lernen nicht ob Filter zu streng sind.

**Lösungsansatz:** Skipped-Signal-Shadow-Tracking (T-D105 in Implementation).

---

## Discovery-Gap

Onurs zweite Beobachtung: Audit prüft nur WALLETS DIE WIR SCHON FOLGEN.
Es gibt ~300.000 Polymarket-Wallets. Vielleicht existieren bessere
Kandidaten die der alte Scout nie vorgeschlagen hat.

**Lösungsansatz:** On-Chain-Wallet-Discovery-Scan (T-D106 neu).

---

## Meta-Erkenntnis für KongReview

Erste Anwendung des Scout-Briefings zeigt gleichzeitig wo
Briefing v1.0 funktioniert (HF-8 Win-Rate erfasst RN1 klar)
und wo Lücken sind (Skipped Signals, Discovery, fehlende Daten für 7 Filter).

Nächste Briefing-Version (v1.1) adressiert:
- Skipped-Signal-Feedback-Loop
- Discovery-Scan-Integration
- External-Data-Source für vollständige Hard-Filter-Prüfung
- Explizite Beobachtungszeit-Regel
