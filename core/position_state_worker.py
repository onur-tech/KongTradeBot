"""
core/position_state_worker.py — T-M08 Phase 2: State-Update-Worker

Polls Polymarket gamma-API alle INTERVAL Sekunden.
Detektiert aufgelöste Märkte und setzt OpenPosition.position_state
auf PENDING_CLOSE.

Design-Prinzipien:
  - Läuft als eigener asyncio-Task, blockiert Main-Loop NICHT
  - Schreibt states nach core/exit_state.json-Muster in data/position_states.json
  - Greift NUR auf engine.open_positions zu (read + state-update)
  - Keine Interferenz mit exit_manager.py (T-M04d/T-M04f UNVERAENDERT)
  - Fehler werden geloggt, nie propagiert
"""

import asyncio
import json
import time
from pathlib import Path

import aiohttp

from core.position_state import PositionState
from utils.logger import get_logger

logger = get_logger("state_worker")

STATES_FILE  = Path("data/position_states.json")
GAMMA_API    = "https://gamma-api.polymarket.com/markets"
REQUEST_TIMEOUT = 8


class PositionStateWorker:
    """
    Hintergrund-Worker: prüft alle INTERVAL Sekunden ob Märkte aufgelöst wurden.

    Verwendung in main.py:
        worker = PositionStateWorker(engine, interval=300)
        asyncio.create_task(worker.run())
    """

    def __init__(self, engine, interval: int = 300):
        self.engine   = engine
        self.interval = interval
        self._states: dict = {}          # "market_id|outcome" → PositionState str
        self._last_run: float = 0.0
        self._load()

    # ── Persistenz ────────────────────────────────────────────────────────────

    def _load(self) -> None:
        try:
            if STATES_FILE.exists():
                self._states = json.loads(STATES_FILE.read_text(encoding="utf-8"))
                logger.info(f"[StateWorker] {len(self._states)} Position-States geladen")
        except Exception as e:
            logger.warning(f"[StateWorker] States laden fehlgeschlagen: {e}")
            self._states = {}

    def _save(self) -> None:
        try:
            STATES_FILE.parent.mkdir(exist_ok=True)
            STATES_FILE.write_text(
                json.dumps(self._states, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"[StateWorker] States speichern fehlgeschlagen: {e}")

    # ── Public Interface ───────────────────────────────────────────────────────

    def get_state(self, market_id: str, outcome: str) -> str:
        """State für eine Position lesen (Default: OPEN)."""
        key = f"{market_id}|{outcome}"
        return self._states.get(key, PositionState.OPEN)

    def get_all_states(self) -> dict:
        return dict(self._states)

    def mark_resolved(self, market_id: str, outcome: str) -> None:
        """Manuell auf RESOLVED setzen (wird von Phase 5 Exit-Guard gerufen)."""
        key = f"{market_id}|{outcome}"
        if self._states.get(key) != PositionState.RESOLVED:
            self._states[key] = PositionState.RESOLVED
            self._save()

    # ── Polymarket API Check ───────────────────────────────────────────────────

    async def _is_market_resolved(self, session: aiohttp.ClientSession, token_id: str) -> bool:
        """
        True wenn der Markt aufgelöst ist.
        Nutzt gamma-API: resolved=true oder resolutionTime gesetzt.
        """
        try:
            url    = f"{GAMMA_API}?clob_token_ids={token_id}"
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            async with session.get(url, timeout=timeout) as r:
                if r.status != 200:
                    return False
                data = await r.json()
                if not isinstance(data, list) or not data:
                    return False
                market = data[0]
                return bool(market.get("resolved") or market.get("resolutionTime"))
        except asyncio.TimeoutError:
            logger.debug(f"[StateWorker] Timeout für token_id {token_id[:16]}...")
        except Exception as e:
            logger.debug(f"[StateWorker] API-Fehler: {e}")
        return False

    # ── Haupt-Loop ────────────────────────────────────────────────────────────

    async def run(self) -> None:
        """Läuft als asyncio-Task. Pausiert INTERVAL Sekunden zwischen Runs."""
        logger.info(f"[StateWorker] Gestartet (Interval: {self.interval}s)")
        while True:
            await asyncio.sleep(self.interval)
            try:
                await self._update_once()
            except Exception as e:
                logger.error(f"[StateWorker] Unerwarteter Fehler: {e}")

    async def _update_once(self) -> None:
        positions = list(self.engine.open_positions.values())
        if not positions:
            return

        changed   = 0
        checked   = 0
        start     = time.monotonic()

        async with aiohttp.ClientSession() as session:
            for pos in positions:
                key     = f"{pos.market_id}|{pos.outcome}"
                current = self._states.get(key, PositionState.OPEN)

                # RESOLVED Positionen nicht mehr prüfen
                if current == PositionState.RESOLVED:
                    continue

                token_id = getattr(pos, "token_id", "")
                if not token_id:
                    continue

                checked += 1
                resolved = await self._is_market_resolved(session, token_id)

                if resolved and current != PositionState.PENDING_CLOSE:
                    self._states[key]   = PositionState.PENDING_CLOSE
                    pos.position_state  = PositionState.PENDING_CLOSE
                    changed += 1
                    logger.info(
                        f"[StateWorker] 🕐 PENDING_CLOSE: {pos.outcome} | "
                        f"{pos.market_question[:55]}"
                    )
                elif not resolved and current == PositionState.OPEN:
                    # Explizit im State speichern falls noch nicht vorhanden
                    self._states[key] = PositionState.OPEN

                # Rate-limit: kurze Pause zwischen API-Calls
                await asyncio.sleep(0.3)

        elapsed = time.monotonic() - start

        if changed:
            self._save()
            logger.info(
                f"[StateWorker] {changed} State(s) → PENDING_CLOSE | "
                f"{checked} geprüft | {elapsed:.1f}s"
            )
        else:
            logger.debug(
                f"[StateWorker] Keine Änderungen | {checked} geprüft | {elapsed:.1f}s"
            )

        self._last_run = time.time()
