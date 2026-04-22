"""
copy_trading.py — Strategie: Copy Trading

KERNAUFGABE:
Entscheidet welche Trades kopiert werden und mit welcher Größe.

LEKTIONEN AUS DER COMMUNITY:
- Nur kurzfristige Märkte (24-72h) kopieren
- Win Rate der Source-Wallet tracken
- Wenn Wallet schlechter wird → aufhören zu kopieren (Win Rate Decay Detection)
- Mehrere Wallets diversifizieren
- Signal-Aggregation: 2+ Wallets im selben Markt = stärkeres Signal → größerer Trade
"""

import asyncio
import json
import os
import time
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional
from collections import deque
from datetime import datetime, timezone

from utils.logger import get_logger
from utils.config import Config
from core.wallet_monitor import TradeSignal
from core.risk_manager import RiskManager, RiskDecision

try:
    from utils.error_handler import handle_error as _handle_error
except ImportError:
    _handle_error = None

try:
    from utils.signal_tracker import log_signal as _log_signal
except ImportError:
    _log_signal = None  # type: ignore


def log_signal(signal, decision: str, reason=None) -> None:
    if _log_signal is not None:
        _log_signal(signal, decision, reason)

logger = get_logger("copy_trading")

# Sekunden nach dem ersten Signal warten, um weitere Wallets zu sammeln
AGGREGATION_WINDOW_S: int = 60

# Multiplikatoren je nach Anzahl bestätigender Wallets
MULTI_SIGNAL_MULTIPLIERS: Dict[int, float] = {
    1: 1.0,
    2: 1.5,
    3: 2.0,  # 3+ Wallets → 2x
}

# Ab diesem Anteil (50%) der Target-Wallets gilt es als Herdentrieb → kein Boost + Alert
HERD_FRACTION: float = 0.50

# Early Entry Bonus: Märkte mit <$10K Volumen bekommen 1.5x Bonus
EARLY_ENTRY_MULTIPLIER: float = 1.5
EARLY_ENTRY_VOLUME_USD: float = 10_000

# ---------------------------------------------------------------------------
# Wallet-Kategorie-Spezialisierung
# Jedes Wallet wird nur für seine Stärke-Kategorien kopiert.
# Wallets ohne Eintrag (oder mit "broad") handeln in allen Märkten.
# ---------------------------------------------------------------------------
WALLET_CATEGORIES: Dict[str, list] = {
    # Sports-Spezialisten
    "0x492442eab586f242b53bda933fd5de859c8a3782": ["sports"],
    "0x02227b8f5a9636e895607edd3185ed6ee5598ff7": ["sports", "macro"],
    "0xefbc5fec8d7b0acdc8911bdd9a98d6964308f9a2": ["sports"],
    "0xc2e7800b5af46e6093872b177b7a5e7f0563be51": ["sports"],
    "0xbddf61af533ff524d27154e589d2d7a81510c684": ["sports"],
    "0x2005d16a84ceefa912d4e380cd32e7ff827875ea": ["sports", "politics", "broad"],
    "0x2a2c53bd278c04da9962fcf96490e17f3dfb9bc1": ["sports", "broad"],
    # Politik-Spezialisten
    "0xbaa2bcb5439e985ce4ccf815b4700027d1b92c73": ["politics", "geopolitics", "sports"],
    "0x0c0e270cf879583d6a0142fc817e05b768d0434e": ["politics", "geopolitics"],
    "0xc6587b11a2209e46dfe3928b31c5514a8e33b784": ["politics", "geopolitics"],
    # Crypto-Spezialisten
    "0xde17f7144fbd0eddb2679132c10ff5e74b120988": ["crypto"],
    "0xd84c2b6d65dc596f49c7b6aadd6d74ca91e407b9": ["crypto"],
    "0x63ce342161250d705dc0b16df89036c8e5f9ba9a": ["crypto"],
    # Allrounder (kein Filter)
    "0x019782cab5d844f02bafb71f512758be78579f3c": ["broad"],
}

_CAT_KEYWORDS: Dict[str, list] = {
    "sports":      ["nba", "nfl", "nhl", "mlb", "soccer", "football", "basketball",
                    "tennis", "golf", "masters", "game", "match", "championship",
                    "score", "tournament", "ucl", "champions league", "premier league",
                    "bundesliga", "serie a", "la liga"],
    "crypto":      ["bitcoin", "btc", "ethereum", "eth", "crypto", "coin", "token",
                    "blockchain", "defi", "nft"],
    "politics":    ["trump", "biden", "election", "president", "congress", "senate",
                    "vote", "poll", "resign"],
    "geopolitics": ["iran", "ukraine", "russia", "israel", "ceasefire", "war",
                    "military", "nuclear", "sanctions", "attack", "nato"],
    "macro":       ["fed", "rate", "inflation", "gdp", "jobs", "unemployment",
                    "recession", "cpi", "fomc"],
    "weather":     ["temperature", "celsius", "fahrenheit", "highest temp", "weather"],
}


