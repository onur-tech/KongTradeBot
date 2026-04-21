"""
MARKET_WS_MONITOR — Ersetzt Data-API-Polling (10s) durch WebSocket (< 1s)
Architektur: WS-Event → Data-API-Lookup → Signal → Buffer
Relevant für: Copy Trading auf kurzen Märkten, Sport, Politik
Weather: kein Vorteil (Signal kommt vom Forecast, nicht von Wallet)

════════════════════════════════════════════════════════════════════════════
ALT (WalletMonitor):
  Kanal  : wss://ws-subscriptions-clob.polymarket.com/ws/market
           Channel "live_activity_by_wallet" → subscribed auf bekannte Wallets
  Polling: data-api.polymarket.com/activity?user=<wallet> alle 10s (Fallback)
  Latenz : 0–10 s (Poll) oder ~50–200 ms (WS user-channel)
  Problem: Nur bekannte Wallets → neue Whale-Wallets werden übersehen
           WS user-channel ist ein undokumentiertes Feature und kann entfernt werden

NEU (MarketWSMonitor):
  Kanal  : wss://ws-subscriptions-clob.polymarket.com/ws/market
           Channel "market" → subscribed auf asset_ids (token_ids) unserer Märkte
  Latenz : < 1 s (Push bei jedem Trade)
  Vorteil: Entdeckt ALLE Wallets in beobachteten Märkten — auch unbekannte Whales
           Offiziell dokumentiert, stabil
  Nachteil: Eine Data-API-Lookup-Anfrage pro Whale-Event (~200 ms zusätzlich)
════════════════════════════════════════════════════════════════════════════
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Callable, List, Optional, Set

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from utils.logger import get_logger
from utils.config import Config
from core.wallet_monitor import TradeSignal

logger = get_logger("market_ws_monitor")

MARKET_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
DATA_API_TRADES = "https://data-api.polymarket.com/trades"
DATA_API_MARKETS = "https://data-api.polymarket.com/markets"


class MarketWSMonitor:
    """
    Überwacht eine Liste von asset_ids (token_ids) via Polymarket Market-WebSocket.
    Erkennt jeden Whale-Trade in diesen Märkten — egal von welcher Wallet.

    Verwendung:
        monitor = MarketWSMonitor(config)
        monitor.asset_ids = ["token_id_1", "token_id_2", ...]
        monitor.on_whale_trade = copy_trading.handle_signal  # TradeSignal callback
        await monitor.start()
    """

    WS_HEARTBEAT_S = 10
    MAX_RECONNECT_RETRIES = 5
    LOOKUP_TIMEOUT_S = 3.0

    def __init__(self, config: Config):
        self.config = config
        self.asset_ids: List[str] = []

        # Callback: wird mit einem TradeSignal aufgerufen — kompatibel zu WalletMonitor
        self.on_whale_trade: Optional[Callable] = None

        self._running = False
        self._session: Optional[aiohttp.ClientSession] = None
        self._seen_tx_hashes: Set[str] = set()
        self._ws_retries = 0

        self._min_whale = float(
            getattr(config, "min_whale_trade_size_usd", None)
            or getattr(config, "MIN_WHALE_SIZE_USD", 100.0)
        )

        self.stats = {
            "ws_events":        0,
            "whale_events":     0,
            "wallet_lookups":   0,
            "lookup_failures":  0,
            "signals_emitted":  0,
            "ws_reconnects":    0,
            "dedup_skips":      0,
        }

    # ── Public API ────────────────────────────────────────────────────────────

    async def start(self):
        """Startet den Monitor. Blockiert bis stop() aufgerufen wird."""
        if not WEBSOCKETS_AVAILABLE:
            logger.error("[MarketWS] 'websockets'-Package fehlt (pip install websockets)")
            return
        if not AIOHTTP_AVAILABLE:
            logger.error("[MarketWS] 'aiohttp'-Package fehlt (pip install aiohttp)")
            return
        if not self.asset_ids:
            logger.warning("[MarketWS] Keine asset_ids konfiguriert — nichts zu beobachten")
            return

        logger.info(
            f"[MarketWS] Start | {len(self.asset_ids)} Märkte | "
            f"MIN_WHALE=${self._min_whale:.0f} | WS: {MARKET_WS_URL}"
        )

        self._running = True
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={"User-Agent": "KongTradeBot/1.0"},
        )

        try:
            await self._reconnect_loop()
        except asyncio.CancelledError:
            logger.info("[MarketWS] Shutdown (CancelledError)")
        finally:
            if self._session and not self._session.closed:
                await self._session.close()
            logger.info(f"[MarketWS] Gestoppt | Stats: {self.stats}")

    async def stop(self):
        self._running = False

    def update_asset_ids(self, asset_ids: List[str]):
        """
        Dynamisch neue asset_ids setzen. Aktive WS-Session bleibt offen —
        Änderungen werden beim nächsten Reconnect wirksam.
        """
        old_count = len(self.asset_ids)
        self.asset_ids = list(dict.fromkeys(asset_ids))  # dedupliziert, Reihenfolge bleibt
        logger.info(
            f"[MarketWS] asset_ids aktualisiert: {old_count} → {len(self.asset_ids)}"
        )

    # ── Reconnect-Schleife ────────────────────────────────────────────────────

    async def _reconnect_loop(self):
        self._ws_retries = 0
        while self._running:
            try:
                await self._ws_session()
                self._ws_retries = 0
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self._ws_retries += 1
                self.stats["ws_reconnects"] += 1
                wait = min(2 ** self._ws_retries, 60)

                if self._ws_retries > self.MAX_RECONNECT_RETRIES:
                    logger.error(
                        f"[MarketWS] {self._ws_retries} Retries erschöpft — "
                        f"Pause 5 min vor nächstem Versuch"
                    )
                    await asyncio.sleep(300)
                    self._ws_retries = 0
                    continue

                logger.warning(
                    f"[MarketWS] Verbindungsfehler: {exc} — "
                    f"Reconnect in {wait}s (Retry {self._ws_retries}/{self.MAX_RECONNECT_RETRIES})"
                )
                await asyncio.sleep(wait)

    # ── WebSocket-Session ─────────────────────────────────────────────────────

    async def _ws_session(self):
        """Eine vollständige WS-Session: verbinden → subscriben → empfangen."""
        async with websockets.connect(
            MARKET_WS_URL,
            ping_interval=None,     # Eigener Heartbeat (Polymarket-Anforderung)
            ping_timeout=None,
            close_timeout=5,
        ) as ws:
            logger.info(f"[MarketWS] Verbunden: {MARKET_WS_URL}")

            subscribe_msg = {
                "type": "subscribe",
                "assets_ids": self.asset_ids,
            }
            await ws.send(json.dumps(subscribe_msg))
            logger.info(f"[MarketWS] Subscribed auf {len(self.asset_ids)} asset_ids")

            heartbeat_task = asyncio.create_task(self._heartbeat(ws))
            try:
                async for raw in ws:
                    if not self._running:
                        break
                    await self._handle_raw(raw)
            finally:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

    # ── Heartbeat ─────────────────────────────────────────────────────────────

    async def _heartbeat(self, ws):
        """Sendet alle WS_HEARTBEAT_S Sekunden einen Ping (Polymarket-Anforderung)."""
        while True:
            await asyncio.sleep(self.WS_HEARTBEAT_S)
            try:
                await ws.send(json.dumps({"type": "ping"}))
                logger.debug("[MarketWS] ♡ Ping gesendet")
            except Exception:
                break

    # ── Nachrichtenverarbeitung ───────────────────────────────────────────────

    async def _handle_raw(self, raw: str):
        try:
            payload = json.loads(raw)
        except Exception:
            return

        # Polymarket sendet entweder ein einzelnes Objekt oder eine Liste von Events
        events = payload if isinstance(payload, list) else [payload]

        for event in events:
            if not isinstance(event, dict):
                continue
            self.stats["ws_events"] += 1

            event_type = event.get("event_type", "")

            if event_type in ("subscribed", "pong", "heartbeat", "connected", ""):
                continue

            if event_type == "last_trade_price":
                await self._handle_trade_event(event)

    async def _handle_trade_event(self, event: dict):
        """Filtert Whale-Trades und startet den Wallet-Lookup."""
        try:
            size = float(event.get("size", 0) or 0)
        except (ValueError, TypeError):
            return

        if size < self._min_whale:
            return

        self.stats["whale_events"] += 1
        asset_id = event.get("asset_id", "")
        side = str(event.get("side", "BUY")).upper()

        try:
            price = float(event.get("price", 0))
        except (ValueError, TypeError):
            price = 0.0

        # Polymarket timestamps sind Sekunden (float oder int)
        try:
            event_ts = float(event.get("timestamp") or time.time())
        except (ValueError, TypeError):
            event_ts = time.time()

        logger.info(
            f"[MarketWS] Whale-Event: ${size:.0f} {side} @ {price:.3f} "
            f"| asset={asset_id[:20]}..."
        )

        signal = await self._lookup_wallet_and_build_signal(
            asset_id=asset_id,
            price=price,
            size_usdc=size,
            side=side,
            event_ts=event_ts,
        )

        if signal is None:
            return

        self.stats["signals_emitted"] += 1
        if self.on_whale_trade:
            try:
                if asyncio.iscoroutinefunction(self.on_whale_trade):
                    await self.on_whale_trade(signal)
                else:
                    self.on_whale_trade(signal)
            except Exception as exc:
                logger.error(f"[MarketWS] on_whale_trade Callback-Fehler: {exc}")

    # ── Data-API-Lookup ───────────────────────────────────────────────────────

    async def _lookup_wallet_and_build_signal(
        self,
        asset_id: str,
        price: float,
        size_usdc: float,
        side: str,
        event_ts: float,
    ) -> Optional[TradeSignal]:
        """
        Fragt data-api.polymarket.com/trades ab, um die Wallet-Adresse des
        soeben per WS gemeldeten Trades zu ermitteln.

        Matching-Strategie: jüngster Trade mit |price_diff| < 0.01.
        Fallback: absolut jüngster Eintrag.
        """
        self.stats["wallet_lookups"] += 1

        try:
            params = {"asset": asset_id, "limit": 5}
            async with self._session.get(
                DATA_API_TRADES,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.LOOKUP_TIMEOUT_S),
            ) as resp:
                if resp.status == 429:
                    logger.warning("[MarketWS] Rate-Limit bei Lookup — überspringe")
                    self.stats["lookup_failures"] += 1
                    return None
                if resp.status != 200:
                    logger.debug(f"[MarketWS] Data-API HTTP {resp.status} für {asset_id[:20]}")
                    self.stats["lookup_failures"] += 1
                    return None
                raw_data = await resp.json()
        except asyncio.TimeoutError:
            logger.debug(f"[MarketWS] Lookup-Timeout für {asset_id[:20]}")
            self.stats["lookup_failures"] += 1
            return None
        except Exception as exc:
            logger.warning(f"[MarketWS] Lookup-Fehler: {exc}")
            self.stats["lookup_failures"] += 1
            return None

        trades = raw_data if isinstance(raw_data, list) else raw_data.get("data", [])
        if not trades:
            self.stats["lookup_failures"] += 1
            return None

        # Besten Match finden
        best = None
        for t in trades:
            try:
                if abs(float(t.get("price", 0)) - price) < 0.01:
                    best = t
                    break
            except (ValueError, TypeError):
                continue
        if best is None:
            best = trades[0]  # Fallback: jüngster Trade

        # TX-Hash-Dedup — verhindert Doppel-Signale
        tx_hash = best.get("transactionHash") or best.get("id") or ""
        if tx_hash and tx_hash in self._seen_tx_hashes:
            self.stats["dedup_skips"] += 1
            return None
        if tx_hash:
            self._seen_tx_hashes.add(tx_hash)
            if len(self._seen_tx_hashes) > 10_000:
                oldest = list(self._seen_tx_hashes)[:1000]
                for h in oldest:
                    self._seen_tx_hashes.discard(h)

        wallet = (
            best.get("maker")
            or best.get("proxyWallet")
            or best.get("user")
            or best.get("address")
            or ""
        )

        condition_id = best.get("conditionId", "")
        outcome = str(best.get("outcome") or "Unknown")
        question = best.get("title") or best.get("question") or ""

        market_closes_at = None
        end_date_str = best.get("endDate") or ""
        if end_date_str:
            try:
                from dateutil import parser as dateparser
                market_closes_at = dateparser.parse(end_date_str)
                if market_closes_at and market_closes_at.tzinfo is None:
                    market_closes_at = market_closes_at.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        latency_ms = int((time.time() - event_ts) * 1000)
        logger.info(
            f"[MarketWS] Signal: {wallet[:12] if wallet else '?'}... "
            f"{side} {outcome} @ {price:.3f} | ${size_usdc:.0f} | "
            f"Latenz ~{latency_ms}ms"
        )

        return TradeSignal(
            tx_hash=tx_hash or f"mws_{asset_id[:8]}_{int(event_ts)}",
            source_wallet=wallet,
            market_id=condition_id,
            token_id=asset_id,
            side=side,
            price=price,
            size_usdc=size_usdc,
            market_closes_at=market_closes_at,
            market_question=question,
            outcome=outcome,
        )


# ── Hilfsfunktion: asset_ids aus aktiven Märkten laden ───────────────────────

async def load_active_asset_ids(
    session: "aiohttp.ClientSession",
    limit: int = 200,
) -> List[str]:
    """
    Lädt die token_ids aller aktiven Polymarket-Märkte (volume > 1000 USDC).
    Geeignet als Startpunkt für MarketWSMonitor.asset_ids.

    Für Production: besser auf spezifische Märkte eingrenzen (z.B. nur Sport/Politik).
    """
    url = "https://gamma-api.polymarket.com/markets"
    params = {"active": "true", "closed": "false", "limit": limit, "order": "volume", "ascending": "false"}
    asset_ids = []
    try:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return []
            markets = await resp.json()
        for m in markets:
            for token in m.get("tokens", []):
                tid = token.get("token_id") or token.get("tokenId") or token.get("id", "")
                if tid:
                    asset_ids.append(tid)
    except Exception as exc:
        logger.warning(f"[MarketWS] load_active_asset_ids Fehler: {exc}")
    logger.info(f"[MarketWS] {len(asset_ids)} asset_ids aus {limit} Märkten geladen")
    return asset_ids


# ── Standalone-Test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")

    class _MockConfig:
        min_whale_trade_size_usd = 50.0
        target_wallets = []
        dry_run = True

    async def _demo():
        import aiohttp as _aiohttp
        async with _aiohttp.ClientSession() as session:
            asset_ids = await load_active_asset_ids(session, limit=20)

        if not asset_ids:
            print("Keine asset_ids geladen — prüfe Netzwerk")
            return

        print(f"\nBeobachte {len(asset_ids)} asset_ids (ersten 5: {asset_ids[:5]})")
        print("Warte auf Whale-Trades (MIN_WHALE=$50)...\n")

        monitor = MarketWSMonitor(_MockConfig())
        monitor.asset_ids = asset_ids[:50]

        def _on_signal(sig: TradeSignal):
            print(f"  → SIGNAL: {sig}")

        monitor.on_whale_trade = _on_signal

        try:
            await asyncio.wait_for(monitor.start(), timeout=30)
        except asyncio.TimeoutError:
            print("\n30s Demo beendet")
            print(f"Stats: {monitor.stats}")

    asyncio.run(_demo())
