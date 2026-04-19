# T-M21 Basket-Strategie Detection
_Erstellt: 2026-04-20 | Aufwand: ~3-4h | Status: DESIGN READY_
_Voraussetzung: T-M08 Phase 3+ deployed_

---

## Problem

SeriouslySirius ($3.6M, 6.339 Trades) und beachboy4 ($4.14M, 149 Trades) platzieren
**mehrere Positionen in kurzen Zeitfenstern** über verschiedene unabhängige Märkte.

Unser Bot kopiert heute jeden Trade als **Einzelsignal**:
- Signal 1 von Wallet X → Multi-Signal-Buffer prüft → 1 von N Bestätigungen
- Signal 2 von gleicher Wallet X (5 Min später) → Buffer prüft erneut → wieder 1 von N
- Resultat: Beide Signale werden einzeln bewertet, nicht als zusammenhängende Basket-Strategie

**Was fehlt:** Wenn ein Whale in 60 Minuten 5–10 Positionen auf verschiedene Märkte platziert,
ist das keine Zufalls-Serie — es ist ein koordinierter **Basket-Move** mit systematischer Logik.
Wir sollten alle oder die stärksten Signale dieses Fensters gemeinsam kopieren.

---

## Strategie-Profile der Ziel-Wallets

### SeriouslySirius — Multi-Market Directional Accumulator

- **Adresse:** `0x16b29c50f2439faf627209b2ac0c7bbddaa8a881`
- **0xinsider Strategie-Typ:** "Directional"
- **Predictions:** 6.339 | **WR:** 50.3% | **Profit:** +$3.6M | **Volume:** $192.6M
- **Größter Einzelgewinn:** $1.18M
- **Merlin:** 20 gleichzeitig offene Positionen in verschiedenen Märkten
- **Joined:** Oktober 2025 (~6 Monate)

**Basket-Verhalten:**
- 35 Trades/Tag Durchschnitt über die Lifetime
- 20 gleichzeitige offene Positionen → viele werden in kurzen Bursts platziert
- Strategie: G:L-Ratio-Edge, nicht hohe Win-Rate (50.3% WR mit $3.6M Profit)
- $192.6M Volume → avg Trade-Size ~$30.4K — moderates Sizing pro Position
- Bei Burst von 10 Positionen: $304K deployed in 60 Min, wir kopieren 10 × $30 = $300 total

**Warum Multi-Signal-Buffer versagt:**
SeriouslySirius ist oft der einzige in einem Markt. Bei WR 50.3% und 6.339 Trades
ist es unwahrscheinlich, dass genau andere Wallets gleichzeitig bestätigen.
→ Signale gehen fast immer verloren (Buffer feuert nicht).

---

### beachboy4 — High-Conviction Multi-Sport

- **Adresse:** `0xc2e7800b5af46e6093872b177b7a5e7f0563be51`
- **Predictions:** 149 gesamt | **Profit:** +$4.14M
- **Januar 18, 2026:** 40 consecutive wins in einem Tag (+$5.6M)
- **Gleichzeitige Bets:** Brestois + Kings vs Warriors am selben Tag (April)
- Sizing: $500K–$1.3M pro Position — sehr großes Ticket

**Basket-Verhalten:**
- Low-frequency aber wenn aktiv: Multi-Sport-Bursts (Fußball + Basketball gleichzeitig)
- 40 Wins in einem Tag = 40 Positionen in ~16h = ~2.5/Stunde
- Burst-Erkennung bei beachboy4: 2–5 Positionen in 60 Min = typischer Aktivitäts-Peak

---

## Was der Bot dafür braucht

### Basket-Erkennungs-Logik

```
Basket = Wenn Wallet X in Zeitfenster T (default: 60 Min)
         ≥ BASKET_MIN_SIGNALS (default: 3) Signale sendet
         → Alle Signale dieses Fensters als "Basket" markieren
         → Copy-Logik: Multi-Signal-Buffer BYPASSEN für diesen Basket
         → Stattdessen: BASKET_MAX_POSITIONS aus dem Fenster kopieren
         → Gesamt-Cap: BASKET_TOTAL_CAP_USD nicht überschreiten
```

**Warum Buffer-Bypass legitim ist:**
Der Multi-Signal-Buffer dient zur Qualitätssicherung durch Konsensus mehrerer Wallets.
Bei Basket-Wallets wie SeriouslySirius ist das Signal der Burst-Aktivität selbst
die Qualitätssicherung — nicht der Konsensus anderer Wallets.

---

## Neue Env-Flags

