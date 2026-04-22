# Position State Drift — Stand 2026-04-22 ~08:30 UTC

## Kontext
Polymarket API: 36 Positionen gesamt | 27 aktiv (currentValue > 0.01) | 9 wertlos
Bot State: 22 Positionen

## 1. Wertlose Positionen in Polymarket API (9)
Bot kennt sie, sind aber abgelaufen/verloren — currentValue ≤ $0.01

| conditionId | Markt |
|---|---|
| 0xae17df74... | Will the highest temperature in Paris be 20°C or higher on April 22? |
| 0x8c657b54... | Will the highest temperature in Seoul be 12°C on April 22? |
| 0xdde7b557... | Will the highest temperature in Toronto be 9°C on April 21? |
| 0x5a8eb147... | Will the highest temperature in Dallas be 64°F or higher on ...? |
| 0xfe91b515... | Will the highest temperature in Busan be 18°C on April 22? |
| 0x562230c9... | Will the highest temperature in Atlanta be between 78-79°F on ...? |
| 0x1507c50c... | Trump announces end of military operations against Iran by April ...? |
| 0x7535ca06... | Will the highest temperature in Dallas be between 62-63°F on ...? |
| 0xe9b620b4... | Will the highest temperature in Busan be 16°C on April 22? |

## 2. In API aktiv, NICHT in Bot State (13) ⚠️ GEFÄHRLICH
Der Bot kennt diese Positionen nicht — kein Exit-Management, kein TP/SL

| conditionId | Markt |
|---|---|
| 0x43d2d52a... | Will the highest temperature in Madrid be 28°C on April 21? |
| 0x9bd45757... | Will the highest temperature in Hong Kong be 27°C on April 22? |
| 0xf1ab28d0... | Will the highest temperature in Beijing be 22°C on April 22? |
| 0xefd0723a... | Will the highest temperature in Seattle be between 62-63°F on ...? |
| 0x7f224949... | Will the highest temperature in Madrid be 25°C on April 23? |
| 0xbea530e0... | Will the highest temperature in Moscow be 4°C on April 23? |
| 0x2215280b... | Will the highest temperature in Hong Kong be 28°C on April 22? |
| 0x02f8dd15... | Israel x Hezbollah Ceasefire extended by April 26, 2026? |
| 0x37aa5401... | Will the highest temperature in Istanbul be 15°C on April 23? |
| 0xab877b73... | Will the highest temperature in Warsaw be 14°C on April 23? |
| 0xc0eb2002... | Will the highest temperature in Istanbul be 10°C on April 22? |
| 0x2a9541d4... | Will the highest temperature in Istanbul be 11°C on April 22? |
| 0xd839785e... | Will Donald Trump announce that the United States blockade of ...? |

**Quelle:** Wahrscheinlich Weather-Shadow-Trades oder Positionen die während Bot-Downtime eröffnet wurden.
**Risiko:** Kein automatischer Exit wenn TP/SL-Kriterien erreicht werden.

## 3. In Bot State, NICHT in API aktiv (8) — Leichen
Bot denkt diese Positionen sind offen, Polymarket kennt sie nicht mehr als aktiv

| conditionId | Markt |
|---|---|
| 0x924a2942... | Strait of Hormuz traffic returns to normal by end of April? |
| 0xe6939069... | Iran agrees to end enrichment of uranium by April 30? |
| 0x0656d252... | Atlanta Braves vs. Philadelphia Phillies |
| 0x89683dab... | Tallahassee: Daniil Glinka vs Jack Kennedy |
| 0xa8832afe... | Tampa Bay Rays vs. Pittsburgh Pirates |
| 0xe9b620b4... | Will the highest temperature in Busan be 16°C on April 22? |
| 0x2ac0be05... | Will the highest temperature in Beijing be 25°C on April 23? |
| 0x4ed3e8cd... | Will the highest temperature in Paris be 17°C on April 22? |

## Nächste Schritte (nächste Session)
1. Auto-Import fremder aktiver Positionen in Bot State (Liste 2)
2. State-Cleanup: Leichen aus bot_state.json entfernen (Liste 3)
3. resolver_loop erweitern: Positionen die nicht mehr in API sind → als RESOLVED_LOST markieren
