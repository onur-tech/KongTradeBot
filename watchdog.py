"""
watchdog.py — KongTrade Bot Watchdog v2 (Race-Condition-Safe)

Prüft in dieser Reihenfolge BEVOR restartet wird:
  1. Lock-PID: Läuft der Bot-Prozess wirklich noch?
  2. Heartbeat: Antwortet der Bot noch (Datei-mtime)?
  3. Rate-Limit: Max 3 Restarts pro Stunde
  4. Graceful Shutdown: SIGTERM → 30s warten → SIGKILL
  5. Lock-Cleanup → Restart via systemctl

Verwendung:
  python3 watchdog.py            # Einmalige Prüfung (systemd-oneshot)
  python3 watchdog.py --dry-run  # Nur anzeigen was getan würde

WARUM 600s Heartbeat-Timeout:
  Der Bot schreibt heartbeat.txt alle 300s (5 Min).
  Timeout muss > Schreibintervall sein → 600s = 2× Schreibintervall.
"""
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

# ── Konfiguration ─────────────────────────────────────────────────────────────
LOCK_FILE          = BASE_DIR / "bot.lock"
HEARTBEAT_FILE     = BASE_DIR / "heartbeat.txt"
STATE_FILE         = BASE_DIR / "data" / "watchdog_state.json"

HEARTBEAT_TIMEOUT  = 600   # Sekunden — muss > heartbeat_interval (300s) sein
SIGTERM_WAIT       = 30    # Sekunden warten nach SIGTERM vor SIGKILL
RESTART_RATE_LIMIT = 3     # Max Restarts innerhalb von RATE_LIMIT_WINDOW
RATE_LIMIT_WINDOW  = 3600  # 1 Stunde

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
_raw_chat_ids  = os.getenv("TELEGRAM_CHAT_IDS", "507270873")
CHAT_IDS       = [cid.strip() for cid in _raw_chat_ids.split(",") if cid.strip()]

DRY_RUN = "--dry-run" in sys.argv


# ── Logging ───────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def send_telegram(msg: str) -> None:
    if DRY_RUN:
        log(f"[DRY-RUN] Telegram: {msg[:120]}")
        return
    if not TELEGRAM_TOKEN:
        log("[Watchdog] Kein Telegram-Token — Alert übersprungen")
        return
    for chat_id in CHAT_IDS:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
                timeout=10,
            )
        except Exception as e:
            log(f"[Watchdog] Telegram-Fehler: {e}")


# ── Rate-Limit State ──────────────────────────────────────────────────────────

def _load_state() -> dict:
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"restarts": [], "rate_limit_alert_sent": False}