def _detect_market_category(question: str) -> str:
    q = question.lower()
    for cat, keywords in _CAT_KEYWORDS.items():
        if any(k in q for k in keywords):
            return cat
    return "other"


def should_copy_trade(wallet_addr: str, market_question: str) -> tuple:
    """Returns (should_copy: bool, reason: str)."""
    allowed = WALLET_CATEGORIES.get(wallet_addr.lower(), [])
    if not allowed or "broad" in allowed:
        return True, "Allrounder"
    market_cat = _detect_market_category(market_question)
    if market_cat in allowed:
        return True, f"Kategorie-Match: {market_cat}"
    return False, f"Kategorie {market_cat!r} nicht in Spezialgebiet {allowed}"


# ---------------------------------------------------------------------------
# Defensive Config (aus .env)
# ---------------------------------------------------------------------------
MAX_POSITIONS_TOTAL: int = int(os.environ.get("MAX_POSITIONS_TOTAL", "999"))
MIN_MARKT_VOLUMEN_USD: float = float(os.environ.get("MIN_MARKT_VOLUMEN", "0"))
_CATEGORY_BLACKLIST: list = [
    s.strip() for s in os.environ.get("CATEGORY_BLACKLIST", "").split(",") if s.strip()
]
_CRYPTO_DAILY_SINGLE_SIGNAL: bool = os.environ.get("CRYPTO_DAILY_SINGLE_SIGNAL", "true").lower() == "true"


# ---------------------------------------------------------------------------
# Crypto-Daily Erkennung
# ---------------------------------------------------------------------------

def is_crypto_daily(signal: "TradeSignal") -> bool:
    """Erkennt tägliche Crypto-Preis-Märkte (BTC/ETH above/below, daily price bets)."""
    slug = getattr(signal, "market_slug", "") or ""
    question = getattr(signal, "market_question", "") or ""
    text = (slug + " " + question).lower()
    crypto_keywords = [
        "bitcoin-above", "ethereum-above", "btc-above", "eth-above",
        "bitcoin-up-or-down", "ethereum-up-or-down",
        "what-price-will-bitcoin", "what-price-will-ethereum",
        "bitcoin-price-on", "ethereum-price-on",
        "crypto-above", "btc-daily", "eth-daily",
        "bitcoin above", "ethereum above", "btc above", "eth above",
        "bitcoin price", "ethereum price",
    ]
    return any(kw in text for kw in crypto_keywords)


