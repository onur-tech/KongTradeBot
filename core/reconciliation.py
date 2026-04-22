"""
Reconciliation-Loop (Phase 2.1)

Compares bot's in-memory positions against actual Polymarket holdings every 60s.
Detects phantom positions (in memory but not on-chain) and logs a Telegram alert.
Runs as an async task inside the main bot event loop.

Safe to run in dry-run mode (read-only, no trading action taken).
"""
import asyncio
import aiohttp
from datetime import datetime, timezone
from typing import Callable, Coroutine, Optional, Any

from utils.logger import get_logger

logger = get_logger("reconciliation")

_POSITIONS_URL = "https://data-api.polymarket.com/positions"
_FETCH_TIMEOUT = 15
_DEFAULT_INTERVAL = 60


class ReconciliationLoop:
    """
    Runs reconciliation every interval_s seconds.
    Injects via dependency: engine (has open_positions), config (has polymarket_address).
    telegram_send is the async send() coroutine from telegram_bot.
    """

    def __init__(self, engine, config, telegram_send: Optional[Callable] = None):
        self._engine = engine
        self._config = config
        self._send = telegram_send
        self._phantom_total = 0
        self._last_check_ts: Optional[float] = None
        self._last_check_ok = True

    # ── Public API ────────────────────────────────────────────────────────────

    async def run(self, interval_s: int = _DEFAULT_INTERVAL):
        """Main loop — runs forever inside the bot event loop."""
        logger.info(f"[Reconcile] Loop started (interval={interval_s}s)")
        while True:
            await asyncio.sleep(interval_s)
            try:
                await self._reconcile()
            except Exception as exc:
                logger.warning(f"[Reconcile] Unexpected error: {exc}")

    def status(self) -> dict:
        return {
            "last_check_ts": self._last_check_ts,
            "last_check_ok": self._last_check_ok,
            "phantom_total_session": self._phantom_total,
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _reconcile(self):
        address = getattr(self._config, "polymarket_address", "") or ""
        if not address:
            logger.debug("[Reconcile] No polymarket_address — skipping")
            return

        self._last_check_ts = datetime.now(timezone.utc).timestamp()

        # Fetch live holdings from Polymarket Data-API
        api_tokens = await self._fetch_api_tokens(address)
        if api_tokens is None:
            # Network failure — don't cry wolf, just log
            logger.debug("[Reconcile] API fetch failed — skipping this cycle")
            return

        # Compare with in-memory positions
        bot_positions = dict(getattr(self._engine, "open_positions", {}))

        phantoms = []
        for order_id, pos in bot_positions.items():
            token_id = getattr(pos, "token_id", None) or ""
            # Synthetic recovery positions (RECOVERED_...) are expected to have
            # token_ids that may not always match exactly — skip them
            if order_id.startswith("RECOVERED_"):
                continue
            if token_id and token_id not in api_tokens:
                phantoms.append((order_id, pos))

        self._last_check_ok = len(phantoms) == 0

        if phantoms:
            self._phantom_total += len(phantoms)
            self._alert_phantoms(phantoms)
        else:
            logger.debug(
                f"[Reconcile] OK — {len(bot_positions)} bot positions, "
                f"{len(api_tokens)} API tokens matched"
            )

    async def _fetch_api_tokens(self, address: str) -> Optional[set]:
        """Returns set of token_ids with holdings > 0.001, or None on failure."""
        url = f"{_POSITIONS_URL}?user={address}&sizeThreshold=0.001&limit=500"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=_FETCH_TIMEOUT)
                ) as resp:
                    if resp.status != 200:
                        logger.debug(f"[Reconcile] Data-API returned HTTP {resp.status}")
                        return None
                    data = await resp.json()
        except asyncio.TimeoutError:
            logger.debug("[Reconcile] Data-API timeout")
            return None
        except Exception as exc:
            logger.debug(f"[Reconcile] Data-API fetch error: {exc}")
            return None

        items = data if isinstance(data, list) else (data.get("data", []) if isinstance(data, dict) else [])
        return {
            str(p.get("asset") or p.get("tokenId") or "")
            for p in items
            if float(p.get("size") or p.get("shares") or 0) > 0.001
        }

    def _alert_phantoms(self, phantoms: list):
        names = [
            f"  • {oid[:12]}: {getattr(p, 'outcome', '?')} ${float(getattr(p, 'size_usdc', 0)):.2f}"
            for oid, p in phantoms
        ]
        msg = (
            f"⚠️ <b>Reconciliation: {len(phantoms)} Phantom-Position(en)</b>\n"
            f"Im Bot-Memory, NICHT auf Polymarket:\n"
            + "\n".join(names)
            + f"\nSession total: {self._phantom_total}"
        )
        logger.warning(f"[Reconcile] {len(phantoms)} phantom(s): {[o for o, _ in phantoms]}")
        if self._send:
            try:
                asyncio.get_running_loop().create_task(self._send(msg))
            except RuntimeError:
                pass  # no running loop in test context
