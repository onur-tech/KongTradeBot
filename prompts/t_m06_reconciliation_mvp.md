# T-M06 Reconciliation MVP
_Erstellt: 2026-04-20 | Aufwand: ~5-6h | Status: DESIGN READY_
_Voraussetzung: T-M08 vollständig deployed_

---

## Problem

Archive und On-Chain divergieren systematisch:

| Metrik | Archive | On-Chain | Delta |
|--------|---------|----------|-------|
| Trades | 110 | 40 | +70 Ghost-Trades |
| Volumen | $1,662 USDC | $522 USDC | +$1,140 Phantom |
| Drift-Quote | — | — | **69–84.9%** |

**Root-Cause 1:** Signal-Logging schreibt VOR Ausführungsbestätigung ins Archive (Ghost-Trades)
**Root-Cause 2:** Manuelle Claims außerhalb des Bots fehlen im Archive (Wuning +$50.13)
**Root-Cause 3:** Failed Orders werden ins Archive geschrieben als wären sie erfüllt
**Root-Cause 4:** Resolver auto-save vor T-M08 Phase 3 nicht aktiviert

**Konsequenz:** Steuer-Export 2026 unmöglich, P&L-Zahlen falsch, tägliche Reports unzuverlässig

---

## Scope MVP (minimal, funktioniert)

**NICHT in scope:**
- Rückwirkende Korrektur aller 110 Einträge (zu aufwändig, zu fehleranfällig)
- Vollautomatischer Abgleich aller historischen Trades (Phase 2, nach MVP)
- Kalshi- oder andere Platform-Integration

**IN scope:**
- Ab sofort: Nur noch confirmed Trades ins Archive (kein Ghost-Write mehr)
- Täglicher Reconciliation-Report via Telegram
- Manueller Claim-Tracker (Wuning, Busan und zukünftige)

---

## Phase 1 — Signal-Logging Fix (~1h, Server-CC)

**Root-Cause finden:**

```bash
# Wo wird ins Archive geschrieben?
grep -n "archive\|log_trade\|tax" /root/KongTradeBot/utils/tax_archive.py | head -30
grep -n "archive\|log_trade" /root/KongTradeBot/strategies/copy_trading.py | head -20
grep -n "archive\|log_trade" /root/KongTradeBot/core/execution_engine.py | head -20

# Typisches falsches Muster (VORHER):
# In copy_trading.py ODER execution_engine.py nach Signal-Empfang:
# archive.log_trade(signal=signal)  ← schreibt BEVOR Order bestätigt
```

**Fix:** Archive-Eintrag nur nach erfolgreicher Order-Bestätigung mit tx_hash:

```python
# NUR hier schreiben — NACH Bestätigung in execution_engine.py:
if order_result.get("success") and order_result.get("order_id"):
    archive.log_trade(
        signal=signal,
        order_id=order_result["order_id"],
        tx_hash=order_result.get("tx_hash", ""),
        confirmed=True
    )
# Bei Failure: KEIN Eintrag ins Archive
```

**STOP-CHECK Phase 1:**
```bash
# 10 neue Orders abwarten, dann prüfen:
tail -20 /root/KongTradeBot/data/tax_archive.jsonl | python3 -c "
import json, sys
for line in sys.stdin:
    t = json.loads(line.strip())
    print(t.get('tx_hash', 'KEIN TX_HASH')[:20], t.get('confirmed', 'UNBEKANNT'))
"
# Erwartung: Alle 10 haben tx_hash, alle haben confirmed=True
```

---

## Phase 2 — Täglicher Reconciliation-Report (~2h, Server-CC)

**Neues Script:** `scripts/reconcile.py`

