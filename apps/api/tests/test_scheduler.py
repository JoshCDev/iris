from app.irrigation.protocol import Stage
from app.irrigation.reason_text import english_reason
from app.irrigation.scheduler import decide


def test_wait_when_above_trigger():
    d = decide(-5.0, Stage.VEG_AWD, 0.0)
    assert d.action == "WAIT"
    assert "Do not drain" not in d.reason_id


def test_irrigate_below_trigger_no_rain():
    d = decide(-16.0, Stage.VEG_AWD, 0.0)
    assert d.action == "IRRIGATE"
    assert d.refill_to_cm == 5.0
    assert "irrigate" in d.reason_id.lower()


def test_irrigate_exactly_at_trigger():
    d = decide(-15.0, Stage.VEG_AWD, 0.0)
    assert d.action == "IRRIGATE"


def test_hold_for_rain_rain_threshold_boundary():
    assert decide(-15.5, Stage.VEG_AWD, 15.0).action == "HOLD_FOR_RAIN"
    assert decide(-15.5, Stage.VEG_AWD, 14.9).action == "IRRIGATE"


def test_hard_floor_forces_irrigate_despite_rain():
    assert decide(-25.0, Stage.VEG_AWD, 200.0).action == "IRRIGATE"
    assert decide(-24.9, Stage.VEG_AWD, 200.0).action == "HOLD_FOR_RAIN"


def test_harvest_drains_even_with_heavy_rain():
    d = decide(5.0, Stage.HARVEST, 999.0)
    assert d.action == "DRAIN"


def test_flowering_lock_never_holds_for_rain():
    d = decide(2.6, Stage.FLOWERING_LOCK, 200.0)
    assert d.action == "IRRIGATE"
    assert "flowering" in d.reason_id.lower()


def test_hold_for_rain():
    d = decide(-16.0, Stage.VEG_AWD, 20.0)
    assert d.action == "HOLD_FOR_RAIN"
    assert "rain" in d.reason_id.lower()


def test_flowering_lock_forces_flood():
    d = decide(2.0, Stage.FLOWERING_LOCK, 0.0)
    assert d.action == "IRRIGATE"
    assert "flowering" in d.reason_id.lower()


def test_wait_when_already_wet_despite_heavy_rain():
    """Prolonged rain must not drain a wet vegetative field; AWD dries by ET."""
    d = decide(5.0, Stage.VEG_AWD, 200.0)
    assert d.action == "WAIT"
    assert "Do not drain" in d.reason_id


def test_wait_when_ponded_at_zero_despite_rain():
    d = decide(0.0, Stage.VEG_AWD, 80.0)
    assert d.action == "WAIT"
    assert "Do not drain" in d.reason_id


def test_excess_pond_recommends_lower_not_harvest_drain():
    """Complete-canopy / deep flood is not AWD; lower toward +5 cm if a drain exists."""
    d = decide(15.0, Stage.VEG_AWD, 0.0)
    assert d.action == "LOWER_POND"
    assert d.action != "DRAIN"
    assert "lower" in d.reason_id.lower()
    assert "+5" in d.reason_id
    assert "AWD trigger" in d.reason_id or "do not dry" in d.reason_id.lower()


def test_shallow_awd_pond_is_not_excess():
    d = decide(5.0, Stage.VEG_AWD, 0.0)
    assert d.action == "WAIT"
    assert "Do not drain" in d.reason_id
    assert d.action != "LOWER_POND"


def test_harvest_drain():
    d = decide(5.0, Stage.HARVEST, 0.0)
    assert d.action == "DRAIN"


def test_establishment_keeps_flooded():
    d = decide(3.0, Stage.ESTABLISHMENT, 0.0)
    assert d.action == "IRRIGATE"


def test_english_reason_maps_legacy_indonesian():
    src = "Kondisi aman (-8.9 cm; pemicu -15.0 cm). Pantau 15 menit berikutnya."
    out = english_reason(src)
    assert out is not None
    assert "Safe" in out
    assert "trigger" in out
    assert english_reason("Safe (+1.0 cm; trigger -15.0 cm). Check again in 15 minutes.") == (
        "Safe (+1.0 cm; trigger -15.0 cm). Check again in 15 minutes."
    )


def test_recheck_when_water_stale():
    d = decide(-16.0, Stage.VEG_AWD, 20.0, water_fresh=False)
    assert d.action == "RECHECK_REQUIRED"
    assert "uk" in d.reason_id or "periksa" in d.reason_id


def test_recheck_when_weather_unavailable():
    d = decide(-5.0, Stage.VEG_AWD, 0.0, weather_availability="unavailable")
    assert d.action == "RECHECK_REQUIRED"


def test_stale_cache_weather_still_decides_with_review_note():
    d = decide(-16.0, Stage.VEG_AWD, 20.0, weather_availability="stale-cache")
    assert d.action == "HOLD_FOR_RAIN"


def test_fresh_defaults_unchanged():
    assert decide(-5.0, Stage.VEG_AWD, 0.0).action == "WAIT"
