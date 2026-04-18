"""
SKILL: exit-manager
Purpose: Evaluiert offene Positionen, triggert Exits via TP-Staffel, Trailing-Stop,
         Whale-Follow-Exit, No-Exit-Rules
Inputs: OpenPosition-Liste, Live-Preise, Whale-Activity
Outputs: Exit-Orders via execution_engine, Telegram-Alerts
Triggers: Alle 60 Sek von main.py (neue async Task)
Status: Production Phase 1
"""

import asyncio
import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

from utils.logger import get_logger
from utils.config import Config

logger = get_logger("exit_manager")

_STATE_FILE = Path(__file__).parent.parent / "data" / "exit_state.json"


# ── Datenklassen ──────────────────────────────────────────────────────────────

@dataclass
class ExitEvent:
    """Beschreibt einen ausgelösten Exit."""
    position_id: str
    market: str
    condition_id: str
    outcome: str
    entry_price: float
    exit_price: float
    shares_sold: float
    usdc_received: float
    pnl_usdc: float
    pnl_pct: float
    exit_type: str          # "tp1" | "tp2" | "tp3" | "trail" | "whale_exit" | "manual"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tx_hash: str = ""


@dataclass
class ExitState:
    """Persistierter Zustand pro Position."""
    position_key: str           # "{condition_id}|{outcome}"
    entry_price: float
    tp1_done: bool = False
    tp2_done: bool = False
    tp3_done: bool = False
    trail_active: bool = False
    highest_price_seen: float = 0.0
    last_evaluated: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ExitState":
        return cls(**d)


# ── Exit-Manager ──────────────────────────────────────────────────────────────

