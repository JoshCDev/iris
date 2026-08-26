import pytest

from app.irrigation.protocol import Stage, stage_on, trigger_level_cm


def test_stage_boundaries():
    assert stage_on(0) is Stage.ESTABLISHMENT
    assert stage_on(13) is Stage.ESTABLISHMENT
    assert stage_on(14) is Stage.VEG_AWD
    assert stage_on(54) is Stage.VEG_AWD
    assert stage_on(55) is Stage.FLOWERING_LOCK
    assert stage_on(79) is Stage.FLOWERING_LOCK
    assert stage_on(80) is Stage.GRAIN_FILL_AWD
    assert stage_on(99) is Stage.GRAIN_FILL_AWD
    assert stage_on(100) is Stage.HARVEST


def test_negative_day_raises():
    with pytest.raises(ValueError):
        stage_on(-1)


def test_triggers_field_vs_scaled():
    assert trigger_level_cm(Stage.VEG_AWD) == -15.0
    assert trigger_level_cm(Stage.VEG_AWD, scaled=True) == -5.0
    assert trigger_level_cm(Stage.ESTABLISHMENT) == 5.0
    assert trigger_level_cm(Stage.FLOWERING_LOCK) == 3.0
    assert trigger_level_cm(Stage.HARVEST) is None
