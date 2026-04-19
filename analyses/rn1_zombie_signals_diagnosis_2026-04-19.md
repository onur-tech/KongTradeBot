# RN1 "Zombie-Signal" Diagnose (19.04.2026)

_Auslöser: Activity-Report (99e9b13) zählte 152 Signale einer entfernten Wallet_
_Ergebnis: Kein Bug — Pre-Audit-Artifact, vollständig benign_

---

## 1. Fact-Check: Wie viele Signale, welcher Typ?

### Gezählt im Log

```bash
# Alle Einträge mit RN1-Adresse (exkl. WalletMonitor-Startup-Zeilen):
grep -i '2005d16a84ceefa912d4e380cd32e7ff827875ea' bot_2026-04-19.log \
  | grep -v 'WalletMonitor startet' | wc -l
→ 296 Einträge

# Startup-Logs (WalletMonitor startet mit Wallet-Liste):
grep -i '2005d16a' bot_2026-04-19.log | grep 'WalletMonitor startet' | wc -l
→ 27 Einträge

# Gesamt: 323 Zeilen mit RN1-Adresse
```

**Diskrepanz zum Activity-Report (152):** Activity-Report zählte vermutlich nur eine Teilmenge
(z.B. nur "Signal buffered" aber nicht "Multiplikator"-Zeilen). Tatsächlich: 296 non-startup entries.

### Typ-Aufschlüsselung der 296 Einträge

| Typ | Beispiel | Bedeutung |
|-----|---------|-----------|
| `⏳ Signal buffered [RN1]` | `"warte 60s auf weitere Wallets..."` | Signal empfangen, in Buffer |
| `⚖️ Multiplikator 0.2x für RN1` | `$252.39 → $50.48` | Größen-Berechnung |
| `🔍 WalletMonitor startet` | `Targets: [...0x2005d1...]` | Startup-Log (excl.) |

**Kein einziger Eintrag:** `Order erstellt`, `BUY LIVE`, `execute`, `fill` → **0 echte Orders aus RN1**

---

## 2. Timeline-Analyse: Pre oder Post Audit?

### Kritische Timestamps

| Event | Timestamp |
|-------|-----------|
| **Erster RN1 Log-Eintrag (Startup)** | `03:53:56` |
| **Erster RN1 Signal-Eintrag** | `03:57:37` (Signal buffered) |
| **Letzter RN1 Log-Eintrag** | `08:30:56` (Signal buffered) |
| **Audit-Commit 7c29ac9** | `08:31:43` (UTC) |
| **Audit deployt (Bot-Restart nötig)** | nach 08:31:43 |

**Differenz letzter RN1-Log → Audit-Commit: 47 Sekunden**

**Befund: ALLE 323 RN1-Einträge sind PRE-AUDIT.**

Kein einziger RN1-Log-Eintrag nach 08:31:43. Nach dem Audit-Commit und dem nächsten
Bot-Restart lud copy_trading.py die neue WALLET_MULTIPLIERS ohne RN1 — seither still.

### Log-Beweis (erste und letzte Einträge)

```
# Erste Signale (03:57 — RN1 noch legitim in TARGET_WALLETS):
03:57:37 | Signal buffered [RN1] Over auf 'Club León FC vs. FC Juárez: O/U 2.5'
03:57:47 | Signal buffered [RN1] Los Angeles Angels auf 'San Diego Padres vs. LA Angels'

# Letzte Signale (08:28-08:30 — 47-68s vor Audit-Commit):
08:28:13 | Signal buffered [RN1] Yunchaokete Bu auf 'Busan: Leandro Riedi vs Yunchaokete Bu'
08:29:13 | Multiplikator 0.2x für RN1 | $6.11 → $1.22
08:30:56 | Signal buffered [RN1] Under auf 'Everton FC vs. Liverpool FC: O/U 1.5'
← DANN: nichts mehr ←
08:31:43 | [GIT] Commit 7c29ac9 — Remove 3 underperforming wallets
```

---

## 3. Hypothesen-Check

### Hypothese 1 — Pre-Audit-Signale (alle vor Audit-Zeit): ✅ BESTÄTIGT

Alle 296 Signale stammen aus dem Zeitraum 03:53–08:30, in dem RN1 noch aktiv in
`TARGET_WALLETS` war. Der Bot verarbeitete sie korrekt als legitime Signale.

### Hypothese 2 — Cache/In-Memory-State nicht gecleared: ❌ NICHT RELEVANT

