from enum import Enum


class Stage(str, Enum):
    ESTABLISHMENT = "establishment"
    VEG_AWD = "veg_awd"
    FLOWERING_LOCK = "flowering_lock"
    GRAIN_FILL_AWD = "grain_fill_awd"
    HARVEST = "harvest"


_TRIGGERS = {
    Stage.ESTABLISHMENT: 5.0,
    Stage.VEG_AWD: -15.0,
    Stage.FLOWERING_LOCK: 3.0,
    Stage.GRAIN_FILL_AWD: -15.0,
}


def stage_on(day: int) -> Stage:
    if day < 0:
        raise ValueError("day after transplant cannot be negative")
    if day < 14:
        return Stage.ESTABLISHMENT
    if day < 55:
        return Stage.VEG_AWD
    if day < 80:
        return Stage.FLOWERING_LOCK
    if day < 100:
        return Stage.GRAIN_FILL_AWD
    return Stage.HARVEST


def trigger_level_cm(stage: Stage, scaled: bool = False) -> float | None:
    t = _TRIGGERS.get(stage)
    if t is None:
        return None
    if scaled and t < 0:
        return t / 3.0
    return t
