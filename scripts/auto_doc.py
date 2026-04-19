#!/usr/bin/env python3
"""
scripts/auto_doc.py — Auto-Documentation Generator (Ebene 2)

Parst Conventional Commits und updated das Docs-Repo automatisch:
  - TASKS.md:         DONE-Eintrag mit T-DXX und Commit-Hash
  - KNOWLEDGE_BASE.md: P0XX-Eintrag wenn Lesson-Feld vorhanden
  - SESSION_RECAPS/YYYY-MM-DD.md: Kumulativer Tages-Log

Usage:
    python3 scripts/auto_doc.py              # Letzten Commit verarbeiten
    python3 scripts/auto_doc.py --hash ABC1234  # Spezifischer Commit
    python3 scripts/auto_doc.py --since 24h     # Alle Commits seit N Stunden
    python3 scripts/auto_doc.py --dry-run        # Preview only, kein Schreiben
    python3 scripts/auto_doc.py --no-push        # Schreiben aber nicht pushen
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

SOURCE_REPO = Path(__file__).parent.parent
DOCS_REPO   = Path.home() / "KongTradeBot-docs"

TYPE_EMOJIS = {
    "fix":      "🐛",
    "feat":     "✨",
    "docs":     "📝",
    "refactor": "♻️",
    "test":     "🧪",
    "perf":     "⚡",
    "chore":    "🔧",
}


# ── CommitParser ──────────────────────────────────────────────────────────────

class CommitParser:
    HEADER_RE = re.compile(r'^(?P<type>\w+)(?:\((?P<scope>[^)]+)\))?:\s*(?P<desc>.+)$')
    SECTION_RE = re.compile(
        r'^(?P<key>Root-Cause|Impact|Fix|Lesson|Closes|Knowledge)\s*:\s*(?P<val>.+)$',
        re.IGNORECASE | re.MULTILINE,
    )

    def parse(self, raw: str) -> dict:
        lines = raw.strip().splitlines()
        header = lines[0].strip() if lines else ""
        body   = "\n".join(lines[1:]).strip()

        m = self.HEADER_RE.match(header)
        commit_type  = m.group("type")  if m else "chore"
        commit_scope = m.group("scope") if m else ""
        commit_desc  = m.group("desc")  if m else header

        sections: dict[str, str] = {}
        for sm in self.SECTION_RE.finditer(body):
            sections[sm.group("key").lower().replace("-", "_")] = sm.group("val").strip()

        return {
            "type":       commit_type,
            "scope":      commit_scope,
            "desc":       commit_desc,
            "header":     header,
            "body":       body,
            "root_cause": sections.get("root_cause", ""),
            "impact":     sections.get("impact", ""),
            "fix":        sections.get("fix", ""),
            "lesson":     sections.get("lesson", ""),
            "closes":     sections.get("closes", ""),
            "knowledge":  sections.get("knowledge", ""),
            "emoji":      TYPE_EMOJIS.get(commit_type, "🔹"),
        }


# ── Git helpers ───────────────────────────────────────────────────────────────

def _git(args: list, cwd=None) -> str:
    result = subprocess.run(
        ["git"] + args, capture_output=True, text=True,
        cwd=str(cwd or SOURCE_REPO),
    )
    return result.stdout.strip()


def get_commits_since(hours: float) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    since  = cutoff.strftime("%Y-%m-%dT%H:%M:%S")
    out = _git(["log", f"--since={since}", "--format=%H%x00%ai%x00%s%x00%B%x00---COMMIT---"])
    return _parse_git_log(out)


def get_commit(hash_: str) -> list[dict]:
    out = _git(["show", "--format=%H%x00%ai%x00%s%x00%B%x00---COMMIT---", "--no-patch", hash_])
    return _parse_git_log(out)


def get_latest_commit() -> list[dict]:
    out = _git(["log", "-1", "--format=%H%x00%ai%x00%s%x00%B%x00---COMMIT---"])
    return _parse_git_log(out)


def _parse_git_log(raw: str) -> list[dict]:
    parser = CommitParser()
    commits = []
    for block in raw.split("---COMMIT---"):
        block = block.strip()
        if not block:
            continue
        parts = block.split("\x00")
        if len(parts) < 4:
            continue
        hash_   = parts[0].strip()
        date_s  = parts[1].strip()
        subject = parts[2].strip()
        body    = parts[3].strip() if len(parts) > 3 else ""
        parsed  = parser.parse(body or subject)
        parsed["hash"]    = hash_[:7]
        parsed["hash_full"] = hash_
        parsed["date"]    = date_s[:10]
        parsed["time"]    = date_s[11:16]
        commits.append(parsed)
    return commits


# ── DocsWriter ────────────────────────────────────────────────────────────────

class DocsWriter:
    def __init__(self, docs_repo: Path, dry_run: bool = False):
        self.docs_repo = docs_repo
        self.dry_run   = dry_run

    def _read(self, path: Path) -> str:
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def _write(self, path: Path, content: str) -> None:
        if self.dry_run:
            print(f"  [DRY-RUN] würde schreiben: {path.relative_to(self.docs_repo)}")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    # ── TASKS.md ─────────────────────────────────────────────────────────────

    def _next_task_id(self, content: str) -> str:
        nums = re.findall(r'T-D(\d+)', content)
        next_num = max((int(n) for n in nums), default=61) + 1
        return f"T-D{next_num:02d}"

    def update_tasks_md(self, commit: dict) -> str | None:
        path = self.docs_repo / "TASKS.md"
        content = self._read(path)
        task_id = self._next_task_id(content)

        emoji = commit["emoji"]
        ctype = commit["type"]
        scope = f"({commit['scope']})" if commit["scope"] else ""
        desc  = commit["desc"]
        date  = commit["date"]
        hash_ = commit["hash"]

        new_row = f"| {task_id} | {emoji} {ctype}{scope}: {desc} ({hash_}) | {date} |\n"

        # Insert nach der ersten Zeile unter "## DONE"
        if "## DONE" not in content:
            print("  WARN: '## DONE' Sektion nicht gefunden in TASKS.md")
            return None

        # Finde Header-Zeile der DONE-Tabelle und füge danach ein
        done_match = re.search(
            r'(## DONE\n\| ID.*\n\|[-| ]+\n)',
            content,
        )
        if done_match:
            insert_pos = done_match.end()
            new_content = content[:insert_pos] + new_row + content[insert_pos:]
        else:
            # Fallback: einfach nach "## DONE\n" einfügen
            new_content = content.replace("## DONE\n", f"## DONE\n{new_row}")

        self._write(path, new_content)
        print(f"  TASKS.md: {task_id} eingefügt — {emoji} {ctype}{scope}: {desc[:50]}")
        return task_id

    # ── KNOWLEDGE_BASE.md ─────────────────────────────────────────────────────

    def _next_p_id(self, content: str) -> str:
        nums = re.findall(r'## P0?(\d+)', content)
        next_num = max((int(n) for n in nums), default=57) + 1
        return f"P{next_num:03d}"

    def update_knowledge_base(self, commit: dict) -> str | None:
        if not commit.get("lesson"):
            return None  # Kein Lesson-Feld → kein KB-Eintrag

        # Explizit angegebene P0XX Nummer bevorzugen
        explicit_id = commit.get("knowledge", "").strip()

        path = self.docs_repo / "KNOWLEDGE_BASE.md"
        content = self._read(path)

        if explicit_id and explicit_id in content:
            print(f"  KB: {explicit_id} existiert bereits — übersprungen")
            return None

        p_id = explicit_id if explicit_id else self._next_p_id(content)
        date = commit["date"]
        hash_ = commit["hash"]
        scope = commit["scope"] or commit["type"]

        entry = f"""
