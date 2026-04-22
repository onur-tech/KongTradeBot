#!/bin/bash
set -e
cd /root/status-repo
cp /home/claudeuser/KongTradeBot/TASKS.md .
cp /home/claudeuser/KongTradeBot/KNOWLEDGE_BASE.md .
python3 /home/claudeuser/KongTradeBot/scripts/generate_status.py
git add -A
git diff --cached --quiet || git commit -m "Auto-update $(date -u +%Y-%m-%dT%H:%M:%SZ)" && git push origin main