Cache-Problem würde Post-Audit-Signale produzieren. Da KEINE Einträge nach 08:31:43
existieren, ist kein Cache-Leak aufgetreten.

### Hypothese 3 — WebSocket-Events kommen weiter an: ❌ NICHT RELEVANT

Gleiche Begründung — keine Post-Audit-Signale nachweisbar.

### Hypothese 4 — Anderer Prozess oder Dead-Instance: ❌ NICHT RELEVANT

Alle Einträge stammen aus demselben `polymarket_bot.copy_trading` Logger-Namespace.

---

## 4. Warum wurden 0 Orders ausgeführt?

296 Signale, 0 Buy-Orders — wie erklärt sich das?

**Mechanismus: Multi-Signal-Buffer + Einzelwallet-Timeout**

```python
# copy_trading.py — Multi-Signal-Boost:
# Signal wird 60s gepuffert und wartet auf weitere Wallets die denselben Markt kaufen.
# Wenn innerhalb 60s kein zweites Wallet denselben Markt kauft → Signal dropped.
⏳ "Signal buffered [RN1] ... — warte 60s auf weitere Wallets..."
```

RN1 kaufte ausschließlich **Sports-Märkte** (Soccer, Baseball, Tennis, Basketball).
Kein anderes Target-Wallet kaufte gleichzeitig dieselben Märkte →
Multi-Signal-Confirmation kam nie → alle Signale verfielen nach 60s Buffer.

**Zusätzlich: 0.2x Multiplier** (niedrigster aller Wallets) → selbst wenn bestätigt,
wäre die Order-Größe nach Risiko-Filter meist unter MIN_TRADE_SIZE gefallen.

**Fazit: RN1 hat mit 296 Signalen keinen einzigen Trade ausgelöst.** Der Multi-Signal-Buffer
hat als natürlicher Filter funktioniert — RN1's Sports-Nische deckte sich nicht mit
dem Rest der Target-Wallets.

---

## 5. Warum laufen noch WALLET_NAMES für RN1?

```python
# strategies/copy_trading.py — Zeile 186:
WALLET_NAMES = {
    ...
    "0x2005d16a84ceefa912d4e380cd32e7ff827875ea": "RN1",  # ← noch vorhanden
    ...
}
```

`WALLET_NAMES` wird für Telegram-Notifications und Log-Labels genutzt.
Es ist nur ein Display-Dict — keine operative Wirkung auf Signalverarbeitung.
Das Entfernen aus `WALLET_MULTIPLIERS` (in `TARGET_WALLETS`) ist der operative Weg.

**Benign.** Kann aber bei nächstem Code-Cleanup aus `WALLET_NAMES` entfernt werden.

---

## 6. Impact-Bewertung

| Aspekt | Bewertung |
|--------|-----------|
| Post-Audit-Signale | ✅ Null — Bot stoppt sofort nach Restart |
| Ausgeführte Orders | ✅ Null — Multi-Signal-Buffer hat gefiltert |
| Archive-Pollution | ✅ Null — keine Orders = keine Archive-Einträge |
| Signal-Statistiken verfälscht | ⚠ Leicht — 296 Signale vor Audit erhöhen RN1-Zähler |
| Operative Risiken | ✅ Keine |

**Gesamt-Impact: Benign.** Rein historisches Log-Artifact.

---

## 7. Empfehlung

| Aktion | Prio | Aufwand |
|--------|------|---------|
| Keine sofortige Maßnahme nötig | — | — |
| `WALLET_NAMES` Cleanup: RN1/Gambler1968/sovereign2013 entfernen | Niedrig (Cleanup) | 2 min |
| Activity-Report-Grep verbessern: Nur Post-Deploy-Signale zählen | Niedrig | 10 min |

**Morgen nicht priorisieren.** Duplicate-Trigger-Fix (T-M04f) und Cap-Erhöhung haben Vorrang.

---

## Zusammenfassung

| Frage | Antwort |
|-------|---------|
| 152 Signale wirklich? | Tatsächlich 296 non-startup RN1-Einträge (Activity-Report zählte Teilmenge) |
| Pre oder Post Audit? | **100% Pre-Audit** — letzter Eintrag 47s vor 7c29ac9 |
| Zombie-Bug? | ❌ NEIN — normales Verhalten vor Entfernung |
| Orders ausgeführt? | ❌ NEIN — Multi-Signal-Buffer hat alle verworfen |
| Fix nötig? | ❌ NEIN — optional: WALLET_NAMES Cleanup |
| Hypothese | **H1 bestätigt:** Pre-Audit-Artifact, vollständig benign |
