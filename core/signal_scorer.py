"""
Signal-Scoring: gewichtet Whale-Signals auf 0-100 Skala.
Höherer Score = stärkeres Signal = höhere Position-Size (multiplikativ auf Kelly).
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class WalletStats:
    win_rate: float            # 0.0 - 1.0
    roi_pct: float             # can be negative
    stddev_returns: float      # volatility
    last_trade_days_ago: int
    trades_total: int          # für data sufficiency check


class SignalScorer:
    """
    Score components (max 100):
    - Win Rate   (0-30): linear 50%→100% WR, Floor bei <50% = 0 pts
    - ROI        (0-25): tanh-normalisiert, +100% ROI ≈ 25 pts, neg ROI = 0
    - Consistency(0-20): 20 × (1 - min(stddev/mean, 1.0))
    - Category   (0-15): category-spez. WR (optional)
    - Recency    (0-10): <7d=10, <30d=5, <90d=2, else=0
    """

    WEIGHTS = {"wr": 30, "roi": 25, "consistency": 20, "category": 15, "recency": 10}

    def __init__(self, config: dict = None):
        self.weights = (config or {}).get("scoring_weights", self.WEIGHTS)

    def score(self, stats: WalletStats, category_wr: float = None) -> float:
        s = 0.0
        s += self._score_wr(stats.win_rate)
        s += self._score_roi(stats.roi_pct)
        s += self._score_consistency(stats.stddev_returns, stats.roi_pct)
        if category_wr is not None:
            s += self._score_category(category_wr)
        s += self._score_recency(stats.last_trade_days_ago)

        # Data sufficiency penalty
        if stats.trades_total < 20:
            s *= 0.7  # -30% when data is sparse

        return min(100.0, max(0.0, s))

    def _score_wr(self, wr: float) -> float:
        if wr < 0.5:
            return 0.0
        return self.weights["wr"] * (wr - 0.5) / 0.5  # linear 50%→100%

    def _score_roi(self, roi: float) -> float:
        if roi <= 0:
            return 0.0
        return self.weights["roi"] * math.tanh(roi)  # diminishing returns

    def _score_consistency(self, stddev: float, mean_roi: float) -> float:
        if mean_roi <= 0 or stddev <= 0:
            return 0.0
        cv = stddev / abs(mean_roi)  # coefficient of variation
        return self.weights["consistency"] * max(0.0, 1.0 - min(cv, 1.0))

    def _score_category(self, cat_wr: float) -> float:
        if cat_wr < 0.5:
            return 0.0
        return self.weights["category"] * (cat_wr - 0.5) / 0.5

    def _score_recency(self, days_ago: int) -> float:
        w = self.weights["recency"]
        if days_ago < 7:
            return float(w)
        if days_ago < 30:
            return w * 0.5
        if days_ago < 90:
            return w * 0.2
        return 0.0

    def score_to_multiplier(self, score: float) -> float:
        """Map score 0-100 to position multiplier 0.5x-2.0x (multiplicative on Kelly)."""
        if score < 30:
            return 0.5   # weak signal: half-size
        if score < 50:
            return 0.75
        if score < 70:
            return 1.0   # standard
        if score < 85:
            return 1.5
        return 2.0       # top-tier
