"""
copy_trading.py — Strategie: Copy Trading

KERNAUFGABE:
Entscheidet welche Trades kopiert werden und mit welcher Größe.

LEKTIONEN AUS DER COMMUNITY:
- Nur kurzfristige Märkte (24-72h) kopieren
- Win Rate der Source-Wallet tracken
- Wenn Wallet schlechter wird → aufhören zu kopieren (Win Rate Decay Detection)
- Mehrere Wallets diversifizieren
- Signal-Aggregation: 2+ Wallets im selben Markt = stärkeres Signal → größerer Trade
"""

import asyncio
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional
from collections import deque
from datetime import datetime, timezone

from utils.logger import get_logger
from utils.config import Config
from core.wallet_monitor import TradeSignal
from core.risk_manager import RiskManager, RiskDecision

logger = get_logger("copy_trading")

# Sekunden nach dem ersten Signal warten, um weitere Wallets zu sammeln
AGGREGATION_WINDOW_S: int = 15

# Multiplikatoren je nach Anzahl bestätigender Wallets
MULTI_SIGNAL_MULTIPLIERS: Dict[int, float] = {
    1: 1.0,
    2: 1.5,
    3: 2.0,  # 3+ Wallets → 2x
}


# ---------------------------------------------------------------------------
# Wallet-Gewichtungs-Konfiguration
# Trägt bekannten Wallets einen Kapital-Multiplikator zu.
# Wallets die hier nicht aufgeführt sind bekommen DEFAULT_WALLET_MULTIPLIER.
# ---------------------------------------------------------------------------
WALLET_MULTIPLIERS: Dict[str, float] = {
    # majorexploiter — 76% Win Rate → 3x
    "0x019782cab5d844f02bafb71f512758be78579f3c": 3.0,

    # April#1 Sports — 65% Win Rate → 2x
    "0x492442eab586f242b53bda933fd5de859c8a3782": 2.0,

    # HorizonSplendidView → 2x
    "0x02227b8f5a9636e895607edd3185ed6ee5598ff7": 2.0,

    # reachingthesky → 2x
    "0xefbc5fec8d7b0acdc8911bdd9a98d6964308f9a2": 2.0,

    # HOOK → 2x
    "0x0b7a6030507efe5db145fbb57a25ba0c5f9d86cf": 2.0,

    # sovereign2013 — 57% Win Rate → 1x (Basiswert)
    "0xee613b3fc183ee44f9da9c05f53e2da107e3debf": 1.0,
}

# Unbekannte / nicht konfigurierte Wallets bekommen halbe Größe
DEFAULT_WALLET_MULTIPLIER: float = 0.5

# ---------------------------------------------------------------------------
# Wallet-Namen-Mapping — lesbare Namen für alle bekannten Target-Wallets
# ---------------------------------------------------------------------------
WALLET_NAMES: Dict[str, str] = {
    "0x019782cab5d844f02bafb71f512758be78579f3c": "majorexploiter",
    "0x492442eab586f242b53bda933fd5de859c8a3782": "April#1 Sports",
    "0x02227b8f5a9636e895607edd3185ed6ee5598ff7": "HorizonSplendidView",
    "0xefbc5fec8d7b0acdc8911bdd9a98d6964308f9a2": "reachingthesky",
    "0x0b7a6030507efe5db145fbb57a25ba0c5f9d86cf": "HOOK",
    "0xee613b3fc183ee44f9da9c05f53e2da107e3debf": "sovereign2013",
    "0xbaa2bcb5439e985ce4ccf815b4700027d1b92c73": "denizz",
    "0xde7be6d489bce070a959e0cb813128ae659b5f4b": "wan123",
    "0x7a6192ea6815d3177e978dd3f8c38be5f575af24": "Gambler1968",
    "0x7177a7f5c216809c577c50c77b12aae81f81ddef": "kcnyekchno",
    "0x2005d16a84ceefa912d4e380cd32e7ff827875ea": "RN1",
}


def get_wallet_name(wallet_address: str) -> str:
    """Gibt den lesbaren Namen einer Wallet zurück, oder eine gekürzte Adresse als Fallback."""
    return WALLET_NAMES.get(wallet_address.lower(), wallet_address[:10] + "...")


def get_wallet_multiplier(wallet_address: str) -> float:
    """Gibt den konfigurierten Größen-Multiplikator für eine Wallet zurück."""
    return WALLET_MULTIPLIERS.get(wallet_address.lower(), DEFAULT_WALLET_MULTIPLIER)


