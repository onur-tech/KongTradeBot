"""
fill_tracker.py — WebSocket-basiertes Fill-Tracking für Polymarket

Verbindet sich mit dem Polymarket User Channel (wss://ws-subscriptions-clob.polymarket.com/ws/user)
und promoted Orders von "pending" → "open" bei CONFIRMED,
bzw. löscht sie bei FAILED/CANCELLATION.

Fix für GitHub Issue #303: User-Channel benötigt L2-Credentials (via
deriveApiKey()), nicht Builder-Credentials. Falsche Creds → silent
disconnect ohne Fehlermeldung.

Status-Flow:
    PLACEMENT  → Order beim Matching-Engine registriert (pending)
    MATCHED    → Order gematcht, noch nicht on-chain (pending)
    MINED      → On-chain transaction submitted (pending)
    CONFIRMED  → On-chain bestätigt → open_positions promoten
    FAILED     → Order gescheitert → aus pending entfernen
    RETRYING   → Transaktion wird wiederholt → pending belassen
    CANCELLATION → Order gecancelt → aus open_positions entfernen
"""

import asyncio
import json
import time
import aiohttp
from typing import Callable, Dict, Optional, Awaitable
from dataclasses import dataclass

from utils.logger import get_logger
from utils.config import Config

logger = get_logger("fill_tracker")

WS_USER_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/user"
PING_INTERVAL = 10        # Sekunden
PENDING_TTL = 60          # Sekunden bis pending_order per REST gecheckt wird
MAX_RECONNECT_DELAY = 30  # Sekunden
NO_EVENT_WARN_SECS = 30   # Warnung wenn nach Connect keine Events kommen


@dataclass
class PendingOrder:
    order_id: str
    token_id: str
    condition_id: str     # market_id = condition_id für WebSocket-Subscription
    size_usdc: float
    price: float
    submitted_at: float   # time.time()


