# Deploy Report Tab + Public Status
_Erstellt: 2026-04-20 | Für: Server-CC Deploy_

## Was du tun musst (Server-CC)

---

### Schritt 1: push_status.py deployen

```bash
cp /root/KongTradeBot-docs/scripts/push_status.py \
   /root/KongTradeBot/scripts/push_status.py
```

Cron-Job (stündlich):
```bash
(crontab -l; echo "0 * * * * python3 \
  /root/KongTradeBot/scripts/push_status.py \
  >> /var/log/status_push.log 2>&1") | crontab -
```

Manuell testen:
```bash
python3 /root/KongTradeBot/scripts/push_status.py
```

---

### Schritt 2: Öffentliches Repo klonen

**Onur muss zuerst:** github.com/new → Name: `kongtrade-status` → **PUBLIC** → Create

Dann auf Server:
```bash
cd /root
git clone https://github.com/onur-tech/kongtrade-status.git
echo '{}' > kongtrade-status/status.json
cd kongtrade-status
git add .
git commit -m "init: public status repo"
git push
```

Nach erfolgreichem Push ist erreichbar:
```
https://raw.githubusercontent.com/onur-tech/kongtrade-status/main/status.json
```

---

### Schritt 3: /api/report Endpoint in dashboard.py

Füge diesen Endpoint in `dashboard.py` ein (nach dem letzten `@app.route`):

```python
@app.route('/api/report')
def api_report():
    """Report Tab Daten — Tab 4."""
    import re
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = f"/root/KongTradeBot/logs/bot_{today}.log"

    data = {
        "trades_today": 0,
        "buys_today": 0,
        "sells_today": 0,
        "errors_today": 0,
        "ws_status": "unknown",
        "rss_signals_today": 0,
        "weather_opportunities": 0,
        "stop_loss_triggered": 0,
        "whale_exit_triggered": 0,
        "blacklist_blocked": 0,
        "restarts_today": 0,
        "anomaly_active": False,
        "recent_errors": [],
        "wallet_activity": [],
        "last_trade_time": None,
        "pnl_today": None,
        "uptime": None
    }

    if os.path.exists(log_file):
        with open(log_file) as f:
            lines = f.readlines()
        for line in lines:
            if "CopyOrder[LIVE]" in line:
                data["trades_today"] += 1
                if "BUY" in line: data["buys_today"] += 1
                if "SELL" in line: data["sells_today"] += 1
                data["last_trade_time"] = line[:19]
            if "ERROR" in line:
                data["errors_today"] += 1
                data["recent_errors"].append(line[20:100].strip())
            if "[WS] Subscribed" in line:
                data["ws_status"] = "connected"
            if "[WS] Disconnect" in line:
                data["ws_status"] = "disconnected"
            if "[RSS]" in line and "Signal" in line:
                data["rss_signals_today"] += 1
            if "[WeatherScout]" in line and "Opportunit" in line:
                data["weather_opportunities"] += 1
            if "stop_loss" in line.lower() or "EXIT_SL" in line:
                data["stop_loss_triggered"] += 1
            if "whale_exit_copy" in line.lower() or "WHALE EXIT" in line:
                data["whale_exit_triggered"] += 1
            if "BLACKLIST" in line or "blockiert" in line:
                data["blacklist_blocked"] += 1
            if "ANOMALY" in line and "gestartet" in line:
                data["anomaly_active"] = True

    data["recent_errors"] = data["recent_errors"][-5:]
    return jsonify(data)
```

---

### Schritt 4: Tab 4 in dashboard.py HTML-Block hinzufügen

1. In `dashboard.py` die Tab-Navigation finden (wo Tab 1/2/3 Buttons sind)
2. Neuen Tab-Button hinzufügen:
   ```html
   <button onclick="showTab('report-tab')" class="tab-btn">REPORT</button>
   ```
3. Den kompletten HTML/JS Block aus
   `/root/KongTradeBot-docs/scripts/dashboard_report_tab.html`
   in den HTML-String in `dashboard.py` einfügen — **nach dem RESOLVED Tab**.

---

### Schritt 5: CSS für Report Tab (in bestehendes `<style>` einfügen)

```css
.report-section { margin-bottom: 24px; }
.section-title { color: #00ff88; font-size: 13px; margin-bottom: 10px; }
.report-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 10px;
}
.stat-box {
  background: #1a1a2e;
  border: 1px solid #333;
  border-radius: 6px;
  padding: 12px;
  display: flex;
  flex-direction: column;
}
.stat-label { font-size: 11px; color: #888; margin-bottom: 4px; }
.stat-value { font-size: 20px; font-weight: bold; color: #fff; }
.feature-table, .wallet-activity-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.feature-table th, .wallet-activity-table th {
  text-align: left;
  color: #888;
  padding: 6px 10px;
  border-bottom: 1px solid #333;
}
.feature-table td, .wallet-activity-table td {
  padding: 8px 10px;
  border-bottom: 1px solid #1a1a2e;
}
.status-dot { font-size: 16px; }
.error-line {
  background: #1a0a0a;
  border-left: 3px solid #ff4444;
  padding: 6px 10px;
  margin-bottom: 4px;
  font-size: 12px;
  font-family: monospace;
  color: #ff8888;
}
.no-errors { color: #00ff88; padding: 10px; }
```

---

### Schritt 6: Syntax-Check + Restart + Commit

```bash
# Syntax prüfen
python3 -c "import py_compile; py_compile.compile('dashboard.py')"

# Service neustarten
systemctl restart kongtrade-dashboard

# Endpoint testen
curl http://localhost:5000/api/report | python3 -m json.tool

# Status-Push testen
python3 /root/KongTradeBot/scripts/push_status.py

# Commit
cd /root/KongTradeBot
git add dashboard.py scripts/push_status.py
git commit -m "feat: Report Tab + Public Status Push"
git push
```

---

## Ergebnis nach Deploy

- **Dashboard Tab 4** zeigt: Nacht-Zusammenfassung, Feature-Ampeln, Wallet-Aktivität, Fehler
- **Public URL:** `https://raw.githubusercontent.com/onur-tech/kongtrade-status/main/status.json`
- **Refresh:** Automatisch alle 30s (Tab) + stündlich (GitHub Push via Cron)
- **Claude.ai kann lesen:** status.json direkt fetchen für Session-Briefing

---

## Checklist

- [ ] Onur hat `kongtrade-status` Repo als PUBLIC erstellt
- [ ] `push_status.py` auf Server deployed
- [ ] Cron-Job eingerichtet (`crontab -l` zur Verifikation)
- [ ] Repo geklont + init-Commit gepusht
- [ ] `/api/report` Endpoint in dashboard.py eingebaut
- [ ] Tab 4 HTML/JS in dashboard.py eingefügt
- [ ] CSS hinzugefügt
- [ ] `systemctl restart kongtrade-dashboard`
- [ ] `curl /api/report` → JSON ohne Fehler
- [ ] Tab 4 im Browser öffnen → Daten erscheinen

---

_Quell-Dateien: scripts/push_status.py + scripts/dashboard_report_tab.html_
_Erstellt von: Windows-CC 2026-04-20_
