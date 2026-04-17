"""
test_wallet_monitor.py — Tests für WalletMonitor

Testet die Kernlogik ohne echte API-Calls:
- Deduplizierung funktioniert
- Parsen von Trade-Daten
- Risiko-Entscheidungen
- Kill-Switch

START:
    python -m pytest tests/ -v
    python tests/test_wallet_monitor.py  # Direkt ausführen
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock

from utils.config import Config
from utils.logger import setup_logger
from core.wallet_monitor import WalletMonitor, TradeSignal
from core.risk_manager import RiskManager


# Test-Config (kein echter Key nötig)
TEST_CONFIG = Config(
    private_key="0x" + "a" * 64,
    polymarket_address="0x" + "b" * 40,
    target_wallets=["0x" + "c" * 40, "0x" + "d" * 40],
    max_daily_loss_usd=50.0,
    max_trade_size_usd=25.0,
    min_trade_size_usd=2.0,
    copy_size_multiplier=0.05,
    dry_run=True,
)


def make_trade_signal(
    tx_hash="abc123",
    price=0.65,
    size_usdc=100.0,
    hours_to_close=24.0
) -> TradeSignal:
    """Erstellt ein Test-TradeSignal."""
    closes_at = datetime.now(timezone.utc) + timedelta(hours=hours_to_close)
    return TradeSignal(
        tx_hash=tx_hash,
        source_wallet="0x" + "c" * 40,
        market_id="market_123",
        token_id="token_456",
        side="BUY",
        price=price,
        size_usdc=size_usdc,
        market_closes_at=closes_at,
        market_question="Will BTC be above $70,000 on April 20?",
        outcome="Yes",
    )


# =========================================================
# TEST 1: Deduplizierung
# =========================================================
def test_deduplication():
    """Derselbe Trade darf nicht zweimal erkannt werden."""
    setup_logger()
    monitor = WalletMonitor(TEST_CONFIG)

    activity = {
        "transactionHash": "0xabc123",
        "type": "BUY",
        "price": "0.65",
        "usdcSize": "100",
        "conditionId": "market_1",
        "asset": "token_1",
        "outcome": "Yes",
    }

    # Erster Aufruf: neu
    result1 = monitor._is_new_trade(activity)
    assert result1 == True, "Erster Trade sollte als NEU erkannt werden"

    # Zweiter Aufruf: Duplikat
    result2 = monitor._is_new_trade(activity)
    assert result2 == False, "Zweiter identischer Trade sollte als DUPLIKAT erkannt werden"

    print("✅ Test 1 BESTANDEN: Deduplizierung funktioniert")


# =========================================================
# TEST 2: Trade Parsing
# =========================================================
def test_trade_parsing():
    """TradeSignal wird korrekt aus API-Daten erstellt."""
    monitor = WalletMonitor(TEST_CONFIG)

    activity = {
        "transactionHash": "0xdef456",
        "type": "BUY",
        "price": "0.72",
        "usdcSize": "250",
        "conditionId": "market_42",
        "asset": "token_99",
        "outcome": "Yes",
        "title": "Will SOL reach $200?",
    }

    signal = monitor._parse_trade(activity, "0x" + "c" * 40)

    assert signal is not None, "Signal sollte geparst werden"
    assert signal.price == 0.72
    assert signal.size_usdc == 250.0
    assert signal.market_question == "Will SOL reach $200?"
    assert signal.outcome == "Yes"
    assert signal.side == "BUY"

    print(f"✅ Test 2 BESTANDEN: Parsing funktioniert | Signal: {signal}")


# =========================================================
# TEST 3: Extrempreise werden übersprungen
# =========================================================
def test_extreme_prices_skipped():
    """Trades mit Preis > 0.99 oder < 0.01 werden übersprungen."""
    monitor = WalletMonitor(TEST_CONFIG)

    for extreme_price in ["0.001", "0.999", "0.995", "0.002"]:
        activity = {
            "transactionHash": f"hash_{extreme_price}",
            "type": "BUY",
            "price": extreme_price,
            "usdcSize": "100",
            "conditionId": "market_1",
            "asset": "token_1",
        }
        signal = monitor._parse_trade(activity, "0x" + "c" * 40)
        assert signal is None, f"Extrempreis {extreme_price} sollte None zurückgeben"

    print("✅ Test 3 BESTANDEN: Extrempreise werden korrekt übersprungen")


# =========================================================
# TEST 4: RiskManager - Proportionales Sizing
# =========================================================
def test_proportional_sizing():
    """Sizing wird korrekt proportional berechnet."""
    risk = RiskManager(TEST_CONFIG)

    # Whale setzt $1000 → wir setzen 5% = $50, aber max ist $25
    signal = make_trade_signal(size_usdc=1000.0)
    decision = risk.evaluate(signal)

    assert decision.allowed == True
    assert decision.adjusted_size_usdc == 25.0  # Geclipt auf max_trade_size

    # Whale setzt $100 → wir setzen 5% = $5
    signal2 = make_trade_signal(tx_hash="xyz789", size_usdc=100.0)
    decision2 = risk.evaluate(signal2)

    assert decision2.allowed == True
    assert decision2.adjusted_size_usdc == 5.0

    print(f"✅ Test 4 BESTANDEN: Sizing korrekt | $1000 Whale → ${decision.adjusted_size_usdc:.2f} | $100 Whale → ${decision2.adjusted_size_usdc:.2f}")


# =========================================================
# TEST 5: Kill-Switch
# =========================================================
def test_kill_switch():
    """Kill-Switch stoppt alle Trades nach Tages-Verlustlimit."""
    risk = RiskManager(TEST_CONFIG)  # Limit: $50

    # Verluste akkumulieren
    risk.record_trade_result(-30.0)
    risk.record_trade_result(-25.0)  # Gesamt: $55 > Limit $50

    assert risk._kill_switch_active == True, "Kill-Switch sollte aktiv sein"

    # Nächster Trade wird abgelehnt
    signal = make_trade_signal(tx_hash="kill_test")
    decision = risk.evaluate(signal)

    assert decision.allowed == False
    assert "Kill-Switch" in decision.reason

    print(f"✅ Test 5 BESTANDEN: Kill-Switch aktiviert nach ${risk._daily_loss_usd:.2f} Verlust")


# =========================================================
# TEST 6: Markt zu kurz / zu lang
# =========================================================
def test_market_timing():
    """Märkte die zu bald oder zu spät schließen werden übersprungen."""
    risk = RiskManager(TEST_CONFIG)

    # Zu bald (<1h)
    signal_soon = make_trade_signal(tx_hash="soon", hours_to_close=0.5)
    decision = risk.evaluate(signal_soon)
    assert decision.allowed == False, "Markt der in 30min schließt sollte abgelehnt werden"

    # Perfekt (24h)
    signal_good = make_trade_signal(tx_hash="good", hours_to_close=24.0)
    decision2 = risk.evaluate(signal_good)
    assert decision2.allowed == True, "Markt der in 24h schließt sollte erlaubt sein"

    # Zu lang (>72h)
    signal_long = make_trade_signal(tx_hash="long", hours_to_close=100.0)
    decision3 = risk.evaluate(signal_long)
    assert decision3.allowed == False, "Markt der in 100h schließt sollte abgelehnt werden"

    print(f"✅ Test 6 BESTANDEN: Timing-Filter funktioniert korrekt")


# =========================================================
# ALLE TESTS AUSFÜHREN
# =========================================================
if __name__ == "__main__":
    print("\n🧪 POLYMARKET BOT — TESTS\n" + "=" * 40)

    tests = [
        test_deduplication,
        test_trade_parsing,
        test_extreme_prices_skipped,
        test_proportional_sizing,
        test_kill_switch,
        test_market_timing,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FEHLER in {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"💥 CRASH in {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 40}")
    print(f"Ergebnis: {passed}/{passed + failed} Tests bestanden")

    if failed == 0:
        print("✅ Alle Tests bestanden! Bot ist bereit für Dry-Run.")
    else:
        print(f"❌ {failed} Tests fehlgeschlagen.")
        sys.exit(1)