def _save_state(state: dict) -> None:
    try:
        STATE_FILE.parent.mkdir(exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        log(f"[Watchdog] State-Save fehlgeschlagen: {e}")


def get_recent_restarts(state: dict) -> list:
    """Gibt Restart-Timestamps aus den letzten RATE_LIMIT_WINDOW Sekunden zurück."""
    cutoff = time.time() - RATE_LIMIT_WINDOW
    return [t for t in state.get("restarts", []) if t >= cutoff]


def record_restart(state: dict) -> dict:
    restarts = get_recent_restarts(state)
    restarts.append(time.time())
    state["restarts"] = restarts[-20:]
    state["last_restart"] = datetime.utcnow().isoformat() + "Z"
    state["rate_limit_alert_sent"] = False
    return state


def is_rate_limited(state: dict) -> bool:
    return len(get_recent_restarts(state)) >= RESTART_RATE_LIMIT


# ── Lock / PID / Heartbeat Checks ─────────────────────────────────────────────

def check_lock_pid() -> tuple:
    """
    Liest bot.lock und prüft ob der Prozess lebt.

    Gibt (pid: int|None, is_alive: bool) zurück.
    pid=None wenn kein Lock-File oder ungültige PID.
    is_alive=True nur wenn Prozess existiert UND 'main.py' im Cmdline hat.
    """
    if not LOCK_FILE.exists():
        return None, False
    try:
        pid = int(LOCK_FILE.read_text().strip())
    except (ValueError, OSError):
        return None, False

    if not psutil.pid_exists(pid):
        return pid, False

    try:
        proc = psutil.Process(pid)
        cmdline = " ".join(proc.cmdline())
        return pid, "main.py" in cmdline
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return pid, False


def check_heartbeat() -> tuple:
    """
    Prüft heartbeat.txt Aktualität via Datei-mtime.

    Gibt (is_fresh: bool, age_seconds: int) zurück.
    age=-1 wenn Datei fehlt.
    """
    if not HEARTBEAT_FILE.exists():
        return False, -1
    try:
        mtime = HEARTBEAT_FILE.stat().st_mtime
        age = int(time.time() - mtime)
        return age <= HEARTBEAT_TIMEOUT, age
    except OSError:
        return False, -1


def cleanup_stale_lock(pid) -> None:
    if LOCK_FILE.exists():
        try:
            LOCK_FILE.unlink()
            log(f"[Watchdog] bot.lock entfernt (PID {pid})")
        except OSError as e:
            log(f"[Watchdog] bot.lock konnte nicht entfernt werden: {e}")


def graceful_shutdown(pid: int) -> bool:
    """
    Beendet Prozess sauber:
      1. SIGTERM senden
      2. SIGTERM_WAIT Sekunden warten
      3. Bei Timeout: SIGKILL

    Gibt True zurück wenn Prozess beendet wurde.
    """
    if DRY_RUN:
        log(f"[DRY-RUN] Würde SIGTERM → PID {pid}, dann {SIGTERM_WAIT}s warten, dann ggf. SIGKILL")
        return True

    try:
        log(f"[Watchdog] SIGTERM → PID {pid}")
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        log(f"[Watchdog] PID {pid} bereits tot")
        return True
    except OSError as e:
        log(f"[Watchdog] SIGTERM fehlgeschlagen: {e}")
        return False

    deadline = time.time() + SIGTERM_WAIT
    while time.time() < deadline:
        time.sleep(1)
        if not psutil.pid_exists(pid):
            log(f"[Watchdog] PID {pid} sauber beendet")
            return True

    log(f"[Watchdog] Timeout nach {SIGTERM_WAIT}s — SIGKILL → PID {pid}")
    try:
        os.kill(pid, signal.SIGKILL)
        time.sleep(2)
    except (ProcessLookupError, OSError):
        pass

    alive = psutil.pid_exists(pid)
    if alive:
        log(f"[Watchdog] WARNUNG: PID {pid} lebt noch nach SIGKILL!")
    return not alive


def restart_service() -> bool:
    if DRY_RUN:
        log("[DRY-RUN] Würde 'systemctl restart kongtrade-bot' ausführen")
        return True
    try:
        subprocess.run(["systemctl", "restart", "kongtrade-bot"], timeout=20, check=True)
        log("[Watchdog] systemctl restart kongtrade-bot — OK")
        return True
    except Exception as e:
        log(f"[Watchdog] systemctl restart fehlgeschlagen: {e}")
        return False


# ── Hauptlogik ────────────────────────────────────────────────────────────────

def check() -> str:
    """
    Einmalige Watchdog-Prüfung.

    Rückgabewerte: 'ok' | 'restarted' | 'rate_limited' | 'skip'
    """
    state = _load_state()
    pid, pid_alive = check_lock_pid()
    hb_fresh, hb_age = check_heartbeat()

    age_str = f"{hb_age}s" if hb_age >= 0 else "unbekannt (heartbeat.txt fehlt)"

    # ── 1. Alles OK ───────────────────────────────────────────────────────────
    if pid_alive and hb_fresh:
        log(f"[Watchdog] ✅ OK — PID {pid} läuft | Heartbeat {age_str} alt")
        # Stabilität: Rate-Limit-Alert-Flag zurücksetzen
        if state.get("rate_limit_alert_sent"):
            state["rate_limit_alert_sent"] = False
            _save_state(state)
        return "ok"

    # ── 2. Prozess lebt, Heartbeat veraltet → Bot hängt ──────────────────────
    if pid_alive and not hb_fresh:
        log(f"[Watchdog] ⚠️  Bot hängt — PID {pid} lebt, Heartbeat {age_str} alt (max {HEARTBEAT_TIMEOUT}s)")

        if is_rate_limited(state):
            if not state.get("rate_limit_alert_sent"):
                log(f"[Watchdog] 🚫 Rate-Limit ({RESTART_RATE_LIMIT}/h) — kein Restart")
                send_telegram(
                    f"🚫 <b>Watchdog Rate-Limit: {RESTART_RATE_LIMIT} Restarts/h!</b>\n"
                    f"⚠️ Bot hängt (Heartbeat {age_str} alt), aber Auto-Restart gestoppt.\n"
                    f"👤 <b>Manuelle Intervention erforderlich!</b>"
                )
                state["rate_limit_alert_sent"] = True
                _save_state(state)
            return "rate_limited"

        send_telegram(
            f"⚠️ <b>Bot hängt!</b>\n"
            f"PID {pid} läuft, aber kein Heartbeat seit {age_str}\n"
            f"→ Graceful Shutdown wird versucht..."
        )
        graceful_shutdown(pid)
        cleanup_stale_lock(pid)
        state = record_restart(state)
        _save_state(state)

        success = restart_service()
        if success:
            send_telegram("✅ <b>Bot nach Freeze neu gestartet</b>")
            log("[Watchdog] Bot nach Freeze neu gestartet")
        else:
            send_telegram("❌ <b>Neustart nach Freeze fehlgeschlagen</b> — bitte manuell prüfen!")
        return "restarted"

    # ── 3. Stale Lock (Prozess tot, Lock existiert noch) ─────────────────────
    if pid is not None and not pid_alive:
        log(f"[Watchdog] ⚠️  Stale Lock — PID {pid} tot | Heartbeat {age_str} alt")
        cleanup_stale_lock(pid)

    # ── 4. Bot nicht aktiv ────────────────────────────────────────────────────
    log(f"[Watchdog] ⚠️  Bot nicht aktiv | Heartbeat {age_str} alt | Rate-Limit prüfen...")

    if is_rate_limited(state):
        if not state.get("rate_limit_alert_sent"):
            log(f"[Watchdog] 🚫 Rate-Limit ({RESTART_RATE_LIMIT}/h) — kein Restart")
            send_telegram(
                f"🚫 <b>Watchdog Rate-Limit: {RESTART_RATE_LIMIT} Restarts/h!</b>\n"
                f"Bot ist offline, Auto-Restart gestoppt.\n"
                f"👤 <b>Manuelle Intervention erforderlich!</b>"
            )
            state["rate_limit_alert_sent"] = True
            _save_state(state)
        return "rate_limited"

    send_telegram(
        f"⚠️ <b>Bot offline</b>\n"
        f"PID nicht aktiv | Heartbeat {age_str} alt\n"
        f"→ Neustart..."
    )
    state = record_restart(state)
    _save_state(state)

    success = restart_service()
    if success:
        send_telegram("✅ <b>Bot neu gestartet</b>")
        log("[Watchdog] Bot neu gestartet")
    else:
        send_telegram("❌ <b>Neustart fehlgeschlagen</b> — bitte manuell prüfen!")
    return "restarted"


def main() -> None:
    if DRY_RUN:
        log("[Watchdog] *** DRY-RUN-Modus — kein Eingriff ***")

    log("[Watchdog] Starte Prüfung...")
    result = check()

    if DRY_RUN:
        log(f"[Watchdog] DRY-RUN Ergebnis: {result}")
    else:
        log(f"[Watchdog] Prüfung abgeschlossen: {result}")


if __name__ == "__main__":
    main()
