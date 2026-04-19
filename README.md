# KongTradeBot — Docs Repository

Dokumentation des KongTradeBot: Polymarket Copy-Trading-System das Whale-Wallets
proportional nachkauft. Der Source-Code liegt in einem separaten Repo (Server: `89.167.29.183`).

---

## Quick-Start für neue Sessions

```
1. SKILL.md lesen          — Pflicht-Bootstrap für jede Session
2. STATUS.md prüfen        — Bot-Zustand, Portfolio, letzte Trades
3. TASKS.md prüfen         — QUEUE (Prio-Reihenfolge), IN ARBEIT
```

Bei Wallet-Fragen: `WALLET_SCOUT_BRIEFING.md`  
Bei Bug/Tech: `KNOWLEDGE_BASE.md` + `ARCHITECTURE.md`  
Bei Strategie: `STRATEGY.md` + `STRATEGIC_VISION.md`

---

## Navigation nach Use-Case

### System verstehen
| Datei | Inhalt |
|-------|--------|
| `ARCHITECTURE.md` | 4-Step-Pipeline, async Tasks, Datenklassen |
| `STRATEGY.md` | Handelslogik, Multiplier-System, Risiko-Regeln |
| `WALLETS.md` | Aktive TARGET_WALLETS mit Tier + Multiplier |

> ⚠️ **Multiplier-Dual-Source:** Multiplier stehen in `strategies/copy_trading.py` (WALLET_MULTIPLIERS) UND `.env` (WALLET_WEIGHTS). `.env` überschreibt Code-Werte zur Laufzeit — beide Stellen müssen synchron geändert werden. → KB P083
| `SETUP.md` | Services, Befehle, Server-Struktur |
| `LIVE_SETUP.md` | Live-Deployment-Checkliste |

### Was gerade läuft
| Datei | Inhalt |
|-------|--------|
| `STATUS.md` | Bot-Status, Portfolio, letzter bekannter Zustand |
| `TASKS.md` | IN ARBEIT / QUEUE / DONE / BLOCKED |

### Aus Fehlern lernen
| Ressource | Inhalt |
|-----------|--------|
| `KNOWLEDGE_BASE.md` | P001–P082: Lessons Learned, codiert nach Thema |
| `SESSION_RECAPS/` | Tages-Chronologie (2026-04-18, 2026-04-19, ...) |
| `analyses/` | Tiefen-Diagnosen zu spezifischen Problemen |

### Neue Features bauen
| Ressource | Inhalt |
|-----------|--------|
| `prompts/` | Vorbereitete Implementation-Prompts für Server-CC |
| `GUIDELINES.md` | Arbeitsweise, Entscheidungsregeln, Override-Verbote |
| `SKILL.md` | Framework-Invocation, Session-Ritual, Anti-Zeremonie |

### Wallet-Selektion & Strategie
| Datei | Inhalt |
|-------|--------|
| `WALLET_SCOUT_BRIEFING.md` | HF-1 bis HF-10, KongScore, 3-Tier-System (v1.2) |
| `KONG_REVIEW_SYSTEM.md` | Review-Ebenen: monatlich / shadow / dashboard / quarterly |
| `STRATEGIC_VISION.md` | Langfrist-Ziele, Philosophie |
| `COLLECTIVE_VISION.md` | Zusammenarbeit Onur/Alex/TB-Kong |

---

## Knowledge-Base-Kategorien (P001–P082)

| Range | Thema |
|-------|-------|
| P001–P008 | **Infrastruktur-Bugs** — FillTracker, On-Chain-Verifikation, Ghost Trades, NegRisk |
| P022–P031 | **Operations** — Crash-Loops, Config-Deployment, Cloudflare-Tunnel, GitHub-Suspend |
| P033–P040 | **Dashboard & Steuer** — tx_hash-Export, Auto-Claim-Errors, Wallet-Scout-SQLite |
| P041–P051 | **Telegram & Exit-Strategie** — Callbacks, Restart-Loop, Exit-Design, Reddit-Research |
| P052–P066 | **Dokumentation & Kollaboration** — Grok-API, Skill-System, Peer-Modell, Auto-Doc |
| P067–P073 | **Wallet-Verifikation** — Scout-Briefing Peer-Review, Zeitstempel-Semantik, polymonit-Warnung |
| P074–P076 | **Feature-Diagnosen** — Bot-Feature-Asymmetrie, Position-State-Bug, ClobClient kein redeem() |
| P077–P083 | **Polymarket-Infrastruktur** — Multiplier-Audit, Archive-Drift, Relayer-Credentials, Custodial-Architecture, Multiplier-Dual-Source-Pattern |

