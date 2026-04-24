"""
CopyTradingPlugin — Phase 4 Port

Port der CopyTradingStrategy zum StrategyPlugin-Interface.
Konfiguration kommt aus config/strategies/copy_trading.yaml statt hardcodierten Dicts.
Business-Logik (Aggregation, Decay, Herd, Kategorie-Filter) bleibt identisch.

live_engine nutzt weiterhin strategy.handle_signal(TradeSignal) als WalletMonitor-Callback.
on_signal(Signal) implementiert das StrategyPlugin-ABC für future Sim-Engine Calls.
"""
from __future__ import annotations

import asyncio
import os
from collections import deque
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional

from core.plugin_base import Fill, Order, Signal, StrategyPlugin, Tick
from core.risk_manager import RiskDecision, RiskManager
from core.signal_scorer import SignalScorer, WalletStats
from core.strategy_config import StrategyConfig, get as get_strategy_config
from core.wallet_categories import MarketCategory, WalletCategoryTracker, classify_market
from core.wallet_decay import WalletDecayMonitor
from core.wallet_monitor import TradeSignal
from utils.config import Config
from utils.logger import get_logger

try:
    from utils.error_handler import handle_error as _handle_error
except ImportError:
    _handle_error = None

try:
    from utils.signal_tracker import log_signal as _log_signal_tracker
except ImportError:
    _log_signal_tracker = None

logger = get_logger("copy_trading_plugin")


# ---------------------------------------------------------------------------
# CopyOrder (re-exported for live_engine compat — same structure as before)
# ---------------------------------------------------------------------------

@dataclass
class CopyOrder:
    signal: TradeSignal
    size_usdc: float
    dry_run: bool
    wallet_multiplier: float = 1.0
    is_multi_signal: bool = False

    def __repr__(self) -> str:
        mode = "[DRY-RUN]" if self.dry_run else "[LIVE]"
        return f"CopyOrder{mode} {self.signal.side} ${self.size_usdc:.2f} | {self.signal}"


# ---------------------------------------------------------------------------
# Per-Wallet Performance Tracking
# ---------------------------------------------------------------------------

@dataclass
class WalletPerformance:
    wallet_address: str
    trades_total: int = 0
    trades_won: int = 0
    trades_lost: int = 0
    total_pnl_usd: float = 0.0
    recent_results: deque = field(default_factory=lambda: deque(maxlen=20))

    @property
    def win_rate(self) -> float:
        return self.trades_won / self.trades_total if self.trades_total else 0.0

    @property
    def recent_win_rate(self) -> float:
        if not self.recent_results:
            return 0.0
        return sum(1 for r in self.recent_results if r > 0) / len(self.recent_results)

    @property
    def is_decaying(self) -> bool:
        return len(self.recent_results) >= 10 and self.recent_win_rate < 0.45

    @property
    def is_trend_declining(self) -> bool:
        return (
            self.trades_total >= 20
            and len(self.recent_results) >= 10
            and self.recent_win_rate < self.win_rate - 0.10
        )

    def record(self, pnl_usd: float) -> None:
        self.trades_total += 1
        self.total_pnl_usd += pnl_usd
        self.recent_results.append(pnl_usd)
        if pnl_usd > 0:
            self.trades_won += 1
        else:
            self.trades_lost += 1


# ---------------------------------------------------------------------------
# CopyTradingPlugin
# ---------------------------------------------------------------------------

