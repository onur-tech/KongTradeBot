#!/usr/bin/env python3
"""
KongTrade Health Monitor
Läuft stündlich via systemd Timer.
Prüft Bot-Gesundheit und sendet Telegram-Alerts + E-Mail.
"""
import os, json, subprocess, time, urllib.request
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
from pathlib import Path

BOT_ROOT = Path("/root/KongTradeBot")
LOG_FILE = BOT_ROOT / "logs/bot.log"
LOCK_FILE = BOT_ROOT / "bot.lock"
SHADOW_FILE = BOT_ROOT / "data/shadow_portfolio.json"
STATUS_FILE = BOT_ROOT / "scripts/.health_status.json"


def load_env():
    env = {}
    env_file = BOT_ROOT / ".env"
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def send_telegram(token, chat_id, msg):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = json.dumps({
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "HTML"
    }).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")


def send_email_alert(subject, body, env):
    """
    Sendet E-Mail via Gmail SMTP (App-Passwort).
    Konfiguration in .env:
      ALERT_EMAIL_FROM=yourmail@gmail.com
      ALERT_EMAIL_PASSWORD=xxxx xxxx xxxx xxxx  (Gmail App-Passwort)
      ALERT_EMAIL_TO=onur73@gmail.com
    """
    smtp_user = env.get("ALERT_EMAIL_FROM", "")
    smtp_pass = env.get("ALERT_EMAIL_PASSWORD", "")
    smtp_to = env.get("ALERT_EMAIL_TO", "onur73@gmail.com")

    if not smtp_user or not smtp_pass:
        print(f"[EMAIL SKIP] Kein SMTP konfiguriert: {subject}")
        return

    msg = MIMEText(body, "html")
    msg["Subject"] = f"[KongTrade] {subject}"
    msg["From"] = smtp_user
    msg["To"] = smtp_to

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(smtp_user, smtp_pass)
            s.send_message(msg)
            print(f"[EMAIL] Gesendet: {subject}")
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")


def check_bot_running():
    result = subprocess.run(
        ["systemctl", "is-active", "kongtrade-bot"],
        capture_output=True, text=True
    )
    return result.stdout.strip() == "active"


def check_heartbeat():
    try:
        lines = Path(LOG_FILE).read_text().splitlines()
        hb_lines = [l for l in lines if "heartbeat" in l.lower() or "Heartbeat" in l]
        if not hb_lines:
            return None, 9999
        last = hb_lines[-1]
        ts_str = last[:19]
        ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        age_minutes = int((datetime.now(timezone.utc) - ts).total_seconds()) // 60
        return ts_str, age_minutes
    except Exception:
        return None, 9999


def check_weather_scout():
    try:
        lines = Path(LOG_FILE).read_text().splitlines()
        ws_lines = [l for l in lines if "WeatherScout" in l or "weather_scout" in l]
        if not ws_lines:
            return None, 9999, "unbekannt"
        last = ws_lines[-1]
        ts_str = last[:19]
        ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        age_hours = int((datetime.now(timezone.utc) - ts).total_seconds()) // 3600
        opportunities = [l for l in ws_lines[-20:] if "Opportunities" in l]
        last_opp = opportunities[-1].strip()[-50:] if opportunities else "unbekannt"
        return ts_str, age_hours, last_opp
    except Exception:
        return None, 9999, "Fehler"


def check_shadow_trades_today():
    try:
        data = json.loads(Path(SHADOW_FILE).read_text())
        today = datetime.now().strftime("%Y-%m-%d")
        positions = data.get("positions", [])
        if isinstance(positions, dict):
            positions = list(positions.values())
        today_trades = [p for p in positions if today in str(p.get("entry_time", ""))]
        return len(today_trades)
    except Exception:
        return -1


def check_real_trades_today():
    try:
        lines = Path(LOG_FILE).read_text().splitlines()
        today = datetime.now().strftime("%Y-%m-%d")
        real_trades = [l for l in lines
                       if today in l and "Order erstellt" in l and "LIVE" in l]
        return len(real_trades)
    except Exception:
        return -1