```python
#!/usr/bin/env python3
"""
T-M06 Phase 2: Täglicher Abgleich Archive vs Polymarket Data-API.
Sendet Reconciliation-Report via Telegram täglich 21:00 (nach Daily-Summary 20:00).
"""
import json, requests, os
from datetime import datetime, timedelta

PROXY = os.getenv("POLYMARKET_ADDRESS", "")
DATA_API = "https://data-api.polymarket.com"
ARCHIVE_PATH = "/root/KongTradeBot/data/tax_archive.jsonl"

def get_onchain_trades(days_back=1):
    """Holt echte On-Chain Trades der letzten N Tage."""
    since = int((datetime.now() - timedelta(days=days_back)).timestamp())
    r = requests.get(f"{DATA_API}/activity?user={PROXY}&limit=500", timeout=10)
    trades = r.json() if r.ok else []
    return [t for t in trades if t.get("timestamp", 0) > since]

def get_archive_trades(days_back=1):
    """Liest Archive-Einträge der letzten N Tage."""
    since = datetime.now() - timedelta(days=days_back)
    trades = []
    if not os.path.exists(ARCHIVE_PATH):
        return trades
    with open(ARCHIVE_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                t = json.loads(line)
                ts_str = t.get("timestamp", "")
                if ts_str:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if ts.replace(tzinfo=None) > since:
                        trades.append(t)
            except Exception:
                continue
    return trades

def reconcile(days_back=1):
    onchain = get_onchain_trades(days_back)
    archive = get_archive_trades(days_back)

    onchain_ids = {t.get("transactionHash", "") for t in onchain if t.get("transactionHash")}
    archive_ids = {t.get("tx_hash", "") for t in archive if t.get("tx_hash")}

    ghost_trades = [t for t in archive if t.get("tx_hash") and t["tx_hash"] not in onchain_ids]
    missing_from_archive = [t for t in onchain if t.get("transactionHash") not in archive_ids]

    drift_pct = len(ghost_trades) / max(len(archive), 1) * 100

    report = (
        f"📊 *Reconciliation Report {datetime.now().strftime('%d.%m.%Y')}*\n\n"
        f"Archive gestern: {len(archive)} Einträge\n"
        f"On-Chain gestern: {len(onchain)} Trades\n\n"
        f"✅ Matched: {len(archive) - len(ghost_trades)}\n"
        f"👻 Ghost-Trades (Archive ohne TX): {len(ghost_trades)}\n"
        f"❓ Fehlt im Archive: {len(missing_from_archive)}\n\n"
        f"Drift-Quote: {drift_pct:.1f}% (Ziel: <5%)"
    )
    return report, ghost_trades, missing_from_archive

if __name__ == "__main__":
    report, ghosts, missing = reconcile()
    print(report)
    if ghosts:
        print("\nGhost-Trades:")
        for t in ghosts[:5]:
            print(f"  {t.get('timestamp','?')[:10]} | {t.get('tx_hash','?')[:16]}...")
    if missing:
        print(f"\nFehlen im Archive: {len(missing)} Trades")
```

**systemd-Timer:** `scripts/reconcile.timer` — täglich 21:00 Berlin
(1 Stunde nach Daily-Summary um 20:00 via 3364181)

**STOP-CHECK Phase 2:**
```bash
python3 /root/KongTradeBot/scripts/reconcile.py
# Erwartung: Script läuft ohne Fehler, Report-Format korrekt
# Drift-Quote nach Phase 1: Deutlich unter 69% (neue Trades korrekt)
# Historische Ghost-Trades: Noch sichtbar bis manuell bereinigt
```

---

## Phase 3 — Manueller Claim-Tracker (~1h, Server-CC)

Claims die außerhalb des Bots passieren (Polymarket UI: Wuning +$50.13, Busan +$39.00)
werden nicht geloggt. Fix: Script fragt Data-API nach geclaimten Positionen und
ergänzt fehlende Einträge als `MANUAL_CLAIM`.

**Neues Script:** `scripts/track_manual_claims.py`

```python
#!/usr/bin/env python3
"""
T-M06 Phase 3: Manueller Claim-Tracker.
GET /positions?user=PROXY&closed=true → prüfe gegen Archive
→ fehlende Positionen als MANUAL_CLAIM ins Archive ergänzen.
"""
import json, requests, os
from datetime import datetime

PROXY = os.getenv("POLYMARKET_ADDRESS", "")
DATA_API = "https://data-api.polymarket.com"
ARCHIVE_PATH = "/root/KongTradeBot/data/tax_archive.jsonl"

def get_closed_positions():
    r = requests.get(f"{DATA_API}/positions?user={PROXY}&closed=true&limit=500", timeout=10)
    return r.json() if r.ok else []

def get_archive_condition_ids():
    ids = set()
    if not os.path.exists(ARCHIVE_PATH):
        return ids
    with open(ARCHIVE_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                t = json.loads(line)
                if t.get("condition_id"):
                    ids.add(t["condition_id"])
            except Exception:
                continue
    return ids

def track_manual_claims():
    closed = get_closed_positions()
    known_ids = get_archive_condition_ids()
    missing = [p for p in closed if p.get("conditionId") not in known_ids]

    added = 0
    with open(ARCHIVE_PATH, "a") as f:
        for p in missing:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "type": "MANUAL_CLAIM",
                "condition_id": p.get("conditionId", ""),
                "market_question": p.get("title", ""),
                "outcome": p.get("outcome", ""),
                "pnl_usdc": float(p.get("cashPnl", 0) or 0),
                "confirmed": True,
                "tx_hash": "",
                "note": "Manuell via Polymarket UI geclaimed — nachträglich erfasst"
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            print(f"  [ADDED] {entry['market_question'][:50]} → PnL ${entry['pnl_usdc']:.2f}")
            added += 1

    print(f"\nManual Claims erfasst: {added}")
    return added

if __name__ == "__main__":
    print("Checking for manual claims not in archive...")
    n = track_manual_claims()
    if n == 0:
        print("Keine fehlenden Claims gefunden.")
```

