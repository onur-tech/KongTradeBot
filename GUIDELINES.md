# KongTrade Bot — Guidelines für Claude Code & Chat-Claude

## LIVE-ZUGRIFF FÜR CHAT-CLAUDE (Dashboard-API)

Chat-Claude kann den Bot LIVE überwachen via Cloudflare-Tunnel-URL
(steht in STATUS.md unter "Dashboard-URL"). Verfügbare Endpoints:

### GET /api/summary
Liefert JSON mit aktuellen Kennzahlen:
- bot_pid, bot_running, heartbeat_age_s
- open (offene Positionen), closed, wins, losses
- today_pnl, total_trades, today_trades
- invested, copy_size_multiplier, max_trade_size_usd
- max_daily_loss_usd, dry_run, win_rate

→ Primäre Quelle für Status-Snapshots. Immer frischer als STATUS.md.

### GET /api/logs?n=N
Liefert letzte N Log-Zeilen (max ~500):
- Sortierung: älteste zuerst
- Format: "YYYY-MM-DD HH:MM:SS | LEVEL | module | message"
- Bei Buffer-Begrenzung fehlen eventuell die neuesten Events

→ Für Debug-Analyse, Fehler-Suche, Verifikation von CC-Deploys.

### Weitere Endpoints (wenn deployed)
/api/positions, /api/signals, /api/decisions, /api/resolutions,
/api/portfolio — Chat-Claude soll via Exa testen welche verfügbar sind.

### Nutzung
Chat-Claude ruft diese Endpoints via Exa web_fetch, nicht via
Browser-Tools. URL immer aus STATUS.md holen (ändert sich bei
Tunnel-Restart, wird via tunnel_watcher.py aktualisiert).

## DATENQUELLEN-PRIORITÄT (Chat-Claude)

1. /api/summary + /api/logs  → LIVE (sekunden-aktuell)
2. STATUS.md im Repo         → alle 5min gepusht (wenn Timer an)
3. TASKS.md im Repo          → Claude Code pflegt
4. KNOWLEDGE_BASE.md         → Claude Code pflegt nach jedem Fix
5. Training/Erinnerung       → IMMER gegen 1-4 validieren

Bei Widerspruch: 1 > 2 > 3 > 4 > 5.

---

## SESSION-START (Claude Code)

Beim Start einer neuen Session immer:

1. `cat STATUS.md` — aktueller Bot-Status + Dashboard-URL
2. `cat TASKS.md` — offene Tasks, Prioritäten
3. `cat KNOWLEDGE_BASE.md` — bekannte Bugs und Workarounds
4. `tail -50 /root/KongTradeBot/bot.log` — letzte Log-Zeilen
5. `/api/summary` via Exa fetchen — Live-Kennzahlen

Niemals Code ändern ohne vorher den aktuellen Server-Status zu kennen.

## COMMIT-KONVENTIONEN

```
fix: kurze Beschreibung (T-XXX)
feat: neue Funktion (T-XXX)
docs: Dokumentation
chore: Housekeeping
```

## KRITISCHE REGELN

- NIEMALS `update_balance_allowance()` nach einem Fill aufrufen
- IMMER `set_api_creds()` vor Trading-Calls
- `signature_type=1` für Magic-Link Accounts (nicht 0)
- `funder=config.polymarket_address` beim ClobClient-Init
- Bot läuft auf Hetzner Helsinki `89.167.29.183` — nicht lokal
- Vor jedem `systemctl restart kongtrade-bot`: 5 Min Log beobachten