```env
# Basket-Strategie Konfiguration
BASKET_COPY_ENABLED=true           # Feature aktivieren/deaktivieren
BASKET_TIME_WINDOW_MINUTES=60      # Zeitfenster für Burst-Erkennung
BASKET_MIN_SIGNALS=3               # Mindest-Signale im Fenster um Basket zu triggern
BASKET_MAX_POSITIONS=3             # Max Positionen pro Basket zu kopieren (erste N)
BASKET_TOTAL_CAP_USD=15            # Max USD total pro Basket (verteilt auf N Positionen)
BASKET_WALLETS=0x16b2...,0xc2e7... # Wallets mit Basket-Copy aktiviert (Komma-getrennt)
                                   # Leer = alle Wallets mit BASKET_COPY_ENABLED
```

**Wichtig: BASKET_WALLETS als Whitelist**
Basket-Bypass ist stark — sollte nur für bekannte Basket-Wallets aktiviert sein.
Für Standard-Wallets bleibt Multi-Signal-Buffer aktiv.

---

## Code-Skizze: basket_detector.py

```python
"""
T-M21: Basket-Strategie Detection
Erkennt Burst-Aktivität eines Wallets und behandelt sie als koordinierten Basket.
"""
import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import List, Optional
import os

@dataclass
class BasketWindow:
    wallet: str
    signals: List = field(default_factory=list)
    opened_at: float = field(default_factory=time.time)
    basket_id: str = ""

    def is_active(self, window_minutes: int) -> bool:
        return (time.time() - self.opened_at) < (window_minutes * 60)

    def signal_count(self) -> int:
        return len(self.signals)


class BasketDetector:
    """
    Verwaltet Burst-Erkennung pro Wallet.
    Wird in WalletMonitor oder CopyTradingStrategy eingehängt.
    """

    def __init__(self):
        self.enabled = os.getenv("BASKET_COPY_ENABLED", "false").lower() == "true"
        self.window_minutes = int(os.getenv("BASKET_TIME_WINDOW_MINUTES", "60"))
        self.min_signals = int(os.getenv("BASKET_MIN_SIGNALS", "3"))
        self.max_positions = int(os.getenv("BASKET_MAX_POSITIONS", "3"))
        self.total_cap_usd = float(os.getenv("BASKET_TOTAL_CAP_USD", "15"))

        # Whitelist (leer = alle Wallets)
        basket_wallets_raw = os.getenv("BASKET_WALLETS", "")
        self.basket_wallets = {
            w.strip().lower()
            for w in basket_wallets_raw.split(",")
            if w.strip()
        }

        # State: wallet_address → aktives BasketWindow
        self._windows: dict[str, BasketWindow] = {}
        self._basket_counter = 0

    def _is_basket_wallet(self, wallet: str) -> bool:
        if not self.enabled:
            return False
        if not self.basket_wallets:
            return True  # Keine Whitelist = alle Wallets
        return wallet.lower() in self.basket_wallets

    def process_signal(self, signal) -> Optional["BasketDecision"]:
        """
        Hauptmethode. Wird für jedes eingehende TradeSignal aufgerufen.
        Gibt BasketDecision zurück: copy/skip/wait.
        """
        if not self._is_basket_wallet(signal.source_wallet):
            return None  # Normaler Pfad (kein Basket)

        wallet = signal.source_wallet.lower()
        now = time.time()

        # Altes Fenster schließen wenn abgelaufen
        if wallet in self._windows and not self._windows[wallet].is_active(self.window_minutes):
            closed = self._windows.pop(wallet)
            # Log: Basket closed mit X Signalen
            pass

        # Neues Fenster öffnen oder bestehendes erweitern
        if wallet not in self._windows:
            self._basket_counter += 1
            self._windows[wallet] = BasketWindow(
                wallet=wallet,
                basket_id=f"basket_{self._basket_counter}_{int(now)}"
            )

        window = self._windows[wallet]
        window.signals.append(signal)

        # Basket-Schwelle noch nicht erreicht → warten
        if window.signal_count() < self.min_signals:
            return BasketDecision(action="wait", basket_id=window.basket_id,
                                  position_in_basket=window.signal_count())

        # Basket aktiv — max_positions enforzen
        position_index = window.signal_count() - self.min_signals  # 0-basiert nach Threshold
        if position_index >= self.max_positions:
            return BasketDecision(action="skip", basket_id=window.basket_id,
                                  reason=f"basket_full (>{self.max_positions})")

        # Position ist im Basket und unter Cap
        size_per_position = self.total_cap_usd / self.max_positions
        return BasketDecision(
            action="copy",
            basket_id=window.basket_id,
            position_in_basket=position_index + 1,
            adjusted_size_usd=size_per_position,
            bypass_multi_signal_buffer=True
        )

    def get_active_baskets(self) -> List[BasketWindow]:
        return [w for w in self._windows.values() if w.is_active(self.window_minutes)]


@dataclass
class BasketDecision:
    action: str                          # "copy" | "skip" | "wait"
    basket_id: str = ""
    position_in_basket: int = 0
    adjusted_size_usd: float = 0.0
    bypass_multi_signal_buffer: bool = False
    reason: str = ""
```

