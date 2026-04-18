#!/bin/bash
set -e
cd /root/status-repo
cp /root/KongTradeBot/TASKS.md .
cp /root/KongTradeBot/KNOWLEDGE_BASE.md .
python3 /root/KongTradeBot/scripts/generate_status.py
git add -A
git diff --cached --quiet || git commit -m "Auto-update $(date -u +%Y-%m-%dT%H:%M:%SZ)" && git push origin main
