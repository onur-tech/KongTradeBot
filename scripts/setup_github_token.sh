#!/bin/bash
# setup_github_token.sh — Setzt GitHub-Token aus .env in die Remote-URL
# Aufruf: bash /home/claudeuser/KongTradeBot/scripts/setup_github_token.sh

ENV_FILE="/home/claudeuser/KongTradeBot/.env"
STATUS_REPO="/root/status-repo"

# Token aus .env lesen
GITHUB_TOKEN=$(grep -E "^GITHUB_TOKEN=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'")

if [ -z "$GITHUB_TOKEN" ]; then
    echo "FEHLER: GITHUB_TOKEN nicht in $ENV_FILE gefunden."
    echo ""
    echo "Bitte folgende Zeile in .env eintragen:"
    echo "  GITHUB_TOKEN=ghp_deinTokenHier"
    echo ""
    echo "Token erstellen unter: https://github.com/settings/tokens"
    echo "Benötigte Scopes: repo (oder public_repo für public repos)"
    exit 1
fi

git config --global --add safe.directory "$STATUS_REPO" 2>/dev/null || true

CURRENT=$(git -C "$STATUS_REPO" remote get-url origin 2>/dev/null || echo "")
REPO_PATH=$(echo "$CURRENT" | sed 's|https://github.com/||' | sed 's|https://.*@github.com/||')

if [ -z "$REPO_PATH" ]; then
    echo "FEHLER: Kein origin-Remote in $STATUS_REPO gefunden."
    exit 1
fi

NEW_URL="https://${GITHUB_TOKEN}@github.com/${REPO_PATH}"
git -C "$STATUS_REPO" remote set-url origin "$NEW_URL"

echo "GitHub-Token gesetzt: $STATUS_REPO → github.com/$REPO_PATH"
echo "Test-Push..."
git -C "$STATUS_REPO" push --dry-run origin main 2>&1 && echo "Token OK — Push funktioniert." || echo "FEHLER: Push fehlgeschlagen. Token prüfen."
