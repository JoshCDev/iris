import pytest

from app.irrigation.water import (cm_to_mm, deficit_mm, et0_hargreaves,
                                  level_cm_to_m3)


def test_conversions():
    assert cm_to_mm(5.0) == 50.0
    assert deficit_mm(-15.0) == 200.0
    assert deficit_mm(6.0) == 0.0
    assert level_cm_to_m3(5.0, 1.0) == 500.0
    assert abs(et0_hargreaves(22, 32, 27, -7.33, 90) - 4.9) < 1.2


def test_et0_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        et0_hargreaves(22, 32, 27, 95, 90)
    with pytest.raises(ValueError):
        et0_hargreaves(22, 32, 27, -7.33, 0)
    assert et0_hargreaves(0, 0, -10, -7.33, 90) == 0.0
