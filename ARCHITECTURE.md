# KongTradeBot — Technische Architektur
_Stand: 18.04.2026_

## Deployment

- Host: Hetzner Cloud CAX11 ARM64, Helsinki
- IP: 89.167.29.183
- OS: Ubuntu 24.04 LTS
- Python: 3.12
- Code-Pfad: /root/KongTradeBot/
- Warum Helsinki: Deutschland bei Polymarket geoblockt, VPN-IPs erkannt, 
  Hetzner-Hosting-IP akzeptiert für API-Traffic

## Wallet-Architektur (KRITISCH)

Magic-Link-Accounts haben DREI separate Adressen:

### 1. Magic-EOA (signiert)
- 0xd7869A5Cae59FDb6ab306ab332a9340AceC8cbE2
- Private Key aus reveal.magic.link/polymarket
- Hält KEIN Geld

### 2. Polymarket-Proxy (hält Geld)
- 0x700BC51b721F168FF975ff28942BC0E5fAF945eb
- Smart-Contract-Wallet, Controller: Magic-EOA
- 629 USDC.e (aktuell)
- Wird beim ersten Trade on-chain deployed (P004)

### 3. Profile-Address (Display)
- 0x3e328A8b896D5ABEC5043E193Dc8045Dc7d3Ed31
- STUCK: 2933 USDC + 165 POL
- Recovery: https://recovery.polymarket.com

## Signature Types

- 0: Standard EOA (MetaMask)
- 1: POLY_PROXY / Magic-Link ← UNSER FALL
- 2: POLY_GNOSIS_SAFE

In execution_engine.py MUSS signature_type=1 sein.

## ClobClient-Init

ClobClient(host, key=MAGIC_EOA_KEY, chain_id=137,
signature_type=1, funder=POLYMARKET_PROXY)

signer = Magic-EOA, funder = Proxy.

## Bot-Komponenten

- core/wallet_monitor.py — Poll Target-Wallets alle 10s
- core/execution_engine.py — ClobClient, Orders, Balance
- core/risk_manager.py — Filter, Kill-Switch
- core/fill_tracker.py — WebSocket User-Channel
- core/balance_fetcher.py — Multi-RPC Fallback
- strategies/copy_trading.py — Signal-Buffer, Multiplier
- utils/config.py, utils/tax_archive.py
- telegram_bot.py
- scripts/watchdog.py, generate_status.py, push_status.sh, 
  tunnel_watcher.py, claim_all.py

## Systemd-Services

| Service | Funktion | Intervall |
|---|---|---|
| kongtrade-bot | Hauptbot | permanent |
| kongtrade-watchdog.timer | Health-Check | 60s |
| kongtrade-tunnel | Cloudflare Tunnel | permanent |
| kongtrade-tunnel-watcher.timer | URL-Alert | 5min |
| kongtrade-status.timer | Auto-Push STATUS | 5min (AUS) |
| kongtrade-deploy.timer | Auto-Pull + Restart | 5min |
| kongtrade-tax-export.timer | Wöchentlicher CSV-Export | Freitag 23:55 Berlin |

## Auto-Deploy-Pipeline (18.04.2026)

Windows-CC pusht Code → GitHub → Hetzner pullt binnen 5 Min autonom.

Komponenten:
- `scripts/auto_deploy.sh` — git fetch, bei Änderung pull +
  systemctl restart kongtrade-bot, Logging in
  /var/log/kongtrade-deploy.log
- `/etc/systemd/system/kongtrade-deploy.service` — Type=oneshot,
  Environment=HOME=/root (kritisch für git-credentials)
- `/etc/systemd/system/kongtrade-deploy.timer` — OnBootSec=2min,
  OnUnitActiveSec=5min

Remote-URL enthält embedded PAT weil systemd kein TTY hat
und interaktive Username-Prompts nicht funktionieren.

Verifikations-Commands:
```
systemctl list-timers | grep kongtrade-deploy
tail -f /var/log/kongtrade-deploy.log
cat /var/log/kongtrade-deploy.log
```

Erster Live-Test am 18.04.2026 11:39 UTC erfolgreich
(857d82b → 5c8cfb5, Bot-Restart in 1 Sekunde).

## Signal-Flow

Polymarket Data-API (Poll 10s) → WalletMonitor → TradeSignal → 
CopyTrading Buffer 60s → Multiplier-Berechnung → RiskManager-Checks → 
ExecutionEngine → CLOB API → On-Chain via Proxy → FillTracker 
WebSocket MATCHED/CONFIRMED → Position promoted.

## Balance-Flow

On-Chain USDC.e → balance_fetcher.py Multi-RPC:
- ankr.com/polygon (primär, oft 0)
- polygon-bor-rpc.publicnode.com (Fallback)
- polygon-rpc.com
- 1rpc.io/matic

## API-Wissen

- CLOB API nutzen: https://clob.polymarket.com/markets/{conditionId}
- Gamma API NICHT für conditionId-Lookup (liefert falsche Märkte)
- Data API: https://data-api.polymarket.com/activity?user=0x...

## Dashboard-API für Chat-Claude

URL in STATUS.md unter "Dashboard-URL" (ändert sich bei Tunnel-Restart).

- GET /api/summary — Kennzahlen
- GET /api/logs?n=N — Log-Zeilen (bis ~500)
- GET /api/positions, /signals, /decisions, /resolutions, /portfolio

Chat-Claude fetcht via Exa.

## VPN / Geoblock-Regeln

- Hetzner Helsinki direkt: OK (Bot)
- Finnland-VPN: BLOCKED (UI)
- Norwegen-VPN: OK (UI + Recovery)
- ExpressVPN US: BLOCKED

## Wichtige Lessons Learned

- Proxy-Deploy Catch-22 (P004): Erster Trade via polymarket.com mit 
  Norwegen-VPN, $1
- Ghost-Trades (P008): create_and_post_order in EINEM Call
- L2-Credentials (P001): FillTracker braucht derived L2 (Issue #303)
- Min-Size pro Markt: NEGRISK anders, via Orderbook abfragen
- Stale token_id (P029): Recovery-Positions ohne token_id filtern

Siehe KNOWLEDGE_BASE.md für alle P001-P029+ Einträge.

Ende ARCHITECTURE.md.
