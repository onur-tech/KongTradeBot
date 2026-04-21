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
