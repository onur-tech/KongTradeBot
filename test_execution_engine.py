"""
test_execution_engine.py — Tests für ExecutionEngine

Testet Dry-Run, Position Tracking, Error Handling
ohne echten API-Call.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone, timedelta
from utils.config import Config
from utils.logger import setup_logger
from core.wallet_monitor import TradeSignal
from core.execution_engine import ExecutionEngine
from strategies.copy_trading import CopyOrder

setup_logger()

TEST_CONFIG = Config(
    private_key="0x" + "a" * 64,
    polymarket_address="0x" + "b" * 40,
    target_wallets=["0x" + "c" * 40],
    max_daily_loss_usd=50.0,
    max_trade_size_usd=25.0,
    min_trade_size_usd=2.0,
    copy_size_multiplier=0.05,
    dry_run=True,
)


def make_copy_order(price=0.65, size=15.0) -> CopyOrder:
    signal = TradeSignal(
        tx_hash="test_hash_123",
        source_wallet="0x" + "c" * 40,
        market_id="market_test",
        token_id="token_test",
        side="BUY",
        price=price,
        size_usdc=100.0,
        market_closes_at=datetime.now(timezone.utc) + timedelta(hours=24),
        market_question="Will BTC be above $80,000 on April 20, 2026?",
        outcome="Yes",
    )
    return CopyOrder(signal=signal, size_usdc=size, dry_run=True)


async def test_dry_run_execute():
    """Dry-Run führt Order aus ohne echten API-Call."""
    engine = ExecutionEngine(TEST_CONFIG)
    await engine.initialize()

    order = make_copy_order()
    result = await engine.execute(order)

    assert result.success == True
    assert result.dry_run == True
    assert result.order_id is not None
    assert result.filled_price == 0.65
    assert result.filled_size_usdc == 15.0

    print(f"✅ Test 1: Dry-Run Execute | {result}")


async def test_position_tracking():
    """Positionen werden korrekt nach Execute getrackt."""
    engine = ExecutionEngine(TEST_CONFIG)
    await engine.initialize()

    assert len(engine.open_positions) == 0

    order = make_copy_order()
    await engine.execute(order)

    assert len(engine.open_positions) == 1

    pos = list(engine.open_positions.values())[0]
    assert pos.outcome == "Yes"
    assert pos.entry_price == 0.65
    assert pos.size_usdc == 15.0
    assert "BTC" in pos.market_question

    print(f"✅ Test 2: Position Tracking | {pos}")


async def test_stats_tracking():
    """Statistiken werden korrekt gezählt."""
    # Frische Config mit anderen Wallets damit kein State geteilt wird
    fresh_config = Config(
        private_key="0x" + "e" * 64,
        polymarket_address="0x" + "f" * 40,
        target_wallets=["0x" + "e" * 40],
        max_daily_loss_usd=50.0,
        max_trade_size_usd=25.0,
        min_trade_size_usd=2.0,
        copy_size_multiplier=0.05,
        dry_run=True,
    )

    from core.execution_engine import ExecutionEngine as EE2
    engine = EE2(fresh_config)
    await engine.initialize()

    timestamp = int(__import__('time').time() * 1000)
    for i in range(3):
        sig = TradeSignal(
            tx_hash=f"stats_test_{timestamp}_{i}",
            source_wallet="0x" + "e" * 40,
            market_id=f"market_stats_{i}",
            token_id=f"token_stats_{i}",
            side="BUY",
            price=0.65,
            size_usdc=100.0,
            market_closes_at=datetime.now(timezone.utc) + timedelta(hours=24),
            market_question=f"Stats test market {i}",
            outcome="Yes",
        )
        await engine.execute(CopyOrder(signal=sig, size_usdc=15.0, dry_run=True))

    stats = engine.get_stats()
    assert stats["orders_attempted"] == 3, f"Expected 3, got {stats['orders_attempted']}"
    assert stats["dry_run_orders"] == 3
    assert stats["open_positions"] == 3, f"Expected 3, got {stats['open_positions']}"
    assert stats["mode"] == "DRY-RUN"

    print(f"✅ Test 3: Stats Tracking | attempted={stats['orders_attempted']}, positions={stats['open_positions']}")


async def test_positions_summary():
    """get_open_positions_summary gibt lesbare Übersicht."""
    engine = ExecutionEngine(TEST_CONFIG)
    await engine.initialize()

    await engine.execute(make_copy_order())
    summary = engine.get_open_positions_summary()

    assert len(summary) == 1
    pos = summary[0]
    assert "entry_price" in pos
    assert "invested" in pos
    assert "question" in pos
    assert "BTC" in pos["question"]

    print(f"✅ Test 4: Positions Summary | {pos}")


async def run_all():
    print("\n🧪 EXECUTION ENGINE TESTS\n" + "=" * 40)

    tests = [
        test_dry_run_execute,
        test_position_tracking,
        test_stats_tracking,
        test_positions_summary,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
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
        print("✅ Alle Tests bestanden!")
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all())
    sys.exit(0 if success else 1)
