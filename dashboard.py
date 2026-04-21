"""
dashboard.py — KongTrade Bot Ultimate Dashboard v2.0
Abhängigkeiten: pip install flask flask-socketio requests
Starten: python dashboard.py
Öffnen:  http://localhost:5000
"""

import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime, date, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
try:
    from strategies.copy_trading import get_wallet_name, WALLET_NAMES
except ImportError:
    def get_wallet_name(addr): return addr[:10] + "..." if addr else "?"
    WALLET_NAMES = {}

import functools
import hashlib
import secrets

try:
    from flask import Flask, render_template, jsonify, request, send_from_directory, session, redirect, url_for
    from flask_socketio import SocketIO, emit
except ImportError:
    print("FEHLER: pip install flask flask-socketio")
    sys.exit(1)

BASE_DIR      = Path(__file__).parent
STATE_FILE    = BASE_DIR / "bot_state.json"
ARCHIVE_FILE  = BASE_DIR / "trades_archive.json"
ENV_FILE      = BASE_DIR / ".env"
STRATEGY_FILE = BASE_DIR / "strategies" / "copy_trading.py"


def _get_midnight_snapshot(today_str: str, current_total: float) -> dict:
    """Lädt oder erstellt den Tages-Snapshot für today_pnl-Berechnung.
    Datei: .portfolio_snapshot_YYYY-MM-DD.json
    Kein Snapshot wird erstellt wenn current_total == 0 (Daten noch nicht geladen).
    Returns: {"snapshot_value": float, "created_at": str}
    """
    snap_file = BASE_DIR / f".portfolio_snapshot_{today_str}.json"
    # Alte Snapshots aufräumen (> 7 Tage)
    try:
        for f in BASE_DIR.glob(".portfolio_snapshot_*.json"):
            if f.name < f".portfolio_snapshot_{today_str}.json":
                f.unlink(missing_ok=True)
    except Exception:
        pass
    if snap_file.exists():
        try:
            existing = json.loads(snap_file.read_text())
            # Überschreibe schlechten Snapshot (snapshot_value == 0 aber Daten jetzt da)
            if existing.get("snapshot_value", 0) == 0 and current_total > 0:
                pass  # → neu erstellen
            else:
                return existing
        except Exception:
            pass
    if current_total <= 0:
        # Daten noch nicht geladen — kein Snapshot erstellen
        return {"snapshot_value": 0.0, "created_at": ""}
    snap = {"snapshot_value": current_total, "created_at": datetime.now(timezone.utc).isoformat()}
    try:
        snap_file.write_text(json.dumps(snap))
    except Exception:
        pass
    return snap
LOG_DIR       = BASE_DIR / "logs"
DB_FILE       = BASE_DIR / "metrics.db"

PROXY_ADDRESS  = "0x700BC51b721F168FF975ff28942BC0E5fAF945eb"
USDC_CONTRACT  = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
POLYGON_RPCS   = [
    "https://polygon-bor-rpc.publicnode.com",
    "https://polygon-rpc.com",
    "https://1rpc.io/matic",
    "https://rpc.ankr.com/polygon",
]

app = Flask(__name__, template_folder=str(BASE_DIR))
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "polymarket-dashboard-2026")
app.config["PERMANENT_SESSION_LIFETIME"] = 86400 * 7  # 7 Tage
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ── Login ──────────────────────────────────────────────────────────────────────

def _load_users() -> list:
    """Lädt users.json; Fallback auf leere Liste."""
    try:
        return json.loads((BASE_DIR / "data" / "users.json").read_text())
    except Exception:
        return []


def _get_dashboard_password() -> str:
    """Fallback: liest DASHBOARD_PASSWORD aus .env (Klartext)."""
    env = {}
    try:
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return env.get("DASHBOARD_PASSWORD", "")


def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Unauthorized"}), 401
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated


