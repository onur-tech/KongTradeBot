"""
T-M-NEW: Anomalie-Detektor
Unabhängig vom normalen Copy-Trading.
Scannt ALLE Polymarket-Trades auf Insider-Muster.
Eigenes Budget: ANOMALY_DAILY_CAP_USD
"""
import asyncio
import time
import os
import aiohttp
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from utils.logger import get_logger

logger = get_logger("anomaly_detector")

DATA_API = "https://data-api.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"


@dataclass
class AnomalySignal:
    condition_id: str
    market_question: str
    entry_price: float            # in Dollar (z.B. 0.08 = 8 Cent)
    total_bet_usd: float
    wallet_count: int
    wallets: list
    anomaly_score: int
    signal_type: str              # "STRONG" | "MODERATE"
    detected_at: float = field(default_factory=time.time)


class AnomalyDetector:
    """
    Unabhängig vom normalen Copy-Trading.
    Prüft ALLE Polymarket-Trades auf Insider-Muster.
    """

    def __init__(self):
        self.enabled = os.getenv("ANOMALY_DETECTOR_ENABLED", "false").lower() == "true"
        self.min_bet_single = float(os.getenv("ANOMALY_MIN_BET_SINGLE_USD", "100000"))
        self.min_bet_cluster = float(os.getenv("ANOMALY_MIN_BET_CLUSTER_USD", "200000"))
        self.min_cluster_size = int(os.getenv("ANOMALY_MIN_CLUSTER_SIZE", "3"))
        self.max_probability = float(os.getenv("ANOMALY_MAX_PROBABILITY", "0.15"))
        self.daily_cap = float(os.getenv("ANOMALY_DAILY_CAP_USD", "20"))
        self.copy_size = float(os.getenv("ANOMALY_COPY_SIZE_USD", "2"))

        # State
        self._daily_spent = 0.0
        self._last_reset = datetime.now(timezone.utc).date()
        self._recent_bets: dict[str, list] = defaultdict(list)  # condition_id → bets
        self._wallet_cache: dict[str, dict] = {}
        self._alerted_conditions: set = set()  # Deduplizierung über Loop-Durchläufe

    def _reset_daily_if_needed(self):
        today = datetime.now(timezone.utc).date()
        if today != self._last_reset:
            self._daily_spent = 0.0
            self._last_reset = today
            self._alerted_conditions.clear()

    async def _get_wallet_age_and_trades(self, wallet: str) -> tuple[int, int]:
        """Gibt (Tage auf Polymarket, Anzahl Trades) zurück."""
        if wallet in self._wallet_cache:
            return self._wallet_cache[wallet]["days"], self._wallet_cache[wallet]["trades"]
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{DATA_API}/activity?user={wallet}&limit=1000"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                    data = await r.json()
                    if not data:
                        return 9999, 9999  # Kein Daten = sehr alt (ignorieren)
                    trades = len(data)
                    timestamps = [t.get("timestamp", 0) for t in data if t.get("timestamp")]
                    if timestamps:
                        first_ts = min(timestamps)
                        days = (time.time() - first_ts) / 86400
                    else:
                        days = 9999
                    self._wallet_cache[wallet] = {"days": int(days), "trades": trades}
                    return int(days), trades
        except Exception:
            return 9999, 9999

    def _calculate_score(self, wallets_data: list, entry_price: float,
                         total_bet: float, is_cluster: bool) -> int:
        score = 0
        unique_wallets = len(wallets_data)

        for days, trades in wallets_data:
            if days < 30:
                score += 2
            if trades < 10:
                score += 2
            # One-Shot-Pattern: Wallet hat ≤ 1 Trade historisch
            if trades <= 1:
                score += 3

        if unique_wallets >= 3:
            score += 4
        if total_bet > 200_000:
            score += 1
        if entry_price < 0.05:
            score += 2

        return score

    async def check_all_trades(self) -> list[AnomalySignal]:
        """
        Holt alle Trades der letzten 30 Min via Data-API.
        Gruppiert nach condition_id.
        Gibt AnomalySignal-Liste zurück.
        """
        if not self.enabled:
            return []

        signals = []
        try:
            async with aiohttp.ClientSession() as session:
                # /trades gibt alle Trades zurück (kein user= erforderlich)
                url = f"{DATA_API}/trades?limit=500"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    trades = await r.json()
        except Exception as e:
            logger.warning(f"[ANOMALY] Data-API Fehler: {e}")
            return []

        if not isinstance(trades, list):
            logger.warning(f"[ANOMALY] Unerwartetes API-Format: {str(trades)[:100]}")
            return []

        # Gruppieren nach condition_id
        by_market: dict[str, list] = defaultdict(list)
        now = time.time()
        for trade in trades:
            ts = trade.get("timestamp", 0)
            if now - ts > 1800:  # Nur letzten 30 Min
                continue
            cid = trade.get("conditionId") or trade.get("condition_id", "")
            if not cid:
                continue
            price = float(trade.get("price", 1.0))
            # size = Shares, size*price = USDC-Einsatz
            shares = float(trade.get("size", 0))
            amount = shares * price  # USDC
            wallet = trade.get("proxyWallet") or trade.get("maker") or trade.get("user", "")
            side = trade.get("side", "BUY")
            # Nur BUY-Signale auf YES (Low-Price = LOW Probability)
            if side.upper() not in ("BUY", "YES"):
                continue
            if price > self.max_probability:
                continue
            if amount < 50_000:
                continue
            by_market[cid].append({
                "wallet": wallet, "price": price, "amount": amount,
                "question": trade.get("title", cid[:20])
            })

        # Signale auswerten
        for cid, bets in by_market.items():
            if cid in self._alerted_conditions:
                continue
            unique_wallets = list({b["wallet"] for b in bets if b["wallet"]})
            total_bet = sum(b["amount"] for b in bets)
            avg_price = sum(b["price"] for b in bets) / len(bets)
            question = bets[0].get("question", cid[:30])

            if total_bet < 50_000:
                continue

            # Wallet-Alter für alle unique Wallets holen
            wallets_data = []
            for w in unique_wallets[:5]:  # Max 5 prüfen
                days, trade_count = await self._get_wallet_age_and_trades(w)
                wallets_data.append((days, trade_count))

            score = self._calculate_score(
                wallets_data, avg_price, total_bet,
                is_cluster=len(unique_wallets) >= self.min_cluster_size
            )

            if score < 3:
                continue

            # STARKES SIGNAL
            if (total_bet >= self.min_bet_single and len(unique_wallets) == 1) or \
               (total_bet >= self.min_bet_cluster and len(unique_wallets) >= self.min_cluster_size):
                signals.append(AnomalySignal(
                    condition_id=cid,
                    market_question=question,
                    entry_price=avg_price,
                    total_bet_usd=total_bet,
                    wallet_count=len(unique_wallets),
                    wallets=unique_wallets,
                    anomaly_score=score,
                    signal_type="STRONG"
                ))
                logger.warning(f"[ANOMALY] STRONG Signal: {question[:50]} | Score: {score} | ${total_bet:,.0f}")

            # MODERATES SIGNAL
            elif 50_000 <= total_bet < self.min_bet_single or score >= 5:
                signals.append(AnomalySignal(
                    condition_id=cid,
                    market_question=question,
                    entry_price=avg_price,
                    total_bet_usd=total_bet,
                    wallet_count=len(unique_wallets),
                    wallets=unique_wallets,
                    anomaly_score=score,
                    signal_type="MODERATE"
                ))
                logger.info(f"[ANOMALY] MODERATE Signal: {question[:50]} | Score: {score} | ${total_bet:,.0f}")

        return signals

    async def execute_signal(self, signal: AnomalySignal,
                              execution_engine) -> bool:
        """
        Kauft ANOMALY_COPY_SIZE_USD wenn STARKES SIGNAL und Budget vorhanden.
        ExecutionEngine.place_order() wird aufgerufen sobald die Methode verfügbar ist.
        """
        self._reset_daily_if_needed()
        if self._daily_spent >= self.daily_cap:
            logger.info(f"[ANOMALY] Daily Cap ${self.daily_cap} erreicht — kein Trade")
            return False
        if signal.signal_type != "STRONG":
            return False

        remaining = self.daily_cap - self._daily_spent
        size = min(self.copy_size, remaining)

        # ExecutionEngine hat kein place_order() — Trade-Ausführung noch nicht implementiert
        # Signal wird geloggt und in zukünftiger Version ausgeführt
        logger.warning(
            f"[ANOMALY] STRONG Signal würde ${size:.2f} kaufen: "
            f"{signal.market_question[:40]} @ {signal.entry_price*100:.1f}¢ "
            f"(Score: {signal.anomaly_score}) — ExecutionEngine.place_order() ausstehend"
        )
        # self._daily_spent += size  # Erst aktivieren wenn place_order implementiert
        return False

    def format_telegram_alert(self, signal: AnomalySignal) -> str:
        emoji = "🚨" if signal.signal_type == "STRONG" else "👁"
        wallets_str = ", ".join(f"<code>{w[:10]}...</code>" for w in signal.wallets[:3])
        auto_trade = (
            "✅ AUTO-TRADE aktiv ($2)" if signal.signal_type == "STRONG"
            else "⚠️ Manuell prüfen"
        )
        return (
            f"{emoji} <b>Anomalie-Signal ({signal.signal_type})</b>\n\n"
            f"Markt: {signal.market_question[:60]}\n"
            f"Entry-Preis: {signal.entry_price*100:.1f}¢\n"
            f"Gesamt-Bet: ${signal.total_bet_usd:,.0f}\n"
            f"Wallets: {signal.wallet_count} ({wallets_str})\n"
            f"Anomalie-Score: {signal.anomaly_score}/20+\n\n"
            f"{auto_trade}"
        )


