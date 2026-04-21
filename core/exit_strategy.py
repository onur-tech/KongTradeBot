"""
Exit Strategy — KongTradeBot
=============================
Erkennt wenn Whale-Wallets ihre Positionen reduzieren oder flippen.
Löst entsprechend Gradual/Full/Flip-Exit aus.

ExitType:
  NONE    — kein Exit-Signal
  GRADUAL — Whale reduziert um 20-50% → halbe Position schließen
  FULL    — Whale reduziert um >50% oder schließt → volle Position schließen
  FLIP    — Whale flippt auf Gegenseite → Position schließen + ggf. reverse
"""

import json
import logging
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger("polymarket_bot.exit_strategy")


class ExitType(Enum):
    NONE = "NONE"
    GRADUAL = "GRADUAL"
    FULL = "FULL"
    FLIP = "FLIP"


@dataclass
class ExitSignal:
    market_id: str
    exit_type: ExitType
    reason: str
    wallet: str
    old_size: float
    new_size: float
    reduction_pct: float       # 0.0 – 1.0
    flip_direction: str = ""   # "YES" / "NO" wenn FLIP
    confidence: float = 0.0    # 0.0 – 1.0


class ExitStrategy:
    """
    Verarbeitet Whale-Aktivitäten und erzeugt Exit-Signale
    für unsere offenen Positionen.
    """

    # Schwellenwerte
    GRADUAL_THRESHOLD = 0.20   # ab 20% Reduktion → GRADUAL
    FULL_THRESHOLD = 0.50      # ab 50% Reduktion → FULL
    CLOSE_THRESHOLD = 0.90     # ab 90% Reduktion → wie FULL behandeln

    def __init__(self, engine=None):
        self.engine = engine   # Trading-Engine Referenz für open_positions

    def process_whale_activity(
            self,
            market_id: str,
            wallet: str,
            old_outcome: str,
            old_size: float,
            new_outcome: Optional[str],
            new_size: float) -> ExitSignal:
        """
        Analysiert Änderung einer Whale-Position und gibt Exit-Signal zurück.

        Args:
            market_id:   Condition-ID des Marktes
            wallet:      Wallet-Adresse des Whales
            old_outcome: Vorherige Seite (YES/NO)
            old_size:    Vorherige Größe in USDC
            new_outcome: Neue Seite (YES/NO) oder None wenn komplett geschlossen
            new_size:    Neue Größe (0.0 wenn geschlossen)
        """
        our_pos = self._find_our_position(market_id)
        if our_pos is None:
            return ExitSignal(
                market_id=market_id,
                exit_type=ExitType.NONE,
                reason="No open position for this market",
                wallet=wallet,
                old_size=old_size,
                new_size=new_size,
                reduction_pct=0.0,
            )

        # Flip: Whale wechselt Seite
        if new_outcome and new_outcome != old_outcome and new_size > 0:
            flip_dir = new_outcome
            logger.warning(
                f"[ExitStrategy] 🔄 FLIP detected: {wallet[:10]} "
                f"flipped {old_outcome}→{new_outcome} on {market_id[:16]}")
            return ExitSignal(
                market_id=market_id,
                exit_type=ExitType.FLIP,
                reason=f"Whale flipped {old_outcome}→{new_outcome}",
                wallet=wallet,
                old_size=old_size,
                new_size=new_size,
                reduction_pct=1.0,
                flip_direction=flip_dir,
                confidence=0.85,
            )

        # Reduktion auf gleicher Seite
        if old_size <= 0:
            reduction_pct = 0.0
        else:
            reduction_pct = max(0.0, (old_size - new_size) / old_size)

        if reduction_pct >= self.FULL_THRESHOLD:
            exit_type = ExitType.FULL
            reason = (
                f"Whale reduced {reduction_pct:.0%} "
                f"({old_size:.0f}→{new_size:.0f} USDC)"
            )
            confidence = min(1.0, reduction_pct)
            logger.warning(
                f"[ExitStrategy] 🚨 FULL EXIT: {wallet[:10]} "
                f"reduced {reduction_pct:.0%} on {market_id[:16]}")
        elif reduction_pct >= self.GRADUAL_THRESHOLD:
            exit_type = ExitType.GRADUAL
            reason = (
                f"Whale reduced {reduction_pct:.0%} "
                f"({old_size:.0f}→{new_size:.0f} USDC)"
            )
            confidence = reduction_pct / self.FULL_THRESHOLD * 0.7
            logger.info(
                f"[ExitStrategy] ⚠️ GRADUAL EXIT: {wallet[:10]} "
                f"reduced {reduction_pct:.0%} on {market_id[:16]}")
        else:
            exit_type = ExitType.NONE
            reason = f"Minor reduction {reduction_pct:.0%} — no action"
            confidence = 0.0

        return ExitSignal(
            market_id=market_id,
            exit_type=exit_type,
            reason=reason,
            wallet=wallet,
            old_size=old_size,
            new_size=new_size,
            reduction_pct=reduction_pct,
            confidence=confidence,
        )

    def execute_exit(self, signal: ExitSignal) -> dict:
        """
        Führt Exit basierend auf Signal aus.
        Gibt Aktions-Dict zurück (für Logging / Telegram).

        Ohne echte Engine: gibt nur die geplante Aktion zurück.
        """
        if signal.exit_type == ExitType.NONE:
            return {"action": "NONE", "signal": signal}

        our_pos = self._find_our_position(signal.market_id)
        if our_pos is None:
            return {"action": "SKIP", "reason": "No open position found"}

        if signal.exit_type == ExitType.GRADUAL:
            close_fraction = 0.5
            action_label = "CLOSE_HALF"
        elif signal.exit_type in (ExitType.FULL, ExitType.FLIP):
            close_fraction = 1.0
            action_label = "CLOSE_ALL"
        else:
            return {"action": "NONE"}

        invested = getattr(our_pos, "size_usdc", None) or our_pos.get("size_usdc", 0) if isinstance(our_pos, dict) else 0
        close_usdc = round(invested * close_fraction, 2)

        logger.info(
            f"[ExitStrategy] 📤 EXECUTE {action_label}: "
            f"market={signal.market_id[:16]} | "
            f"close=${close_usdc:.2f} ({close_fraction:.0%}) | "
            f"reason={signal.reason}")

        return {
            "action": action_label,
            "market_id": signal.market_id,
            "close_fraction": close_fraction,
            "close_usdc": close_usdc,
            "exit_type": signal.exit_type.value,
            "reason": signal.reason,
            "wallet": signal.wallet,
            "confidence": signal.confidence,
            "flip_direction": signal.flip_direction,
        }

    def _find_our_position(self, market_id: str):
        """Sucht unsere offene Position für diesen Markt."""
        if self.engine is None:
            return None
        # engine.open_positions ist ein dict: token_id → Position
        for pos in self.engine.open_positions.values():
            mid = getattr(pos, "market_id", None) or getattr(pos, "condition_id", None)
            if mid == market_id:
                return pos
        return None


