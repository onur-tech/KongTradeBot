"""
Thesis-Invalidation Guard + Hard-Stop (Phase 2.7)

Copy-trade thesis: "Whale X is right → we copy."
Thesis is invalidated by two events:

  1. Whale EXIT signal  — the whale who triggered us SELLS their position.
     on_whale_exit(source_wallet, market_id) → returns list of invalidated order_ids.

  2. Hard-Stop price drop — price falls > THESIS_HARD_STOP_PCT from our entry.
     check_hard_stop(order_id, entry_price, current_price) → ThesisViolation | None.

Violations are stored in memory. Caller (main.py exit_loop) should poll
get_violation() and act on returned order_ids.

Design decisions:
  - Module is stateless between restarts (positions re-register on startup via
    restore flow). After restart, hard-stop monitoring resumes from loaded
    positions; whale-exit invalidation covers new signals only.
  - THESIS_EXIT_ON_WHALE_EXIT=false disables whale-exit invalidation (still
    hard-stop active).
"""
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from utils.logger import get_logger

logger = get_logger("thesis_guard")

HARD_STOP_PCT         = float(os.getenv("THESIS_HARD_STOP_PCT",         "0.40"))
EXIT_ON_WHALE_EXIT    = os.getenv("THESIS_EXIT_ON_WHALE_EXIT", "true").lower() == "true"


@dataclass
class ThesisViolation:
    order_id:     str
    reason:       str
    trigger_price: float
    triggered_at: datetime


class ThesisGuard:
    """
    Tracks open positions and their thesis conditions.
    Thread-safe only within a single asyncio event loop (no cross-thread sharing).
    """

    def __init__(self):
        # order_id → ThesisViolation (once set, stays until clear_position)
        self._violations: Dict[str, ThesisViolation] = {}
        # source_wallet → [order_ids] for whale-exit cross-reference
        self._wallet_orders: Dict[str, List[str]] = {}
        # order_id → entry_price for hard-stop calculation
        self._entry_prices: Dict[str, float] = {}

    # ── Registration ─────────────────────────────────────────────────────────

    def register_position(
        self,
        order_id: str,
        source_wallet: str,
        entry_price: float,
    ):
        """Call after trade entry so the guard can monitor this position."""
        self._entry_prices[order_id] = entry_price
        if source_wallet:
            self._wallet_orders.setdefault(source_wallet, []).append(order_id)
        logger.debug(
            f"[ThesisGuard] registered {order_id[:12]} "
            f"entry={entry_price:.4f} wallet={source_wallet[:12] if source_wallet else '-'}"
        )

    # ── Thesis invalidation events ────────────────────────────────────────────

    def on_whale_exit(self, source_wallet: str, _market_id: str = "") -> List[str]:
        """
        Called when a whale sells a position.
        Returns list of our order_ids whose thesis is now invalidated.
        """
        if not EXIT_ON_WHALE_EXIT:
            return []

        affected = list(self._wallet_orders.get(source_wallet, []))
        for oid in affected:
            if oid not in self._violations:
                v = ThesisViolation(
                    order_id=oid,
                    reason=f"Whale {source_wallet[:12]} exited — thesis invalidated",
                    trigger_price=0.0,
                    triggered_at=datetime.now(timezone.utc),
                )
                self._violations[oid] = v

        if affected:
            logger.warning(
                f"[ThesisGuard] Whale exit: wallet={source_wallet[:12]} "
                f"→ {len(affected)} position(s) invalidated: {[o[:12] for o in affected]}"
            )
        return affected

    def check_hard_stop(
        self,
        order_id: str,
        entry_price: float,
        current_price: float,
    ) -> Optional[ThesisViolation]:
        """
        Check if hard-stop threshold is breached.
        Returns ThesisViolation if triggered (first time only), else None.
        """
        if order_id in self._violations:
            return None  # already invalidated — don't double-fire

        if entry_price <= 0 or current_price < 0:
            return None

        loss_pct = (entry_price - current_price) / entry_price
        if loss_pct < HARD_STOP_PCT:
            return None

        v = ThesisViolation(
            order_id=order_id,
            reason=(
                f"Hard-stop: price dropped {loss_pct:.1%} from entry "
                f"{entry_price:.4f} → {current_price:.4f} "
                f"(threshold {HARD_STOP_PCT:.0%})"
            ),
            trigger_price=current_price,
            triggered_at=datetime.now(timezone.utc),
        )
        self._violations[order_id] = v
        logger.warning(
            f"[ThesisGuard] Hard-stop: {order_id[:12]} "
            f"entry={entry_price:.4f} current={current_price:.4f} "
            f"loss={loss_pct:.1%}"
        )
        return v

    # ── Query / cleanup ───────────────────────────────────────────────────────

    def get_violation(self, order_id: str) -> Optional[ThesisViolation]:
        return self._violations.get(order_id)

    def all_violations(self) -> Dict[str, ThesisViolation]:
        return dict(self._violations)

    def clear_position(self, order_id: str):
        """Call when position is closed (exit executed)."""
        self._violations.pop(order_id, None)
        self._entry_prices.pop(order_id, None)
        for orders in self._wallet_orders.values():
            try:
                orders.remove(order_id)
            except ValueError:
                pass
        logger.debug(f"[ThesisGuard] cleared {order_id[:12]}")
