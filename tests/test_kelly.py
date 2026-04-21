import math
from core.kelly import kelly_fraction_binary, quarter_kelly_stake

def test_yes_bet_positive_edge():
    # Markt @ 0.30, wahre P = 0.50 -> edge=0.20, Full-Kelly = 0.20/0.70 ~= 0.2857
    f = kelly_fraction_binary(0.50, 0.30, "YES")
    assert math.isclose(f, 0.2857142, rel_tol=1e-4)

def test_no_bet_positive_edge():
    # Markt @ 0.70, wahre P = 0.40 -> NO-edge = 0.30, Full-Kelly = 0.30/0.70 ~= 0.4286
    f = kelly_fraction_binary(0.40, 0.70, "NO")
    assert math.isclose(f, 0.4285714, rel_tol=1e-4)

def test_zero_edge_returns_zero():
    assert kelly_fraction_binary(0.30, 0.30, "YES") == 0.0
    assert kelly_fraction_binary(0.70, 0.70, "NO") == 0.0

def test_negative_edge_returns_zero():
    assert kelly_fraction_binary(0.20, 0.30, "YES") == 0.0
    assert kelly_fraction_binary(0.80, 0.70, "NO") == 0.0

def test_quarter_kelly_sizing_caps():
    res = quarter_kelly_stake(0.80, 0.30, 10_000, "YES")
    assert res.stake_usd == 500.0
    assert res.reason == "OK"

def test_liquidity_cap():
    res = quarter_kelly_stake(0.80, 0.30, 10_000, "YES",
                              available_liquidity_usd=1_000)
    assert res.stake_usd == 20.0

def test_edge_below_minimum():
    res = quarter_kelly_stake(0.32, 0.30, 10_000, "YES", min_edge=0.05)
    assert res.stake_usd == 0.0
    assert res.reason == "edge_below_minimum"
