"""Tests for core/signal_scorer.py."""
import math

import pytest

from core.signal_scorer import SignalScorer, WalletStats


def _stats(**overrides) -> WalletStats:
    defaults = dict(
        win_rate=0.70,
        roi_pct=0.50,
        stddev_returns=0.10,
        last_trade_days_ago=3,
        trades_total=50,
    )
    defaults.update(overrides)
    return WalletStats(**defaults)


# ---------------------------------------------------------------------------
# Basic score computation
# ---------------------------------------------------------------------------

def test_score_returns_float():
    scorer = SignalScorer()
    s = scorer.score(_stats())
    assert isinstance(s, float)


def test_score_bounded_0_to_100():
    scorer = SignalScorer()
    # Max possible stats
    s_max = scorer.score(_stats(win_rate=1.0, roi_pct=10.0, stddev_returns=0.01,
                                 last_trade_days_ago=1, trades_total=100), category_wr=1.0)
    assert 0.0 <= s_max <= 100.0

    # Min possible stats
    s_min = scorer.score(_stats(win_rate=0.0, roi_pct=-5.0, stddev_returns=10.0,
                                 last_trade_days_ago=200, trades_total=100))
    assert s_min == pytest.approx(0.0)


def test_score_with_category_higher_than_without():
    scorer = SignalScorer()
    base = scorer.score(_stats())
    with_cat = scorer.score(_stats(), category_wr=0.80)
    assert with_cat > base


# ---------------------------------------------------------------------------
# Win Rate component
# ---------------------------------------------------------------------------

def test_wr_below_50_contributes_zero():
    scorer = SignalScorer()
    s1 = scorer.score(_stats(win_rate=0.49))
    s2 = scorer.score(_stats(win_rate=0.0))
    # Both should have 0 WR contribution — scores should be equal
    assert s1 == pytest.approx(s2)


def test_wr_100_contributes_max():
    scorer = SignalScorer()
    # WR=100% should contribute exactly 30 pts
    wr_component = scorer._score_wr(1.0)
    assert wr_component == pytest.approx(30.0)


def test_wr_50_contributes_zero():
    scorer = SignalScorer()
    assert scorer._score_wr(0.50) == pytest.approx(0.0)


def test_wr_75_contributes_half():
    scorer = SignalScorer()
    # 75% WR is halfway between 50% and 100% → 15 pts
    assert scorer._score_wr(0.75) == pytest.approx(15.0)


# ---------------------------------------------------------------------------
# ROI component
# ---------------------------------------------------------------------------

def test_roi_negative_contributes_zero():
    scorer = SignalScorer()
    assert scorer._score_roi(-0.50) == pytest.approx(0.0)
    assert scorer._score_roi(0.0) == pytest.approx(0.0)


def test_roi_positive_contributes_positive():
    scorer = SignalScorer()
    assert scorer._score_roi(1.0) > 0


def test_roi_large_capped_by_tanh():
    scorer = SignalScorer()
    # tanh(100) ≈ 1.0, so max approaches weights["roi"] = 25
    s = scorer._score_roi(100.0)
    assert s <= 25.0
    assert s > 24.0  # should be very close to 25


# ---------------------------------------------------------------------------
# Consistency component
# ---------------------------------------------------------------------------

def test_consistency_zero_mean_roi():
    scorer = SignalScorer()
    assert scorer._score_consistency(0.1, 0.0) == pytest.approx(0.0)


def test_consistency_zero_stddev():
    scorer = SignalScorer()
    assert scorer._score_consistency(0.0, 1.0) == pytest.approx(0.0)


def test_consistency_low_cv_high_score():
    scorer = SignalScorer()
    # stddev=0.01, mean=1.0 → CV=0.01 → score ≈ 20 * (1-0.01) ≈ 19.8
    s = scorer._score_consistency(0.01, 1.0)
    assert s > 19.0