def check_ws_events():
    try:
        lines = Path(LOG_FILE).read_text().splitlines()
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_ws = []
        for l in lines:
            if "WS" in l or "WebSocket" in l or "ws_event" in l.lower():
                try:
                    ts = datetime.strptime(l[:19], "%Y-%m-%d %H:%M:%S")
                    if ts > one_hour_ago:
                        recent_ws.append(l)
                except Exception:
                    pass
        return len(recent_ws)
    except Exception:
        return -1


def check_insider_scan():
    result = subprocess.run(
        ["pgrep", "-f", "insider_analysis"],
        capture_output=True, text=True
    )
    return result.stdout.strip() != ""


def run_health_check():
    env = load_env()
    token = env.get("TELEGRAM_TOKEN", "")
    chat_id = env.get("TELEGRAM_CHAT_IDS", "507270873").split(",")[0]

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    alerts = []
    infos = []

    # 1. Bot läuft?
    bot_running = check_bot_running()
    if not bot_running:
        alerts.append("🔴 KRITISCH: kongtrade-bot.service ist DOWN!")
    else:
        infos.append("✅ Bot: RUNNING")

    # 2. Heartbeat
    hb_ts, hb_age = check_heartbeat()
    if hb_age > 10:
        alerts.append(f"🟡 WARN: Heartbeat {hb_age} Min alt (letzte: {hb_ts})")
    else:
        infos.append(f"✅ Heartbeat: {hb_age} Min ago")

    # 3. WeatherScout
    ws_result = check_weather_scout()
    ws_ts, ws_age = ws_result[0], ws_result[1]
    ws_opp = ws_result[2] if len(ws_result) > 2 else "?"
    if ws_age > 7:
        alerts.append(f"🟡 WARN: WeatherScout seit {ws_age}h nicht gelaufen!")
    else:
        infos.append(f"✅ WeatherScout: vor {ws_age}h | {ws_opp}")

    # 4. Shadow Trades heute
    shadow_count = check_shadow_trades_today()
    if shadow_count == 0:
        alerts.append("🟡 WARN: Heute 0 Shadow-Trades — Scout findet nichts?")
    else:
        infos.append(f"✅ Shadow-Trades heute: {shadow_count}")

    # 5. Echte Trades heute
    real_count = check_real_trades_today()
    infos.append(f"📊 Echte Trades heute: {real_count}")

    # 6. WebSocket Events
    ws_events = check_ws_events()
    if ws_events == 0:
        alerts.append("🟡 WARN: 0 WebSocket Events in letzter Stunde")
    else:
        infos.append(f"✅ WS Events (1h): {ws_events}")

    # 7. Insider-Scan
    insider_running = check_insider_scan()
    if not insider_running:
        alerts.append("🟡 WARN: Insider-Scan läuft nicht mehr!")
    else:
        infos.append("✅ Insider-Scan: aktiv")

    # Telegram + E-Mail senden
    if alerts:
        msg = f"⚠️ <b>KongTrade Health Alert</b> — {now}\n\n"
        msg += "\n".join(alerts)
        msg += "\n\n<i>" + " | ".join(infos[:3]) + "</i>"
        send_telegram(token, chat_id, msg)
        # E-Mail bei Alerts immer
        email_body = msg.replace("\n", "<br>").replace("<b>", "<strong>").replace("</b>", "</strong>")
        send_email_alert(f"Health Alert — {len(alerts)} Problem(e)", email_body, env)
        print(f"ALERT gesendet: {len(alerts)} Probleme")
    else:
        hour = datetime.now().hour
        if hour == 6:  # 06:00 UTC = 08:00 Berlin
            info_str = "\n".join(infos)
            msg = f"📊 <b>KongTrade Daily Report</b> — {now}\n\n{info_str}"
            # Daily Report: nur E-Mail, kein Telegram-Spam
            email_body = msg.replace("\n", "<br>").replace("<b>", "<strong>").replace("</b>", "</strong>")
            send_email_alert(f"Daily Report {now}", email_body, env)
            print("Daily Report (E-Mail) gesendet")
        else:
            print(f"OK — alle Checks bestanden ({now})")

    status = {
        "last_check": now,
        "bot_running": bot_running,
        "alerts": alerts,
        "checks_passed": len(infos)
    }
    Path(STATUS_FILE).write_text(json.dumps(status, indent=2))


if __name__ == "__main__":
    run_health_check()