# ---------------------------------------------------------------------------
# Wallet-Gewichtungs-Konfiguration
# Trägt bekannten Wallets einen Kapital-Multiplikator zu.
# Wallets die hier nicht aufgeführt sind bekommen DEFAULT_WALLET_MULTIPLIER.
# ---------------------------------------------------------------------------
WALLET_MULTIPLIERS: Dict[str, float] = {
    # majorexploiter — Sports/UCL (nicht Geopolitics wie angenommen) → 1.5x
    # RECAL 2026-04-19 T-M09: Bug-Fix 8d9b08a zeigte Sports 100% (UCL), war 3.0x
    "0x019782cab5d844f02bafb71f512758be78579f3c": 1.5,

    # April#1 Sports — WATCHING 0.3x
    # RECAL 2026-04-19 T-M09b: Extern WR 46.7% (Cointrenches), Lifetime PnL -$9.8M
    # HF-8 FAIL + HF-10 HFT-Bot. Review: T-D109 (2026-05-19). Siehe KB P077. Ref: 5d7d138
    "0x492442eab586f242b53bda933fd5de859c8a3782": 0.3,

    # HorizonSplendidView → 0.5x (0 Activity erkannt, inaktiv)
    # RECAL 2026-04-19 T-M09: 0 Activity-Records via API, war 2.0x
    "0x02227b8f5a9636e895607edd3185ed6ee5598ff7": 0.5,

    # reachingthesky — Tier B 1.0x
    # RECAL 2026-04-19: Code war 2.0x veraltet, .env gewann mit 1.0x - sync aligned (P083)
    "0xefbc5fec8d7b0acdc8911bdd9a98d6964308f9a2": 1.0,

    # HOOK — Tier B 1.0x
    # RECAL 2026-04-19 T-M09b: Nur 46 Trades (unter HF-1 100-Trade-Minimum),
    # WR diskrepant (38.5% vs 67%). Review: T-D109 (2026-05-19). Siehe KB P077. Ref: 5d7d138
    "0x0b7a6030507efe5db145fbb57a25ba0c5f9d86cf": 1.0,

    # REMOVED 2026-04-19 Audit v1.0 HF-8 FAIL (49% WR)
    # "0xee613b3fc183ee44f9da9c05f53e2da107e3debf": 0.3,  # sovereign2013

    # Countryside — 92% Win Rate (predicts.guru) → 3x
    "0xbddf61af533ff524d27154e589d2d7a81510c684": 3.0,

    # Crypto Spezialist — 65.6% Win Rate → 2x
    "0xde17f7144fbd0eddb2679132c10ff5e74b120988": 2.0,

    # BoneReader — 72% Win Rate → 1.5x
    "0xd84c2b6d65dc596f49c7b6aadd6d74ca91e407b9": 1.5,

    # DrPufferfish — 92% Win Rate (predicts.guru) → 3x
    "0xdb27bf2ac5d428a9c63dbc914611036855a6c56e": 3.0,

    # wan123 — negative ROI-Flag, Moonshot-Pattern → 0.5x
    # RECAL 2026-04-19 T-M09: negative ROI in KNOWLEDGE_BASE, war 2.5x
    "0xde7be6d489bce070a959e0cb813128ae659b5f4b": 0.5,

    # kcnyekchno — 81% Win Rate → 1x (bisher 0 Trades kopiert, konservativ)
    # RECAL 2026-04-19 T-M09: 0 kopierte Trades bisher, war 2.0x
    "0x7177a7f5c216809c577c50c77b12aae81f81ddef": 1.0,

    # REMOVED 2026-04-19 Audit v1.0 HF-8 FAIL (45% WR)
    # "0x7a6192ea6815d3177e978dd3f8c38be5f575af24": 0.3,  # Gambler1968

    # REMOVED 2026-04-19 Audit v1.0 HF-8 FAIL (26.8% WR, 87% Copy-Volume)
    # "0x2005d16a84ceefa912d4e380cd32e7ff827875ea": 0.2,  # RN1

    # ADDED 2026-04-19: Manual Discovery (Commit 38bbb5c Windows-CC)
    "0xc6587b11a2209e46dfe3928b31c5514a8e33b784": 0.5,  # Erasmus - Geopolitics/Iran, Tier B
    "0x0c0e270cf879583d6a0142fc817e05b768d0434e": 0.3,  # TheSpiritofUkraine - Geopolitics seit 2021, Tier B

    # denizz — polymonit April Politics #1 +$751k (UCL-Soccer-Spezialist) → 1.0x
    # RECAL 2026-04-19 T-M09: explizit auf 1.0x (vorher DEFAULT 0.5x)
    "0xbaa2bcb5439e985ce4ccf815b4700027d1b92c73": 1.0,

    # PANews Biteye Smart Money — integriert 2026-04-20, Review 2026-05-05
    # HF-7 PENDING (predicts.guru Deposit-ROI unverified) → 0.3x konservativ
    "0x38e59b36aae31b164200d0cad7c3fe5e0ee795e7": 0.3,  # cowcat — ME Longshot +117% ROI
    "0x15ceffed7bf820cd2d90f90ea24ae9909f5cd5fa": 0.3,  # HondaCivic — Weather 85.7% WR
    "0x8c0b024c17831a0dde038547b7e791ae6a0d7aa5": 0.3,  # EFFICIENCYEXPERT — Esports $580K
    "0x8e0b7ae246205b1ddf79172148a58a3204139e5c": 0.3,  # synnet — Tennis $290K Underdogs
    "0x6c743aafd813475986dcd930f380a1f50901bd4e": 0.3,  # middleoftheocean — Soccer 83.1% WR
}

# Unbekannte / nicht konfigurierte Wallets bekommen halbe Größe
DEFAULT_WALLET_MULTIPLIER: float = 0.5

# ---------------------------------------------------------------------------
# Override WALLET_MULTIPLIERS mit WALLET_WEIGHTS aus .env (falls gesetzt)
# Format: '{"0xABCD...":1.5,"default":1.0}'
# Nur Prefix-Matching (erste 18 Zeichen der Adresse)
# ---------------------------------------------------------------------------
def _load_env_weights() -> dict:
    raw = os.environ.get("WALLET_WEIGHTS", "")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}

_ENV_WEIGHTS = _load_env_weights()

