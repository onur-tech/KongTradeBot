#!/usr/bin/env python3
"""
scripts/test_slippage.py — Unit-Tests für slippage_tracker + slippage_analyzer
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import utils.slippage_tracker as st_mod
from utils.slippage_analyzer import (
    compute_daily_stats, compute_weekly_stats,
    compute_by_wallet, compute_by_market_category,
    compute_by_signal_type, get_today_alert_status,
)


# ── Hilfsfunktionen ──────────────────────────────────────────────────────────

def _make_entry(whale_price=0.50, our_price=0.55, dry_run=False,
                category="politics", is_multi=False, wallet="0xABCD..."):
    return {
        "timestamp": "2026-04-19T10:00:00+00:00",
        "market":    "Test-Markt",
        "market_id": "0xMARKET",
        "outcome":   "Yes",
        "whale_wallet": wallet,
        "whale_price": round(whale_price, 4),
        "our_price":   round(our_price, 4),
        "delta_cents": round((our_price - whale_price) * 100, 3),
        "delta_bps":   round(((our_price - whale_price) / whale_price) * 10_000, 1),
        "our_size_usdc": 5.0,
        "detection_lag_seconds": 2.5,
        "category": category,
        "is_multi_signal": is_multi,
        "dry_run": dry_run,
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_log_slippage_writes_entry():
    """log_slippage() schreibt Eintrag in JSONL-Datei."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "slippage_log.jsonl"
        with patch.object(st_mod, "SLIPPAGE_LOG", log_file), \
             patch.object(st_mod, "DATA_DIR", Path(tmpdir)):
            entry = st_mod.log_slippage(
                whale_price=0.50, our_price=0.55,
                market="Test", market_id="0xABC", outcome="Yes",
                whale_wallet="0xWHALE123", our_size_usdc=5.0,
                category="politics", is_multi_signal=False,
                detection_lag_seconds=1.5, dry_run=False,
            )
        assert log_file.exists(), "JSONL-Datei wurde nicht erstellt"
        lines = [l for l in log_file.read_text().splitlines() if l.strip()]
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert abs(data["delta_cents"] - 5.0) < 0.01, f"delta_cents falsch: {data['delta_cents']}"
        assert abs(data["delta_bps"] - 1000.0) < 1.0
    print("  ✅ test_log_slippage_writes_entry")


def test_dry_run_entry_excluded_from_load():
    """load_entries() ignoriert dry_run-Einträge."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "slippage_log.jsonl"
        entries = [_make_entry(dry_run=True), _make_entry(dry_run=False)]
        log_file.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
        with patch.object(st_mod, "SLIPPAGE_LOG", log_file):
            loaded = st_mod.load_entries()
        assert len(loaded) == 1, f"Erwartet 1 Eintrag, bekommen {len(loaded)}"
        assert not loaded[0]["dry_run"]
    print("  ✅ test_dry_run_entry_excluded_from_load")


def test_compute_daily_stats():
    """compute_daily_stats() berechnet Mittelwert korrekt."""
    entries = [
        _make_entry(whale_price=0.40, our_price=0.44),  # delta = 4¢
        _make_entry(whale_price=0.60, our_price=0.68),  # delta = 8¢
    ]
    with patch("utils.slippage_analyzer.load_entries", return_value=entries):
        stats = compute_daily_stats()
    assert len(stats) == 1
    day_stats = list(stats.values())[0]
    assert abs(day_stats["mean"] - 6.0) < 0.1, f"mean falsch: {day_stats['mean']}"
    assert day_stats["count"] == 2
    print("  ✅ test_compute_daily_stats")


def test_alert_triggered_above_threshold():
    """alert=True wenn Tages-Mittelwert > ALERT_THRESHOLD_CENTS (6¢)."""
    entries = [_make_entry(whale_price=0.40, our_price=0.48)]  # delta = 8¢
    with patch("utils.slippage_analyzer.load_entries", return_value=entries):
        stats = compute_daily_stats()
    day_stats = list(stats.values())[0]
    assert day_stats["alert"] is True, "Alert sollte True sein bei 8¢ > 6¢"
    print("  ✅ test_alert_triggered_above_threshold")


def test_compute_by_wallet():
    """compute_by_wallet() gruppiert nach whale_wallet korrekt."""
    entries = [
        _make_entry(whale_price=0.50, our_price=0.55, wallet="0xAAA..."),
        _make_entry(whale_price=0.50, our_price=0.57, wallet="0xBBB..."),
        _make_entry(whale_price=0.50, our_price=0.56, wallet="0xAAA..."),
    ]
    with patch("utils.slippage_analyzer.load_entries", return_value=entries):
        result = compute_by_wallet()
    assert "0xAAA..." in result
    assert result["0xAAA..."]["count"] == 2
    print("  ✅ test_compute_by_wallet")


def test_compute_by_signal_type():
    """compute_by_signal_type() trennt single vs. multi korrekt."""
    entries = [
        _make_entry(whale_price=0.50, our_price=0.52, is_multi=False),
        _make_entry(whale_price=0.50, our_price=0.52, is_multi=False),
        _make_entry(whale_price=0.50, our_price=0.56, is_multi=True),
    ]
    with patch("utils.slippage_analyzer.load_entries", return_value=entries):
        result = compute_by_signal_type()
    assert result["single"]["count"] == 2
    assert result["multi"]["count"] == 1
    assert result["multi"]["mean"] > result["single"]["mean"]
    print("  ✅ test_compute_by_signal_type")


# ── Runner ────────────────────────────────────────────────────────────────────

def run():
    tests = [
        test_log_slippage_writes_entry,
        test_dry_run_entry_excluded_from_load,
        test_compute_daily_stats,
        test_alert_triggered_above_threshold,
        test_compute_by_wallet,
        test_compute_by_signal_type,
    ]
    ok = fail = 0
    for t in tests:
        try:
            t()
            ok += 1
        except Exception as e:
            fail += 1
            import traceback
            print(f"  ❌ FAIL {t.__name__}: {e}")
            traceback.print_exc()

    total = len(tests)
    print(f"\n{'✅ Alle' if fail == 0 else '⚠️ '}{ok}/{total} Tests bestanden"
          + (f" | {fail} Fehler" if fail else ""))
    return fail == 0


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
