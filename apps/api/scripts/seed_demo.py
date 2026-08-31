"""Deterministic demo seeder for the IRIS platform (pinned contract).

Drives the REAL protocol + scheduler code paths: every reading is pushed
through `app.irrigation.scheduler.decide` exactly like a live ingest, so the
seeded decisions/irrigations are what the audited engine would have produced.

Contract:
- plot "Sawah Demo - Salatiga" (1 ha, pipe_zero 30 cm, lat -7.3305,
  lon 110.5064, transplant_date = today(WIB) - 30 d, is_demo = 1)
- 2880 readings = 30 days x 96/day @ 15 min, anchored to transplant midnight
  WIB (deterministic within a day)
- diurnal-noise drawdown sawtooth between -15 and +5 cm
- one synthetic rain event on days 18-19 (rain72_mm = 22) producing >= 1
  HOLD_FOR_RAIN decision
- battery voltage 3.8-4.1 V
- idempotent: re-running replaces all is_demo=1 rows
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db
from app.config import get_settings
from app.db import session_scope
from app.db_l1 import (
    insert_recommendation,
    insert_water_observation,
    insert_weather_snapshot_row,
)
from app.irrigation.bmkg_areas import ensure_bmkg_areas
from app.irrigation.protocol import stage_on
from app.irrigation.scheduler import REFILL_CM, decide
from app.irrigation.water import level_cm_to_m3
from app.vision.crop_packs import RICE_SLUG  # light: json/pathlib only
from app.vision.severity import calculate_severity

WIB = timezone(timedelta(hours=7))

PLOT_NAME = "Sawah Demo - Salatiga"
VARIETY = "Ciherang"
AREA_HA = 1.0
PIPE_ZERO_CM = 30.0
LAT = -7.3305
LON = 110.5064

STEPS_PER_DAY = 96
CADENCE_MIN = 15
DAYS = 30
TOTAL_STEPS = DAYS * STEPS_PER_DAY  # 2880

RAIN_EVENT_DAYS = (16, 17, 18)
RAIN72_MM = 22.0
# Simulated storm intensity per rain-event day, in mm per 15-minute step.
# Sums to 22 mm over the 3-day event (day 16 light showers ~5 mm, day 17
# peak ~12 mm, day 18 tail ~5 mm) so RAIN72_MM stays the wet-forecast value
# the scheduler sees and HOLD_FOR_RAIN still fires on days 16-18.
STORM_MM_PER_STEP = (0.8, 2.0, 0.8)

# Rain-to-pond efficiency: only a fraction of the fallen rain actually
# raises the field-tube level (canopy interception, bund overflow, runoff).
RAIN_RISE_FRACTION = 0.45

VEG_TRIGGER_CM = -15.0


def _transplant_date(today: date | None = None) -> date:
    return ((today or datetime.now(WIB).date()) - timedelta(days=DAYS))


def _grid_start_utc(transplant: date) -> datetime:
    """Transplant midnight WIB expressed in UTC."""
    return datetime(transplant.year, transplant.month, transplant.day,
                    tzinfo=WIB).astimezone(timezone.utc)


def _diurnal_factor(minute_of_day: float) -> float:
    return 1.0 + 0.35 * math.sin(2.0 * math.pi * minute_of_day / 1440.0
                                 - math.pi / 2.0)


def _simulate_series(start_ts: datetime) -> list[dict[str, Any]]:
    """Generate readings+engine decisions for the whole window.

    The trace is deliberately not a clean sawtooth: drainage varies
    day to day (weather-driven ET), the simulated storm actually lifts
    the pond, and the sensor adds a little jitter — closer to a real
    field-tube record than a perfectly even dry-down.
    """
    rng_day = random.Random(42)       # day-to-day drainage-rate variation
    rng_step = random.Random(2024)    # within-day drawdown jitter
    rng_sensor = random.Random(7)     # sensor noise on the reported level
    rng_batt = random.Random(1337)
    out: list[dict[str, Any]] = []
    level = REFILL_CM

    # Drainage base rate per day (cm per 15-min step), varying ±45% around
    # 0.10 cm to mimic hotter/drier days vs cooler/cloudier ones.
    day_rates = [
        round(0.10 * rng_day.uniform(0.55, 1.45), 4)
        for _ in range(DAYS)
    ]
    # A couple of short "cooler/cloudier" spells where drainage slows for a
    # day or two (lower ET), then recovers — keeps the dry-down irregular.
    for spell_start in (9, 23):
        for d in range(spell_start, min(spell_start + 2, DAYS)):
            day_rates[d] = round(day_rates[d] * 0.55, 4)
    # A dry, windy couple of days just before the storm: drainage speeds up so
    # the pond actually reaches the AWD trigger in time for the rain-hold
    # logic to fire when the wet forecast arrives (realistic pre-storm dry-down).
    for d in (15, 16):
        day_rates[d] = round(day_rates[d] * 2.1, 4)
    for i in range(TOTAL_STEPS):
        day_index = i // STEPS_PER_DAY
        step_in_day = i % STEPS_PER_DAY
        minute_of_day = step_in_day * CADENCE_MIN
        ts = start_ts + timedelta(minutes=CADENCE_MIN * i)
        stage = stage_on(day_index)

        if stage.value == "establishment":
            # Field kept flooded by continuous inflow; level hugs +5 with a
            # gentle daily cycle plus a little sensor noise.
            wiggle = 0.35 * (0.5 - 0.5 * math.cos(
                2.0 * math.pi * minute_of_day / 1440.0))
            level = REFILL_CM + 0.05 + wiggle \
                + rng_sensor.uniform(-0.06, 0.06)
        else:
            rate = day_rates[day_index] * _diurnal_factor(minute_of_day) \
                * rng_step.uniform(0.85, 1.15)
            level = level - rate
            # The simulated storm actually raises the pond: each rain-event
            # day adds a burst of rainfall through the day that lifts the
            # field-tube level (a fraction of the rain reaches the pond).
            if day_index in RAIN_EVENT_DAYS:
                event_pos = RAIN_EVENT_DAYS.index(day_index)
                mm = STORM_MM_PER_STEP[event_pos]
                # Bursts in the afternoon/evening (typical convective rain),
                # tapering through the day.
                burst = 1.0 + 1.6 * math.exp(
                    -((minute_of_day - 960.0) / 240.0) ** 2)
                level = level + mm * burst * RAIN_RISE_FRACTION / 10.0
                # Heavy rain can also soften the dry-down that step.
                level = level + rng_step.uniform(0.0, 0.02)

        # Small sensor noise on the reported reading (sub-cm jitter).
        reported = level + rng_sensor.uniform(-0.05, 0.05)

        dec = _decide_for(reported, stage, day_index)

        irrigation_m3 = None
        if dec.action == "IRRIGATE":
            deficit_cm = max(0.0, (dec.refill_to_cm or REFILL_CM) - level)
            if deficit_cm > 0:
                irrigation_m3 = level_cm_to_m3(deficit_cm, AREA_HA)
                level = dec.refill_to_cm or REFILL_CM

        batt_v = min(4.1, max(3.8, 3.95 + 0.075 * math.sin(i / 300.0)
                              + rng_batt.uniform(-0.02, 0.02)))
        out.append({
            "i": i,
            "ts": ts.isoformat(),
            "day_index": day_index,
            "stage": stage.value,
            "level_cm": round(reported, 3),
            "dist_cm": round(PIPE_ZERO_CM - round(reported, 3), 3),
            "batt_v": round(batt_v, 2),
            "action": dec.action,
            "reason_id": dec.reason_id,
            "rain72_mm": rain72_mm(day_index),
            "irrigation_m3": irrigation_m3,
        })
    return out


def rain72_mm(day_index: int) -> float:
    """72 h forecast the scheduler sees on a given day (22 mm on rain days)."""
    return RAIN72_MM if day_index in RAIN_EVENT_DAYS else 0.0


def _decide_for(level_cm: float, stage, day_index: int):
    """Run the real scheduler with the day's wet-forecast value."""
    return decide(level_cm, stage, rain72_mm(day_index))


