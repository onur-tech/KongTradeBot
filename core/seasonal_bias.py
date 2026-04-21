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
