"""Rule-based risk fusion: AWD hydrology state x weather x detected disease.

Pure functions only, driven by fusion_rules.json (pinned matrix). No ML in v1
 -  rules are explainable on stage.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.irrigation.protocol import Stage

_RULES_PATH = Path(__file__).resolve().parent / "fusion_rules.json"

AWD_FLOODED = "flooded"
AWD_SHALLOW_DRY = "shallow_dry"
AWD_DEEP_DRY = "deep_dry"
AWD_BEYOND_TRIGGER = "beyond_trigger"
AWD_FLOWERING_LOCK = "flowering_lock"


@lru_cache(maxsize=1)
def load_rules() -> dict[str, Any]:
    with open(_RULES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def wet_weather_from_rain(rain72_mm: float) -> bool:
    return rain72_mm >= float(load_rules()["wet_weather_threshold_mm"])


def awd_state_from(level_cm: float, stage: Stage | str) -> str:
    """Map a water level (+ stage) to a fusion awd_state band.

    Bands (pinned): flooded >= 0 · shallow_dry -8..0 (exclusive of -8) ·
    deep_dry -15..-8 · beyond_trigger < -15 · flowering_lock overrides by stage.
    """
    if isinstance(stage, Stage):
        stage_val = stage.value
    else:
        stage_val = str(stage)
    if stage_val == Stage.FLOWERING_LOCK.value:
        return AWD_FLOWERING_LOCK
    if level_cm >= 0.0:
        return AWD_FLOODED
    if level_cm > -8.0:
        return AWD_SHALLOW_DRY
    if level_cm >= -15.0:
        return AWD_DEEP_DRY
    return AWD_BEYOND_TRIGGER


def assess(disease: str, awd_state: str, wet_weather: bool) -> dict[str, Any]:
    """Evaluate the pinned fusion matrix.

    Returns {"risk_level", "drivers_id", "drivers_en"} plus optional
    "irrigation_note". Unknown combinations fall back to low + generic note.
    """
    rules = load_rules()
    for rule in rules["rules"]:
        when = rule["when"]
        if disease not in when["disease"]:
            continue
        if awd_state not in when["awd_state"]:
            continue
        expected_wet = when["wet_weather"]
        if expected_wet is not None and bool(expected_wet) != bool(wet_weather):
            continue
        out: dict[str, Any] = {
            "risk_level": rule["risk_level"],
            "drivers_id": list(rule["drivers_id"]),
            "drivers_en": list(rule["drivers_en"]),
        }
        note = rule.get("irrigation_note")
        if note:
            out["irrigation_note"] = note
        return out
    fb = rules["fallback"]
    out = {
        "risk_level": fb["risk_level"],
        "drivers_id": list(fb["drivers_id"]),
        "drivers_en": list(fb["drivers_en"]),
    }
    if fb.get("irrigation_note"):
        out["irrigation_note"] = fb["irrigation_note"]
    return out