def _build_series() -> list[dict[str, Any]]:
    start = _grid_start_utc(_transplant_date())
    series = _simulate_series(start)
    holds = sum(1 for s in series if s["action"] == "HOLD_FOR_RAIN")
    if holds < 1:
        raise RuntimeError(
            "seeder contract violated: no HOLD_FOR_RAIN decision produced")
    return series


_VISION: dict[str, Any] = {}


def _vision_services():
    """Lazily built, reused across seed runs (one ONNX session total)."""
    if "svc" in _VISION:
        return _VISION["svc"]
    from app.vision.advisory import AdvisoryService
    from app.vision.crop_packs import CropPackService
    from app.vision.image_guard import ImageGuardService
    from app.vision.inference import InferenceService

    pack_dir = Path(__file__).resolve().parents[1] / "crop_packs" / "rice"
    packs = CropPackService(pack_dir.parent)
    packs.load()
    inference = InferenceService(packs)
    inference.load()
    if not inference.onnx.is_loaded(RICE_SLUG):
        _VISION["svc"] = None
        return None
    _VISION["svc"] = (packs, inference, ImageGuardService(),
                      AdvisoryService(packs))
    return _VISION["svc"]


def _seed_vision_reports(conn, plot_id: int) -> int:
    """Run the REAL triage pipeline on two bundled sample images and persist
    the results as demo vision reports (is_demo=1).

    Deterministic: same bytes -> same ONNX logits -> same stored values.
    Fast: one cached ONNX session, exactly two inferences per seed run.
    """
    pack_dir = Path(__file__).resolve().parents[1] / "crop_packs" / "rice"
    samples = ["rice-blast-demo.jpg", "rice-blast-demo.webp"]
    if not (pack_dir / "model.onnx").exists():
        return 0
    services = _vision_services()
    if services is None:
        return 0
    packs, inference, guard, advisory = services

    base_ts = _grid_start_utc(_transplant_date())
    inserted = 0
    for n, name in enumerate(samples):
        path = pack_dir / name
        if not path.exists():
            continue
        image_bytes = path.read_bytes()
        try:
            quality = guard.analyze(image_bytes)
            result = inference.predict(
                RICE_SLUG, image_bytes, file_name=name,
                quality_metrics=quality.metrics)
        except Exception:
            continue
        predicted = result.predicted
        disease_class = packs.get_class_by_slug(RICE_SLUG,
                                                predicted.class_slug)
        risk_rule = packs.risk_rule_for(RICE_SLUG, predicted.class_slug)
        _score, severity_lbl, _review = calculate_severity(
            class_slug=predicted.class_slug,
            confidence=predicted.confidence,
            risk_weight=float(disease_class["risk_weight"]),
            recent_same_area_count=0,
            default_expert_review=bool(risk_rule.get("default_expert_review",
                                                     False)),
        )
        advisories = advisory.build_bilingual(RICE_SLUG,
                                              predicted.class_slug)
        ts = (base_ts + timedelta(days=DAYS - 1, minutes=15 * n)).isoformat()
        conn.execute(
            "INSERT INTO vision_reports (plot_id, ts, image_path, top_class,"
            " confidence, severity, language, advisory_json, fusion_json,"
            " is_demo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, 1)",
            (plot_id, ts, name, predicted.class_slug,
             float(predicted.confidence), severity_lbl, "id",
             json.dumps(advisories)))
        inserted += 1
    return inserted


