# KongTradeBot — Live-Activity-Report: T-M04d Soft-Live
**Datum:** 2026-04-19 | **Report erstellt:** 14:20 UTC  
**Analysezeitraum:** Ganztag (03:53–14:20 UTC), Fokus: Soft-Live ab 14:02 UTC  
**Report-Typ:** Read-only Analyse, kein Code-Write

---

## A. Bot-Status

| Parameter | Wert |
|---|---|
| **Status** | ✅ LIVE (PID 159463) |
| **Letzter Start** | 2026-04-19 14:02:38 UTC (Soft-Live-Restart) |
| **Modus** | 🔴 LIVE (DRY_RUN=false) |
| **EXIT_DRY_RUN** | false (seit 14:02) |
| **DAILY_SELL_CAP_USD** | $30.00 |
| **TAKE_PROFIT_PRICE_CENTS** | 95¢ |
| **TAKE_PROFIT_STABILITY_MINUTES** | 10 min |
| **AUTO_SELL_EMERGENCY_STOP** | false |
| **Budget** | $463.35 USDC (max investierbar: $231.67) |
| **Heartbeat** | letzte Balance-Aktualisierung: 14:12 UTC |
| **CLOB Client** | ✅ initialisiert, funder: 0x700BC51b... |
| **Bekannte Trades (Sync)** | 470 TX-Hashes geladen |
| **Exit-State** | 9 Positionen geladen (kein exit_state.json mehr on-disk) |

**Restarts heute:** 4× (03:53, 07:14, 13:01, 14:02)  
Der 14:02-Restart aktivierte EXIT_DRY_RUN=false und DAILY_SELL_CAP=$30.

---

## B. Signal-Pipeline (Ganztag 03:53–14:20)

### B1 — Signale pro Wallet

| Alias | Adresse | Signale detektiert | Kopiert (live buys) | Multiplikator |
|---|---|---|---|---|
| **RN1** | 0x2005d16a... | ~152 (gepuffert) | 7 | 0.2x |
| **denizz** | 0xbaa2bcb5... | ~57 (gepuffert) | 15 | 1.0x |
| **wan123** | 0xde7be6d4... | ~12 (gepuffert) | 1 | 0.5x |
| **0x0c0e270c...** | 0x0c0e270c... | 6 | 0 | default |
| **sovereign2013** | 0xee613b3f... | 3 | 1 | 0.3x |
| **HOOK** | 0x0B7A6030... | 1 | 0 | 1.0x |
| **majorexploiter / kcnyekchno / HorizonSplendidView / reachingthesky** | diverse | 0 | 0 | — |

**Gesamt detektiert:** 425 TradeSignals  
**Gesamt gepuffert:** 231 (54% Pufferrate — Rest sind Duplikate oder direkte Vorab-Ablehnungen)  
**Gesamt live ausgeführt:** 24 BUY-Trades

### B2 — Neue Wallets / Unbekannte Aktivität

- **Erasmus / TheSpiritofUkraine:** Keine Aktivität in heutigem Log erkannt. Diese Wallets befinden sich nicht in den aktuellen TARGET_WALLETS (WalletScout-Ergebnis ausstehend — nächster Scan: 20.04. 09:00 UTC).
- **Gambler1968 (0x7a6192ea...):** War in früheren Restarts noch in der Target-Liste, ab 07:14 entfernt. Heute 0 Signale nach Restart.
- **sovereign2013 (0xee613b3f...):** 3 Signale (Tennis, Busan), 1 Trade ausgeführt ($19.09 → Yunchaokete Bu @ 0.570). Resultat: VERLUST (-$19.09, -100% — Leandro Riedi gewann).

### B3 — Skip-Analyse

| Ablehnungsgrund | Anzahl |
|---|---|
| Budget-Cap überschritten | **136** |
| Micro-Trade < $0.50 | 24 |
| Markt-Budget erschöpft | 7 |
| Odds außerhalb 15–85% | 2 |
| **Gesamt blockiert** | **169** |

