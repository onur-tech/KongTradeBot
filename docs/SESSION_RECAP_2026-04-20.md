# Session Recap — 2026-04-20 (Sonntag)
_Erstellt: 2026-04-20 | Dauer: ~6 Stunden | Windows-CC + Server-CC_

---

## Was heute deployed wurde (Server-CC)

### T-M08 Phase 4+5 — State-Machine
- Positionen haben nun explizite States: `ACTIVE` und `RESOLVED_LOST`
- Verhindert Zombie-Positionen die endlos offen bleiben
- Gelöste Märkte werden korrekt als RESOLVED_LOST markiert statt still gelöscht

### T-M04e — Stop-Loss (Trigger B + C)
- **Trigger B:** Position nach 24h noch ≤15¢ → automatisches Close
- **Trigger C:** Entry ≥40¢ und aktueller Preis ≤30% des Entry → Close
- Erster echter automatischer Stop-Loss im Bot
- Nicht angewendet auf Longshots (<15¢ Entry) und letzte 6h vor Marktende

### T-M03 — Whale-Exit-Copy
- Bot kopiert jetzt SELL-Signale von Whales
- Wenn getrackte Wallet verkauft → wir folgen proportional
- Einstieg UND Ausstieg wird kopiert (Gradual / Full Exit / Flip)
- Ermöglicht erstmals korrekte P&L-Berechnung

### T-M06 — Reconciliation MVP + echter P&L
- On-Chain-Abgleich: Bot-Positionen werden mit Blockchain-State verglichen
- Echter realisierter P&L berechenbar (nicht nur Schätzwerte)
- Basis für zukünftige Kelly-Formel und Edge-Kalibrierung

### Dashboard-Fix — OPEN=12 / RESOLVED=13
- Zählfehler behoben: Positionen wurden doppelt gezählt
- Dashboard zeigt jetzt korrekte Positionsanzahl

### Crypto-Daily Single-Signal Buffer
- Crypto-Sektor: erstes Signal wird 24h gepuffert
- Erst beim zweiten Bestätiger oder nach 24h wird Trade ausgeführt
- Verhindert Einzelwallet-Bounce-Trades im volatilen Crypto-Sektor

### Daily-Cap $100
- Maximal $100 an neuen Trades pro Tag
- Unabhängig von MAX_DAILY_LOSS (Verlust-Stop)
- Verhindert Overtrading bei vielen gleichzeitigen Signalen

### Log-Rotation
- Tägliche Logfiles: `logs/bot_YYYY-MM-DD.log`
- Automatische Archivierung älterer Logs
- Basis für Latenz-Monitoring und Performance-Analyse

### Portfolio-Chart
- Telegram-Report enthält jetzt Portfolio-Value-Chart
- Tägliche Snapshot-Grafik mit P&L-Verlauf

---

## Was heute entschieden wurde (Strategie)

### Lern-Modus: Datenpunkte > Portfolio-Schutz
Das $1.000-Portfolio ist Spielkapital. Ziel ist nicht maximaler Schutz,
sondern maximale Daten und Feature-Tests. Parameter entsprechend gelockert:
COPY_SIZE_MULTIPLIER 0.05 → 0.10, MAX_POSITIONS 15 → 30.

### WALLET_SCOUT_BRIEFING v2.0: Profitabilität zuerst
Alte Philosophie: Wallet muss WR ≥55% haben → viele profitable Wallets rejected.
Neue Philosophie: Einzige Frage ist "Hat das Wallet Geld verdient?".
WR ist kein Gate sondern Strategie-Indikator.
Dokument: `WALLET_SCOUT_BRIEFING.md` v2.0 deployed.

### Early-Loss-Selling = legitime Strategie (kein Ablehnungsgrund)
DrPufferfish (91% WR predicts.guru = 50.9% true) und Countryside (96% → 48.5%)
zeigen artificial WR durch Early-Loss-Selling + Zombie-Orders.
Entscheidung: Diese Strategie ist legitim — WR-Artefakt ist Feature, nicht Bug.
Beide werden nicht wegen WR rejected sondern wegen Bot-Kompatibilität (T-M03 nötig).