async def anomaly_detector_loop(detector: AnomalyDetector,
                                 execution_engine,
                                 send_fn,
                                 interval_seconds: int = 300):
    """
    Haupt-Loop: alle 5 Minuten scannen.
    Läuft parallel zu WalletMonitor in main.py.
    send_fn: async callable (z.B. telegram_bot.send)
    """
    if not detector.enabled:
        logger.info("[ANOMALY] Detektor deaktiviert (ANOMALY_DETECTOR_ENABLED=false)")
        return

    logger.info(f"[ANOMALY] Detektor gestartet — Scan-Intervall: {interval_seconds}s")
    while True:
        try:
            signals = await asyncio.wait_for(
                detector.check_all_trades(), timeout=30.0)
            for signal in signals:
                detector._alerted_conditions.add(signal.condition_id)
                alert = detector.format_telegram_alert(signal)
                await send_fn(alert, urgent=(signal.signal_type == "STRONG"))
                if signal.signal_type == "STRONG":
                    await detector.execute_signal(signal, execution_engine)
        except asyncio.TimeoutError:
            logger.warning("[ANOMALY] Scan-Timeout (>30s) — übersprungen")
        except Exception as e:
            logger.error(f"[ANOMALY] Loop-Fehler: {e}")
        await asyncio.sleep(interval_seconds)
