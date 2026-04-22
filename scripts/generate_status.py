#!/usr/bin/env python3
import subprocess, re, os, json, urllib.request
from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def get_service_status():
    try:
        r = subprocess.run(["systemctl","show","kongtrade-bot","--property=ActiveState,SubState,ExecMainStartTimestamp"], capture_output=True, text=True)
        props = dict(l.split("=",1) for l in r.stdout.strip().splitlines() if "=" in l)
        state, sub = props.get("ActiveState","?"), props.get("SubState","?")
        started = props.get("ExecMainStartTimestamp","?")
        if state == "active" and sub == "running":
            return f"RUNNING (seit {started})"
        return f"DOWN {state}/{sub}"
    except Exception as e:
        return f"Fehler: {e}"

def get_dashboard_url():
    try:
        with open("/home/claudeuser/KongTradeBot/.current_tunnel_url") as f:
            return f.read().strip()
    except Exception:
        return "nicht verfuegbar"


def get_watchdog_timer_info():
    """Liest letzten Watchdog-Timer-Lauf aus systemctl (immer aktuell)."""
    try:
        r = subprocess.run(
            ["systemctl", "show", "kongtrade-watchdog.timer",
             "--property=LastTriggerUSec"],
            capture_output=True, text=True
        )
        props = dict(l.split("=", 1) for l in r.stdout.strip().splitlines() if "=" in l)
        val = props.get("LastTriggerUSec", "").strip()
        if not val or val == "0":
            return "Watchdog-Timer: noch kein Lauf"
        # systemd liefert lesbares Datum: "Sat 2026-04-18 08:35:27 UTC"
        from datetime import datetime as _dt
        import re as _re
        m = _re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", val)
        if m:
            last = _dt.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            age_s = int((datetime.now(timezone.utc) - last).total_seconds())
            if age_s < 90:
                return f"OK — lief vor {age_s}s"
            elif age_s < 300:
                return f"WARNUNG — lief vor {age_s}s"
            else:
                return f"STALE — lief vor {age_s}s"
        return f"Watchdog-Timer: {val}"
    except Exception as e:
        return f"Watchdog-Timer Fehler: {e}"


def get_watchdog_heartbeat():
    hb = "/home/claudeuser/KongTradeBot/heartbeat.txt"
    if not os.path.exists(hb):
        return "Kein Heartbeat-File"
    age = int(datetime.now().timestamp() - os.path.getmtime(hb))
    # heartbeat_loop schreibt alle 300s; Puffer 60s -> OK bis 360s
    if age < 360:  return f"OK ({age}s alt)"
    if age < 700:  return f"WARNUNG {age}s alt"
    return f"STALE {age}s alt (Bot moeglicherweise haengend)"

def sanitize(line):
    line = re.sub(r"0x[a-fA-F0-9]{10,}", "[WALLET]", line)
    line = re.sub(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", "[IP]", line)
    line = re.sub(r"apiKey=[A-Za-z0-9]+", "apiKey=[REDACTED]", line)
    return line

def grep_log(pattern, log, flags="-E"):
    try:
        r = subprocess.run(["grep", flags, pattern, log], capture_output=True, text=True)
        return [sanitize(l.strip()) for l in r.stdout.splitlines() if l.strip()]
    except Exception as e:
        return [f"Log nicht lesbar: {e}"]

def get_portfolio():
    try:
        req = urllib.request.Request("http://localhost:5000/api/portfolio", headers={"User-Agent":"StatusBot/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

def get_cash_balance():
    try:
        req = urllib.request.Request("http://localhost:5000/api/balance", headers={"User-Agent":"StatusBot/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            d = json.loads(resp.read())
            return d.get("cash", None)
    except Exception:
        return None

log = "/home/claudeuser/KongTradeBot/logs/service-bot.log"
pdata = get_portfolio()
cash_usdc = get_cash_balance()

portfolio_lines = []
if "error" in pdata:
    portfolio_lines.append("Dashboard nicht erreichbar: " + pdata.get("error", "?"))
else:
    in_pos = pdata.get("total_value", 0)
    cash_str = f"${cash_usdc:.2f} USDC" if cash_usdc is not None else "n/a"
    total = (cash_usdc or 0) + in_pos
    portfolio_lines += [
        f"Total:         ${total:.2f} USDC",
        f"Cash:          {cash_str}",
        f"In Positionen: ${in_pos:.2f} USDC",
        f"Offene Pos.:   {pdata.get('count', 0)}",
    ]

trades = grep_log("NEUER TRADE|Order erstellt|Trade abgelehnt|geclaimed", log)
errors = grep_log("error|critical|exception", log, flags="-iE")

sections = [
    "# KongTradeBot Live Status",
    "",
    f"> {utc_now()}",
    "",
    "## Bot-Status",
    "```",
    get_service_status(),
    "```",
    "",
    "## Dashboard-URL",
    "```",
    get_dashboard_url(),
    "```",
    "",
    "## Watchdog",
    "```",
    get_watchdog_timer_info() + " | HB: " + get_watchdog_heartbeat(),
    "```",
    "",
    "## Portfolio",
    "```",
] + portfolio_lines + [
    "```",
    "",
    "## Letzte Trades (5)",
    "```",
] + (trades[-5:] if trades else ["Keine"]) + [
    "```",
    "",
    "## Letzte Fehler (3)",
    "```",
] + (errors[-3:] if errors else ["Keine"]) + [
    "```",
    "",
    "---",
    "*Naechstes Update in ~5 Minuten*",
    "",
]

content = chr(10).join(sections)
with open("/root/status-repo/STATUS.md", "w") as f:
    f.write(content)
print(f"STATUS.md {len(content)} Bytes")
