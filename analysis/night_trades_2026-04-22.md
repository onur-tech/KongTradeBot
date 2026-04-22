# Night Trades Damage Assessment — 2026-04-22 00:00–05:49

**Zeitraum:** Bot lief LIVE (DRY_RUN=false) bis 05:49 Uhr  
**Umstellung auf Paper:** 05:49 Uhr nach manueller .env-Änderung + Restart  
**Alle 14 Orders:** Weather-Scout-Entries (kein Copy-Trading)  
**WEATHER_DRY_RUN=true hatte KEINEN EFFEKT** — nur Dashboard-Display-Flag

---

## Die 14 Orders

| Zeit  | Markt                              | Side | Entry | Einsatz | Status        | Cur%  | P&L     |
|-------|------------------------------------|------|-------|---------|---------------|-------|---------|
| 00:06 | Paris 20°C+ Apr 21                 | YES  | 0.4%  | $10     | RESOLVED_LOST | 0%    | -$2.38  |
| 00:06 | Seoul 16°C Apr 22                  | NO   | 67.5% | $10     | ACTIVE/WIN    | 100%  | +$8.65  |
| 00:37 | NYC 70-71°F Apr 23                 | NO   | 69%   | $10     | ACTIVE        | 67.5% | -$0.22  |
| 00:38 | Atlanta 84-85°F Apr 23             | NO   | 68%   | $10     | ACTIVE        | 68.5% | +$0.07  |
| 00:38 | Seattle 58-59°F Apr 23             | NO   | 67%   | $10     | ACTIVE        | 65.5% | -$0.21  |
| 00:39 | Moscow 4°C Apr 23                  | YES  | 1.2%  | $10     | ACTIVE        | 1.7%  | +$0.46  |
| 02:12 | NYC 68-69°F Apr 23 **DUPLIKAT #1** | NO   | 75%   | $10     | ACTIVE        | 78%   | +$0.36  |
| 02:43 | NYC 68-69°F Apr 23 **DUPLIKAT #2** | NO   | 75%   | $10     | ACTIVE        | 78%   | +$0.36  |
| 03:14 | NYC 68-69°F Apr 23 **DUPLIKAT #3** | NO   | 75%   | $10     | ACTIVE        | 78%   | +$0.36  |
| 04:16 | Beijing 22°C Apr 22                | YES  | 0.6%  | $10     | ACTIVE        | ~0%   | ~-$10   |
| 04:47 | Shanghai 16°C Apr 23               | NO   | 64%   | $10     | ACTIVE        | 63.5% | -$0.08  |
| 04:47 | Istanbul 15°C Apr 23 **DUPLIKAT #1**| YES | 4%    | $10     | ?             | ?     | ?       |
| 05:19 | Istanbul 15°C Apr 23 **DUPLIKAT #2**| YES | 4%    | $10     | ?             | ?     | ?       |
| 05:19 | Miami 78-79°F Apr 23               | NO   | 59%   | $10     | ACTIVE        | 58.5% | -$0.24  |

**Gesamt investiert:** ~$140 USDC (14 × $10)  
**Geschätzter aktueller P&L:** ~-$3 bis +$2 (die meisten NO-Positionen ~breakeven)  
**Einziger klarer Verlierer:** Paris 20°C+ Apr 21 = -$2.38 (April 21 abgelaufen)

---

## Duplikats-Analyse

### NYC 68-69°F (condition_id `0x5dfc7e8cf7d28381...`) — 3× gekauft

**Root Cause: FillTracker-Delay + Snapshot-Timing im Weather-Loop**

```
main.py:1359:  open_condition_ids = {pos.market_id for pos in engine.open_positions.values()}
```

Der Snapshot wird **einmal pro Scan-Iteration** gemacht, bevor die Orders platziert werden. Nach `on_copy_order()` landet die Order zunächst in `engine._pending_data` (warten auf WebSocket-Bestätigung) — **nicht** in `engine.open_positions`. Der nächste Scan-Zyklus (30 Min später) liest wieder denselben leeren Stand.

Timeline:
```
02:12:22  Scan #1 → open_condition_ids = {...} (NYC 68-69 NOT IN IT)
02:12:22  Order gesendet | ID: 0x060ef579...
02:12:22  ⏳ Order pending (wartet auf WS-Bestätigung)
            → in _pending_data, NICHT in open_positions
02:42:37  Scan #2 → open_condition_ids = {...} (NYC 68-69 STILL NOT IN IT!)
02:43:17  Order gesendet | ID: 0x9f23339b...
03:13:32  Scan #3 → open_condition_ids = {...} (NYC 68-69 STILL NOT IN IT!)
03:14:12  Order gesendet | ID: 0x0aac7e70...
```

Die 3 Scans liefen alle 30 Minuten auseinander. Jedes Mal war die vorherige Order noch nicht von FillTracker in `open_positions` promotet worden (oder WS-Bestätigung kam nie).

**Gleiche Root Cause bei Istanbul 15°C** (04:47 und 05:19, 32 Min auseinander).

### Fix (Phase 0.7): In-Memory-Set `_weather_ordered_cids`
Wird in `weather_loop()` als prozessweites Set geführt. Nach jedem `on_copy_order()` sofort befüllt, **unabhängig von FillTracker**. Überlebt mehrere Scan-Zyklen.

---

## Alle Orders: Quelle = Weather-Scout

Kein einziger dieser Trades war ein Copy-Trade. Alle kamen aus dem Weather-Scout via `run_weather_scout()` in `main.py:weather_loop()`. Der Bot handelte autonom auf Basis seiner eigenen Forecast-Analyse — ohne Whale-Signal.

---

## Offene Risiken dieser Positionen

- **NYC 68-69 NO (x3):** Drei separate Positionen auf dieselbe condition_id — $30 investiert statt $10. Aktuell leicht positiv (+$1.08 gesamt). Schließt in ~18h.
- **Beijing 22°C YES:** Sehr niedriger Entry-Preis (0.6%), wahrscheinlich ~-$10 bei Auflösung.
- **Moscow 4°C YES:** Longshot, $10 auf 1.7% Preis.
- **Paris YES:** Bereits verloren (-$2.38, RESOLVED_LOST).
- **Seoul 16°C NO:** Gewinnt gerade (+$8.65, Preis bei 100%).

**Erwarteter Gesamt-P&L dieser 14 Orders: ca. -$4 bis +$12** je nach NYC/Seoul/Atlanta-Auflösung.
