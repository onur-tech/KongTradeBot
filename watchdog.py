"""
watchdog.py — KongTrade Bot Watchdog
Prüft Heartbeat, schickt Telegram-Alert bei Problemen, 
kann Bot via systemctl neustarten.
"""
import os
import sys
import time
import subprocess
import psutil
import requests
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / '.env')

HEARTBEAT_FILE = BASE_DIR / 'heartbeat.txt'
HEARTBEAT_MAX_AGE = 600  # Sekunden

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
CHAT_IDS = [cid.strip() for cid in os.getenv('TELEGRAM_CHAT_IDS', '507270873').split(',')]

def send_telegram(msg: str):
    if not TELEGRAM_TOKEN:
        print(f'[Watchdog] No Telegram token, would send: {msg}')
        return
    for chat_id in CHAT_IDS:
        try:
            requests.post(
                f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
                json={'chat_id': chat_id, 'text': msg, 'parse_mode': 'HTML'},
                timeout=10,
            )
        except Exception as e:
            print(f'[Watchdog] Telegram error: {e}')

def get_service_status(service: str) -> str:
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', service],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip()
    except Exception:
        return 'unknown'

def cleanup_stale_lock():
    """Entfernt stale bot.lock wenn der Prozess darin nicht mehr existiert."""
    lock_file = BASE_DIR / "bot.lock"
    if lock_file.exists():
        try:
            pid = int(lock_file.read_text().strip())
            if not psutil.pid_exists(pid):
                lock_file.unlink()
                print(f"[Watchdog] Stale lock removed (PID {pid} tot)")
                return True
        except (ValueError, OSError):
            try:
                lock_file.unlink()
                print("[Watchdog] Korrupte lock removed")
            except OSError:
                pass
            return True
    return False


def restart_bot():
    try:
        subprocess.run(['systemctl', 'restart', 'kongtrade-bot'], timeout=15)
        return True
    except Exception as e:
        print(f'[Watchdog] Restart failed: {e}')
        return False

def check_heartbeat() -> tuple[bool, int]:
    try:
        mtime = HEARTBEAT_FILE.stat().st_mtime
        age = int(time.time() - mtime)
        return age <= HEARTBEAT_MAX_AGE, age
    except FileNotFoundError:
        return False, -1

def main():
    print('[Watchdog] Starting...')
    already_alerted = False

    hb_ok, hb_age = check_heartbeat()
    bot_status = get_service_status('kongtrade-bot')

    if bot_status == 'active' and hb_ok:
        print(f'[Watchdog] OK — Bot active, heartbeat {hb_age}s ago')
        already_alerted = False
        return

    if bot_status == 'failed' or bot_status == 'inactive':
        msg = f'⚠️ <b>KongTrade Bot DOWN</b>\nService: {bot_status}\nHeartbeat: {hb_age}s\n→ Restarting...'
        print(f'[Watchdog] {msg}')
        send_telegram(msg)
        cleanup_stale_lock()
        if restart_bot():
            print('[Watchdog] Bot neu gestartet via systemd')
        else:
            send_telegram('❌ <b>KongTrade Bot</b> Neustart fehlgeschlagen!')
        return

    if not hb_ok and hb_age > HEARTBEAT_MAX_AGE:
        msg = f'⚠️ <b>KongTrade Bot Frozen?</b>\nService: {bot_status} aber kein Heartbeat seit {hb_age}s\n→ Restarting...'
        print(f'[Watchdog] {msg}')
        send_telegram(msg)
        cleanup_stale_lock()
        if restart_bot():
            print('[Watchdog] Bot neu gestartet (frozen)')
        return

if __name__ == '__main__':
    main()
