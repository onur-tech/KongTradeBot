"""
X/Twitter Real-Time Monitor.
Phase 1: Tweapi REST polling alle 30s ($10/Mo)
Phase 2: WebSocket wenn skaliert
Aktivieren: TWEAPI_KEY=xxx in .env + X_MONITOR_ENABLED=true
"""
import asyncio
import aiohttp
import os
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("polymarket_bot.x_monitor")

TWITTERAPI_KEY  = os.getenv("TWITTERAPI_KEY", "")
TWITTERAPI_BASE = "https://api.twitterapi.io"

MONITORED_ACCOUNTS = {

    # ── BREAKING NEWS (Priorität 1 - sofort handeln) ──
    "AP": {
        "priority": 1,
        "keywords": ["breaking", "just in", "confirms",
                     "announces", "declares", "warns"],
        "tags": ["all"],
        "category": "breaking_news",
    },
    "BNONews": {
        "priority": 1,
        "keywords": ["breaking", "just in", "explosion",
                     "attack", "ceasefire", "deal"],
        "tags": ["geopolitics"],
        "category": "breaking_news",
    },
    "Reuters": {
        "priority": 1,
        "keywords": ["breaking", "exclusive", "sources say",
                     "confirmed", "agreement", "talks"],
        "tags": ["all"],
        "category": "breaking_news",
    },

    # ── MACRO & FED (Priorität 1) ──
    "NickTimiraos": {
        "priority": 1,
        "keywords": ["rate", "fed", "cut", "hike", "pause",
                     "inflation", "fomc", "pivot"],
        "tags": ["fed", "rate cut", "fomc", "inflation"],
        "category": "macro",
    },
    "unusual_whales": {
        "priority": 2,
        "keywords": ["congress", "bill", "passed", "signed",
                     "veto", "executive", "fed", "rate"],
        "tags": ["politics", "macro"],
        "category": "macro",
    },

    # ── GEOPOLITIK (Priorität 1) ──
    "WhiteHouse": {
        "priority": 1,
        "keywords": ["iran", "ceasefire", "sanctions",
                     "agreement", "deal", "military",
                     "executive order", "tariff"],
        "tags": ["geopolitics", "iran", "trump"],
        "category": "geopolitics",
    },
    "StateDept": {
        "priority": 1,
        "keywords": ["ceasefire", "negotiations", "talks",
                     "agreement", "sanctions", "diplomatic"],
        "tags": ["geopolitics", "iran", "ukraine"],
        "category": "geopolitics",
    },

    # ── TWEET-COUNT MÄRKTE ──
    "elonmusk": {
        "priority": 2,
        "keywords": ["*"],  # Jeden Tweet zählen
        "tags": ["elon tweets", "tweet count"],
        "category": "tweet_count",
        "count_tweets": True,
    },

    # ── CRYPTO (Priorität 2) ──
    "whale_alert": {
        "priority": 2,
        "keywords": ["bitcoin", "ethereum", "transferred",
                     "moved", "whale", "million"],
        "tags": ["bitcoin", "crypto", "btc"],
        "category": "crypto",
    },

    # ── SPORTS (Priorität 2) ──
    "AdamSchefter": {
        "priority": 2,
        "keywords": ["injury", "trade", "signing",
                     "suspended", "cut", "released"],
        "tags": ["nfl", "sports"],
        "category": "sports",
    },
    "wojespn": {
        "priority": 2,
        "keywords": ["injury", "trade", "signing",
                     "suspended", "out", "return"],
        "tags": ["nba", "sports"],
        "category": "sports",
    },
    "FabrizioRomano": {
        "priority": 2,
        "keywords": ["here we go", "confirmed", "transfer",
                     "signs", "contract", "deal"],
        "tags": ["soccer", "champions league"],
        "category": "sports",
    },

    # ── POLYMARKET-SPEZIFISCH ──
    "Polymarket": {
        "priority": 1,
        "keywords": ["new market", "launching", "resolved",
                     "live", "announcing"],
        "tags": ["all"],
        "category": "polymarket",
    },
    "glintintel": {
        "priority": 2,
        "keywords": ["alert", "signal", "breaking",
                     "whale", "polymarket"],
        "tags": ["all"],
        "category": "polymarket",
    },

    # ── WETTER (Priorität 3) ──
    "NWSweather": {
        "priority": 3,
        "keywords": ["record", "extreme", "warning",
                     "historic", "temperature", "heat"],
        "tags": ["weather", "temperature"],
        "category": "weather",
    },
    "spydenuevo": {
        "priority": 2,
        "keywords": ["temperature", "weather", "celsius",
                     "polymarket", "bet"],
        "tags": ["weather", "temperature"],
        "category": "weather",
    },
}

