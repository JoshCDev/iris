import pytest

from app.irrigation.ipcc import (GWP100_CH4_AR6, SF_W_MULTIPLE_AERATION,
                                 build_receipt, co2e_t, effective_sf_w, ef_c,
                                 seasonal_ch4_kg)


def test_spec_worked_example():
    base = seasonal_ch4_kg(sf_w=1.0)
    awd = seasonal_ch4_kg(sf_w=SF_W_MULTIPLE_AERATION)
    assert abs(base - 130.0) < 1e-9
    assert abs(awd - 101.4) < 1e-9
    saved = base - awd
    assert abs(co2e_t(saved) - 28.6 * GWP100_CH4_AR6 / 1000) < 1e-9


def test_ef_c_composition():
    assert abs(ef_c(1.0) - 1.3) < 1e-9
    assert abs(ef_c(0.78, 2.0) - 1.3 * 0.78 * 2.0) < 1e-9


def test_effective_sf_w_bounds_and_monotonic():
    assert effective_sf_w(100, 100) == 1.0
    assert abs(effective_sf_w(0, 100) - 0.78) < 1e-9
    mid = effective_sf_w(60, 100)
    assert 0.78 < mid < 1.0
    assert effective_sf_w(70, 100) > mid


def test_build_receipt_fields():
    r = build_receipt("Sawah Kampus", season_days=100, flooded_days=70,
                      water_baseline_m3=12000.0, water_actual_m3=8000.0)
    assert r.water_saved_m3 == 4000.0
    assert abs(r.water_saved_pct - 33.33) < 0.01
    assert r.ch4_saved_kg > 0
    assert r.co2e_saved_t > 0
    assert r.label == "simulated"
    with pytest.raises(ValueError):
        build_receipt("X", season_days=0, flooded_days=0,
                      water_baseline_m3=1, water_actual_m3=1)


def test_build_receipt_rejects_equal_water_volumes():
    with pytest.raises(ValueError):
        build_receipt("Sawah Kampus", season_days=100, flooded_days=70,
                      water_baseline_m3=8000.0, water_actual_m3=8000.0)


def test_build_receipt_rejects_flooded_days_out_of_range():
    with pytest.raises(ValueError):
        build_receipt("Sawah Kampus", season_days=100, flooded_days=-1,
                      water_baseline_m3=12000.0, water_actual_m3=8000.0)
    with pytest.raises(ValueError):
        build_receipt("Sawah Kampus", season_days=100, flooded_days=101,
                      water_baseline_m3=12000.0, water_actual_m3=8000.0)


def test_build_receipt_label_whitelist():
    for label in ("simulated", "measured", "projected"):
        r = build_receipt("Sawah Kampus", season_days=100, flooded_days=70,
                          water_baseline_m3=12000.0, water_actual_m3=8000.0,
                          label=label)
        assert r.label == label
    with pytest.raises(ValueError):
        build_receipt("Sawah Kampus", season_days=100, flooded_days=70,
                      water_baseline_m3=12000.0, water_actual_m3=8000.0,
                      label="estimated")