def _apply_env_weights():
    """Merged ENV-Weights in WALLET_MULTIPLIERS (Prefix-Match auf 18 Chars)."""
    for env_prefix, weight in _ENV_WEIGHTS.items():
        if env_prefix == "default":
            continue
        for full_addr in list(WALLET_MULTIPLIERS.keys()):
            if full_addr.lower().startswith(env_prefix.lower()):
                WALLET_MULTIPLIERS[full_addr] = float(weight)
    default = _ENV_WEIGHTS.get("default")
    if default is not None:
        global DEFAULT_WALLET_MULTIPLIER
        DEFAULT_WALLET_MULTIPLIER = float(default)

_apply_env_weights()

# ---------------------------------------------------------------------------
# Wallet-Namen-Mapping — lesbare Namen für alle bekannten Target-Wallets
# ---------------------------------------------------------------------------
WALLET_NAMES: Dict[str, str] = {
    "0x019782cab5d844f02bafb71f512758be78579f3c": "majorexploiter",
    "0x492442eab586f242b53bda933fd5de859c8a3782": "April#1 Sports",
    "0x02227b8f5a9636e895607edd3185ed6ee5598ff7": "HorizonSplendidView",
    "0xefbc5fec8d7b0acdc8911bdd9a98d6964308f9a2": "reachingthesky",
    "0x0b7a6030507efe5db145fbb57a25ba0c5f9d86cf": "HOOK",
    "0xee613b3fc183ee44f9da9c05f53e2da107e3debf": "sovereign2013",
    "0xbaa2bcb5439e985ce4ccf815b4700027d1b92c73": "denizz",
    "0xde7be6d489bce070a959e0cb813128ae659b5f4b": "wan123",
    "0x7a6192ea6815d3177e978dd3f8c38be5f575af24": "Gambler1968",
    "0x7177a7f5c216809c577c50c77b12aae81f81ddef": "kcnyekchno",
    "0x2005d16a84ceefa912d4e380cd32e7ff827875ea": "RN1",
    "0xbddf61af533ff524d27154e589d2d7a81510c684": "Countryside",
    "0xde17f7144fbd0eddb2679132c10ff5e74b120988": "Crypto Spezialist",
    "0xd84c2b6d65dc596f49c7b6aadd6d74ca91e407b9": "BoneReader",
    "0xdb27bf2ac5d428a9c63dbc914611036855a6c56e": "DrPufferfish",
}


def get_wallet_name(wallet_address: str) -> str:
    """Gibt den lesbaren Namen einer Wallet zurück, oder eine gekürzte Adresse als Fallback."""
    return WALLET_NAMES.get(wallet_address.lower(), wallet_address[:10] + "...")


def get_wallet_multiplier(wallet_address: str) -> float:
    """Gibt den konfigurierten Größen-Multiplikator für eine Wallet zurück."""
    return WALLET_MULTIPLIERS.get(wallet_address.lower(), DEFAULT_WALLET_MULTIPLIER)


@dataclass
class WalletPerformance:
    """Trackt Performance einer kopierten Wallet."""
    wallet_address: str
    trades_total: int = 0
    trades_won: int = 0
    trades_lost: int = 0
    total_pnl_usd: float = 0.0

    # Letzte 20 Trades für Win-Rate-Decay-Detection
    recent_results: deque = field(default_factory=lambda: deque(maxlen=20))

    @property
    def win_rate(self) -> float:
        if self.trades_total == 0:
            return 0.0
        return self.trades_won / self.trades_total

    @property
    def recent_win_rate(self) -> float:
        """Win Rate der letzten 20 Trades."""
        if not self.recent_results:
            return 0.0
        wins = sum(1 for r in self.recent_results if r > 0)
        return wins / len(self.recent_results)

    @property
    def is_decaying(self) -> bool:
        """Win Rate unter 45% in den letzten 20 Trades → Wallet komplett überspringen."""
        if len(self.recent_results) < 10:
            return False
        return self.recent_win_rate < 0.45

    @property
    def is_trend_declining(self) -> bool:
        """
        Trend-Decline Detection: Recent Win Rate >10% unter Gesamt-Win Rate.
        Nicht hart stoppen, aber Multiplikator halbieren.
        Erfordert mind. 20 Gesamttrades und 10 Recent-Trades für Signal.
        """
        if self.trades_total < 20 or len(self.recent_results) < 10:
            return False
        return self.recent_win_rate < self.win_rate - 0.10

    def record(self, pnl_usd: float):
        self.trades_total += 1
        self.total_pnl_usd += pnl_usd
        self.recent_results.append(pnl_usd)
        if pnl_usd > 0:
            self.trades_won += 1
        else:
            self.trades_lost += 1


@dataclass
class CopyOrder:
    """Ein Order der ausgeführt werden soll."""
    signal: TradeSignal
    size_usdc: float
    dry_run: bool
    wallet_multiplier: float = 1.0
    is_multi_signal: bool = False

    def __repr__(self):
        mode = "[DRY-RUN]" if self.dry_run else "[LIVE]"
        return f"CopyOrder{mode} {self.signal.side} ${self.size_usdc:.2f} | {self.signal}"


