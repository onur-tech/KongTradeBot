# KongTradeBot — Setup & Schnellreferenz
_Stand: 18.04.2026_

## Projektziel

Polymarket Copy Trading Bot. Kopiert 11 profitable Whale-Wallets in 
reduzierter Größe. Live seit 17.04.2026.

## Aktueller Stand

- Bot läuft LIVE auf Hetzner Helsinki VPS (89.167.29.183)
- USDC.e Balance Proxy: 629 USD
- Defensive Config nach 137 USD Verlust (Multiplier 0.05, MAX_POS=15)
- Dashboard via Cloudflare Quick Tunnel (URL wechselt, siehe STATUS.md)
- Telegram: @Kong_polymarket_bot
- Chat-IDs: Onur (507270873), Alex read-only (7777386792)

## Server

- Host: Hetzner CAX11 ARM64, Helsinki
- IP: 89.167.29.183
- OS: Ubuntu 24.04, Python 3.12
- Pfad: /root/KongTradeBot/
- SSH: ssh root@89.167.29.183

## Systemd-Services

- kongtrade-bot.service — Bot (Restart=always)
- kongtrade-watchdog.timer — 60s Health-Check
- kongtrade-tunnel.service — Cloudflare Tunnel
- kongtrade-tunnel-watcher.timer — URL-Change-Alert 5min
- kongtrade-status.timer — Auto-Push STATUS.md (AUS, Warm-Start)
- kongtrade-tax-export.timer — Wöchentlicher CSV-Export (Freitag 23:55)

## Tax-Exports herunterladen

Exports liegen auf dem Server unter `/root/KongTradeBot/exports/`:
```
scp root@89.167.29.183:/root/KongTradeBot/exports/tax_2026_KW*.csv .
scp root@89.167.29.183:/root/KongTradeBot/exports/blockpit_2026_KW*.csv .
```
Formate: `tax_YYYY_KWWW.csv` (Deutsch, semicolon, EUR) + `blockpit_YYYY_KWWW.csv` (Blockpit-Import)

## Wallet-Architektur (Kurzfassung)

- Magic-EOA: 0xd7869A5Cae59FDb6ab306ab332a9340AceC8cbE2 (signiert)
- Polymarket-Proxy: 0x700BC51b721F168FF975ff28942BC0E5fAF945eb (hält USDC.e)
- Profile-Address: 0x3e328A8b896D5ABEC5043E193Dc8045Dc7d3Ed31 (stuck)
- signature_type = 1 (POLY_PROXY / Magic-Link)

Details siehe ARCHITECTURE.md.

## Commands

Bot Status
systemctl status kongtrade-bot
Bot Restart
systemctl restart kongtrade-bot
Logs live
journalctl -u kongtrade-bot -f
Bot stoppen
systemctl stop kongtrade-bot
Status manuell pushen
bash /root/KongTradeBot/scripts/push_status.sh
Dashboard-URL finden
journalctl -u kongtrade-tunnel | grep trycloudflare | tail -1

## Repos

- https://github.com/onur-tech/KongTradeBot (öffentlich, Doku + Status)
- https://github.com/onur-tech/KongTradeBot-src (privat, Source-Code)

## Git-Workflow (ab 18.04.2026)

- **onur-tech/KongTradeBot** (öffentlich) — Docs (MD-Dateien), STATUS, Bootstrap
- **onur-tech/KongTradeBot-src** (privat) — Source-Code, Single-Source-of-Truth für Bot

**Entwicklungsfluss:**
1. Windows-CC arbeitet in
   `C:\Users\OnurAribas\Downloads\Trading Bot\Trading Bot\Trading Bot`
2. `git add / commit / git push origin main`
   (origin = KongTradeBot-src)
3. GitHub empfängt Push
4. Hetzner-Timer kongtrade-deploy.timer triggered alle 5 Min
5. Bei Änderung: pull + systemctl restart kongtrade-bot
6. Live binnen 5 Min

**Manuelle Interventionen (nur Notfall):**
```
ssh root@89.167.29.183
cd /root/KongTradeBot
systemctl start kongtrade-deploy.service  # sofort triggern
```

## Arbeitsweise

Chat-Claude liest beim Start automatisch 9 Files via SKILL.md Bootstrap.
Arbeitsteilung: Chat = Denken, Claude Code = Machen.
Details in GUIDELINES.md.

Ende SETUP.md.
