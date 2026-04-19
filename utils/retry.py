"""
utils/retry.py — Exponential Backoff für RPC/Network Calls

Quelle: Pattern aus TradeSEB/polymarket-copytrading-bot.
RPC-Calls scheitern oft temporär (Rate-Limit, Timeout, Network-Glitch).
Retry 2s→4s→8s löst >90% der transienten Fehler.
"""

import asyncio
import logging
import time
from typing import Callable, Awaitable, TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T")

# Strings die auf retrybare Fehler hinweisen
_RETRYABLE_SUBSTRINGS = (
    "network",
    "timeout",
    "ECONNREFUSED",
    "ETIMEDOUT",
    "ECONNRESET",
    "rpc",
    "rate limit",
    "rate_limit",
    "503",
    "502",
    "504",
    "connection",
    "socket",
    "ankr",
    "too many requests",
    "try again",
)


async def retry_with_backoff(
    fn: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    initial_delay: float = 2.0,
    retryable_substrings: tuple = _RETRYABLE_SUBSTRINGS,
) -> T:
    """
    Async retry mit Exponential Backoff.

    Versuche: 1 → 2s warten → 2 → 4s warten → 3 → raise

    Nur retrybare Fehler (Netzwerk, Timeout, RPC) werden wiederholt.
    Andere Fehler werden sofort weitergegeben.

    Verwendung:
        result = await retry_with_backoff(lambda: rpc_call())
        result = await retry_with_backoff(
            lambda: fetch_data(),
            max_retries=5,
            initial_delay=1.0
        )
    """
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return await fn()
        except Exception as e:
            last_error = e
            msg = str(e).lower()
            is_retryable = any(s.lower() in msg for s in retryable_substrings)
            if not is_retryable or attempt == max_retries:
                raise
            delay = initial_delay * (2 ** (attempt - 1))
            logger.warning(
                f"[retry] Versuch {attempt}/{max_retries} fehlgeschlagen: "
                f"{str(e)[:80]} — Retry in {delay:.0f}s"
            )
            await asyncio.sleep(delay)
    raise last_error  # unreachable, aber mypy-freundlich


def retry_sync(
    fn: Callable[[], T],
    max_retries: int = 3,
    initial_delay: float = 2.0,
    retryable_substrings: tuple = _RETRYABLE_SUBSTRINGS,
) -> T:
    """
    Sync version für non-async Calls (z.B. Web3/RPC in balance_fetcher).

    Versuche: 1 → 2s warten → 2 → 4s warten → 3 → raise
    """
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except Exception as e:
            last_error = e
            msg = str(e).lower()
            is_retryable = any(s.lower() in msg for s in retryable_substrings)
            if not is_retryable or attempt == max_retries:
                raise
            delay = initial_delay * (2 ** (attempt - 1))
            logger.warning(
                f"[retry_sync] Versuch {attempt}/{max_retries}: "
                f"{str(e)[:80]} — {delay:.0f}s"
            )
            time.sleep(delay)
    raise last_error
