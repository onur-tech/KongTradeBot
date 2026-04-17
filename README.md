# Polymarket Copy Trading Bot

## Architektur

```
polymarket_bot/
├── core/
│   ├── wallet_monitor.py     # Schritt 1: Wallet überwachen (WebSocket + Polling)
│   ├── trade_detector.py     # Schritt 2: Trades erkennen & deduplizieren
│   ├── execution_engine.py   # Schritt 3: Orders platzieren (mit On-Chain Verifikation)
│   └── risk_manager.py       # Schritt 4: Kill-Switch, Max-Loss, Limits
├── strategies/
│   └── copy_trading.py       # Strategie: Proportionales Sizing
├── utils/
│   ├── logger.py             # Strukturiertes Logging
│   └── config.py             # Config aus .env
├── tests/
│   └── test_wallet_monitor.py
├── .env.example              # Template — NIEMALS echten Key committen
├── main.py                   # Einstiegspunkt
└── README.md
```

## Lektionen aus der Community eingebaut

1. **On-Chain Verifikation** — API-Response wird NICHT vertraut, Balance direkt on-chain geprüft
2. **Transaction Hash Deduplizierung** — Kein doppeltes Kopieren desselben Trades
3. **Proportionales Sizing** — Nicht blind dieselben Dollarbeträge kopieren
4. **WebSocket first** — Kein langsames Polling, sondern Live-Stream
5. **Dry-Run Modus** — Bot läuft vollständig, kauft aber nichts (für Tests)
6. **Kill-Switch** — Tages-Verlustlimit stoppt den Bot automatisch
7. **Private Key Sicherheit** — Nur in .env, niemals im Code

## Setup

```bash
pip install py-clob-client python-dotenv web3 aiohttp websockets
cp .env.example .env
# .env ausfüllen — niemals committen!
```

## Starten (Dry-Run)

```bash
python main.py --dry-run
```

## Starten (Live)

```bash
python main.py --live
```
