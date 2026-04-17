#!/bin/bash
# ============================================================
# setup_server.sh — Polymarket Bot: Ubuntu Server Setup
# Getestet auf: Ubuntu 22.04 LTS (NiPoGi Mini PC)
# Ausführen mit: bash setup_server.sh
# ============================================================

set -e  # Abbruch bei erstem Fehler

echo "============================================================"
echo "  POLYMARKET BOT — SERVER SETUP"
echo "============================================================"

# --- 1. System Update ---
echo ""
echo "[1/8] System-Update..."
sudo apt-get update -qq
sudo apt-get upgrade -y -qq

# --- 2. Python 3.11 ---
echo ""
echo "[2/8] Python 3.11 installieren..."
sudo apt-get install -y -qq python3.11 python3.11-venv python3-pip python3.11-dev
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
echo "Python-Version: $(python3 --version)"

# --- 3. Basis-Tools ---
echo ""
echo "[3/8] Basis-Tools installieren..."
sudo apt-get install -y -qq \
    git curl wget unzip \
    build-essential libssl-dev libffi-dev \
    screen tmux \
    ufw fail2ban \
    net-tools

# --- 4. OpenVPN + WireGuard ---
echo ""
echo "[4/8] VPN-Clients installieren..."
sudo apt-get install -y -qq openvpn wireguard resolvconf

# NordVPN CLI (optional — auskommentieren wenn nicht benötigt)
# wget -qO /tmp/nordvpn-install.sh https://downloads.nordcdn.com/apps/linux/install.sh
# bash /tmp/nordvpn-install.sh

echo "VPN-Pakete installiert (OpenVPN + WireGuard)"

# --- 5. Firewall konfigurieren ---
echo ""
echo "[5/8] Firewall (UFW) konfigurieren..."
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw --force enable
echo "Firewall aktiv. Status:"
sudo ufw status

# --- 6. Virtualenv erstellen ---
echo ""
echo "[6/8] Python Virtual Environment erstellen..."
BOT_DIR="$HOME/trading-bot"
mkdir -p "$BOT_DIR"

if [ ! -d "$BOT_DIR/venv" ]; then
    python3 -m venv "$BOT_DIR/venv"
    echo "Venv erstellt: $BOT_DIR/venv"
else
    echo "Venv existiert bereits, übersprungen."
fi

# Aktivieren
source "$BOT_DIR/venv/bin/activate"

# --- 7. Python-Pakete installieren ---
echo ""
echo "[7/8] Python-Abhängigkeiten installieren..."
pip install --upgrade pip -q

# py-clob-client zuerst (kritisch, manchmal Konflikte)
pip install py-clob-client>=0.16.0

# Restliche Pakete
pip install \
    aiohttp>=3.9.0 \
    websockets>=12.0 \
    python-dateutil>=2.8.2 \
    python-dotenv>=1.0.0 \
    web3>=6.0.0 \
    typing-extensions>=4.0.0 \
    anthropic>=0.40.0

echo "Pakete installiert:"
pip list | grep -E "clob|aiohttp|web3|anthropic|dotenv"

# --- 8. systemd Service einrichten ---
echo ""
echo "[8/8] systemd Service erstellen..."

sudo tee /etc/systemd/system/polymarket-bot.service > /dev/null << EOF
[Unit]
Description=Polymarket Copy Trading Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BOT_DIR/app
ExecStart=$BOT_DIR/venv/bin/python main.py --live
Restart=on-failure
RestartSec=30
StandardOutput=append:$BOT_DIR/app/logs/service.log
StandardError=append:$BOT_DIR/app/logs/service.log
Environment="PATH=$BOT_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
echo "Service registriert (noch nicht gestartet)"

# --- Fertig ---
echo ""
echo "============================================================"
echo "  SETUP ABGESCHLOSSEN"
echo "============================================================"
echo ""
echo "Nächste Schritte:"
echo "  1. Bot-Dateien nach $BOT_DIR/app/ kopieren"
echo "  2. .env.live nach $BOT_DIR/app/.env kopieren"
echo "  3. VPN verbinden (siehe LIVE_SETUP.md)"
echo "  4. Bot starten: bash $BOT_DIR/app/start_live.sh"
echo ""
echo "Bot-Verzeichnis: $BOT_DIR/app/"
echo "Venv aktivieren: source $BOT_DIR/venv/bin/activate"
