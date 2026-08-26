"""Rain LogReg second opinion, plus a human-review flag.

The logistic regression is not HITL. HITL is the person who confirms.
This module scores P(wet) and sets needs_review when that score disagrees
with BMKG or sits in an uncertain band. BMKG remains the scheduler input.
This model never forces HOLD_FOR_RAIN.

Weights are fit offline on Open-Meteo daily precipitation for Salatiga
(see experiments/train_rain_logreg.py) and stored in rain_logreg.json.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Sequence

RAIN_SKIP_MM = 15.0
UNCERTAIN_LO = 0.35
UNCERTAIN_HI = 0.65
SALATIGA_LAT = -7.331
SALATIGA_LON = 110.508
_WEIGHTS_PATH = Path(__file__).resolve().parent / "rain_logreg.json"


def sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)


def _default_weights() -> tuple[float, ...]:
    if _WEIGHTS_PATH.exists():
        blob = json.loads(_WEIGHTS_PATH.read_text(encoding="utf-8"))
        return tuple(float(x) for x in blob["weights"])
    return (-0.8, 0.04, 0.03, 0.2, -0.1)


def features(recent_1d_mm: float, recent_3d_mm: float, doy: int) -> list[float]:
    ang = 2.0 * math.pi * ((doy - 1) % 365) / 365.0
    return [1.0, float(recent_1d_mm), float(recent_3d_mm), math.sin(ang), math.cos(ang)]


@dataclass(frozen=True)
class RainHitl:
    bmkg_rain72_mm: float
    bmkg_wet: bool
    logreg_p_wet: float
    logreg_wet: bool
    needs_review: bool
    recent_1d_mm: float
    recent_3d_mm: float
    source: str
    note: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "bmkg_rain72_mm": self.bmkg_rain72_mm,
            "bmkg_wet": self.bmkg_wet,
            "logreg_p_wet": self.logreg_p_wet,
            "logreg_wet": self.logreg_wet,
            "needs_review": self.needs_review,
            "recent_1d_mm": self.recent_1d_mm,
            "recent_3d_mm": self.recent_3d_mm,
            "source": self.source,
            "note": self.note,
        }


def assess_rain_hitl(
    bmkg_rain72_mm: float,
    recent_1d_mm: float = 0.0,
    recent_3d_mm: float = 0.0,
    *,
    doy: int | None = None,
    weights: Sequence[float] | None = None,
    source: str = "features",
) -> RainHitl:
    if doy is None:
        doy = date.today().timetuple().tm_yday
    w = tuple(weights) if weights is not None else _default_weights()
    x = features(recent_1d_mm, recent_3d_mm, doy)
    logit = sum(wi * xi for wi, xi in zip(w, x))
    p = round(sigmoid(logit), 4)
    bmkg_wet = float(bmkg_rain72_mm) >= RAIN_SKIP_MM
    logreg_wet = p >= 0.5
    uncertain = UNCERTAIN_LO <= p <= UNCERTAIN_HI
    disagree = bmkg_wet != logreg_wet
    needs_review = bool(uncertain or disagree)
    if disagree:
        note = (
            "Human review: BMKG 72 h wetness and the persistence LogReg disagree. "
            "The scheduler still uses BMKG; do not skip irrigation on the model alone."
        )
    elif uncertain:
        note = (
            "Human review: rain-hold probability is uncertain. "
            "Confirm before treating a HOLD_FOR_RAIN as settled."
        )
    else:
        note = "BMKG and the persistence LogReg agree. Forecast remains supporting only."
    return RainHitl(
        bmkg_rain72_mm=round(float(bmkg_rain72_mm), 1),
        bmkg_wet=bmkg_wet,
        logreg_p_wet=p,
        logreg_wet=logreg_wet,
        needs_review=needs_review,
        recent_1d_mm=round(float(recent_1d_mm), 1),
        recent_3d_mm=round(float(recent_3d_mm), 1),
        source=source,
        note=note,
    )


def fetch_recent_precip(lat: float = SALATIGA_LAT,
                        lon: float = SALATIGA_LON) -> tuple[float, float, str]:
    """Last 1-day and 3-day observed rain (mm). Fail-soft to zeros."""
    try:
        import httpx

        end = date.today()
        start = end - timedelta(days=3)
        r = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "daily": "precipitation_sum",
                "timezone": "Asia/Jakarta",
            },
            timeout=8.0,
            headers={"User-Agent": "IRIS/1.0 (INOVATALK 2026)"},
        )
        r.raise_for_status()
        vals = [float(v or 0.0) for v in r.json().get("daily", {}).get("precipitation_sum") or []]
        if not vals:
            return 0.0, 0.0, "doy_only"
        recent_1d = vals[-1]
        recent_3d = sum(vals[-3:])
        return round(recent_1d, 1), round(recent_3d, 1), "open-meteo"
    except Exception:
        return 0.0, 0.0, "doy_only"


def weather_payload(rain72_mm: float, stale: bool) -> dict[str, Any]:
    r1, r3, src = fetch_recent_precip()
    hitl = assess_rain_hitl(rain72_mm, r1, r3, source=src)
    return {"rain72_mm": round(float(rain72_mm), 1), "stale": bool(stale),
            "hitl": hitl.as_dict()}
