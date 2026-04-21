#!/usr/bin/env python3
"""Schreibt public_status.json für /status.json Endpoint — läuft alle 5 Min via Cron."""
import json, os, sys
import requests
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent.parent
OUT  = BASE / "public_status.json"

def load_env():
    env = {}
    try:
        for line in (BASE / ".env").read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return env

def read_log_tail(n=100):
    log = BASE / "logs" / "bot.log"
    try:
        return log.read_text(errors="replace").splitlines()[-n:]
    except Exception:
        return []

def main():
    env = load_env()
    lines = read_log_tail(200)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    ws_status = "unknown"
    rss_signals = 0
    errors = 0
    last_trade = None
    anomaly_active = False

    for line in lines:
        if "[WS] Subscribed" in line:     ws_status = "connected"
        if "[WS] Disconnect" in line:     ws_status = "disconnected"
        if "[RSS]" in line and "Signal" in line and line.startswith(today): rss_signals += 1
        if " ERROR " in line and line.startswith(today): errors += 1
        if ("CopyOrder[LIVE]" in line or "Order erstellt" in line) and line.startswith(today):
            last_trade = line[:19]
        if "[ANOMALY] Detektor gestartet" in line: anomaly_active = True

    # Heartbeat-Alter
    hb_age = None
    try:
        hb = (BASE / "heartbeat.txt").read_text().strip()
        from datetime import datetime as dt
        hb_ts = dt.fromisoformat(hb.replace("Z", "+00:00"))
        hb_age = int((datetime.now(timezone.utc) - hb_ts).total_seconds())
    except Exception:
        pass

    # Bot-Prozess
    bot_running = False
    try:
        import subprocess
        out = subprocess.check_output(["pgrep", "-f", "main.py"], text=True)
        bot_running = bool(out.strip())
    except Exception:
        pass

    portfolio_value = 0
    today_pnl = 0
    active_positions = 0
    try:
        r = requests.get("http://localhost:5000/internal/portfolio", timeout=5)
        p = r.json()
        portfolio_value = p.get("total_value", 0)
        today_pnl = p.get("today_pnl_portfolio", 0)
        active_positions = p.get("count", 0)
    except Exception:
        pass

    status = {
        "generated_at":    datetime.now(timezone.utc).isoformat(),
        "bot_running":     bot_running,
        "ws_status":       ws_status,
        "heartbeat_age_s": hb_age,
        "rss_signals_today": rss_signals,
        "errors_today":    errors,
        "last_trade":      last_trade,
        "anomaly_active":  anomaly_active,
        "dry_run":         env.get("DRY_RUN", "true") == "true",
        "weather_dry_run": env.get("WEATHER_DRY_RUN", "true") == "true",
        "max_daily_sell":  env.get("MAX_DAILY_SELL_USD", "200"),
        "portfolio_value": round(float(portfolio_value), 2),
        "today_pnl":       round(float(today_pnl), 2),
        "active_positions": active_positions,
    }

    OUT.write_text(json.dumps(status, indent=2))
    print(f"[status] Geschrieben: {OUT} ({len(json.dumps(status))} Bytes)")

if __name__ == "__main__":
    main()
