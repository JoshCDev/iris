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
    return {
        "evidence_type": "simulated",
        "label": "DEFINED SIMULATION",
        "title": "IRIS defined scheduler simulation (E3)",
        "assumptions": {
            "season_days": 100,
            "area_ha": 1.0,
            "rain_mm": 0,
            "drawdown_cm_per_day": 0.8,
        },
        "values": {
            "water_cf_m3": float(data["water_cf_m3"]),
            "water_awd_m3": float(data["water_awd_m3"]),
            "water_saved_pct": float(data["water_saved_pct"]),
            "flooded_days_awd": int(data["flooded_days_awd"]),
            "ch4_cf_kg": float(data["ch4_cf_kg"]),
            "ch4_awd_kg": float(data["ch4_awd_kg"]),
            "co2e_saved_t": float(data["co2e_saved_t"]),
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
