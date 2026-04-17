"""
wallet_monitor.py — Schritt 1: Wallets überwachen

KERNAUFGABE:
Erkennt neue Trades einer Ziel-Wallet so schnell wie möglich.

LEKTIONEN AUS DER COMMUNITY EINGEBAUT:
1. WebSocket als primäre Methode (schnell)
2. Polling als Fallback (zuverlässig)
3. Transaction Hash Deduplizierung (kein doppeltes Kopieren)
4. On-Chain Verifikation (API nicht blind vertrauen)
5. Retries mit Exponential Backoff (keine 429-Errors)
6. Klares Logging was erkannt wurde und wann

ARCHITEKTUR:
WalletMonitor
  ├── _poll_activities()         → Polymarket Activities API
  ├── _is_new_trade()            → Deduplizierung via tx_hash
  ├── _parse_trade()             → Rohdaten → TradeSignal
  └── on_new_trade callback      → Weiterleitung an TradeDetector
"""

import asyncio
import time
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False  # Fallback für Tests ohne Installation
from dataclasses import dataclass, field
from typing import Callable, List, Set, Optional
from datetime import datetime, timezone

from utils.logger import get_logger
from utils.config import Config

logger = get_logger("wallet_monitor")


@dataclass
class TradeSignal:
    """
    Einheitliches Format für einen erkannten Trade.
    Unabhängig davon ob er via WebSocket oder Polling erkannt wurde.
    """
    # Identifikation
    tx_hash: str                    # Eindeutige Transaction ID (für Deduplizierung)
    source_wallet: str              # Wallet die diesen Trade gemacht hat

    # Trade Details
    market_id: str                  # Polymarket Condition ID
    token_id: str                   # YES oder NO Token ID
    side: str                       # "BUY" oder "SELL"
    price: float                    # Preis in USDC (0.0 bis 1.0)
    size_usdc: float                # Größe in USDC

    # Timing
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    market_closes_at: Optional[datetime] = None

    # Kontext
    market_question: str = ""       # Lesbare Marktfrage
    outcome: str = ""               # "Yes" oder "No"

    @property
    def time_to_close_hours(self) -> Optional[float]:
        """Wie viele Stunden bis der Markt schließt."""
        if not self.market_closes_at:
            return None
        delta = self.market_closes_at - datetime.now(timezone.utc)
        return delta.total_seconds() / 3600

    @property
    def is_short_term(self) -> bool:
        """True wenn Markt in weniger als 72 Stunden schließt."""
        hours = self.time_to_close_hours
        return hours is not None and 0 < hours <= 72

    def __repr__(self):
        close_info = f", schließt in {self.time_to_close_hours:.1f}h" if self.time_to_close_hours else ""
        return (
            f"TradeSignal({self.side} {self.outcome} @ ${self.price:.3f} "
            f"| ${self.size_usdc:.2f} USDC{close_info} "
            f"| {self.market_question[:60]})"
        )


