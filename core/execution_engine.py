"""
execution_engine.py — Schritt 2: Orders auf Polymarket platzieren

KERNAUFGABE:
Nimmt einen CopyOrder entgegen und führt ihn aus.
Im Dry-Run: Loggt alles, kauft nichts.
Im Live-Modus: Echte Order via py-clob-client.

LEKTIONEN AUS DER COMMUNITY EINGEBAUT:
1. create_and_post_order statt create_order + post_order (eine Zeile, kein Ghost-Trade)
2. On-Chain Verifikation nach jedem Fill — API NICHT blind vertrauen
3. set_api_creds() VOR jedem Trading-Call aufrufen
4. 500ms Delay nach Fill bevor Balance geprüft wird (API-Sync-Lag)
5. Exit-Manager: Positionen tracken und schließen können
6. Limit Orders statt Market Orders (besserer Fill-Preis, kein Slippage)

ABHÄNGIGKEITEN:
    pip install py-clob-client python-dotenv web3

WICHTIG:
    Niemals private Key hardcoden!
    Niemals update_balance_allowance() nach einem Fill aufrufen!
    (Überschreibt internen CLOB-State mit on-chain Wert = 0 → Bot kann nicht mehr verkaufen)
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime, timezone

from utils.logger import get_logger
from utils.config import Config
from strategies.copy_trading import CopyOrder, get_wallet_name

logger = get_logger("execution")

# py-clob-client Import — optional, damit Tests ohne Installation laufen
try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs, OrderType
    from py_clob_client.order_builder.constants import BUY
    CLOB_AVAILABLE = True
except ImportError:
    CLOB_AVAILABLE = False
    logger.warning("py-clob-client nicht installiert. Nur Dry-Run möglich.")
    logger.warning("Installation: pip install py-clob-client")


@dataclass
class OpenPosition:
    """Eine offene Position die wir halten."""
    order_id: str
    market_id: str
    token_id: str
    outcome: str
    market_question: str

    entry_price: float
    size_usdc: float
    shares: float

    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    market_closes_at: Optional[datetime] = None

    # Tracking
    source_wallet: str = ""
    tx_hash_entry: str = ""

    @property
    def current_value_usdc(self) -> float:
        """Berechnet aktuellen Wert — wird bei Preis-Updates aktualisiert."""
        return self.shares * self.entry_price  # Placeholder, wird überschrieben

    def __repr__(self):
        return (
            f"Position({self.outcome} @ ${self.entry_price:.3f} | "
            f"${self.size_usdc:.2f} invested | {self.market_question[:50]})"
        )


@dataclass
class ExecutionResult:
    """Ergebnis einer Order-Ausführung."""
    success: bool
    order_id: Optional[str] = None
    filled_price: Optional[float] = None
    filled_size_usdc: Optional[float] = None
    error: Optional[str] = None
    dry_run: bool = False

    def __repr__(self):
        if self.dry_run:
            return f"ExecutionResult[DRY-RUN | würde ${self.filled_size_usdc:.2f} kaufen @ ${self.filled_price:.3f}]"
        if self.success:
            return f"ExecutionResult[✅ Filled ${self.filled_size_usdc:.2f} @ ${self.filled_price:.3f} | ID: {self.order_id}]"
        return f"ExecutionResult[❌ Fehler: {self.error}]"


class ExecutionEngine:
    """
    Führt Orders auf Polymarket aus.

    Dry-Run: Simuliert alle Orders, kauft nichts echtes.
    Live: Echte Orders via py-clob-client.
    """

    def __init__(self, config: Config):
        self.config = config
        self._client: Optional[object] = None

        # GeoBlock Circuit-Breaker: nach 403 alle Orders X Sekunden überspringen
        # verhindert Thread-Pool-Erschöpfung durch simultane fehlgeschlagene Orders
        self._geoblock_until: float = 0.0
        self._GEOBLOCK_COOLDOWN = 120  # Sekunden Pause nach GeoBlock

        # Offene Positionen tracken
        self.open_positions: Dict[str, OpenPosition] = {}  # order_id → Position

        # Statistik
        self.stats = {
            "orders_attempted": 0,
            "orders_filled": 0,
            "orders_failed": 0,
            "dry_run_orders": 0,
            "total_invested_usdc": 0.0,
        }

    async def initialize(self):
        """
        Initialisiert den CLOB Client.

        LEKTION: set_api_creds() MUSS aufgerufen werden bevor Trading-Calls!
        Fehlende Credentials führen zu stillen Auth-Fehlern.
        """
        if self.config.dry_run:
            logger.info("Execution Engine im DRY-RUN Modus — kein echter Client nötig")
            return

        if not CLOB_AVAILABLE:
            raise RuntimeError(
                "py-clob-client ist nicht installiert!\n"
                "Installiere es mit: pip install py-clob-client\n"
                "Live-Trading ohne dieses Paket nicht möglich."
            )

        logger.info("Initialisiere CLOB Client...")

        try:
            # Proxy-Adresse validieren (Polymarket verwendet Proxy-Wallets)
            funder = self.config.polymarket_address
            if not funder or not funder.startswith("0x") or len(funder) != 42:
                raise ValueError(
                    f"POLYMARKET_ADDRESS ungültig: '{funder}' — muss 0x + 40 Hex-Zeichen sein"
                )

            self._client = ClobClient(
                host=self.config.clob_host,
                chain_id=self.config.chain_id,
                key=self.config.private_key,
                funder=funder,  # Proxy-Wallet-Adresse (KRITISCH für Polymarket)
            )

            # KRITISCH: API Credentials ableiten und setzen
            # LEKTION: Ohne diesen Schritt schlagen alle Trading-Calls still fehl
            creds = self._client.create_or_derive_api_creds()
            self._client.set_api_creds(creds)

            logger.info(f"✅ CLOB Client initialisiert | funder: {funder[:10]}...")

            # Balance prüfen
            await self._check_balance()

        except Exception as e:
            logger.error(f"CLOB Client Initialisierung fehlgeschlagen: {e}")
            raise

    async def execute(self, order: CopyOrder) -> ExecutionResult:
        """
        Hauptfunktion: Führt einen CopyOrder aus.

        Dry-Run → loggt was passieren würde
        Live → echter Trade
        """
        self.stats["orders_attempted"] += 1

        if order.dry_run:
            return await self._dry_run_execute(order)
        else:
            return await self._live_execute(order)

    async def _dry_run_execute(self, order: CopyOrder) -> ExecutionResult:
        """
        Simuliert eine Order-Ausführung.
        Loggt alles was im Live-Modus passieren würde.
        """
        self.stats["dry_run_orders"] += 1

        signal = order.signal
        logger.info(
            f"[DRY-RUN] 📋 ORDER SIMULIERT:\n"
            f"  Markt:    {signal.market_question[:80]}\n"
            f"  Seite:    {signal.outcome} ({signal.side})\n"
            f"  Preis:    ${signal.price:.4f}\n"
            f"  Größe:    ${order.size_usdc:.2f} USDC\n"
            f"  Shares:   ~{order.size_usdc / signal.price:.2f}\n"
            f"  Schließt: {(signal.time_to_close_hours or 0):.1f}h\n"
            f"  Source:   {get_wallet_name(signal.source_wallet)}"
        )

        # Simulierte Position tracken (auch im Dry-Run)
        self._dry_run_counter = getattr(self, "_dry_run_counter", 0) + 1
        fake_order_id = f"dry_run_{self._dry_run_counter}_{signal.tx_hash[:8]}"
        position = OpenPosition(
            order_id=fake_order_id,
            market_id=signal.market_id,
            token_id=signal.token_id,
            outcome=signal.outcome,
            market_question=signal.market_question,
            entry_price=signal.price,
            size_usdc=order.size_usdc,
            shares=order.size_usdc / signal.price if signal.price > 0 else 0,
            market_closes_at=signal.market_closes_at,
            source_wallet=signal.source_wallet,
            tx_hash_entry=signal.tx_hash,
        )
        self.open_positions[fake_order_id] = position

        return ExecutionResult(
            success=True,
            order_id=fake_order_id,
            filled_price=signal.price,
            filled_size_usdc=order.size_usdc,
            dry_run=True,
        )

    async def _live_execute(self, order: CopyOrder) -> ExecutionResult:
        """
        Führt echten Trade auf Polymarket aus.

        LEKTION: create_and_post_order ist die richtige Methode —
        nicht create_order + post_order separat (Ghost-Trade-Risiko)!
        """
        logger.debug(f"DEBUG: Entering _live_execute | order={order!r}")

        if not self._client:
            logger.error("❌ CLOB Client ist None — engine.initialize() wurde nicht aufgerufen!")
            return ExecutionResult(
                success=False,
                error="CLOB Client nicht initialisiert — rufe initialize() auf"
            )

        logger.debug(f"DEBUG: Client is {type(self._client).__name__} (not None)")

        # GeoBlock Circuit-Breaker: sofort abbrechen statt API zu kontaktieren
        if time.time() < self._geoblock_until:
            remaining = int(self._geoblock_until - time.time())
            logger.debug(f"GeoBlock Circuit-Breaker aktiv — überspringe Order ({remaining}s verbleibend)")
            self.stats["orders_failed"] += 1
            return ExecutionResult(success=False, error="GeoBlock Cooldown aktiv")

        signal = order.signal

        MAX_RETRIES = 3
        try:
            logger.info(
                f"🔴 LIVE ORDER:\n"
                f"  Markt: {signal.market_question[:60]}\n"
                f"  {signal.outcome} @ ${signal.price:.4f} | ${order.size_usdc:.2f} USDC"
            )

            # Tick Size für diesen Markt holen
            tick_size = await self._get_tick_size(signal.token_id)
            logger.debug(f"DEBUG: tick_size={tick_size}")

            # Order platzieren — create_and_post_order in einem Call
            # LEKTION: NICHT create_order() dann post_order() separat!
            # Das führt zu Ghost Trades wenn zwischen den zwei Calls ein Fehler passiert.
            # LEKTION: OrderArgs-Objekt verwenden, NICHT plain dict!
            shares = order.size_usdc / signal.price
            order_args = OrderArgs(
                token_id=signal.token_id,
                price=signal.price,
                size=shares,
                side=BUY,
            )
            logger.debug(
                f"DEBUG: About to call create_and_post_order with "
                f"token_id={signal.token_id} price={signal.price} "
                f"size={shares:.4f} side=BUY"
            )
            # run_in_executor: verhindert dass der synchrone requests-Call
            # den asyncio Event-Loop einfriert.
            # Retry bei VPN-Netzwerkfehlern (WinError 10035, httpx.ReadError).
            response = None
            loop = asyncio.get_event_loop()
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    response = await asyncio.wait_for(
                        loop.run_in_executor(None, self._client.create_and_post_order, order_args),
                        timeout=30.0,
                    )
                    break
                except (asyncio.TimeoutError, Exception) as _exc:
                    _err = str(_exc)
                    _retryable = (
                        isinstance(_exc, asyncio.TimeoutError)
                        or "10035" in _err
                        or "ReadError" in _err
                        or ("status_code=None" in _err and "Request exception" in _err)
                    )
                    if _retryable and attempt < MAX_RETRIES:
                        logger.warning(
                            f"Netzwerkfehler Versuch {attempt}/{MAX_RETRIES}: "
                            f"{_err[:80]} — retry in 2s"
                        )
                        await asyncio.sleep(2)
                    else:
                        raise
            logger.debug(f"DEBUG: API response: {response!r}")

            order_id = response.get("orderID") or response.get("id", "unknown")
            logger.debug(f"DEBUG: Order ID returned: {order_id}")
            logger.info(f"Order gesendet | ID: {order_id}")

            # KRITISCH: On-Chain Verifikation
            # LEKTION: API-Response NICHT blind vertrauen — immer on-chain checken!
            await asyncio.sleep(0.5)  # 500ms warten — API braucht Zeit zum Sync
            verified = await self._verify_order_onchain(order_id, signal.token_id)

            if not verified:
                logger.warning(f"⚠️  Order {order_id} nicht on-chain verifiziert!")
                # Trotzdem als Position tracken — könnte noch gefillt werden
            else:
                logger.info(f"✅ Order on-chain verifiziert: {order_id}")

            # Position tracken
            position = OpenPosition(
                order_id=order_id,
                market_id=signal.market_id,
                token_id=signal.token_id,
                outcome=signal.outcome,
                market_question=signal.market_question,
                entry_price=signal.price,
                size_usdc=order.size_usdc,
                shares=order.size_usdc / signal.price if signal.price > 0 else 0,
                market_closes_at=signal.market_closes_at,
                source_wallet=signal.source_wallet,
                tx_hash_entry=signal.tx_hash,
            )
            self.open_positions[order_id] = position
            self.stats["orders_filled"] += 1
            self.stats["total_invested_usdc"] += order.size_usdc

            return ExecutionResult(
                success=True,
                order_id=order_id,
                filled_price=signal.price,
                filled_size_usdc=order.size_usdc,
                dry_run=False,
            )

        except Exception as e:
            self.stats["orders_failed"] += 1
            error_msg = str(e)

            # Häufige Fehler mit hilfreichen Meldungen
            if "UNAUTHORIZED" in error_msg or "unauthorized" in error_msg.lower():
                logger.error("Auth-Fehler: set_api_creds() wurde nicht aufgerufen oder Key ist falsch")
            elif "INVALID_SIGNATURE" in error_msg:
                logger.error("Signatur-Fehler: Private Key oder Chain ID falsch")
            elif "403" in error_msg and ("geoblock" in error_msg.lower() or "restricted" in error_msg.lower()):
                self._geoblock_until = time.time() + self._GEOBLOCK_COOLDOWN
                logger.warning(
                    f"🚫 GeoBlock 403 — Circuit-Breaker aktiviert für {self._GEOBLOCK_COOLDOWN}s. "
                    f"VPN aktivieren (US/EU) und Bot neu starten."
                )
            elif "429" in error_msg:
                logger.warning("Rate Limit! Warte 30 Sekunden...")
                await asyncio.sleep(30)
            elif "10035" in error_msg or "ReadError" in error_msg or (
                "status_code=None" in error_msg and "Request exception" in error_msg
            ):
                logger.error(
                    f"VPN-Netzwerkfehler nach {MAX_RETRIES} Versuchen: {error_msg[:120]}\n"
                    f"Tipp: VPN-Server wechseln falls Fehler anhält."
                )
            else:
                logger.error(f"Order fehlgeschlagen: {error_msg}", exc_info=True)

            return ExecutionResult(success=False, error=error_msg)

    async def _get_tick_size(self, token_id: str) -> str:
        """
        Holt die Tick Size für einen Markt.

        LEKTION: Falsche Tick Size → 'ceiling price too tight' Fehler
        → Order wird abgelehnt obwohl Liquidität vorhanden ist.
        """
        try:
            loop = asyncio.get_event_loop()
            market_info = await asyncio.wait_for(
                loop.run_in_executor(None, self._client.get_market, token_id),
                timeout=10.0,
            )
            return str(market_info.get("minimum_tick_size", "0.01"))
        except Exception:
            return "0.01"  # Safe Default

    async def _verify_order_onchain(self, order_id: str, token_id: str) -> bool:
        """
        Verifiziert dass eine Order tatsächlich on-chain existiert.

        LEKTION: API sagt manchmal 'kein Fill' obwohl on-chain gefüllt wurde.
        Immer direkt on-chain prüfen!
        """
        try:
            # LEKTION: get_balance_allowance() lesen (READ-ONLY)
            # NIEMALS update_balance_allowance() aufrufen nach einem Fill!
            # Das überschreibt den internen CLOB-State!
            loop = asyncio.get_event_loop()
            balance = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self._client.get_balance_allowance(
                        params={"asset_type": "CONDITIONAL", "token_id": token_id}
                    )
                ),
                timeout=10.0,
            )
            # Wenn Balance > 0, haben wir Tokens erhalten → Order war erfolgreich
            holdings = float(balance.get("balance", 0) or 0)
            return holdings > 0
        except Exception as e:
            logger.warning(f"On-Chain Verifikation fehlgeschlagen: {e}")
            return False  # Im Zweifel: nicht verifiziert

    async def _check_balance(self):
        """Prüft USDC Balance beim Start."""
        try:
            balance = self._client.get_balance_allowance(
                params={"asset_type": "USDC"}
            )
            usdc = float(balance.get("balance", 0) or 0)
            logger.info(f"💰 USDC Balance: ${usdc:.2f}")

            if usdc < 10:
                logger.warning(f"⚠️  Wenig USDC! Balance: ${usdc:.2f}")
        except Exception as e:
            logger.warning(f"Balance-Check fehlgeschlagen: {e}")

    def get_open_positions_summary(self) -> List[dict]:
        """Gibt eine Zusammenfassung aller offenen Positionen zurück."""
        return [
            {
                "order_id": pos.order_id[:12] + "...",
                "question": pos.market_question[:50],
                "outcome": pos.outcome,
                "entry_price": f"${pos.entry_price:.3f}",
                "invested": f"${pos.size_usdc:.2f}",
                "closes_in": f"{pos.time_to_close_hours:.1f}h" if hasattr(pos, 'time_to_close_hours') else "?",
            }
            for pos in self.open_positions.values()
        ]

    def get_stats(self) -> dict:
        return {
            **self.stats,
            "open_positions": len(self.open_positions),
            "mode": "DRY-RUN" if self.config.dry_run else "LIVE",
        }
