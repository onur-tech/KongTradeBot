"""
Telegram Bridge — Liest Glint Alerts und triggert Trades.
Nutzt Telethon als UserBot (liest eigene Telegram-Nachrichten).

WICHTIG: Braucht Telegram API credentials:
- API_ID und API_HASH von https://my.telegram.org
- Einmalig Session erstellen
"""
import asyncio
import os
import re

from utils.logger import get_logger

logger = get_logger("telegram_bridge")

# Telegram API Credentials (aus .env)
API_ID   = int(os.getenv("TELEGRAM_API_ID", "0") or "0")
API_HASH = os.getenv("TELEGRAM_API_HASH", "")

# Glint Bot Username oder Chat-ID
GLINT_SOURCE = os.getenv("GLINT_SOURCE", "@GlintAlertsBot")


class TelegramBridge:
    """
    Überwacht Glint Alerts in Telegram.
    Parsed Signale und leitet sie an den Trading Bot weiter.
    """

    def __init__(self, signal_callback=None):
        self.signal_callback = signal_callback
        self.enabled = os.getenv(
            "TELEGRAM_BRIDGE_ENABLED", "false").lower() == "true"
        self.client = None

    def parse_glint_alert(self, text: str) -> dict | None:
        """
        Parsed einen Glint Alert.

        Erwartetes Format:
        🔴 CRITICAL · Reuters
        "US x Iran ceasefire signed"
        Related Markets (2):
        1. US x Iran ceasefire · YES 21¢ · 9/10
        """
        if not text:
            return None

        # Impact Level
        impact = "LOW"
        if "CRITICAL" in text.upper():
            impact = "CRITICAL"
        elif "HIGH" in text.upper():
            impact = "HIGH"

        # Relevanz Score (z.B. "9/10")
        relevance = 0
        score_match = re.search(r'(\d+)\s*/\s*10', text)
        if score_match:
            relevance = int(score_match.group(1))

        # Markt-Preis in Cent (z.B. "YES 21¢")
        price = None
        price_match = re.search(r'YES\s+(\d+)¢', text)
        if price_match:
            price = int(price_match.group(1))

        # Markt-Name extrahieren (erste Related Market Zeile)
        market_match = re.search(r'\d+\.\s+(.+?)\s+·\s+YES', text)
        market_name = market_match.group(1).strip() if market_match else ""

        # Ignorieren bei niedriger Relevanz
        if relevance < 8 and impact not in ("CRITICAL", "HIGH"):
            logger.debug(
                f"[TGBridge] Signal ignoriert: Impact={impact} Relevanz={relevance}/10"
            )
            return None

        should_trade = (
            impact == "CRITICAL"
            and relevance >= 8
            and price is not None
            and price < 40  # Nur wenn Preis noch günstig (< 40¢)
        )

        return {
            "impact":       impact,
            "relevance":    relevance,
            "price_cents":  price,
            "market_name":  market_name,
            "raw_text":     text[:200],
            "should_trade": should_trade,
        }

    async def start(self):
        """Startet den Telegram Bridge UserBot."""
        if not self.enabled:
            logger.info("[TGBridge] Deaktiviert (TELEGRAM_BRIDGE_ENABLED=false)")
            return

        if not API_ID or not API_HASH:
            logger.warning(
                "[TGBridge] Keine Telegram API Credentials. "
                "Bitte TELEGRAM_API_ID und TELEGRAM_API_HASH in .env setzen. "
                "Credentials: https://my.telegram.org"
            )
            return

        try:
            from telethon import TelegramClient, events
        except ImportError:
            logger.error("[TGBridge] telethon nicht installiert: pip install telethon")
            return

        logger.info("[TGBridge] Starte Telegram UserBot...")
        session_file = "/root/KongTradeBot/telegram_bridge_session"

        self.client = TelegramClient(session_file, API_ID, API_HASH)
        await self.client.start()
        logger.info(f"[TGBridge] Verbunden — überwache {GLINT_SOURCE}")

        @self.client.on(events.NewMessage(from_users=GLINT_SOURCE))
        async def handle_glint_alert(event):
            text = event.message.text or ""
            logger.info(f"[TGBridge] Glint Alert: {text[:80]}")

            signal = self.parse_glint_alert(text)
            if not signal:
                return

            logger.info(
                f"[TGBridge] Signal: Impact={signal['impact']} "
                f"Relevanz={signal['relevance']}/10 "
                f"Preis={signal['price_cents']}¢ "
                f"Trade={signal['should_trade']}"
            )

            if self.signal_callback:
                await self.signal_callback(signal)

        logger.info(
            f"[TGBridge] Bereit — CRITICAL + Relevanz≥8 + Preis<40¢ → Auto-Trade"
        )
        await self.client.run_until_disconnected()