class CopyTradingStrategy:
    """
    Verarbeitet eingehende TradeSignals und entscheidet ob kopiert wird.

    Wird vom WalletMonitor via Callback aufgerufen.
    Gibt CopyOrder weiter an ExecutionEngine.

    Signal-Aggregation: Signale für denselben Markt innerhalb von
    AGGREGATION_WINDOW_S Sekunden werden kombiniert → 1.5x / 2x Größe.
    """

    def __init__(self, config: Config, risk_manager: RiskManager):
        self.config = config
        self.risk_manager = risk_manager

        # Performance pro Wallet tracken
        self.wallet_performance: Dict[str, WalletPerformance] = {
            wallet: WalletPerformance(wallet_address=wallet)
            for wallet in config.target_wallets
        }

        # Callback zur ExecutionEngine
        self.on_copy_order: Optional[callable] = None

        # Callback: gibt aktuelle Anzahl offener Positionen zurück (für MAX_POSITIONS_TOTAL)
        self.get_open_positions_count: Optional[callable] = None

        # T-M03: Whale-Exit-Copy Callbacks
        self.get_open_positions: Optional[callable] = None   # () → Dict[str, OpenPosition]
        self.on_whale_exit: Optional[callable] = None        # (pos, signal) → coroutine

        # Callback für Wallet-Warnungen (Trend-Decline) → Telegram
        self.on_wallet_warning: Optional[callable] = None

        # Callback für Herdentrieb-Alert → Telegram
        self.on_herd_alert: Optional[callable] = None

        # Signal-Aggregation: key = "token_id:outcome", value = Liste von Signalen
        self._agg_buffer: Dict[str, List[TradeSignal]] = {}
        self._agg_tasks: Dict[str, asyncio.Task] = {}

        # Statistik
        self.stats = {
            "signals_received": 0,
            "orders_created": 0,
            "orders_skipped": 0,
            "multi_signals": 0,
        }

    async def handle_signal(self, signal: TradeSignal):
        """
        Hauptfunktion: Verarbeitet ein TradeSignal.
        Wird vom WalletMonitor aufgerufen wenn neuer Trade erkannt.

        Statt sofort auszuführen: Signal in Aggregations-Buffer legen und
        AGGREGATION_WINDOW_S Sekunden auf weitere Wallets warten.
        """
        self.stats["signals_received"] += 1

        key = f"{signal.token_id}:{signal.outcome}"

        if key not in self._agg_buffer:
            self._agg_buffer[key] = []

        # Nur einmal pro Wallet buffern (kein Duplikat)
        already_from_wallet = any(
            s.source_wallet == signal.source_wallet for s in self._agg_buffer[key]
        )
        if already_from_wallet:
            return

        self._agg_buffer[key].append(signal)

        wallet_name = get_wallet_name(signal.source_wallet)
        market_short = signal.market_question[:60] if signal.market_question else signal.token_id[:16]

        # Erster Eingang → Aggregations-Timer starten
        if key not in self._agg_tasks or self._agg_tasks[key].done():
            logger.info(
                f"⏳ Signal buffered [{wallet_name}] {signal.outcome} auf '{market_short}' "
                f"— warte {AGGREGATION_WINDOW_S}s auf weitere Wallets..."
            )
            task = asyncio.create_task(self._flush_aggregated(key))
            self._agg_tasks[key] = task
        else:
            # Weiteres Signal für denselben Markt → sofort Vorschau loggen
            count = len(self._agg_buffer[key])
            names = " + ".join(get_wallet_name(s.source_wallet) for s in self._agg_buffer[key])
            multiplier = MULTI_SIGNAL_MULTIPLIERS.get(count, 2.0)
            logger.info(
                f"🔥 MULTI-SIGNAL ({count}x): {names} kaufen beide "
                f"{signal.outcome} auf '{market_short}' → {multiplier}x Größe!"
            )

    async def _flush_aggregated(self, key: str):
        """Nach AGGREGATION_WINDOW_S Sekunden: alle gesammelten Signale auswerten und ausführen."""
        await asyncio.sleep(AGGREGATION_WINDOW_S)

        signals = self._agg_buffer.pop(key, [])
        self._agg_tasks.pop(key, None)

        if not signals:
            return

        count = len(signals)
        # Basiswert: Signal mit größtem Einsatz der kopierenden Wallets
        base_signal = max(signals, key=lambda s: s.size_usdc)
        market_short = base_signal.market_question[:60] if base_signal.market_question else base_signal.token_id[:16]

        # Herdentrieb-Check: >50% der Target-Wallets = kein Boost + Telegram Alert
        total_wallets  = max(1, len(self.config.target_wallets))
        herd_threshold = max(3, int(total_wallets * HERD_FRACTION))
        if count > herd_threshold:
            multi_multiplier = 1.0
            self.stats["herd_signals"] = self.stats.get("herd_signals", 0) + 1
            names = " + ".join(get_wallet_name(s.source_wallet) for s in signals)
            pct   = count / total_wallets * 100
            logger.warning(
                f"🐑 HERDENTRIEB ({count}/{total_wallets} = {pct:.0f}% Wallets) — kein Größen-Boost | "
                f"{names} | {base_signal.outcome} auf '{market_short}'"
            )
            if self.on_herd_alert:
                asyncio.create_task(self._safe_call(
                    self.on_herd_alert,
                    count, total_wallets, names, base_signal.outcome, market_short
                ))
        else:
            multi_multiplier = MULTI_SIGNAL_MULTIPLIERS.get(count, 2.0)  # 3+ → 2x

        # Min-Wallet-Check: Crypto-Daily = 1 Wallet reicht; alle anderen = 2 Wallets benötigt
        if _CRYPTO_DAILY_SINGLE_SIGNAL:
            min_signals_required = 1 if is_crypto_daily(base_signal) else 2
        else:
            min_signals_required = 1
        if count < min_signals_required:
            wallet_name = get_wallet_name(base_signal.source_wallet)
            logger.info(
                f"⏭️ SKIP: nur {count} Wallet ({wallet_name}) — min {min_signals_required} "
                f"für diesen Markt | {base_signal.outcome} auf '{market_short}'"
            )
            self.stats["orders_skipped"] += 1
            log_signal(base_signal, "SKIPPED", f"MIN_WALLETS:{count}<{min_signals_required}")
            return

        if count >= 2:
            self.stats["multi_signals"] += 1
            names = " + ".join(get_wallet_name(s.source_wallet) for s in signals)
            logger.info(
                f"🔥 MULTI-SIGNAL AUSFÜHRUNG ({count} Wallets, {multi_multiplier}x): "
                f"{names} | {base_signal.outcome} auf '{market_short}'"
            )
            # Telegram-Benachrichtigung über on_multi_signal Callback (optional)
            if hasattr(self, "on_multi_signal") and self.on_multi_signal:
                try:
                    await self._safe_call(
                        self.on_multi_signal,
                        count, names, base_signal.outcome, market_short, multi_multiplier
                    )
                except Exception:
                    pass
        else:
            # count == 1, Crypto-Daily — explizit loggen
            wallet_name = get_wallet_name(base_signal.source_wallet)
            logger.info(
                f"₿ CRYPTO-DAILY SINGLE-SIGNAL [{wallet_name}]: "
                f"{base_signal.outcome} auf '{market_short}'"
            )

        await self._process_signal(base_signal, extra_multiplier=multi_multiplier)

    async def _process_signal(self, signal: TradeSignal, extra_multiplier: float = 1.0):
        """Interne Ausführungslogik für ein (ggf. aggregiertes) Signal."""
        # 0a. CATEGORY_BLACKLIST-Check
        if _CATEGORY_BLACKLIST:
            slug = (getattr(signal, "market_slug", "") or signal.market_question or "").lower()
            for prefix in _CATEGORY_BLACKLIST:
                if prefix.lower() in slug:
                    logger.info(
                        f"⏭️ SKIP: reason=CATEGORY_BLACKLIST prefix={prefix!r} "
                        f"(slug={slug[:60]})"
                    )
                    self.stats["orders_skipped"] += 1
                    log_signal(signal, "SKIPPED", f"CATEGORY_BLACKLIST:{prefix}")
                    return

        # 0a1. OPPOSING_SIDE + EVENT_CAP Guard
        if self.get_open_positions is not None:
            _open = self.get_open_positions()
            _mkt_id = signal.market_id
            # Block: gegenseitige Seite auf derselben condition_id bereits offen
            for _pos in _open.values():
                if _pos.market_id == _mkt_id and _pos.outcome != signal.outcome:
                    logger.info(
                        f"⏭️ SKIP: reason=OPPOSING_SIDE_BLOCKED "
                        f"market={_mkt_id[:16]} already_hold={_pos.outcome} new={signal.outcome}"
                    )
                    self.stats["orders_skipped"] += 1
                    log_signal(signal, "SKIPPED", "OPPOSING_SIDE_BLOCKED")
                    return
            # Block: mehr als EVENT_CAP Outcomes des gleichen neg_risk Events
            _neg_risk_id = getattr(signal, "neg_risk_market_id", "") or ""
            if _neg_risk_id:
                _event_cap = int(os.environ.get("COPY_EVENT_CAP", "3"))
                _held = sum(1 for _p in _open.values() if getattr(_p, "neg_risk_market_id", "") == _neg_risk_id)
                if _held >= _event_cap:
                    logger.info(
                        f"⏭️ SKIP: reason=EVENT_CAP_REACHED event={_neg_risk_id[:16]} "
                        f"held={_held}/{_event_cap}"
                    )
                    self.stats["orders_skipped"] += 1
                    log_signal(signal, "SKIPPED", f"EVENT_CAP:{_held}/{_event_cap}")
                    return

        # 0a2. WALLET_CATEGORY_FILTER — nur in Spezialgebiet des Wallets handeln
        _mq = signal.market_question or ""
        _copy_ok, _copy_reason = should_copy_trade(signal.source_wallet, _mq)
        if not _copy_ok:
            logger.info(
                f"⏭️ SKIP: reason=WALLET_CATEGORY wallet={signal.source_wallet[:18]} "
                f"| {_copy_reason} | {_mq[:50]}"
            )
            self.stats["orders_skipped"] += 1
            log_signal(signal, "SKIPPED", f"WALLET_CATEGORY:{_copy_reason}")
            return

        # 0b. MIN_MARKT_VOLUMEN-Check (nur wenn Volumen explizit bekannt und > 0)
        market_vol = getattr(signal, "market_volume_usd", None)
        if MIN_MARKT_VOLUMEN_USD > 0 and market_vol is not None and market_vol > 0 and market_vol < MIN_MARKT_VOLUMEN_USD:
            logger.info(
                f"⏭️ SKIP: reason=MIN_MARKT_VOLUMEN vol=${market_vol:,.0f} < ${MIN_MARKT_VOLUMEN_USD:,.0f} "
                f"(slug={getattr(signal, 'market_slug', signal.token_id[:12])})"
            )
            self.stats["orders_skipped"] += 1
            log_signal(signal, "SKIPPED", "MIN_MARKT_VOLUMEN")
            return

        # 0c. MAX_POSITIONS_TOTAL-Check
        if self.get_open_positions_count is not None:
            open_pos = self.get_open_positions_count()
            if open_pos >= MAX_POSITIONS_TOTAL:
                logger.info(
                    f"⏭️ SKIP: reason=MAX_POSITIONS_TOTAL ({open_pos}/{MAX_POSITIONS_TOTAL}) "
                    f"(slug={getattr(signal, 'market_slug', signal.token_id[:12])})"
                )
                self.stats["orders_skipped"] += 1
                log_signal(signal, "SKIPPED", "MAX_POSITIONS_TOTAL")
                return

        # 1. Performance der Source-Wallet prüfen
        perf = self.wallet_performance.get(signal.source_wallet)
        if perf and perf.is_decaying:
            logger.warning(
                f"⚠️  Win Rate Decay erkannt bei {get_wallet_name(signal.source_wallet)} | "
                f"Aktuelle Win Rate: {perf.recent_win_rate:.0%} — überspringe Trade"
            )
            self.stats["orders_skipped"] += 1
            log_signal(signal, "SKIPPED", "WIN_RATE_DECAY")
            return

        # 2. Wallet-Multiplikator — ggf. halbieren bei Trend-Decline
        wallet_multiplier = get_wallet_multiplier(signal.source_wallet)

        if perf and perf.is_trend_declining:
            original_mult = wallet_multiplier
            wallet_multiplier = round(wallet_multiplier / 2, 2)
            logger.warning(
                f"📉 Trend-Decline bei {get_wallet_name(signal.source_wallet)} | "
                f"Gesamt: {perf.win_rate:.0%} vs. Letzte 20: {perf.recent_win_rate:.0%} | "
                f"Multiplikator: {original_mult}x → {wallet_multiplier}x (halbiert)"
            )
            if self.on_wallet_warning:
                asyncio.create_task(self._safe_call(
                    self.on_wallet_warning,
                    get_wallet_name(signal.source_wallet),
                    perf.win_rate,
                    perf.recent_win_rate,
                    original_mult,
                    wallet_multiplier,
                ))

        # Early Entry Bonus: Markt unter $10K Volumen → 1.5x
        early_bonus = 1.0
        if getattr(signal, "is_early_entry", False):
            early_bonus = EARLY_ENTRY_MULTIPLIER
            logger.info(
                f"🌱 Early Entry Bonus {EARLY_ENTRY_MULTIPLIER}x | "
                f"Markt-Volumen: ${getattr(signal, 'market_volume_usd', 0):,.0f} "
                f"| {signal.market_question[:50]}"
            )

        combined_multiplier = wallet_multiplier * extra_multiplier * early_bonus
        scaled_signal = replace(signal, size_usdc=signal.size_usdc * combined_multiplier)

        if combined_multiplier != 1.0:
            logger.info(
                f"⚖️  Multiplikator {combined_multiplier:.1f}x für {get_wallet_name(signal.source_wallet)} "
                f"(Wallet {wallet_multiplier}x × Multi-Signal {extra_multiplier}x) | "
                f"${signal.size_usdc:.2f} → ${scaled_signal.size_usdc:.2f}"
            )

        # 3. Risiko-Check
        decision: RiskDecision = self.risk_manager.evaluate(scaled_signal)

        if not decision.allowed:
            logger.info(f"❌ Trade abgelehnt: {decision.reason}")
            self.stats["orders_skipped"] += 1
            log_signal(signal, "SKIPPED", decision.reason)
            return

        # 4. Order erstellen und weiterleiten
        order = CopyOrder(
            signal=signal,
            size_usdc=decision.adjusted_size_usdc,
            dry_run=self.config.dry_run,
            wallet_multiplier=wallet_multiplier,
            is_multi_signal=extra_multiplier > 1.0,
        )

        self.stats["orders_created"] += 1
        logger.info(f"📋 Order erstellt: {order}")
        log_signal(signal, "COPIED", None)

        if self.on_copy_order:
            await self._safe_execute(order)

    async def _safe_execute(self, order: CopyOrder):
        """Führt Order aus — fängt Fehler damit die Strategie weiterläuft."""
        await self._safe_call(self.on_copy_order, order)

    async def _safe_call(self, fn, *args):
        # DEPRECATED: Bitte safe_call_transparent-Decorator aus utils.error_handler verwenden.
        # Bleibt für Rückwärtskompatibilität, leitet nun an handle_error weiter.
        try:
            if asyncio.iscoroutinefunction(fn):
                await fn(*args)
            else:
                fn(*args)
        except Exception as e:
            logger.error(f"Fehler bei Callback {getattr(fn, '__name__', fn)}: {e}", exc_info=True)
            if _handle_error is not None:
                ctx = f"_safe_call({getattr(fn, '__name__', str(fn))[:40]})"
                try:
                    await _handle_error(e, context=ctx, severity="ERROR", telegram_alert=True, reraise=False)
                except Exception:
                    pass

    async def handle_whale_sell(self, signal: TradeSignal):
        """
        T-M03: Wird aufgerufen wenn eine tracked Wallet verkauft.
        Prüft ob wir dieselbe Position halten und triggert sofortigen Exit.
        """
        if signal.side != "SELL":
            return
        if not getattr(self.config, "whale_exit_copy_enabled", False):
            return
        if not self.get_open_positions or not self.on_whale_exit:
            return

        open_positions = self.get_open_positions()
        wallet_name = get_wallet_name(signal.source_wallet)
        market_short = signal.market_question[:50] if signal.market_question else signal.market_id[:16]

        for pos in open_positions.values():
            if pos.market_id != signal.market_id:
                continue
            if pos.source_wallet.lower() != signal.source_wallet.lower():
                continue
            logger.info(
                f"[whale_exit_copy] 🐋 {wallet_name} verkauft "
                f"'{market_short}' → wir folgen (Exit {pos.outcome})"
            )
            try:
                if asyncio.iscoroutinefunction(self.on_whale_exit):
                    await self.on_whale_exit(pos, signal)
                else:
                    self.on_whale_exit(pos, signal)
            except Exception as e:
                logger.error(f"[whale_exit_copy] on_whale_exit Fehler: {e}", exc_info=True)
            return  # nur erste Match-Position — weitere Iterationen unnötig

    def get_status(self) -> dict:
        """Gibt aktuellen Status der Strategie zurück."""
        wallet_stats = {}
        for wallet, perf in self.wallet_performance.items():
            multiplier = get_wallet_multiplier(wallet)
            wallet_stats[wallet[:10] + "..."] = {
                "win_rate": f"{perf.win_rate:.0%}",
                "recent_win_rate": f"{perf.recent_win_rate:.0%}",
                "trades": perf.trades_total,
                "pnl": f"${perf.total_pnl_usd:.2f}",
                "decaying": perf.is_decaying,
                "multiplier": f"{multiplier}x",
            }

        return {
            "strategy": "copy_trading",
            "signals_received": self.stats["signals_received"],
            "orders_created": self.stats["orders_created"],
            "orders_skipped": self.stats["orders_skipped"],
            "multi_signals": self.stats["multi_signals"],
            "wallets": wallet_stats,
        }