LOGIN_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>KongTrade Login</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#030303;color:#e0e0e0;font-family:monospace;display:flex;align-items:center;justify-content:center;height:100vh}
.box{background:#0d0d1a;border:1px solid #1a1a3e;border-radius:12px;padding:40px;width:360px;text-align:center}
.logo{font-size:22px;font-weight:800;letter-spacing:4px;color:#00ff88;margin-bottom:8px}
.logo span{color:#666;font-weight:300}
.subtitle{color:#555;font-size:11px;letter-spacing:2px;margin-bottom:30px}
input{width:100%;padding:12px 16px;background:#0a0a14;border:1px solid #1a1a3e;border-radius:8px;color:#e0e0e0;font-size:14px;font-family:monospace;outline:none;margin-bottom:12px}
input:focus{border-color:#00ff88}
button{width:100%;padding:12px;background:transparent;border:1px solid #00ff88;border-radius:8px;color:#00ff88;font-size:13px;font-family:monospace;letter-spacing:2px;cursor:pointer;margin-top:4px}
button:hover{background:rgba(0,255,136,.08)}
.err{color:#ff4444;font-size:12px;margin-top:12px}
</style>
</head>
<body>
<div class="box">
  <div class="logo">KONG<span>TRADE</span></div>
  <div class="subtitle">DASHBOARD ACCESS</div>
  <form method="POST" action="/login">
    <input type="email" name="email" placeholder="E-Mail" autofocus autocomplete="username">
    <input type="password" name="password" placeholder="Passwort" autocomplete="current-password">
    <button type="submit">EINLOGGEN</button>
  </form>
  {error}
</div>
</body>
</html>"""


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        pw       = request.form.get("password", "")
        pw_hash  = hashlib.sha256(pw.encode()).hexdigest()

        user = next(
            (u for u in _load_users()
             if u["email"].lower() == email and u["password_hash"] == pw_hash),
            None,
        )

        # Fallback: altes Klartext-Passwort (für Übergangszeitraum)
        if user is None:
            fallback_pwd = _get_dashboard_password()
            if fallback_pwd and pw == fallback_pwd:
                user = {"email": email or "admin", "role": "admin", "name": "Admin"}

        if user:
            session.permanent = True
            session["authenticated"] = True
            session["email"]          = user["email"]
            session["role"]           = user.get("role", "viewer")
            session["name"]           = user.get("name", "User")
            return redirect("/")

        return LOGIN_HTML.replace(
            "{error}", '<div class="err">Falsche E-Mail oder Passwort</div>')

    if session.get("authenticated"):
        return redirect("/")
    return LOGIN_HTML.replace("{error}", "")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/api/me")
@login_required
def api_me():
    return _cors(jsonify({
        "email": session.get("email", ""),
        "name":  session.get("name", ""),
        "role":  session.get("role", "viewer"),
    }))


@app.route("/admin/add-user", methods=["GET", "POST"])
@login_required
def add_user():
    if session.get("role") != "admin":
        return "Kein Zugriff", 403

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        pw    = request.form.get("password", "")
        name  = request.form.get("name", "")
        role  = request.form.get("role", "viewer")

        if not email or not pw:
            return "E-Mail und Passwort erforderlich", 400

        users_file = BASE_DIR / "data" / "users.json"
        users = _load_users()

        if any(u["email"].lower() == email.lower() for u in users):
            return "User existiert bereits", 400

        users.append({
            "email":         email,
            "password_hash": hashlib.sha256(pw.encode()).hexdigest(),
            "role":          role,
            "name":          name,
        })
        users_file.write_text(json.dumps(users, indent=2))
        return f"""<html><body style="font-family:monospace;background:#111;color:#eee;padding:20px">
        ✅ User <b>{email}</b> ({role}) erstellt.<br><br>
        <a href="/admin/add-user" style="color:#00ff88">Weiteren hinzufügen</a> |
        <a href="/" style="color:#00ff88">Dashboard</a>
        </body></html>"""

    return """<html><body style="font-family:monospace;background:#111;color:#eee;padding:20px">
    <h2 style="color:#00ff88;margin-bottom:20px">Neuen User hinzufügen</h2>
    <form method="POST" style="max-width:320px">
      <input name="name" placeholder="Name" style="display:block;width:100%;margin:6px 0;padding:10px;background:#1a1a2e;color:#eee;border:1px solid #333;border-radius:6px;font-family:monospace">
      <input name="email" type="email" placeholder="E-Mail" style="display:block;width:100%;margin:6px 0;padding:10px;background:#1a1a2e;color:#eee;border:1px solid #333;border-radius:6px;font-family:monospace">
      <input name="password" type="password" placeholder="Passwort" style="display:block;width:100%;margin:6px 0;padding:10px;background:#1a1a2e;color:#eee;border:1px solid #333;border-radius:6px;font-family:monospace">
      <select name="role" style="display:block;width:100%;margin:6px 0;padding:10px;background:#1a1a2e;color:#eee;border:1px solid #333;border-radius:6px;font-family:monospace">
        <option value="viewer">Viewer</option>
        <option value="admin">Admin</option>
      </select>
      <button type="submit" style="display:block;width:100%;margin-top:12px;padding:10px;background:transparent;border:1px solid #00ff88;color:#00ff88;border-radius:6px;cursor:pointer;font-family:monospace;letter-spacing:1px">USER ERSTELLEN</button>
    </form>
    <p style="margin-top:16px"><a href="/" style="color:#555">← Dashboard</a></p>
    </body></html>"""


@app.before_request
def require_login():
    public = {"/login", "/logout"}
    if request.path in public or request.path.startswith("/static/"):
        return
    if request.path.startswith("/internal/") and request.remote_addr in ("127.0.0.1", "::1"):
        return
    pwd = _get_dashboard_password()
    if pwd and not session.get("authenticated"):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Unauthorized"}), 401
        return redirect("/login")


# ── Gamma endDate cache (condition_id → (ts, end_date_str)) ───────────────────
_gamma_enddate_cache: dict = {}


def _batch_fetch_gamma_enddates(condition_ids: list) -> dict:
    now = time.time()
    uncached = [cid for cid in condition_ids
                if cid not in _gamma_enddate_cache
                or now - _gamma_enddate_cache[cid][0] > 3600]
    if uncached:
        # Gamma API batch (up to 20 at once)
        try:
            ids_str = ",".join(uncached[:20])
            r = requests.get(
                f"https://gamma-api.polymarket.com/markets?condition_ids={ids_str}",
                timeout=5
            )
            if r.status_code == 200:
                for m in r.json():
                    cid = m.get("conditionId", "")
                    if cid:
                        end = (m.get("endDate") or m.get("endDateIso")
                               or m.get("end_date_iso") or m.get("endDateTimestamp"))
                        _gamma_enddate_cache[cid] = (now, end)
        except Exception:
            pass
        # CLOB API fallback for any still-uncached IDs
        for cid in uncached:
            if cid not in _gamma_enddate_cache or _gamma_enddate_cache[cid][1] is None:
                try:
                    r2 = requests.get(
                        f"https://clob.polymarket.com/markets/{cid}",
                        timeout=5
                    )
                    if r2.status_code == 200:
                        m2 = r2.json()
                        end = (m2.get("end_date_iso") or m2.get("endDateIso")
                               or m2.get("game_start_time")
                               or m2.get("accepting_orders_until"))
                        _gamma_enddate_cache[cid] = (now, end)
                except Exception:
                    pass
        for cid in uncached:
            if cid not in _gamma_enddate_cache:
                _gamma_enddate_cache[cid] = (now, None)
    return {cid: _gamma_enddate_cache.get(cid, (0, None))[1] for cid in condition_ids}


_MONTH_MAP = {
    "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
    "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
    "jan":1,"feb":2,"mar":3,"apr":4,"jun":6,"jul":7,"aug":8,
    "sep":9,"oct":10,"nov":11,"dec":12,
}
_DATE_RE = re.compile(
    r"by\s+([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s*(\d{4}))?",
    re.IGNORECASE
)

def _parse_title_date(title: str):
    """Try to extract a deadline date from a market title like 'by April 30, 2026'."""
    m = _DATE_RE.search(title or "")
    if not m:
        return None
    mon_str, day_str, yr_str = m.group(1).lower(), m.group(2), m.group(3)
    mon = _MONTH_MAP.get(mon_str)
    if not mon:
        return None
    year = int(yr_str) if yr_str else datetime.now(timezone.utc).year
    try:
        from datetime import date as _date
        return datetime(year, mon, int(day_str), 23, 59, 59, tzinfo=timezone.utc)
    except ValueError:
        return None


def _closes_in_label(end_date_str, market_title: str = "") -> tuple:
    """Returns (label, css_class) for countdown display."""
    if not end_date_str:
        # Fallback: try to parse date from title
        dt = _parse_title_date(market_title)
        if dt is None:
            return "?", "closes-gray"
    else:
        try:
            dt = datetime.fromisoformat(str(end_date_str).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            dt = _parse_title_date(market_title)
            if dt is None:
                return "?", "closes-gray"
    try:
        now_utc = datetime.now(timezone.utc)
        diff_s = (dt - now_utc).total_seconds()
        if diff_s <= 0:
            return "ENDED", "closes-ended"
        if diff_s < 3600:
            return f"{int(diff_s // 60)}m", "closes-red"
        elif diff_s < 6 * 3600:
            h, m = int(diff_s // 3600), int((diff_s % 3600) // 60)
            return f"{h}h {m}m", "closes-orange"
        elif diff_s < 24 * 3600:
            return f"{int(diff_s // 3600)}h", "closes-yellow"
        else:
            d, h = int(diff_s // 86400), int((diff_s % 86400) // 3600)
            return f"{d}d {h}h", "closes-gray"
    except Exception:
        return "?", "closes-gray"


# ── SQLite Metrics DB ──────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(str(DB_FILE))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS balance_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            balance_usdc REAL NOT NULL,
            portfolio_total REAL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_balance_ts ON balance_snapshots(ts)")
    # Migration: add portfolio_total column if not yet present
    try:
        conn.execute("ALTER TABLE balance_snapshots ADD COLUMN portfolio_total REAL")
    except Exception:
        pass  # Column already exists
    conn.commit()
    conn.close()


def db_insert_balance(balance: float, portfolio_total: float | None = None):
    try:
        conn = sqlite3.connect(str(DB_FILE))
        conn.execute(
            "INSERT INTO balance_snapshots (ts, balance_usdc, portfolio_total) VALUES (?,?,?)",
            (int(time.time()), balance, portfolio_total),
        )
        conn.execute("DELETE FROM balance_snapshots WHERE ts < ?", (int(time.time()) - 30 * 86400,))
        conn.commit()
        conn.close()
    except Exception:
        pass


def db_get_balance_history(hours: int = 24):
    try:
        conn = sqlite3.connect(str(DB_FILE))
        since = int(time.time()) - hours * 3600
        rows = conn.execute(
            "SELECT ts, balance_usdc, portfolio_total FROM balance_snapshots WHERE ts >= ? ORDER BY ts ASC",
            (since,)
        ).fetchall()
        conn.close()
        return [
            {"ts": r[0], "balance": round(r[1], 2),
             "portfolio_total": round(r[2], 2) if r[2] is not None else round(r[1], 2)}
            for r in rows
        ]
    except Exception:
        return []


# ── On-Chain Balance ──────────────────────────────────────────────────────────

_current_balance: dict = {"value": None, "ts": 0.0}
POLYMARKET_DATA_API = "https://data-api.polymarket.com"
_polymarket_positions: dict = {"data": [], "ts": 0.0}


def fetch_polymarket_positions_sync() -> list:
    env = load_env()
    proxy = env.get("POLYMARKET_ADDRESS", PROXY_ADDRESS)
    try:
        url = f"{POLYMARKET_DATA_API}/positions?user={proxy}&sizeThreshold=.01&limit=500"
        resp = requests.get(url, timeout=10, headers={"User-Agent": "KongTradeBot/2.0"})
        if resp.status_code == 200:
            data = resp.json()
            return data if isinstance(data, list) else data.get("data", [])
    except Exception:
        pass
    return []


def _positions_updater_thread():
    global _polymarket_positions
    time.sleep(8)
    while True:
        try:
            positions = fetch_polymarket_positions_sync()
            if positions is not None:
                _polymarket_positions = {"data": positions, "ts": time.time()}
                try:
                    socketio.emit("positions_update", {"count": len(positions), "ts": time.time()})
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(60)




def fetch_onchain_balance_sync() -> float | None:
    env = load_env()
    proxy = env.get("POLYMARKET_ADDRESS", PROXY_ADDRESS)
    padded = proxy.lower().replace("0x", "").zfill(64)
    data = f"0x70a08231{padded}"
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [{"to": USDC_CONTRACT, "data": data}, "latest"],
        "id": 1,
    }
    for rpc in POLYGON_RPCS:
        try:
            resp = requests.post(rpc, json=payload,
                                 headers={"Content-Type": "application/json"},
                                 timeout=10)
            if resp.status_code == 200:
                result = resp.json().get("result", "0x0")
                return int(result, 16) / 1_000_000
        except Exception:
            continue
    return None


def _balance_updater_thread():
    global _current_balance
    # Initial fetch immediately
    time.sleep(3)
    while True:
        try:
            bal = fetch_onchain_balance_sync()
            if bal is not None:
                _current_balance = {"value": round(bal, 2), "ts": time.time()}
                positions = _polymarket_positions.get("data", [])
                in_pos = round(sum(float(p.get("currentValue") or 0) for p in positions), 2)
                ptotal = round(bal + in_pos, 2) if in_pos >= 0 else None
                db_insert_balance(bal, portfolio_total=ptotal)
                try:
                    socketio.emit("balance_update", {"balance": round(bal, 2), "ts": time.time()})
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(30)


# ── Helper functions ───────────────────────────────────────────────────────────

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


def get_log_lines(n=100):
    # Prefer undated rolling log (bot.log) — most up-to-date
    rolling = LOG_DIR / "bot.log"
    if rolling.exists():
        try:
            return rolling.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
        except Exception:
            pass
    # Fallback: today's dated file, then most recent dated file
    today = date.today().strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"bot_{today}.log"
    if not log_file.exists():
        try:
            files = sorted(LOG_DIR.glob("bot_*.log"), key=lambda f: f.stat().st_mtime, reverse=True)
            if files:
                log_file = files[0]
            else:
                return []
        except Exception:
            return []
    try:
        return log_file.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
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
        if os.name == "nt":
            out = subprocess.check_output("tasklist", shell=True, text=True)
            return "python" in out.lower(), None
        else:
            out = subprocess.check_output(["pgrep", "-f", "main.py"], text=True)
            pids = [int(p) for p in out.strip().split() if p.strip()]
            return bool(pids), pids[0] if pids else None
    except Exception:
        return False, None


def _get_bot_uptime():
    """Liest Bot-Startzeit aus lock- oder pid-Datei."""
    for fname in ("bot.pid", "bot.lock"):
        f = BASE_DIR / fname
        if f.exists():
            try:
                mtime = f.stat().st_mtime
                return int(time.time() - mtime)
            except Exception:
                pass
    return None


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
    cats = {}
    for t in archive:
        cat = t.get("kategorie", "Sonstiges") or "Sonstiges"
        cats[cat] = cats.get(cat, 0) + 1
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
        "wallet_perf":  {k[:10] + "...": v for k, v in wallet_perf.items()},
    }


def _parse_closes_in(closes_at_str):
    """Returns (closes_in_s, closes_in_h) or (None, None)."""
    if not closes_at_str:
        return None, None
    try:
        closes_dt = datetime.fromisoformat(closes_at_str.replace("Z", "+00:00"))
        if closes_dt.tzinfo is None:
            closes_dt = closes_dt.replace(tzinfo=timezone.utc)
        diff = (closes_dt - datetime.now(timezone.utc)).total_seconds()
        s = max(0.0, diff)
        return int(s), round(s / 3600, 2)
    except Exception:
        return None, None


# ── REST API Endpoints ────────────────────────────────────────────────────────

def _cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/")
def index():
    return send_from_directory(str(BASE_DIR), "dashboard.html")


_START_FILE = BASE_DIR / "portfolio_start_value.json"

def _get_or_create_start_snapshot(portfolio_total: float, cash: float) -> dict:
    """Lädt oder erstellt einmalig portfolio_start_value.json."""
    if _START_FILE.exists():
        try:
            snap = json.loads(_START_FILE.read_text())
            if snap.get("start_value", 0) > 0:
                return snap
        except Exception:
            pass
    if portfolio_total <= 0:
        return {"start_value": 0.0, "start_cash": 0.0, "start_time": ""}
    snap = {
        "start_time":  datetime.now(timezone.utc).isoformat(),
        "start_value": round(portfolio_total, 2),
        "start_cash":  round(cash or 0.0, 2),
    }
    try:
        _START_FILE.write_text(json.dumps(snap, indent=2))
    except Exception:
        pass
    return snap


@app.route("/api/balance")
def api_balance():
    env = load_env()
    initial = float(env.get("BOT_INITIAL_BALANCE_USD", "988.49"))
    cash = _current_balance.get("value")
    last_ts = _current_balance.get("ts", 0)

    history_24h = db_get_balance_history(24)
    history_7d  = db_get_balance_history(168)
    history_30d = db_get_balance_history(720)

    if cash is None and history_24h:
        cash = history_24h[-1]["balance"]

    positions = _polymarket_positions.get("data", [])
    in_positions = round(sum(float(p.get("currentValue") or p.get("value") or 0) for p in positions), 2)
    portfolio_total = round((cash or 0) + in_positions, 2)
    to_win_total = round(sum(float(p.get("toWin") or p.get("maxPayout") or p.get("size") or 0) for p in positions), 2)
    unclaimed = [p for p in positions if any(p.get(k) for k in ("redeemable", "isRedeemable", "is_redeemable"))]
    unclaimed_amount = round(sum(float(p.get("currentValue") or 0) for p in unclaimed), 2)
    unrealized_pnl = round(sum(float(p.get("unrealizedPnl") or 0) for p in positions), 2)

    delta_total_cash = round(cash - initial, 2) if cash is not None else 0

    # SEIT START: portfolio_total vs start-snapshot
    start_snap = _get_or_create_start_snapshot(portfolio_total, cash)
    start_value = start_snap.get("start_value", 0)
    delta_since_start = round(portfolio_total - start_value, 2) if start_value > 0 else None

    h1_cut = time.time() - 3600
    h1_pts = [h for h in history_24h if h["ts"] >= h1_cut]
    delta_1h = round(cash - h1_pts[0]["balance"], 2) if h1_pts and cash is not None else 0
    delta_24h_cash = round(cash - history_24h[0]["balance"], 2) if history_24h and cash is not None else 0

    return _cors(jsonify({
        "current":          cash,
        "cash":             cash,
        "in_positions":     in_positions,
        "portfolio_total":  portfolio_total,
        "to_win_total":     to_win_total,
        "unclaimed_amount": unclaimed_amount,
        "unclaimed_count":  len(unclaimed),
        "unrealized_pnl":   unrealized_pnl,
        "initial":          initial,
        "delta_total":      delta_total_cash,
        "delta_since_start": delta_since_start,
        "start_value":      start_value,
        "delta_24h":        delta_24h_cash,
        "delta_1h":         delta_1h,
        "last_fetch_ts":    last_ts,
        "positions_ts":     _polymarket_positions.get("ts", 0),
        "history_24h":      history_24h[-200:],
        "history_7d":       history_7d[-200:],
        "history_30d":      history_30d[-200:],
    }))


@app.route("/api/positions")
def api_positions():
    state   = load_json(STATE_FILE) or {}
    archive = load_json(ARCHIVE_FILE) or []

    # OPEN positions
    open_pos = []
    for p in state.get("open_positions", []):
        closes_in_s, closes_in_h = _parse_closes_in(p.get("market_closes_at"))
        entry_price = float(p.get("entry_price", 0) or 0)
        size_usdc   = float(p.get("size_usdc", 0) or 0)
        shares      = float(p.get("shares", 0) or 0)
        profit_win  = round(shares - size_usdc, 2) if shares > size_usdc else 0
        open_pos.append({
            "order_id":      str(p.get("order_id", ""))[:16],
            "market":        (p.get("market_question") or "Unknown")[:72],
            "outcome":       p.get("outcome", ""),
            "entry_price_pct": round(entry_price * 100, 1),
            "size_usdc":     round(size_usdc, 2),
            "shares":        round(shares, 3),
            "profit_if_win": profit_win,
            "closes_in_h":   closes_in_h,
            "closes_in_s":   closes_in_s,
            "wallet":        get_wallet_name(p.get("source_wallet", "")),
            "opened_at":     p.get("opened_at", ""),
        })
    open_pos.sort(key=lambda x: (x.get("closes_in_h") or 9999))

    # PENDING positions
    pending = []
    for oid, pd in (state.get("pending_data") or {}).items():
        submitted = pd.get("submitted_at", 0)
        age_s = int(time.time() - submitted) if isinstance(submitted, (int, float)) and submitted > 0 else 0
        pending.append({
            "order_id":      oid[:16] + "...",
            "market":        (pd.get("market_question") or "")[:72],
            "outcome":       pd.get("outcome", ""),
            "entry_price_pct": round(float(pd.get("entry_price", 0) or 0) * 100, 1),
            "size_usdc":     round(float(pd.get("size_usdc", 0) or 0), 2),
            "age_s":         age_s,
            "stuck":         age_s > 60,
        })

    # RESOLVED positions
    resolved = []
    for t in archive:
        if not t.get("aufgeloest"):
            continue
        pnl  = float(t.get("gewinn_verlust_usdc", 0) or 0)
        size = float(t.get("einsatz_usdc", 0) or 0)
        roi  = round(pnl / size * 100, 1) if size > 0 else 0
        resolved.append({
            "time":     f"{t.get('datum', '')} {t.get('zeit', '')}",
            "market":   (t.get("markt") or t.get("market_question") or "")[:72],
            "outcome":  t.get("ergebnis_seite", t.get("outcome", "")),
            "result":   t.get("ergebnis", ""),
            "pnl":      round(pnl, 2),
            "roi":      roi,
            "wallet":   get_wallet_name(t.get("source_wallet", "")),
            "size_usdc": round(size, 2),
        })
    resolved = list(reversed(resolved))[:50]

    return _cors(jsonify({
        "open":    open_pos,
        "pending": pending,
        "resolved": resolved,
        "counts": {
            "open":    len(open_pos),
            "pending": len(pending),
            "resolved": len(resolved),
        },
    }))



@app.route("/api/portfolio")
def api_portfolio():
    positions = _polymarket_positions.get("data", [])

    # Gamma API endDate lookup (batched, cached 1h)
    condition_ids = [p.get("conditionId", "") for p in positions if p.get("conditionId")]
    enddate_map = _batch_fetch_gamma_enddates(condition_ids) if condition_ids else {}

    # Source-wallet mapping from bot_state (condition_id → wallet name)
    state = load_json(STATE_FILE) or {}
    wallet_map = {}
    for op in state.get("open_positions", []):
        cid = op.get("market_id", "")
        if cid:
            wallet_map[cid] = get_wallet_name(op.get("source_wallet", ""))

    result = []
    for p in positions:
        avg_price   = float(p.get("avgPrice") or p.get("averagePrice") or 0)
        cur_price   = float(p.get("curPrice") or p.get("currentPrice") or p.get("price") or 0)
        shares      = float(p.get("size") or p.get("shares") or 0)
        traded_usdc = float(p.get("initialValue") or p.get("cost") or (avg_price * shares) or 0)
        cur_value   = float(p.get("currentValue") or p.get("value") or (cur_price * shares) or 0)
        to_win      = float(p.get("toWin") or p.get("maxPayout") or shares or 0)
        pnl_pct     = round((cur_value - traded_usdc) / max(0.001, traded_usdc) * 100, 1) if traded_usdc > 0 else 0
        result.append({
            "condition_id":  p.get("conditionId", ""),
            "market":        (p.get("title") or p.get("question") or p.get("market") or "")[:80],
            "outcome":       p.get("outcome", ""),
            "avg_price_pct": round(avg_price * 100, 1),
            "cur_price_pct": round(cur_price * 100, 1),
            "shares":        round(shares, 4),
            "traded":        round(traded_usdc, 2),
            "current_value": round(cur_value, 2),
            "to_win":        round(to_win, 2),
            "pnl_usdc":      round(cur_value - traded_usdc, 2),
            "pnl_pct":       pnl_pct,
        })
        end_date_str = (p.get("endDate") or p.get("endDateIso") or p.get("end_date")
                        or enddate_map.get(p.get("conditionId", "")))
        mkt_title = p.get("title") or p.get("question") or p.get("market") or ""
        ci_label, ci_class = _closes_in_label(end_date_str, market_title=mkt_title)
        redeemable = bool(any(p.get(k) for k in ("redeemable", "isRedeemable", "is_redeemable")))
        if redeemable and cur_value > 0.01:
            pos_state = "RESOLVED_WON"
        elif redeemable:
            pos_state = "RESOLVED_LOST"
        elif cur_price < 0.005 and cur_value < 0.01:
            pos_state = "TRADING_ENDED"
        else:
            pos_state = "ACTIVE"
        result[-1].update({
            "redeemable":      redeemable,
            "position_state":  pos_state,
            "asset_id":        p.get("asset_id") or p.get("tokenId") or "",
            "closes_in_label": ci_label,
            "closes_in_class": ci_class,
            "wallet":          wallet_map.get(p.get("conditionId", ""), "—"),
        })
    result.sort(key=lambda x: x["current_value"], reverse=True)
    active   = [r for r in result if r["position_state"] == "ACTIVE"]
    inactive = [r for r in result if r["position_state"] != "ACTIVE"]
    total_value  = round(sum(r["current_value"] for r in result), 2)
    total_traded = round(sum(r["traded"] for r in result), 2)
    total_to_win = round(sum(r["to_win"] for r in result), 2)
    total_pnl    = round(sum(r["pnl_usdc"] for r in result), 2)

    # Midnight snapshot → today_pnl_portfolio = Wertveränderung seit Tagesbeginn
    today_str = date.today().isoformat()
    snap = _get_midnight_snapshot(today_str, total_value)
    today_pnl_portfolio = round(total_value - snap["snapshot_value"], 2)

    return _cors(jsonify({
        "positions":            active,
        "inactive_positions":   inactive,
        "count":                len(active),
        "count_all":            len(result),
        "total_value":          total_value,
        "total_traded":         total_traded,
        "total_to_win":         total_to_win,
        "total_pnl":            total_pnl,
        "redeemable_count":     sum(1 for r in result if r["redeemable"]),
        "today_pnl_portfolio":  today_pnl_portfolio,
        "snapshot_value":       snap["snapshot_value"],
        "snapshot_created_at":  snap.get("created_at", ""),
        "ts":                   _polymarket_positions.get("ts", 0),
    }))


@app.route("/internal/portfolio")
def internal_portfolio():
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return jsonify({"error": "forbidden"}), 403
    return api_portfolio()


@app.route("/api/health")
def api_health():
    running, pid = is_bot_running()
    env = load_env()
    uptime_s = _get_bot_uptime()

    hb_age = None
    hb_file = BASE_DIR / "heartbeat.txt"
    if hb_file.exists():
        hb_age = int(time.time() - hb_file.stat().st_mtime)

    # Last error from log
    last_error = None
    lines = get_log_lines(300)
    for line in reversed(lines):
        if "ERROR" in line or "CRITICAL" in line:
            raw = line.strip()[-200:]
            if "not enough balance" in raw or ("allowance" in raw.lower() and "balance" in raw.lower()):
                last_error = "⚠️ Balance zu gering für Orders — Wins claimen oder USDC aufladen"
            elif "geoblock" in raw.lower() or "Trading restricted" in raw:
                last_error = "🚫 Geoblock — Bot-IP prüfen oder VPN deaktivieren"
            elif "403" in raw and "restricted" in raw.lower():
                last_error = "🚫 HTTP 403 — Zugriff verweigert (Geoblock)"
            else:
                last_error = raw[-150:]
            break

    # Last trade time
    last_trade_at = None
    for line in reversed(lines):
        if "LIVE ORDER" in line or "DRY-RUN" in line or "Order gesendet" in line:
            try:
                last_trade_at = line[:19]
            except Exception:
                pass
            break

    # System resources
    cpu_pct = ram_pct = None
    try:
        import psutil
        cpu_pct = round(psutil.cpu_percent(interval=0.1), 1)
        ram_pct = round(psutil.virtual_memory().percent, 1)
    except Exception:
        pass

    # Count WS MATCHED events in recent logs
    ws_events_min = sum(1 for l in lines[-60:] if "CONFIRMED" in l or "MATCHED" in l or "NEUER TRADE" in l or "Signal buffered" in l or "Order erstellt" in l)

    return _cors(jsonify({
        "bot_running":    running,
        "bot_pid":        pid,
        "uptime_s":       uptime_s,
        "dry_run":        env.get("DRY_RUN", "true").lower() == "true",
        "heartbeat_age_s": hb_age,
        "heartbeat_ok":   (hb_age is not None and hb_age < 360),
        "last_error":     last_error,
        "last_trade_at":  last_trade_at,
        "cpu_pct":        cpu_pct,
        "ram_pct":        ram_pct,
        "ws_events_recent": ws_events_min,
        "balance":        _current_balance.get("value"),
        "balance_ts":     _current_balance.get("ts"),
        "ts":             int(time.time()),
    }))


@app.route("/api/stats/session")
def api_stats_session():
    archive = load_json(ARCHIVE_FILE) or []
    today   = date.today().isoformat()
    today_trades  = [t for t in archive if t.get("datum") == today]
    today_filled  = [t for t in today_trades if t.get("aufgeloest")]
    today_wins    = [t for t in today_filled if t.get("ergebnis") == "GEWINN"]
    today_losses  = [t for t in today_filled if t.get("ergebnis") == "VERLUST"]
    today_pnl     = sum(float(t.get("gewinn_verlust_usdc", 0) or 0) for t in today_filled)
    today_won_usdc  = sum(float(t.get("gewinn_verlust_usdc", 0) or 0) for t in today_wins)
    today_lost_usdc = sum(float(t.get("gewinn_verlust_usdc", 0) or 0) for t in today_losses)

    best  = max(today_filled, key=lambda t: float(t.get("gewinn_verlust_usdc", 0) or 0), default=None)
    worst = min(today_filled, key=lambda t: float(t.get("gewinn_verlust_usdc", 0) or 0), default=None)

    streak = 0
    for t in reversed(today_filled):
        r = t.get("ergebnis", "")
        if r == "GEWINN":
            if streak >= 0: streak += 1
            else: break
        elif r == "VERLUST":
            if streak <= 0: streak -= 1
            else: break

    lines = get_log_lines(500)
    signals_today  = sum(1 for l in lines if "NEUER TRADE erkannt" in l)
    orders_tried   = sum(1 for l in lines if "LIVE ORDER" in l or "DRY-RUN" in l)
    orders_skipped = sum(1 for l in lines if "übersprungen" in l or "Order übersprungen" in l)
    orders_rejected = sum(1 for l in lines if "abgelehnt" in l or "Preis zu extrem" in l)

    return _cors(jsonify({
        "today_date":       today,
        "signals_today":    signals_today,
        "orders_tried":     orders_tried,
        "orders_filled":    len(today_trades),
        "orders_skipped":   orders_skipped,
        "orders_rejected":  orders_rejected,
        "resolved_today":   len(today_filled),
        "wins_today":       len(today_wins),
        "losses_today":     len(today_losses),
        "pnl_today":        round(today_pnl, 2),
        "won_usdc_today":   round(today_won_usdc, 2),
        "lost_usdc_today":  round(today_lost_usdc, 2),
        "win_rate_today":   round(len(today_wins) / max(1, len(today_filled)) * 100, 1),
        "streak":           streak,
        "best_trade":       {
            "market": (best.get("markt") or "")[:50],
            "pnl":    round(float(best.get("gewinn_verlust_usdc", 0) or 0), 2),
        } if best else None,
        "worst_trade":      {
            "market": (worst.get("markt") or "")[:50],
            "pnl":    round(float(worst.get("gewinn_verlust_usdc", 0) or 0), 2),
        } if worst else None,
    }))


@app.route("/api/stats/wallets")
def api_stats_wallets():
    archive = load_json(ARCHIVE_FILE) or []
    closed  = [t for t in archive if t.get("aufgeloest")]
    wallet_stats: dict = {}
    for t in closed:
        w    = t.get("source_wallet", "Unknown") or "Unknown"
        name = get_wallet_name(w)
        if w not in wallet_stats:
            wallet_stats[w] = {"name": name, "address": w[:10] + "...", "trades": 0,
                               "wins": 0, "losses": 0, "pnl": 0.0, "invested": 0.0}
        wallet_stats[w]["trades"]   += 1
        wallet_stats[w]["pnl"]      += float(t.get("gewinn_verlust_usdc", 0) or 0)
        wallet_stats[w]["invested"] += float(t.get("einsatz_usdc", 0) or 0)
        if t.get("ergebnis") == "GEWINN":
            wallet_stats[w]["wins"] += 1
        elif t.get("ergebnis") == "VERLUST":
            wallet_stats[w]["losses"] += 1

    result = []
    for s in wallet_stats.values():
        trades   = s["trades"]
        invested = s["invested"]
        pnl      = s["pnl"]
        result.append({
            "name":      s["name"],
            "address":   s["address"],
            "trades":    trades,
            "wins":      s["wins"],
            "losses":    s["losses"],
            "win_rate":  round(s["wins"] / max(1, trades) * 100, 1),
            "pnl":       round(pnl, 2),
            "roi":       round(pnl / max(0.01, invested) * 100, 1),
            "invested":  round(invested, 2),
        })
    result.sort(key=lambda x: x["pnl"], reverse=True)
    return _cors(jsonify({"wallets": result}))


@app.route("/api/resolutions")
def api_resolutions():
    state   = load_json(STATE_FILE) or {}
    archive = load_json(ARCHIVE_FILE) or []

    upcoming = []
    for p in state.get("open_positions", []):
        closes_in_s, closes_in_h = _parse_closes_in(p.get("market_closes_at"))
        if closes_in_s is None or closes_in_s <= 0:
            continue
        entry_price = float(p.get("entry_price", 0) or 0)
        size_usdc   = float(p.get("size_usdc", 0) or 0)
        shares      = float(p.get("shares", 0) or 0)
        profit_win  = round(max(0, shares - size_usdc), 2)
        upcoming.append({
            "market":        (p.get("market_question") or "Unknown")[:72],
            "outcome":       p.get("outcome", ""),
            "closes_in_s":   closes_in_s,
            "closes_in_h":   closes_in_h,
            "closes_at":     p.get("market_closes_at", ""),
            "size_usdc":     round(size_usdc, 2),
            "profit_if_win": profit_win,
        })
    # Weather shadow positions resolving within 48h
    sp_file = BASE_DIR / "data" / "shadow_portfolio.json"
    try:
        sp_data = json.loads(sp_file.read_text())
        weather_open = [
            p for p in sp_data.get("positions", [])
            if p.get("strategy") == "WEATHER" and p.get("status") == "OPEN"
        ]
    except Exception:
        weather_open = []
    if weather_open:
        w_cids = list({p.get("market_id", "") for p in weather_open if p.get("market_id")})
        w_end_map = _batch_fetch_gamma_enddates(w_cids)
        seen_w = set()
        for p in weather_open:
            cid = p.get("market_id", "")
            if cid in seen_w:
                continue
            end_str = w_end_map.get(cid)
            closes_in_s, _ = _parse_closes_in(end_str)
            if closes_in_s is None or closes_in_s <= 0 or closes_in_s > 48 * 3600:
                continue
            seen_w.add(cid)
            invested = float(p.get("invested_usdc", 0) or 0)
            shares   = float(p.get("shares", 0) or 0)
            upcoming.append({
                "market":        (p.get("question") or "Unknown")[:72],
                "outcome":       p.get("outcome", ""),
                "closes_in_s":   closes_in_s,
                "closes_in_h":   round(closes_in_s / 3600, 2),
                "closes_at":     end_str or "",
                "size_usdc":     round(invested, 2),
                "profit_if_win": round(max(0, shares - invested), 2),
                "is_weather":    True,
            })

    upcoming.sort(key=lambda x: x["closes_in_s"])

    # Recent resolutions
    recent = []
    for t in archive:
        if not t.get("aufgeloest"):
            continue
        pnl = float(t.get("gewinn_verlust_usdc", 0) or 0)
        recent.append({
            "time":   f"{t.get('datum', '')} {t.get('zeit', '')}",
            "market": (t.get("markt") or t.get("market_question") or "")[:60],
            "result": t.get("ergebnis", ""),
            "pnl":    round(pnl, 2),
        })
    recent = list(reversed(recent))[:10]

    return _cors(jsonify({
        "upcoming":           upcoming[:8],
        "total_at_stake":     round(sum(x["size_usdc"] for x in upcoming), 2),
        "max_possible_win":   round(sum(x["profit_if_win"] for x in upcoming), 2),
        "recent_resolutions": recent,
    }))


@app.route("/api/logs")
def api_logs():
    n = min(int(request.args.get("n", 150)), 500)
    filter_type = request.args.get("filter", "all")
    search = request.args.get("search", "").lower()
    lines = get_log_lines(500)

    if filter_type == "orders":
        lines = [l for l in lines if "LIVE ORDER" in l or "DRY-RUN" in l or
                 "Order gesendet" in l or "Order pending" in l or "übersprungen" in l]
    elif filter_type == "signals":
        lines = [l for l in lines if "NEUER TRADE" in l or "buffered" in l or
                 "Multiplikator" in l or "Signal" in l]
    elif filter_type == "errors":
        lines = [l for l in lines if "ERROR" in l or "WARNING" in l or
                 "CRITICAL" in l or "Exception" in l or "Traceback" in l or "Kill-Switch" in l]
    elif filter_type == "resolutions":
        lines = [l for l in lines if "GEWINN" in l or "VERLUST" in l or
                 "resolver" in l.lower() or "resolved" in l.lower() or "aufgelöst" in l.lower()]

    if search:
        lines = [l for l in lines if search in l.lower()]

    return _cors(jsonify({"count": len(lines), "lines": lines[-n:]}))


@app.route("/api/whatif")
def api_whatif():
    sim_mult = float(request.args.get("multiplier", 0.15))
    env      = load_env()
    archive  = load_json(ARCHIVE_FILE) or []
    today    = date.today().isoformat()
    today_trades = [t for t in archive if t.get("datum") == today]
    actual_mult  = float(env.get("COPY_SIZE_MULTIPLIER", "0.15"))
    min_size     = float(env.get("MIN_TRADE_SIZE_USD", "5.0"))

    simulated = []
    for t in today_trades:
        actual_size = float(t.get("einsatz_usdc", 0) or 0)
        if actual_mult > 0 and actual_size > 0:
            whale_size = actual_size / actual_mult
            sim_size   = round(whale_size * sim_mult, 2)
            simulated.append({
                "market":       (t.get("markt") or "")[:50],
                "actual_size":  round(actual_size, 2),
                "sim_size":     sim_size,
                "would_exec":   sim_size >= min_size,
            })

    executed  = [s for s in simulated if s["would_exec"]]
    total_vol = round(sum(s["sim_size"] for s in executed), 2)

    return _cors(jsonify({
        "actual_mult":   actual_mult,
        "sim_mult":      sim_mult,
        "actual_trades": len(today_trades),
        "sim_trades":    len(executed),
        "sim_volume":    total_vol,
        "trades":        simulated[:20],
    }))


@app.route("/api/summary")
def api_summary():
    stats = get_stats()
    running, pid = is_bot_running()
    env = load_env()
    hb_age = None
    try:
        hb_file = BASE_DIR / "heartbeat.txt"
        if hb_file.exists():
            hb_age = round(time.time() - hb_file.stat().st_mtime, 1)
    except Exception:
        pass
    # Budget-Utilization aus bot_state.json berechnen
    total_invested_open = 0.0
    max_invested_usd = 0.0
    budget_utilization_pct = 0.0
    open_positions = []
    try:
        state = load_json(STATE_FILE) or {}
        open_positions = state.get("open_positions", [])
        total_invested_open = sum(float(p.get("size_usdc", 0) or 0) for p in open_positions)
        # Read actual on-chain balance from cache written by balance_fetcher
        balance_cache = load_json(BASE_DIR / "data" / "balance_cache.json") or {}
        if balance_cache.get("balance_usdc", 0) > 0:
            portfolio_budget = float(balance_cache["balance_usdc"])
            max_portfolio_pct = float(balance_cache.get("max_portfolio_pct",
                                      env.get("MAX_PORTFOLIO_PCT", "0.5")))
        else:
            # Fallback: PORTFOLIO_BUDGET_USD is a 100M sentinel → use 1000 as default
            _raw = float(env.get("PORTFOLIO_BUDGET_USD", "1000") or "1000")
            portfolio_budget = _raw if _raw < 100_000 else 1000.0
            max_portfolio_pct = float(env.get("MAX_PORTFOLIO_PCT", "0.5") or "0.5")
        max_invested_usd = portfolio_budget * max_portfolio_pct
        budget_utilization_pct = round(
            total_invested_open / max(0.01, max_invested_usd) * 100, 1
        )
    except Exception:
        pass

    data = {
        "bot_running": running,
        "bot_pid": pid,
        "dry_run": env.get("DRY_RUN", "true").lower() == "true",
        "heartbeat_age_s": hb_age,
        "max_trade_size_usd": env.get("MAX_TRADE_SIZE_USD"),
        "copy_size_multiplier": env.get("COPY_SIZE_MULTIPLIER"),
        "max_daily_loss_usd": env.get("MAX_DAILY_LOSS_USD"),
        "total_invested_usd": round(total_invested_open, 2),
        "max_invested_usd": round(max_invested_usd, 2),
        "budget_utilization_pct": budget_utilization_pct,
        **{k: stats[k] for k in ("total_trades", "closed", "wins", "losses",
                                  "win_rate", "pnl", "today_trades", "today_pnl")},
        "open":     len(open_positions),
        "invested": round(total_invested_open, 2),
    }
    return _cors(jsonify(data))


@app.route("/api/signals")
def api_signals():
    """Letzte 30 Bot-Aktionen aus Log (Live Signal Feed)."""
    signals = []
    log_file = LOG_DIR / "bot.log"
    if not log_file.exists():
        # fallback: neueste datierte Log-Datei
        files = sorted(LOG_DIR.glob("bot_*.log"), key=lambda f: f.stat().st_mtime, reverse=True)
        if files:
            log_file = files[0]
        else:
            return _cors(jsonify({"signals": []}))
    try:
        lines = log_file.read_text(errors="replace").splitlines()[-200:]
    except Exception:
        return _cors(jsonify({"signals": []}))
    _BLOCK_KW  = ("blockiert", "rejected", "skip", "budget", "SKIP", "Risk", "blacklist", "Blacklist")
    _REASON_KW = ("weil", "because", "budget", "blacklist", "Blacklist", "min_size", "cap", "Cap")
    for line in reversed(lines):
        if not any(k in line for k in [
            "[WS]", "[RSS]", "ANOMALY", "Weather",
            "TRADE", "EXIT", "COPY", "Signal",
            "BUY", "SELL", "Opportunit",
            "CopyOrder", "blockiert", "rejected", "skip", "SKIP"]):
            continue
        t = line[:19] if len(line) > 19 else ""
        typ = "INFO"
        if "[WS]" in line:       typ = "WS"
        elif "[RSS]" in line:    typ = "RSS"
        elif "ANOMALY" in line:  typ = "ANOMALY"
        elif "Weather" in line:  typ = "WEATHER"
        elif "BUY" in line or "COPY" in line or "CopyOrder" in line: typ = "TRADE"
        elif "EXIT" in line or "SELL" in line: typ = "EXIT"

        # Determine action badge
        action = None
        reason = None
        if "CopyOrder[LIVE]" in line or ("Order erstellt" in line and "DRY" not in line):
            action = "kopiert"
        elif "DRY" in line and any(k in line for k in ("CopyOrder", "Order", "BUY", "SELL")):
            action = "dry-run"
        elif any(k in line for k in _BLOCK_KW):
            action = "blockiert"
            # Extract reason from line
            msg = line[30:]
            for rk in _REASON_KW:
                idx = msg.find(rk)
                if idx >= 0:
                    reason = msg[idx:idx+60].split("\n")[0].strip()
                    break

        signals.append({
            "time":    t[11:19] if len(t) >= 19 else t,
            "type":    typ,
            "action":  action,
            "reason":  reason,
            "message": line[30:120].strip(),
        })
        if len(signals) >= 30:
            break
    return _cors(jsonify({"signals": signals}))


@app.route("/api/weather/toggle", methods=["POST"])
def toggle_weather():
    """Schaltet WEATHER_DRY_RUN in .env um und startet Bot neu."""
    try:
        env_text = ENV_FILE.read_text()
        if "WEATHER_DRY_RUN=true" in env_text:
            env_text = env_text.replace("WEATHER_DRY_RUN=true", "WEATHER_DRY_RUN=false")
            msg = "Weather Trading LIVE aktiviert!"
        else:
            env_text = env_text.replace("WEATHER_DRY_RUN=false", "WEATHER_DRY_RUN=true")
            msg = "Weather Trading zurück auf DRY-RUN"
        ENV_FILE.write_text(env_text)
        os.system("systemctl restart kongtrade-bot &")
        return _cors(jsonify({"status": "ok", "msg": msg}))
    except Exception as e:
        return _cors(jsonify({"status": "error", "msg": str(e)}))


@app.route("/api/weather_status")
def api_weather_status():
    """Liefert Weather-Scout-Status: Konfiguration + letzte Opportunities aus bot.log."""
    env_text = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    def _env(key, default=""):
        for line in env_text.splitlines():
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip()
        return default

    config = {
        "enabled": _env("WEATHER_TRADING_ENABLED", "false").lower() == "true",
        "dry_run": _env("WEATHER_DRY_RUN", "true").lower() == "true",
        "max_daily_usd": _env("WEATHER_MAX_DAILY_USD", "10"),
        "max_price": _env("WEATHER_MAX_PRICE", "0.20"),
    }

    # Parse bot.log for recent WeatherScout lines (last 2000 lines)
    log_file = LOG_DIR / "bot.log"
    opportunities = []
    scan_info = {"total_markets": 0, "last_scan": None}
    try:
        if log_file.exists():
            lines = log_file.read_text(errors="replace").splitlines()
            recent = lines[-2000:]
            for line in reversed(recent):
                if "[WeatherScout]" not in line:
                    continue
                ts = line[:19] if len(line) > 19 else ""
                if "Total:" in line and "Opportunities" in line:
                    try:
                        n = int(line.split("Total:")[1].split()[0])
                        scan_info["total_markets"] = n
                        scan_info["last_scan"] = ts
                    except Exception:
                        pass
                elif "✅ Opportunity:" in line:
                    try:
                        rest = line.split("✅ Opportunity:")[1].strip()
                        # format: YES Paris Forecast 28.5°C Edge 15% | question
                        parts = rest.split("|")[0].strip()
                        question = rest.split("|")[1].strip() if "|" in rest else ""
                        direction = parts.split()[0]
                        city = parts.split()[1]
                        edge_str = ""
                        if "Edge" in parts:
                            edge_str = parts.split("Edge")[1].strip().split()[0]
                        forecast = ""
                        if "Forecast" in parts:
                            forecast = parts.split("Forecast")[1].split("Edge")[0].strip()
                        opportunities.append({
                            "ts": ts, "direction": direction, "city": city,
                            "forecast": forecast, "edge": edge_str,
                            "question": question[:80],
                        })
                        if len(opportunities) >= 20:
                            break
                    except Exception:
                        pass
    except Exception as e:
        scan_info["error"] = str(e)

    return _cors(jsonify({
        "config": config,
        "scan": scan_info,
        "opportunities": opportunities,
    }))


@app.route("/api/decisions")
def api_decisions():
    n = min(int(request.args.get("n", 100)), 500)
    state = load_json(STATE_FILE) or {}
    decisions = state.get("recent_decisions", [])
    return _cors(jsonify({"count": len(decisions), "decisions": decisions[-n:]}))


@app.route("/api/killswitch")
def api_killswitch():
    ks_file = BASE_DIR / "data" / "kill_switch_state.json"
    state = {}
    try:
        if ks_file.exists():
            state = json.loads(ks_file.read_text(encoding="utf-8"))
        else:
            state = {
                "active": False, "triggered_at": None, "triggered_by": None,
                "reason": None, "auto_reset_at": None, "history": [],
            }
    except Exception as e:
        return _cors(jsonify({"error": str(e)})), 500

    # Restzeit berechnen
    if state.get("active") and state.get("auto_reset_at"):
        try:
            from datetime import datetime
            reset_dt = datetime.fromisoformat(state["auto_reset_at"])
            remaining_s = (reset_dt - datetime.utcnow()).total_seconds()
            state["auto_reset_in_hours"] = round(max(0, remaining_s) / 3600, 1)
        except Exception:
            state["auto_reset_in_hours"] = None

    return _cors(jsonify(state))


@app.route("/api/errors")
def api_errors():
    severity_filter = request.args.get("severity", "").upper()
    context_filter  = request.args.get("context", "").lower()
    limit = min(int(request.args.get("n", 50)), 500)

    error_log = BASE_DIR / "data" / "error_log.jsonl"
    entries = []
    try:
        if error_log.exists():
            lines = error_log.read_text(encoding="utf-8").splitlines()
            for line in reversed(lines):
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    if severity_filter and entry.get("severity") != severity_filter:
                        continue
                    if context_filter and context_filter not in entry.get("context", "").lower():
                        continue
                    entry_clean = {k: v for k, v in entry.items() if k != "stack_trace"}
                    entries.append(entry_clean)
                    if len(entries) >= limit:
                        break
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        return _cors(jsonify({"error": str(e)})), 500

    stats_file = BASE_DIR / "data" / "error_stats.json"
    stats = {}
    try:
        if stats_file.exists():
            stats = json.loads(stats_file.read_text(encoding="utf-8"))
    except Exception:
        pass

    return _cors(jsonify({"count": len(entries), "errors": entries, "stats": stats}))


@app.route("/api/slippage")
def api_slippage():
    """
    GET /api/slippage
    Query params:
      view=daily|weekly|wallet|category|signal   (default: daily)
      date=YYYY-MM-DD                            (only for view=daily)
      n=50                                       (recent raw entries, view=raw)
    """
    view = request.args.get("view", "daily")
    try:
        sys.path.insert(0, str(BASE_DIR))
        from utils.slippage_analyzer import (
            compute_daily_stats, compute_weekly_stats,
            compute_by_wallet, compute_by_market_category,
            compute_by_signal_type, get_today_alert_status,
        )
        from utils.slippage_tracker import load_entries, ALERT_THRESHOLD_CENTS

        if view == "daily":
            date_filter = request.args.get("date")
            data = compute_daily_stats(date_filter)
            return _cors(jsonify({"view": "daily", "data": data, "threshold": ALERT_THRESHOLD_CENTS}))
        elif view == "weekly":
            data = compute_weekly_stats()
            return _cors(jsonify({"view": "weekly", "data": data, "threshold": ALERT_THRESHOLD_CENTS}))
        elif view == "wallet":
            data = compute_by_wallet()
            return _cors(jsonify({"view": "wallet", "data": data}))
        elif view == "category":
            data = compute_by_market_category()
            return _cors(jsonify({"view": "category", "data": data}))
        elif view == "signal":
            data = compute_by_signal_type()
            return _cors(jsonify({"view": "signal", "data": data}))
        elif view == "raw":
            n = min(int(request.args.get("n", 50)), 500)
            date_filter = request.args.get("date")
            entries = load_entries(date_filter)
            return _cors(jsonify({"view": "raw", "count": len(entries), "entries": entries[-n:]}))
        elif view == "alert":
            return _cors(jsonify(get_today_alert_status()))
        else:
            return _cors(jsonify({"error": f"Unbekannte view: {view}"})), 400
    except ImportError as e:
        return _cors(jsonify({"error": f"slippage_analyzer nicht verfügbar: {e}"})), 500
    except Exception as e:
        return _cors(jsonify({"error": str(e)})), 500


@app.route("/api/wallet_performance")
def api_wallet_performance():
    """
    GET /api/wallet_performance
    Query params:
      wallet=0x...          (single wallet; omit for all wallets)
      view=stats|category|timeframe|all   (default: stats)
      since=30              (days lookback, default 30)
    """
    since = int(request.args.get("since", 30))
    wallet = request.args.get("wallet", "").strip()
    view   = request.args.get("view", "stats")
    try:
        sys.path.insert(0, str(BASE_DIR))
        from utils.wallet_performance import (
            compute_wallet_stats, compute_by_category,
            compute_by_timeframe, compute_all_wallets,
        )

        if not wallet:
            data = compute_all_wallets(since_days=since)
            return _cors(jsonify({"view": "all_wallets", "since_days": since, "wallets": data}))

        if view == "stats":
            return _cors(jsonify({"view": "stats", "since_days": since, "data": compute_wallet_stats(wallet, since)}))
        elif view == "category":
            return _cors(jsonify({"view": "category", "since_days": since, "data": compute_by_category(wallet, since)}))
        elif view == "timeframe":
            return _cors(jsonify({"view": "timeframe", "since_days": since, "data": compute_by_timeframe(wallet, since)}))
        elif view == "all":
            return _cors(jsonify({
                "view":      "all",
                "since_days": since,
                "stats":     compute_wallet_stats(wallet, since),
                "category":  compute_by_category(wallet, since),
                "timeframe": compute_by_timeframe(wallet, since),
            }))
        else:
            return _cors(jsonify({"error": f"Unbekannte view: {view}"})), 400
    except ImportError as e:
        return _cors(jsonify({"error": f"wallet_performance nicht verfügbar: {e}"})), 500
    except Exception as e:
        return _cors(jsonify({"error": str(e)})), 500


# ── Wallet Performance (T-017) ────────────────────────────────────────────────

@app.route("/api/wallets")
def api_wallets():
    """Per-Wallet Performance: log-basierte Signale + Archiv-Statistiken."""
    import re as _re
    from datetime import date as _date
    from collections import defaultdict
    today_str = _date.today().isoformat()

    # 1. TARGET_WALLETS + WALLET_WEIGHTS aus .env
    target_wallets: list[str] = []
    weights_raw: dict = {}
    try:
        env_text = ENV_FILE.read_text()
        for line in env_text.splitlines():
            line = line.strip()
            if line.startswith("TARGET_WALLETS="):
                raw = line.split("=", 1)[1].strip().strip('"').strip("'")
                target_wallets = [w.strip() for w in raw.split(",") if w.strip()]
            if line.startswith("WALLET_WEIGHTS="):
                try:
                    weights_raw = json.loads(line.split("=", 1)[1].strip())
                except Exception:
                    pass
    except Exception:
        pass

    # Multiplier per Adresse auflösen (prefix-match wie copy_trading.py)
    def _mult(addr: str) -> float:
        for prefix, w in weights_raw.items():
            if prefix != "default" and addr.lower().startswith(prefix.lower()):
                return float(w)
        return float(weights_raw.get("default", 0.05))

    # 2. WALLET_NAMES aus copy_trading
    wallet_names: dict[str, str] = {}
    try:
        sys.path.insert(0, str(BASE_DIR))
        from strategies.copy_trading import WALLET_NAMES as _WN
        wallet_names = {k.lower(): v for k, v in _WN.items()}
    except Exception:
        pass

    # 3. Log-basierte Signale (heute): nur Signal-relevante Zeilen
    SIGNAL_KEYWORDS = ("NEUER TRADE", "FRÜH-SIGNAL", "CopyOrder", "BUY", "SKIP",
                       "blockiert", "geskipped", "Risk", "Signal")
    log_file = LOG_DIR / "bot.log"
    # per wallet: {addr_lower: {"signals": int, "copied": int, "blocked": int, "last_log": str}}
    log_stats: dict = defaultdict(lambda: {"signals": 0, "copied": 0, "blocked": 0, "last_log": None})
    try:
        for line in log_file.read_text(errors="replace").splitlines():
            if not line.startswith(today_str):
                continue
            if not any(k in line for k in SIGNAL_KEYWORDS):
                continue
            line_low = line.lower()
            for addr in target_wallets:
                if addr.lower()[:16] in line_low:
                    log_stats[addr.lower()]["signals"] += 1
                    log_stats[addr.lower()]["last_log"] = line[11:19]
                    if "SKIP" in line or "blockiert" in line or "geskipped" in line:
                        log_stats[addr.lower()]["blocked"] += 1
                    elif "CopyOrder" in line or "BUY" in line:
                        log_stats[addr.lower()]["copied"] += 1
    except Exception:
        pass

    # 4a. Archiv: historische Win-Rate + PnL (aus trades_archive.json falls vorhanden)
    archive = load_json(ARCHIVE_FILE) or []
    wallet_trades: dict = defaultdict(list)
    wallet_trades_today: dict = defaultdict(list)
    for t in archive:
        sw = (t.get("source_wallet") or "").lower()
        if not sw or sw.startswith("["):
            continue
        wallet_trades[sw].append(t)
        if t.get("datum") == today_str:
            wallet_trades_today[sw].append(t)

    # 4b. all_signals.jsonl: Signal-Totals + copied/skipped per Wallet
    sig_totals: dict = defaultdict(lambda: {"total": 0, "copied": 0, "skipped": 0})
    try:
        sig_file = BASE_DIR / "data" / "all_signals.jsonl"
        if sig_file.exists():
            for line in sig_file.read_text(errors="replace").splitlines():
                try:
                    s = json.loads(line)
                    w = (s.get("wallet") or "").lower()
                    if not w:
                        continue
                    sig_totals[w]["total"] += 1
                    dec = s.get("decision", "")
                    if "COPY" in dec:
                        sig_totals[w]["copied"] += 1
                    elif "SKIP" in dec or "REJECT" in dec:
                        sig_totals[w]["skipped"] += 1
                except Exception:
                    pass
    except Exception:
        pass

    # 4c. wallet_decisions.jsonl: Win-Rate aus predicts.guru
    wd_stats: dict = {}
    try:
        wd_file = BASE_DIR / "data" / "wallet_decisions.jsonl"
        if wd_file.exists():
            for line in wd_file.read_text(errors="replace").splitlines():
                try:
                    wd = json.loads(line)
                    w = (wd.get("wallet") or "").lower()
                    if w:
                        wd_stats[w] = {
                            "win_rate_pct": wd.get("win_rate_pct"),
                            "trades_copied": wd.get("trades_copied", 0),
                            "decision":      wd.get("decision", ""),
                        }
                except Exception:
                    pass
    except Exception:
        pass

    # 5. Zusammenbauen
    result = []
    for addr in target_wallets:
        addr_low  = addr.lower()
        alias     = wallet_names.get(addr_low, addr[:8] + "...")
        mult      = _mult(addr)
        ls        = log_stats[addr_low]
        trades_all   = wallet_trades[addr_low]

        # Zuletzt aktiv: Log-Zeit bevorzugen, sonst Archiv
        last_active = ls["last_log"]
        if not last_active and trades_all:
            last_t = max(trades_all, key=lambda t: f"{t.get('datum','')}{t.get('uhrzeit','')}")
            d = last_t.get("datum", ""); u = last_t.get("uhrzeit", "")
            last_active = f"{d[5:]} {u}".strip() if d else None

        resolved  = [t for t in trades_all if t.get("aufgeloest")]
        wins      = [t for t in resolved if t.get("ergebnis") == "GEWINN"]
        # P&L from archive first; fallback to predicts.guru win rate from wallet_decisions
        wd        = wd_stats.get(addr_low, {})
        win_rate_archive = round(len(wins) / len(resolved) * 100, 1) if resolved else None
        win_rate  = win_rate_archive or wd.get("win_rate_pct")
        total_pnl = round(sum(float(t.get("gewinn_verlust_usdc") or 0) for t in resolved), 2)

        # signals_total: archive OR all_signals.jsonl (whichever is larger)
        st_sig    = sig_totals.get(addr_low, {})
        sig_total_signals = st_sig.get("total", 0)
        sig_total_copied  = st_sig.get("copied", 0)
        signals_total = max(len(trades_all), sig_total_signals)
        # copies_total: archive trades OR all_signals copied count OR wallet_decisions
        copies_total = max(
            len(trades_all),
            sig_total_copied,
            wd.get("trades_copied", 0)
        )

        # signals_today: log-basiert ODER Archiv-Fallback
        signals_today = ls["signals"] or len(wallet_trades_today[addr_low])

        result.append({
            "address":       addr,
            "alias":         alias,
            "multiplier":    mult,
            "signals_today": signals_today,
            "copied_today":  ls["copied"],
            "blocked_today": ls["blocked"],
            "signals_total": signals_total,
            "copies_total":  copies_total,
            "last_active":   last_active,
            "win_rate":      win_rate,
            "total_pnl":     total_pnl,
            "wins":          len(wins),
            "losses":        len(resolved) - len(wins),
            "wd_decision":   wd.get("decision", ""),
        })

    result.sort(key=lambda w: (-w["signals_today"], -w["signals_total"]))
    active_today = sum(1 for w in result if w["signals_today"] > 0)

    return _cors(jsonify({
        "wallets":      result,
        "total":        len(result),
        "active_today": active_today,
        "top_wallet":   result[0]["alias"] if result else None,
    }))


# ── Mutable Endpoints ─────────────────────────────────────────────────────────

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

    if action == "stop":
        pid_file = BASE_DIR / "bot.pid"
        try:
            if pid_file.exists():
                pid = int(pid_file.read_text().strip())
                os.kill(pid, 15)
                return jsonify({"ok": True, "message": f"Bot gestoppt (PID {pid})"})
            if os.name == "nt":
                subprocess.run("taskkill /F /IM python.exe", shell=True, capture_output=True)
            else:
                subprocess.run(["pkill", "-f", "main.py"], capture_output=True)
            return jsonify({"ok": True, "message": "Bot gestoppt"})
        except Exception as e:
            return jsonify({"ok": False, "message": str(e)})

    elif action == "restart":
        try:
            if os.name == "nt":
                subprocess.run("taskkill /F /IM python.exe", shell=True, capture_output=True)
            else:
                subprocess.run(["pkill", "-f", "main.py"], capture_output=True)
            time.sleep(2)
            flags = subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0
            subprocess.Popen([python, "main.py"], cwd=bot_dir, creationflags=flags)
            return jsonify({"ok": True, "message": "Bot neu gestartet"})
        except Exception as e:
            return jsonify({"ok": False, "message": str(e)})

    elif action == "auswertung":
        try:
            result = subprocess.run(
                [python, "auswertung.py"], cwd=bot_dir,
                capture_output=True, text=True, timeout=60
            )
            output = (result.stdout or "") + (result.stderr or "")
            return jsonify({"ok": True, "output": output[-4000:], "message": "Auswertung abgeschlossen"})
        except subprocess.TimeoutExpired:
            return jsonify({"ok": False, "output": "", "message": "Timeout (60s)"})
        except Exception as e:
            return jsonify({"ok": False, "output": "", "message": str(e)})

    elif action == "resolver":
        try:
            result = subprocess.run(
                [python, "resolver.py"], cwd=bot_dir,
                capture_output=True, text=True, timeout=120
            )
            output = (result.stdout or "") + (result.stderr or "")
            return jsonify({"ok": True, "output": output[-4000:], "message": "Resolver abgeschlossen"})
        except subprocess.TimeoutExpired:
            return jsonify({"ok": False, "output": "", "message": "Timeout (120s)"})
        except Exception as e:
            return jsonify({"ok": False, "output": "", "message": str(e)})

    return jsonify({"ok": False, "message": "Unbekannte Aktion"})


@app.route("/api/manual_exit", methods=["POST"])
def api_manual_exit():
    """
    Manueller Exit für eine Position.
    Schreibt Exit-Request in manual_exit_queue.json — der Bot verarbeitet ihn im exit_loop.
    Body: { "condition_id": "0x...", "reason": "profit_taking" }
    """
    data         = request.json or {}
    condition_id = (data.get("condition_id") or "").strip()
    reason       = (data.get("reason") or "manual").strip()[:50]

    if not condition_id:
        return jsonify({"ok": False, "error": "condition_id fehlt"}), 400

    queue_path = BASE_DIR / "manual_exit_queue.json"
    try:
        queue = []
        if queue_path.exists():
            try:
                queue = json.loads(queue_path.read_text())
            except Exception:
                queue = []
        # Duplikat-Check
        if any(e.get("condition_id") == condition_id for e in queue):
            return jsonify({"ok": True, "queued": False, "message": "Bereits in Queue"})
        queue.append({
            "condition_id": condition_id,
            "reason":       reason,
            "requested_at": datetime.now(timezone.utc).isoformat(),
        })
        queue_path.write_text(json.dumps(queue, indent=2))
        return jsonify({
            "ok":      True,
            "queued":  True,
            "message": f"Exit-Request eingereiht: {condition_id[:20]}… ({reason})",
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/wallet_trends")
def api_wallet_trends():
    """
    Gibt Wallet-Scout-Zeitreihe zurück.
    ?wallet=0x...  → Trend-History für eine Wallet
    ?report=1      → Weekly-Summary (new, decay, stars, stable)
    """
    try:
        from utils.wallet_trends import (
            get_wallet_trend, get_new_entries,
            get_decay_candidates, get_rising_stars, get_top_stable
        )
    except Exception as e:
        return _cors(jsonify({"error": f"wallet_trends nicht verfügbar: {e}"}))

    source = request.args.get("source", "polymonit")
    days   = int(request.args.get("days", "14"))
    wallet = request.args.get("wallet", "")

    if wallet:
        trend = get_wallet_trend(wallet, days=days)
        return _cors(jsonify({"wallet": wallet, "days": days, "trend": trend}))

    # Summary-Report
    return _cors(jsonify({
        "source":     source,
        "days":       days,
        "new":        get_new_entries(source, days=days),
        "decay":      get_decay_candidates(source, days=days),
        "rising":     get_rising_stars(source, days=days),
        "stable_top5": get_top_stable(source, days=days),
    }))


@app.route("/api/skipped_signals")
def api_skipped_signals():
    """
    Shadow-Tracking: SKIPPED-Signal-Performance.
    ?view=summary          → Gesamtstatistik (default)
    ?view=by_reason        → Aufschlüsselung nach Skip-Grund
    ?view=missed_profits   → Theoretische Gewinne/Verluste evaluierter Signale
    ?days=7                → Zeitfenster (default 7)
    """
    try:
        from utils.signal_tracker import get_summary_stats, _read_signals, _read_outcomes
    except Exception as e:
        return _cors(jsonify({"error": f"signal_tracker nicht verfügbar: {e}"}))

    view = request.args.get("view", "summary")
    days = int(request.args.get("days", "7"))
    stats = get_summary_stats(days=days)

    if view == "by_reason":
        return _cors(jsonify({
            "days": days,
            "by_reason": stats["by_reason"],
            "worst_filter": stats["worst_filter"],
        }))

    if view == "missed_profits":
        from datetime import datetime, timezone, timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        outcomes = _read_outcomes()
        week = [o for o in outcomes if o.get("ts_evaluated", "") >= cutoff]
        winners = [o for o in week if o.get("signal_correct")]
        losers = [o for o in week if not o.get("signal_correct")]
        return _cors(jsonify({
            "days": days,
            "evaluated": len(week),
            "winners": len(winners),
            "losers": len(losers),
            "missed_profit_usd": round(sum(o.get("theoretical_profit_usdc", 0) for o in winners), 2),
            "avoided_loss_usd": round(sum(abs(o.get("theoretical_profit_usdc", 0)) for o in losers), 2),
            "net_missed_usd": stats["net_missed_usd"],
            "details": week[-50:],
        }))

    return _cors(jsonify(stats))


# ── WebSocket Push ─────────────────────────────────────────────────────────────

_last_log_count = 0


def background_push():
    global _last_log_count
    while True:
        try:
            with app.app_context():
                stats = get_stats()
                running, pid = is_bot_running()
                env = load_env()
                stats["bot_running"] = running
                stats["bot_pid"]     = pid
                stats["dry_run"]     = env.get("DRY_RUN", "true").lower() == "true"
                socketio.emit("stats", stats)

                state = load_json(STATE_FILE) or {}
                open_count   = len(state.get("open_positions", []))
                pending_count = len(state.get("pending_data") or {})
                socketio.emit("position_counts", {"open": open_count, "pending": pending_count})

                lines = get_log_lines(100)
                if len(lines) != _last_log_count:
                    _last_log_count = len(lines)
                    socketio.emit("log", lines[-60:])
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
    emit("log", get_log_lines(60))
    mults, default = load_wallet_multipliers()
    emit("multipliers", {"wallets": mults, "default": default})
    emit("env", load_env())
    if _current_balance.get("value") is not None:
        emit("balance_update", {"balance": _current_balance["value"], "ts": _current_balance["ts"]})


# ── Background watchdog ───────────────────────────────────────────────────────

_push_thread: threading.Thread | None = None


def _ensure_push_thread_running():
    global _push_thread
    if _push_thread is None or not _push_thread.is_alive():
        _push_thread = threading.Thread(target=background_push, daemon=True)
        _push_thread.start()


def _watchdog():
    while True:
        try:
            time.sleep(10)
            _ensure_push_thread_running()
        except Exception:
            pass


# ── Start ─────────────────────────────────────────────────────────────────────

_BANNER = """\
=======================================================
  KongTrade Bot Dashboard v2.0 — ULTIMATE
  http://localhost:5000
  Stoppen: Ctrl+C
======================================================="""

MAX_RESTARTS = 20


@app.route("/api/report")
def api_report():
    """Report Tab — Tagesstatistik: Trades, Features, Fehler."""
    import re as _re
    from datetime import datetime as _dt
    today = _dt.now().strftime("%Y-%m-%d")
    # Prefer today's dated log; fall back to bot.log (rolling log)
    log_file = os.path.join(BASE_DIR, "logs", f"bot_{today}.log")
    if not os.path.exists(log_file):
        fallback = os.path.join(BASE_DIR, "logs", "bot.log")
        if os.path.exists(fallback):
            log_file = fallback
        else:
            log_file = None

    data = {
        "trades_today": 0, "buys_today": 0, "sells_today": 0,
        "errors_today": 0, "ws_status": "unknown",
        "rss_signals_today": 0, "weather_opportunities": 0,
        "stop_loss_triggered": 0, "whale_exit_triggered": 0,
        "blacklist_blocked": 0, "anomaly_active": False,
        "recent_errors": [], "last_trade_time": None,
    }
    if log_file and os.path.exists(log_file):
        with open(log_file, errors="replace") as f:
            for line in f:
                if "CopyOrder[LIVE]" in line or "Order erstellt" in line:
                    data["trades_today"] += 1
                    if "BUY" in line: data["buys_today"] += 1
                    if "SELL" in line: data["sells_today"] += 1
                    data["last_trade_time"] = line[:19]
                if " ERROR " in line:
                    data["errors_today"] += 1
                    ts = line[:8].strip() if len(line) >= 8 else ""
                    msg = line[20:120].strip()
                    data["recent_errors"].append(f"{ts} | {msg}" if ts else msg)
                if "[WS] Subscribed" in line:
                    data["ws_status"] = "connected"
                if "[WS] Disconnect" in line or "[WS] Verbindungs" in line:
                    data["ws_status"] = "disconnected"
                if "[RSS]" in line and "Signal" in line:
                    data["rss_signals_today"] += 1
                if "[WeatherScout]" in line and "Opportunit" in line:
                    data["weather_opportunities"] += 1
                if "EXIT_SL" in line or "stop_loss" in line.lower():
                    data["stop_loss_triggered"] += 1
                if "WHALE EXIT" in line or "whale_exit_copy" in line.lower():
                    data["whale_exit_triggered"] += 1
                if "BLACKLIST" in line or "blockiert" in line:
                    data["blacklist_blocked"] += 1
                if "[ANOMALY] Detektor gestartet" in line:
                    data["anomaly_active"] = True
    data["recent_errors"] = data["recent_errors"][-5:]
    return _cors(jsonify(data))


@app.route("/api/weather_paper_trades")
@login_required
def api_weather_paper_trades():
    pt_file = BASE_DIR / "data" / "weather_paper_trades.json"
    try:
        trades = json.loads(pt_file.read_text())
    except Exception:
        trades = []

    # Fetch end dates for all condition_ids (batched, cached 1h)
    cids = list({t.get("condition_id", "") for t in trades if t.get("condition_id")})
    enddate_map = _batch_fetch_gamma_enddates(cids) if cids else {}

    def _closes_label(cid):
        end_str = enddate_map.get(cid)
        if not end_str:
            return None, "—"
        s, _ = _parse_closes_in(end_str)
        if s is None:
            return None, "—"
        if s <= 0:
            # CLOB end_date_iso is midnight UTC of resolution day.
            # Show "TODAY" if the date is today (market may still be open).
            try:
                end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                today = datetime.now(timezone.utc).date()
                if end_dt.date() == today:
                    return 0, "TODAY"
            except Exception:
                pass
            return 0, "ENDED"
        h = int(s) // 3600
        d = h // 24
        rh = h % 24
        if d >= 1:
            return s, f"in {d}d {rh}h" if rh else f"in {d}d"
        return s, f"in {h}h"

    enriched = []
    for t in trades:
        s, label = _closes_label(t.get("condition_id", ""))
        enriched.append({**t, "closes_in_s": s, "closes_in_label": label})

    # Sort: OPEN soonest-first, then non-OPEN at the end
    def _sort_key(t):
        if t.get("status") != "OPEN":
            return (1, 0)
        s = t.get("closes_in_s")
        return (0, s if s is not None else float("inf"))

    enriched.sort(key=_sort_key)

    total_invested = sum(t.get("simulated_buy_usd", 0) for t in trades)
    total_won = sum(
        t.get("potential_win_usd", 0) for t in trades if t.get("status") == "WON"
    )
    won  = len([t for t in trades if t.get("status") == "WON"])
    lost = len([t for t in trades if t.get("status") == "LOST"])
    open_trades = len([t for t in trades if t.get("status") == "OPEN"])
    return _cors(jsonify({
        "trades": enriched[:30],
        "stats": {
            "total_trades":       len(trades),
            "won":                won,
            "lost":               lost,
            "open":               open_trades,
            "total_invested_usd": round(total_invested, 2),
            "total_won_usd":      round(total_won, 2),
            "win_rate":           round(won / max(won + lost, 1) * 100, 1),
        },
    }))


def _run_server():
    socketio.run(app, host="127.0.0.1", port=5000, debug=False, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    init_db()
    _ensure_push_thread_running()
    threading.Thread(target=_watchdog, daemon=True).start()
    threading.Thread(target=_balance_updater_thread, daemon=True).start()
    threading.Thread(target=_positions_updater_thread, daemon=True).start()

    print(_BANNER)

    restarts = 0
    while restarts < MAX_RESTARTS:
        try:
            _run_server()
            break
        except KeyboardInterrupt:
            print("\n[Dashboard] Gestoppt.")
            break
        except OSError as e:
            if "Address already in use" in str(e) or "10048" in str(e):
                print(f"[Dashboard] Port 5000 belegt — warte 10s...")
                time.sleep(10)
            else:
                restarts += 1
                print(f"[Dashboard] Fehler: {e} — Neustart {restarts}/{MAX_RESTARTS}")
                time.sleep(3)
        except Exception as e:
            restarts += 1
            print(f"[Dashboard] Unerwarteter Fehler: {e} — Neustart {restarts}/{MAX_RESTARTS}")
            time.sleep(3)
