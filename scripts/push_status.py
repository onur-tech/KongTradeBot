#!/usr/bin/env python3
"""
push_status.py — Generates status.json and pushes to kongtrade-status repo.
Runs every 5 minutes via cron. Reads from dashboard API (localhost:5000).
"""
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

STATUS_REPO = "/root/kongtrade-status"
STATUS_FILE = os.path.join(STATUS_REPO, "status.json")


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_json(path, timeout=5):
    try:
        req = urllib.request.Request(
            f"http://localhost:5000{path}",
            headers={"User-Agent": "StatusBot/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def get_service_state():
    try:
        r = subprocess.run(
            ["systemctl", "show", "kongtrade-bot",
             "--property=ActiveState,SubState,ExecMainStartTimestamp"],
            capture_output=True, text=True
        )
        props = dict(l.split("=", 1) for l in r.stdout.strip().splitlines() if "=" in l)
        state = props.get("ActiveState", "?")
        sub = props.get("SubState", "?")
        return "running" if state == "active" and sub == "running" else f"{state}/{sub}"
    except Exception:
        return "unknown"


def get_heartbeat_age():
    hb = "/home/claudeuser/KongTradeBot/heartbeat.txt"
    if not os.path.exists(hb):
        return None
    return int(datetime.now().timestamp() - os.path.getmtime(hb))


portfolio = fetch_json("/api/portfolio")
balance = fetch_json("/api/balance")

status = {
    "updated_at": utc_now(),
    "bot_state": get_service_state(),
    "heartbeat_age_s": get_heartbeat_age(),
    "cash_usdc": balance.get("cash") if "error" not in balance else None,
    "portfolio_value_usdc": portfolio.get("total_value") if "error" not in portfolio else None,
    "open_positions": portfolio.get("count") if "error" not in portfolio else None,
    "dashboard_error": portfolio.get("error"),
}

os.makedirs(STATUS_REPO, exist_ok=True)
with open(STATUS_FILE, "w") as f:
    json.dump(status, f, indent=2)

print(f"[push_status] status.json geschrieben: bot={status['bot_state']}, "
      f"cash=${status['cash_usdc']}, hb={status['heartbeat_age_s']}s")

# Git push
try:
    subprocess.run(["git", "-C", STATUS_REPO, "add", "status.json"], check=True)
    result = subprocess.run(
        ["git", "-C", STATUS_REPO, "diff", "--cached", "--quiet"]
    )
    if result.returncode != 0:
        subprocess.run(
            ["git", "-C", STATUS_REPO, "commit", "-m",
             f"status: {utc_now()}"],
            check=True
        )
        subprocess.run(["git", "-C", STATUS_REPO, "push"], check=True)
        print("[push_status] GitHub Push OK")
    else:
        print("[push_status] Keine Änderung — kein Push")
except subprocess.CalledProcessError as e:
    print(f"[push_status] Git-Fehler: {e}", file=sys.stderr)
    sys.exit(1)