class FillTracker:
    """
    Horcht auf den Polymarket User-WebSocket-Channel und
    meldet Fills/Rejections an den ExecutionEngine zurück.
    """

    def __init__(self, config: Config):
        self.config = config
        self._pending: Dict[str, PendingOrder] = {}
        self._subscribed_conditions: set = set()
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._running = False
        self._last_event_time: float = 0.0

        # Callbacks — werden von ExecutionEngine registriert
        self._on_matched: Optional[Callable[[str], Awaitable[None]]] = None
        self._on_failed: Optional[Callable[[str], Awaitable[None]]] = None
        self._on_cancelled: Optional[Callable[[str], Awaitable[None]]] = None

    def register_callbacks(
        self,
        on_matched: Callable[[str], Awaitable[None]],
        on_failed: Callable[[str], Awaitable[None]],
        on_cancelled: Callable[[str], Awaitable[None]],
    ):
        self._on_matched = on_matched
        self._on_failed = on_failed
        self._on_cancelled = on_cancelled

    def add_pending(self, order: PendingOrder):
        """Registriert eine neu abgeschickte Order als pending."""
        self._pending[order.order_id] = order
        logger.debug(f"Pending: {order.order_id[:12]}... | ${order.size_usdc:.2f}")

    def get_all_condition_ids(self) -> list:
        """Alle condition_ids der aktuell pendenden Orders."""
        return list({o.condition_id for o in self._pending.values()})

    async def run(self):
        """Hauptloop — reconnectet bei Fehler mit exponential backoff."""
        self._running = True
        reconnect_delay = 1.0

        while self._running:
            try:
                await self._connect_and_listen()
                reconnect_delay = 1.0
            except Exception as e:
                logger.warning(f"WebSocket-Fehler: {e} — Reconnect in {reconnect_delay:.0f}s")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, MAX_RECONNECT_DELAY)

    async def stop(self):
        self._running = False
        if self._ws and not self._ws.closed:
            await self._ws.close()
        if self._session and not self._session.closed:
            await self._session.close()

    async def _connect_and_listen(self):
        """Stellt WebSocket-Verbindung her und verarbeitet Events."""
        self._session = aiohttp.ClientSession()
        try:
            async with self._session.ws_connect(
                WS_USER_URL,
                heartbeat=PING_INTERVAL,
                timeout=aiohttp.ClientWSTimeout(ws_receive=30),
            ) as ws:
                self._ws = ws
                self._last_event_time = time.time()
                logger.info("✅ FillTracker WebSocket verbunden")

                await self._subscribe(ws)

                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self._listen(ws))
                    tg.create_task(self._ttl_checker())

        finally:
            if self._session and not self._session.closed:
                await self._session.close()
            self._session = None

    def _derive_l2_creds(self) -> Optional[dict]:
        """
        Leitet L2-Credentials via ClobClient.derive_api_key() ab.
        Fix für Issue #303: User-Channel benötigt L2-Creds, nicht Builder-Creds.
        """
        try:
            from py_clob_client.client import ClobClient
            client = ClobClient(
                host=getattr(self.config, 'clob_host', 'https://clob.polymarket.com'),
                key=self.config.private_key,
                chain_id=137,
                signature_type=1,
                funder=self.config.polymarket_address,
            )
            creds = client.derive_api_key()
            key_prefix = (creds.api_key or "")[:6]
            logger.info(f"FillTracker L2-Creds abgeleitet: apiKey={key_prefix}...")
            return {
                "apiKey": creds.api_key,
                "secret": creds.api_secret,
                "passphrase": creds.api_passphrase,
            }
        except Exception as e:
            logger.warning(f"L2-Creds ableiten fehlgeschlagen: {e} — fallback auf Config-Creds")
            return self._get_config_creds()

    def _get_config_creds(self) -> Optional[dict]:
        """Fallback: Creds direkt aus Config lesen."""
        try:
            return {
                "apiKey": self.config.api_key,
                "secret": self.config.api_secret,
                "passphrase": self.config.api_passphrase,
            }
        except AttributeError:
            return None

    async def _subscribe(self, ws: aiohttp.ClientWebSocketResponse):
        """Sendet Auth + initiale Market-Subscription mit L2-Credentials."""
        creds = self._derive_l2_creds()
        if not creds:
            logger.warning("FillTracker: Keine API-Creds — WebSocket ohne Auth (Issue #303!)")
            return

        condition_ids = self.get_all_condition_ids()
        msg: dict = {
            "auth": creds,
            "type": "user",
        }
        if condition_ids:
            msg["markets"] = condition_ids
            self._subscribed_conditions.update(condition_ids)

        await ws.send_json(msg)
        logger.info(f"User-Channel subscribed auf {len(condition_ids)} Märkte")

    async def _subscribe_new_conditions(self, new_ids: list):
        """Subscribed dynamisch auf neue Märkte ohne Reconnect."""
        if not self._ws or self._ws.closed:
            return
        to_add = [cid for cid in new_ids if cid not in self._subscribed_conditions]
        if not to_add:
            return
        await self._ws.send_json({"markets": to_add, "operation": "subscribe"})
        self._subscribed_conditions.update(to_add)
        logger.debug(f"Dynamisch subscribed: {to_add}")

    async def _listen(self, ws: aiohttp.ClientWebSocketResponse):
        """Event-Listener-Loop mit Auth-Diagnose."""
        connect_time = time.time()
        warned_no_events = False

        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                self._last_event_time = time.time()
                warned_no_events = False
                try:
                    data = json.loads(msg.data)
                    event_type = data.get("event_type") or data.get("type", "")
                    # Log all event types for diagnostics
                    if event_type not in ("", None):
                        logger.debug(f"WS Event: type={event_type} status={data.get('status','?')} id={str(data.get('id',''))[:12]}")
                    await self._handle_event(data)
                except Exception as e:
                    logger.debug(f"Event-Parse-Fehler: {e}")
            elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                logger.info("WebSocket geschlossen — reconnecting...")
                break
            else:
                # Check for auth-problem silence (Issue #303)
                if not warned_no_events and (time.time() - connect_time) > NO_EVENT_WARN_SECS:
                    logger.warning(
                        "Keine Events empfangen seit Connect — möglicherweise "
                        "Auth-Problem (siehe GitHub Issue #303). L2-Creds prüfen!"
                    )
                    warned_no_events = True

    async def _handle_event(self, event: dict):
        """
        Verarbeitet ein einzelnes WebSocket-Event.

        Status-Flow:
            PLACEMENT  → ignore (Order noch nicht gematcht)
            MATCHED    → pending belassen (noch nicht on-chain)
            MINED      → pending belassen (on-chain submitted, nicht confirmed)
            CONFIRMED  → in open_positions promoten
            FAILED     → aus pending entfernen
            RETRYING   → pending belassen
            CANCELLATION → aus open_positions entfernen
        """
        event_type = event.get("event_type") or event.get("type", "")
        status = event.get("status", "").upper()
        order_id = event.get("id", "")

        if event_type == "trade":
            if status == "CONFIRMED":
                await self._fire(order_id, "matched")
            elif status == "FAILED":
                await self._fire(order_id, "failed")
            elif status in ("MATCHED", "MINED", "PLACEMENT", "RETRYING"):
                if order_id in self._pending:
                    logger.debug(f"Order {order_id[:12]}... Status={status} — pending belassen")
            else:
                logger.debug(f"Unbekannter Trade-Status '{status}' für {order_id[:12]}")

        elif event_type == "order":
            order_type = event.get("type", "").upper()
            if order_type == "CANCELLATION":
                await self._fire(order_id, "cancelled")

    async def _fire(self, order_id: str, event: str):
        """Löst Callback aus wenn order_id in pending_orders."""
        if order_id not in self._pending:
            return
        pending = self._pending.pop(order_id)
        logger.info(f"Fill-Event '{event}' für {order_id[:12]}... | ${pending.size_usdc:.2f}")

        try:
            if event == "matched" and self._on_matched:
                await self._on_matched(order_id)
            elif event == "failed" and self._on_failed:
                await self._on_failed(order_id)
            elif event == "cancelled" and self._on_cancelled:
                await self._on_cancelled(order_id)
        except Exception as e:
            logger.error(f"Callback-Fehler bei '{event}': {e}")

    async def _ttl_checker(self):
        """Prüft pending_orders auf TTL-Überschreitung und checkt per REST."""
        while self._running:
            await asyncio.sleep(10)
            now = time.time()
            expired = [
                oid for oid, o in self._pending.items()
                if now - o.submitted_at > PENDING_TTL
            ]
            for order_id in expired:
                await self._check_pending_via_rest(order_id)

            new_conditions = self.get_all_condition_ids()
            await self._subscribe_new_conditions(new_conditions)

    async def _check_pending_via_rest(self, order_id: str):
        """Fallback: REST-Abfrage für Orders die keinen WebSocket-Event hatten."""
        try:
            url = f"{getattr(self.config, 'clob_host', 'https://clob.polymarket.com')}/orders/{order_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        status = data.get("status", "").upper()
                        if status in ("CONFIRMED", "MATCHED", "FILLED"):
                            await self._fire(order_id, "matched")
                        elif status in ("CANCELLED", "REJECTED", "FAILED"):
                            await self._fire(order_id, "failed")
                        elif status in ("MINED", "RETRYING", "LIVE"):
                            logger.debug(f"REST: {order_id[:12]}... Status={status} — pending belassen")
                        else:
                            logger.warning(
                                f"TTL überschritten, unbekannter REST-Status '{status}' "
                                f"für {order_id[:12]}... → failed"
                            )
                            await self._fire(order_id, "failed")
        except Exception as e:
            logger.warning(f"REST-Check fehlgeschlagen für {order_id[:12]}: {e}")
            self._pending.pop(order_id, None)
