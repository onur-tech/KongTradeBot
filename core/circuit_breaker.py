"""
Circuit-Breaker 3-Level (Phase 2.5)

Monitors daily loss as a percentage of bankroll and triggers escalating responses:

  Level 1 (WARN)  — CB_LEVEL1_PCT (default 5%)
    → Telegram warning, trading continues.

  Level 2 (PAUSE) — CB_LEVEL2_PCT (default 10%)
    → New entries blocked for CB_LEVEL2_PAUSE_S seconds (default 1h).
    → Auto-unblocks when pause expires; resets to Level 0.

  Level 3 (HALT)  — CB_LEVEL3_PCT (default 15%)
    → All new entries blocked permanently until manual reset.
    → Telegram critical alert.

Persistent state in data/circuit_breaker.json survives bot restarts.
Level 1 and 2 reset automatically at day rollover (daily_reset()).
Level 3 requires explicit manual reset (reset()).
"""
import os
import json
import asyncio
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Callable, Coroutine, Optional

from utils.logger import get_logger

logger = get_logger("circuit_breaker")

L1_PCT         = float(os.getenv("CB_LEVEL1_PCT",       "0.05"))   # 5%
L2_PCT         = float(os.getenv("CB_LEVEL2_PCT",       "0.10"))   # 10%
L3_PCT         = float(os.getenv("CB_LEVEL3_PCT",       "0.15"))   # 15%
L2_PAUSE_S     = int(os.getenv("CB_LEVEL2_PAUSE_S",   "3600"))    # 1 hour
_BASE          = Path(__file__).parent.parent
CB_STATE_PATH  = _BASE / "data" / "circuit_breaker.json"


@dataclass
class CBState:
    level:        int = 0
    triggered_at: str = ""
    reason:       str = ""
    pause_until:  str = ""   # ISO — only used at level 2


class CircuitBreaker:
    """
    Call update() after each trade result or on a periodic timer.
    Call is_blocked() before submitting new entries.
    """

    def __init__(self, telegram_send: Optional[Callable] = None):
        self._state = CBState()
        self._send = telegram_send
        self._load()

    # ── Public API ────────────────────────────────────────────────────────────

    def is_blocked(self) -> bool:
        """Returns True if new entries should be blocked."""
        s = self._state
        if s.level == 3:
            return True
        if s.level == 2 and s.pause_until:
            try:
                expiry = datetime.fromisoformat(s.pause_until)
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) < expiry:
                    return True
                # Pause expired — auto-demote to level 0
                logger.info("[CB] Level-2 pause expired — auto-reset to 0")
                self._state = CBState()
                self._save()
            except Exception:
                pass
        return False

    async def update(self, daily_loss_usd: float, bankroll: float):
        """
        Evaluate current loss against thresholds and escalate if necessary.
        Idempotent — won't re-send alerts for the same level.
        """
        if bankroll <= 0:
            return

        loss_pct = daily_loss_usd / bankroll
        now = datetime.now(timezone.utc).isoformat()
        current = self._state.level

        if loss_pct >= L3_PCT and current < 3:
            await self._set_level(
                3, now,
                reason=f"Level-3 HALT: {loss_pct:.1%} daily loss ≥ {L3_PCT:.0%}",
            )
        elif loss_pct >= L2_PCT and current < 2:
            pause_until = (
                datetime.now(timezone.utc) + timedelta(seconds=L2_PAUSE_S)
            ).isoformat()
            await self._set_level(
                2, now,
                reason=f"Level-2 PAUSE: {loss_pct:.1%} daily loss ≥ {L2_PCT:.0%}",
                pause_until=pause_until,
            )
        elif loss_pct >= L1_PCT and current < 1:
            await self._set_level(
                1, now,
                reason=f"Level-1 WARN: {loss_pct:.1%} daily loss ≥ {L1_PCT:.0%}",
            )

    def reset(self, reason: str = "manual"):
        """Manually reset all levels including Level 3."""
        if self._state.level > 0:
            logger.info(f"[CB] Reset level {self._state.level} ({reason})")
        self._state = CBState()
        self._save()

    def daily_reset(self):
        """
        Day-rollover reset: clears levels 1 and 2.
        Level 3 is intentionally NOT cleared — requires manual intervention.
        """
        if self._state.level in (1, 2):
            logger.info(f"[CB] Daily reset: level {self._state.level} → 0")
            self._state = CBState()
            self._save()

    def status(self) -> dict:
        s = self._state
        return {
            "level":        s.level,
            "reason":       s.reason,
            "triggered_at": s.triggered_at,
            "pause_until":  s.pause_until,
            "blocked":      self.is_blocked(),
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _set_level(self, level: int, now: str, *, reason: str, pause_until: str = ""):
        self._state = CBState(
            level=level,
            triggered_at=now,
            reason=reason,
            pause_until=pause_until,
        )
        self._save()

        if level == 3:
            logger.critical(f"[CB] ⛔ {reason}")
            if self._send:
                await self._send(
                    f"🚨 <b>Circuit Breaker LEVEL 3 — HALT</b>\n"
                    f"{reason}\n"
                    f"Alle neuen Entries gestoppt. Manueller Reset erforderlich.\n"
                    f"<code>/cb_reset</code> zum Entsperren."
                )
        elif level == 2:
            logger.warning(f"[CB] ⚠️ {reason}")
            expiry_short = pause_until[:16] if pause_until else "?"
            if self._send:
                await self._send(
                    f"⚠️ <b>Circuit Breaker Level 2 — Pause 1h</b>\n"
                    f"{reason}\n"
                    f"Neue Entries pausiert bis {expiry_short} UTC"
                )
        elif level == 1:
            logger.warning(f"[CB] ⚠️ {reason}")
            if self._send:
                await self._send(
                    f"⚠️ <b>Circuit Breaker Level 1 — Warnung</b>\n"
                    f"{reason}\n"
                    f"Trading läuft weiter."
                )

    def _load(self):
        try:
            if CB_STATE_PATH.exists():
                data = json.loads(CB_STATE_PATH.read_text())
                self._state = CBState(**{k: data.get(k, v) for k, v in asdict(CBState()).items()})
                if self._state.level > 0:
                    logger.warning(
                        f"[CB] Restored level={self._state.level} from disk: {self._state.reason}"
                    )
        except Exception as exc:
            logger.debug(f"[CB] Could not load state: {exc}")

    def _save(self):
        try:
            CB_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            CB_STATE_PATH.write_text(json.dumps(asdict(self._state), indent=2))
        except Exception as exc:
            logger.warning(f"[CB] Could not save state: {exc}")
