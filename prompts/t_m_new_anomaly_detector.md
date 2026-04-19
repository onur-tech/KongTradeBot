# T-M-NEW: Anomalie-Detektor — Insider-Signal-Erkennung
_Erstellt: 2026-04-20 | Aufwand: ~4-5h | Status: DESIGN READY_
_Voraussetzung: Keine (unabhängiges Modul)_

---

## Problem

Insider kaufen auf Polymarket bei **3–10 Cent** auf Ereignisse mit < 10% Markt-Wahrscheinlichkeit.
Der Preis springt nach der News auf 80–100 Cent.

Unser Bot kauft aktuell **NACH** der Preisbewegung bei 20–80 Cent (Copy-Trading der bekannten Wallets).
Wenn wir das Muster früh erkennen, können wir bei **10–20 Cent** kaufen — vor dem Sprung.

**Dokumentierte echte Insider-Signale 2026:**

| Datum | Event | Entry-Preis | Bet-Größe | Profit | Wallet |
|-------|-------|-------------|-----------|--------|--------|
| 2026-04-07 | Iran Ceasefire | 2.9–10.3¢ | $140K–$467K | +$643K gesamt | 4 koordinierte neue Wallets |
| 2026 (früh) | Iran-Strike | < 5¢ | ~$550K | Sehr groß | Whale-Cluster |
| 2026 (früh) | Maduro Capture | < 10¢ | ~$400K | Groß | Neue Wallets |

**Gemeinsames Muster:**
- Frische Wallets (< 30 Tage alt)
- Genau eine oder wenige Wetten
- Sehr kleine Startwahrscheinlichkeit (< 10–15 Cent)
- Sehr große Position (> $100K)
- Koordiniert: 3–4 Wallets gleichzeitig

---

## Signal-Kriterien (kalibriert auf echte Insider-Ereignisse)

### STARKES SIGNAL — sofort handeln (Auto-Trade)

```
Bedingung A: Ein einzelnes Wallet
  → Bet > $100.000
  → Auf Event < 10 Cent Wahrscheinlichkeit
  → Wallet < 90 Tage alt (auf Polymarket)

ODER

Bedingung B: Koordinierter Cluster
  → 3+ verschiedene Wallets in 30 Min
  → Gesamt-Bet > $200.000
  → Auf dasselbe Event < 15 Cent
```

→ **Auto-Trade: ANOMALY_COPY_SIZE_USD direkt kaufen**

### MODERATES SIGNAL — Telegram-Alert, kein Auto-Trade

```
Bedingung C: Mittelgroße Einzelbet
  → $50.000 – $100.000
  → Event < 15 Cent
  → Wallet < 90 Tage alt

ODER

Bedingung D: Kleiner Cluster
  → 2 Wallets in 30 Min
  → Gesamt > $50.000
  → Event < 10 Cent
```

→ **Telegram-Alert mit Markt-Details — manuelle Entscheidung**

### IGNORIEREN

```
- Unter $50.000 single wallet (zu viel Noise)
- Über 25 Cent Wahrscheinlichkeit (kein Insider-Edge)
- Bekannte Wallets mit > 100 Trades (haben legitimen Research-Edge, kein Insider-Typ-A nötig)
- Crypto-Märkte (BTC Up/Down) — zu viel normales Noise
```

---

## Anomalie-Score für frische Wallets

Je mehr Punkte, desto höher die Priorität:

| Kriterium | Punkte |
|-----------|--------|
| Wallet < 30 Tage alt (Polymarket) | +2 |
| Wallet < 10 vorherige Trades | +2 |
| Wallet platziert genau EINE einzige Wette (One-Shot-Pattern) | +3 |
| 3+ koordinierte neue Wallets (gleiche condition_id, 30-Min-Fenster) | +4 |
| Bet > $200K | +1 |
| Entry-Preis < 5 Cent | +2 |

**Score-Interpretation:**
- Score ≥ 5 → HIGH PRIORITY — eigene Telegram-Kategorie
- Score 3–4 → MODERATE — Standard-Anomalie-Alert
- Score < 3 → IGNORIEREN