@dataclass
class WalletPerformance:
    """Trackt Performance einer kopierten Wallet."""
    wallet_address: str
    trades_total: int = 0
    trades_won: int = 0
    trades_lost: int = 0
    total_pnl_usd: float = 0.0

    # Letzte 20 Trades für Win-Rate-Decay-Detection
    recent_results: deque = field(default_factory=lambda: deque(maxlen=20))

    @property
    def win_rate(self) -> float:
        if self.trades_total == 0:
            return 0.0
        return self.trades_won / self.trades_total

    @property
    def recent_win_rate(self) -> float:
        """Win Rate der letzten 20 Trades."""
        if not self.recent_results:
            return 0.0
        wins = sum(1 for r in self.recent_results if r > 0)
        return wins / len(self.recent_results)

    @property
    def is_decaying(self) -> bool:
        """
        Win Rate Decay Detection.
        LEKTION: Wenn jemand gut war aber jetzt schlecht ist → aufhören zu kopieren.
        Erfordert mindestens 10 Trades für Signal.
        """
        if len(self.recent_results) < 10:
            return False
        return self.recent_win_rate < 0.45  # Unter 45% in letzten 20 Trades

    def record(self, pnl_usd: float):
        self.trades_total += 1
        self.total_pnl_usd += pnl_usd
        self.recent_results.append(pnl_usd)
        if pnl_usd > 0:
            self.trades_won += 1
        else:
            self.trades_lost += 1


@dataclass
class CopyOrder:
    """Ein Order der ausgeführt werden soll."""
    signal: TradeSignal
    size_usdc: float
    dry_run: bool

    def __repr__(self):
        mode = "[DRY-RUN]" if self.dry_run else "[LIVE]"
        return f"CopyOrder{mode} {self.signal.side} ${self.size_usdc:.2f} | {self.signal}"