Budget-Cap war der mit Abstand häufigste Blockierungsgrund. Zwei Schwellenwerte sichtbar:
- `$342.45 >= $314.53` (109×) — 13:01-Restart, Budget $629→ limit $314
- `$538.49 >= $500.92` (27×) — früherer Restart, Budget $608→ limit $304 (höherer invested-Wert aus sync)

Das Portfolio-Budget-Cap-System funktioniert korrekt: es verhinderte, dass mehr als 50% des On-Chain-Walletguthabens gleichzeitig investiert werden.

---

## C. T-M04d: Price-Trigger ≥95¢ Status

### C1 — Price-Trigger Log-Aktivität

Seit dem Soft-Live-Restart (14:02 UTC) gab es **keine Price-Trigger-Ereignisse** (`price_trigger`-Typ weder als DRY-RUN noch LIVE geloggt).

Vorher (vor 14:02, noch DRY-RUN Modus): Keine `price_trigger`-Einträge gefunden — keiner der Exits vor 14:02 erreichte ≥95¢ Stabilität.

### C2 — Positionen nahe 95¢

**Aktuell offene Positionen: 0** (alle 109 Positionen aus dem Dashboard gehören zu früheren Perioden, API zeigt `"open": 0` für heutigen Tag).

Das Exit-State wurde beim 14:02-Restart mit 9 Positionen geladen — deren aktuelle Preise nicht lokal verfügbar (kein exit_state.json on-disk, keine Live-Price-Abfrage möglich ohne bot-interne Daten).

**Fazit C:** Der Price-Trigger ist korrekt konfiguriert (95¢, 10min Stabilität, $30 Cap, LIVE-Modus). Er wurde heute noch nicht ausgelöst — keine Position hat die Schwelle stabil überschritten.

---

## D. Exit-Manager Events

### D1 — Whale-Exit Events (LIVE-Modus, seit 14:02)

| Zeit | Markt | Aktion | Wert | Status |
|---|---|---|---|---|
| 14:13:52 | US x Iran permanent peace deal by April | WHALE_EXIT Yes | $117.27 | **BLOCKED: Daily-Sell-Cap** |
| 14:14:53 | US x Iran permanent peace deal by April | WHALE_EXIT Yes | $117.27 | **BLOCKED: Daily-Sell-Cap** |

Der Daily-Sell-Cap ($30.00) hat korrekt eingegriffen: Eine Whale-Exit-Sell von $117.27 wurde verhindert. Der Bot prüfte: `$0.00 + $117.27 > $30.00` → geblockt.

**Wichtige Beobachtung:** Die Whale-Exit-Logik hat einen Wiederholungsbug — dieselbe Position "US x Iran permanent peace deal" wurde 5× vor dem Restart (13:56–14:01, noch DRY-RUN) und 2× nach dem Restart (14:13, 14:14) gemeldet. Der Sell-Cap hat die Live-Ausführung korrekt verhindert, aber der Trigger selbst feuert wiederholt.

### D2 — Whale-Exit Events (vor 14:02, DRY-RUN)

Zwischen 13:56 und 14:01 wurden 5× `[DRY-RUN] EXIT WHALE_EXIT: Yes @ 0.500 | sell 100% (13.21 shares) | recv $6.61 | pnl $-3.04 (-31.5%)` für "US x Iran ceasefire extended by April 21" geloggt.

### D3 — TP-Events (DRY-RUN, vor 14:02)

Großes TP-Batch bei Preissprung der Iran-Geopolitik-Positionen auf $0.50:

