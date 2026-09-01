"""Versioned evidence payloads (WEBAPP_SPEC §7.9, §8.5)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.vision.crop_packs import CROP_PACK_ROOT

_REPO = Path(__file__).resolve().parents[3]
E3_SUMMARY_PATH = _REPO / "experiments" / "outputs" / "backtest_summary.json"
VISION_METRICS_PATH = _REPO / "experiments" / "outputs" / "vision_test_metrics.json"
RICE_METADATA_PATH = CROP_PACK_ROOT / "rice" / "metadata.json"

_DEFAULT_RICE_MODEL_VERSION = "rice-mobilenet-v3-large-v0.3.0-onnx"


def _generated_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rice_model_version() -> str:
    metadata = json.loads(RICE_METADATA_PATH.read_text(encoding="utf-8"))
    return str(metadata.get("model_version", _DEFAULT_RICE_MODEL_VERSION))


def e3_evidence_payload() -> dict[str, Any]:
    data = json.loads(E3_SUMMARY_PATH.read_text(encoding="utf-8"))
    cf = data["continuous_flooding"]
    e3 = data["iris_e3"]
    water_saved_pct = round(
        (1.0 - float(e3["water_m3_ha_season"])
         / float(cf["water_m3_ha_season"])) * 100.0, 2)
    return {
        "evidence_type": "simulated",
        "label": "DEFINED SIMULATION",
        "title": "IRIS defined scheduler simulation (E3)",
        "assumptions": {
            "season_days": int(data["scenario"]["season_days"]),
            "area_ha": float(data["scenario"]["area_ha"]),
            "rain_mm": float(data["scenario"]["rain_mm"]),
            "drawdown_cm_per_day": float(
                data["scenario"]["drawdown_cm_per_day"]),
        },
        "values": {
            "water_cf_m3": float(cf["water_m3_ha_season"]),
            "water_awd_m3": float(e3["water_m3_ha_season"]),
            "water_saved_pct": water_saved_pct,
            "flooded_days_awd": int(e3["flooded_days"]),
            "ch4_cf_kg": float(cf["ch4_kg_ha_season"]),
            "ch4_awd_kg": float(e3["ch4_kg_ha_season"]),
            "co2e_saved_t": float(e3["ch4_only_avoided_co2e_t_ha_season"]),
        },
        "disclosures": [
            "The -15 cm refill trigger did not activate in vegetative or "
            "grain-fill stages during E3 (minimum simulated level -14.6 cm).",
            "Scheduled irrigation volume in the defined scenario, not a "
            "measured water saving on any plot.",
        ],
        "source_version": "backtest_summary.json",
        "calculation_version": "1",
        "generated_at": _generated_at(),
    }


def vision_evidence_payload() -> dict[str, Any]:
    data = json.loads(VISION_METRICS_PATH.read_text(encoding="utf-8"))
    return {
        "evidence_type": "public-dataset",
        "label": "PUBLIC-DATASET BENCHMARK",
        "title": "Rice-leaf screening model — held-out public dataset",
        "n": int(data.get("n_images", data.get("n", 1621))),
        "accuracy": float(data["overall_accuracy"]),
        "macro_f1": float(data["macro_f1"]),
        "model_version": _rice_model_version(),
        "field_validation": "pending",
        "note": "Indonesian field validation remains pending.",
        "source_version": "vision_test_metrics.json",
        "calculation_version": "1",
        "generated_at": _generated_at(),
    }
