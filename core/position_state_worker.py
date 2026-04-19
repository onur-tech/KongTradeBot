"""
core/position_state_worker.py — T-M08 Phase 2: State-Update-Worker

Einzelner data-API-Call (?redeemable=true) statt N gamma-API-Calls.
Detektiert aufgelöste Märkte und setzt OpenPosition.position_state
auf PENDING_CLOSE.

Design-Prinzipien:
  - Läuft als eigener asyncio-Task, blockiert Main-Loop NICHT
  - 1 API-Call pro Zyklus statt N (eine Anfrage für alle Positionen)
  - Schreibt states in data/position_states.json
  - Greift NUR auf engine.open_positions zu (read + state-update)
  - Keine Interferenz mit exit_manager.py (T-M04d/T-M04f UNVERAENDERT)
  - Fehler werden geloggt, nie propagiert
"""

import asyncio
import json
import os
import time
from pathlib import Path

import aiohttp

from core.position_state import PositionState
from utils.logger import get_logger

logger = get_logger("state_worker")

STATES_FILE     = Path("data/position_states.json")
DATA_API_BASE   = "https://data-api.polymarket.com"
REQUEST_TIMEOUT = 12


class PositionStateWorker:
    """
    Hintergrund-Worker: prüft alle INTERVAL Sekunden ob Märkte aufgelöst wurden.

    Nutzt einen einzigen API-Call:
        GET /positions?user={proxy}&redeemable=true
    → liefert alle aufgelösten Positionen auf einmal (effizienter als N gamma-Calls).

    Verwendung in main.py:
        worker = PositionStateWorker(engine, interval=300)
        asyncio.create_task(worker.run())
    """

    def __init__(self, engine, interval: int = 300):
        self.engine        = engine
        self.interval      = interval
        self._states: dict = {}          # "condition_id|outcome" → PositionState str
        self._last_run: float = 0.0
        self._proxy_addr   = os.getenv("POLYMARKET_ADDRESS", "")
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

    # ── Batch Redeemable Fetch ─────────────────────────────────────────────────

    async def _fetch_redeemable_set(self, session: aiohttp.ClientSession) -> set:
        """
        Holt alle redeemable Positionen in einem einzigen API-Call.
        Gibt ein Set von "conditionId|outcome"-Strings zurück.

        Effizienz: 1 HTTP-Call statt N gamma-API-Calls pro Position.
        """
        if not self._proxy_addr:
            logger.warning("[StateWorker] POLYMARKET_ADDRESS nicht gesetzt — kein Redeemable-Check")
            return set()

        url = (
            f"{DATA_API_BASE}/positions"
            f"?user={self._proxy_addr}&redeemable=true&sizeThreshold=.01&limit=500"
        )
        try:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            async with session.get(url, timeout=timeout) as r:
                if r.status != 200:
                    logger.warning(f"[StateWorker] data-API Status {r.status}")
                    return set()
                data = await r.json()
                if not isinstance(data, list):
                    return set()
                result = set()
                for entry in data:
                    cid     = entry.get("conditionId", "")
                    outcome = entry.get("outcome", "")
                    if cid and outcome:
                        result.add(f"{cid}|{outcome}")
                logger.debug(
                    f"[StateWorker] {len(result)} redeemable Positionen von API"
                )
                return result
        except asyncio.TimeoutError:
            logger.warning("[StateWorker] Timeout beim Redeemable-Fetch")
        except Exception as e:
            logger.warning(f"[StateWorker] API-Fehler: {e}")
        return set()

    # ── Haupt-Loop ────────────────────────────────────────────────────────────

    async def run(self) -> None:
        """Läuft als asyncio-Task. Pausiert INTERVAL Sekunden zwischen Runs."""
        logger.info(
            f"[StateWorker] Gestartet (Interval: {self.interval}s, "
            f"Proxy: {self._proxy_addr[:10]}...)"
        )
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

        changed = 0
        start   = time.monotonic()

        async with aiohttp.ClientSession() as session:
            # Einziger API-Call für alle Positionen
            redeemable_set = await self._fetch_redeemable_set(session)

        for pos in positions:
            key     = f"{pos.market_id}|{pos.outcome}"
            current = self._states.get(key, PositionState.OPEN)

            if current == PositionState.RESOLVED:
                continue

            is_redeemable = key in redeemable_set

            if is_redeemable and current != PositionState.PENDING_CLOSE:
                self._states[key]  = PositionState.PENDING_CLOSE
                pos.position_state = PositionState.PENDING_CLOSE
                changed += 1
                logger.info(
                    f"[StateWorker] 🕐 PENDING_CLOSE: {pos.outcome} | "
                    f"{pos.market_question[:55]}"
                )
            elif not is_redeemable and key not in self._states:
                self._states[key] = PositionState.OPEN

        elapsed = time.monotonic() - start

        if changed:
            self._save()
            logger.info(
                f"[StateWorker] {changed} State(s) → PENDING_CLOSE | "
                f"{len(positions)} geprüft | {elapsed:.1f}s"
            )
        else:
            logger.debug(
                f"[StateWorker] Keine Änderungen | {len(positions)} geprüft | "
                f"{len(redeemable_set) if 'redeemable_set' in dir() else 0} redeemable | "
                f"{elapsed:.1f}s"
            )

        self._last_run = time.time()