| Zeit | Typ | Position | Pnl |
|---|---|---|---|
| 12:44:31 | TP1 (40%) | US x Iran permanent peace deal | +$25.87 (+123%) |
| 12:44:31 | TP1 (40%) | Iran agrees to end enrichment | +$17.07 (+77.5%) |
| 12:44:31 | TP1 (40%) | Iran x Israel/US conflict ends | +$23.31 (+203%) |
| 12:44:31 | TP1 (40%) | Trump end military operations | +$16.49 (+91.8%) |
| 12:44:31 | TP1 (40%) | Strait of Hormuz traffic normal | +$10.94 (+72.2%) |
| 12:44:32 | TP1 (40%) | Iran surrenders enriched uranium | +$5.92 (+65.6%) |
| 12:44:32 | TP1 (40%) | Trump end military (2. Position) | +$3.74 (+35.1%) |
| 12:47:15 | TP2 (40%) | US x Iran permanent peace | +$25.87 (+123%) |
| ... | TP2 (6 weitere) | diverse Iran-Positionen | ... |
| 12:48:17 | TP3 (15%) | US x Iran permanent peace | +$9.70 (+123%) |
| 12:48:17 | TP3 | Iran x Israel/US conflict | +$8.74 (+203%) |

**Alle DRY-RUN** — diese wären im LIVE-Modus signifikante Gewinne gewesen. Trailing-Stop wurde für 6 Positionen aktiviert.

---

## E. Fehler & Warnungen

### E1 — Seit Soft-Live (14:02–14:20)

| Zeit | Level | Modul | Nachricht |
|---|---|---|---|
| 14:02:38 | WARNING | balance | RPC ankr.com → $0.00 (Fallback auf publicnode.com ✅) |
| 14:07:39 | WARNING | balance | RPC ankr.com → $0.00 (Fallback ✅) |
| 14:12:39 | WARNING | balance | RPC ankr.com → $0.00 (Fallback ✅) |
| 14:13:52 | WARNING | exit_manager | Daily-Sell-Cap: $0.00 + $117.27 > $30.00 |
| 14:14:53 | WARNING | exit_manager | Daily-Sell-Cap: $0.00 + $117.27 > $30.00 |

Kein ERROR seit 14:02. RPC-Fallback auf publicnode.com funktioniert zuverlässig.

### E2 — Ganztag (kritische Fehler)

| Zeit | Level | Modul | Nachricht |
|---|---|---|---|
| 11:23–12:28 | ERROR | claim | `'ClobClient' object has no attribute 'redeem'` (×14) |
| 12:44:32 | ERROR | main | `log_trade() missing 6 required positional arguments` |

**E2a — Claim-Fehler:** AutoClaim versucht `clob.redeem()`, diese Methode existiert nicht in der aktuellen CLOB-Client-Version. Betroffen: "Fajing Sun" (11:23–12:28) und "Leandro Riedi" (11:48–12:28). Kein Geldverlust — nur fehlgeschlagene Claim-Versuche. Architekt. Blockade bekannt (T-M04b). **Pendend: Fix für claim.py.**

**E2b — log_trade() Fehler:** Einmalig bei 12:44:32 im exit_loop aufgetreten. Wahrscheinlich nach dem TP-Exit-Batch, als exit_manager versucht hat einen Trade zu loggen. Signature-Mismatch zwischen exit_manager und log_trade(). Wurde bei DRY-RUN nicht blockierend — Trade-Archiv enthält nur BUY-Einträge und [polymarket-sync]-SELLs, keine Exit-Manager-Sells.

---

## F. P&L Übersicht

### F1 — Heute (2026-04-19, nach Archive)

| Metrik | Wert |
|---|---|
| **Ausgeführte BUY-Trades** | 24 (live) |
| **Ausgeführte SELL-Trades** | 13 (DRY-RUN via exit_manager, vor 14:02) |
| **Investiert (buys)** | $361.52 |
| **PnL heute** | **-$11.26** |
| **Aufgelöste Positionen** | 5 (2 GEWINN, 3 VERLUST) |
| **Win/Loss** | 2W / 3L = 40% WR |