def _seed_v1_records(conn, plot_id: int, series: list[dict[str, Any]]) -> dict[str, int]:
    """Mirror the demo series into the L1 (v1) tables.

    Every Nth simulated reading becomes a `water_observations` row with a
    matching `weather_snapshots` row and an immutable `recommendations`
    row — the same records Today/Water/Records/Assistant read — so the
    demo is consistent across pages without any manual entry first.
    Manual-source rows are sprinkled in so the chart's data-kind
    distinction is visible (sensor vs manual).
    """
    step = 96  # one row per simulated day
    snap_idx = 0
    n_obs = n_snap = n_rec = 0
    for i in range(0, len(series), step):
        s = series[i]
        observed_at = s["ts"]
        received_at = observed_at
        source = "manual" if i % (step * 7) == 0 else "sensor"
        obs_id = insert_water_observation(
            conn, plot_id=plot_id, source=source,
            level_cm=s["level_cm"], observed_at=observed_at,
            received_at=received_at, quality_state="ok", demo=True)
        n_obs += 1
        snap_id = insert_weather_snapshot_row(
            conn, plot_id=plot_id, source="BMKG", adm4="33.73.01.1003",
            fetched_at=observed_at,
            window_end=(datetime.fromisoformat(observed_at)
                        + timedelta(hours=72)).isoformat(),
            rain72_mm=s["rain72_mm"], availability="fresh", demo=True)
        snap_idx += 1
        n_snap += 1
        rec_id = insert_recommendation(
            conn, plot_id=plot_id, observation_id=obs_id,
            weather_snapshot_id=snap_id, stage=s["stage"],
            action=s["action"], reason_codes=json.dumps([s["reason_id"]]),
            ruleset_version="safe-awd-v1", created_at=received_at,
            needs_review=False, demo=True)
        n_rec += 1
    return {"observations": n_obs, "weather_snapshots": n_snap,
            "recommendations": n_rec}


