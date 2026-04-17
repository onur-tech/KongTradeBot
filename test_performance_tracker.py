"""
test_performance_tracker.py — Tests für PerformanceTracker
"""

import sys, os, shutil, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.disable(logging.CRITICAL)

from core.performance_tracker import PerformanceTracker

TEST_DATA_DIR = "/tmp/test_tracker_data"


def fresh_tracker() -> PerformanceTracker:
    if os.path.exists(TEST_DATA_DIR):
        shutil.rmtree(TEST_DATA_DIR)
    return PerformanceTracker(data_dir=TEST_DATA_DIR)


def test_record_entry_and_exit():
    """Trade öffnen und schließen."""
    t = fresh_tracker()

    trade = t.record_entry(
        trade_id="trade_001",
        source_wallet="0xabc",
        market_question="Will BTC be above $80k?",
        outcome="Yes",
        market_id="market_1",
        entry_price=0.65,
        entry_size_usdc=15.0,
        dry_run=True,
    )

    assert trade.status == "OPEN"
    assert trade.entry_price == 0.65

    t.record_exit("trade_001", pnl_usdc=5.77)

    closed = t._trades["trade_001"]
    assert closed.status == "RESOLVED"
    assert closed.is_win == True
    assert closed.pnl_usdc == 5.77

    print("✅ Test 1: Entry + Exit funktioniert")


def test_wallet_stats():
    """Wallet-Statistiken werden korrekt berechnet."""
    t = fresh_tracker()

    for i in range(5):
        t.record_entry(f"t{i}", "0xwallet", f"Frage {i}", "Yes", f"m{i}", 0.5, 10.0)

    # 3 Gewinne, 2 Verluste
    t.record_exit("t0", pnl_usdc=5.0)
    t.record_exit("t1", pnl_usdc=3.0)
    t.record_exit("t2", pnl_usdc=-8.0)
    t.record_exit("t3", pnl_usdc=4.0)
    t.record_exit("t4", pnl_usdc=-6.0)

    stats = t._get_wallet_stats("0xwallet")
    assert stats.trades_won == 3
    assert stats.trades_lost == 2
    assert abs(stats.win_rate - 0.6) < 0.01
    assert abs(stats.total_pnl_usdc - (5+3-8+4-6)) < 0.01

    print(f"✅ Test 2: Wallet Stats | Win Rate: {stats.win_rate:.0%} | PnL: ${stats.total_pnl_usdc:.2f}")


def test_performance_report():
    """Report enthält alle wichtigen Metriken."""
    t = fresh_tracker()

    for i in range(12):
        t.record_entry(f"r{i}", "0xtest", f"Markt {i}", "Yes", f"m{i}", 0.6, 20.0, market_category="crypto")
        pnl = 8.0 if i % 3 != 0 else -12.0
        t.record_exit(f"r{i}", pnl_usdc=pnl)

    report = t.get_performance_report()
    assert "gesamt" in report
    assert "wallets" in report
    assert "trend" in report

    g = report["gesamt"]
    assert g["trades_closed"] == "12" or int(g["trades_closed"]) == 12

    print(f"✅ Test 3: Performance Report | Win Rate: {report['gesamt']['win_rate']} | Trend: {report['trend']}")


def test_tax_csv_export():
    """CSV-Export für Finanzamt."""
    t = fresh_tracker()

    t.record_entry("tax1", "0xabc", "Will SOL hit $200?", "Yes", "m1", 0.70, 25.0)
    t.record_exit("tax1", pnl_usdc=10.71)

    t.record_entry("tax2", "0xabc", "Will BTC drop below $60k?", "No", "m2", 0.30, 15.0)
    t.record_exit("tax2", pnl_usdc=-15.0)

    csv_path = t.export_tax_csv(year=2026)
    assert os.path.exists(csv_path)

    with open(csv_path) as f:
        content = f.read()

    assert "USDC (Polymarket)" in content
    assert "SOL" in content
    assert "§22 EStG" in content

    print(f"✅ Test 4: Tax CSV exportiert | Datei: {csv_path}")


def test_yearly_summary():
    """Jahres-Zusammenfassung für Steuererklärung."""
    t = fresh_tracker()

    # 3 Trades: +800, +400, -100 → Netto +1100 → steuerpflichtig
    for i, pnl in enumerate([800.0, 400.0, -100.0]):
        t.record_entry(f"y{i}", "0xabc", f"Frage {i}", "Yes", f"m{i}", 0.5, abs(pnl))
        t.record_exit(f"y{i}", pnl_usdc=pnl)

    summary = t.get_yearly_summary(2026)
    assert summary["netto_pnl_usd"] == 1100.0
    assert summary["steuerpflichtig"] == True

    print(f"✅ Test 5: Jahres-Summary | Netto: ${summary['netto_pnl_usd']} | Steuerpflichtig: {summary['steuerpflichtig']}")
    print(f"   → {summary['hinweis']}")


def test_persistence():
    """Trades überleben Bot-Neustart."""
    t1 = fresh_tracker()
    t1.record_entry("persist1", "0xabc", "Test", "Yes", "m1", 0.5, 10.0)
    t1.record_exit("persist1", pnl_usdc=5.0)

    # Neuer Tracker, gleicher Ordner → lädt aus Datei
    t2 = PerformanceTracker(data_dir=TEST_DATA_DIR)
    assert "persist1" in t2._trades
    assert t2._trades["persist1"].pnl_usdc == 5.0

    print("✅ Test 6: Persistenz funktioniert — Trades überleben Neustart")


if __name__ == "__main__":
    print("\n🧪 PERFORMANCE TRACKER TESTS\n" + "=" * 40)
    tests = [
        test_record_entry_and_exit,
        test_wallet_stats,
        test_performance_report,
        test_tax_csv_export,
        test_yearly_summary,
        test_persistence,
    ]
    passed = failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: {e}")
            import traceback; traceback.print_exc()
            failed += 1

    print(f"\n{'='*40}")
    print(f"Ergebnis: {passed}/{passed+failed} Tests bestanden")
    if failed == 0:
        print("✅ Alle Tests bestanden!")

    # Cleanup
    if os.path.exists(TEST_DATA_DIR):
        shutil.rmtree(TEST_DATA_DIR)
