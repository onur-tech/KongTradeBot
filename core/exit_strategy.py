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

import logging
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