## {p_id} — {commit['desc'][:80]} ({date})
**Status:** FIXED via `{hash_}`
**Scope:** {scope}

**Root Cause:** {commit.get('root_cause') or '—'}

**Impact:** {commit.get('impact') or '—'}

**Fix:** {commit.get('fix') or '—'}

**Lesson:** {commit['lesson']}

"""
        new_content = content.rstrip() + "\n" + entry
        self._write(path, new_content)
        print(f"  KNOWLEDGE_BASE.md: {p_id} eingefügt — {commit['desc'][:50]}")
        return p_id

    # ── SESSION_RECAP ─────────────────────────────────────────────────────────

    def update_session_recap(self, commit: dict) -> None:
        date     = commit["date"]
        time_    = commit["time"]
        hash_    = commit["hash"]
        emoji    = commit["emoji"]
        ctype    = commit["type"]
        scope    = f"({commit['scope']})" if commit["scope"] else ""
        desc     = commit["desc"]

        recap_dir  = self.docs_repo / "SESSION_RECAPS"
        recap_file = recap_dir / f"{date}.md"
        content    = self._read(recap_file)

        new_line = f"- {time_} `{hash_}` {emoji} {ctype}{scope}: {desc}\n"

        if content:
            if "## Commits" in content:
                # Hänge ans Ende der Commits-Sektion
                new_content = content.rstrip() + "\n" + new_line
            else:
                new_content = content.rstrip() + "\n\n## Commits\n" + new_line
        else:
            new_content = f"# Session {date}\n\n## Commits\n{new_line}"

        self._write(recap_file, new_content)
        print(f"  SESSION_RECAPS/{date}.md: Zeile hinzugefügt — {time_} {hash_}")

    # ── Git Commit & Push ─────────────────────────────────────────────────────

    def git_commit_and_push(self, commits: list[dict]) -> bool:
        if self.dry_run:
            print("  [DRY-RUN] git add + commit + push übersprungen")
            return True

        repo = self.docs_repo
        # Stage alle geänderten Docs
        subprocess.run(["git", "add", "-A"], cwd=str(repo), check=True)

        status = _git(["status", "--porcelain"], cwd=repo)
        if not status:
            print("  Docs-Repo: keine Änderungen zu committen")
            return True

        hashes = ", ".join(c["hash"] for c in commits)
        msg = f"docs: auto-update via {hashes}\n\nGenerated by auto_doc.py"
        result = subprocess.run(
            ["git", "commit", "-m", msg],
            cwd=str(repo), capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"  WARN: git commit fehlgeschlagen: {result.stderr[:200]}")
            return False

        push = subprocess.run(
            ["git", "push"],
            cwd=str(repo), capture_output=True, text=True,
        )
        if push.returncode != 0:
            print(f"  WARN: git push fehlgeschlagen: {push.stderr[:200]}")
            return False

        print(f"  Docs-Repo gepusht: {hashes}")
        return True


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hash",     help="Spezifischer Commit-Hash")
    ap.add_argument("--since",    help="Alle Commits seit N Stunden (z.B. '24h' oder '2')")
    ap.add_argument("--dry-run",  action="store_true")
    ap.add_argument("--no-push",  action="store_true")
    args = ap.parse_args()

    if not DOCS_REPO.exists():
        print(f"FEHLER: Docs-Repo nicht gefunden: {DOCS_REPO}")
        print("  git clone https://github.com/onur-tech/KongTradeBot ~/KongTradeBot-docs")
        sys.exit(1)

    # Commits laden
    if args.hash:
        commits = get_commit(args.hash)
    elif args.since:
        hours = float(args.since.rstrip("h"))
        commits = get_commits_since(hours)
    else:
        commits = get_latest_commit()

    if not commits:
        print("Keine Commits gefunden.")
        return

    print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}Verarbeite {len(commits)} Commit(s)...\n")

    writer = DocsWriter(DOCS_REPO, dry_run=args.dry_run)
    processed = []

    for c in commits:
        print(f"── {c['hash']} {c['emoji']} {c['type']}({c['scope']}): {c['desc'][:60]}")
        task_id = writer.update_tasks_md(c)
        p_id    = writer.update_knowledge_base(c)
        writer.update_session_recap(c)
        processed.append(c)

        if args.dry_run:
            print(f"  Preview TASKS.md:         → {task_id or '(keine Änderung)'}")
            print(f"  Preview KNOWLEDGE_BASE.md: → {p_id or '(kein Lesson-Feld)'}")
        print()

    if not args.no_push:
        writer.git_commit_and_push(processed)

    # Letzten verarbeiteten Hash speichern
    if not args.dry_run and processed:
        try:
            Path("/var/lib/kongtrade/last_doc_hash").write_text(
                processed[-1]["hash_full"], encoding="utf-8"
            )
        except Exception:
            pass  # Nicht kritisch

    print(f"✅ Fertig: {len(processed)} Commit(s) dokumentiert")


if __name__ == "__main__":
    main()
