#!/bin/bash
# KongTrade Deploy Script — Windows CC Build
# Ausführen auf Server: bash deploy_to_server.sh

set -e

echo "=== KongTrade Deploy — Tier-Architektur ==="

# Backup
cp core/weather_tiers.py core/weather_tiers.py.bak 2>/dev/null || true
cp core/kelly.py core/kelly.py.bak 2>/dev/null || true

# ─────────────────────────────────────────────
# FILE 1: core/weather_tiers.py
# ─────────────────────────────────────────────
cat > core/weather_tiers.py << 'HEREDOC'
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
HEREDOC

# ─────────────────────────────────────────────
# FILE 2: core/kelly.py
# ─────────────────────────────────────────────
cat > core/kelly.py << 'HEREDOC'
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
HEREDOC

# ─────────────────────────────────────────────
# FILE 3: core/seasonal_bias.py
# ─────────────────────────────────────────────
cat > core/seasonal_bias.py << 'HEREDOC'
"""Saisonale Bias-Korrektur pro Station und Quartal.

Bias-Konvention: bias = observed - forecast
-> korrigierter Forecast = raw_forecast + bias
Seoul Q1/Q2 wurden aus ~180 Tagen METAR-vs-GFS-Daten gelernt
(Stand: Dezember 2025). Alle anderen Stationen: TBD aus Shadow-v2-Daten.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

Quarter = Literal["Q1", "Q2", "Q3", "Q4"]
Model = Literal["GFS", "ECMWF", "ICON", "HRRR", "NAM"]


@dataclass(frozen=True)
class QuarterlyBias:
    mean_bias: float          # in der jeweiligen Unit (°C oder °F)
    sample_size: int          # Anzahl Tage in der Kalibrierung
    rmse: float | None = None # Modell-RMSE nach Bias-Korrektur
    last_updated: str = ""    # ISO-Date des letzten Retraining

    @property
    def is_calibrated(self) -> bool:
        return self.sample_size >= 30


# Struktur: {station_key: {model: {quarter: QuarterlyBias}}}
SEASONAL_BIAS: dict[str, dict[str, dict[str, QuarterlyBias]]] = {
    "SEO": {
        "GFS": {
            "Q1": QuarterlyBias(-1.98, 90, rmse=1.4, last_updated="2025-12-15"),
            "Q2": QuarterlyBias(-1.74, 90, rmse=1.5, last_updated="2025-12-15"),
            "Q3": QuarterlyBias(0.0, 0),    # TBD
            "Q4": QuarterlyBias(0.0, 0),    # TBD
        },
    },
    "NYC":  {"GFS":     {q: QuarterlyBias(0.0, 0) for q in ("Q1", "Q2", "Q3", "Q4")},
             "HRRR":    {q: QuarterlyBias(0.0, 0) for q in ("Q1", "Q2", "Q3", "Q4")}},
    "LON":  {"ECMWF":   {q: QuarterlyBias(0.0, 0) for q in ("Q1", "Q2", "Q3", "Q4")},
             "ICON-EU": {q: QuarterlyBias(0.0, 0) for q in ("Q1", "Q2", "Q3", "Q4")},
             "GFS":     {q: QuarterlyBias(0.0, 0) for q in ("Q1", "Q2", "Q3", "Q4")}},
    "CHI":  {"GFS":     {q: QuarterlyBias(0.0, 0) for q in ("Q1", "Q2", "Q3", "Q4")},
             "HRRR":    {q: QuarterlyBias(0.0, 0) for q in ("Q1", "Q2", "Q3", "Q4")}},
    "TYO":  {"ECMWF":   {q: QuarterlyBias(0.0, 0) for q in ("Q1", "Q2", "Q3", "Q4")},
             "GFS":     {q: QuarterlyBias(0.0, 0) for q in ("Q1", "Q2", "Q3", "Q4")},
             "ICON":    {q: QuarterlyBias(0.0, 0) for q in ("Q1", "Q2", "Q3", "Q4")}},
    "PAR":  {"ECMWF":   {q: QuarterlyBias(0.0, 0) for q in ("Q1", "Q2", "Q3", "Q4")},
             "ICON-EU": {q: QuarterlyBias(0.0, 0) for q in ("Q1", "Q2", "Q3", "Q4")},
             "GFS":     {q: QuarterlyBias(0.0, 0) for q in ("Q1", "Q2", "Q3", "Q4")}},
}


def _quarter_of(month: int) -> str:
    return f"Q{(month - 1) // 3 + 1}"


def apply_bias_correction(
    raw_forecast: float,
    station_key: str,
    model: str,
    month: int,
) -> tuple[float, QuarterlyBias | None]:
    """Gibt (korrigierter Forecast, angewendeter Bias oder None) zurueck."""
    q = _quarter_of(month)
    try:
        bias = SEASONAL_BIAS[station_key][model][q]
    except KeyError:
        return raw_forecast, None
    if not bias.is_calibrated:
        return raw_forecast, None
    return raw_forecast + bias.mean_bias, bias
HEREDOC

# ─────────────────────────────────────────────
# FILE 4: core/ensemble_gate.py
# ─────────────────────────────────────────────
cat > core/ensemble_gate.py << 'HEREDOC'
"""Multi-Model Ensemble Confidence Gate.

