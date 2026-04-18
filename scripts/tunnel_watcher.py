#!/usr/bin/env python3
"""Tunnel-Watcher: extrahiert aktuelle trycloudflare URL, sendet Telegram bei Aenderung."""
import os
import re
import subprocess
import urllib.request
import urllib.parse
import logging
from datetime import datetime, timezone

LOG_FILE = "/root/KongTradeBot/logs/tunnel_watcher.log"
LAST_URL_FILE = "/root/KongTradeBot/.last_tunnel_url"
CURRENT_URL_FILE = "/root/KongTradeBot/.current_tunnel_url"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("tunnel_watcher")

def get_current_url():
    try:
        r = subprocess.run(
            ["journalctl", "-u", "kongtrade-tunnel", "--no-pager", "-n", "200"],
            capture_output=True, text=True
        )
        matches = re.findall(r"https://[a-z0-9-]+\.trycloudflare\.com", r.stdout)
        return matches[-1] if matches else None
    except Exception as e:
        log.error(f"URL-Extraktion fehlgeschlagen: {e}")
        return None

def read_file(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except Exception:
        return None

def write_file(path, content):
    with open(path, "w") as f:
        f.write(content)

def send_telegram(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            log.info(f"Telegram gesendet an {chat_id}: HTTP {resp.status}")
            return True
    except Exception as e:
        log.error(f"Telegram-Fehler: {e}")
        return False

def load_env():
    env = {}
    try:
        with open("/root/KongTradeBot/.env") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    except Exception as e:
        log.error(f".env lesen fehlgeschlagen: {e}")
    return env

# --- Main ---
current_url = get_current_url()
if not current_url:
    log.warning("Keine trycloudflare-URL im Journal gefunden — exit")
    exit(0)

log.info(f"Aktuelle URL: {current_url}")
last_url = read_file(LAST_URL_FILE)

if current_url == last_url:
    log.info("URL unveraendert — kein Update noetig")
    exit(0)

log.info(f"URL geaendert: {last_url!r} -> {current_url!r}")

# Speichern
write_file(LAST_URL_FILE, current_url)
write_file(CURRENT_URL_FILE, current_url)

# Telegram senden
env = load_env()
token = env.get("TELEGRAM_TOKEN", "")
chat_ids_raw = env.get("TELEGRAM_CHAT_IDS", "")
first_chat_id = chat_ids_raw.split(",")[0].strip() if chat_ids_raw else ""

if token and chat_ids_raw:
    chat_ids = [cid.strip() for cid in chat_ids_raw.split(",") if cid.strip()]
    msg = (
        f"<b>Neue Dashboard-URL</b>\n\n"
        f"{current_url}\n\n"
        f"Status-Repo: https://github.com/KongTradeBot/KongTradeBot-Status"
    )
    sent = [cid for cid in chat_ids if send_telegram(token, cid, msg)]
    log.info(f"Alert an {len(sent)}/{len(chat_ids)} Chat-IDs gesendet: {sent}")
else:
    log.warning("Kein TELEGRAM_TOKEN oder CHAT_ID in .env — kein Telegram-Alert")

log.info("Tunnel-Watcher abgeschlossen")
