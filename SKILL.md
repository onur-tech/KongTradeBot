# SKILL.md — Verhaltens-Leitfaden für Claude Code

Dieses Dokument definiert wie Claude Code in diesem Projekt
arbeiten und entscheiden soll.

1. Sicherheit vor Features — kein Code ohne Verständnis deployen.
2. Diagnose vor Fix — erst verstehen, dann ändern.
3. Konservativ bei Unklarheit — lieber nachfragen als falsch handeln.
4. EXIT_DRY_RUN respektieren — nie ohne explizite Erlaubnis auf live wechseln.
5. Kein Silent-Fail — jeder Fehler wird geloggt und gemeldet.
6. Kein over-engineering — nur was die Task verlangt, nicht mehr.
7. Tests vor Commit — Unit-Tests müssen grün sein.
8. Commit-Messages auf Englisch, beschreibend, mit Co-Author-Tag.
9. Struktur: Diagnose → Plan → Implementation → Test → Commit → Verifizierung.
10. KNOWLEDGE_BASE.md lesen wenn unbekannte Domäne oder Architektur-Frage.
11. STRATEGIC_VISION.md konsultieren bei Roadmap- oder Architektur-Entscheidungen.
12. Bei allen Fragen zur Kollaboration mit Alex/Tunay/Dietmar
    oder zum Collective-Modell:
    - COLLECTIVE_VISION.md (Governance, Roadmap, Entscheidungslogik)
    Peer-Modell gilt — keine Chef-Empfehlungen.
13. Vor jedem größeren Feature/Refactor: docs/AUDIT_INDEX.md konsultieren.
    Verbindlicher Audit: docs/AUDIT_2026-04-22.md (Strategic Audit 22.04.2026).
    Audit-Empfehlung > kurzfristiger Wunsch; Abweichung begründen.