---

## Integration in CopyTradingStrategy

```python
# In strategies/copy_trading.py — nach Signal-Empfang, vor Risk-Manager

from utils.basket_detector import BasketDetector, BasketDecision

class CopyTradingStrategy:
    def __init__(self, ...):
        ...
        self.basket_detector = BasketDetector()

    async def process_signal(self, signal: TradeSignal) -> Optional[CopyOrder]:
        # --- BASKET CHECK ---
        basket_decision = self.basket_detector.process_signal(signal)

        if basket_decision is not None:
            if basket_decision.action == "wait":
                # Signal im Basket aber Schwelle noch nicht erreicht — NICHT weiterleiten
                logger.info(f"[BASKET] {signal.source_wallet[:8]} Signal {basket_decision.position_in_basket}/{self.basket_detector.min_signals} — warte auf Basket-Threshold")
                return None

            elif basket_decision.action == "skip":
                logger.info(f"[BASKET] {basket_decision.basket_id} voll ({self.basket_detector.max_positions} Pos) — Signal übersprungen")
                return None

            elif basket_decision.action == "copy":
                # Basket-Signal: Buffer bypassen, Cap-Größe verwenden
                logger.info(f"[BASKET] {basket_decision.basket_id} Pos {basket_decision.position_in_basket}/{self.basket_detector.max_positions} → ${basket_decision.adjusted_size_usd:.2f}")
                order = CopyOrder(
                    signal=signal,
                    size_usdc=basket_decision.adjusted_size_usd,
                    dry_run=self.config.dry_run,
                    basket_id=basket_decision.basket_id,
                    bypass_multi_signal=True  # Risk-Manager respektiert dieses Flag
                )
                return order

        # --- NORMALER PFAD (kein Basket) ---
        # Bestehende Logik: Win-Rate-Decay, Multiplier, Multi-Signal-Buffer
        ...
```

---

## STOP-CHECKs für Server-CC

```bash
# 1. Feature aktiviert?
grep "BASKET_COPY_ENABLED\|BASKET_TIME_WINDOW\|BASKET_MIN_SIGNALS" /root/KongTradeBot/.env
# Erwartung: BASKET_COPY_ENABLED=true, BASKET_TIME_WINDOW_MINUTES=60, etc.

# 2. Basket-Wallet konfiguriert?
grep "BASKET_WALLETS" /root/KongTradeBot/.env
# Erwartung: 0x16b2... (SeriouslySirius) und/oder 0xc2e7... (beachboy4)

# 3. Logs: Basket-Erkennung sichtbar?
journalctl -u kongtrade-bot -n 50 --no-pager | grep -i "BASKET"
# Erwartung nach 1h: "[BASKET] 0x16b2... Signal 1/3 — warte auf Basket-Threshold"
# Nach Threshold: "[BASKET] basket_123 Pos 1/3 → $5.00"

# 4. Kein normaler Buffer für Basket-Wallets?
# Wenn "[BASKET] ... bypass_multi_signal=True" in Logs: korrekt
# Wenn "[MULTI_SIGNAL] waiting for confirmation" für Basket-Wallet: BUG

# 5. Cap eingehalten?
tail -100 /root/KongTradeBot/data/tax_archive.jsonl | python3 -c "
import json, sys, collections
baskets = collections.defaultdict(list)
for line in sys.stdin:
    t = json.loads(line.strip())
    if t.get('basket_id'):
        baskets[t['basket_id']].append(float(t.get('size_usdc', 0)))
for bid, sizes in baskets.items():
    total = sum(sizes)
    print(f'{bid}: {len(sizes)} Pos, Total \${total:.2f}')
"
# Erwartung: kein Basket > BASKET_TOTAL_CAP_USD
```

---

## Erwartetes Ergebnis

| Metrik | Ohne T-M21 | Mit T-M21 |
|--------|-----------|-----------|
| SeriouslySirius Signale pro Tag | 0 (Buffer feuert nie) | ~10 Basket-Signale |
| Kopierte Positionen pro Basket | 0 | 1–3 (BASKET_MAX_POSITIONS) |
| USD deployed pro Basket | $0 | max $15 (BASKET_TOTAL_CAP_USD) |
| Datenpunkte pro Woche | 0 | ~70 (SeriouslySirius 35/Tag × 2 = ~70 Basket-Signals) |
| Untersuchter Wert (SeriouslySirius) | $0 | Learning-Phase → T-D109 Review |