Ein Bet wird NUR platziert, wenn mindestens `min_models` unabhängige NWPs
dieselbe Richtung anzeigen UND der kombinierte Confidence-Score >= Gate.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass
class EnsembleDecision:
    p_ensemble: float      # gewichteter Mean-P(event)
    confidence: float      # [0,1], 1 = alle Modelle sagen dasselbe
    n_models: int
    direction_agreement: float   # Anteil der Modelle auf dominanter Seite
    conviction: float      # |mean_p - 0.5| * 2
    spread_penalty: float  # 1 - min(1, std(p_i) / 0.25)
    gate_passed: bool
    reason: str


def ensemble_confidence(
    per_model_p: dict[str, float],
    *,
    min_models: int = 2,
    gate_threshold: float = 0.55,
    threshold_midpoint: float = 0.5,
) -> EnsembleDecision:
    """Berechnet Confidence und entscheidet, ob Gate passiert wurde.

    per_model_p: {"GFS": 0.72, "ECMWF": 0.68, "ICON": 0.71}
    """
    if not per_model_p:
        return EnsembleDecision(0.0, 0.0, 0, 0.0, 0.0, 0.0, False, "no_models")
    n = len(per_model_p)
    if n < min_models:
        return EnsembleDecision(
            float(np.mean(list(per_model_p.values()))), 0.0, n, 0.0, 0.0, 0.0,
            False, f"only_{n}_models_need_{min_models}"
        )

    p = np.array(list(per_model_p.values()), dtype=float)
    mean_p = float(p.mean())
    above = float((p > threshold_midpoint).mean())
    below = float((p < threshold_midpoint).mean())
    direction_agreement = max(above, below)
    conviction = min(1.0, abs(mean_p - 0.5) * 2)
    spread_penalty = 1.0 - min(1.0, float(p.std()) / 0.25)
    confidence = direction_agreement * conviction * spread_penalty

    gate_passed = bool(confidence >= gate_threshold and direction_agreement >= 0.66)
    reason = "OK" if gate_passed else (
        f"conf={confidence:.2f}<{gate_threshold} or agreement={direction_agreement:.2f}<0.66"
    )
    return EnsembleDecision(mean_p, confidence, n, direction_agreement,
                            conviction, spread_penalty, gate_passed, reason)
HEREDOC

# ─────────────────────────────────────────────
# FILE 5: integrations/kalshi_scraper.py
# ─────────────────────────────────────────────
mkdir -p integrations
touch integrations/__init__.py

