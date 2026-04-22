"""
Healthchecks.io Heartbeat (Phase 2.6)

Pings HEALTHCHECKS_PING_URL every 30s via httpx.
URL loaded from .env — never hardcoded in source.

On 3 consecutive failures: logs warning, bot continues running.
Heartbeat is non-critical: any exception is swallowed so this task
never crashes the main bot event loop.
"""
import os
import asyncio
from utils.logger import get_logger

logger = get_logger("heartbeat")

_MAX_CONSECUTIVE_FAIL = 3


async def run(interval_s: int = 30) -> None:
    """
    Async task — runs forever inside the main event loop.
    Designed to be launched via asyncio.create_task(heartbeat.run()).
    """
    url = os.getenv("HEALTHCHECKS_PING_URL", "").strip()
    if not url:
        logger.warning("[Heartbeat] HEALTHCHECKS_PING_URL not set — heartbeat disabled")
        return

    logger.info(f"[Heartbeat] Started (interval={interval_s}s url={url[:30]}...)")
    consecutive_failures = 0

    while True:
        await asyncio.sleep(interval_s)
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    consecutive_failures = 0
                    logger.debug("[Heartbeat] Ping OK")
                else:
                    raise RuntimeError(f"HTTP {resp.status_code}")
        except Exception as exc:
            consecutive_failures += 1
            if consecutive_failures >= _MAX_CONSECUTIVE_FAIL:
                logger.warning(
                    f"[Heartbeat] {consecutive_failures} consecutive ping failures: {exc}. "
                    "Healthchecks.io may trigger the dead-man-switch."
                )
            else:
                logger.debug(f"[Heartbeat] Ping failed ({consecutive_failures}): {exc}")
