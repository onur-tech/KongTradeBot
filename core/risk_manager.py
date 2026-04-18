"""
risk_manager.py — Schritt 4: Risiko-Kontrolle

KERNAUFGABE:
Entscheidet ob ein Trade ausgeführt werden darf.
Kill-Switch wenn Tages-Verlust überschritten wird.

LEKTIONEN AUS DER COMMUNITY:
- Tages-Verlustlimit als harte Grenze
- Max Trade-Größe begrenzen
- Sehr kurzfristige Märkte (<1h) überspringen
- Märkte die fast aufgelöst sind überspringen (Preis > 0.90)
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from typing import Optional, Dict

from utils.logger import get_logger
from utils.config import Config
from core.wallet_monitor import TradeSignal

logger = get_logger("risk_manager")

MAX_MARKET_BUDGET_PCT = 0.03  # Max 3% des Portfolios pro einzelnem Markt


@dataclass
class RiskDecision:
    """Ergebnis einer Risiko-Prüfung."""
    allowed: bool
    reason: str
    adjusted_size_usdc: float = 0.0


class RiskManager:
    """
    Prüft jeden potenziellen Trade gegen Risiko-Regeln.

    Wenn der Kill-Switch ausgelöst wird, werden KEINE weiteren Trades
    ausgeführt bis der Bot neu gestartet wird.
    """

    def __init__(self, config: Config):
        self.config = config
        self._kill_switch_active = False
        self._kill_switch_reason = ""

        # Tages-Tracking
        self._today = date.today()
        self._daily_loss_usd = 0.0
        self._daily_profit_usd = 0.0
        self._trades_today = 0

        # Markt-Budget-Tracking: investierter Betrag pro market_id heute
        self._market_investments: Dict[str, float] = {}

    @property
    def net_pnl_today(self) -> float:
        return self._daily_profit_usd - self._daily_loss_usd

    def evaluate(self, signal: TradeSignal) -> RiskDecision:
        """
        Hauptfunktion: Darf dieser Trade ausgeführt werden?

        Gibt RiskDecision zurück mit allowed=True/False und Begründung.
        """
        self._reset_if_new_day()

        # 1. Kill-Switch
        if self._kill_switch_active:
            return RiskDecision(
                allowed=False,
                reason=f"Kill-Switch aktiv: {self._kill_switch_reason}"
            )

        # 2. Tages-Verlustlimit
        if self._daily_loss_usd >= self.config.max_daily_loss_usd:
            self._activate_kill_switch(f"Tages-Verlustlimit erreicht: ${self._daily_loss_usd:.2f}")
            return RiskDecision(
                allowed=False,
                reason=f"Tages-Verlustlimit ${self.config.max_daily_loss_usd} erreicht"
            )

        # 3. Schließzeit: wenn API kein market_closes_at liefert → 48h annehmen
        time_to_close = signal.time_to_close_hours if signal.time_to_close_hours is not None else 48.0

        # 4. Markt zu kurz bis Auflösung (< 1 Stunde) oder bereits geschlossen
        if time_to_close < 1:
            return RiskDecision(
                allowed=False,
                reason=f"Markt schließt zu bald: {signal.time_to_close_hours:.1f}h"
            )

        # 5. Markt bereits fast aufgelöst (Preis zu extrem)
        if signal.price > 0.92 or signal.price < 0.08:
            return RiskDecision(
                allowed=False,
                reason=f"Preis zu extrem ({signal.price:.2f}) — Markt fast aufgelöst"
            )

        # 5b. Minimum Odds Filter: nur Trades zwischen 15% und 85%
        if signal.price < 0.15 or signal.price > 0.85:
            return RiskDecision(
                allowed=False,
                reason=f"Odds außerhalb 15-85% Range ({signal.price:.2f})"
            )

        # 5c. Trade Freshness Filter: Signal darf nicht älter als 5 Minuten sein
        detected_at = getattr(signal, "detected_at", None)
        if detected_at is not None:
            if detected_at.tzinfo is None:
                detected_at = detected_at.replace(tzinfo=timezone.utc)
            signal_age_seconds = (datetime.now(timezone.utc) - detected_at).total_seconds()
            if signal_age_seconds > 300:
                return RiskDecision(
                    allowed=False,
                    reason=f"Signal zu alt (>{signal_age_seconds/60:.1f} Min — max 5 Min)"
                )

        # 6. Nur kurzfristige Märkte (unsere Strategie: <72h)
        if time_to_close > 72:
            return RiskDecision(
                allowed=False,
                reason=f"Markt läuft zu lang: {signal.time_to_close_hours:.0f}h (max 72h)"
            )

        # 7. Trade-Größe berechnen (proportional + Limits)
        adjusted_size = self._calculate_size(signal.size_usdc)

        if adjusted_size < self.config.min_trade_size_usd:
            return RiskDecision(
                allowed=False,
                reason=f"Micro-Trade geskipped: ${adjusted_size:.2f} < MIN_TRADE_SIZE ${self.config.min_trade_size_usd:.2f}"
            )

        # 8. Max 3% Budget pro Markt (verhindert Überkonzentration in einem Markt)
        if signal.market_id:
            market_budget  = self.config.portfolio_budget_usd * MAX_MARKET_BUDGET_PCT
            already_in     = self._market_investments.get(signal.market_id, 0.0)
            remaining_budget = market_budget - already_in
            if remaining_budget <= 0:
                return RiskDecision(
                    allowed=False,
                    reason=(
                        f"Markt-Budget erschöpft: ${already_in:.2f}/${market_budget:.2f} "
                        f"bereits investiert (max {MAX_MARKET_BUDGET_PCT:.0%} Budget)"
                    )
                )
            if adjusted_size > remaining_budget:
                logger.info(
                    f"⚠️  Markt-Budget Limit: ${adjusted_size:.2f} → ${remaining_budget:.2f} "
                    f"(${already_in:.2f} bereits in diesem Markt)"
                )
                adjusted_size = remaining_budget
            if adjusted_size < self.config.min_trade_size_usd:
                return RiskDecision(
                    allowed=False,
                    reason=f"Micro-Trade geskipped: Markt-Budget Rest ${adjusted_size:.2f} < MIN_TRADE_SIZE ${self.config.min_trade_size_usd:.2f}"
                )

        fallback_note = " [Fallback 48h]" if signal.time_to_close_hours is None else ""
        logger.info(
            f"✅ Trade erlaubt | Größe: ${adjusted_size:.2f} | "
            f"Markt schließt in: {time_to_close:.1f}h{fallback_note} | "
            f"Preis: {signal.price:.3f}"
        )

        return RiskDecision(
            allowed=True,
            reason="Alle Checks bestanden",
            adjusted_size_usdc=adjusted_size
        )

    def record_market_investment(self, market_id: str, size_usdc: float):
        """Registriert eine ausgeführte Investment-Größe für das Markt-Budget-Tracking."""
        if market_id:
            self._market_investments[market_id] = (
                self._market_investments.get(market_id, 0.0) + size_usdc
            )

    def record_trade_result(self, pnl_usd: float):
        """
        Registriert das Ergebnis eines ausgeführten Trades.
        Muss aufgerufen werden wenn ein Markt aufgelöst wird.
        """
        self._reset_if_new_day()

        if pnl_usd >= 0:
            self._daily_profit_usd += pnl_usd
            logger.info(f"Trade Gewinn: +${pnl_usd:.2f} | Heute gesamt: {self.net_pnl_today:+.2f}")
        else:
            self._daily_loss_usd += abs(pnl_usd)
            logger.info(f"Trade Verlust: ${pnl_usd:.2f} | Heute Verlust: ${self._daily_loss_usd:.2f}")

            # Prüfen ob Kill-Switch ausgelöst werden soll
            if self._daily_loss_usd >= self.config.max_daily_loss_usd:
                self._activate_kill_switch(
                    f"Tages-Verlustlimit ${self.config.max_daily_loss_usd} überschritten"
                )

    def _calculate_size(self, whale_size_usdc: float) -> float:
        """
        Berechnet proportionale Trade-Größe.

        LEKTION: Nicht blind dieselben Dollarbeträge kopieren!
        Wenn Whale $10.000 setzt und du $1.000 hast → du setzt $50 (5%)
        """
        raw_size = whale_size_usdc * self.config.copy_size_multiplier
        # Auf Limits clippen
        return min(raw_size, self.config.max_trade_size_usd)

    def _activate_kill_switch(self, reason: str):
        """Aktiviert den Kill-Switch — stoppt alle weiteren Trades."""
        self._kill_switch_active = True
        self._kill_switch_reason = reason
        logger.warning(f"🛑 KILL-SWITCH AKTIVIERT: {reason}")
        logger.warning("Bot führt keine weiteren Trades aus. Neustart erforderlich.")

    def _reset_if_new_day(self):
        """Setzt Tages-Zähler zurück wenn neuer Tag begonnen hat."""
        today = date.today()
        if today != self._today:
            logger.info(
                f"Neuer Tag | PnL gestern: {self.net_pnl_today:+.2f} | "
                f"Trades: {self._trades_today}"
            )
            self._today = today
            self._daily_loss_usd = 0.0
            self._daily_profit_usd = 0.0
            self._trades_today = 0
            # Markt-Investments zurücksetzen
            self._market_investments.clear()
            # Kill-Switch täglich automatisch zurücksetzen
            if self._kill_switch_active:
                logger.info("Kill-Switch durch Tageswechsel zurückgesetzt")
                self._kill_switch_active = False
                self._kill_switch_reason = ""

    def status(self) -> dict:
        """Gibt aktuellen Risiko-Status zurück."""
        return {
            "kill_switch": self._kill_switch_active,
            "kill_switch_reason": self._kill_switch_reason,
            "daily_loss_usd": self._daily_loss_usd,
            "daily_profit_usd": self._daily_profit_usd,
            "net_pnl_today": self.net_pnl_today,
            "trades_today": self._trades_today,
            "limit_usd": self.config.max_daily_loss_usd,
            "remaining_usd": max(0, self.config.max_daily_loss_usd - self._daily_loss_usd),
        }
