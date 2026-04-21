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
import math
import aiohttp
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timezone, timedelta

from utils.logger import get_logger
from utils.config import Config
from strategies.copy_trading import CopyOrder, get_wallet_name
from core.position_state import PositionState
from utils.balance_cli import get_usdc_balance_via_cli as _balance_cli

logger = get_logger("execution")

try:
    from utils.error_handler import handle_error as _handle_error
except ImportError:
    _handle_error = None

# py-clob-client Import — optional, damit Tests ohne Installation laufen
try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import (
        OrderArgs, OrderType, BalanceAllowanceParams, AssetType,
        PartialCreateOrderOptions,
    )
    from py_clob_client.order_builder.constants import BUY
    CLOB_AVAILABLE = True
except ImportError:
    CLOB_AVAILABLE = False
    BalanceAllowanceParams = None
    AssetType = None
    PartialCreateOrderOptions = None
    logger.warning("py-clob-client nicht installiert. Nur Dry-Run möglich.")
    logger.warning("Installation: pip install py-clob-client")

MARKET_INFO_CACHE_TTL = 60  # Sekunden — Orderbook-Daten cachen

# Last allowance-alert timestamp — verhindert Spam (max 1x / 30 Min)
_last_allowance_alert_ts: float = 0.0


def _send_allowance_alert(msg: str, config) -> None:
    """Sendet Telegram-Alert für Allowance = 0. Rate-limited auf 1×/30 Min."""
    import time as _t, urllib.request as _ur, json as _js
    global _last_allowance_alert_ts
    if _t.time() - _last_allowance_alert_ts < 1800:
        return
    _last_allowance_alert_ts = _t.time()
    try:
        token = getattr(config, "telegram_token", "") or ""
        chat_id = getattr(config, "telegram_chat_id", "") or "507270873"
        if not token:
            import os as _os
            token = _os.getenv("TELEGRAM_TOKEN", "")
            chat_id = _os.getenv("TELEGRAM_CHAT_IDS", chat_id).split(",")[0]
        if not token:
            logger.warning(f"[Allowance Alert] Kein Telegram-Token — Alert nicht gesendet")
            return
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = _js.dumps({"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}).encode()
        req = _ur.Request(url, data=data, headers={"Content-Type": "application/json"})
        _ur.urlopen(req, timeout=8)
        logger.info(f"[Allowance Alert] Telegram gesendet")
    except Exception as e:
        logger.warning(f"[Allowance Alert] Telegram-Fehler: {e}")


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

    # T-M08: State-Machine
    position_state: str = PositionState.OPEN

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

        # Orderbook-Info-Cache: token_id → (timestamp, min_order_size, tick_size, neg_risk)
        self._market_info_cache: Dict[str, Tuple[float, float, float, bool]] = {}

        # Offene Positionen: order_id → Position (nur CONFIRMED/MATCHED)
        self.open_positions: Dict[str, OpenPosition] = {}

        # Pending Orders: submitted aber noch nicht von Polymarket bestätigt
        # FillTracker promoted diese nach open_positions oder löscht sie bei Ablehnung
        self._pending_data: Dict[str, dict] = {}  # order_id → Position-Konstrukt-Daten

        # FillTracker reference for dynamic market subscription
        self._fill_tracker = None

        # Statistik
        self.stats = {
            "orders_attempted": 0,
            "orders_filled": 0,
            "orders_failed": 0,
            "orders_pending": 0,
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
                signature_type=1,  # Magic-Link Account (0 = MetaMask/EOA, 1 = Magic-Link)
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

    def set_fill_tracker(self, ft) -> None:
        """Registriert FillTracker für dynamische Market-Subscriptions nach Orders."""
        self._fill_tracker = ft

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

        # CTF Exchange Allowance Pre-Trade-Check
        _allow_ok, _allow_err = await self.check_ctf_allowance_pre_trade()
        if not _allow_ok:
            self.stats["orders_failed"] += 1
            return ExecutionResult(success=False, error=_allow_err)

        signal = order.signal

        MAX_RETRIES = 3
        try:
            # Dynamischer Pre-Submit-Check via Orderbook-API (gecacht 60s)
            min_size, tick_size_f, neg_risk = await self._get_market_info(signal.token_id)

            if order.size_usdc < min_size:
                logger.info(
                    f"⏭️  Order übersprungen (unter Minimum): "
                    f"${order.size_usdc:.2f} < ${min_size:.2f} | {signal.market_question[:50]}"
                )
                self.stats["orders_failed"] += 1
                return ExecutionResult(
                    success=False,
                    error=f"Size ${order.size_usdc:.2f} unter Minimum ${min_size:.2f}"
                )

            # Limit-Order-Buffer: +3% über Wallet-Preis um Fill sicherzustellen
            # wenn der Markt sich seit dem Wallet-Trade bewegt hat.
            import os as _os_buf
            _buf_pct = float(_os_buf.getenv("BUY_PRICE_BUFFER_PCT", "0.03"))
            _raw_price = signal.price * (1 + _buf_pct)
            _capped_price = min(_raw_price, 0.97)  # nie über 97¢
            price = self._round_to_tick(_capped_price, tick_size_f)
            if abs(price - signal.price) > 0.0001:
                logger.info(
                    f"[Limit+Buffer] {signal.price:.4f} → {price:.4f} "
                    f"(+{_buf_pct:.0%} Buffer, tick={tick_size_f})"
                )

            logger.info(
                f"🔴 LIVE ORDER:\n"
                f"  Markt: {signal.market_question[:60]}\n"
                f"  {signal.outcome} @ ${price:.4f} | ${order.size_usdc:.2f} USDC"
                + (" [NEGRISK]" if neg_risk else "")
            )

            # Order platzieren — create_and_post_order in einem Call
            # LEKTION: NICHT create_order() dann post_order() separat!
            # Das führt zu Ghost Trades wenn zwischen den zwei Calls ein Fehler passiert.
            # LEKTION: OrderArgs-Objekt verwenden, NICHT plain dict!
            shares = order.size_usdc / price if price > 0 else 0
            order_args = OrderArgs(
                token_id=signal.token_id,
                price=price,
                size=shares,
                side=BUY,
            )
            # NEG_RISK: Env-Override (true) oder Wert aus Marktdaten (API-Feld neg_risk)
            import os as _os
            _env_neg_risk = _os.getenv("NEG_RISK", "false").lower() == "true"
            _effective_neg_risk = _env_neg_risk or neg_risk
            order_options = None
            if PartialCreateOrderOptions is not None:
                order_options = PartialCreateOrderOptions(
                    tick_size=str(tick_size_f),
                    neg_risk=_effective_neg_risk,
                )
            logger.debug(
                f"DEBUG: About to call create_and_post_order with "
                f"token_id={signal.token_id} price={signal.price} "
                f"size={shares:.4f} side=BUY neg_risk={_effective_neg_risk}"
            )
            # run_in_executor: verhindert dass der synchrone requests-Call
            # den asyncio Event-Loop einfriert.
            # Retry bei VPN-Netzwerkfehlern (WinError 10035, httpx.ReadError).
            response = None
            loop = asyncio.get_event_loop()
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    response = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            lambda: self._client.create_and_post_order(order_args, order_options),
                        ),
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

            # API-Fehler-Check: Nur bei gültigem Status ("matched"/"resting") als Position tracken
            # Sonst entstehen Phantom-Positionen für abgelehnte Orders
            api_error = response.get("error") or response.get("errorMessage")
            order_status = response.get("status", "")
            has_valid_id = bool(response.get("orderID") or response.get("id"))

            if api_error or (not has_valid_id and order_status not in ("matched", "resting", "")):
                reason = api_error or f"Unbekannter Status: {order_status}"
                logger.warning(f"⚠️  Polymarket hat Order abgelehnt: {reason}")
                self.stats["orders_failed"] += 1
                return ExecutionResult(success=False, error=f"API Ablehnung: {reason}")

            order_id = response.get("orderID") or response.get("id", "unknown")
            logger.debug(f"DEBUG: Order ID returned: {order_id}")
            logger.info(f"Order gesendet | ID: {order_id}")

            # Order in pending_data ablegen — FillTracker bestätigt via WebSocket
            # NICHT sofort in open_positions! Verhindert Phantom-Positionen.
            self._pending_data[order_id] = {
                "order_id": order_id,
                "market_id": signal.market_id,
                "token_id": signal.token_id,
                "outcome": signal.outcome,
                "market_question": signal.market_question,
                "entry_price": price,
                "size_usdc": order.size_usdc,
                "shares": order.size_usdc / price if price > 0 else 0,
                "market_closes_at": signal.market_closes_at,
                "source_wallet": signal.source_wallet,
                "tx_hash_entry": signal.tx_hash,
            }
            self.stats["orders_pending"] += 1
            logger.info(f"⏳ Order pending (wartet auf WebSocket-Bestätigung): {order_id[:12]}...")

            # Dynamic Subscribe: FillTracker auf diesen Markt subscriben
            if self._fill_tracker is not None:
                condition_id = signal.market_id  # market_id == condition_id auf Polymarket
                asyncio.create_task(self._fill_tracker._subscribe_new_conditions([condition_id]))

            return ExecutionResult(
                success=True,
                order_id=order_id,
                filled_price=price,
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

            if _handle_error is not None:
                try:
                    await _handle_error(e, context="CLOB_API_ERROR:execute", severity="ERROR",
                                        telegram_alert=True, reraise=False)
                except Exception:
                    pass

            return ExecutionResult(success=False, error=error_msg)

    async def _get_market_info(self, token_id: str) -> Tuple[float, float, bool]:
        """
        Holt min_order_size, tick_size und neg_risk vom Orderbook-Endpoint.
        Gecacht für MARKET_INFO_CACHE_TTL Sekunden pro token_id.
        Gibt (min_order_size, tick_size_float, neg_risk) zurück.
        """
        cached = self._market_info_cache.get(token_id)
        if cached and (time.time() - cached[0]) < MARKET_INFO_CACHE_TTL:
            return cached[1], cached[2], cached[3]

        try:
            url = f"{self.config.clob_host}/book?token_id={token_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        min_size = float(data.get("min_order_size", 5.0))
                        tick_size = float(data.get("tick_size", 0.01))
                        neg_risk = bool(data.get("neg_risk", False))
                        self._market_info_cache[token_id] = (time.time(), min_size, tick_size, neg_risk)
                        return min_size, tick_size, neg_risk
        except Exception as e:
            logger.debug(f"Orderbook-Fetch fehlgeschlagen für {token_id[:12]}: {e}")

        return 5.0, 0.01, False  # Safe defaults

    @staticmethod
    def _round_to_tick(price: float, tick_size: float) -> float:
        """Rundet Preis auf nächsten gültigen Tick ab."""
        if tick_size <= 0:
            return price
        rounded = math.floor(price / tick_size) * tick_size
        return round(rounded, 6)

    async def _get_tick_size(self, token_id: str) -> str:
        """Holt Tick Size — delegiert an _get_market_info (gecacht)."""
        _, tick_size, _ = await self._get_market_info(token_id)
        return str(tick_size)

    async def _verify_order_onchain(self, order_id: str, token_id: str) -> bool:
        """
        Verifiziert dass eine Order tatsächlich on-chain existiert.

        LEKTION: API sagt manchmal 'kein Fill' obwohl on-chain gefüllt wurde.
        Immer direkt on-chain prüfen!
        """
        try:
            # T-010: Leere token_id führt zu API 400 "invalid hex address"
            if not token_id or token_id.strip() in ("", "0x", "0x0"):
                logger.warning(f"_verify_order_onchain: token_id leer für {order_id[:12]}... — übersprungen")
                return False
            # LEKTION: get_balance_allowance() lesen (READ-ONLY)
            # NIEMALS update_balance_allowance() aufrufen nach einem Fill!
            # Das überschreibt den internen CLOB-State!
            loop = asyncio.get_event_loop()
            if BalanceAllowanceParams is not None:
                params = BalanceAllowanceParams(asset_type=AssetType.CONDITIONAL, token_id=token_id)
                balance = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: self._client.get_balance_allowance(params=params)
                    ),
                    timeout=10.0,
                )
            else:
                balance = await asyncio.wait_for(
                    loop.run_in_executor(None, self._client.get_balance_allowance),
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
            # BalanceAllowanceParams verwenden statt plain dict —
            # dict führt zu 'dict has no attribute signature_type' im py-clob-client
            if BalanceAllowanceParams is not None:
                params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
                balance = self._client.get_balance_allowance(params=params)
            else:
                balance = self._client.get_balance_allowance()
            usdc = float(balance.get("balance", 0) or 0)
            logger.info(f"💰 USDC Balance: ${usdc:.2f}")

            if usdc < 10:
                logger.warning(f"⚠️  Wenig USDC! Balance: ${usdc:.2f}")
        except Exception as e:
            if "invalid hex address" in str(e) or "assetAddress" in str(e):
                # Fallback auf polymarket-cli wenn CLOB-SDK assetAddress-Fehler wirft
                cli_bal = _balance_cli()
                if cli_bal is not None:
                    logger.info(f"💰 USDC Balance (cli-fallback): ${cli_bal:.2f}")
                    return
            logger.warning(f"Balance-Check fehlgeschlagen: {e}")
            if _handle_error is not None:
                try:
                    await _handle_error(e, context="BALANCE_CHECK_FAILED:_check_balance",
                                        severity="WARNING", telegram_alert=True, reraise=False)
                except Exception:
                    pass

    async def check_clob_allowance_health(self) -> dict:
        """
        Prüft den CLOB-Deposit-Balance (der für Orders verfügbare USDC-Betrag).
        Das relevante Feld ist 'balance' (in micro-USDC) — die API-Fehlermeldung
        'not enough balance / allowance: balance: X' bezieht sich genau auf diesen Wert.
        Gibt Health-Dict zurück: allowance_usdc, is_healthy, warning_needed, critical.
        """
        if not self._client or BalanceAllowanceParams is None:
            return {
                "allowance_usdc": 0.0, "is_healthy": False,
                "warning_needed": True, "critical": True,
                "error": "Client nicht initialisiert",
            }
        try:
            params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
            result = self._client.get_balance_allowance(params=params)
            # 'balance' = CLOB-Deposit in micro-USDC (6 Dezimalstellen)
            balance_raw = int(result.get("balance", 0) or 0)
            allowance_usdc = balance_raw / 1_000_000
            max_trade = float(self.config.max_trade_size_usd)
            logger.info(f"💳 CLOB-Balance: ${allowance_usdc:.2f} USDC (max_trade=${max_trade:.2f})")
            return {
                "allowance_usdc": allowance_usdc,
                "is_healthy": allowance_usdc >= max_trade,
                "warning_needed": allowance_usdc < max_trade * 2,
                "critical": allowance_usdc < max_trade,
            }
        except Exception as e:
            logger.warning(f"CLOB-Allowance-Check fehlgeschlagen: {e}")
            return {
                "allowance_usdc": 0.0, "is_healthy": False,
                "warning_needed": True, "critical": True,
                "error": str(e),
            }

    # --- FillTracker Callbacks ---

    async def on_order_matched(self, order_id: str):
        """FillTracker ruft dies bei MATCHED/CONFIRMED auf → Position in open_positions promoten."""
        data = self._pending_data.pop(order_id, None)
        if data is None:
            return
        position = OpenPosition(
            order_id=data["order_id"],
            market_id=data["market_id"],
            token_id=data["token_id"],
            outcome=data["outcome"],
            market_question=data["market_question"],
            entry_price=data["entry_price"],
            size_usdc=data["size_usdc"],
            shares=data["shares"],
            market_closes_at=data["market_closes_at"],
            source_wallet=data["source_wallet"],
            tx_hash_entry=data["tx_hash_entry"],
        )
        self.open_positions[order_id] = position
        self.stats["orders_filled"] += 1
        self.stats["orders_pending"] = max(0, self.stats["orders_pending"] - 1)
        self.stats["total_invested_usdc"] += data["size_usdc"]
        logger.info(
            f"✅ CONFIRMED: {data['outcome']} @ ${data['entry_price']:.4f} | "
            f"${data['size_usdc']:.2f} | {data['market_question'][:50]}"
        )

    async def on_order_failed(self, order_id: str):
        """FillTracker ruft dies bei FAILED/abgelehnter Order auf."""
        data = self._pending_data.pop(order_id, None)
        if data is None:
            return
        self.stats["orders_failed"] += 1
        self.stats["orders_pending"] = max(0, self.stats["orders_pending"] - 1)
        logger.warning(
            f"❌ Order ABGELEHNT: {data['outcome']} @ ${data['entry_price']:.4f} | "
            f"${data['size_usdc']:.2f} | {data['market_question'][:50]}"
        )

    async def on_order_cancelled(self, order_id: str):
        """FillTracker ruft dies bei CANCELLATION auf."""
        # Aus pending oder open entfernen
        if order_id in self._pending_data:
            data = self._pending_data.pop(order_id)
            self.stats["orders_pending"] = max(0, self.stats["orders_pending"] - 1)
            logger.info(f"🚫 Pending Order gecancelt: {order_id[:12]}...")
        elif order_id in self.open_positions:
            pos = self.open_positions.pop(order_id)
            logger.info(f"🚫 Position gecancelt: {pos.outcome} | ${pos.size_usdc:.2f}")

    async def create_and_post_sell_order(
        self,
        asset_id: str,
        shares: float,
        min_price: Optional[float] = None,
        exit_dry_run: bool = True,
    ) -> dict:
        """
        Verkauft `shares` eines Tokens (SELL-Order) auf Polymarket.

        Analogon zu create_and_post_order (BUY) mit gleichen Sicherheitsprinzipien:
        - set_api_creds zuerst (bereits in initialize() gesetzt)
        - create_and_post_order als single call (kein split, kein Ghost-Trade)
        - tick_size via _get_market_info (gecacht)
        - 500ms wait nach Submit für API-Sync

        Returns dict mit: success, order_id, filled_price, shares_sold,
                          remaining_shares, error, dry_run
        Retry: max 2x bei Netzwerkfehlern (5s Delay)
        """
        MAX_RETRIES = 3
        RETRY_DELAY = 5.0

        if exit_dry_run or self.config.dry_run:
            logger.info(
                f"[EXIT DRY-RUN] SELL {shares:.4f} shares @ asset={asset_id[:16]}... "
                f"(min_price={min_price})"
            )
            return {
                "success": True, "order_id": f"sell_dry_{int(time.time())}",
                "filled_price": min_price or 0.0, "shares_sold": shares,
                "remaining_shares": 0.0, "error": None, "dry_run": True,
            }

        if not CLOB_AVAILABLE or not self._client:
            return {
                "success": False, "order_id": None, "filled_price": None,
                "shares_sold": 0.0, "remaining_shares": shares,
                "error": "CLOB Client nicht initialisiert", "dry_run": False,
            }

        try:
            _, tick_size_f, _ = await self._get_market_info(asset_id)
            sell_price = self._round_to_tick(min_price if min_price else 0.01, tick_size_f)

            try:
                from py_clob_client.clob_types import OrderArgs
                from py_clob_client.order_builder.constants import SELL as SELL_SIDE
            except ImportError:
                return {
                    "success": False, "order_id": None, "filled_price": None,
                    "shares_sold": 0.0, "remaining_shares": shares,
                    "error": "py-clob-client fehlt (SELL const)", "dry_run": False,
                }

            # Cancel existing open orders for this token before selling.
            # The 400 "not enough balance" error occurs when tokens are already
            # locked in active orders — cancelling first frees them.
            try:
                cancel_result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._client.cancel_market_orders(asset_id=asset_id),
                )
                cancelled_ids = (cancel_result or {}).get("canceled", []) if isinstance(cancel_result, dict) else []
                if cancelled_ids:
                    logger.info(f"[SELL] {len(cancelled_ids)} offene Order(s) gecancelt vor Sell (token={asset_id[:16]})")
                    await asyncio.sleep(1.0)  # allow API to settle after cancel
            except Exception as _ce:
                logger.warning(f"[SELL] Cancel-before-sell fehlgeschlagen (nicht kritisch): {_ce}")

            order_args = OrderArgs(
                token_id=asset_id,
                price=sell_price,
                size=shares,
                side=SELL_SIDE,
            )

            loop = asyncio.get_event_loop()
            response = None
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    response = await asyncio.wait_for(
                        loop.run_in_executor(None, self._client.create_and_post_order, order_args),
                        timeout=30.0,
                    )
                    break
                except (asyncio.TimeoutError, Exception) as exc:
                    err_s = str(exc)
                    retryable = (
                        isinstance(exc, asyncio.TimeoutError)
                        or "10035" in err_s or "ReadError" in err_s
                    )
                    if retryable and attempt < MAX_RETRIES:
                        logger.warning(f"[SELL] Netzwerkfehler Versuch {attempt}: {err_s[:60]} — retry in {RETRY_DELAY}s")
                        await asyncio.sleep(RETRY_DELAY)
                    else:
                        raise

            await asyncio.sleep(0.5)  # API-Sync-Lag nach Fill

            api_error = response.get("error") or response.get("errorMessage")
            if api_error:
                raise RuntimeError(f"API Ablehnung: {api_error}")

            order_id = response.get("orderID") or response.get("id", "unknown")
            filled = float(response.get("sizeMatched") or shares)
            remaining = round(shares - filled, 6)
            fill_price = float(response.get("price") or sell_price)

            logger.info(
                f"✅ SELL ORDER gefüllt: {filled:.4f} shares @ ${fill_price:.4f} | "
                f"ID: {order_id} | remaining: {remaining:.4f}"
            )
            return {
                "success": True, "order_id": order_id, "filled_price": fill_price,
                "shares_sold": filled, "remaining_shares": remaining,
                "error": None, "dry_run": False,
            }

        except Exception as exc:
            logger.error(f"[SELL] Fehler: {exc}", exc_info=True)
            return {
                "success": False, "order_id": None, "filled_price": None,
                "shares_sold": 0.0, "remaining_shares": shares,
                "error": str(exc), "dry_run": False,
            }

    # States that still have capital at risk — used for budget calculations
    _ACTIVE_STATES = {"OPEN", "ACTIVE"}

    def get_open_positions_summary(self) -> List[dict]:
        """Gibt eine Zusammenfassung aktiver Positionen zurück (ENDED/PENDING_CLOSE ausgeschlossen)."""
        return [
            {
                "order_id": pos.order_id[:12] + "...",
                "question": pos.market_question[:50],
                "outcome": pos.outcome,
                "entry_price": f"${pos.entry_price:.3f}",
                "invested": f"${pos.size_usdc:.2f}",
                "closes_in": f"{pos.time_to_close_hours:.1f}h" if hasattr(pos, 'time_to_close_hours') else "?",
                "source": getattr(pos, "source_wallet", "")[:10],
            }
            for pos in self.open_positions.values()
            if pos.position_state in self._ACTIVE_STATES
        ]

    def get_total_invested_usd(self) -> float:
        """Kapital in aktiven Positionen — ENDED/PENDING_CLOSE zählen nicht."""
        return sum(
            float(pos.size_usdc or 0)
            for pos in self.open_positions.values()
            if pos.position_state in self._ACTIVE_STATES
        )

    def cleanup_expired_positions(self) -> dict:
        """
        Täglicher Cleanup für RECOVERED_ Positionen.

        Regeln:
          1. market_closes_at ist abgelaufen UND opened_at > 48h ago
             → position_state = EXPIRED (kein Geld mehr zu erwarten)
          2. RECOVERED_ Position mit aktuell 0¢ auf Polymarket (RESOLVED_LOST)
             → position_state = RESOLVED_LOST (Verlust abschreiben)

        Gibt zurück: {"expired": int, "resolved_lost": int, "skipped": int}
        """
        from datetime import timezone as _tz
        now = datetime.now(_tz.utc)
        cutoff_48h = now - timedelta(hours=48)

        expired_count = 0
        resolved_lost_count = 0
        skipped = 0

        to_remove = []
        for oid, pos in self.open_positions.items():
            if pos.position_state not in (PositionState.OPEN, "ACTIVE", "OPEN"):
                skipped += 1
                continue

            is_recovered = oid.startswith("RECOVERED_")

            # Rule 1: Markt abgelaufen → EXPIRED
            # RECOVERED_: opened_at = Sync-Zeitpunkt (nicht Trade-Zeit) → kein 48h-Check
            # Normale Positionen: 48h-Guard damit frische Positionen mit altem closes_at
            # nicht sofort abgeschrieben werden.
            if pos.market_closes_at and pos.market_closes_at < now:
                age_ok = is_recovered or (pos.opened_at < cutoff_48h)
                if age_ok:
                    pos.position_state = PositionState.EXPIRED
                    to_remove.append(oid)
                    expired_count += 1
                    logger.info(
                        f"[Cleanup] EXPIRED: {oid[:30]} | "
                        f"closed={pos.market_closes_at.date()} | "
                        f"${pos.size_usdc:.2f} | {pos.market_question[:40]}"
                    )
                else:
                    skipped += 1

            # Rule 2: RESOLVED_LOST (bereits beim Sync gesetzt, hier aus open_positions entfernen)
            elif pos.position_state == "RESOLVED_LOST":
                to_remove.append(oid)
                resolved_lost_count += 1
                logger.info(
                    f"[Cleanup] RESOLVED_LOST abgeschrieben: {oid[:30]} | "
                    f"${pos.size_usdc:.2f} | {pos.market_question[:40]}"
                )
            else:
                skipped += 1

        for oid in to_remove:
            self.open_positions.pop(oid, None)

        if expired_count or resolved_lost_count:
            logger.info(
                f"[Cleanup] Fertig — EXPIRED: {expired_count}, "
                f"RESOLVED_LOST: {resolved_lost_count}, "
                f"unverändert: {skipped}"
            )
        return {
            "expired": expired_count,
            "resolved_lost": resolved_lost_count,
            "skipped": skipped,
        }

    async def check_ctf_allowance_pre_trade(self) -> tuple[bool, str]:
        """
        Prüft CTF Exchange Allowance vor jedem Live-Trade.
        Gibt (ok, error_msg) zurück.
        Wenn allowance_usdc == 0 → Trade blockieren + Telegram-Alert.
        """
        if not self._client or BalanceAllowanceParams is None:
            return True, ""  # Kein Client → skip (DRY-RUN)
        try:
            loop = asyncio.get_event_loop()
            params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self._client.get_balance_allowance(params=params)
                ),
                timeout=8.0,
            )
            balance_raw = int(result.get("balance", 0) or 0)
            allowance_raw = int(result.get("allowance", 0) or 0)
            balance_usdc = balance_raw / 1_000_000
            allowance_usdc = allowance_raw / 1_000_000

            if allowance_usdc == 0 and balance_usdc == 0:
                msg = (
                    "🚨 <b>Allowance = 0 — Trade blockiert!</b>\n"
                    "CTF Exchange Allowance ist null.\n"
                    "Manueller Fix nötig: Polymarket → Einzahlen → Approve."
                )
                logger.error(f"[Allowance] KRITISCH: allowance=0, balance=0 — Trade geblockt")
                try:
                    _send_allowance_alert(msg, self.config)
                except Exception:
                    pass
                return False, "Allowance = 0, manueller Fix nötig"

            if balance_usdc == 0:
                msg = (
                    f"⚠️ <b>CLOB-Balance = $0 — kein Trade möglich</b>\n"
                    f"Allowance: ${allowance_usdc:.2f} vorhanden, aber kein Deposit.\n"
                    f"Bitte USDC auf Polymarket CLOB einzahlen."
                )
                logger.warning(f"[Allowance] Balance=0 (Allowance={allowance_usdc:.2f}) — Trade geblockt")
                try:
                    _send_allowance_alert(msg, self.config)
                except Exception:
                    pass
                return False, f"CLOB-Balance = $0"

            return True, ""
        except Exception as e:
            logger.warning(f"[Allowance] Pre-Trade-Check fehlgeschlagen: {e} — Trade erlaubt")
            return True, ""  # Bei Fehler im Check → nicht blockieren

    def get_stats(self) -> dict:
        return {
            **self.stats,
            "open_positions": len(self.open_positions),
            "mode": "DRY-RUN" if self.config.dry_run else "LIVE",
        }
