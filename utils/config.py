"""
config.py — Konfiguration aus .env laden und validieren
"""
import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv
load_dotenv()

@dataclass
class Config:
    # Wallet
    private_key: str = ""
    polymarket_address: str = ""

    # Copy Trading Targets
    target_wallets: List[str] = field(default_factory=list)

    # Risiko Management
    max_daily_loss_usd: float = 50.0
    max_trade_size_usd: float = 25.0
    min_trade_size_usd: float = 0.50
    min_whale_trade_size_usd: float = 5.00
    copy_size_multiplier: float = 0.05

    # Portfolio Limits
    portfolio_budget_usd: float = 1000.0        # Gesamtbudget deines Kontos
    max_portfolio_pct: float = 0.20             # Max 20% des Budgets gleichzeitig im Rennen
    max_trades_per_day: int = 100               # Max Trades pro Tag
    max_trades_per_wallet: int = 20             # Max Trades pro Wallet pro Tag

    # Bot Einstellungen
    poll_interval_seconds: int = 10
    dry_run: bool = True
    log_level: str = "INFO"

    # Exit-Manager
    exit_enabled: bool = True
    exit_dry_run: bool = True            # WICHTIG: Erste 24h nur loggen, nicht traden
    exit_loop_interval: int = 60
    exit_tp1_threshold: float = 0.30
    exit_tp1_sell_ratio: float = 0.40
    exit_tp2_threshold: float = 0.60
    exit_tp2_sell_ratio: float = 0.40
    exit_tp3_threshold: float = 1.00
    exit_tp3_sell_ratio: float = 0.15
    exit_multi_signal_boost_min: int = 3
    exit_tp1_threshold_boost: float = 0.50
    exit_tp2_threshold_boost: float = 0.90
    exit_tp3_threshold_boost: float = 1.50
    exit_trail_activation: float = 0.12
    exit_trail_distance_liquid: float = 0.07
    exit_trail_distance_thin: float = 0.10
    exit_trail_liquidity_threshold: float = 50000.0
    exit_min_position_usdc: float = 3.0
    exit_min_hours_to_close: float = 24.0
    # Price-trigger ≥Xc Auto-Sell
    exit_price_trigger_cents: float = 95.0
    exit_price_trigger_stability_min: int = 10
    exit_daily_sell_cap_usd: float = 200.0
    exit_auto_sell_emergency_stop: bool = False
    # Stop-Loss T-M04e
    exit_sl_enabled: bool = True
    exit_sl_time_price_hours: float = 24.0
    exit_sl_time_price_cents: float = 0.15
    exit_sl_drawdown_pct: float = 0.30
    exit_sl_drawdown_min_entry: float = 0.40
    exit_sl_cooldown_after_entry_min: int = 60
    exit_sl_min_price_to_sell: float = 0.02
    exit_sl_max_events_per_hour: int = 3
    exit_sl_spread_max: float = 0.05

    # Crypto-Daily Single-Signal
    crypto_daily_single_signal: bool = True

    # T-M03: Whale-Exit-Copy
    whale_exit_copy_enabled: bool = True

    # API
    clob_host: str = "https://clob.polymarket.com"
    gamma_host: str = "https://gamma-api.polymarket.com"
    chain_id: int = 137

    @property
    def max_total_invested_usd(self) -> float:
        """Dynamisches Limit: max_portfolio_pct % des Gesamtbudgets."""
        return self.portfolio_budget_usd * self.max_portfolio_pct

    def validate(self):
        errors = []
        if not self.dry_run:
            if not self.private_key or self.private_key == "0xDEIN_PRIVATE_KEY_HIER":
                errors.append("PRIVATE_KEY fehlt oder ist noch Beispielwert")
            if not self.polymarket_address or self.polymarket_address == "0xDEINE_POLYMARKET_ADRESSE":
                errors.append("POLYMARKET_ADDRESS fehlt oder ist noch Beispielwert")
        if not self.target_wallets:
            errors.append("TARGET_WALLETS fehlt — mindestens eine Wallet-Adresse angeben")
        if self.copy_size_multiplier > 0.5:
            errors.append(f"COPY_SIZE_MULTIPLIER={self.copy_size_multiplier} ist zu hoch (max 0.5)")
        # NUR im Live-Modus prüfen — Dry-Run darf 99% haben für maximale Daten
        if not self.dry_run and self.max_portfolio_pct > 0.9:
            errors.append(f"MAX_PORTFOLIO_PCT={self.max_portfolio_pct} ist zu hoch (max 90% empfohlen)")
        if errors:
            raise ValueError(f"Config-Fehler:\n" + "\n".join(f"  - {e}" for e in errors))
        return self