### Geopolitik-Konzentration = größtes Risiko
Aktuelle Wallet-Liste: 4+ Geopolitik-Wallets (Erasmus, TheSpiritofUkraine,
wokerjoesleeper, ScottyNooo). Ein einziges Breaking-News-Event korreliert alle.
Warnung in STRATEGY.md dokumentiert. Sektor-Balance-Ziel: max 4 Geo-Wallets.

### Insider-Pattern kopieren = neue Strategie (T-M-NEW)
Harvard-Studie: $143M wurden über 3 Jahre auf Polymarket in Kenntnishandel investiert.
Iran-Ceasefire April 7: $663K auf 4 neue Wallets bei 2.9–10.3¢ — vor Nachricht.
Entscheidung: AnomalyDetector scannt alle Trades nach Insider-Muster.
Prompt fertig: `prompts/t_m_new_anomaly_detector.md`

### WebSocket = nächste Latenz-Reduktion (T-WS)
Aktuell: 10s Poll → 13–15s Signal-Latenz. Breaking-News-Window: <30 Sekunden.
Entscheidung: WebSocket-Upgrade ist höchste technische Priorität.
Prompt fertig: `prompts/t_ws_websocket_wallet_monitor.md`

---

## Wallet-Änderungen heute

| Aktion | Wallet | Adresse | Begründung |
|--------|--------|---------|-----------|
| ENTFERNT | April#1 Sports | `0x492442...` | Lifetime PnL -$9.8M, HF-10 FAIL |
| HINZUGEFÜGT | DrPufferfish | `0xdb27bf...` | 3.0x dormant, T-M03 Exit-Quelle (NBA) |
| HINZUGEFÜGT | Countryside | `0xbddf61...` | 3.0x dormant, T-M03 Exit-Quelle (Sports) |
| HINZUGEFÜGT | wokerjoesleeper | `0x63d43b...` | Tier B 0.5x, $900K, +227% ROI |
| HINZUGEFÜGT | ScottyNooo | `0xbacd00...` | Tier B 0.3x, $1.3M, Politik/Trump/Iran |
| REJECT | bcda | `0xb45a79...` | -89.41% ROI auf Deposits, -$2.4M all-time |
| REJECT initial | DrPufferfish | — | HF-8 FAIL (WR), revidiert: dormant für T-M03 |
| REJECT initial | Countryside | — | HF-8 FAIL (WR), revidiert: dormant für T-M03 |

**DrPufferfish + Countryside Status:** Dormante Code-Einträge (in WALLET_MULTIPLIERS,
NICHT in TARGET_WALLETS). Aktivierung erst wenn T-M03 Whale-Exit-Copy live.

**bcda Lektion (KB P084):** Cointrenches meldete "+$2M/Woche" — war Peak-Woche-Snapshot.
0xinsider: -$1.55M, predicts.guru: -$2.39M (-89% ROI). Pflicht: BEIDE Quellen vor APPROVE.

---

## Offene Tasks (Priorität)

### SOFORT (nächste Session)
1. **T-WS** — WebSocket WalletMonitor
   - Prompt: `prompts/t_ws_websocket_wallet_monitor.md` (bereit)
   - Server-CC implementiert nach Windows-CC Push
   - Ergebnis: 10s → 1-3s Latenz

2. **T-M-NEW** — Anomalie-Detektor
   - Prompt: `prompts/t_m_new_anomaly_detector.md` (bereit)
   - Nach T-WS implementieren (Synergie: 1-5s Insider-Erkennung)

3. **US×Iran Resolution** — heute Nacht / morgen
   - Position bei ≥95¢ → T-M04d feuert automatisch
   - Manuell claimen: polymarket.com + Norwegen-VPN

### BALD
4. **T-M11** — Auto-Claim
   - Blockiert durch fehlende POL für Gas-Fees
   - Manuelles Claimen als Workaround

