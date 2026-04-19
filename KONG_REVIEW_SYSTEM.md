# KONG_REVIEW_SYSTEM.md
_Automatisierte Selbst-Überprüfung des Wallet-Selection-Systems_

**Version:** 1.0
**Erstellt:** 2026-04-19

---

## Zweck

Profit allein ist kein ausreichendes Feedback-Signal. Ein Bot kann
profitabel sein und trotzdem systematisch bessere Wallets verpassen.
Dieses System prüft regelmäßig ob unsere Wallet-Auswahl-Kriterien
noch optimal sind.

---

## Die 4 Review-Ebenen

### Ebene 1: Monthly Wallet Audit (automatisch, 1. des Monats)

**Script:** `scripts/monthly_wallet_audit.py`

Aktion:
- Alle APPROVED-Wallets gegen aktuelle Kriterien neu prüfen
- Vergleich mit Vormonat (Score-Drift)
- Disqualifikationen → Telegram-Alert → Brrudi entscheidet
- Automatischer Report in `analyses/monthly_audit_YYYY-MM.md`

### Ebene 2: Shadow Performance Tracking (permanent)

**Datenbank:** `data/shadow_wallets.db`

Was gespeichert wird:
- Alle REJECTED-Wallets (90 Tage Tracking)
- Alle WATCHING-Wallets (unbegrenzt)
- Welches Kriterium hat sie disqualifiziert?
- Fiktive Performance wenn wir sie kopiert hätten

**Wochen-Report (Freitag 23:55):**
```
Top 3 Shadow-Wallets diese Woche wären gewesen:
 - 0xabc: +$87 (abgelehnt wegen HF-1 Sample-Size 42<50)
 - 0xdef: +$45 (abgelehnt wegen HF-3 Max-DD 34%)
 - 0xghi: +$23 (abgelehnt wegen RF-2 Volume-Mover)
```

### Ebene 3: Missed-Profit-Dashboard-Metric

Neue Dashboard-Sektion:
- Shadow-Performance letzte 30 Tage: +$XYZ
- Active-Performance letzte 30 Tage: +$ABC
- Differenz: Aussagekraft über Kriterien-Qualität

| Ergebnis | Interpretation |
|---------|---------------|
| Shadow > Active | Warnung: Kriterien zu streng |
| Shadow < Active | Validiert: Kriterien richtig kalibriert |

### Ebene 4: Quarterly Criteria Review (1.4./1.7./1.10./1.1.)

**Script:** `scripts/quarterly_criteria_review.py`

Ablauf:
1. Sammle Performance-Daten letzte 90 Tage
2. Sammle Shadow-Performance-Daten
3. Claude API (Anthropic) analysiert:
   - Welche Kriterien haben gut funktioniert?
   - Welche nicht?
   - Welche Änderungen werden vorgeschlagen?
4. Später: Grok-API cross-checkt mit aktueller Polymarket-Literatur
5. Report an Brrudi via Telegram + Dashboard
6. Brrudi entscheidet: Änderungen annehmen oder nicht
7. Bei Annahme: WALLET_SCOUT_BRIEFING.md Version-Bump + Git-Commit

---

## Wallet-Zustände

Persistent in `data/wallet_decisions.jsonl`:

| Status | Bedeutung |
|--------|-----------|
| `APPROVED_TIER_A` | Aktiv kopiert mit vollem Multiplier |
| `APPROVED_TIER_B` | Aktiv kopiert mit reduziertem Multiplier |
| `WATCHING` | Passiv beobachtet, Daten werden gesammelt |
| `REJECTED` | Disqualifiziert, Shadow-Tracking 90 Tage |
| `EXPIRED` | 90 Tage Shadow beendet, Daten archiviert |
| `POST_MORTEM_REQUIRED` | 30 Tage als APPROVED, Review offen |

---

## Disziplin-Regeln

| Regel | Inhalt |
|-------|--------|
| DR-1 | Keine Kriterien-Änderung basierend auf Einzelfall |
| DR-2 | Drei Monate konsistente Evidenz nötig für Anpassung |
| DR-3 | Alle Änderungen werden versioniert in Git-History |
| DR-4 | Rollback jederzeit möglich |

---

## Automation-Übersicht

| Timer | Trigger | Aktion |
|-------|---------|--------|
| `monthly_wallet_audit` | 1. jeden Monats 06:00 UTC | Hard-Filter-Check aller APPROVED-Wallets |
| `weekly_shadow_report` | Freitag 23:55 UTC | Top-3-Shadow-Wallets Telegram-Report |
| `quarterly_criteria_review` | 1.4./1.7./1.10./1.1. 06:00 UTC | Claude-API Kriterien-Analyse |
| `daily_missed_profit_update` | Täglich 00:30 UTC | Dashboard-Metric aktualisieren |

---

## Verknüpfung mit WALLET_SCOUT_BRIEFING.md

Dieses Dokument ist das Feedback-System für
[WALLET_SCOUT_BRIEFING.md](WALLET_SCOUT_BRIEFING.md).

- WALLET_SCOUT_BRIEFING.md definiert die Kriterien
- KONG_REVIEW_SYSTEM.md überprüft ob die Kriterien noch stimmen
- Quarterly Review → möglicher Version-Bump in WALLET_SCOUT_BRIEFING.md