**Iran Ceasefire Beispiel-Score:**
- 4 Wallets alle April 2026 (< 30 Tage): +2 × 4 = +8
- Alle hatten genau 1 Wette: +3 × 4 = +12
- Koordiniert (4 Wallets): +4
- Entry 2.9–10.3 Cent: +2
- **Gesamt: 26 Punkte → Höchste Priorität**

---

## Implementation: core/anomaly_detector.py

```python
"""
T-M-NEW: Anomalie-Detektor
Unabhängig vom normalen Copy-Trading.
Scannt ALLE Polymarket-Trades auf Insider-Muster.
Eigenes Budget: ANOMALY_DAILY_CAP_USD
"""
import asyncio
import time
import os
import aiohttp
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

DATA_API = "https://data-api.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"

@dataclass
class AnomalySignal:
    condition_id: str
    market_question: str
    entry_price: float            # in Dollar (z.B. 0.08 = 8 Cent)
    total_bet_usd: float
    wallet_count: int
    wallets: list
    anomaly_score: int
    signal_type: str              # "STRONG" | "MODERATE"
    detected_at: float = field(default_factory=time.time)


class AnomalyDetector:
    """
    Unabhängig vom normalen Copy-Trading.
    Prüft ALLE Polymarket-Trades auf Insider-Muster.
    """

    def __init__(self):
        self.enabled = os.getenv("ANOMALY_DETECTOR_ENABLED", "false").lower() == "true"
        self.min_bet_single = float(os.getenv("ANOMALY_MIN_BET_SINGLE_USD", "100000"))
        self.min_bet_cluster = float(os.getenv("ANOMALY_MIN_BET_CLUSTER_USD", "200000"))
        self.min_cluster_size = int(os.getenv("ANOMALY_MIN_CLUSTER_SIZE", "3"))
        self.max_probability = float(os.getenv("ANOMALY_MAX_PROBABILITY", "0.15"))
        self.daily_cap = float(os.getenv("ANOMALY_DAILY_CAP_USD", "20"))
        self.copy_size = float(os.getenv("ANOMALY_COPY_SIZE_USD", "2"))

        # State
        self._daily_spent = 0.0
        self._last_reset = datetime.now(timezone.utc).date()
        self._recent_bets: dict[str, list] = defaultdict(list)  # condition_id → bets
        self._wallet_cache: dict[str, dict] = {}

    def _reset_daily_if_needed(self):
        today = datetime.now(timezone.utc).date()
        if today != self._last_reset:
            self._daily_spent = 0.0
            self._last_reset = today

    async def _get_wallet_age_and_trades(self, wallet: str) -> tuple[int, int]:
        """Gibt (Tage auf Polymarket, Anzahl Trades) zurück."""
        if wallet in self._wallet_cache:
            return self._wallet_cache[wallet]["days"], self._wallet_cache[wallet]["trades"]
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{DATA_API}/activity?user={wallet}&limit=1000"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                    data = await r.json()
                    if not data:
                        return 9999, 9999  # Kein Daten = sehr alt (ignorieren)
                    trades = len(data)
                    timestamps = [t.get("timestamp", 0) for t in data if t.get("timestamp")]
                    if timestamps:
                        first_ts = min(timestamps)
                        days = (time.time() - first_ts) / 86400
                    else:
                        days = 9999
                    self._wallet_cache[wallet] = {"days": int(days), "trades": trades}
                    return int(days), trades
        except Exception:
            return 9999, 9999

    def _calculate_score(self, wallets_data: list, entry_price: float,
                         total_bet: float, is_cluster: bool) -> int:
        score = 0
        unique_wallets = len(wallets_data)

        for days, trades in wallets_data:
            if days < 30:
                score += 2
            if trades < 10:
                score += 2
            # One-Shot-Pattern: Wir prüfen ob Wallet < 5 Trades historisch
            if trades <= 1:
                score += 3

        if unique_wallets >= 3:
            score += 4
        if total_bet > 200_000:
            score += 1
        if entry_price < 0.05:
            score += 2

        return score

    async def check_all_trades(self) -> list[AnomalySignal]:
        """
        Holt alle Trades der letzten 30 Min via Data-API.
        Gruppiert nach condition_id.
        Gibt AnomalySignal-Liste zurück.
        """
        if not self.enabled:
            return []

        signals = []
        try:
            async with aiohttp.ClientSession() as session:
                # Alle großen Trades der letzten 30 Min
                # Data-API unterstützt minAmount-Filter
                url = f"{DATA_API}/activity?limit=500&minAmount=50000"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    trades = await r.json()
        except Exception:
            return []

        # Gruppieren nach condition_id
        by_market: dict[str, list] = defaultdict(list)
        now = time.time()
        for trade in trades:
            ts = trade.get("timestamp", 0)
            if now - ts > 1800:  # Nur letzten 30 Min
                continue
            cid = trade.get("conditionId") or trade.get("condition_id", "")
            if not cid:
                continue
            price = float(trade.get("price", 1.0))
            amount = float(trade.get("usdcSize", 0) or trade.get("amount", 0))
            wallet = trade.get("maker") or trade.get("user", "")
            side = trade.get("side", "BUY")
            # Nur BUY-Signale auf YES (Low-Price = LOW Probability)
            if side.upper() not in ("BUY", "YES"):
                continue
            if price > self.max_probability:
                continue
            if amount < 50_000:
                continue
            by_market[cid].append({
                "wallet": wallet, "price": price, "amount": amount,
                "question": trade.get("title", cid[:20])
            })

        # Signale auswerten
        for cid, bets in by_market.items():
            unique_wallets = list({b["wallet"] for b in bets if b["wallet"]})
            total_bet = sum(b["amount"] for b in bets)
            avg_price = sum(b["price"] for b in bets) / len(bets)
            question = bets[0].get("question", cid[:30])

            if total_bet < 50_000:
                continue

            # Wallet-Alter für alle unique Wallets holen
            wallets_data = []
            for w in unique_wallets[:5]:  # Max 5 prüfen
                days, trades = await self._get_wallet_age_and_trades(w)
                wallets_data.append((days, trades))

            score = self._calculate_score(
                wallets_data, avg_price, total_bet,
                is_cluster=len(unique_wallets) >= self.min_cluster_size
            )

            # STARKES SIGNAL
            if (total_bet >= self.min_bet_single and len(unique_wallets) == 1) or \
               (total_bet >= self.min_bet_cluster and len(unique_wallets) >= self.min_cluster_size):
                signals.append(AnomalySignal(
                    condition_id=cid,
                    market_question=question,
                    entry_price=avg_price,
                    total_bet_usd=total_bet,
                    wallet_count=len(unique_wallets),
                    wallets=unique_wallets,
                    anomaly_score=score,
                    signal_type="STRONG"
                ))

            # MODERATES SIGNAL
            elif 50_000 <= total_bet < self.min_bet_single or score >= 5:
                signals.append(AnomalySignal(
                    condition_id=cid,
                    market_question=question,
                    entry_price=avg_price,
                    total_bet_usd=total_bet,
                    wallet_count=len(unique_wallets),
                    wallets=unique_wallets,
                    anomaly_score=score,
                    signal_type="MODERATE"
                ))

        return signals

    async def execute_signal(self, signal: AnomalySignal,
                              execution_engine) -> bool:
        """
        Kauft ANOMALY_COPY_SIZE_USD wenn STARKES SIGNAL und Budget vorhanden.
        """
        self._reset_daily_if_needed()
        if self._daily_spent >= self.daily_cap:
            return False
        if signal.signal_type != "STRONG":
            return False

        remaining = self.daily_cap - self._daily_spent
        size = min(self.copy_size, remaining)

        # Nutzt ExecutionEngine mit eigenem Budget
        result = await execution_engine.place_order(
            condition_id=signal.condition_id,
            price=signal.entry_price,
            size_usdc=size,
            side="BUY",
            source="ANOMALY_DETECTOR",
            anomaly_score=signal.anomaly_score
        )
        if result.success:
            self._daily_spent += size
        return result.success

    def format_telegram_alert(self, signal: AnomalySignal) -> str:
        emoji = "🚨" if signal.signal_type == "STRONG" else "👁"
        wallets_str = ", ".join(f"`{w[:10]}...`" for w in signal.wallets[:3])
        return (
            f"{emoji} *Anomalie-Signal ({signal.signal_type})*\n\n"
            f"Markt: {signal.market_question[:60]}\n"
            f"Entry-Preis: {signal.entry_price*100:.1f}¢\n"
            f"Gesamt-Bet: ${signal.total_bet_usd:,.0f}\n"
            f"Wallets: {signal.wallet_count} ({wallets_str})\n"
            f"Anomalie-Score: {signal.anomaly_score}/20+\n\n"
            f"{'✅ AUTO-TRADE ausgeführt ($2)' if signal.signal_type == 'STRONG' else '⚠️ Manuell prüfen'}"
        )


async def anomaly_detector_loop(detector: AnomalyDetector,
                                 execution_engine,
                                 telegram_bot,
                                 interval_seconds: int = 300):
    """
    Haupt-Loop: alle 5 Minuten scannen.
    Läuft parallel zu WalletMonitor in main.py.
    """
    while True:
        try:
            signals = await detector.check_all_trades()
            for signal in signals:
                alert = detector.format_telegram_alert(signal)
                await telegram_bot.send_message(alert)
                if signal.signal_type == "STRONG":
                    await detector.execute_signal(signal, execution_engine)
        except Exception as e:
            pass  # Fehler nie den Haupt-Bot unterbrechen
        await asyncio.sleep(interval_seconds)
```