def seed_demo(db_url: str | None = None) -> dict[str, Any]:
    series = _build_series()
    database = db.init_db(db_url) if db_url else db.get_db()
    with session_scope(database) as conn:
        n_areas = 0
        if not os.environ.get("IRIS_SKIP_DOTENV"):
            n_areas = ensure_bmkg_areas(conn)
        replaced = db.delete_demo_rows(conn)
        transplant = _transplant_date()
        plot_id = db.create_plot(
            conn, name=PLOT_NAME, transplant_date=transplant.isoformat(),
            variety=VARIETY, area_ha=AREA_HA, pipe_zero_cm=PIPE_ZERO_CM,
            scaled=False, lat=LAT, lon=LON, bmkg_adm4="33.73.01.1003",
            is_demo=True)
        for s in series:
            db.insert_reading(conn, plot_id=plot_id, ts=s["ts"],
                              dist_cm=s["dist_cm"],
                              level_cm=s["level_cm"], batt_v=s["batt_v"])
            db.insert_decision(conn, plot_id=plot_id, ts=s["ts"],
                               stage=s["stage"], level_cm=s["level_cm"],
                               action=s["action"], reason_id=s["reason_id"],
                               rain72_mm=s["rain72_mm"])
            if s["irrigation_m3"] is not None:
                db.insert_irrigation(conn, plot_id=plot_id, ts=s["ts"],
                                     volume_m3=round(s["irrigation_m3"], 2))
        n_irr = db.count_rows(conn, "irrigations", plot_id)
        n_read = db.count_rows(conn, "readings", plot_id)
        n_dec = db.count_rows(conn, "decisions", plot_id)
        holds = conn.execute(
            "SELECT COUNT(*) AS n FROM decisions WHERE plot_id = ?"
            " AND action = 'HOLD_FOR_RAIN'", (plot_id,)).fetchone()["n"]
        vision_reports = _seed_vision_reports(conn, plot_id)
        v1 = _seed_v1_records(conn, plot_id, series)
    return {
        "plot_id": plot_id,
        "name": PLOT_NAME,
        "readings": n_read,
        "decisions": n_dec,
        "irrigations": n_irr,
        "hold_for_rain": int(holds),
        "vision_reports": vision_reports,
        "v1": v1,
        "replaced_plots": replaced,
        "bmkg_areas": n_areas,
        "is_demo": True,
    }


def default_db_url() -> str:
    return get_settings().iris_db


def main() -> None:
    ap = argparse.ArgumentParser(description="Seed IRIS demo data")
    ap.add_argument("--db", default=None)
    args = ap.parse_args()
    summary = seed_demo(args.db)
    print(f"seeded {summary['readings']} readings into "
          f"{args.db or default_db_url()}: {summary}")


if __name__ == "__main__":
    main()
