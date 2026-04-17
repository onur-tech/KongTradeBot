# LIVE_SETUP.md — Polymarket Bot: NiPoGi Server Setup

Schritt-für-Schritt Anleitung für den Betrieb auf dem NiPoGi Ubuntu-Server.

---

## Voraussetzungen

- NiPoGi Mini PC mit Ubuntu 22.04 LTS
- SSH-Zugang zum Server
- Polymarket-Wallet mit USDC auf Polygon
- (Optional) VPN-Konfigurationsdatei (.ovpn oder WireGuard .conf)

---

## Schritt 1: Mit Server verbinden

```bash
ssh user@<SERVER-IP>
```

IP-Adresse des NiPoGi im lokalen Netz herausfinden:
```bash
# Am Server selbst:
hostname -I
```

---

## Schritt 2: Setup-Script ausführen

Bot-Dateien auf den Server kopieren (von Windows aus):

```bash
# Von Windows PowerShell:
scp -r "C:\Users\OnurAribas\Downloads\Trading Bot\Trading Bot\Trading Bot\*" user@<SERVER-IP>:~/trading-bot/app/
```

Dann auf dem Server:

```bash
cd ~/trading-bot/app
chmod +x setup_server.sh start_live.sh
bash setup_server.sh
```

Das Script installiert automatisch:
- Python 3.11 + Virtualenv
- alle pip-Pakete (py-clob-client, aiohttp, web3, anthropic, ...)
- OpenVPN + WireGuard
- UFW Firewall (nur SSH erlaubt eingehend)
- systemd Service (für Autostart)

---

## Schritt 3: VPN einrichten

### Option A — WireGuard (empfohlen, schneller)

```bash
# WireGuard-Config auf Server kopieren (von Windows):
scp wireguard.conf user@<SERVER-IP>:/etc/wireguard/wg0.conf

# VPN starten:
sudo wg-quick up wg0

# Beim Systemstart automatisch starten:
sudo systemctl enable wg-quick@wg0

# Status prüfen:
sudo wg show
```

### Option B — OpenVPN

```bash
# .ovpn-Datei auf Server kopieren:
scp client.ovpn user@<SERVER-IP>:/etc/openvpn/client.ovpn

# VPN starten:
sudo openvpn --config /etc/openvpn/client.ovpn --daemon

# Beim Systemstart automatisch:
sudo systemctl enable openvpn@client

# Status prüfen:
curl https://api.ipify.org   # sollte VPN-IP zeigen
```

### VPN-Verbindung testen

```bash
curl https://api.ipify.org        # externe IP anzeigen
curl https://clob.polymarket.com  # sollte erreichbar sein
```

---

## Schritt 4: Live-Konfiguration einrichten

```bash
cd ~/trading-bot/app

# .env.live ist bereits vorhanden — Private Key und Adressen kontrollieren:
nano .env.live
```

Wichtige Werte in `.env.live` für den Start:

| Variable | Wert | Bedeutung |
|---|---|---|
| `DRY_RUN` | `false` | Echtes Trading aktiv |
| `MAX_DAILY_LOSS_USD` | `10` | Bot stoppt nach $10 Verlust/Tag |
| `MAX_TRADE_SIZE_USD` | `2` | Max $2 pro Trade |
| `COPY_SIZE_MULTIPLIER` | `0.001` | 0.1% der Whale-Position |
| `MIN_TRADE_SIZE_USD` | `0.50` | Trades unter $0.50 ignorieren |
| `PORTFOLIO_BUDGET_USD` | `100` | Budget für Positionsberechnung |

> **Tipp:** Nach 1 Woche erfolgreichem Betrieb `MAX_TRADE_SIZE_USD` auf $5 und `MAX_DAILY_LOSS_USD` auf $25 erhöhen.

---

## Schritt 5: Bot starten

### Empfohlen: Mit tmux (Bot läuft weiter nach SSH-Trennung)

