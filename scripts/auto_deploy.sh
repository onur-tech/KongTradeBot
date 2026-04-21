#!/bin/bash
set -e
cd /root/KongTradeBot
LOG=/var/log/kongtrade-deploy.log

git fetch origin main 2>>"$LOG"

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    exit 0
fi

echo "[$(date -Iseconds)] Update: $LOCAL -> $REMOTE" >> "$LOG"
git pull origin main --ff-only >> "$LOG" 2>&1
systemctl restart kongtrade-bot
echo "[$(date -Iseconds)] Bot restarted at $REMOTE" >> "$LOG"
