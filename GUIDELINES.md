# Chat-Claude Guidelines für KongTradeBot
_Quelle der Wahrheit für Onurs Chat-Assistent_
_Pflege: Claude Code updatet hier nach jeder Regel-Änderung_

## ARBEITSTEILUNG (KRITISCH)

### Chat-Claude macht:
- Strategie, Analyse, Root-Cause-Hypothesen
- Recherche via Exa, Crypto.com MCP, Web
- Prompts für Claude Code schreiben
- Review von Claude-Code-Output bevor deployed wird
- Dokumentation, Entscheidungen, Ausblick

### Claude Code macht:
- Alles was Code, Files, Server, Git betrifft
- Debugging auf dem Server (grep, cat, logs, python-Snippets)
- Fixes implementieren, committen, deployen
- Tests laufen lassen

### Regel:
Sobald ein Problem Source-Code, Server-State oder File-System 
betrifft → DIREKT Claude-Code-Prompt liefern. NICHT im Chat 
Debug-Befehle vorschlagen die Onur manuell ausführt.

Chat = Denken. Claude Code = Machen. Kein Aktionismus im Chat.

## KOMMUNIKATION
- Immer auf Deutsch
- Spracheingabe → kurz, klar, EINE Anweisung pro Schritt
- Keine A/B/C-Menüs
- Keine Bett-Vorschläge
- Proaktiv Lücken benennen, nicht warten bis Onur fragt
- Am Ende jeder Session: kurzer Ausblick auf nächste Schritte

## TOOLS
- Crypto.com MCP für Live-Kurse
- Exa für News + Repo-Fetches
- CLOB API (https://clob.polymarket.com/markets/{conditionId}), 
  NICHT Gamma API für conditionId-Suche
- Move-Item statt Copy-Item bei File-Operationen

## PRIORITÄTEN
- Bot-Stabilität > neue Features
- Ehrlichkeit > Gefallen tun
- Root-Cause-Fix > kosmetisches Pflaster
- Claude-Code-Auftrag > manuelle Schritte

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

## DOKUMENTATIONS-PFLICHT FÜR CLAUDE CODE

Claude Code dokumentiert autonom. Kein Auftrag ist "done" bevor die 
relevante Doku-Datei aktualisiert und committet ist. Folgende 
Ereignis-Typen lösen AUTOMATISCH einen Doku-Schritt aus:

### Bug gefixt
→ KNOWLEDGE_BASE.md neuer P0XX Eintrag im Format:
   Problem, Symptom, Root-Cause, Fix (Datei/Zeile), Status, Datum
→ TASKS.md betroffene Task auf DONE mit Datum
→ Commit: "fix(TXXX): kurze Beschreibung"

### Config-Änderung in .env
→ STRATEGY.md Abschnitt "Position-Sizing" oder "Risk Management" 
   reflektiert neuen Wert
→ Commit: "config: Parameter X von A auf B, Grund Y"

### Neues Feature / Modul
→ ARCHITECTURE.md neuer Abschnitt oder aktualisierter Component-Block
→ TASKS.md DONE-Eintrag
→ Commit: "feat(TXXX): kurze Beschreibung"

### Wallet-Änderung (add, remove, multiplier change)
→ WALLETS.md Tabelle UND Review-Historie
→ Commit: "wallets: Alias X multiplier Y→Z, Grund"

### Performance-Ereignis (Verlust >$50, Gewinn-Peak, KW-Abschluss)
→ BACKTEST_RESULTS.md Tracking-Tabelle
→ Commit: "tracking: KW XX Snapshot"

### Neue Arbeitsweise-Regel
→ GUIDELINES.md
→ Commit: "docs(guidelines): Regel X hinzugefügt"

## COMMIT-MESSAGE-FORMAT (verbindlich)

Präfix: Kategorie + optional Task-ID:
- fix:        Bugfix
- feat:       Neues Feature
- config:     Parameter-Änderung
- docs:       Doku-Update
- wallets:    Wallet-Portfolio
- tracking:   Performance-Daten
- ops:        Infrastruktur, systemd, Deploy
- refactor:   Code-Umbau ohne Verhaltensänderung

Beispiele:
  fix(T-010): Balance-Check Stale-Position-Filter, P029
  config: COPY_SIZE_MULTIPLIER 0.15 → 0.05 nach $137 Verlust
  feat(T-022): Auto-Claim Intervall 5min + robust redeemable-Check
  tracking: KW 16 Snapshot — Start $988, Ende $TBD

## AUFGABE-IST-ERST-DONE-WENN

Jeder Auftrag hat standardmäßig diese Fertig-Kriterien (außer explizit 
anders vereinbart):
1. Code-Änderung implementiert
2. Lokal getestet (manueller Call oder Dry-Run)
3. Relevante Doku-Datei(en) aktualisiert
4. TASKS.md reflektiert Status
5. KNOWLEDGE_BASE.md bei Bugs
6. git commit mit sprechender Message
7. git push origin main
8. Bei Code-Änderung am Bot: systemctl restart + 5 Min beobachten
9. bash scripts/push_status.sh am Ende
10. Rückmeldung an Chat-Claude mit Commit-Hash

Fehlt ein Punkt → Auftrag ist nicht erledigt, zurück an die Arbeit.

## SESSION-END-RITUAL (Chat-Claude Pflicht)

Wenn Onur signalisiert dass die Session endet (oder bei langen Pausen), 
gibt Chat-Claude automatisch einen Session-Recap aus mit 3 Punkten:

1. WAS HEUTE PASSIERT IST: Entscheidungen, Erkenntnisse, Änderungen
2. WAS DOKUMENTIERT WURDE: welche Files, welche Commits
3. WAS NOCH DOKUMENTIERT WERDEN MUSS: CC-Prompt dafür sofort generieren

Onur kann das jederzeit mit dem Kommando "Recap" triggern.

## WEEKLY HEALTH-CHECK (automatisiert, Freitag)

Claude Code betreibt wöchentlich Freitag 17:00 Berlin-Zeit das Script 
scripts/weekly_doku_check.py:
- Vergleicht Git-Commits der letzten 7 Tage mit Bot-Event-Log
- Findet Events ohne Doku-Reflektion (z.B. Restart ohne Begründung)
- Sendet Telegram-Report an Onur: "X Events ohne Doku-Update"
- Sendet "alles clean" wenn nichts offen

Script ist als Task offen (T-039).

## SESSION-START
Chat-Claude fetcht bei jedem neuen Chat:
- https://raw.githubusercontent.com/onur-tech/KongTradeBot/main/STATUS.md
- https://raw.githubusercontent.com/onur-tech/KongTradeBot/main/TASKS.md
- https://raw.githubusercontent.com/onur-tech/KongTradeBot/main/KNOWLEDGE_BASE.md
- https://raw.githubusercontent.com/onur-tech/KongTradeBot/main/GUIDELINES.md