cat > integrations/kalshi_scraper.py << 'HEREDOC'
"""Read-Only Kalshi Weather Markets Scraper.

Benoetigt keinen Account, keinen API-Key. Liest oeffentliche Marktdaten fuer
Signal-Generierung und Cross-Market-Comparison mit Polymarket.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
import time
import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"

# Die bekannten Daily-Temperature Series-Tickers (High & Low)
WEATHER_SERIES_HIGH = [
    "KXHIGHNY", "KXHIGHMIA", "KXHIGHLAX", "KXHIGHAUS", "KXHIGHCHI",
    "KXHIGHTPHX", "KXHIGHTSFO", "KXHIGHTGATL", "KXHIGHPHIL", "KXHIGHTDC",
    "KXHIGHDEN", "KXHIGHTSEA", "KXHIGHTHOU", "KXHIGHTMIN", "KXHIGHTBOS",
    "KXHIGHTLV", "KXHIGHTOKC",
]
WEATHER_SERIES_LOW = [
    "KXLOWTCHI", "KXLOWTNYC", "KXLOWTAUS", "KXLOWTMIA",
    "KXLOWTDEN", "KXLOWTPHIL", "KXLOWTLAX",
]


@dataclass
class KalshiMarket:
    ticker: str
    title: str
    yes_bid: float
    yes_ask: float
    last_price: float | None
    volume: int
    status: str


def _get(path: str, params: dict | None = None, retries: int = 3) -> dict:
    url = f"{BASE}{path}"
    for i in range(retries):
        r = requests.get(url, params=params, timeout=15,
                         headers={"User-Agent": "KongTrade-ReadOnly/1.0"})
        if r.status_code == 429:
            time.sleep(2 ** i)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"Kalshi API failed after {retries} retries: {url}")


def fetch_series_markets(series_ticker: str, status: str = "open") -> list[KalshiMarket]:
    data = _get("/markets", params={"series_ticker": series_ticker,
                                    "status": status, "limit": 100})
    out = []
    for m in data.get("markets", []):
        out.append(KalshiMarket(
            ticker=m["ticker"],
            title=m.get("title", ""),
            yes_bid=float(m.get("yes_bid_dollars") or m.get("yes_bid", 0) / 100),
            yes_ask=float(m.get("yes_ask_dollars") or m.get("yes_ask", 0) / 100),
            last_price=(float(m["last_price_dollars"])
                        if m.get("last_price_dollars") else None),
            volume=int(m.get("volume", 0)),
            status=m.get("status", ""),
        ))
    return out


def fetch_orderbook(ticker: str) -> dict:
    return _get(f"/markets/{ticker}/orderbook").get("orderbook_fp", {})


def snapshot_all_weather(series: Iterable[str] | None = None) -> dict[str, list[KalshiMarket]]:
    series = list(series or WEATHER_SERIES_HIGH)
    out = {}
    for s in series:
        try:
            out[s] = fetch_series_markets(s)
        except Exception as e:
            print(f"[kalshi] {s} failed: {e}")
            out[s] = []
        time.sleep(0.05)   # <20 req/s hold
    return out


if __name__ == "__main__":
    nyc = fetch_series_markets("KXHIGHNY")
    print(f"KXHIGHNY: {len(nyc)} open markets")
    for m in nyc[:5]:
        print(f"  {m.ticker:35} bid={m.yes_bid:.2f} ask={m.yes_ask:.2f} vol={m.volume}")
HEREDOC

# ─────────────────────────────────────────────
# TESTS
# ─────────────────────────────────────────────
mkdir -p tests
touch tests/__init__.py

cat > tests/test_kelly.py << 'HEREDOC'
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
HEREDOC

cat > tests/test_seasonal_bias.py << 'HEREDOC'
from core.seasonal_bias import apply_bias_correction, SEASONAL_BIAS

def test_seoul_q1_gfs_applies_known_bias():
    corrected, bias = apply_bias_correction(5.0, "SEO", "GFS", month=2)
    assert bias is not None
    assert corrected == 5.0 + (-1.98)

def test_nyc_uncalibrated_returns_raw():
    corrected, bias = apply_bias_correction(72.0, "NYC", "GFS", month=2)
    assert bias is None
    assert corrected == 72.0

def test_unknown_station_returns_raw():
    corrected, bias = apply_bias_correction(20.0, "ZZZ", "GFS", month=1)
    assert bias is None
    assert corrected == 20.0
HEREDOC

cat > tests/test_ensemble_gate.py << 'HEREDOC'
from core.ensemble_gate import ensemble_confidence

def test_single_model_fails_gate():
    d = ensemble_confidence({"GFS": 0.85})
    assert not d.gate_passed
    assert "only_1_models" in d.reason

def test_strong_agreement_passes():
    d = ensemble_confidence({"GFS": 0.80, "ECMWF": 0.78, "ICON": 0.82})
    assert d.gate_passed
    assert d.direction_agreement == 1.0

def test_split_ensemble_fails():
    d = ensemble_confidence({"GFS": 0.70, "ECMWF": 0.30, "ICON": 0.55})
    assert not d.gate_passed

def test_weak_conviction_fails():
    d = ensemble_confidence({"GFS": 0.54, "ECMWF": 0.52, "ICON": 0.53})
    assert not d.gate_passed
HEREDOC

# ─────────────────────────────────────────────
# SYNTAX CHECKS
# ─────────────────────────────────────────────
echo ""
echo "=== Syntax Checks ==="
python3 -m py_compile core/weather_tiers.py   && echo "OK  core/weather_tiers.py"
python3 -m py_compile core/kelly.py           && echo "OK  core/kelly.py"
python3 -m py_compile core/seasonal_bias.py   && echo "OK  core/seasonal_bias.py"
python3 -m py_compile core/ensemble_gate.py   && echo "OK  core/ensemble_gate.py"
python3 -m py_compile integrations/kalshi_scraper.py && echo "OK  integrations/kalshi_scraper.py"

# ─────────────────────────────────────────────
# TESTS
# ─────────────────────────────────────────────
echo ""
echo "=== Tests ==="
if command -v pytest &>/dev/null || python3 -m pytest --version &>/dev/null 2>&1; then
    python3 -m pytest tests/test_kelly.py tests/test_seasonal_bias.py tests/test_ensemble_gate.py -v
else
    python3 -m unittest discover tests/
fi

echo ""
echo "=== FERTIG ==="