**STOP-CHECK Phase 3:**
```bash
python3 /root/KongTradeBot/scripts/track_manual_claims.py
# Erwartung: Wuning (+$50.13) und Busan (+$39.00) erscheinen als MANUAL_CLAIM
# Archive hat jetzt 2 korrekte Einträge für manuell geclaime Positionen
```

---

## STOP-CHECKs gesamt (nach allen 3 Phasen)

```bash
# Drift-Quote nach 24h (sollte deutlich unter 69% sein):
python3 /root/KongTradeBot/scripts/reconcile.py

# Wuning + Busan im Archive?
grep -i "MANUAL_CLAIM\|Fajing\|Busan" /root/KongTradeBot/data/tax_archive.jsonl | wc -l
# Erwartung: >= 2

# Neue Orders: haben alle tx_hash?
tail -10 /root/KongTradeBot/data/tax_archive.jsonl | python3 -c "
import json, sys
for line in sys.stdin:
    t = json.loads(line.strip())
    if t.get('type') != 'MANUAL_CLAIM':
        has_tx = bool(t.get('tx_hash'))
        print('tx_hash OK' if has_tx else 'KEIN TX_HASH', t.get('timestamp','?')[:16])
"
```

---

## Edge Cases

| Edge Case | Handling |
|-----------|---------|
| Order submitted aber nie gefüllt | Kein Archive-Eintrag — korrekt nach Phase 1 |
| Partial Fill | Archive-Eintrag mit tatsächlichem Fill-Betrag, confirmed=True |
| Network-Error nach Submit | retry.py (deployed 058497c) versucht Bestätigung, dann Archive |
| Manual Claim in UI | track_manual_claims.py erkennt es täglich — oder manuell aufrufen |
| Rückwirkende historische Ghosts | Bleiben als historischer Datenpunkt, kein Löschen |
| Tax-Export für 2026 | Erst nach Phase 1+3 zuverlässig: neue Trades confirmed, manuelle Claims erfasst |

---

## Deployment-Reihenfolge

```
Phase 1: fix(archive): Logging nur nach Bestätigung — Ghost-Trades eliminieren
Phase 2: feat(scripts): reconcile.py + systemd-Timer 21:00
Phase 3: feat(scripts): track_manual_claims.py
```

**Erwartetes Ergebnis nach 7 Tagen:**
- Drift-Quote neue Trades: < 5% (war 69–84.9%)
- Archive zeigt echte P&L für alle Trades ab Deployment-Datum
- Wuning + Busan als MANUAL_CLAIM korrekt erfasst
- Daily-Reconciliation-Alert um 21:00 bestätigt Qualität täglich
- Steuer-Export 2026 ab sofort möglich (neue Trades + manuelle Claims)

---

## ABSCHLUSSBERICHT (Server-CC nach Implementation)

1. **Phase 1:** Welche Datei hatte den Ghost-Write? Zeile? Fix bestätigt?
2. **Phase 2:** reconcile.py Drift-Quote nach erstem Lauf? Telegram-Alert korrekt?
3. **Phase 3:** Wuning + Busan als MANUAL_CLAIM erfasst? PnL korrekt ($50.13 + $39.00)?
4. **Drift-Quote nach 24h:** Wie viel % (Ziel < 5% für neue Trades)?
5. **Tax-Export:** `python3 main.py --export-tax 2026` — Ausgabe plausibel?

---

## Referenzen

| Quelle | Inhalt |
|--------|--------|
| `analyses/position_state_bug_diagnosis_2026-04-19.md` | Archive-Drift-Diagnose (69%) |
| KB P078 | Archive-Drift Root-Cause |
| `utils/tax_archive.py` | Ghost-Write-Location (Phase 1 Target) |
| Commit 5980e02 | 13 Legacy SELL-Einträge ohne tx_hash geflagged |
| `utils/retry.py` (058497c) | Exponential Backoff für Phase 1 Fix |
| T-M08 (a656bb6) | position_state — RESOLVED erkannte Positionen nicht mehr archiviert |