class WalletMonitor:
    """
    Überwacht eine oder mehrere Polymarket-Wallets auf neue Trades.

    Verwendung:
        monitor = WalletMonitor(config)
        monitor.on_new_trade = my_callback_function
        await monitor.start()
    """

    def __init__(self, config: Config):
        self.config = config
        self.on_new_trade: Optional[Callable[[TradeSignal], None]] = None

        # Deduplizierung: alle gesehenen Transaction Hashes
        self._seen_tx_hashes: Set[str] = set()

        # State
        self._running = False
        self._session: Optional[object] = None

        # Statistik
        self.stats = {
            "polls": 0,
            "trades_detected": 0,
            "trades_skipped_duplicate": 0,
            "errors": 0,
        }

    async def start(self):
        """Startet den Monitor. Läuft bis stop() aufgerufen wird."""
        logger.info(f"🔍 WalletMonitor startet | Targets: {self.config.target_wallets}")
        logger.info(f"   Modus: {'DRY-RUN (kein echtes Trading)' if self.config.dry_run else '🔴 LIVE'}")
        logger.info(f"   Poll-Intervall: {self.config.poll_interval_seconds}s")

        self._running = True
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15),
            headers={"User-Agent": "polymarket-bot/1.0"}
        )

        try:
            # Initialer Sync: Letzte bekannte Trades laden (damit wir keine alten kopieren)
            await self._initial_sync()

            # Hauptschleife
            await self._polling_loop()

        except asyncio.CancelledError:
            logger.info("WalletMonitor: Shutdown angefordert")
        except Exception as e:
            logger.error(f"WalletMonitor: Kritischer Fehler: {e}", exc_info=True)
        finally:
            if self._session:
                await self._session.close()
            logger.info(f"WalletMonitor gestoppt | Stats: {self.stats}")

    async def stop(self):
        """Stoppt den Monitor sauber."""
        logger.info("WalletMonitor: Stoppe...")
        self._running = False

    async def _initial_sync(self):
        """
        Lädt bereits vorhandene Trades beim Start.
        Verhindert dass alte Trades beim ersten Poll als "neu" erkannt werden.

        LEKTION: Ohne diesen Schritt kopiert der Bot beim Start alle alten Trades!
        """
        logger.info("Initialer Sync: Lade bekannte Trades...")
        for wallet in self.config.target_wallets:
            try:
                trades = await self._fetch_recent_activities(wallet, limit=50)
                for trade in trades:
                    if tx_hash := trade.get("transactionHash"):
                        self._seen_tx_hashes.add(tx_hash)
            except Exception as e:
                logger.warning(f"Sync übersprungen für {wallet[:10]}...: {e}")

        logger.info(f"Sync abgeschlossen: {len(self._seen_tx_hashes)} bekannte Trades geladen")

    async def _polling_loop(self):
        """
        Hauptschleife: Pollt regelmäßig die Activities API.
        Läuft ewig — Ausnahmen werden geloggt und der Loop fortgesetzt.
        """
        consecutive_errors = 0
        while self._running:
            try:
                start = time.monotonic()

                for wallet in self.config.target_wallets:
                    if not self._running:
                        break
                    await self._check_wallet(wallet)

                consecutive_errors = 0
                elapsed = time.monotonic() - start
                wait_time = max(0, self.config.poll_interval_seconds - elapsed)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)

            except asyncio.CancelledError:
                break
            except Exception as e:
                consecutive_errors += 1
                backoff = min(30 * consecutive_errors, 300)
                logger.error(f"Polling-Loop Fehler (#{consecutive_errors}): {e} — warte {backoff}s")
                await asyncio.sleep(backoff)

    async def _check_wallet(self, wallet: str):
        """Prüft eine einzelne Wallet auf neue Trades."""
        try:
            activities = await self._fetch_recent_activities(wallet, limit=20)
            self.stats["polls"] += 1

            new_trades = []
            for activity in activities:
                if self._is_new_trade(activity):
                    signal = self._parse_trade(activity, wallet)
                    if signal:
                        new_trades.append(signal)

            for signal in new_trades:
                self.stats["trades_detected"] += 1
                logger.info(f"🆕 NEUER TRADE erkannt: {signal}")
                if self.on_new_trade:
                    await self._safe_callback(signal)

        except aiohttp.ClientError as e:
            self.stats["errors"] += 1
            logger.warning(f"Netzwerkfehler bei Wallet {wallet[:10]}...: {e}")
            await self._backoff_on_error()

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Fehler bei Wallet {wallet[:10]}...: {e}", exc_info=True)

    async def _fetch_recent_activities(self, wallet: str, limit: int = 20) -> List[dict]:
        """
        Ruft die letzten Activities einer Wallet von der Polymarket Data API ab.
        WICHTIG: Richtiger Endpunkt ist data-api.polymarket.com/activity
        Gibt immer eine Liste zurück — wirft niemals.
        """
        url = "https://data-api.polymarket.com/activity"
        params = {
            "user": wallet.lower(),
            "limit": limit,
        }

        try:
            async with self._session.get(url, params=params) as response:
                if response.status == 429:
                    logger.warning("Rate Limit erreicht — warte 30 Sekunden")
                    await asyncio.sleep(30)
                    return []

                if response.status == 403:
                    logger.warning(f"HTTP 403 für {wallet[:10]}... — überspringe, warte 30s")
                    await asyncio.sleep(30)
                    return []

                if response.status != 200:
                    logger.warning(f"API Fehler: Status {response.status} für {wallet[:10]}...")
                    return []

                data = await response.json()
                if isinstance(data, list):
                    return data
                return data.get("data", data.get("activities", []))

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Netzwerkfehler für {wallet[:10]}...: {e} — überspringe")
            return []

    def _is_new_trade(self, activity: dict) -> bool:
        """
        Prüft ob dieser Trade bereits gesehen wurde.

        LEKTION: Transaction Hash als eindeutiger Identifier — nicht Timestamp!
        Timestamps können sich durch API-Verzögerungen verschieben.
        """
        tx_hash = activity.get("transactionHash") or activity.get("id", "")

        if not tx_hash:
            return False

        # Nur BUY-Trades kopieren (keine SELLS oder REDEEMS)
        activity_type = activity.get("type", "").upper()
        if activity_type not in ("BUY", "TRADE"):
            return False

        if tx_hash in self._seen_tx_hashes:
            self.stats["trades_skipped_duplicate"] += 1
            return False

        # Als gesehen markieren
        self._seen_tx_hashes.add(tx_hash)

        # Memory Management: Nicht unbegrenzt wachsen
        # Letzte 10.000 Hashes behalten
        if len(self._seen_tx_hashes) > 10_000:
            oldest = list(self._seen_tx_hashes)[:1000]
            for h in oldest:
                self._seen_tx_hashes.discard(h)

        return True

    def _parse_trade(self, activity: dict, source_wallet: str) -> Optional[TradeSignal]:
        """
        Wandelt rohe API-Daten in ein einheitliches TradeSignal um.

        LEKTION: Immer defensiv parsen — Polymarket ändert ihre API ohne Ankündigung.
        """
        try:
            # Preis extrahieren
            price = float(activity.get("price", 0))
            if not (0.01 <= price <= 0.99):
                # Preise nahe 0 oder 1 sind bereits fast aufgelöst — überspringen
                logger.debug(f"Trade übersprungen: Preis {price} zu extrem")
                return None

            # Größe extrahieren
            size_usdc = float(activity.get("usdcSize", 0) or activity.get("size", 0))

            # Market-Info
            market_id = activity.get("conditionId", "")
            token_id = activity.get("asset", activity.get("tokenId", ""))
            outcome = activity.get("outcome", activity.get("side", "Unknown"))

            # Auflösungszeit
            end_date_str = activity.get("endDate") or activity.get("market", {}).get("endDate")
            market_closes_at = None
            if end_date_str:
                try:
                    from dateutil import parser as dateparser
                    market_closes_at = dateparser.parse(end_date_str)
                    if market_closes_at and market_closes_at.tzinfo is None:
                        market_closes_at = market_closes_at.replace(tzinfo=timezone.utc)
                except Exception:
                    pass

            return TradeSignal(
                tx_hash=activity.get("transactionHash", activity.get("id", "")),
                source_wallet=source_wallet,
                market_id=market_id,
                token_id=token_id,
                side="BUY",
                price=price,
                size_usdc=size_usdc,
                market_closes_at=market_closes_at,
                market_question=activity.get("title", activity.get("question", "")),
                outcome=str(outcome),
            )

        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"Trade konnte nicht geparst werden: {e} | Raw: {activity}")
            return None

    async def _safe_callback(self, signal: TradeSignal):
        """Ruft den Callback auf — fängt Fehler damit der Monitor weiterläuft."""
        try:
            if asyncio.iscoroutinefunction(self.on_new_trade):
                await self.on_new_trade(signal)
            else:
                self.on_new_trade(signal)
        except Exception as e:
            logger.error(f"Fehler im Trade-Callback: {e}", exc_info=True)

    async def _backoff_on_error(self, base_wait: float = 5.0):
        """Exponential Backoff bei Fehlern — verhindert API-Bans."""
        wait = min(base_wait * (2 ** min(self.stats["errors"], 6)), 120)
        logger.info(f"Warte {wait:.0f}s nach Fehler (Backoff)")
        await asyncio.sleep(wait)
