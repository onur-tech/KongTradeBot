# KongTradeBot — SKILL.md
_Chat-Claude Pflicht-Kontext bei jedem Session-Start_

## Session-Start Fetches (1–9)

Chat-Claude fetcht bei jedem neuen Chat diese 9 Dokumente:

1. https://raw.githubusercontent.com/onur-tech/KongTradeBot/main/GUIDELINES.md
2. https://raw.githubusercontent.com/onur-tech/KongTradeBot/main/STRATEGY.md
3. https://raw.githubusercontent.com/onur-tech/KongTradeBot/main/WALLETS.md
4. https://raw.githubusercontent.com/onur-tech/KongTradeBot/main/ARCHITECTURE.md
5. https://raw.githubusercontent.com/onur-tech/KongTradeBot/main/SETUP.md
6. https://raw.githubusercontent.com/onur-tech/KongTradeBot/main/STATUS.md
7. https://raw.githubusercontent.com/onur-tech/KongTradeBot/main/TASKS.md
8. https://raw.githubusercontent.com/onur-tech/KongTradeBot/main/KNOWLEDGE_BASE.md
9. https://raw.githubusercontent.com/onur-tech/KongTradeBot/main/BACKTEST_RESULTS.md

GUIDELINES.md hat Vorrang bei Widersprüchen.

---

## Investment-Frameworks (10–12) — PFLICHT

10. Bei allen Risiko-, Portfolio- und Investment-Entscheidungen
    IMMER die folgenden Skill-Frameworks konsultieren:
    - `/mnt/skills/user/dalio-risiko-framework/SKILL.md`
      → All-Weather-Prinzip, Diversifikation, Risk-Parity
    - `/mnt/skills/user/howard-marks-market-cycles/SKILL.md`
      → Zyklus-Awareness, Contrarian-Thinking, Mean-Reversion
    - `/mnt/skills/user/taleb-antifragilitaet/SKILL.md`
      → Asymmetrische Bets, Schwarze Schwäne, Skin-in-the-Game

11. Bei allen Crypto- und Polymarket-Investment-Fragen
    zusätzlich konsultieren:
    - `/mnt/skills/user/crypto-analyst/SKILL.md`
      → Portfolio-Kontext, Exit-Strategien, Market-Knowledge

12. Bei allen Fragen zur Kollaboration mit Alex/Tunay/Dietmar
    oder zum Collective-Modell:
    - `COLLECTIVE_VISION.md` (Governance, Roadmap, Entscheidungslogik)
    - Peer-Modell gilt — keine Chef-Empfehlungen.

**WICHTIG:** Diese Skills sind nicht optional. Sie werden bei JEDER
Entscheidung zu Risiko, Portfolio, Position-Sizing, Exit-Strategie
oder neuen Investment-Ideen aktiv herangezogen. Bei Widersprüchen
zwischen Frameworks: Chat-Claude dokumentiert die Abwägung explizit.

---

## Explicit Invocation Pattern (13–14) — PFLICHT

13. Bei Aufgaben zu Wallet-Selection, Position-Sizing, Exit-Strategien,
    Portfolio-Konstruktion oder Risk-Management MUSS jede Claude-Instanz
    die folgenden Schritte abarbeiten:

    **Schritt 1: Framework-Check (vor Beginn der Aufgabe)**

    Aktiviere bewusst die 4 relevanten Skills:

    a) **Ray Dalio:** Was sagt das Principles-Framework dazu?
       — Diversifikation? Unkorrelierte Bets? System vs Intuition?

    b) **Howard Marks:** Welche Marktzyklus/Contrarian-Perspektive fehlt?
       — Was wissen alle? (Dann kein Edge) Ist die Wallet stress-getestet?

    c) **Nassim Taleb:** Ist das antifragil oder fragil?
       — Wo ist Ruin-Risiko? Asymmetrischer Upside? Via-Negativa-Denken?

    d) **Crypto-Analyst:** Wie passt das zu unserem Portfolio-Kontext?

    **Schritt 2: Kontext-Anker prüfen**

    Folgende Domain-spezifische Dokumente konsultieren:
    - Wallet-Themen: `WALLET_SCOUT_BRIEFING.md`
    - Review-Themen: `KONG_REVIEW_SYSTEM.md`
    - Strategie-Themen: `STRATEGY.md`
    - Exit-Themen: `STRATEGY.md` (Abschnitt Exit)
    - Risiko-Themen: `GUIDELINES.md` (Abschnitt Risk)

    **Schritt 3: Externe Recherche**

    Erst NACH Framework-Check und Kontext-Anker externe Quellen.
    Andernfalls Gefahr von Best-Practice ohne Prinzipien.

    **Schritt 4: Synthese**

    Kombiniere Framework-Insights + Kontext-Wissen + aktuelle Recherche.
    Dokumentiere welche Quelle welches Argument liefert.

14. **SESSION-START-RITUAL** — Zu Beginn jeder komplexen Aufgabe
    (>15 Min erwarteter Aufwand) explizit fragen:

    1. Welche der 4 Skills sind hier relevant?
    2. Welche Dokumente aus dem docs-Repo sollten gelesen werden?
    3. Ist dies eine Wallet/Strategie/Exit/Risk-Frage?
       → Dann Framework-Check Pflicht.
    4. Ist dies eine Infrastruktur/Bug-Fix/Deploy-Frage?
       → Dann Framework-Check optional.
