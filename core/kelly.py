"""Quarter-Kelly Position Sizing für Polymarket Binary YES/NO.

Formeln verifiziert gegen Meister (2024) "Application of the Kelly Criterion
to Prediction Markets" (arXiv:2412.14144) und den Standard-Kelly (Wikipedia).

Polymarket Payoff-Struktur:
  - YES @ price P: bei Win +((1-P)/P) pro $, bei Loss -100%
  - NO  @ price P: bei Win +(P/(1-P)) pro $, bei Loss -100%
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

Side = Literal["YES", "NO"]


@dataclass
class KellyResult:
    side: Side
    f_full: float         # Full-Kelly fraction
    f_quarter: float      # Quarter-Kelly fraction
    stake_usd: float      # tatsächlicher Einsatz nach Caps
    edge: float           # p_true - price (YES) oder price - p_true (NO)
    reason: str           # "OK" oder Grund für Ablehnung


def kelly_fraction_binary(p_true: float, price: float, side: Side) -> float:
    """Full-Kelly Bruchteil für Polymarket Binary.

    Returns 0.0 wenn kein +EV oder ungültige Inputs.
    """
    if not (0.0 < price < 1.0) or not (0.0 <= p_true <= 1.0):
        return 0.0
    if side == "YES":
        edge = p_true - price
        if edge <= 0.0:
            return 0.0
        return edge / (1.0 - price)
    elif side == "NO":
        edge = price - p_true
        if edge <= 0.0:
            return 0.0
        return edge / price
    raise ValueError(f"side must be YES or NO, got {side!r}")


def quarter_kelly_stake(
    p_true: float,
    price: float,
    bankroll_usd: float,
    side: Side = "YES",
    *,
    kelly_fraction: float = 0.25,
    max_pct_bankroll: float = 0.05,
    max_pct_liquidity: float = 0.02,
    available_liquidity_usd: float | None = None,
    min_edge: float = 0.03,
) -> KellyResult:
    """Berechnet den finalen Einsatz mit Risk-Caps."""
    f_full = kelly_fraction_binary(p_true, price, side)
    edge = (p_true - price) if side == "YES" else (price - p_true)

    if f_full <= 0.0:
        return KellyResult(side, 0.0, 0.0, 0.0, edge, "no_positive_edge")
    if edge < min_edge:
        return KellyResult(side, f_full, 0.0, 0.0, edge, "edge_below_minimum")

    f_q = f_full * kelly_fraction
    stake = f_q * bankroll_usd
    stake = min(stake, max_pct_bankroll * bankroll_usd)
    if available_liquidity_usd is not None and available_liquidity_usd > 0:
        stake = min(stake, max_pct_liquidity * available_liquidity_usd)
    stake = max(0.0, round(stake, 2))
    return KellyResult(side, f_full, f_q, stake, edge, "OK")