class ExitManager:
    """
    Wertet offene Positionen aus und löst Exits aus.

    Aufruf-Interface (Teil 2 wired up in main.py):
        manager = ExitManager(config, wallet_monitor=monitor, on_exit_event=callback)
        await manager.evaluate_all(positions, live_prices, market_volumes)

    wallet_monitor muss get_recent_sells(wallet_addr, minutes) -> List[dict] bereitstellen.
    live_prices: Dict[token_id, float]
    market_volumes: Dict[condition_id, float] — optional, default 0 (→ thin-market trail)
    """

    def __init__(
        self,
        config: Config,
        wallet_monitor=None,
        on_exit_event: Optional[Callable] = None,
    ):
        self.cfg = config
        self.wallet_monitor = wallet_monitor
        self.on_exit_event = on_exit_event
        self._states: Dict[str, ExitState] = {}
        self._load_state()

    # ── State Persistence ─────────────────────────────────────────────────────

    def _load_state(self):
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not _STATE_FILE.exists():
            return
        try:
            raw = json.loads(_STATE_FILE.read_text())
            self._states = {k: ExitState.from_dict(v) for k, v in raw.items()}
            logger.info(f"[ExitMgr] State geladen: {len(self._states)} Positionen")
        except Exception as e:
            logger.warning(f"[ExitMgr] State-Datei korrupt, wird neu erstellt: {e}")
            self._states = {}

    def _save_state(self):
        try:
            _STATE_FILE.write_text(json.dumps(
                {k: v.to_dict() for k, v in self._states.items()},
                indent=2,
            ))
        except Exception as e:
            logger.error(f"[ExitMgr] State speichern fehlgeschlagen: {e}")

    def _get_or_create_state(self, pos) -> ExitState:
        key = f"{pos.market_id}|{pos.outcome}"
        if key not in self._states:
            self._states[key] = ExitState(
                position_key=key,
                entry_price=pos.entry_price,
                highest_price_seen=pos.entry_price,
            )
        return self._states[key]

    def _remove_state(self, condition_id: str, outcome: str):
        key = f"{condition_id}|{outcome}"
        self._states.pop(key, None)
        self._save_state()

    # ── No-Exit-Checks ────────────────────────────────────────────────────────

    def _should_skip(self, pos, current_value: float, hours_to_resolution: float) -> bool:
        if pos.shares <= 0:
            return True
        if current_value < self.cfg.exit_min_position_usdc:
            logger.debug(f"[ExitMgr] SKIP {pos.order_id}: value ${current_value:.2f} < min ${self.cfg.exit_min_position_usdc}")
            return True
        if 0 < hours_to_resolution < self.cfg.exit_min_hours_to_close:
            logger.debug(f"[ExitMgr] SKIP {pos.order_id}: nur {hours_to_resolution:.1f}h bis Close (< {self.cfg.exit_min_hours_to_close}h)")
            return True
        return False

    # ── Whale-Follow-Exit ─────────────────────────────────────────────────────

    async def _check_whale_exit(self, pos) -> bool:
        """True wenn Whale verkauft hat → Komplett-Exit triggern."""
        if not self.wallet_monitor or not hasattr(self.wallet_monitor, "get_recent_sells"):
            return False
        if not pos.source_wallet:
            return False
        try:
            sells = await self.wallet_monitor.get_recent_sells(pos.source_wallet, minutes=60)
            for sell in sells:
                sell_cid = sell.get("condition_id") or sell.get("market_id", "")
                if sell_cid == pos.market_id:
                    logger.info(
                        f"[ExitMgr] 🐋 WHALE EXIT: {pos.source_wallet[:10]}... verkaufte "
                        f"{pos.outcome} auf '{pos.market_question[:40]}'"
                    )
                    return True
        except Exception as e:
            logger.warning(f"[ExitMgr] get_recent_sells Fehler: {e}")
        return False

    # ── TP-Staffel ────────────────────────────────────────────────────────────

    def _check_tp(
        self,
        pos,
        state: ExitState,
        pnl_pct: float,
        multi_signal_count: int,
    ) -> Optional[tuple]:
        """Gibt (shares_ratio, exit_type) zurück oder None wenn kein TP."""
        boost = multi_signal_count >= self.cfg.exit_multi_signal_boost_min
        tp1_thr = self.cfg.exit_tp1_threshold_boost if boost else self.cfg.exit_tp1_threshold
        tp2_thr = self.cfg.exit_tp2_threshold_boost if boost else self.cfg.exit_tp2_threshold
        tp3_thr = self.cfg.exit_tp3_threshold_boost if boost else self.cfg.exit_tp3_threshold

        if not state.tp1_done and pnl_pct >= tp1_thr:
            return (self.cfg.exit_tp1_sell_ratio, "tp1")
        if not state.tp2_done and pnl_pct >= tp2_thr:
            return (self.cfg.exit_tp2_sell_ratio, "tp2")
        if not state.tp3_done and pnl_pct >= tp3_thr:
            return (self.cfg.exit_tp3_sell_ratio, "tp3")
        return None

    # ── Trailing-Stop ─────────────────────────────────────────────────────────

    def _check_trail(
        self,
        pos,
        state: ExitState,
        current_price: float,
        market_volume: float,
    ) -> bool:
        """Aktualisiert highest_price_seen und gibt True zurück wenn Stop ausgelöst."""
        gain = current_price - state.entry_price
        if gain < self.cfg.exit_trail_activation:
            return False

        if not state.trail_active:
            state.trail_active = True
            logger.info(
                f"[ExitMgr] 📈 Trailing-Stop aktiviert: {pos.outcome} @ {current_price:.3f} "
                f"(entry {state.entry_price:.3f}, gain +{gain:.3f})"
            )

        if current_price > state.highest_price_seen:
            state.highest_price_seen = current_price

        liquid = market_volume >= self.cfg.exit_trail_liquidity_threshold
        trail_dist = self.cfg.exit_trail_distance_liquid if liquid else self.cfg.exit_trail_distance_thin
        stop_price = max(state.entry_price, state.highest_price_seen - trail_dist)

        if current_price <= stop_price:
            logger.info(
                f"[ExitMgr] 🔻 TRAIL STOP: {pos.outcome} current={current_price:.3f} "
                f"<= stop={stop_price:.3f} (high={state.highest_price_seen:.3f}, dist={trail_dist})"
            )
            return True
        return False

    # ── Exit ausführen ────────────────────────────────────────────────────────

    async def _execute_exit(
        self,
        pos,
        state: ExitState,
        shares_ratio: float,
        exit_type: str,
        current_price: float,
    ) -> Optional[ExitEvent]:
        shares_to_sell = round(pos.shares * shares_ratio, 6)
        usdc_received  = round(shares_to_sell * current_price, 4)
        cost_basis     = round(pos.size_usdc * shares_ratio, 4)
        pnl_usdc       = round(usdc_received - cost_basis, 4)
        pnl_pct        = round((current_price - state.entry_price) / max(0.001, state.entry_price) * 100, 2)

        event = ExitEvent(
            position_id=pos.order_id,
            market=pos.market_question,
            condition_id=pos.market_id,
            outcome=pos.outcome,
            entry_price=state.entry_price,
            exit_price=current_price,
            shares_sold=shares_to_sell,
            usdc_received=usdc_received,
            pnl_usdc=pnl_usdc,
            pnl_pct=pnl_pct,
            exit_type=exit_type,
        )

        dry_tag = "[DRY-RUN] " if self.cfg.exit_dry_run else ""
        logger.info(
            f"[ExitMgr] {dry_tag}EXIT {exit_type.upper()}: {pos.outcome} @ {current_price:.3f} | "
            f"sell {shares_ratio*100:.0f}% ({shares_to_sell:.4f} shares) | "
            f"recv ${usdc_received:.2f} | pnl {'+' if pnl_usdc>=0 else ''}${pnl_usdc:.2f} ({pnl_pct:+.1f}%) | "
            f"{pos.market_question[:50]}"
        )

        if not self.cfg.exit_dry_run:
            # Part 2: hier execution_engine.sell_position(pos, shares_to_sell) aufrufen
            pass

        if self.on_exit_event:
            try:
                await self.on_exit_event(event)
            except Exception as e:
                logger.warning(f"[ExitMgr] on_exit_event callback Fehler: {e}")

        return event

    # ── Haupt-Evaluations-Loop ────────────────────────────────────────────────

    async def evaluate_all(
        self,
        positions: list,
        live_prices: Dict[str, float],
        market_volumes: Optional[Dict[str, float]] = None,
        multi_signal_counts: Optional[Dict[str, int]] = None,
    ) -> List[ExitEvent]:
        """
        Evaluiert alle offenen Positionen. Gibt Liste der ausgelösten ExitEvents zurück.

        positions: Liste von OpenPosition-Objekten (aus execution_engine)
        live_prices: {token_id: float}  — aktuelle Marktpreise (0..1)
        market_volumes: {condition_id: float} — optional, 0 = thin market
        multi_signal_counts: {condition_id: int} — optional, für Boost-Staffel
        """
        if not self.cfg.exit_enabled:
            return []

        volumes = market_volumes or {}
        multi_counts = multi_signal_counts or {}
        events: List[ExitEvent] = []
        state_dirty = False

        for pos in positions:
            current_price = live_prices.get(pos.token_id)
            if current_price is None:
                logger.debug(f"[ExitMgr] Kein Live-Preis für token_id={pos.token_id[:16]}, skip")
                continue

            current_value = pos.shares * current_price
            hours_to_resolution = self._hours_to_resolution(pos)

            if self._should_skip(pos, current_value, hours_to_resolution):
                continue

            state = self._get_or_create_state(pos)
            state.last_evaluated = time.time()
            multi_count = multi_counts.get(pos.market_id, 1)
            pnl_pct = (current_price - state.entry_price) / max(0.001, state.entry_price)

            # 1. Whale-Follow-Exit (höchste Priorität)
            if await self._check_whale_exit(pos):
                event = await self._execute_exit(pos, state, 1.0, "whale_exit", current_price)
                if event:
                    events.append(event)
                    self._remove_state(pos.market_id, pos.outcome)
                    state_dirty = False  # remove_state already saves
                continue

            # 2. TP-Staffel
            tp_result = self._check_tp(pos, state, pnl_pct, multi_count)
            if tp_result:
                ratio, exit_type = tp_result
                event = await self._execute_exit(pos, state, ratio, exit_type, current_price)
                if event:
                    events.append(event)
                    if exit_type == "tp1":
                        state.tp1_done = True
                    elif exit_type == "tp2":
                        state.tp2_done = True
                    elif exit_type == "tp3":
                        state.tp3_done = True
                    state_dirty = True

            # 3. Trailing-Stop (unabhängig von Staffel)
            market_vol = volumes.get(pos.market_id, 0.0)
            if self._check_trail(pos, state, current_price, market_vol):
                event = await self._execute_exit(pos, state, 1.0, "trail", current_price)
                if event:
                    events.append(event)
                    self._remove_state(pos.market_id, pos.outcome)
                    state_dirty = False
                continue

            if state_dirty:
                self._save_state()
                state_dirty = False

        return events

    # ── Hilfsfunktionen ───────────────────────────────────────────────────────

    @staticmethod
    def _hours_to_resolution(pos) -> float:
        """Stunden bis Markt schließt. 0 wenn unbekannt (kein Skip)."""
        closes_at = getattr(pos, "market_closes_at", None)
        if not closes_at:
            return 0.0
        try:
            if closes_at.tzinfo is None:
                closes_at = closes_at.replace(tzinfo=timezone.utc)
            delta = (closes_at - datetime.now(timezone.utc)).total_seconds()
            return max(0.0, delta / 3600)
        except Exception:
            return 0.0
