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
import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db
from app.config import get_settings
from app.db import session_scope
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

RAIN_EVENT_DAYS = (18, 19)
RAIN72_MM = 22.0

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
    """Generate readings+engine decisions for the whole window."""
    rng_level = random.Random(42)
    rng_batt = random.Random(1337)
    out: list[dict[str, Any]] = []
    level = REFILL_CM
    for i in range(TOTAL_STEPS):
        day_index = i // STEPS_PER_DAY
        step_in_day = i % STEPS_PER_DAY
        minute_of_day = step_in_day * CADENCE_MIN
        ts = start_ts + timedelta(minutes=CADENCE_MIN * i)
        stage = stage_on(day_index)
        rain72 = RAIN72_MM if day_index in RAIN_EVENT_DAYS else 0.0

        if stage.value == "establishment":
            # Field kept flooded by continuous inflow; level hugs +5.
            wiggle = 0.35 * (0.5 - 0.5 * math.cos(
                2.0 * math.pi * minute_of_day / 1440.0))
            level = round(REFILL_CM + 0.05 + wiggle, 3)
        else:
            rate = 0.10 * _diurnal_factor(minute_of_day) \
                * rng_level.uniform(0.85, 1.15)
            level = level - rate

        dec = decide(level, stage, rain72)

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
            "level_cm": round(level, 3),
            "dist_cm": round(PIPE_ZERO_CM - round(level, 3), 3),
            "batt_v": round(batt_v, 2),
            "action": dec.action,
            "reason_id": dec.reason_id,
            "rain72_mm": rain72,
            "irrigation_m3": irrigation_m3,
        })
    return out


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


def seed_demo(db_url: str | None = None) -> dict[str, Any]:
    series = _build_series()
    database = db.init_db(db_url) if db_url else db.get_db()
    with session_scope(database) as conn:
        replaced = db.delete_demo_rows(conn)
        transplant = _transplant_date()
        plot_id = db.create_plot(
            conn, name=PLOT_NAME, transplant_date=transplant.isoformat(),
            variety=VARIETY, area_ha=AREA_HA, pipe_zero_cm=PIPE_ZERO_CM,
            scaled=False, lat=LAT, lon=LON, is_demo=True)
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
    return {
        "plot_id": plot_id,
        "name": PLOT_NAME,
        "readings": n_read,
        "decisions": n_dec,
        "irrigations": n_irr,
        "hold_for_rain": int(holds),
        "vision_reports": vision_reports,
        "replaced_plots": replaced,
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
