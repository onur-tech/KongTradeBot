# KongTradeBot — Entwicklungs-Guidelines

## Commit-Format (Conventional Commits)

Jeder Commit folgt diesem Format:

```
type(scope): kurze Beschreibung  (max 72 Zeichen)

Root-Cause: Was hat das Problem verursacht?
Impact:     Beobachtbarer Effekt VOR dem Fix (Metriken, User Impact)
Fix:        Was macht dieser Commit? 1-3 Sätze.
Lesson:     Was haben wir gelernt? NUR wenn nicht-offensichtlich.
Closes: T-XXX
Knowledge: P0XX
```

### Gültige Types

| Type | Bedeutung |
|------|-----------|
| `fix` | Bug-Fix |
| `feat` | Neues Feature |
| `docs` | Doku-Änderung |
| `refactor` | Code-Umbau ohne Verhaltens-Änderung |
| `test` | Tests hinzufügen/ändern |
| `perf` | Performance-Verbesserung |
| `chore` | Wartung (deps, config) |

### Gültige Scopes

`risk` · `execution` · `exit` · `watchdog` · `category` · `errors` ·
`dashboard` · `telegram` · `kill_switch` · `slippage` · `monitoring` ·
`analytics` · `state` · `config` · `automation` · `infra`

### Warum dieses Format?

Das `Lesson`-Feld ist die **einzige Quelle für KNOWLEDGE_BASE-Einträge**.
`auto_doc.py` parst das Feld und erstellt automatisch P0XX-Einträge.
`Closes: T-XXX` setzt den TASKS.md-Status auf DONE mit Commit-Hash.

Kein Lesson-Feld → kein KB-Eintrag. Keine Ausnahmen.

---

## Auto-Documentation Pipeline

### Ebene 1 — Conventional Commits

Commit-Template ist aktiv (`.gitmessage`). Bei `git commit` wird das
Template automatisch geladen (interaktiver Editor). `commit.cleanup strip`
entfernt Kommentarzeilen aus der Commit-Message.

### Ebene 2 — auto_doc.py

```bash
# Letzten Commit dokumentieren
python3 scripts/auto_doc.py

# Spezifischer Commit
python3 scripts/auto_doc.py --hash 451c09f

# Alle Commits der letzten 24h
python3 scripts/auto_doc.py --since 24h

# Preview
python3 scripts/auto_doc.py --dry-run
```

Schreibt in `~/KongTradeBot-docs/`:
- `TASKS.md` → neuer DONE-Eintrag
- `KNOWLEDGE_BASE.md` → neuer P0XX-Eintrag (wenn `Lesson:` vorhanden)
- `SESSION_RECAPS/YYYY-MM-DD.md` → Commit-Zeile

### Ebene 3 — session_end.py

```bash
# Naechtliche Narrative generieren (braucht ANTHROPIC_API_KEY in .env)
python3 scripts/session_end.py

# Spezifischer Tag
python3 scripts/session_end.py --date 2026-04-19

# Preview (kein API-Aufruf)
python3 scripts/session_end.py --dry-run
```

Setzt `## Narrative`-Sektion in der SESSION_RECAP-Datei.

### ANTHROPIC_API_KEY

In `.env` eintragen:
```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Code-Regeln

- Kein Error-Handling für Szenarien die nicht passieren können
- `create_and_post_order()` — nie `create_order()` + `post_order()` separat
- `update_balance_allowance()` nie nach einem Fill aufrufen
- Fills immer on-chain verifizieren, nie API-Response allein vertrauen
- TX-Hash-Dedup-Set ist auf 10.000 Einträge begrenzt
- DRY_RUN ist default — `--live` Flag für echte Trades