5. **T-M21** — Basket-Strategie (SeriouslySirius, beachboy4)
   - Prompt: `prompts/t_m21_basket_strategy.md` (bereit)
   - Benötigt: SeriouslySirius + beachboy4 WR-Bestätigung zuerst

### REVIEWS
- 2026-05-05: ScottyNooo predicts.guru Deposit-ROI; cowcat/Frank0951/middleoftheocean
- 2026-05-19: T-D109 monatliche Wallet-Review (Erasmus, TheSpiritofUkraine, HOOK, April#1)
- 2026-05-20: Countryside 30-Tage-Shadow
- 2026-07-20: DrPufferfish 90-Tage-Shadow

---

## Wichtigste Erkenntnisse

### 1. predicts.guru WR > 80% → immer mit 0xinsider gegenchecken
predicts.guru-WR ist durch Early-Loss-Selling + Zombie-Orders verzerrt.
Beispiele: DrPufferfish 91% → 50.9% wahre WR; Countryside 96% → 48.5%.
Regel: Hohe WR ist Warn-Signal, nicht Beweis. Immer Cross-Check.

### 2. ROI auf Deposits ist einziger echter Performance-Indikator
Absolutes PnL kann durch hohes eingesetztes Kapital entstehen.
Cointrenches zeigt Peak-Wochen, nicht All-Time. Predicts.guru ROI auf Deposits
ist der einzige Wert der Kapitaleffizienz korrekt misst. Beispiel: bcda $2.7M
eingezahlt, $66K raus → -89% ROI trotz "+$2M/Woche"-Schlagzeile.

### 3. Geopolitik-Wallets können Insider sein
Harvard-Studie: $143M an verifizierten Insider-Trades auf Polymarket.
Iran-Ceasefire: 4 neue Wallets, $663K, Entry 2.9–10.3¢ = klares Insider-Signal.
T-M-NEW soll genau diese Muster in Echtzeit erkennen.

### 4. Copy Exit ist genauso wichtig wie Copy Entry
Ohne T-M03 kopierten wir nur Einstiege — Whale-Timing beim Ausstieg
ist oft der Mehrwert. DrPufferfish und Countryside sind primär Exit-Quellen.
T-M03 ist damit das wertvollste heute deployte Feature.

### 5. PANews Biteye als neue Top-Wallet-Quelle
26 handkuratierte Adressen mit Sektor-Breakdown und Style-Profilen.
Qualität deutlich höher als Polyscan/WalletMaster (nur Marketing-Seiten).
Wokerjoesleeper (+227% ROI) und ScottyNooo ($1.3M) daraus entdeckt.

### 6. Watching-Queue für zukünftige Approvals
5 weitere vielversprechende Wallets dokumentiert (Review 2026-05-05):
cowcat (+117% ROI, ME-Longshot), Frank0951, middleoftheocean, ewelmealt, How.Dare.You.

---

## Analyse-Dateien erstellt heute

| Datei | Inhalt |
|-------|--------|
| `analyses/re_audit_rejected_wallets_2026-04-20.md` | Re-Audit 14 Wallets unter v2.0 |
| `analyses/wallet_scout_v2_2026-04-20.md` | Scout v2.0 Ergebnisse |
| `analyses/bcda_verification_2026-04-20.md` | bcda REJECT-Dokumentation |
| `analyses/deep_discovery_2026-04-20.md` | Deep Discovery (PANews 26 Wallets) |
| `prompts/t_m21_basket_strategy.md` | Basket-Strategie Design |
| `prompts/t_m_new_anomaly_detector.md` | Anomalie-Detektor Design |
| `prompts/t_ws_websocket_wallet_monitor.md` | WebSocket Monitor Design |
| `STRATEGY.md` | Vollständig überarbeitet |
| `WALLET_SCOUT_BRIEFING.md` | v2.0 Profit-First |

---

_Commits heute: 93506bc, c642706, 3bfcba3, ebc2754, ee9670f, 4de6ef5_
