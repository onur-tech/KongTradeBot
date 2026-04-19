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

## Explicit Invocation Pattern (13–15) — PFLICHT

13. **EXPLICIT INVOCATION PATTERN (kontextbezogen)**

    Bei Wallet/Strategie/Exit/Risk-Aufgaben die **RELEVANTEN** Skills
    aktivieren — nicht pauschal alle 4.

    **Relevanz-Matrix:**

    | Aufgabe | Dalio | Marks | Taleb | Crypto-Analyst |
    |---------|-------|-------|-------|----------------|
    | Wallet-Selektion | ✓ | ✓ | ✓ | — |
    | Portfolio-Construction | ✓✓ | — | ✓ | — |
    | Exit-Strategie | — | ✓ | ✓ | ✓✓ |
    | Risk-Management | ✓ | — | ✓✓ | ✓ |
    | Neue Asset-Klasse | ✓ | ✓ | ✓ | ✓ |
    | Kriterien-Änderung | ✓✓ | ✓ | — | — |
    | Infrastruktur/Bug-Fix | — | — | — | — |

    ✓✓ = Primär (immer aktivieren) | ✓ = Sekundär (wenn relevant) | — = überspringen

    **Schritt 1: Relevanz-Check** — Welche ✓-markierten Skills für diese Aufgabe?

    **Schritt 2: Kontext-Anker prüfen**

    Folgende Domain-spezifische Dokumente konsultieren:
    - Wallet-Themen: `WALLET_SCOUT_BRIEFING.md`
    - Review-Themen: `KONG_REVIEW_SYSTEM.md`
    - Strategie-Themen: `STRATEGY.md`
    - Exit-Themen: `STRATEGY.md` (Abschnitt Exit)
    - Risiko-Themen: `GUIDELINES.md` (Abschnitt Risk)

    **Schritt 3: Externe Recherche** — Erst nach Schritt 1+2.

    **Schritt 4: Synthese** — Welche Quelle liefert welches Argument?

14. **SESSION-START-RITUAL** — Zu Beginn jeder komplexen Aufgabe
    (>15 Min erwarteter Aufwand) explizit fragen:

    1. Welche der 4 Skills sind hier relevant? (Relevanz-Matrix)
    2. Welche Dokumente aus dem docs-Repo sollten gelesen werden?
    3. Ist dies eine Wallet/Strategie/Exit/Risk-Frage?
       → Dann Framework-Check Pflicht (Relevanz-Matrix).
    4. Ist dies eine Infrastruktur/Bug-Fix/Deploy-Frage?
       → Dann Framework-Check entfällt.

15. **ANTI-ZEREMONIE-REGEL**

    Skill-Invocation ist KEIN Legitimations-Stempel.

    **Verboten:**
    - "Laut Taleb's Via Negativa entscheiden wir..."
    - "Dalio sagt X, deshalb machen wir Y"
    - Framework-Citations als Begründungs-Ersatz ohne echten Inhalt

    **Erlaubt:**
    - Bei ECHTER Anwendung: "Das Ruin-Risiko-Argument ist hier zentral
      weil konkret [X] eintreten kann."
    - Bei ECHTEN Gegensätzen: "Dalio würde X sagen, Taleb würde Y —
      hier priorisieren wir Y weil [konkreter Grund]."

    **Test-Frage:** Würde Dalio/Marks/Taleb dieser spezifischen Entscheidung
    zustimmen? Wenn "wahrscheinlich zu wenig Daten" → Framework als Kompass,
    nicht als Kochrezept.
