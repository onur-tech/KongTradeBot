"""
RSS Monitor — Tier-1 News Quellen für Polymarket Signale.
Pollt alle 30 Sekunden. Matched Headlines gegen offene Märkte.
Sendet Telegram-Alert bei Treffer.
"""
import asyncio
import feedparser
import hashlib
import os
import time
from datetime import datetime, timezone

from utils.logger import get_logger

logger = get_logger("rss_monitor")

# Tier-1 Quellen — BBC, Al Jazeera, AP (via NPR), NYT World
RSS_FEEDS = {
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "AP News": "https://feeds.npr.org/1001/rss.xml",
    "NYT World": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
}

# Keyword → Kategorie Mapping
KEYWORD_CATEGORIES = {
    "geopolitics": [
        "iran", "ceasefire", "tehran", "khamenei",
        "hormuz", "israel", "hezbollah", "hamas",
        "ukraine", "russia", "nato", "sanctions"
    ],
    "us_politics": [
        "trump", "white house", "executive order",
        "congress", "senate", "president", "oval office",
        "tariff", "trade war"
    ],
    "macro": [
        "federal reserve", "fed ", "interest rate",
        "powell", "fomc", "rate hike", "rate cut",
        "inflation", "recession", "gdp"
    ],
    "crypto": [
        "bitcoin", "btc", "ethereum", "crypto",
        "sec", "etf", "coinbase", "binance"
    ],
    "weather": [
        "temperature record", "heatwave", "extreme weather",
        "hurricane", "tornado", "blizzard", "drought"
    ],
    "sports": [
        "nba", "nfl", "world cup", "champions league",
        "playoff", "finals", "championship"
    ]
}


class RSSMonitor:
    def __init__(self, send_fn=None):
        self.send_fn = send_fn  # async callable: send_fn(text, urgent=False)
        self.seen_hashes = set()
        self.enabled = os.getenv(
            "RSS_MONITOR_ENABLED", "true").lower() == "true"
        self.poll_interval = int(
            os.getenv("RSS_POLL_INTERVAL_SECONDS", "30"))
        logger.info(
            f"[RSS] Monitor initialisiert — "
            f"{'ENABLED' if self.enabled else 'DISABLED'}, "
            f"Poll: {self.poll_interval}s")

    def _hash_item(self, title: str, link: str) -> str:
        return hashlib.md5(
            f"{title}{link}".encode()).hexdigest()

    def _match_keywords(self, text: str) -> list:
        """Findet Kategorien die zum Text passen."""
        text_lower = text.lower()
        matched = []
        for category, keywords in KEYWORD_CATEGORIES.items():
            if any(kw in text_lower for kw in keywords):
                matched.append(category)
        return matched

    def _is_fresh(self, published_parsed) -> bool:
        """Artikel älter als 10 Minuten ignorieren."""
        if not published_parsed:
            return True  # Kein Datum = akzeptieren
        pub_ts = time.mktime(published_parsed)
        age_minutes = (time.time() - pub_ts) / 60
        return age_minutes < 10

    async def poll_once(self) -> list:
        """Einmaliger Poll aller RSS Feeds."""
        signals = []
        for source, url in RSS_FEEDS.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:10]:
                    title = entry.get("title", "")
                    link = entry.get("link", "")
                    h = self._hash_item(title, link)

                    if h in self.seen_hashes:
                        continue

                    if not self._is_fresh(
                            entry.get("published_parsed")):
                        continue

                    categories = self._match_keywords(title)
                    if not categories:
                        continue

                    self.seen_hashes.add(h)
                    if len(self.seen_hashes) > 5000:
                        oldest = next(iter(self.seen_hashes))
                        self.seen_hashes.discard(oldest)

                    signal = {
                        "source": source,
                        "title": title,
                        "link": link,
                        "categories": categories,
                        "tier": 1
                    }
                    signals.append(signal)

                    logger.info(
                        f"[RSS] {source}: {title[:60]} "
                        f"→ {categories}")

                    if self.send_fn:
                        await self._send_alert(signal)

            except Exception as e:
                logger.error(f"[RSS] {source} Fehler: {e}")

        return signals

    async def _send_alert(self, signal: dict):
        """Sendet Telegram-Alert für News-Signal."""
        cats = " + ".join(signal["categories"])
        msg = (
            f"📰 <b>NEWS SIGNAL</b> [Tier 1]\n"
            f"Quelle: {signal['source']}\n"
            f"📌 {signal['title'][:100]}\n"
            f"🏷 Kategorie: {cats}\n"
            f"🔗 {signal['link'][:80]}"
        )
        try:
            await self.send_fn(msg, urgent=True)
        except Exception as e:
            logger.error(f"[RSS] Telegram-Alert Fehler: {e}")

    async def run(self):
        """Dauerhafter RSS Monitor Loop."""
        if not self.enabled:
            logger.info("[RSS] Monitor deaktiviert (RSS_MONITOR_ENABLED=false)")
            return

        logger.info(
            f"[RSS] Monitor gestartet — "
            f"{len(RSS_FEEDS)} Feeds, alle {self.poll_interval}s")

        while True:
            try:
                signals = await self.poll_once()
                if signals:
                    logger.info(f"[RSS] {len(signals)} neue Signale")
            except Exception as e:
                logger.error(f"[RSS] Loop-Fehler: {e}")
            await asyncio.sleep(self.poll_interval)
