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
