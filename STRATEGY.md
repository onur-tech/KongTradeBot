# KongTradeBot — Handelslogik & Strategie
_Stand: 18.04.2026_

## 1. Grundidee: Copy Trading

Wir kopieren 11 profitable Polymarket-Wallets ("Whales") die historisch 
belegt Geld verdienen. Sobald eine Whale-Wallet eine Wette platziert, 
spiegeln wir sie automatisch in reduzierter Größe.

Warum es funktioniert: Diese Wallets haben über Monate/Jahre Edge 
bewiesen — viele sind Profi-Trader oder Insider in bestimmten Bereichen 
(Tennis, Baseball, Geopolitik). Statt selbst zu analysieren, folgen 
wir den Besten.

## 2. Position-Sizing

Formel:
  Unsere Größe = Whale-Größe 
                × COPY_SIZE_MULTIPLIER (global)
                × Wallet-Multiplier (per-Wallet)
                × Multi-Signal-Boost (1.0-2.0x)

Gecapt bei MAX_TRADE_SIZE_USD.

Aktuelle Config (defensive, nach 137 USD Verlust am 17.04.):
  COPY_SIZE_MULTIPLIER = 0.05  (war 0.15, davor 0.02)
  MAX_TRADE_SIZE_USD = 30
  MAX_POSITIONS_TOTAL = 15
  MIN_MARKT_VOLUMEN_USD = 50000
  CATEGORY_BLACKLIST = col1-, por-, ecu-, arg-b-

## 3. Multi-Signal-Boost (Schwarmintelligenz)

Wenn mehrere Whales gleichzeitig auf denselben Markt setzen:
- 1 Wallet → 1.0x
- 2 Wallets → 1.5x
- 3+ Wallets → 2.0x

Schutz: Wenn mehr als 50 Prozent aller Wallets dieselbe Seite wählen → 
kein Boost (Herdentrieb-Schutz).

Signal-Buffer: 60 Sekunden. Signale werden gesammelt, dann in einem 
Rutsch verarbeitet.

## 4. Risk Management

Hart-Limits:
- MAX_TRADE_SIZE_USD = 30
- MAX_DAILY_LOSS_USD = 150 (Kill-Switch)
- MAX_PORTFOLIO_PCT = 50%
- MAX_POSITIONS_TOTAL = 15

Odds-Filter: nur Trades zwischen 15% und 85% Wahrscheinlichkeit.
Freshness-Filter: Signale älter als 5 Min werden ignoriert.
Market-Budget-Limit: max 30 USD pro einzelnem Markt.
Volumen-Filter: Märkte unter 50k USD Volumen geskippt 
(Bug-Fix 18.04.: vol > 0 and vol < MIN, P026b).

## 5. KEIN klassischer Stop-Loss (bewusste Entscheidung)

Polymarket-Wetten sind binäre Outcomes. Preise kippen kurz vor Auflösung 
zu 0 oder 1. Stop-Loss würde schlechter rausdrücken als Abwarten.

Stattdessen: Daily Loss Stop + geplante Exit-Strategie.

## 6. Exit-Strategie (geplant, offen)

3 Szenarien entworfen, noch nicht im Code:
1. Gradual Exit — Whale verkauft 50% → wir auch 50%
2. Full Exit — Whale verkauft alles → wir auch
3. Flip — Whale dreht um → wir drehen auch

Task: Exit-Strategie-Implementierung (siehe TASKS.md).

## 7. Wallet-Decay-Score

- >52% WR → behalten
- 45-52% WR → beobachten (1 Woche)
- <45% WR → austauschen

Kadenzen: Täglich 09:00 WalletScout, Freitag wallet_check.py, 
Monatlich manuelle Review.

## 8. Safety-Systeme

- systemd Auto-Restart
- Watchdog 60s, Telegram-Alert bei Heartbeat-Stale
- PID-Lock mit atexit + SIGTERM + ExecStartPre (3-Ebenen, P022)
- Persistent State mit Stale-Position-Filter (P029)
- Claim-Loop alle 30min (→ 5min geplant)

## 9. Was wir (noch) NICHT machen

- Exit-Strategie (Szenarien oben)
- Slippage-Modell
- Korrelations-Check
- Kelly-Formel
- Dynamic-Edge-Adjustment

## 10. Antworten auf typische Fragen

- "Stop-Loss bei -20%?" → Nein, Polymarket zu volatil
- "Nur Top-3 Wallets?" → Weniger Diversifikation
- "Martingale?" → Tödlich
- "Kelly-Formel?" → Phase 2

Ende STRATEGY.md.
