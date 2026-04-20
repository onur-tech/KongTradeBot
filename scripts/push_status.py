"""
Stündlicher Status-Push in öffentliches GitHub Repo.
Nur öffentliche Daten — keine Secrets, keine Keys.
Claude.ai kann dann direkt darauf zugreifen.
"""
import json, subprocess, os, glob
from datetime import datetime, timezone

STATUS_REPO_PATH = "/root/kongtrade-status"
STATUS_FILE = f"{STATUS_REPO_PATH}/status.json"

def get_bot_status():
    now = datetime.now(timezone.utc).isoformat()

    # Bot läuft?
    result = subprocess.run(
        ["systemctl", "is-active", "kongtrade-bot"],
        capture_output=True, text=True)
    bot_running = result.stdout.strip() == "active"

    log_file = f"/root/KongTradeBot/logs/bot_{datetime.now().strftime('%Y-%m-%d')}.log"
    trades_today = buys = sells = errors = rss = weather = sl = whale = restarts = 0
    ws_status = "unknown"
    last_trade = last_error = None

    if os.path.exists(log_file):
        with open(log_file) as f:
            lines = f.readlines()
        for line in lines:
            if "CopyOrder[LIVE]" in line:
                trades_today += 1
                if "BUY" in line: buys += 1
                if "SELL" in line: sells += 1
                last_trade = line[:19]
            if "ERROR" in line or "CRITICAL" in line:
                errors += 1
                last_error = line[20:100]
            if "[WS] Subscribed" in line: ws_status = "connected"
            if "[WS] Disconnect" in line: ws_status = "disconnected"
            if "[RSS]" in line and "Signal" in line: rss += 1
            if "[WeatherScout]" in line and "Opportunit" in line: weather += 1
            if "stop_loss" in line.lower() or "EXIT_SL" in line: sl += 1
            if "whale_exit_copy" in line.lower() or "WHALE EXIT" in line: whale += 1
            if "Started kongtrade" in line: restarts += 1

    return {
        "timestamp": now,
        "bot_running": bot_running,
        "trades_today": trades_today,
        "buys_today": buys,
        "sells_today": sells,
        "errors_today": errors,
        "last_trade_time": last_trade,
        "last_error": last_error,
        "ws_status": ws_status,
        "rss_signals_today": rss,
        "weather_opportunities": weather,
        "stop_loss_triggered": sl,
        "whale_exit_triggered": whale,
        "restarts_today": restarts
    }

def push_status():
    status = get_bot_status()
    os.makedirs(STATUS_REPO_PATH, exist_ok=True)
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)
    os.chdir(STATUS_REPO_PATH)
    subprocess.run(["git", "add", "status.json"])
    subprocess.run(["git", "commit", "-m",
        f"status: {status['timestamp'][:16]} | "
        f"trades={status['trades_today']} | "
        f"bot={'OK' if status['bot_running'] else 'DOWN'}"])
    result = subprocess.run(["git", "push"], capture_output=True, text=True)
    print(f"Push: {result.returncode} | {status}")

if __name__ == "__main__":
    push_status()
