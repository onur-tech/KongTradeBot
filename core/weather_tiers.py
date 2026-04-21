from dataclasses import dataclass, field
from typing import Literal, Optional

@dataclass(frozen=True)
class TierStation:
    icao: str
    city: str
    country_code: str             # ISO-2 für Wunderground-URL
    wunderground_slug: str        # URL-Pfad bei wunderground
    temp_unit: Literal["C", "F"]
    bracket_width: float          # 1.0 °C (non-US) oder 2.0 °F (US)
    primary_models: tuple[str, ...]   # welche NWPs sinnvoll sind
    has_hrrr: bool
    timezone: str

TIER_1_STATIONS: dict[str, TierStation] = {
    "NYC": TierStation(
        icao="KLGA", city="New York", country_code="us",
        wunderground_slug="us/ny/new-york-city/KLGA",
        temp_unit="F", bracket_width=2.0,
        primary_models=("GFS", "HRRR", "ECMWF", "NAM"),
        has_hrrr=True, timezone="America/New_York",
    ),
    "LON": TierStation(
        icao="EGLC", city="London", country_code="gb",
        wunderground_slug="gb/london/EGLC",
        temp_unit="C", bracket_width=1.0,
        primary_models=("ECMWF", "ICON-EU", "GFS"),
        has_hrrr=False, timezone="Europe/London",
    ),
    "SEO": TierStation(
        icao="RKSI", city="Seoul", country_code="kr",
        wunderground_slug="kr/incheon/RKSI",
        temp_unit="C", bracket_width=1.0,
        primary_models=("ECMWF", "GFS", "ICON"),
        has_hrrr=False, timezone="Asia/Seoul",
    ),
    "CHI": TierStation(
        icao="KORD", city="Chicago", country_code="us",
        wunderground_slug="us/il/chicago/KORD",
        temp_unit="F", bracket_width=2.0,
        primary_models=("GFS", "HRRR", "ECMWF", "NAM"),
        has_hrrr=True, timezone="America/Chicago",
    ),
    "TYO": TierStation(
        icao="RJTT", city="Tokyo", country_code="jp",
        wunderground_slug="jp/tokyo/RJTT",
        temp_unit="C", bracket_width=1.0,
        primary_models=("ECMWF", "GFS", "ICON"),
        has_hrrr=False, timezone="Asia/Tokyo",
    ),
    "PAR": TierStation(
        icao="LFPG", city="Paris", country_code="fr",
        wunderground_slug="fr/paris/LFPG",
        temp_unit="C", bracket_width=1.0,
        primary_models=("ECMWF", "ICON-EU", "GFS"),
        has_hrrr=False, timezone="Europe/Paris",
    ),
}

# Compatibility: accept old keys that referenced wrong stations
_STATION_ALIASES = {
    "EGLL": "LON",  # Heathrow -> LON (EGLC)
    "LFPB": "PAR",  # Le Bourget -> PAR (LFPG)
    "LFPO": "PAR",
    "RJAA": "TYO",  # Narita -> TYO (RJTT)
    "RKSS": "SEO",
    "KJFK": "NYC",
    "KNYC": "NYC",  # Central Park (temp markets still use KLGA)
    "KMDW": "CHI",
}

def resolve_station(key: str) -> TierStation:
    if key in TIER_1_STATIONS:
        return TIER_1_STATIONS[key]
    if key in _STATION_ALIASES:
        return TIER_1_STATIONS[_STATION_ALIASES[key]]
    if key.upper() in TIER_1_STATIONS:
        return TIER_1_STATIONS[key.upper()]
    raise KeyError(f"Unknown Tier-1 station: {key}")


# Polymarket city-name variants → Tier-1 key
_CITY_NAME_ALIASES: dict[str, str] = {
    "new york city": "NYC",
    "new york":      "NYC",
    "new york, ny":  "NYC",
    "nyc":           "NYC",
    "london":        "LON",
    "london, uk":    "LON",
    "seoul":         "SEO",
    "seoul, korea":  "SEO",
    "chicago":       "CHI",
    "chicago, il":   "CHI",
    "tokyo":         "TYO",
    "tokyo, japan":  "TYO",
    "paris":         "PAR",
    "paris, france": "PAR",
}


def get_tier(city: str) -> int:
    """Gibt 1 zurück wenn Tier-1-Stadt, sonst 2."""
    key = _CITY_NAME_ALIASES.get(city.lower().strip())
    if key and key in TIER_1_STATIONS:
        return 1
    # Direkt-Match auf Tier-1-Key (z.B. "NYC")
    if city.upper().strip() in TIER_1_STATIONS:
        return 1
    return 2


def should_trade(
    city: str,
    edge_pct: float,
    price: float,
    outcome: str = "YES",
) -> tuple[bool, str]:
    """
    Tier-Gate für Weather-Trades.

    Tier 3 — Barbell:  edge >= 30%, price <= 8¢  → immer handeln
    Tier 1 — Deep:     edge >= 15%, price 5-85¢
    Tier 2 — Broad:    YES < 12¢ ODER NO > 50¢, edge >= 7%
    """
    # Tier 3 Barbell überstimmt alles
    if edge_pct >= 0.30 and price <= 0.08:
        return True, "TIER3_BARBELL"

    tier = get_tier(city)

    if tier == 1:
        if edge_pct < 0.15:
            return False, f"TIER1_EDGE_LOW {edge_pct:.1%}<15%"
        if price > 0.85:
            return False, "TIER1_PRICE_HIGH >85¢"
        if price <= 0.05:
            return False, "TIER1_PRICE_TOO_LOW ≤5¢"
        return True, "TIER1_OK"

    # Tier 2
    if outcome.upper() == "YES" and price > 0.12:
        return False, f"TIER2_YES_TOO_EXPENSIVE {price:.0%}>12¢"
    if outcome.upper() == "NO" and price < 0.50:
        return False, f"TIER2_NO_TOO_CHEAP {price:.0%}<50¢"
    if edge_pct < 0.07:
        return False, f"TIER2_EDGE_LOW {edge_pct:.1%}<7%"
    return True, "TIER2_OK"
