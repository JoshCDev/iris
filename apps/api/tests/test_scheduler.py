from app.irrigation.protocol import Stage
from app.irrigation.reason_text import english_reason
from app.irrigation.scheduler import decide


def test_wait_when_above_trigger():
    d = decide(0.0, Stage.VEG_AWD, 0.0)
    assert d.action == "WAIT"


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