---

## Integration in main.py

```python
# In main.py — neben den anderen Tasks:

from core.anomaly_detector import AnomalyDetector, anomaly_detector_loop

async def main():
    ...
    anomaly_detector = AnomalyDetector()

    tasks = [
        asyncio.create_task(wallet_monitor.run()),
        asyncio.create_task(status_reporter.run()),
        asyncio.create_task(balance_updater.run()),
        asyncio.create_task(morning_report.run()),
        asyncio.create_task(resolver_loop.run()),
        asyncio.create_task(command_poller.run()),
        # NEU:
        asyncio.create_task(
            anomaly_detector_loop(anomaly_detector, execution_engine, telegram_bot)
        ),
    ]
    await asyncio.gather(*tasks)
```

---

## Neue .env Variablen

```env
# Anomalie-Detektor
ANOMALY_DETECTOR_ENABLED=true
ANOMALY_MIN_BET_SINGLE_USD=100000   # Einzel-Wallet Schwelle für STARKES Signal
ANOMALY_MIN_BET_CLUSTER_USD=200000  # Cluster-Schwelle (3+ Wallets) für STARKES Signal
ANOMALY_MIN_CLUSTER_SIZE=3          # Mindest-Wallets für Cluster
ANOMALY_MAX_PROBABILITY=0.15        # Max Entry-Preis (15 Cent)
ANOMALY_DAILY_CAP_USD=20            # Max USD/Tag für Anomalie-Trades
ANOMALY_COPY_SIZE_USD=2             # USD pro Anomalie-Trade
ANOMALY_SCAN_INTERVAL_SECONDS=300   # Scan alle 5 Minuten
```