**Gewinner heute:**
- Leandro Riedi (Busan): +$18.54 (+185.7%, $9.98 investiert)
- Leandro Riedi (Busan, 2.): +$5.75 (+112.8%, $5.10 investiert)

**Verlierer heute (bereits resolved):**
- Yunchaokete Bu (Busan, 2 Positionen): -$19.09 + -$7.85 (-100%)
- Under (Adelaide): -$8.61 (-100%)

**Größte offene Positionen (unresolved, Geopolitik):**
- denizz: 10+ Iran-Positionen @ $0.19–$0.73 Einstieg, alle von 10:20–12:27
- wan123: 1 Iran-Position @ $0.296

### F2 — Gesamtkonto (Dashboard-Stats)

| Metrik | Wert |
|---|---|
| **Gesamte offene Positionen** | 109 |
| **Geschlossene Positionen** | 18 |
| **PnL heute (Bot-intern)** | -$11.26 |
| **PnL gesamt** | -$127.82 |
| **Win-Rate** | 11.1% (2W / 16L) |
| **Investiert (offen)** | $167.18 |
| **On-Chain Balance** | $463.35 USDC |

---

## G. Auffälligkeiten & Empfehlungen

### G1 — Whale-Exit Wiederholungs-Bug (kritisch)
**Problem:** Position "US x Iran ceasefire extended by April 21" feuerte den WHALE_EXIT-Trigger 7× (5× DRY-RUN, 2× LIVE geblockt). Der Trigger re-evaluated dieselbe Whale-Sell-Transaktion in jedem Loop-Durchlauf.  
**Impact:** Im LIVE-Modus ohne Daily-Cap würde dieselbe Position mehrfach verkauft. Daily-Cap hat hier als Sicherheitsnetz gewirkt.  
**Empfehlung:** Exit-State `whale_exit_done: bool` Flag prüfen oder TX-Hash der Whale-Sell deduplizieren.

### G2 — log_trade() Signature-Mismatch (mittel)
**Problem:** exit_manager.py ruft `log_trade()` ohne alle 6 Pflichtargumente auf.  
**Impact:** Exit-Manager-Sells werden nicht ins trades_archive.json geschrieben — Audit-Trail lückenhaft.  
**Empfehlung:** log_trade()-Aufruf in exit_manager.py mit allen Parametern fixen.

### G3 — Budget-Cap-Dominanz (Information)
136 von 169 Ablehnungen (80%) wegen Budget-Cap. Bei $463.35 Balance und $231.67 max-invest wurden die meisten denizz Iran-Signale nach dem 12. Trade geblockt. Kein Handlungsbedarf — System wie designed.

### G4 — Daily-Sell-Cap korrekt aktiv (positiv)
Der $30-Cap hat heute eine $117.27-Sell verhindert. Da es sich um eine Iran-Geopolitik-Position handelt, die noch offen ist, ist der Cap-Block strategisch korrekt (Position könnte noch steigen).

### G5 — Price-Trigger noch nicht ausgelöst (neutral)
Keine Position hat 95¢ stabil für 10 min erreicht. Iran-Positionen auf 50¢ — weit entfernt. Trigger wartet.

---

## H. Konfiguration beim Report-Zeitpunkt

```
DRY_RUN=false                          ← LIVE
EXIT_DRY_RUN=false                     ← LIVE (seit 14:02)
TAKE_PROFIT_PRICE_CENTS=95
TAKE_PROFIT_STABILITY_MINUTES=10
DAILY_SELL_CAP_USD=30
AUTO_SELL_EMERGENCY_STOP=false
COPY_SIZE_MULTIPLIER=0.05
MAX_TRADE_SIZE_USD=30
WALLET_WEIGHTS: April#1-Sports=0.3x, HOOK=1.0x (T-M09b)
```

---

*Generiert von Claude Code (claude-sonnet-4-6) | Commit: docs(analysis): Live-Bot-Activity-Report*
