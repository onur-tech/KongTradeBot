# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a **Polymarket Copy Trading Bot (v0.6)** — an async Python bot that monitors target wallets (whales) on Polymarket prediction markets and copies their trades proportionally using a 4-step pipeline.

## Running the Bot

```bash
# Install dependencies (one-time)
pip install -r requirements.txt
cp .env.example .env   # then fill in .env with your wallet/config

# Dry-run (default — simulates trades, no real money)
python main.py

# Live trading (real money)
python main.py --live

# Export tax CSV
python main.py --export-tax 2026

# Utility scripts
python api_test.py        # Test Polymarket API connectivity
python wallet_check.py    # Check wallet USDC balance
python resolver.py        # Resolve markets & update PnL
python auswertung.py      # Analytics/reporting
```

## Running Tests

```bash
python test_execution_engine.py
python test_performance_tracker.py
```

## Architecture: 4-Step Pipeline

Each trade signal flows through four sequential components:

```
WalletMonitor → CopyTradingStrategy → RiskManager → ExecutionEngine
```

1. **`core/wallet_monitor.py`** — Polls `data-api.polymarket.com/activity` every 10s for target wallets. Deduplicates by transaction hash (not timestamp). Emits `TradeSignal` dataclass objects.

2. **`strategies/copy_trading.py`** — Receives `TradeSignal`, checks source wallet win-rate decay (stops copying if recent 20-trade win rate < 45%), calculates proportional size (`whale_size × COPY_SIZE_MULTIPLIER`, default 5%), emits `CopyOrder`.

3. **`core/risk_manager.py`** — Enforces all risk constraints in order: kill-switch, daily loss limit, time-to-close (24–72h only), price extremity (8%–92% range), min/max size. Returns `RiskDecision`. Kill-switch auto-resets at midnight.

4. **`core/execution_engine.py`** — Dry-run: simulates and logs. Live: creates `ClobClient`, derives API creds, retrieves tick size, calls `create_and_post_order()` (single call — do NOT split into create + post), waits 500ms, verifies fill on-chain (never trust API response alone).

## Key Architecture Notes

**main.py** runs 6 concurrent async tasks: `WalletMonitor`, `StatusReporter` (console 60s / Telegram 1h), `BalanceUpdater` (every 5m from Polygon RPC), `MorningReportSender` (8am daily), `ResolverLoop` (every 15m), `CommandPoller` (Telegram commands).

**State persistence** (`utils/state_manager.py`): saves to `bot_state.json` on shutdown, restores on startup (same-day positions + all tx hashes). Seen tx hashes are always restored to prevent duplicate trades across restarts.

**Configuration** (`utils/config.py`): all settings from `.env`. Key vars: `PRIVATE_KEY`, `POLYMARKET_ADDRESS`, `TARGET_WALLETS` (comma-separated), `DRY_RUN`, `MAX_DAILY_LOSS_USD`, `MAX_TRADE_SIZE_USD`, `COPY_SIZE_MULTIPLIER`, `PORTFOLIO_BUDGET_USD`.

**Balance** is read directly from Polygon blockchain via Web3 RPC — not from Polymarket API — and updates `config.portfolio_budget_usd` live.

## Critical Implementation Rules

- **Always use `create_and_post_order()`** in the execution engine — never `create_order()` + `post_order()` separately (causes ghost trades).
- **Never call `update_balance_allowance()`** after a fill — it breaks state.
- **Always call `set_api_creds()`** before any trading operation.
- Verify fills **on-chain** (check balance change), do not trust API response alone.
- Transaction hash dedup set is capped at 10,000 entries (memory management).

## Data Classes (core structures)

| Class | File | Key Fields |
|---|---|---|
| `TradeSignal` | `core/wallet_monitor.py` | tx_hash, source_wallet, market_id, token_id, side, price, size_usdc |
| `CopyOrder` | `strategies/copy_trading.py` | signal, size_usdc, dry_run |
| `RiskDecision` | `core/risk_manager.py` | allowed, reason, adjusted_size_usdc |
| `OpenPosition` | `core/execution_engine.py` | order_id, market_id, token_id, entry_price, size_usdc, shares |
| `ExecutionResult` | `core/execution_engine.py` | success, order_id, filled_price, error, dry_run |

## Generated Files (runtime)

- `bot_state.json` — persistent positions and seen tx hashes
- `trades_archive.json` — all trades for auditing and tax
- `wallet_history.json` — wallet monitoring history
- `logs/bot_YYYY-MM-DD.log` — daily rotating logs
- `steuer_export_YYYY.csv` — tax export (German §22 EStG format)