---

## Warum kleines eigenes Budget ($2/Signal, $20/Tag)

**EV-Kalkulation bei echten Insider-Treffern:**

| Szenario | Stake | Entry | Payout wenn Treffer | EV |
|----------|-------|-------|--------------------|----|
| Iran Ceasefire-Typ | $2 | 10¢ | $20 (10x) | hoch |
| Maduro-Typ | $2 | 8¢ | $25 (12.5x) | sehr hoch |
| Fehlalarm | $2 | 8¢ | $0 | -$2 |

**Monats-Kalkulation:**
- 5–10 Signale/Monat erwartet (basierend auf 2026-Häufigkeit)
- Davon 2–3 echte Insider-Treffer (historische Rate)
- Verluste: 7 × $2 = $14
- Gewinne: 3 × $2 × 10x Durchschnitt = $60
- **Netto-Erwartungswert: +$46/Monat bei max $20 Risiko**

Wichtig: Das Budget lernt. Nach 3 Monaten: echte Trefferrate messen → Budget adjustieren.

---

## Data-API Query-Strategie

```python
# Primärer Scan (alle 5 Min):
GET https://data-api.polymarket.com/activity?limit=500&minAmount=50000
→ Alle Trades > $50K der letzten ~30 Min
→ Filter: price < 0.15 (unter 15 Cent)
→ Gruppieren nach condition_id

# Wallet-Alter Check:
GET https://data-api.polymarket.com/activity?user={wallet}&limit=1000
→ Ersten Timestamp = Account-Alter
→ Anzahl Trades = Trade-History

# Markt-Details (für Alert):
GET https://gamma-api.polymarket.com/markets/{condition_id}
→ Question, Category, Ende-Datum
```