**SeriouslySirius spezifisch:**
- 35 Trades/Tag → ca. 8–12 Basket-Fenster/Tag (nicht alle 35 sind geclustert)
- Bei BASKET_MIN_SIGNALS=3 und BASKET_MAX_POSITIONS=3: 3 Kopier-Signale pro qualifiziertem Basket
- Bei $15 Cap + 3 Pos: $5/Position — gering aber Learning-relevant

**beachboy4 spezifisch (wenn reaktiviert):**
- Seltene Aktivierung (149 Trades gesamt in 5 Monaten)
- Bei Aktivierungstag: 10–40 Positionen in 1 Tag → Basket feuert sicher
- Wichtig: BASKET_MAX_POSITIONS=3 hält Exposure unter Kontrolle
  (beachboy4 setzt $500K–$1.3M pro Position → wir setzen $5 pro Position)

---

## Edge Cases

| Edge Case | Handling |
|-----------|---------|
| Wallet sendet 3 Signale in 60 Min, dann pause, dann 3 mehr | Zweites Fenster öffnet nach Ablauf des ersten |
| Basket-Signal zu teuer nach Risk-Manager | Risk-Manager lehnt ab trotz basket_id — wird als Skip geloggt |
| Bot-Restart während aktivem Basket | Fenster verloren — neues Basket öffnet bei nächstem Signal |
| Wallet nicht in BASKET_WALLETS | Normaler Multi-Signal-Buffer-Pfad, kein Basket |
| BASKET_MIN_SIGNALS=1 | Degenerate Case: jedes Signal ist sofort ein Basket → nicht empfohlen |
| Basket-Wallet hat auch Einzelsignale außerhalb Burst | Fenster muss ablaufen → dann normale Copy-Logik |

---

## Deployment-Reihenfolge

```
1. utils/basket_detector.py erstellen (neues File)
2. strategies/copy_trading.py: BasketDetector einbinden
3. core/execution_engine.py: basket_id ins Archive übernehmen
4. .env: BASKET_COPY_ENABLED + Parameter setzen
5. Bot-Restart
6. STOP-CHECKs ausführen
7. 48h Beobachtung → Review
```

**Commit-Messages:**
```
feat(basket): T-M21 BasketDetector — Burst-Erkennung für Multi-Position-Wallets
feat(copy): T-M21 Integration in CopyTradingStrategy — Buffer-Bypass für Basket-Wallets
```

---

## Wallet-Zuordnung (nach Analyse)

| Wallet | Basket-Typ | BASKET_MIN_SIGNALS | BASKET_MAX_POSITIONS | Multiplier |
|--------|-----------|-------------------|---------------------|------------|
| SeriouslySirius | Continuous Burst (35/Tag) | 3 | 3 | 0.3x (Learning) |
| beachboy4 | Sporadic Mega-Burst (seltener) | 5 | 3 | 0.3x (Vorsicht, HF-3) |
| bcda | Kein Basket (18/Tag verteilt) | — | — | 0.5x normal |

---

## ABSCHLUSSBERICHT (Server-CC nach Implementation)

1. **basket_detector.py:** Datei erstellt? Import in copy_trading.py funktioniert?
2. **Basket-Erkennung:** Nach 24h: Wie viele Baskets von SeriouslySirius erkannt?
3. **Buffer-Bypass:** Logs zeigen "bypass_multi_signal=True" für Basket-Wallets?
4. **Cap eingehalten:** Kein Basket > $15 in tax_archive.jsonl?
5. **beachboy4 Aktivierung:** Falls Aktivierung beobachtet → Basket-Logs zeigen 5+ Signale?

---

## Referenzen

| Quelle | Inhalt |
|--------|--------|
| 0xinsider SeriouslySirius | WR 50.3%, $3.6M, 6.339 Trades, "Directional" Typ |
| Merlin SeriouslySirius | 20 gleichzeitige offene Positionen, $192.6M Volume |
| cointrenches beachboy4 | 40 consecutive wins in einem Tag, Multi-Sport-Bursts |
| WALLET_SCOUT_BRIEFING.md v2.0 Teil 17.3 | SINGLE_SIGNAL_CATEGORIES als Alternative |
| analyses/re_audit_rejected_wallets_2026-04-20.md | SeriouslySirius WATCHING ($3.6M, T-M21 req.) |
