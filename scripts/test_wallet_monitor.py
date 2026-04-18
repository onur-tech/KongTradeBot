"""
Unit-Tests für WalletMonitor.get_recent_sells()
pytest scripts/test_wallet_monitor.py -v
"""

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.wallet_monitor import WalletMonitor


def _make_monitor():
    cfg = MagicMock()
    cfg.target_wallets = []
    cfg.dry_run = True
    cfg.poll_interval_seconds = 10
    cfg.min_whale_trade_size_usd = 5.0
    m = WalletMonitor(cfg)
    m._recent_sells_cache = {}  # isoliert pro Test
    return m


def _run(coro):
    return asyncio.run(coro)


def _sell_activity(condition_id="cond_xyz", ts_offset_s=0, price=0.72, size=50.0):
    """Hilfsfunktion: erzeugt ein SELL-Activity-Dict wie die API es liefert."""
    return {
        "side": "SELL",
        "conditionId": condition_id,
        "outcome": "Yes",
        "price": str(price),
        "size": str(size),
        "timestamp": str(time.time() - ts_offset_s),
        "transactionHash": f"0xabcdef{ts_offset_s:04d}",
    }


def _mock_session_response(activities: list):
    """Erstellt eine aiohttp-Session-Mock die `activities` zurückgibt."""
    resp_mock = AsyncMock()
    resp_mock.status = 200
    resp_mock.json = AsyncMock(return_value=activities)
    resp_mock.__aenter__ = AsyncMock(return_value=resp_mock)
    resp_mock.__aexit__ = AsyncMock(return_value=False)

    session_mock = MagicMock()
    session_mock.closed = False
    session_mock.get = MagicMock(return_value=resp_mock)
    session_mock.close = AsyncMock()
    return session_mock


# ── Test 1: Rückgabe ist Liste von Dicts mit korrekten Feldern ────────────────

def test_get_recent_sells_returns_list_of_dicts():
    monitor = _make_monitor()
    monitor._session = _mock_session_response([_sell_activity()])

    result = _run(monitor.get_recent_sells("0xWALLET1", minutes=60))

    assert isinstance(result, list)
    assert len(result) == 1
    entry = result[0]
    assert "condition_id" in entry
    assert "outcome" in entry
    assert "shares_sold" in entry
    assert "price" in entry
    assert "timestamp" in entry
    assert "tx_hash" in entry


# ── Test 2: Zeitfilter — zu alte Sells werden rausgefiltert ──────────────────

def test_get_recent_sells_filters_by_time_window():
    monitor = _make_monitor()
    # Ein Sell vor 30 Min (innerhalb 60 Min → drin)
    # Ein Sell vor 90 Min (außerhalb 60 Min → raus)
    activities = [
        _sell_activity("cond_a", ts_offset_s=1800),   # 30 min alt → drin
        _sell_activity("cond_b", ts_offset_s=5400),   # 90 min alt → raus
    ]
    monitor._session = _mock_session_response(activities)

    result = _run(monitor.get_recent_sells("0xWALLET1", minutes=60))

    cids = [r["condition_id"] for r in result]
    assert "cond_a" in cids, "30-min-alter Sell muss enthalten sein"
    assert "cond_b" not in cids, "90-min-alter Sell muss rausgefiltert werden"


# ── Test 3: Keine Aktivität → leere Liste ────────────────────────────────────

def test_get_recent_sells_returns_empty_when_no_activity():
    monitor = _make_monitor()
    monitor._session = _mock_session_response([])  # API liefert keine Einträge

    result = _run(monitor.get_recent_sells("0xWALLET_INACTIVE", minutes=60))

    assert result == []


# ── Test 4: API-Fehler → leere Liste, keine Exception ────────────────────────

def test_get_recent_sells_handles_api_error_gracefully():
    monitor = _make_monitor()

    resp_mock = AsyncMock()
    resp_mock.status = 500
    resp_mock.__aenter__ = AsyncMock(return_value=resp_mock)
    resp_mock.__aexit__ = AsyncMock(return_value=False)
    session_mock = MagicMock()
    session_mock.closed = False
    session_mock.get = MagicMock(return_value=resp_mock)
    monitor._session = session_mock

    result = _run(monitor.get_recent_sells("0xWALLET_ERROR", minutes=60))
    assert result == [], "Bei API-Fehler muss [] zurückkommen, keine Exception"


# ── Test 5: Cache funktioniert — zweiter Call ohne API ───────────────────────

def test_get_recent_sells_cache_works():
    monitor = _make_monitor()
    call_count = 0

    async def patched_fetch(wallet, minutes):
        nonlocal call_count
        call_count += 1
        return [{"condition_id": "cond_cached", "outcome": "Yes",
                 "shares_sold": 10.0, "price": 0.5, "timestamp": time.time(), "tx_hash": "0x1"}]

    # Ersten Call machen (setzt Cache)
    wallet = "0xtest_cache"
    monitor._recent_sells_cache[wallet.lower()] = (time.time(), [
        {"condition_id": "cond_cached", "outcome": "Yes",
         "shares_sold": 10.0, "price": 0.5, "timestamp": time.time(), "tx_hash": "0x1"}
    ])

    monitor._session = _mock_session_response([_sell_activity()])
    result = _run(monitor.get_recent_sells(wallet, minutes=60))

    # Session darf NICHT aufgerufen werden (Cache-Hit)
    monitor._session.get.assert_not_called()
    assert len(result) == 1
    assert result[0]["condition_id"] == "cond_cached"


# ── Test 6: BUY-Activities werden nicht als Sells zurückgegeben ──────────────

def test_buy_activities_not_included():
    monitor = _make_monitor()
    activities = [
        {"side": "BUY", "conditionId": "cond_buy", "outcome": "Yes",
         "price": "0.40", "size": "20.0", "timestamp": str(time.time()),
         "transactionHash": "0xbuy001"},
        _sell_activity("cond_sell"),
    ]
    monitor._session = _mock_session_response(activities)

    result = _run(monitor.get_recent_sells("0xWALLET1", minutes=60))

    cids = [r["condition_id"] for r in result]
    assert "cond_buy" not in cids, "BUY-Aktivitäten dürfen nicht in Sell-Liste auftauchen"
    assert "cond_sell" in cids


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