# Elon Tweet-Counter (Wochen-basiert für Tweet-Count-Märkte)
_elon_tweet_count: int = 0
_elon_week_start: datetime | None = None


def _get_week_start() -> datetime:
    now = datetime.now(timezone.utc)
    return now - timedelta(days=now.weekday())


class XMonitor:
    def __init__(self, signal_callback=None):
        self.enabled = bool(TWITTERAPI_KEY) and \
            os.getenv("X_MONITOR_ENABLED", "false").lower() == "true"
        self.signal_callback = signal_callback
        self._last_ids: dict = {}
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"X-API-Key": TWITTERAPI_KEY},
                timeout=aiohttp.ClientTimeout(total=10),
            )
        return self._session

    async def check_account(self, account: str, config: dict) -> list:
        global _elon_tweet_count, _elon_week_start
        if not TWITTERAPI_KEY:
            return []
        try:
            url = f"{TWITTERAPI_BASE}/twitter/user/last_tweets"
            s = await self._get_session()
            async with s.get(url, params={"userName": account, "count": 5}) as r:
                data = await r.json(content_type=None)

            # twitterapi.io: {"status":"success","data":{"tweets":[...]}}
            raw = data.get("tweets") or data.get("data", {}).get("tweets", [])
            new_tweets = []
            for tw in raw:
                tid = tw.get("id") or tw.get("tweet_id", "")
                if tid == self._last_ids.get(account):
                    break
                new_tweets.append(tw)
            if new_tweets:
                tid0 = new_tweets[0].get("id") or new_tweets[0].get("tweet_id", "")
                self._last_ids[account] = tid0

            # Elon Tweet-Counter
            if config.get("count_tweets") and new_tweets:
                week_start = _get_week_start()
                if _elon_week_start is None or week_start.date() != _elon_week_start.date():
                    _elon_tweet_count = 0
                    _elon_week_start = week_start
                _elon_tweet_count += len(new_tweets)
                logger.info(
                    f"[X] Elon Tweet-Count diese Woche: {_elon_tweet_count} "
                    f"(+{len(new_tweets)} neu)")

            return new_tweets
        except Exception as e:
            logger.warning(f"[X] @{account}: {e}")
            return []

    def analyze(self, tweet: dict, config: dict) -> dict | None:
        # twitterapi.io: text in "text" or "full_text"; author in "author" str or "user.name"
        raw_text = tweet.get("text") or tweet.get("full_text", "")
        author = tweet.get("author") or \
            (tweet.get("user") or {}).get("name", "") or \
            (tweet.get("user") or {}).get("screen_name", "")
        text = raw_text.lower()
        # count_tweets-Accounts: jeder Tweet ist ein Signal
        if config.get("count_tweets"):
            return {
                "account":  author,
                "text":     raw_text[:200],
                "keywords": ["*"],
                "tags":     config["tags"],
                "priority": config["priority"],
                "category": config.get("category", ""),
                "ts":       datetime.now(timezone.utc).isoformat(),
            }
        hits = [k for k in config["keywords"] if k in text]
        if not hits:
            return None
        return {
            "account":  author,
            "text":     raw_text[:200],
            "keywords": hits,
            "tags":     config["tags"],
            "priority": config["priority"],
            "category": config.get("category", ""),
            "ts":       datetime.now(timezone.utc).isoformat(),
        }

    async def run_loop(self):
        if not self.enabled:
            logger.info(
                "[X] Monitor deaktiviert — "
                "TWITTERAPI_KEY fehlt oder X_MONITOR_ENABLED=false"
            )
            return
        categories = {}
        for cfg in MONITORED_ACCOUNTS.values():
            c = cfg.get("category", "other")
            categories[c] = categories.get(c, 0) + 1
        logger.info(
            f"[X] Monitor gestartet — {len(MONITORED_ACCOUNTS)} Accounts | "
            + " | ".join(f"{c}:{n}" for c, n in sorted(categories.items()))
        )
        while True:
            try:
                for account, cfg in MONITORED_ACCOUNTS.items():
                    try:
                        tweets = await self.check_account(account, cfg)
                        for tw in tweets:
                            sig = self.analyze(tw, cfg)
                            if sig:
                                logger.info(
                                    f"[X] {'🚨' if sig['priority']==1 else '📢'} "
                                    f"@{account} [{sig['category']}]: "
                                    f"{sig['keywords']} — {sig['text'][:80]}"
                                )
                                if self.signal_callback:
                                    try:
                                        await self.signal_callback(sig)
                                    except Exception as cb_e:
                                        logger.warning(f"[X] Callback-Fehler: {cb_e}")
                    except Exception as e:
                        logger.warning(f"[X] @{account} Fehler: {e}")
                        continue
            except Exception as e:
                logger.error(f"[X] Loop-Fehler: {e}")
            await asyncio.sleep(30)
