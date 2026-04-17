#!/bin/bash
# ============================================================
# start_live.sh — Polymarket Bot: Live-Trading Starter
# Prüft VPN, Umgebung und startet den Bot sicher
# ============================================================

set -e

BOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$HOME/trading-bot/venv/bin/python"
LOG_DIR="$BOT_DIR/logs"
ENV_FILE="$BOT_DIR/.env.live"

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "============================================================"
echo "  POLYMARKET BOT — LIVE TRADING START"
echo "============================================================"
echo ""

# --- 1. .env.live prüfen ---
echo "[1/5] Konfigurationsdatei prüfen..."
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}FEHLER: $ENV_FILE nicht gefunden!${NC}"
    echo "Kopiere .env.live in das Bot-Verzeichnis: $BOT_DIR"
    exit 1
fi

# Sicherstellen dass DRY_RUN=false gesetzt ist
DRY_RUN_VAL=$(grep "^DRY_RUN=" "$ENV_FILE" | cut -d'=' -f2 | tr -d ' \r')
if [ "$DRY_RUN_VAL" != "false" ]; then
    echo -e "${YELLOW}WARNUNG: DRY_RUN=$DRY_RUN_VAL — Bot läuft im Simulation-Modus!${NC}"
    echo "Setze DRY_RUN=false in $ENV_FILE für echtes Trading."
else
    echo -e "${GREEN}✓ DRY_RUN=false — LIVE TRADING AKTIV${NC}"
fi

# --- 2. Python/Venv prüfen ---
echo ""
echo "[2/5] Python-Umgebung prüfen..."
if [ ! -f "$VENV_PYTHON" ]; then
    # Fallback: system python3
    VENV_PYTHON="$(which python3)"
    echo -e "${YELLOW}Venv nicht gefunden, nutze: $VENV_PYTHON${NC}"
else
    echo -e "${GREEN}✓ Venv: $VENV_PYTHON${NC}"
fi

PYTHON_VERSION=$("$VENV_PYTHON" --version 2>&1)
echo -e "${GREEN}✓ $PYTHON_VERSION${NC}"

# --- 3. VPN-Verbindung prüfen ---
echo ""
echo "[3/5] VPN-Verbindung prüfen..."

VPN_OK=false

# Methode A: WireGuard Interface
if ip link show wg0 &>/dev/null 2>&1; then
    WG_STATUS=$(ip link show wg0 | grep -c "UP" || true)
    if [ "$WG_STATUS" -gt 0 ]; then
        VPN_IP=$(ip addr show wg0 2>/dev/null | grep "inet " | awk '{print $2}' | head -1)
        echo -e "${GREEN}✓ WireGuard VPN aktiv (wg0) — IP: $VPN_IP${NC}"
        VPN_OK=true
    fi
fi

# Methode B: OpenVPN Interface (tun0)
if [ "$VPN_OK" = false ] && ip link show tun0 &>/dev/null 2>&1; then
    TUN_STATUS=$(ip link show tun0 | grep -c "UP" || true)
    if [ "$TUN_STATUS" -gt 0 ]; then
        VPN_IP=$(ip addr show tun0 2>/dev/null | grep "inet " | awk '{print $2}' | head -1)
        echo -e "${GREEN}✓ OpenVPN aktiv (tun0) — IP: $VPN_IP${NC}"
        VPN_OK=true
    fi
fi

# Methode C: Externe IP prüfen (kein US/Polymarket-geblockte Region)
if [ "$VPN_OK" = false ]; then
    EXTERNAL_IP=$(curl -s --max-time 5 https://api.ipify.org 2>/dev/null || echo "unbekannt")
    echo -e "${YELLOW}⚠ Kein VPN-Interface gefunden. Externe IP: $EXTERNAL_IP${NC}"
    echo ""
    echo "  Optionen:"
    echo "  a) Ohne VPN fortfahren (wenn Server-Standort kein Problem)"
    echo "  b) WireGuard starten: sudo wg-quick up wg0"
    echo "  c) OpenVPN starten:   sudo openvpn --config /etc/openvpn/client.ovpn --daemon"
    echo ""
    read -p "Ohne VPN fortfahren? (j/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Jj]$ ]]; then
        echo "Bot-Start abgebrochen. VPN zuerst verbinden."
        exit 1
    fi
    echo -e "${YELLOW}Fortfahren ohne VPN...${NC}"
fi

# --- 4. Polymarket API-Erreichbarkeit prüfen ---
echo ""
echo "[4/5] Polymarket API prüfen..."
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "https://clob.polymarket.com" 2>/dev/null || echo "000")

if [ "$API_STATUS" = "200" ] || [ "$API_STATUS" = "404" ] || [ "$API_STATUS" = "405" ]; then
    echo -e "${GREEN}✓ Polymarket CLOB API erreichbar (HTTP $API_STATUS)${NC}"
elif [ "$API_STATUS" = "000" ]; then
    echo -e "${RED}FEHLER: Polymarket API nicht erreichbar (Timeout)${NC}"
    echo "Prüfe Internetverbindung und VPN-Einstellungen."
    exit 1
else
    echo -e "${YELLOW}⚠ Polymarket API antwortet mit HTTP $API_STATUS — mit Vorsicht fortfahren${NC}"
fi

# --- 5. Bot starten ---
echo ""
echo "[5/5] Bot starten..."
mkdir -p "$LOG_DIR"

# .env.live als .env verwenden
cp "$ENV_FILE" "$BOT_DIR/.env"

echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  BOT STARTET — LIVE TRADING${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo "Logs:     $LOG_DIR/"
echo "Stoppen:  Ctrl+C"
echo ""
echo "Zum Stoppen im Hintergrund: kill \$(cat $BOT_DIR/bot.pid)"
echo ""

# Im Vordergrund starten (für tmux/screen Nutzung empfohlen)
# PID speichern
cd "$BOT_DIR"
"$VENV_PYTHON" main.py --live &
BOT_PID=$!
echo $BOT_PID > "$BOT_DIR/bot.pid"
echo "Bot PID: $BOT_PID (gespeichert in bot.pid)"

wait $BOT_PID