class CopyTradingStrategy:
    """
    Verarbeitet eingehende TradeSignals und entscheidet ob kopiert wird.

    Wird vom WalletMonitor via Callback aufgerufen.
    Gibt CopyOrder weiter an ExecutionEngine.

    Signal-Aggregation: Signale für denselben Markt innerhalb von
    AGGREGATION_WINDOW_S Sekunden werden kombiniert → 1.5x / 2x Größe.
    """

    def __init__(self, config: Config, risk_manager: RiskManager):
        self.config = config
        self.risk_manager = risk_manager

        # Performance pro Wallet tracken
        self.wallet_performance: Dict[str, WalletPerformance] = {
            wallet: WalletPerformance(wallet_address=wallet)
            for wallet in config.target_wallets
        }

        # Callback zur ExecutionEngine
        self.on_copy_order: Optional[callable] = None

        # Signal-Aggregation: key = "token_id:outcome", value = Liste von Signalen
        self._agg_buffer: Dict[str, List[TradeSignal]] = {}
        self._agg_tasks: Dict[str, asyncio.Task] = {}

        # Statistik
        self.stats = {
            "signals_received": 0,
            "orders_created": 0,
            "orders_skipped": 0,
            "multi_signals": 0,
        }

    async def handle_signal(self, signal: TradeSignal):
        """
        Hauptfunktion: Verarbeitet ein TradeSignal.
        Wird vom WalletMonitor aufgerufen wenn neuer Trade erkannt.

        Statt sofort auszuführen: Signal in Aggregations-Buffer legen und
        AGGREGATION_WINDOW_S Sekunden auf weitere Wallets warten.
        """
        self.stats["signals_received"] += 1

        key = f"{signal.token_id}:{signal.outcome}"

        if key not in self._agg_buffer:
            self._agg_buffer[key] = []

        # Nur einmal pro Wallet buffern (kein Duplikat)
        already_from_wallet = any(
            s.source_wallet == signal.source_wallet for s in self._agg_buffer[key]
        )
        if already_from_wallet:
            return

        self._agg_buffer[key].append(signal)

        wallet_name = get_wallet_name(signal.source_wallet)
        market_short = signal.market_question[:60] if signal.market_question else signal.token_id[:16]

        # Erster Eingang → Aggregations-Timer starten
        if key not in self._agg_tasks or self._agg_tasks[key].done():
            logger.info(
                f"⏳ Signal buffered [{wallet_name}] {signal.outcome} auf '{market_short}' "
                f"— warte {AGGREGATION_WINDOW_S}s auf weitere Wallets..."
            )
            task = asyncio.create_task(self._flush_aggregated(key))
            self._agg_tasks[key] = task
        else:
            # Weiteres Signal für denselben Markt → sofort Vorschau loggen
            count = len(self._agg_buffer[key])
            names = " + ".join(get_wallet_name(s.source_wallet) for s in self._agg_buffer[key])
            multiplier = MULTI_SIGNAL_MULTIPLIERS.get(count, 2.0)
            logger.info(
                f"🔥 MULTI-SIGNAL ({count}x): {names} kaufen beide "
                f"{signal.outcome} auf '{market_short}' → {multiplier}x Größe!"
            )

    async def _flush_aggregated(self, key: str):
        """Nach AGGREGATION_WINDOW_S Sekunden: alle gesammelten Signale auswerten und ausführen."""
        await asyncio.sleep(AGGREGATION_WINDOW_S)

        signals = self._agg_buffer.pop(key, [])
        self._agg_tasks.pop(key, None)

        if not signals:
            return

        count = len(signals)
        # Basiswert: Signal mit größtem Einsatz der kopierenden Wallets
        base_signal = max(signals, key=lambda s: s.size_usdc)
        multi_multiplier = MULTI_SIGNAL_MULTIPLIERS.get(count, 2.0)  # 3+ → 2x
        market_short = base_signal.market_question[:60] if base_signal.market_question else base_signal.token_id[:16]

        if count >= 2:
            self.stats["multi_signals"] += 1
            names = " + ".join(get_wallet_name(s.source_wallet) for s in signals)
            logger.info(
                f"🔥 MULTI-SIGNAL AUSFÜHRUNG ({count} Wallets, {multi_multiplier}x): "
                f"{names} | {base_signal.outcome} auf '{market_short}'"
            )
            # Telegram-Benachrichtigung über on_multi_signal Callback (optional)
            if hasattr(self, "on_multi_signal") and self.on_multi_signal:
                try:
                    await self._safe_call(
                        self.on_multi_signal,
                        count, names, base_signal.outcome, market_short, multi_multiplier
                    )
                except Exception:
                    pass

        await self._process_signal(base_signal, extra_multiplier=multi_multiplier)

    async def _process_signal(self, signal: TradeSignal, extra_multiplier: float = 1.0):
        """Interne Ausführungslogik für ein (ggf. aggregiertes) Signal."""
        # 1. Performance der Source-Wallet prüfen
        perf = self.wallet_performance.get(signal.source_wallet)
        if perf and perf.is_decaying:
            logger.warning(
                f"⚠️  Win Rate Decay erkannt bei {get_wallet_name(signal.source_wallet)} | "
                f"Aktuelle Win Rate: {perf.recent_win_rate:.0%} — überspringe Trade"
            )
            self.stats["orders_skipped"] += 1
            return

        # 2. Wallet-Multiplikator × Multi-Signal-Multiplikator anwenden
        wallet_multiplier = get_wallet_multiplier(signal.source_wallet)
        combined_multiplier = wallet_multiplier * extra_multiplier
        scaled_signal = replace(signal, size_usdc=signal.size_usdc * combined_multiplier)

        if combined_multiplier != 1.0:
            logger.info(
                f"⚖️  Multiplikator {combined_multiplier:.1f}x für {get_wallet_name(signal.source_wallet)} "
                f"(Wallet {wallet_multiplier}x × Multi-Signal {extra_multiplier}x) | "
                f"${signal.size_usdc:.2f} → ${scaled_signal.size_usdc:.2f}"
            )

        # 3. Risiko-Check
        decision: RiskDecision = self.risk_manager.evaluate(scaled_signal)

        if not decision.allowed:
            logger.info(f"❌ Trade abgelehnt: {decision.reason}")
            self.stats["orders_skipped"] += 1
            return

        # 4. Order erstellen und weiterleiten
        order = CopyOrder(
            signal=signal,
            size_usdc=decision.adjusted_size_usdc,
            dry_run=self.config.dry_run,
        )

        self.stats["orders_created"] += 1
        logger.info(f"📋 Order erstellt: {order}")

        if self.on_copy_order:
            await self._safe_execute(order)

    async def _safe_execute(self, order: CopyOrder):
        """Führt Order aus — fängt Fehler damit die Strategie weiterläuft."""
        await self._safe_call(self.on_copy_order, order)

    async def _safe_call(self, fn, *args):
        try:
            if asyncio.iscoroutinefunction(fn):
                await fn(*args)
            else:
                fn(*args)
        except Exception as e:
            logger.error(f"Fehler bei Callback: {e}", exc_info=True)

    def get_status(self) -> dict:
        """Gibt aktuellen Status der Strategie zurück."""
        wallet_stats = {}
        for wallet, perf in self.wallet_performance.items():
            multiplier = get_wallet_multiplier(wallet)
            wallet_stats[wallet[:10] + "..."] = {
                "win_rate": f"{perf.win_rate:.0%}",
                "recent_win_rate": f"{perf.recent_win_rate:.0%}",
                "trades": perf.trades_total,
                "pnl": f"${perf.total_pnl_usd:.2f}",
                "decaying": perf.is_decaying,
                "multiplier": f"{multiplier}x",
            }

        return {
            "strategy": "copy_trading",
            "signals_received": self.stats["signals_received"],
            "orders_created": self.stats["orders_created"],
            "orders_skipped": self.stats["orders_skipped"],
            "multi_signals": self.stats["multi_signals"],
            "wallets": wallet_stats,
        }
