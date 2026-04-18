# CHANGES_NIGHT.md — Nacht-Autopilot 17./18.04.2026

_Alle Änderungen seit Commit 6104d97 — bereit für GitHub-Push_

## Neue Dateien
-  — Auto-Claim für redeemable Polymarket-Positionen (alle 30min)

## Geänderte Dateien

### main.py
- **T-NIGHT-3**:  — Dynamic Subscribe nach Orders
- **T-NIGHT-4**:  — Startet Polymarket Data-API als Quelle der Wahrheit
- **T-NIGHT-5**:  als asyncio-Task (alle 30min Auto-Claim)
- **T-NIGHT-8**:  auf 08:00 Europe/Berlin (UTC+2) umgestellt + Portfolio-Daten

### core/execution_engine.py
- **T-NIGHT-3**:  Methode +  Attribut
- **T-NIGHT-3**: Nach Order-Submission: 

### dashboard.py
- **T-NIGHT-2/P013**: WS Events Counter zählt jetzt auch Signale + buffered + Order-erstellt
- **T-NIGHT-2/P006**: Lesbare Fehlermeldungen für Balance/Geoblock (nicht mehr rohe Exception)

### dashboard.html
- **T-NIGHT-2/P014**: CLAIM-Button:  (API-Inkonsistenz gefixt)
- **T-NIGHT-2/P015**:  380px → 600px (alle 37 Positionen sichtbar)

### telegram_bot.py
- **T-NIGHT-8**:  +  mit Portfolio-Daten, Redeemable-Wins, Resolutions heute

### utils/logger.py
- **P020**:  — Duplikat-Log-Zeilen verhindert

### utils/balance_fetcher.py
- **P019**: Skip RPCs die /usr/bin/bash.00 zurückgeben — alle 4 RPCs durchprobieren

### KNOWLEDGE_BASE.md
- **T-NIGHT-1**: P009-P021 hinzugefügt (13 neue Bugs aus Session 17./18.04)

## Blockiert (braucht GitHub-Token)
- T-008: GitHub Push auf Remote — 
- T-021: Public Status Repo KongTradeBot-Status

## Commit-Befehl (nach Token-Erhalt)
On branch main
Your branch is up to date with 'origin/main'.

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   CLAUDE.md
	modified:   README.md
	modified:   core/execution_engine.py
	modified:   dashboard.html
	modified:   dashboard.py
	modified:   heartbeat.txt
	modified:   main.py
	modified:   telegram_bot.py
	modified:   utils/balance_fetcher.py
	modified:   utils/logger.py

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	KNOWLEDGE_BASE.md
	STATUS.md
	TASKS.md
	bot.lock
	core/fill_tracker.py
	test_fill_tracker.py

no changes added to commit (use "git add" and/or "git commit -a")
