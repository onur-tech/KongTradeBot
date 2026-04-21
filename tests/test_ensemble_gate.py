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