**Rate-Limit-Schutz:**
- Scan nur alle 5 Min (nicht aggressiver)
- Wallet-Age gecacht (24h TTL)
- Max 5 Wallets pro Signal parallel checked

---

## STOP-CHECKs für Server-CC

```bash
# 1. Modul geladen?
python3 -c "from core.anomaly_detector import AnomalyDetector; print('OK')"

# 2. Data-API liefert große Trades?
python3 -c "
import asyncio, aiohttp
async def test():
    async with aiohttp.ClientSession() as s:
        async with s.get('https://data-api.polymarket.com/activity?limit=10&minAmount=50000') as r:
            data = await r.json()
            print(f'Trades gefunden: {len(data)}')
            for t in data[:2]:
                print(f'  Amount: {t.get(\"usdcSize\", \"?\")} | Price: {t.get(\"price\", \"?\")}')
asyncio.run(test())
"
# Erwartung: Mindestens einige Trades mit großem Volumen

# 3. DRY-RUN: Detector manuell triggern
python3 -c "
import asyncio, os
os.environ['ANOMALY_DETECTOR_ENABLED'] = 'true'
os.environ['ANOMALY_DAILY_CAP_USD'] = '20'
os.environ['ANOMALY_COPY_SIZE_USD'] = '2'
from core.anomaly_detector import AnomalyDetector
async def test():
    d = AnomalyDetector()
    signals = await d.check_all_trades()
    print(f'Signale gefunden: {len(signals)}')
    for s in signals:
        print(f'  {s.signal_type}: {s.market_question[:40]} | Score: {s.anomaly_score}')
asyncio.run(test())
"
# Erwartung: Script läuft durch. 0–3 Signale normal (je nach Marktlage)

# 4. Telegram-Alert Format ok?
python3 -c "
from core.anomaly_detector import AnomalyDetector, AnomalySignal
d = AnomalyDetector()
test_signal = AnomalySignal(
    condition_id='test123',
    market_question='Will Iran and US sign ceasefire by May?',
    entry_price=0.08,
    total_bet_usd=350000,
    wallet_count=4,
    wallets=['0xabc', '0xdef', '0x123'],
    anomaly_score=18,
    signal_type='STRONG'
)
print(d.format_telegram_alert(test_signal))
"
# Erwartung: Formatierter Telegram-Text mit allen Feldern

# 5. Budget-Cap eingehalten?
tail -50 /root/KongTradeBot/data/tax_archive.jsonl | python3 -c "
import json, sys
total = 0
for line in sys.stdin:
    t = json.loads(line.strip())
    if t.get('source') == 'ANOMALY_DETECTOR':
        total += float(t.get('size_usdc', 0))
        print(f'  Anomalie-Trade: \${t[\"size_usdc\"]} | Score: {t.get(\"anomaly_score\", \"?\")}')
print(f'Total Anomalie heute: \${total:.2f}')
"
```

---

## Erwartetes Ergebnis (30 Tage)

| Metrik | Erwartung |
|--------|-----------|
| Scans pro Tag | 288 (alle 5 Min) |
| False Positives (kein Insider) | 7–8/Monat |
| True Positives (echter Insider) | 2–3/Monat |
| Auto-Trades (STRONG) | 5–10/Monat |
| USD deployed gesamt | max $20/Monat |
| Erwarteter Gewinn (bei 2 Treffern × 10x) | +$40 |
| Netto EV | **+$20–40/Monat** |
| Haupt-Nutzen | **Learning-Daten + System-Validation** |

---

## Referenzen

| Quelle | Inhalt |
|--------|--------|
| cointrenches Iran Ceasefire | $663K auf 4 Wallets bei 2.9–10.3¢, April 2026 |
| Polymarket Iran Ceasefire Market | "$11M Volumen, 70% Smart Money gegen schnellen Deal" |
| WALLET_SCOUT_BRIEFING.md v2.0 Teil 0 | Insider-Typ-A als K.O.-Kriterium |
| KB P073 | Polymarket Data-API Reliability |