class CopyTradingPlugin(StrategyPlugin):
    """
    Copy-Trading strategy as a StrategyPlugin.

    Requires:
      config     — bot Config (from utils.config)
      risk       — shared RiskManager instance
      mode       — "live" or "simulation"
      scfg       — optional StrategyConfig; defaults to module singleton from YAML
    """

    def __init__(
        self,
        config: Config,
        risk: RiskManager,
        mode: str = "live",
        scfg: Optional[StrategyConfig] = None,
    ) -> None:
        super().__init__(mode=mode)  # type: ignore[arg-type]
        self.config = config
        self.risk_manager = risk
        self._scfg: StrategyConfig = scfg if scfg is not None else get_strategy_config()

        # Per-wallet performance
        self.wallet_performance: Dict[str, WalletPerformance] = {
            w: WalletPerformance(wallet_address=w) for w in config.target_wallets
        }

        # Callbacks (same names as CopyTradingStrategy for live_engine compat)
        self.on_copy_order: Optional[callable] = None
        self.get_open_positions_count: Optional[callable] = None
        self.get_open_positions: Optional[callable] = None
        self.on_whale_exit: Optional[callable] = None
        self.on_wallet_warning: Optional[callable] = None
        self.on_herd_alert: Optional[callable] = None

        # Signal aggregation buffers
        self._agg_buffer: Dict[str, List[TradeSignal]] = {}
        self._agg_tasks: Dict[str, asyncio.Task] = {}

        self.stats: Dict[str, int] = {
            "signals_received": 0,
            "orders_created": 0,
            "orders_skipped": 0,
            "multi_signals": 0,
        }

        # Phase 5A: Optimization Layer (optional — only active when db_path is set)
        _db = os.environ.get("TRADE_LOGGER_DB", "data/kongtrade.db")
        self._scorer = SignalScorer()
        self._decay_monitor = WalletDecayMonitor(db_path=_db)
        self._cat_tracker = WalletCategoryTracker(db_path=_db)
        # Set to False to disable 5A features without code changes
        self._scoring_enabled: bool = os.environ.get("SIGNAL_SCORING_ENABLED", "true").lower() == "true"

    # ── helpers ──────────────────────────────────────────────────────────────

    def _wallet_name(self, addr: str) -> str:
        return self._scfg.wallet_names.get(addr.lower(), addr[:10] + "...")

    def _wallet_multiplier(self, addr: str) -> float:
        return self._scfg.wallet_multipliers.get(addr.lower(), self._scfg.default_multiplier)

    def _detect_category(self, question: str) -> str:
        q = question.lower()
        for cat, keywords in self._scfg.category_keywords.items():
            if any(k in q for k in keywords):
                return cat
        return "other"

    def _should_copy(self, wallet_addr: str, market_question: str) -> tuple[bool, str]:
        allowed = self._scfg.wallet_categories.get(wallet_addr.lower(), [])
        if not allowed or "broad" in allowed:
            return True, "Allrounder"
        cat = self._detect_category(market_question)
        if cat in allowed:
            return True, f"Kategorie-Match: {cat}"
        return False, f"Kategorie {cat!r} nicht in Spezialgebiet {allowed}"

    def _is_crypto_daily(self, signal: TradeSignal) -> bool:
        slug = getattr(signal, "market_slug", "") or ""
        question = getattr(signal, "market_question", "") or ""
        text = (slug + " " + question).lower()
        return any(kw in text for kw in self._scfg.crypto_daily_keywords)

    def _log_signal(self, signal: TradeSignal, decision: str, reason: Optional[str]) -> None:
        if _log_signal_tracker is not None:
            _log_signal_tracker(signal, decision, reason)

    # ── StrategyPlugin ABC ────────────────────────────────────────────────────

    async def on_signal(self, signal: Signal) -> Optional[Order]:
        """ABC entry point — converts plugin Signal → TradeSignal and routes to handle_signal."""
        ts = TradeSignal(
            tx_hash=signal.tx_hash,
            source_wallet=signal.source_wallet,
            market_id=signal.market_id,
            token_id=signal.token_id,
            side=signal.side,
            price=signal.price,
            size_usdc=signal.size_usdc,
        )
        await self.handle_signal(ts)
        return None  # Order is dispatched via on_copy_order callback, not returned

    async def on_fill(self, fill: Fill) -> None:
        pass

    async def on_tick(self, tick: Tick) -> None:
        pass

    # ── Main entry (backward compat with live_engine callbacks) ───────────────

    async def handle_signal(self, signal: TradeSignal) -> None:
        """Called by WalletMonitor via on_new_trade callback."""
        self.stats["signals_received"] += 1

        key = f"{signal.token_id}:{signal.outcome}"
        if key not in self._agg_buffer:
            self._agg_buffer[key] = []

        if any(s.source_wallet == signal.source_wallet for s in self._agg_buffer[key]):
            return

        self._agg_buffer[key].append(signal)

        name = self._wallet_name(signal.source_wallet)
        market_short = (signal.market_question or signal.token_id)[:60]

        if key not in self._agg_tasks or self._agg_tasks[key].done():
            logger.info(
                f"⏳ Signal buffered [{name}] {signal.outcome} auf '{market_short}' "
                f"— warte {self._scfg.aggregation.window_s}s auf weitere Wallets..."
            )
            self._agg_tasks[key] = asyncio.create_task(self._flush_aggregated(key))
        else:
            count = len(self._agg_buffer[key])
            names = " + ".join(self._wallet_name(s.source_wallet) for s in self._agg_buffer[key])
            mult = self._scfg.aggregation.multi_signal_multipliers.get(count, 2.0)
            logger.info(
                f"🔥 MULTI-SIGNAL ({count}x): {names} kaufen beide "
                f"{signal.outcome} auf '{market_short}' → {mult}x Größe!"
            )

    async def _flush_aggregated(self, key: str) -> None:
        await asyncio.sleep(self._scfg.aggregation.window_s)

        signals = self._agg_buffer.pop(key, [])
        self._agg_tasks.pop(key, None)
        if not signals:
            return

        count = len(signals)
        base = max(signals, key=lambda s: s.size_usdc)
        market_short = (base.market_question or base.token_id)[:60]

        total_wallets = max(1, len(self.config.target_wallets))
        herd_threshold = max(3, int(total_wallets * self._scfg.aggregation.herd_fraction))

        if count > herd_threshold:
            multi_mult = 1.0
            self.stats["herd_signals"] = self.stats.get("herd_signals", 0) + 1
            names = " + ".join(self._wallet_name(s.source_wallet) for s in signals)
            logger.warning(
                f"🐑 HERDENTRIEB ({count}/{total_wallets} = {count/total_wallets:.0%} Wallets) "
                f"— kein Größen-Boost | {names} | {base.outcome} auf '{market_short}'"
            )
            if self.on_herd_alert:
                asyncio.create_task(self._safe_call(
                    self.on_herd_alert, count, total_wallets, names, base.outcome, market_short
                ))
        else:
            multi_mult = self._scfg.aggregation.multi_signal_multipliers.get(count, 2.0)

        # Min-Wallet-Check
        crypto_single = os.environ.get("CRYPTO_DAILY_SINGLE_SIGNAL", "true").lower() == "true"
        min_sigs = 1 if (crypto_single and self._is_crypto_daily(base)) else 2
        if count < min_sigs:
            logger.info(
                f"⏭️ SKIP: nur {count} Wallet ({self._wallet_name(base.source_wallet)}) "
                f"— min {min_sigs} für diesen Markt | {base.outcome} auf '{market_short}'"
            )
            self.stats["orders_skipped"] += 1
            self._log_signal(base, "SKIPPED", f"MIN_WALLETS:{count}<{min_sigs}")
            return

        if count >= 2:
            self.stats["multi_signals"] += 1
            names = " + ".join(self._wallet_name(s.source_wallet) for s in signals)
            logger.info(
                f"🔥 MULTI-SIGNAL AUSFÜHRUNG ({count} Wallets, {multi_mult}x): "
                f"{names} | {base.outcome} auf '{market_short}'"
            )
            if hasattr(self, "on_multi_signal") and self.on_multi_signal:
                try:
                    await self._safe_call(
                        self.on_multi_signal, count, names, base.outcome, market_short, multi_mult
                    )
                except Exception:
                    pass
        else:
            logger.info(
                f"₿ CRYPTO-DAILY SINGLE-SIGNAL [{self._wallet_name(base.source_wallet)}]: "
                f"{base.outcome} auf '{market_short}'"
            )

        await self._process_signal(base, extra_multiplier=multi_mult)

    async def _process_signal(self, signal: TradeSignal, extra_multiplier: float = 1.0) -> None:
        # 0a. CATEGORY_BLACKLIST
        blacklist = [s.strip() for s in os.environ.get("CATEGORY_BLACKLIST", "").split(",") if s.strip()]
        if blacklist:
            slug = (getattr(signal, "market_slug", "") or signal.market_question or "").lower()
            for prefix in blacklist:
                if prefix.lower() in slug:
                    logger.info(f"⏭️ SKIP: reason=CATEGORY_BLACKLIST prefix={prefix!r} (slug={slug[:60]})")
                    self.stats["orders_skipped"] += 1
                    self._log_signal(signal, "SKIPPED", f"CATEGORY_BLACKLIST:{prefix}")
                    return

        # 0a1. OPPOSING_SIDE + EVENT_CAP
        if self.get_open_positions is not None:
            open_pos = self.get_open_positions()
            for pos in open_pos.values():
                if pos.market_id == signal.market_id and pos.outcome != signal.outcome:
                    logger.info(
                        f"⏭️ SKIP: reason=OPPOSING_SIDE_BLOCKED "
                        f"market={signal.market_id[:16]} already_hold={pos.outcome} new={signal.outcome}"
                    )
                    self.stats["orders_skipped"] += 1
                    self._log_signal(signal, "SKIPPED", "OPPOSING_SIDE_BLOCKED")
                    return
            neg_risk_id = getattr(signal, "neg_risk_market_id", "") or ""
            if neg_risk_id:
                event_cap = int(os.environ.get("COPY_EVENT_CAP", "3"))
                held = sum(
                    1 for p in open_pos.values()
                    if getattr(p, "neg_risk_market_id", "") == neg_risk_id
                )
                if held >= event_cap:
                    logger.info(
                        f"⏭️ SKIP: reason=EVENT_CAP_REACHED event={neg_risk_id[:16]} held={held}/{event_cap}"
                    )
                    self.stats["orders_skipped"] += 1
                    self._log_signal(signal, "SKIPPED", f"EVENT_CAP:{held}/{event_cap}")
                    return

        # 0a2. WALLET_CATEGORY_FILTER
        copy_ok, copy_reason = self._should_copy(signal.source_wallet, signal.market_question or "")
        if not copy_ok:
            logger.info(
                f"⏭️ SKIP: reason=WALLET_CATEGORY wallet={signal.source_wallet[:18]} "
                f"| {copy_reason} | {(signal.market_question or '')[:50]}"
            )
            self.stats["orders_skipped"] += 1
            self._log_signal(signal, "SKIPPED", f"WALLET_CATEGORY:{copy_reason}")
            return

        # 0b. MIN_MARKT_VOLUMEN
        min_vol = float(os.environ.get("MIN_MARKT_VOLUMEN", "0"))
        market_vol = getattr(signal, "market_volume_usd", None)
        if min_vol > 0 and market_vol and market_vol < min_vol:
            logger.info(
                f"⏭️ SKIP: reason=MIN_MARKT_VOLUMEN vol=${market_vol:,.0f} < ${min_vol:,.0f}"
            )
            self.stats["orders_skipped"] += 1
            self._log_signal(signal, "SKIPPED", "MIN_MARKT_VOLUMEN")
            return

        # 0c. MAX_POSITIONS_TOTAL
        max_pos = int(os.environ.get("MAX_POSITIONS_TOTAL", "999"))
        if self.get_open_positions_count is not None:
            open_count = self.get_open_positions_count()
            if open_count >= max_pos:
                logger.info(f"⏭️ SKIP: reason=MAX_POSITIONS_TOTAL ({open_count}/{max_pos})")
                self.stats["orders_skipped"] += 1
                self._log_signal(signal, "SKIPPED", "MAX_POSITIONS_TOTAL")
                return

        # 1. Win-Rate-Decay
        perf = self.wallet_performance.get(signal.source_wallet)
        if perf and perf.is_decaying:
            logger.warning(
                f"⚠️  Win Rate Decay bei {self._wallet_name(signal.source_wallet)} | "
                f"Recent WR: {perf.recent_win_rate:.0%} — skip"
            )
            self.stats["orders_skipped"] += 1
            self._log_signal(signal, "SKIPPED", "WIN_RATE_DECAY")
            return

        # 2. Wallet-Multiplikator
        wallet_mult = self._wallet_multiplier(signal.source_wallet)
        if perf and perf.is_trend_declining:
            original = wallet_mult
            wallet_mult = round(wallet_mult / 2, 2)
            logger.warning(
                f"📉 Trend-Decline bei {self._wallet_name(signal.source_wallet)} | "
                f"Gesamt: {perf.win_rate:.0%} vs. Letzte 20: {perf.recent_win_rate:.0%} | "
                f"Mult: {original}x → {wallet_mult}x"
            )
            if self.on_wallet_warning:
                asyncio.create_task(self._safe_call(
                    self.on_wallet_warning,
                    self._wallet_name(signal.source_wallet),
                    perf.win_rate, perf.recent_win_rate, original, wallet_mult,
                ))

        # 2a. Phase 5A: Wallet-Decay-Check (adjusts wallet_mult via 30d DB stats)
        if self._scoring_enabled:
            decay = self._decay_monitor.evaluate(signal.source_wallet, wallet_mult)
            if decay.adjusted_multiplier != wallet_mult:
                logger.info(
                    f"📉 Decay-Adjust [{self._wallet_name(signal.source_wallet)}] "
                    f"{decay.reason}: {wallet_mult}x → {decay.adjusted_multiplier}x"
                )
            wallet_mult = decay.adjusted_multiplier

        # 2b. Phase 5A: Category-WR-Check (skip if wallet below threshold in market's category)
        if self._scoring_enabled:
            market_cat = classify_market(signal.market_question or "")
            if not self._cat_tracker.should_accept_signal(signal.source_wallet, market_cat):
                logger.info(
                    f"⏭️ SKIP: reason=CATEGORY_WR_BELOW_THRESHOLD "
                    f"wallet={signal.source_wallet[:18]} cat={market_cat.value}"
                )
                self.stats["orders_skipped"] += 1
                self._log_signal(signal, "SKIPPED", f"CATEGORY_WR:{market_cat.value}")
                return

        # Early-Entry Bonus
        early_bonus = 1.0
        if getattr(signal, "is_early_entry", False):
            early_bonus = self._scfg.aggregation.early_entry_multiplier
            logger.info(
                f"🌱 Early Entry Bonus {early_bonus}x | "
                f"Vol: ${getattr(signal, 'market_volume_usd', 0):,.0f}"
            )

        # 2c. Phase 5A: Signal-Score → size multiplier
        score_mult = 1.0
        if self._scoring_enabled:
            ws = WalletStats(
                win_rate=perf.win_rate if perf else 0.5,
                roi_pct=0.0,           # live ROI not yet tracked in plugin context
                stddev_returns=0.0,
                last_trade_days_ago=0,
                trades_total=perf.trades_total if perf else 0,
            )
            score = self._scorer.score(ws)
            score_mult = self._scorer.score_to_multiplier(score)
            if score_mult != 1.0:
                logger.debug(
                    f"🎯 Signal-Score {score:.0f}/100 → {score_mult}x "
                    f"[{self._wallet_name(signal.source_wallet)}]"
                )

        combined = wallet_mult * extra_multiplier * early_bonus * score_mult
        scaled = replace(signal, size_usdc=signal.size_usdc * combined)

        if combined != 1.0:
            logger.info(
                f"⚖️  Mult {combined:.1f}x für {self._wallet_name(signal.source_wallet)} "
                f"(Wallet {wallet_mult}x × Multi {extra_multiplier}x) | "
                f"${signal.size_usdc:.2f} → ${scaled.size_usdc:.2f}"
            )

        # 3. Risk check
        decision: RiskDecision = self.risk_manager.evaluate(scaled)
        if not decision.allowed:
            logger.info(f"❌ Trade abgelehnt: {decision.reason}")
            self.stats["orders_skipped"] += 1
            self._log_signal(signal, "SKIPPED", decision.reason)
            return

        # 4. Dispatch
        order = CopyOrder(
            signal=signal,
            size_usdc=decision.adjusted_size_usdc,
            dry_run=self.config.dry_run,
            wallet_multiplier=wallet_mult,
            is_multi_signal=extra_multiplier > 1.0,
        )
        self.stats["orders_created"] += 1
        logger.info(f"📋 Order erstellt: {order}")
        self._log_signal(signal, "COPIED", None)

        if self.on_copy_order:
            await self._safe_call(self.on_copy_order, order)

    # ── Whale-Exit-Copy ───────────────────────────────────────────────────────

    async def handle_whale_sell(self, signal: TradeSignal) -> None:
        if signal.side != "SELL":
            return
        if not getattr(self.config, "whale_exit_copy_enabled", False):
            return
        if not self.get_open_positions or not self.on_whale_exit:
            return

        open_positions = self.get_open_positions()
        name = self._wallet_name(signal.source_wallet)
        market_short = (signal.market_question or signal.market_id)[:50]

        for pos in open_positions.values():
            if pos.market_id != signal.market_id:
                continue
            if pos.source_wallet.lower() != signal.source_wallet.lower():
                continue
            logger.info(f"[whale_exit_copy] 🐋 {name} verkauft '{market_short}' → Exit {pos.outcome}")
            try:
                if asyncio.iscoroutinefunction(self.on_whale_exit):
                    await self.on_whale_exit(pos, signal)
                else:
                    self.on_whale_exit(pos, signal)
            except Exception as e:
                logger.error(f"[whale_exit_copy] on_whale_exit Fehler: {e}", exc_info=True)
            return

    # ── Status ────────────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        wallet_stats = {}
        for wallet, perf in self.wallet_performance.items():
            mult = self._wallet_multiplier(wallet)
            wallet_stats[wallet[:10] + "..."] = {
                "win_rate": f"{perf.win_rate:.0%}",
                "recent_win_rate": f"{perf.recent_win_rate:.0%}",
                "trades": perf.trades_total,
                "pnl": f"${perf.total_pnl_usd:.2f}",
                "decaying": perf.is_decaying,
                "multiplier": f"{mult}x",
            }
        return {
            "strategy": "copy_trading_plugin",
            "mode": self.mode,
            "signals_received": self.stats["signals_received"],
            "orders_created": self.stats["orders_created"],
            "orders_skipped": self.stats["orders_skipped"],
            "multi_signals": self.stats["multi_signals"],
            "wallets": wallet_stats,
        }

    # ── Internal safe-call ────────────────────────────────────────────────────

    async def _safe_call(self, fn, *args) -> None:
        try:
            if asyncio.iscoroutinefunction(fn):
                await fn(*args)
            else:
                fn(*args)
        except Exception as e:
            logger.error(f"Fehler bei Callback {getattr(fn, '__name__', fn)}: {e}", exc_info=True)
            if _handle_error is not None:
                ctx = f"_safe_call({getattr(fn, '__name__', str(fn))[:40]})"
                try:
                    await _handle_error(e, context=ctx, severity="ERROR", telegram_alert=True, reraise=False)
                except Exception:
                    pass
