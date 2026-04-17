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
    min_trade_size_usd: float = 0.01
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
        if not self.dry_run and self.max_portfolio_pct > 0.5:
            errors.append(f"MAX_PORTFOLIO_PCT={self.max_portfolio_pct} ist zu hoch (max 50% empfohlen)")
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
        min_trade_size_usd=float(os.getenv("MIN_TRADE_SIZE_USD", "0.01")),
        copy_size_multiplier=float(os.getenv("COPY_SIZE_MULTIPLIER", "0.05")),
        portfolio_budget_usd=float(os.getenv("PORTFOLIO_BUDGET_USD", "1000")),
        max_portfolio_pct=float(os.getenv("MAX_PORTFOLIO_PCT", "0.20")),
        max_trades_per_day=int(os.getenv("MAX_TRADES_PER_DAY", "100")),
        max_trades_per_wallet=int(os.getenv("MAX_TRADES_PER_WALLET", "20")),
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "10")),
        dry_run=os.getenv("DRY_RUN", "true").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        clob_host=os.getenv("CLOB_HOST", "https://clob.polymarket.com"),
        gamma_host=os.getenv("GAMMA_HOST", "https://gamma-api.polymarket.com"),
        chain_id=int(os.getenv("CHAIN_ID", "137")),
    )

    return config.validate()
