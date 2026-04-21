"""
KongWeather Tier-Architektur
3 separate Decision-Engines für Weather-Trading

TIER 1: 6 Stationen tief kalibriert — Hauptprofit-Generator
TIER 2: 15-25 Stationen breit — Variance-Shield + Edge-Discovery
TIER 3: Barbell Lottery-Tickets — Hans323-Style
"""

# ═══════════════════════════════════════
# TIER 1 — DEEP CALIBRATED STATIONS
# ═══════════════════════════════════════
TIER1_STATIONS = {
    "New York City": {
        "icao": "KLGA",
        "min_edge": 0.15,
        "max_price": 0.85,
        "kelly_fraction": 0.25,
        "max_bankroll_pct": 0.10,
        "use_hrrr": True,
        "use_ensemble": True,
        "tier": 1,
    },
    "London": {
        "icao": "EGLC",
        "min_edge": 0.15,
        "max_price": 0.85,
        "kelly_fraction": 0.25,
        "max_bankroll_pct": 0.10,
        "use_hrrr": False,
        "use_ensemble": True,
        "tier": 1,
    },
    "Seoul": {
        "icao": "RKSI",
        "min_edge": 0.15,
        "max_price": 0.85,
        "kelly_fraction": 0.25,
        "max_bankroll_pct": 0.10,
        "use_hrrr": False,
        "use_ensemble": True,
        "seasonal_bias": {"Q1": -1.98, "Q2": -1.74, "Q3": 0.0, "Q4": 0.0},
        "tier": 1,
    },
    "Chicago": {
        "icao": "KORD",
        "min_edge": 0.15,
        "max_price": 0.85,
        "kelly_fraction": 0.25,
        "max_bankroll_pct": 0.10,
        "use_hrrr": True,
        "use_ensemble": True,
        "tier": 1,
    },
    "Tokyo": {
        "icao": "RJTT",
        "min_edge": 0.15,
        "max_price": 0.85,
        "kelly_fraction": 0.25,
        "max_bankroll_pct": 0.10,
        "use_hrrr": False,
        "use_ensemble": True,
        "tier": 1,
    },
    "Paris": {
        "icao": "LFPB",
        "min_edge": 0.15,
        "max_price": 0.85,
        "kelly_fraction": 0.25,
        "max_bankroll_pct": 0.10,
        "use_hrrr": False,
        "use_ensemble": True,
        "tier": 1,
    },
}

# ═══════════════════════════════════════
# TIER 2 — BROAD SCATTER (gopfan2 Style)
# ═══════════════════════════════════════
TIER2_CONFIG = {
    "min_edge": 0.10,
    "max_price_yes": 0.12,
    "min_price_no": 0.50,
    "kelly_fraction": 0.10,
    "max_bankroll_pct": 0.005,
    "fixed_size_usd": 1.0,
    "use_hrrr": False,
    "use_ensemble": False,
    "tier": 2,
}

TIER2_EXCLUDED = set(TIER1_STATIONS.keys())

# ═══════════════════════════════════════
# TIER 3 — BARBELL (Hans323 Style)
# ═══════════════════════════════════════
TIER3_CONFIG = {
    "min_edge": 0.30,
    "max_price": 0.08,
    "kelly_fraction": 0.25,
    "max_bankroll_pct": 0.05,
    "max_trades_per_week": 3,
    "use_hrrr": True,
    "use_ensemble": True,
    "tier": 3,
}


def get_tier(city: str) -> int:
    """Gibt Tier einer Stadt zurück."""
    if city in TIER1_STATIONS:
        return 1
    return 2


def get_tier_config(city: str, tier: int = None) -> dict:
    """Gibt Config für Stadt/Tier zurück."""
    if tier is None:
        tier = get_tier(city)
    if tier == 1 and city in TIER1_STATIONS:
        return TIER1_STATIONS[city]
    elif tier == 3:
        return TIER3_CONFIG
    else:
        return TIER2_CONFIG


def should_trade(
    city: str,
    edge_pct: float,
    price: float,
    outcome: str,
) -> tuple[bool, str]:
    """
    Prüft ob ein Trade die Tier-Kriterien erfüllt.
    Returns: (should_trade, reason)
    """
    tier = get_tier(city)
    config = get_tier_config(city, tier)

    t3 = TIER3_CONFIG
    if edge_pct >= t3["min_edge"] and price <= t3["max_price"]:
        return True, f"TIER3_BARBELL edge={edge_pct:.0%}"

    if tier == 1:
        cfg = config
        if edge_pct < cfg["min_edge"]:
            return False, f"TIER1_EDGE_LOW {edge_pct:.0%}<{cfg['min_edge']:.0%}"
        if price > cfg["max_price"]:
            return False, f"TIER1_PRICE_HIGH {price:.0%}>{cfg['max_price']:.0%}"
        return True, f"TIER1 edge={edge_pct:.0%}"

    cfg = TIER2_CONFIG
    if outcome.lower() == "yes" and price > cfg["max_price_yes"]:
        return False, f"TIER2_YES_TOO_EXPENSIVE {price:.0%}>{cfg['max_price_yes']:.0%}"
    if outcome.lower() == "no" and price < cfg["min_price_no"]:
        return False, f"TIER2_NO_TOO_CHEAP {price:.0%}<{cfg['min_price_no']:.0%}"
    if edge_pct < cfg["min_edge"]:
        return False, f"TIER2_EDGE_LOW {edge_pct:.0%}"
    return True, f"TIER2 edge={edge_pct:.0%}"