```bash
# Neue tmux-Session:
tmux new -s polybot

# Bot starten:
cd ~/trading-bot/app
bash start_live.sh

# Session verlassen (Bot läuft weiter):
# Ctrl+B, dann D

# Session wieder öffnen:
tmux attach -t polybot
```

### Alternativ: Mit screen

```bash
screen -S polybot
bash start_live.sh
# Ctrl+A, dann D zum Trennen
screen -r polybot  # Wieder öffnen
```

### Als systemd Service (Autostart nach Reboot)

```bash
# Service starten:
sudo systemctl start polymarket-bot
sudo systemctl enable polymarket-bot  # Autostart aktivieren

# Logs verfolgen:
sudo journalctl -u polymarket-bot -f

# Status prüfen:
sudo systemctl status polymarket-bot
```

---

## Schritt 6: Bot überwachen

### Logs live verfolgen

```bash
# Neueste Log-Datei:
tail -f ~/trading-bot/app/logs/bot_$(date +%Y-%m-%d).log

# Nur Fehler und Trades:
tail -f ~/trading-bot/app/logs/bot_$(date +%Y-%m-%d).log | grep -E "ERROR|WARNING|TRADE|✅|❌|💰"
```

### Telegram-Befehle

Der Bot antwortet auf diese Telegram-Nachrichten:
- `/status` — aktueller Status, PnL, offene Positionen
- `/balance` — USDC-Kontostand
- `/stop` — Bot stoppen (Kill-Switch)

---

## Schritt 7: Bot stoppen

```bash
# Sanft stoppen (wartet auf sauberes Shutdown):
kill $(cat ~/trading-bot/app/bot.pid)

# Oder via systemd:
sudo systemctl stop polymarket-bot

# Sofort stoppen:
pkill -f "python.*main.py"
```

---

## Wichtige Dateien auf dem Server

```
~/trading-bot/
├── app/                    ← Bot-Code
│   ├── main.py
│   ├── .env                ← Aktive Konfiguration (Kopie von .env.live)
│   ├── .env.live           ← Live-Konfiguration
│   ├── start_live.sh       ← Start-Script
│   ├── bot.pid             ← Prozess-ID (wird automatisch erstellt)
│   ├── bot_state.json      ← Persistenter Bot-Zustand
│   ├── trades_archive.json ← Alle Trades
│   └── logs/               ← Log-Dateien
└── venv/                   ← Python Virtual Environment
```

---

## Häufige Probleme

### "py-clob-client" Installation schlägt fehl
```bash
pip install --upgrade pip setuptools wheel
pip install py-clob-client --no-cache-dir
```

### VPN trennt sich nach Idle
```bash
# WireGuard Keepalive aktivieren (in /etc/wireguard/wg0.conf):
# PersistentKeepalive = 25
sudo wg-quick down wg0 && sudo wg-quick up wg0
```

### Bot startet aber macht keine Trades
1. `DRY_RUN=false` in `.env` prüfen
2. Logs auf "Schließzeit unbekannt" prüfen → normal, API-seitig
3. Logs auf "Trade erlaubt" prüfen → falls vorhanden aber kein Trade: ExecutionEngine prüfen
4. `POLYMARKET_ADDRESS` korrekt? → `wallet_check.py` ausführen

### Balance zeigt $0.00
```bash
python wallet_check.py  # Wallet-Balance direkt prüfen
```
Wenn $0.00: USDC auf Polygon-Netzwerk fehlt. Auf Polygon Chain (nicht Ethereum!) überweisen.

---

## Skalierungs-Roadmap

| Phase | Woche | MAX_TRADE | MAX_DAILY_LOSS | MULTIPLIER |
|---|---|---|---|---|
| Test | 1–2 | $2 | $10 | 0.001 |
| Aufbau | 3–4 | $5 | $25 | 0.002 |
| Normal | 5+ | $10 | $50 | 0.005 |
| Aggressiv | 8+ | $25 | $100 | 0.02 |

Nur erhöhen wenn die vorherige Phase profitabel war!
