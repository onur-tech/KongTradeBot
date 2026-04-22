"""
Slippage Pre-Check (Phase 2.3)

Before order execution: fetches CLOB orderbook, computes VWAP for the intended
order size, calculates slippage vs signal price.

Thresholds (configurable via .env):
  SLIPPAGE_WARN_BPS   default 300 — log warning, allow trade
  SLIPPAGE_REJECT_BPS default 500 — reject trade, log + Telegram

Returns (allowed: bool, slippage_bps: float, reason: str).
On orderbook fetch failure: allows trade (fail-open), logs debug.
"""
import os
import asyncio
import aiohttp
from typing import List, Literal, Optional, Tuple

from utils.logger import get_logger

logger = get_logger("slippage_check")

_sim_log: List[str] = []

WARN_BPS   = float(os.getenv("SLIPPAGE_WARN_BPS",   "300"))
REJECT_BPS = float(os.getenv("SLIPPAGE_REJECT_BPS", "500"))
_BOOK_URL  = "https://clob.polymarket.com/book"
_TIMEOUT   = 8.0


async def _fetch_orderbook(token_id: str) -> Optional[dict]:
    """Fetches CLOB orderbook for token_id. Returns dict or None on failure."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{_BOOK_URL}?token_id={token_id}",
                timeout=aiohttp.ClientTimeout(total=_TIMEOUT),
            ) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()
    except Exception as exc:
        logger.debug(f"[SlippageCheck] orderbook fetch failed: {exc}")
        return None


def _compute_vwap(book: dict, side: str, size_usdc: float) -> Optional[float]:
    """
    Walk the orderbook for 'side' (BUY → use asks, SELL → use bids).
    Returns VWAP in price per share, or None if orderbook is empty/thin.
    """
    levels_key = "asks" if side.upper() == "BUY" else "bids"
    levels = book.get(levels_key, [])
    if not levels:
        return None

    # Sort: asks ascending (cheapest first), bids descending (best bid first)
    reverse = side.upper() == "SELL"
    try:
        sorted_levels = sorted(levels, key=lambda x: float(x.get("price", 0)), reverse=reverse)
    except Exception:
        return None

    remaining_usdc = size_usdc
    total_cost = 0.0
    total_shares = 0.0

    for level in sorted_levels:
        try:
            level_price = float(level.get("price", 0))
            level_size_shares = float(level.get("size", 0))
        except (TypeError, ValueError):
            continue
        if level_price <= 0 or level_size_shares <= 0:
            continue

        level_usdc = level_size_shares * level_price
        take_usdc = min(remaining_usdc, level_usdc)
        take_shares = take_usdc / level_price

        total_cost += take_usdc
        total_shares += take_shares
        remaining_usdc -= take_usdc

        if remaining_usdc <= 1e-9:
            break

    if total_shares <= 0:
        return None
    return total_cost / total_shares


async def check_slippage(
    token_id: str,
    signal_price: float,
    size_usdc: float,
    side: str = "BUY",
    mode: Literal["live", "simulation"] = "live",
) -> Tuple[bool, float, str]:
    """
    Main entry point.
    Returns (allowed, slippage_bps, reason).
    Fail-open: if orderbook unavailable, returns (True, 0.0, 'skipped').
    In simulation mode: skips HTTP fetch, returns (True, 0.0, 'sim mode').
    """
    if mode == "simulation":
        _sim_log.append(f"[SIM SlippageCheck] token={token_id[:16]} price={signal_price} size={size_usdc}")
        return True, 0.0, "sim mode"

    if not token_id or signal_price <= 0 or size_usdc <= 0:
        return True, 0.0, "check skipped (missing params)"

    book = await _fetch_orderbook(token_id)
    if book is None:
        return True, 0.0, "check skipped (orderbook unavailable)"

    vwap = _compute_vwap(book, side, size_usdc)
    if vwap is None:
        return True, 0.0, "check skipped (orderbook too thin)"

    slippage_bps = ((vwap - signal_price) / signal_price) * 10_000

    if slippage_bps > REJECT_BPS:
        reason = f"slippage {slippage_bps:.0f} bps > reject threshold {REJECT_BPS:.0f} bps"
        logger.warning(f"[SlippageCheck] REJECT: {reason} (token={token_id[:16]})")
        return False, slippage_bps, reason

    if slippage_bps > WARN_BPS:
        reason = f"slippage {slippage_bps:.0f} bps > warn threshold {WARN_BPS:.0f} bps"
        logger.warning(f"[SlippageCheck] WARN: {reason}")
        return True, slippage_bps, reason

    return True, slippage_bps, f"OK ({slippage_bps:.0f} bps)"
