# CHANGES_NIGHT.md — Nacht-Autopilot 17./18.04.2026

_Alle Aenderungen seit Commit 6104d97 — bereit fuer GitHub-Push_

## Neue Dateien
- `claim_all.py` — Auto-Claim fuer redeemable Polymarket-Positionen (alle 30min)

## Geaenderte Dateien

### main.py
- T-NIGHT-3: engine.set_fill_tracker() — Dynamic Subscribe nach Orders
- T-NIGHT-4: sync_positions_from_polymarket() — Polymarket als Quelle der Wahrheit
- T-NIGHT-5: claim_loop() als asyncio-Task (alle 30min Auto-Claim)
- T-NIGHT-8: morning_report_sender() auf 08:00 Europe/Berlin (UTC+2) + Portfolio-Daten

### core/execution_engine.py
- T-NIGHT-3: set_fill_tracker() Methode + Dynamic Subscribe nach Order-Submission

### dashboard.py
- P013: WS Events Counter zaehlt jetzt Signale + buffered + Order-erstellt
- P006: Lesbare Fehlermeldungen fuer Balance/Geoblock

### dashboard.html
- P014: CLAIM-Button: p.redeemable || p.isRedeemable
- P015: .tbl-wrap max-height 380px -> 600px (alle 37 Positionen sichtbar)

### telegram_bot.py
- T-NIGHT-8: Morning Report mit Portfolio-Total, Redeemable-Wins, Resolutions heute

### utils/logger.py
- P020: logger.propagate = False — Duplikat-Log-Zeilen verhindert

### utils/balance_fetcher.py
- P019: Skip RPCs die $0.00 zurueckgeben — alle 4 RPCs durchprobieren

### KNOWLEDGE_BASE.md
- T-NIGHT-1: P009-P021 hinzugefuegt (13 neue Bugs aus Session 17./18.04)

## Blockiert (braucht GitHub-Token)
- T-008: GitHub Push
- T-021: Public Status Repo

## Commit-Befehl (nach Token)
git add -A && git push https://TOKEN@github.com/KongTradeBot/KongTradeBot.git main