def load_config() -> Config:
    raw_wallets = os.getenv("TARGET_WALLETS", "")
    target_wallets = [w.strip() for w in raw_wallets.split(",") if w.strip()]

    config = Config(
        private_key=os.getenv("PRIVATE_KEY", ""),
        polymarket_address=os.getenv("POLYMARKET_ADDRESS", ""),
        target_wallets=target_wallets,
        max_daily_loss_usd=float(os.getenv("MAX_DAILY_LOSS_USD", "50")),
        max_trade_size_usd=float(os.getenv("MAX_TRADE_SIZE_USD", "25")),
        min_trade_size_usd=float(os.getenv("MIN_TRADE_SIZE_USD", "0.50")),
        min_whale_trade_size_usd=float(os.getenv("MIN_WHALE_TRADE_SIZE_USD", "5.00")),
        copy_size_multiplier=float(os.getenv("COPY_SIZE_MULTIPLIER", "0.05")),
        portfolio_budget_usd=float(os.getenv("PORTFOLIO_BUDGET_USD", "1000")),
        max_portfolio_pct=float(os.getenv("MAX_PORTFOLIO_PCT", "0.20")),
        max_trades_per_day=int(os.getenv("MAX_TRADES_PER_DAY", "100")),
        max_trades_per_wallet=int(os.getenv("MAX_TRADES_PER_WALLET", "20")),
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "10")),
        dry_run=os.getenv("DRY_RUN", "true").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        exit_enabled=os.getenv("EXIT_ENABLED", "true").lower() == "true",
        exit_dry_run=os.getenv("EXIT_DRY_RUN", "true").lower() == "true",
        exit_loop_interval=int(os.getenv("EXIT_LOOP_INTERVAL", "60")),
        exit_tp1_threshold=float(os.getenv("EXIT_TP1_THRESHOLD", "0.30")),
        exit_tp1_sell_ratio=float(os.getenv("EXIT_TP1_SELL_RATIO", "0.40")),
        exit_tp2_threshold=float(os.getenv("EXIT_TP2_THRESHOLD", "0.60")),
        exit_tp2_sell_ratio=float(os.getenv("EXIT_TP2_SELL_RATIO", "0.40")),
        exit_tp3_threshold=float(os.getenv("EXIT_TP3_THRESHOLD", "1.00")),
        exit_tp3_sell_ratio=float(os.getenv("EXIT_TP3_SELL_RATIO", "0.15")),
        exit_multi_signal_boost_min=int(os.getenv("EXIT_MULTI_SIGNAL_BOOST_MIN", "3")),
        exit_tp1_threshold_boost=float(os.getenv("EXIT_TP1_THRESHOLD_BOOST", "0.50")),
        exit_tp2_threshold_boost=float(os.getenv("EXIT_TP2_THRESHOLD_BOOST", "0.90")),
        exit_tp3_threshold_boost=float(os.getenv("EXIT_TP3_THRESHOLD_BOOST", "1.50")),
        exit_trail_activation=float(os.getenv("EXIT_TRAIL_ACTIVATION", "0.12")),
        exit_trail_distance_liquid=float(os.getenv("EXIT_TRAIL_DISTANCE_LIQUID", "0.07")),
        exit_trail_distance_thin=float(os.getenv("EXIT_TRAIL_DISTANCE_THIN", "0.10")),
        exit_trail_liquidity_threshold=float(os.getenv("EXIT_TRAIL_LIQUIDITY_THRESHOLD", "50000")),
        exit_min_position_usdc=float(os.getenv("EXIT_MIN_POSITION_USDC", "3.0")),
        exit_min_hours_to_close=float(os.getenv("EXIT_MIN_HOURS_TO_CLOSE", "24.0")),
        exit_price_trigger_cents=float(os.getenv("TAKE_PROFIT_PRICE_CENTS", "95")),
        exit_price_trigger_stability_min=int(os.getenv("TAKE_PROFIT_STABILITY_MINUTES", "10")),
        exit_daily_sell_cap_usd=float(os.getenv("DAILY_SELL_CAP_USD", "200")),
        exit_auto_sell_emergency_stop=os.getenv("AUTO_SELL_EMERGENCY_STOP", "false").lower() == "true",
        exit_sl_enabled=os.getenv("EXIT_SL_ENABLED", "true").lower() == "true",
        exit_sl_time_price_hours=float(os.getenv("EXIT_SL_TIME_PRICE_HOURS", "24.0")),
        exit_sl_time_price_cents=float(os.getenv("EXIT_SL_TIME_PRICE_CENTS", "0.15")),
        exit_sl_drawdown_pct=float(os.getenv("EXIT_SL_DRAWDOWN_PCT", "0.30")),
        exit_sl_drawdown_min_entry=float(os.getenv("EXIT_SL_DRAWDOWN_MIN_ENTRY", "0.40")),
        exit_sl_cooldown_after_entry_min=int(os.getenv("EXIT_SL_COOLDOWN_MINUTES", "60")),
        exit_sl_min_price_to_sell=float(os.getenv("EXIT_SL_MIN_PRICE", "0.02")),
        exit_sl_max_events_per_hour=int(os.getenv("EXIT_SL_MAX_PER_HOUR", "3")),
        exit_sl_spread_max=float(os.getenv("EXIT_SL_SPREAD_MAX", "0.05")),
        crypto_daily_single_signal=os.getenv("CRYPTO_DAILY_SINGLE_SIGNAL", "true").lower() == "true",
        whale_exit_copy_enabled=os.getenv("WHALE_EXIT_COPY_ENABLED", "true").lower() == "true",
        clob_host=os.getenv("CLOB_HOST", "https://clob.polymarket.com"),
        gamma_host=os.getenv("GAMMA_HOST", "https://gamma-api.polymarket.com"),
        chain_id=int(os.getenv("CHAIN_ID", "137")),
    )

    return config.validate()
