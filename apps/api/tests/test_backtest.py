import pytest

from app.backtest.engine import run_backtest


def test_deterministic_savings_relations():
    r = run_backtest(days=100, drawdown_cm_day=0.8, rain_series=[0.0] * 100)
    assert r.irrigations_awd < r.irrigations_cf
    assert r.water_awd_m3 < r.water_cf_m3
    assert r.flooded_days_awd < r.flooded_days_cf
    assert 0.78 <= r.sf_w_eff < 1.0
    assert r.co2e_saved_t > 0
    assert 0 < r.water_saved_pct < 100


def test_e3_defaults_match_committed_summary():
    r = run_backtest()
    assert (r.irrigations_awd, r.irrigations_cf) == (23, 100)
    assert (r.water_awd_m3, r.water_cf_m3) == (5000.0, 8000.0)
    assert (r.flooded_days_awd, r.flooded_days_cf) == (51, 100)
    assert r.sf_w_eff == 0.8922
    assert (r.ch4_cf_kg, r.ch4_awd_kg) == (130.0, 115.99)
    assert r.co2e_saved_t == 0.3784
    assert r.water_saved_pct == 37.5


def test_flooded_rain_zero_awd_irrigation():
    r = run_backtest(days=100, rain_series=[40.0] * 100)
    assert r.irrigations_awd == 0


def test_run_backtest_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        run_backtest(days=0)
    with pytest.raises(ValueError):
        run_backtest(days=-10)
    with pytest.raises(ValueError):
        run_backtest(days=100, drawdown_cm_day=0.0)
    with pytest.raises(ValueError):
        run_backtest(days=100, area_ha=-1.0)
    with pytest.raises(ValueError):
        run_backtest(days=100, rain_series=[0.0] * 99)
