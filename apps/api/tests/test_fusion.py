import pytest

from app.fusion.risk import assess, awd_state_from, wet_weather_from_rain
from app.irrigation.protocol import Stage

# Table-driven: one row per pinned matrix rule + fallbacks.
MATRIX_ROWS = [
    # (disease, awd_state, wet_weather, expected risk, note present)
    ("brown_spot", "deep_dry", False, "high", True),
    ("brown_spot", "beyond_trigger", False, "high", True),
    ("brown_spot", "deep_dry", True, "high", True),
    ("brown_spot", "shallow_dry", False, "medium", False),
    ("brown_spot", "flooded", False, "low", False),
    ("blast", "flooded", True, "high", False),
    ("blast", "flowering_lock", True, "high", False),
    ("blast", "flooded", False, "medium", False),
    ("blast", "shallow_dry", False, "low", False),
    ("blast", "deep_dry", False, "low", False),
    ("blast", "beyond_trigger", True, "low", True),
    ("bacterial_leaf_blight", "flooded", True, "high", True),
    ("bacterial_leaf_blight", "flowering_lock", True, "high", True),
    ("bacterial_leaf_blight", "flooded", False, "low", False),
    ("bacterial_leaf_blight", "deep_dry", True, "low", True),
    ("tungro", "flooded", False, "medium", False),
    ("tungro", "flowering_lock", True, "medium", False),
    ("tungro", "deep_dry", False, "medium", False),
    ("none", "flooded", False, "low", False),
    ("none", "deep_dry", True, "low", False),
]


@pytest.mark.parametrize("disease,state,wet,expected,has_note", MATRIX_ROWS)
def test_matrix_rows(disease, state, wet, expected, has_note):
    out = assess(disease, state, wet)
    assert out["risk_level"] == expected
    if has_note:
        assert "irrigation_note" in out
        assert out["irrigation_note"]
    else:
        assert "irrigation_note" not in out


def test_brown_spot_driver_texts():
    out = assess("brown_spot", "deep_dry", False)
    assert any("bercak cokelat" in d for d in out["drivers_id"])
    assert all(isinstance(d, str) for d in out["drivers_en"])


def test_blast_wet_driver_text():
    out = assess("blast", "flooded", True)
    assert any("Kanopi basah" in d for d in out["drivers_id"])


def test_blb_wet_driver_and_note():
    out = assess("bacterial_leaf_blight", "flowering_lock", True)
    assert any("BLB" in d or "Air jalan" in d for d in out["drivers_id"])
    assert out.get("irrigation_note")


def test_tungro_driver_mentions_vector():
    out = assess("tungro", "shallow_dry", False)
    assert any("wereng" in d.lower() for d in out["drivers_id"])


def test_none_generic_monitoring():
    out = assess("none", "flooded", False)
    assert out["risk_level"] == "low"
    assert any("pemantauan" in d for d in out["drivers_id"])


def test_unknown_disease_falls_back_low_generic():
    out = assess("leaf_rust", "flooded", False)
    assert out["risk_level"] == "low"
    assert out["drivers_id"] and out["drivers_en"]
    assert out["irrigation_note"]


def test_unknown_state_falls_back_low_generic():
    out = assess("blast", "mysterious_state", True)
    assert out["risk_level"] == "low"
    assert out["irrigation_note"]


@pytest.mark.parametrize(
    "level,stage,expected",
    [
        (5.0, Stage.VEG_AWD, "flooded"),
        (0.0, Stage.VEG_AWD, "flooded"),
        (-0.1, Stage.VEG_AWD, "shallow_dry"),
        (-7.9, Stage.VEG_AWD, "shallow_dry"),
        (-8.0, Stage.VEG_AWD, "deep_dry"),
        (-14.9, Stage.VEG_AWD, "deep_dry"),
        (-15.0, Stage.VEG_AWD, "deep_dry"),
        (-15.1, Stage.VEG_AWD, "beyond_trigger"),
        (-24.0, Stage.VEG_AWD, "beyond_trigger"),
        (-2.0, Stage.FLOWERING_LOCK, "flowering_lock"),
        (-20.0, Stage.FLOWERING_LOCK, "flowering_lock"),
        (4.0, "veg_awd", "flooded"),
    ],
)
def test_awd_state_from_bands(level, stage, expected):
    assert awd_state_from(level, stage) == expected


def test_wet_weather_threshold_is_15mm():
    assert wet_weather_from_rain(15.0) is True
    assert wet_weather_from_rain(14.9) is False
    assert wet_weather_from_rain(22.0) is True