→ Vollständige Einträge in `KNOWLEDGE_BASE.md`

---

## Aktuelle Baustellen

→ Vollständige Liste: **`TASKS.md`** (IN ARBEIT + QUEUE-Sektion)

Top-Prioritäten heute:
1. **T-M04b** — Auto-Claim via RelayClient (läuft auf Server-CC)
2. **T-M04d** — Take-Profit >=95c Trigger (Prompt: `prompts/t_m04d_take_profit_trigger.md`)
3. **T-M09b** — Multiplier: April#1 Sports 0.3x + HOOK 1.0x (Prompt: `prompts/t_m09b_multiplier_adjust.md`)
4. **T-M08** — Dashboard position_state AKTIV-Zähler korrigieren

---

## Analyses-Verzeichnis

Tiefen-Diagnosen wenn ein Thema mehr als einen KB-Eintrag braucht:

| Datei | Inhalt |
|-------|--------|
| `audit_v1_results_2026-04-19.md` | Wallet-Audit v1.0: 3 Wallets entfernt |
| `claim_fix_research_2026-04-19.md` | Claim-Fix Research (P076 — Vorsicht: P079 korrigiert Credentials) |
| `builder_program_research_2026-04-19.md` | Builder Program = Grants/Leaderboard, kein Claim-Weg (P079) |
| `builder_code_setup_2026-04-19.md` | KongTrade Builder-Profil: Credentials + Integration-Plan |
| `position_state_bug_diagnosis_2026-04-19.md` | 14/25 Positionen stuck: Lifecycle + Fix-Plan (P075) |
| `reconciliation_tax_diagnosis_2026-04-19.md` | Archive-Drift 69%, Steuer-Export-Design (P078) |
| `hook_april_sports_verification_2026-04-19.md` | HOOK/April#1 Verifikation: Multiplier-Kalibrierung (P077) |
| `jakgez_verification_and_polymarket_timestamps_2026-04-19.md` | Zeitstempel-Semantik + Wallet-Verifikation (P071) |
| `manual_candidates_review_2026-04-19.md` | Erasmus + TheSpiritofUkraine: Tier-B-Aufnahme |

---

## Für Collaboratoren (Alex / TB-Kong)

**Zugang:** GitHub Repo `onur-tech/KongTradeBot` (docs-Repo)  
**Server:** `89.167.29.183` — kein direkter Zugang für Collaboratoren (Onur-managed)

**Einstieg:**
1. `SKILL.md` lesen — definiert wie Sessions ablaufen
2. `COLLECTIVE_VISION.md` — Kollaborations-Philosophie
3. `KONG_REVIEW_SYSTEM.md` — Review-Ebenen und Rollen
4. `WALLET_SCOUT_BRIEFING.md` — Wallet-Auswahl-Framework (v1.2)

**Commit-Konvention:** Conventional Commits  
```
feat(scope): kurze Beschreibung
fix(scope): was behoben wurde
docs(scope): nur Dokumentation
refactor(scope): kein Feature-Change
```

**Branches:** Alle Docs-Commits auf `main`. Source-Repo-Commits ebenfalls `main`.  
PRs nur bei größeren strukturellen Änderungen.

---

## Kontakt & Escalation

| Rolle | Person |
|-------|--------|
| Primary / Owner | Onur (onur73@gmail.com) |
| Collaborator | Alex (TB-Kong) |
| Server | claudeuser@89.167.29.183 |

---

_Letztes Update: 2026-04-19_