def check_weather_exit_signals(shadow_data: dict) -> list:
    """
    Prüft laufende Weather-Positionen auf 60% Edge-Capture.
    Kein automatischer Verkauf — gibt Alert-Liste zurück.

    edge_captured = (current_price - entry_price) / (1.0 - entry_price)
    → 60% des maximal möglichen Gewinns bereits realisierbar.

    Aufrufen alle 15 Minuten aus weather_exit_loop() in main.py.
    """
    GAMMA_API = "https://gamma-api.polymarket.com"
    EDGE_CAPTURE_THRESHOLD = 0.60

    alerts = []
    positions = shadow_data.get("positions", [])
    weather_positions = [
        p for p in positions
        if p.get("strategy") in ("WEATHER", "BUCKET_ARB", "COMBINED")
        and p.get("status") == "OPEN"
    ]

    if not weather_positions:
        return []

    for pos in weather_positions:
        condition_id = pos.get("market_id", "")
        entry_price = float(pos.get("entry_price", 0))
        outcome = pos.get("outcome", "YES")
        city = pos.get("city") or pos.get("question", "")[:20]

        if entry_price <= 0 or entry_price >= 0.99:
            continue

        # Aktuellen Preis von Gamma API holen
        try:
            url = f"{GAMMA_API}/markets?conditionId={condition_id}"
            req = urllib.request.Request(
                url, headers={"User-Agent": "KongTradeBot/1.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                mkt_data = json.loads(r.read())
            mkt = mkt_data[0] if isinstance(mkt_data, list) and mkt_data else {}
            prices = mkt.get("outcomePrices", [])
            outcomes = mkt.get("outcomes", ["Yes", "No"])
            current_price = None
            for i, oc in enumerate(outcomes):
                if oc.upper() == outcome.upper() and i < len(prices):
                    current_price = float(prices[i])
                    break
        except Exception as e:
            logger.debug(f"[ExitStrategy] Preis-Fetch {condition_id[:14]}: {e}")
            continue

        if current_price is None or current_price <= entry_price:
            continue

        # edge_captured: wie viel % des max. möglichen Gewinns ist schon drin?
        full_potential = 1.0 - entry_price
        edge_captured = (current_price - entry_price) / full_potential

        if edge_captured >= EDGE_CAPTURE_THRESHOLD:
            alert = {
                "city": city,
                "outcome": outcome,
                "entry_price": round(entry_price, 3),
                "current_price": round(current_price, 3),
                "edge_captured_pct": round(edge_captured, 3),
                "condition_id": condition_id,
                "invested_usdc": pos.get("invested_usdc", 0),
            }
            alerts.append(alert)
            logger.info(
                f"[ExitStrategy] 💰 60% EDGE CAPTURED: {city} {outcome} "
                f"entry={entry_price:.3f} → now={current_price:.3f} "
                f"captured={edge_captured:.0%} — Telegram-Alert empfohlen")

    return alerts
