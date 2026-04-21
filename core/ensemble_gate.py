"""Multi-Model Ensemble Gate — min 2 Modelle."""
from dataclasses import dataclass
import math


@dataclass
class EnsembleDecision:
    p_ensemble: float
    confidence: float
    n_models: int
    gate_passed: bool
    reason: str


def _mean(vals):
    return sum(vals) / len(vals) if vals else 0.0


def _std(vals):
    if len(vals) < 2:
        return 0.0
    m = _mean(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals))


def ensemble_confidence(
    per_model_p: dict,
    min_models: int = 2,
    gate_threshold: float = 0.55,
) -> EnsembleDecision:
    if not per_model_p:
        return EnsembleDecision(0, 0, 0, False, "no_models")
    n = len(per_model_p)
    vals = list(per_model_p.values())
    mean_p = _mean(vals)
    if n < min_models:
        return EnsembleDecision(mean_p, 0, n, False, f"need_{min_models}_got_{n}")
    above_half = sum(1 for v in vals if v > 0.5)
    agreement = max(above_half, n - above_half) / n
    conviction = min(1.0, abs(mean_p - 0.5) * 2)
    spread = 1.0 - min(1.0, _std(vals) / 0.25)
    conf = agreement * conviction * spread
    passed = bool(conf >= gate_threshold and agreement >= 0.66)
    reason = "OK" if passed else f"conf={conf:.2f} agree={agreement:.2f}"
    return EnsembleDecision(mean_p, conf, n, passed, reason)
