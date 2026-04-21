"""Quarter-Kelly für Polymarket Binary YES/NO."""
from dataclasses import dataclass


@dataclass
class KellyResult:
    side: str
    f_full: float
    f_quarter: float
    stake_usd: float
    edge: float
    reason: str


def kelly_fraction(p_true: float, price: float, side: str = "YES") -> float:
    if not (0 < price < 1) or not (0 <= p_true <= 1):
        return 0.0
    if side.upper() == "YES":
        edge = p_true - price
        return edge / (1 - price) if edge > 0 else 0.0
    else:
        edge = price - p_true
        return edge / price if edge > 0 else 0.0


def quarter_kelly_stake(
    p_true: float,
    price: float,
    bankroll: float,
    side: str = "YES",
    kelly_frac: float = 0.25,
    max_pct: float = 0.05,
    min_edge: float = 0.03,
) -> KellyResult:
    f = kelly_fraction(p_true, price, side)
    edge = (p_true - price) if side.upper() == "YES" else (price - p_true)
    if f <= 0:
        return KellyResult(side, 0, 0, 0, edge, "no_edge")
    if edge < min_edge:
        return KellyResult(side, f, 0, 0, edge, "edge_low")
    f_q = f * kelly_frac
    stake = min(f_q * bankroll, max_pct * bankroll)
    return KellyResult(side, f, f_q, round(stake, 2), edge, "OK")
