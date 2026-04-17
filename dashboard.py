"""
dashboard.py — KongTrade Bot Premium Dashboard
Abhängigkeiten: pip install flask flask-socketio
Starten: python dashboard.py
Öffnen:  http://localhost:5000  (auch remote via http://<server-ip>:5000)
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
try:
    from strategies.copy_trading import get_wallet_name, WALLET_NAMES
except ImportError:
    def get_wallet_name(addr): return addr[:10] + "..." if addr else "?"
    WALLET_NAMES = {}

try:
    from flask import Flask, render_template, jsonify, request, send_from_directory
    from flask_socketio import SocketIO, emit
except ImportError:
    print("FEHLER: pip install flask flask-socketio")
    sys.exit(1)

BASE_DIR      = Path(__file__).parent
STATE_FILE    = BASE_DIR / "bot_state.json"
ARCHIVE_FILE  = BASE_DIR / "trades_archive.json"
ENV_FILE      = BASE_DIR / ".env"
STRATEGY_FILE = BASE_DIR / "strategies" / "copy_trading.py"
LOG_DIR       = BASE_DIR / "logs"

app = Flask(__name__, template_folder=str(BASE_DIR))
app.config["SECRET_KEY"] = "polymarket-dashboard-2026"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ── Hilfsfunktionen ──────────────────────────────────────────────────────────

def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def load_env():
    env = {}
    try:
        with open(ENV_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip()
    except Exception:
        pass
    return env


def save_env_key(key, value):
    allowed = {"MAX_TRADE_SIZE_USD", "MAX_DAILY_LOSS_USD", "MIN_TRADE_SIZE_USD",
               "COPY_SIZE_MULTIPLIER", "DRY_RUN"}
    if key not in allowed:
        return False, f"Key '{key}' nicht erlaubt"
    try:
        with open(ENV_FILE, encoding="utf-8") as f:
            content = f.read()
        pattern = rf"^({re.escape(key)}\s*=).*$"
        new_line = f"{key}={value}"
        if re.search(pattern, content, re.MULTILINE):
            content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
        else:
            content += f"\n{new_line}"
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        return True, None
    except Exception as e:
        return False, str(e)


def load_wallet_multipliers():
    multipliers, default = {}, 0.5
    try:
        src = STRATEGY_FILE.read_text(encoding="utf-8")
        block = re.search(r"WALLET_MULTIPLIERS\s*:\s*Dict\[.*?\]\s*=\s*\{(.*?)\}", src, re.DOTALL)
        if block:
            for m in re.finditer(r'#\s*(.*?)\n.*?"(0x[0-9a-fA-F]+)"\s*:\s*([\d.]+)', block.group(1)):
                multipliers[m.group(2).lower()] = {"value": float(m.group(3)), "label": m.group(1).strip()}
            for m in re.finditer(r'"(0x[0-9a-fA-F]+)"\s*:\s*([\d.]+)', block.group(1)):
                addr = m.group(1).lower()
                if addr not in multipliers:
                    multipliers[addr] = {"value": float(m.group(2)), "label": addr[:10] + "..."}
        dm = re.search(r"DEFAULT_WALLET_MULTIPLIER\s*:\s*float\s*=\s*([\d.]+)", src)
        if dm:
            default = float(dm.group(1))
    except Exception:
        pass
    return multipliers, default


def save_wallet_multiplier(wallet, value):
    try:
        src = STRATEGY_FILE.read_text(encoding="utf-8")
        wallet_l = wallet.lower()
        pattern = rf'("{re.escape(wallet_l)}"\s*:\s*)([\d.]+)'
        if re.search(pattern, src, re.IGNORECASE):
            src = re.sub(pattern, lambda m: f'{m.group(1)}{value}', src, flags=re.IGNORECASE)
            STRATEGY_FILE.write_text(src, encoding="utf-8")
            return True, None
        return False, "Wallet nicht gefunden"
    except Exception as e:
        return False, str(e)


def save_default_multiplier(value):
    try:
        src = STRATEGY_FILE.read_text(encoding="utf-8")
        src = re.sub(r"(DEFAULT_WALLET_MULTIPLIER\s*:\s*float\s*=\s*)([\d.]+)", rf"\g<1>{value}", src)
        STRATEGY_FILE.write_text(src, encoding="utf-8")
        return True, None
    except Exception as e:
        return False, str(e)


def get_stats():
    archive = load_json(ARCHIVE_FILE) or []
    closed  = [t for t in archive if t.get("aufgeloest")]
    open_t  = [t for t in archive if not t.get("aufgeloest")]
    wins    = [t for t in closed if t.get("ergebnis") == "GEWINN"]
    losses  = [t for t in closed if t.get("ergebnis") == "VERLUST"]
    pnl     = sum(float(t.get("gewinn_verlust_usdc", 0) or 0) for t in closed)
    invested = sum(float(t.get("einsatz_usdc", 0) or 0) for t in closed)
    win_rate = len(wins) / len(closed) * 100 if closed else 0
    today   = date.today().isoformat()
    today_trades = [t for t in archive if t.get("datum") == today]
    today_pnl    = sum(float(t.get("gewinn_verlust_usdc", 0) or 0) for t in today_trades if t.get("aufgeloest"))

    # Kategorie-Breakdown
    cats = {}
    for t in archive:
        cat = t.get("kategorie", "Sonstiges") or "Sonstiges"
        cats[cat] = cats.get(cat, 0) + 1

    # Wallet-Performance
    wallet_perf = {}
    for t in closed:
        w = t.get("source_wallet", "Unknown")
        if w not in wallet_perf:
            wallet_perf[w] = {"wins": 0, "losses": 0, "pnl": 0}
        if t.get("ergebnis") == "GEWINN":
            wallet_perf[w]["wins"] += 1
        else:
            wallet_perf[w]["losses"] += 1
        wallet_perf[w]["pnl"] += float(t.get("gewinn_verlust_usdc", 0) or 0)

    return {
        "total_trades": len(archive),
        "open":         len(open_t),
        "closed":       len(closed),
        "wins":         len(wins),
        "losses":       len(losses),
        "pnl":          round(pnl, 2),
        "invested":     round(invested, 2),
        "win_rate":     round(win_rate, 1),
        "today_trades": len(today_trades),
        "today_pnl":    round(today_pnl, 2),
        "categories":   cats,
        "wallet_perf":  {k[:10]+"...": v for k, v in wallet_perf.items()},
    }


def get_positions():
    state = load_json(STATE_FILE)
    if not state:
        return []
    result = []
    for p in state.get("open_positions", []):
        opened = p.get("opened_at", "")
        try:
            age_h = round((datetime.now() - datetime.fromisoformat(opened)).total_seconds() / 3600, 1)
        except Exception:
            age_h = 0
        result.append({
            "market":      p.get("market_question", "Unknown")[:52],
            "outcome":     p.get("outcome", ""),
            "entry_price": round(float(p.get("entry_price", 0)) * 100, 1),
            "size_usdc":   round(float(p.get("size_usdc", 0)), 2),
            "age_h":       age_h,
            "wallet":      get_wallet_name(p.get("source_wallet", "")),
        })
    return result


def get_log_lines(n=50):
    today = date.today().strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"bot_{today}.log"
    if not log_file.exists():
        return []
    try:
        lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
        return lines[-n:]
    except Exception:
        return []


def is_bot_running():
    pid_file = BASE_DIR / "bot.pid"
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)
            return True, pid
        except Exception:
            pass
    try:
        out = subprocess.check_output("tasklist", shell=True, text=True)
        return "python" in out.lower(), None
    except Exception:
        return False, None


# ── WebSocket Live-Push ───────────────────────────────────────────────────────

_last_log_count = 0

def background_push():
    global _last_log_count
    while True:
        try:
            with app.app_context():
                # Stats
                stats = get_stats()
                running, pid = is_bot_running()
                env = load_env()
                stats["bot_running"] = running
                stats["bot_pid"]     = pid
                stats["dry_run"]     = env.get("DRY_RUN", "true").lower() == "true"
                socketio.emit("stats", stats)

                # Positionen
                socketio.emit("positions", get_positions())

                # Log (nur neue Zeilen)
                lines = get_log_lines(80)
                if len(lines) != _last_log_count:
                    _last_log_count = len(lines)
                    socketio.emit("log", lines[-50:])
        except Exception:
            pass
        time.sleep(5)


@socketio.on("connect")
def on_connect():
    stats = get_stats()
    running, pid = is_bot_running()
    env = load_env()
    stats["bot_running"] = running
    stats["bot_pid"]     = pid
    stats["dry_run"]     = env.get("DRY_RUN", "true").lower() == "true"
    emit("stats", stats)
    emit("positions", get_positions())
    emit("log", get_log_lines(50))
    mults, default = load_wallet_multipliers()
    emit("multipliers", {"wallets": mults, "default": default})
    emit("env", load_env())


# ── REST Endpoints ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(str(BASE_DIR), "dashboard.html")


@app.route("/api/env", methods=["POST"])
def api_env():
    data  = request.json
    ok, err = save_env_key(data.get("key", ""), str(data.get("value", "")))
    return jsonify({"ok": ok, "error": err})


@app.route("/api/multipliers", methods=["POST"])
def api_multipliers():
    data   = request.json
    wallet = data.get("wallet", "")
    value  = round(float(data.get("value", 1.0)), 2)
    if wallet == "__default__":
        ok, err = save_default_multiplier(value)
    else:
        ok, err = save_wallet_multiplier(wallet, value)
    return jsonify({"ok": ok, "error": err})


@app.route("/api/action", methods=["POST"])
def api_action():
    action  = request.json.get("action", "")
    python  = sys.executable
    bot_dir = str(BASE_DIR)
    flags   = subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0

    if action == "stop":
        pid_file = BASE_DIR / "bot.pid"
        try:
            if pid_file.exists():
                pid = int(pid_file.read_text().strip())
                os.kill(pid, 15)
                return jsonify({"ok": True, "message": f"Bot gestoppt (PID {pid})"})
            subprocess.run("taskkill /F /IM python.exe", shell=True, capture_output=True)
            return jsonify({"ok": True, "message": "Bot gestoppt"})
        except Exception as e:
            return jsonify({"ok": False, "message": str(e)})

    elif action == "restart":
        try:
            subprocess.run("taskkill /F /IM python.exe", shell=True, capture_output=True)
            time.sleep(2)
            subprocess.Popen([python, "main.py"], cwd=bot_dir, creationflags=flags)
            return jsonify({"ok": True, "message": "Bot neu gestartet"})
        except Exception as e:
            return jsonify({"ok": False, "message": str(e)})

    elif action == "auswertung":
        try:
            subprocess.Popen([python, "auswertung.py"], cwd=bot_dir, creationflags=flags)
            return jsonify({"ok": True, "message": "Auswertung gestartet"})
        except Exception as e:
            return jsonify({"ok": False, "message": str(e)})

    elif action == "resolver":
        try:
            subprocess.Popen([python, "resolver.py"], cwd=bot_dir, creationflags=flags)
            return jsonify({"ok": True, "message": "Resolver gestartet"})
        except Exception as e:
            return jsonify({"ok": False, "message": str(e)})

    return jsonify({"ok": False, "message": "Unbekannte Aktion"})


# ── Background-Push Watchdog ─────────────────────────────────────────────────

_push_thread: threading.Thread | None = None


def _ensure_push_thread_running():
    """Startet den background_push Thread neu falls er gestorben ist."""
    global _push_thread
    if _push_thread is None or not _push_thread.is_alive():
        _push_thread = threading.Thread(target=background_push, daemon=True)
        _push_thread.start()
        print(f"[Dashboard] background_push Thread (neu)gestartet")


def _watchdog():
    """Überwacht background_push und startet ihn neu falls er stirbt."""
    while True:
        try:
            time.sleep(10)
            _ensure_push_thread_running()
        except Exception:
            pass


# ── Start ─────────────────────────────────────────────────────────────────────

_BANNER = """\
=======================================================
  KongTrade Bot Dashboard
  http://localhost:5000
  Netzwerk: http://0.0.0.0:5000
  Stoppen: Ctrl+C
======================================================="""

MAX_RESTARTS = 20


def _run_server():
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    _ensure_push_thread_running()
    threading.Thread(target=_watchdog, daemon=True).start()

    print(_BANNER)

    restarts = 0
    while restarts < MAX_RESTARTS:
        try:
            _run_server()
            break  # Sauberer Exit (Ctrl+C)
        except KeyboardInterrupt:
            print("\n[Dashboard] Gestoppt.")
            break
        except OSError as e:
            if "Address already in use" in str(e) or "10048" in str(e):
                print(f"[Dashboard] Port 5000 belegt — warte 10s und versuche erneut...")
                time.sleep(10)
            else:
                restarts += 1
                print(f"[Dashboard] Fehler: {e} — Neustart {restarts}/{MAX_RESTARTS} in 3s")
                time.sleep(3)
        except Exception as e:
            restarts += 1
            print(f"[Dashboard] Unerwarteter Fehler: {e} — Neustart {restarts}/{MAX_RESTARTS} in 3s")
            time.sleep(3)

    if restarts >= MAX_RESTARTS:
        print(f"[Dashboard] {MAX_RESTARTS} Neustarts erreicht — beendet.")