def test_consistency_high_cv_zero_score():
    scorer = SignalScorer()
    # stddev=2.0, mean=1.0 → CV=2.0, clamped to 1.0 → score = 0
    s = scorer._score_consistency(2.0, 1.0)
    assert s == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Data sufficiency penalty
# ---------------------------------------------------------------------------

def test_data_sufficiency_penalty_below_20_trades():
    scorer = SignalScorer()
    s_few = scorer.score(_stats(trades_total=10))
    s_many = scorer.score(_stats(trades_total=50))
    # Score with few trades should be ~70% of score with many trades
    assert s_few == pytest.approx(s_many * 0.7, rel=0.01)


def test_data_sufficiency_no_penalty_at_20():
    scorer = SignalScorer()
    s_19 = scorer.score(_stats(trades_total=19))
    s_20 = scorer.score(_stats(trades_total=20))
    # 19 → penalty applies, 20 → no penalty
    assert s_19 < s_20


# ---------------------------------------------------------------------------
# Recency component
# ---------------------------------------------------------------------------

def test_recency_under_7_days():
    scorer = SignalScorer()
    assert scorer._score_recency(0) == pytest.approx(10.0)
    assert scorer._score_recency(6) == pytest.approx(10.0)


def test_recency_7_to_29_days():
    scorer = SignalScorer()
    assert scorer._score_recency(7) == pytest.approx(5.0)
    assert scorer._score_recency(29) == pytest.approx(5.0)


def test_recency_30_to_89_days():
    scorer = SignalScorer()
    assert scorer._score_recency(30) == pytest.approx(2.0)
    assert scorer._score_recency(89) == pytest.approx(2.0)


def test_recency_over_90_days():
    scorer = SignalScorer()
    assert scorer._score_recency(90) == pytest.approx(0.0)
    assert scorer._score_recency(365) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# score_to_multiplier
# ---------------------------------------------------------------------------

def test_multiplier_below_30_half_size():
    scorer = SignalScorer()
    assert scorer.score_to_multiplier(0.0) == pytest.approx(0.5)
    assert scorer.score_to_multiplier(29.9) == pytest.approx(0.5)


def test_multiplier_30_to_49():
    scorer = SignalScorer()
    assert scorer.score_to_multiplier(30.0) == pytest.approx(0.75)
    assert scorer.score_to_multiplier(49.9) == pytest.approx(0.75)


def test_multiplier_50_to_69():
    scorer = SignalScorer()
    assert scorer.score_to_multiplier(50.0) == pytest.approx(1.0)
    assert scorer.score_to_multiplier(69.9) == pytest.approx(1.0)


def test_multiplier_70_to_84():
    scorer = SignalScorer()
    assert scorer.score_to_multiplier(70.0) == pytest.approx(1.5)
    assert scorer.score_to_multiplier(84.9) == pytest.approx(1.5)


def test_multiplier_85_and_above():
    scorer = SignalScorer()
    assert scorer.score_to_multiplier(85.0) == pytest.approx(2.0)
    assert scorer.score_to_multiplier(100.0) == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Config override for weights
# ---------------------------------------------------------------------------

def test_custom_weights_applied():
    custom = {"scoring_weights": {"wr": 50, "roi": 10, "consistency": 10, "category": 20, "recency": 10}}
    scorer = SignalScorer(config=custom)
    # WR=100% should now contribute 50 pts
    assert scorer._score_wr(1.0) == pytest.approx(50.0)


def test_default_weights_used_without_config():
    scorer = SignalScorer()
    assert scorer.weights == SignalScorer.WEIGHTS


# ---------------------------------------------------------------------------
# Category component
# ---------------------------------------------------------------------------

def test_category_below_50_zero():
    scorer = SignalScorer()
    assert scorer._score_category(0.49) == pytest.approx(0.0)


def test_category_100_max():
    scorer = SignalScorer()
    assert scorer._score_category(1.0) == pytest.approx(15.0)
