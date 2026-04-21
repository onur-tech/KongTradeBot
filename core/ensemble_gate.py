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
