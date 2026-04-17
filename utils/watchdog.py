"""
utils/watchdog.py — Bot Offline Detection & Auto-Restart

Runs as a separate process (via watchdog.bat).
Checks heartbeat.txt every 2 minutes.
If heartbeat is older than 10 minutes → Telegram alert + auto-restart.
"""

import os
import sys
import time
import subprocess
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).resolve().parent.parent
HEARTBEAT_FILE  = BASE_DIR / "heartbeat.txt"
BOT_SCRIPT      = BASE_DIR / "main.py"
PYTHON_EXE      = sys.executable          # same python that runs watchdog
CHECK_INTERVAL  = 120                     # check every 2 minutes
MAX_OFFLINE_AGE = 600                     # alert if heartbeat > 10 min old
RESTART_COOLDOWN = 180                    # don't restart more often than 3 min

# Load Telegram credentials from .env
def _load_env():
    env_file = BASE_DIR / ".env"
    result = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                result[k.strip()] = v.strip().strip('"').strip("'")
    return result


_env = _load_env()
TELEGRAM_TOKEN   = _env.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = _env.get("TELEGRAM_CHAT_ID", "")


def _send_telegram(text: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[watchdog] Telegram not configured — skipping alert")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"[watchdog] Telegram send failed: {e}")


def _read_heartbeat() -> datetime | None:
    if not HEARTBEAT_FILE.exists():
        return None
    try:
        raw = HEARTBEAT_FILE.read_text(encoding="utf-8").strip()
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _is_bot_running() -> bool:
    """Check if any python process is running main.py."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
            capture_output=True, text=True, timeout=5
        )
        return "python.exe" in result.stdout
    except Exception:
        return False


def _start_bot() -> bool:
    try:
        subprocess.Popen(
            [PYTHON_EXE, str(BOT_SCRIPT)],
            cwd=str(BASE_DIR),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        print(f"[watchdog] Bot gestartet: {PYTHON_EXE} {BOT_SCRIPT}")
        return True
    except Exception as e:
        print(f"[watchdog] Neustart fehlgeschlagen: {e}")
        return False


def run():
    print(f"[watchdog] Gestartet — prüfe alle {CHECK_INTERVAL}s | Heartbeat: {HEARTBEAT_FILE}")
    _send_telegram("🐕 <b>KongTrade Watchdog gestartet</b>\nÜberwache Bot alle 2 Minuten.")

    last_restart = datetime.min.replace(tzinfo=timezone.utc)
    alert_sent   = False

    while True:
        now       = datetime.now(timezone.utc)
        heartbeat = _read_heartbeat()

        if heartbeat is None:
            age_s = float("inf")
            age_str = "unbekannt (heartbeat.txt fehlt)"
        else:
            age_s   = (now - heartbeat).total_seconds()
            age_str = heartbeat.strftime("%H:%M:%S UTC")

        if age_s > MAX_OFFLINE_AGE:
            print(f"[watchdog] ⚠️  Bot offline seit {age_s/60:.1f} min (letzter Heartbeat: {age_str})")

            if not alert_sent:
                _send_telegram(
                    f"🚨 <b>ALARM: KongTrade Bot ist OFFLINE!</b>\n"
                    f"Letzter Heartbeat: <code>{age_str}</code>\n"
                    f"Starte Bot automatisch neu..."
                )
                alert_sent = True

            # Auto-restart (max once per RESTART_COOLDOWN)
            cooldown_elapsed = (now - last_restart).total_seconds()
            if cooldown_elapsed > RESTART_COOLDOWN:
                success = _start_bot()
                last_restart = now
                if success:
                    _send_telegram("✅ <b>Bot neu gestartet!</b> Warte auf ersten Heartbeat...")
                    alert_sent = False  # reset — next check will confirm
                else:
                    _send_telegram("❌ <b>Automatischer Neustart fehlgeschlagen.</b> Bitte manuell prüfen!")
            else:
                remaining = int(RESTART_COOLDOWN - cooldown_elapsed)
                print(f"[watchdog] Warte noch {remaining}s vor erneutem Neustart-Versuch")
        else:
            if alert_sent:
                # Bot came back online
                _send_telegram(f"✅ <b>Bot ist wieder ONLINE!</b> Heartbeat empfangen: <code>{age_str}</code>")
                alert_sent = False
            print(f"[watchdog] ✅ Bot OK — letzter Heartbeat: {age_str} ({age_s:.0f}s ago)")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run()
