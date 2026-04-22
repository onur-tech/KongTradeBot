"""
Quarter-Kelly Position Sizer (Phase 2.4)

Formula:  f* = (p·b - q) / b
  p    = KELLY_ASSUMED_WIN_PROB (default 0.55 — conservative copy-trade edge)
  b    = net odds = (1 - price) / price
  q    = 1 - p
  applied_kelly = KELLY_FRACTION (default 0.25) × f*

Hard caps (all configurable via .env):
  KELLY_MAX_POS_PCT    = 2%  — max single position as % of bankroll
  KELLY_MAX_MARKET_PCT = 10% — max total exposure per market

If full-Kelly is negative (no edge at this price), falls back to KELLY_FLOOR_PCT
of bankroll (non-zero floor keeps copy-trade discipline intact).

Returns (size_usdc, kelly_fraction_applied, cap_hit_flag).
"""
import os
from typing import List, Literal, Optional, Tuple

from utils.logger import get_logger

logger = get_logger("kelly_sizer")

_sim_log: List[str] = []

KELLY_FRACTION      = float(os.getenv("KELLY_FRACTION",         "0.25"))
ASSUMED_WIN_PROB    = float(os.getenv("KELLY_ASSUMED_WIN_PROB",  "0.55"))
MAX_POS_PCT         = float(os.getenv("KELLY_MAX_POS_PCT",       "0.02"))
MAX_MARKET_PCT      = float(os.getenv("KELLY_MAX_MARKET_PCT",    "0.10"))
FLOOR_PCT           = float(os.getenv("KELLY_FLOOR_PCT",         "0.002"))  # 0.2% floor


def kelly_size(
    price: float,
    bankroll: float,
    *,
    market_already_invested: float = 0.0,
    kelly_fraction: float = KELLY_FRACTION,
    max_pos_pct: float = MAX_POS_PCT,
    max_market_pct: float = MAX_MARKET_PCT,
    win_prob: float = ASSUMED_WIN_PROB,
    floor_pct: float = FLOOR_PCT,
    mode: Literal["live", "simulation"] = "live",
) -> Tuple[float, float, Optional[str]]:
    """
    Compute Quarter-Kelly position size.

    Returns (size_usdc, kelly_fraction_applied, cap_hit_flag).
    cap_hit_flag: None | 'pos_cap' | 'market_cap' | 'negative_kelly'
    """
    if bankroll <= 0:
        return 0.0, 0.0, None
    if not (0 < price < 1):
        return 0.0, 0.0, None

    # Net odds
    b = (1.0 - price) / price
    q = 1.0 - win_prob

    # Full Kelly fraction
    full_kelly = (win_prob * b - q) / b

    cap_flag: Optional[str] = None

    if full_kelly <= 0:
        # Negative edge at this price — use floor
        size = bankroll * floor_pct
        applied_fraction = 0.0
        cap_flag = "negative_kelly"
        logger.debug(
            f"[Kelly] Negative Kelly ({full_kelly:.4f}) at price={price:.3f} "
            f"win_prob={win_prob:.2f} — using floor ${size:.2f}"
        )
    else:
        applied_fraction = kelly_fraction * full_kelly
        size = applied_fraction * bankroll

    # Hard cap: per-position limit
    max_pos_size = bankroll * max_pos_pct
    if size > max_pos_size:
        size = max_pos_size
        cap_flag = "pos_cap"

    # Hard cap: per-market limit (remaining capacity)
    max_market_remaining = max(0.0, bankroll * max_market_pct - market_already_invested)
    if size > max_market_remaining:
        size = max_market_remaining
        cap_flag = "market_cap"

    size = round(size, 2)

    prefix = "[SIM Kelly]" if mode == "simulation" else "[Kelly]"
    logger.debug(
        f"{prefix} price={price:.3f} b={b:.3f} full_kelly={full_kelly:.4f} "
        f"applied_frac={applied_fraction:.4f} → ${size:.2f} cap={cap_flag}"
    )
    if mode == "simulation":
        _sim_log.append(
            f"{prefix} price={price:.3f} → ${size:.2f} cap={cap_flag}"
        )

    return size, round(applied_fraction, 6), cap_flag
