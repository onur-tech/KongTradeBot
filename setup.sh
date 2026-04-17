#!/bin/bash
# ============================================================
# setup.sh — Server-Einrichtung für den Polymarket Bot
# ============================================================
# Ausführen mit:
#   chmod +x setup.sh
#   ./setup.sh
# ============================================================

set -e  # Bei Fehler sofort stoppen

echo ""
echo "🤖 POLYMARKET BOT — SERVER SETUP"
echo "================================="
echo ""

# Python prüfen
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 nicht gefunden. Installiere es zuerst:"
    echo "   sudo apt update && sudo apt install python3 python3-pip -y"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python $PYTHON_VERSION gefunden"

# pip prüfen
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 nicht gefunden"
    echo "   sudo apt install python3-pip -y"
    exit 1
fi

echo ""
echo "📦 Installiere Abhängigkeiten..."
pip3 install -r requirements.txt --quiet

echo "✅ Abhängigkeiten installiert"

echo ""
echo "⚙️  .env Konfiguration..."

if [ -f ".env" ]; then
    echo "✅ .env bereits vorhanden"
else
    cp .env.example .env
    echo "📝 .env aus Vorlage erstellt"
    echo ""
    echo "⚠️  JETZT AUSFÜLLEN:"
    echo "   nano .env"
    echo ""
    echo "Mindestens diese Felder setzen:"
    echo "   PRIVATE_KEY=0x..."
    echo "   POLYMARKET_ADDRESS=0x..."
    echo "   TARGET_WALLETS=0x..."
    echo ""
fi

echo ""
echo "🧪 Tests ausführen..."

if python3 tests/test_wallet_monitor.py 2>/dev/null | grep -q "Alle Tests bestanden"; then
    echo "✅ Wallet Monitor Tests: bestanden"
else
    echo "⚠️  Wallet Monitor Tests: Fehler (prüfe Ausgabe)"
    python3 tests/test_wallet_monitor.py
fi

if python3 tests/test_execution_engine.py 2>/dev/null | grep -q "bestanden"; then
    PASSED=$(python3 tests/test_execution_engine.py 2>/dev/null | grep "Ergebnis" | grep -o "[0-9]*/" | head -1)
    echo "✅ Execution Engine Tests: ${PASSED}4 bestanden"
fi

echo ""
echo "================================="
echo "🚀 SETUP ABGESCHLOSSEN"
echo ""
echo "Nächste Schritte:"
echo ""
echo "1. .env ausfüllen (falls noch nicht gemacht):"
echo "   nano .env"
echo ""
echo "2. Bot im Dry-Run starten (SICHER — kein echtes Geld):"
echo "   python3 main.py"
echo ""
echo "3. Bot live starten (ECHTES GELD):"
echo "   python3 main.py --live"
echo ""
echo "4. Als Service im Hintergrund laufen lassen:"
echo "   nohup python3 main.py > logs/bot.log 2>&1 &"
echo "   tail -f logs/bot.log"
echo ""
echo "⚠️  SICHERHEITS-CHECKLISTE:"
echo "   ✓ .env in .gitignore (bereits konfiguriert)"
echo "   ✓ Private Key nur in .env, niemals im Code"
echo "   ✓ Erst Dry-Run, dann Live"
echo "   ✓ Mit kleinem Kapital starten ($100)"
echo "================================="
