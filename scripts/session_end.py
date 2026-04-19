#!/usr/bin/env python3
"""
scripts/session_end.py — Naechtliche Session-Narrative via Claude API (Ebene 3)

Liest alle heutigen Commits, lässt Claude eine Session-Geschichte schreiben,
updated SESSION_RECAPS/YYYY-MM-DD.md und pusht ins Docs-Repo.

Usage:
    python3 scripts/session_end.py           # Heutige Commits
    python3 scripts/session_end.py --date 2026-04-19  # Spezifischer Tag
    python3 scripts/session_end.py --dry-run  # Preview only

Voraussetzung: ANTHROPIC_API_KEY in .env
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, date
from pathlib import Path

SOURCE_REPO = Path(__file__).parent.parent
DOCS_REPO   = Path.home() / "KongTradeBot-docs"

# .env laden
try:
    from dotenv import load_dotenv
    load_dotenv(SOURCE_REPO / ".env")
except ImportError:
    pass


def _git(args: list, cwd=None) -> str:
    result = subprocess.run(
        ["git"] + args, capture_output=True, text=True,
        cwd=str(cwd or SOURCE_REPO),
    )
    return result.stdout.strip()


def get_commits_for_date(target_date: str) -> list[dict]:
    """Holt alle Commits für ein bestimmtes Datum (YYYY-MM-DD)."""
    out = _git([
        "log",
        f"--after={target_date} 00:00:00",
        f"--before={target_date} 23:59:59",
        "--format=%H|%ai|%s",
        "--no-merges",
    ])
    commits = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue
        hash_, date_s, subject = parts
        commits.append({
            "hash":    hash_[:7],
            "date":    date_s[:10],
            "time":    date_s[11:16],
            "subject": subject.strip(),
        })
    return commits


def get_commit_details(hash_: str) -> dict:
    """Holt vollständigen Commit-Body für Details."""
    body = _git(["show", "--format=%B", "--no-patch", hash_])
    return {"hash": hash_[:7], "body": body}


def build_narrative_prompt(commits: list[dict], commit_details: list[dict]) -> str:
    commits_json = json.dumps([
        {"hash": c["hash"], "time": c["time"], "subject": c["subject"],
         "body": d["body"][:500]}
        for c, d in zip(commits, commit_details)
    ], ensure_ascii=False, indent=2)

    return f"""Du bist der Session-Chronist für KongTradeBot.
Heute wurden folgende Commits gemacht:

{commits_json}

Schreibe eine zusammenhängende Session-Zusammenfassung auf Deutsch in Markdown:

1. **Fokus** (1 Satz Hauptthema der Session)
2. **Major Milestones** (3-5 Bullets — was wurde konkret erreicht?)
3. **Kritische Entscheidungen** (Warum wurde X so und nicht anders gelöst?)
4. **Lessons** (Aus den Lesson-Feldern der Commits — nur nicht-offensichtliche Erkenntnisse)
5. **Offene Punkte** (Was wurde nicht abgeschlossen oder bleibt unklar?)
6. **Nächste Session** (Konkrete 2-3 nächste Schritte)

Maximal 300 Wörter. Konkret. Keine Marketing-Sprache. Kein Buzzword-Bingo.
Schreib wie ein erfahrener Entwickler der sich selbst eine Notiz hinterlässt."""


def call_claude(prompt: str) -> str:
    """Ruft Claude Sonnet 4.5 auf und gibt die Narrative zurück."""
    try:
        import anthropic
    except ImportError:
        print("FEHLER: pip install anthropic")
        sys.exit(1)

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("FEHLER: ANTHROPIC_API_KEY nicht gesetzt (in .env eintragen)")
        sys.exit(1)

    import time
    client = anthropic.Anthropic(api_key=api_key)
    for attempt in range(3):
        try:
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except anthropic.RateLimitError as e:
            wait = 30 * (attempt + 1)
            print(f"  Rate-Limit (429) — warte {wait}s, Versuch {attempt+2}/3...")
            time.sleep(wait)
    raise RuntimeError("Rate-Limit nach 3 Versuchen — Account-Credits prüfen auf console.anthropic.com")


def update_session_recap(target_date: str, narrative: str, dry_run: bool) -> None:
    recap_dir  = DOCS_REPO / "SESSION_RECAPS"
    recap_file = recap_dir / f"{target_date}.md"

    existing = recap_file.read_text(encoding="utf-8") if recap_file.exists() else ""

    # Füge Narrative nach bestehenden Commits ein (oder erstelle neue Datei)
    if "## Narrative" in existing:
        # Ersetze bestehende Narrative
        import re
        new_content = re.sub(
            r'## Narrative\n.*?(?=\n## |\Z)',
            f"## Narrative\n{narrative}\n",
            existing, flags=re.DOTALL,
        )
    elif existing:
        new_content = existing.rstrip() + f"\n\n## Narrative\n{narrative}\n"
    else:
        new_content = f"# Session {target_date}\n\n## Narrative\n{narrative}\n"

    if dry_run:
        print("\n── PREVIEW SESSION_RECAP ──────────────────────────────")
        print(new_content[:1200])
        print("── (truncated) ────────────────────────────────────────")
        return

    recap_dir.mkdir(parents=True, exist_ok=True)
    recap_file.write_text(new_content, encoding="utf-8")
    print(f"SESSION_RECAPS/{target_date}.md: Narrative geschrieben ({len(narrative)} Zeichen)")


def git_commit_and_push(target_date: str) -> None:
    repo = DOCS_REPO
    subprocess.run(["git", "add", "-A"], cwd=str(repo), check=True)
    status = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, cwd=str(repo)
    ).stdout.strip()
    if not status:
        print("Docs-Repo: keine Änderungen zu committen")
        return

    msg = f"docs: session-end narrative {target_date}"
    subprocess.run(["git", "commit", "-m", msg], cwd=str(repo), check=True)
    result = subprocess.run(["git", "push"], cwd=str(repo), capture_output=True, text=True)
    if result.returncode != 0:
        print(f"WARN: git push fehlgeschlagen: {result.stderr[:200]}")
    else:
        print(f"Docs-Repo gepusht: {target_date} Narrative")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date",    help="Datum (YYYY-MM-DD), default: heute")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not DOCS_REPO.exists():
        print(f"FEHLER: Docs-Repo nicht gefunden: {DOCS_REPO}")
        sys.exit(1)

    target_date = args.date or date.today().isoformat()
    print(f"Session-Narrative für {target_date}...")

    commits = get_commits_for_date(target_date)
    if not commits:
        print(f"Keine Commits für {target_date} gefunden.")
        return

    print(f"{len(commits)} Commits gefunden:")
    for c in commits:
        print(f"  {c['time']} {c['hash']} {c['subject'][:60]}")

    details = [get_commit_details(c["hash"]) for c in commits]
    prompt  = build_narrative_prompt(commits, details)

    print("\nRufe Claude API auf...")
    if args.dry_run:
        print("[DRY-RUN] Claude-Aufruf übersprungen")
        narrative = "_[DRY-RUN — hier würde die Claude-Narrative stehen]_"
    else:
        narrative = call_claude(prompt)
        print(f"Narrative erhalten: {len(narrative)} Zeichen")

    update_session_recap(target_date, narrative, args.dry_run)

    if not args.dry_run:
        git_commit_and_push(target_date)

    print("✅ Session-End fertig")


if __name__ == "__main__":
    main()
