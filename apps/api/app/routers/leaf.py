"""v1 rice-leaf screening endpoints (LEAF-001..010)."""
from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app import db
from app.db_l1 import insert_leaf_assessment
from app.vision.image_guard import ImageRejectedError

router = APIRouter(prefix="/api/v1/plots", tags=["leaf"])


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/{plot_id}/leaf-assessments")
async def post_leaf_assessment(
    plot_id: int,
    image: UploadFile = File(...),
):
    from app.main import (
        RICE_SLUG, _ensure_vision_loaded, advisory_service, crop_packs,
        image_guard, inference_service,
    )
    from app.vision.inference import LowConfidenceRejection
    from app.vision.severity import calculate_severity

    if not _ensure_vision_loaded():
        raise HTTPException(status_code=503,
                            detail={"code": "vision_unavailable",
                                    "message": "vision model unavailable"})
    with db.session_scope() as conn:
        plot = db.get_plot(conn, plot_id)
        if plot is None:
            raise HTTPException(status_code=404,
                                detail={"code": "plot_not_found",
                                        "message": "plot not found"})
    image_bytes = await image.read()
    try:
        image_guard.validate_upload(image_bytes)
        quality = image_guard.analyze(image_bytes)
    except ImageRejectedError as exc:
        status = 413 if exc.code == "upload_too_large" else 422
        return JSONResponse(status_code=status,
                            content={"code": exc.code, "detail": exc.message})

    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(
            None, inference_service.predict,
            RICE_SLUG, image_bytes, image.filename or "leaf.jpg",
            quality.metrics)
    except LowConfidenceRejection as exc:
        _store(plot_id, image_bytes, "low_confidence", None, None, None,
               None, demo=bool(plot["is_demo"]))
        return JSONResponse(status_code=422,
                            content={"code": "low_confidence",
                                     "detail": exc.message})

    predicted = result.predicted
    disease_class = crop_packs.get_class_by_slug(RICE_SLUG,
                                                 predicted.class_slug)
    _score, severity_lbl, _review = calculate_severity(
        class_slug=predicted.class_slug,
        confidence=predicted.confidence,
        risk_weight=float(disease_class["risk_weight"]),
        recent_same_area_count=0,
        default_expert_review=False)
    advisories = advisory_service.build_bilingual(RICE_SLUG,
                                                  predicted.class_slug)
    fusion_payload = _plot_fusion(plot_id, predicted.class_slug)
    assessment_id = _store(
        plot_id, image_bytes, "ok", predicted.class_slug,
        float(predicted.confidence), severity_lbl,
        result.model_version, demo=bool(plot["is_demo"]))
    return {
        "id": assessment_id,
        "class": predicted.class_slug,
        "class_label_en": disease_class["name_en"],
        "confidence": float(predicted.confidence),
        "severity": severity_lbl,
        "evidence_type": "public-dataset",
        "model_version": result.model_version,
        "disclaimer": "Screening, not a diagnosis. Confirm with an extension officer.",
        "advisory_id": advisories["id"]["summary"],
        "advisory_en": advisories["en"]["summary"],
        "fusion": fusion_payload,
        "is_demo": bool(plot["is_demo"]),
    }


def _plot_fusion(plot_id: int, class_slug: str) -> dict | None:
    """Combined plot concern (disease × AWD state × wet weather) from the
    latest v1 water observation + weather snapshot — the same unified
    records every other page reads."""
    from app.fusion.risk import assess, awd_state_from, wet_weather_from_rain
    from app.main import _VISION_DISEASE_CLASSES
    from app.weather.snapshots import latest_weather_snapshot

    with db.session_scope() as conn:
        obs = conn.execute(
            "SELECT level_cm FROM water_observations WHERE plot_id = ?"
            " ORDER BY id DESC LIMIT 1", (plot_id,)).fetchone()
        snap = latest_weather_snapshot(conn, plot_id)
        rec = conn.execute(
            "SELECT stage FROM recommendations WHERE plot_id = ?"
            " ORDER BY id DESC LIMIT 1", (plot_id,)).fetchone()
    if obs is None or rec is None:
        return None
    rain72 = (float(snap.rain72_mm)
              if snap is not None and snap.rain72_mm is not None else 0.0)
    disease = class_slug if class_slug in _VISION_DISEASE_CLASSES else "none"
    awd_state = awd_state_from(float(obs["level_cm"]), rec["stage"])
    return assess(disease, awd_state, wet_weather_from_rain(rain72))


@router.get("/{plot_id}/leaf-assessments")
def list_leaf_assessments(plot_id: int, limit: int = 20, offset: int = 0):
    """Paginated assessment history (newest first)."""
    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))
    with db.session_scope() as conn:
        plot = db.get_plot(conn, plot_id)
        if plot is None:
            raise HTTPException(status_code=404,
                                detail={"code": "plot_not_found",
                                        "message": "plot not found"})
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM leaf_assessments WHERE plot_id = ?",
            (plot_id,)).fetchone()["n"]
        rows = conn.execute(
            "SELECT * FROM leaf_assessments WHERE plot_id = ?"
            " ORDER BY id DESC LIMIT ? OFFSET ?",
            (plot_id, limit, offset)).fetchall()
    return {"plot_id": plot_id, "total": int(total),
            "assessments": [
                {"id": int(r["id"]), "class": r["class"],
                 "confidence": (float(r["confidence"])
                                if r["confidence"] is not None else None),
                 "severity": r["severity"],
                 "evidence_type": r["evidence_type"],
                 "created_at": r["created_at"], "demo": bool(r["demo"])}
                for r in rows]}


def _store(plot_id, image_bytes, guard_result, class_, confidence,
           severity, model_version, *, demo) -> int:
    with db.session_scope() as conn:
        return insert_leaf_assessment(
            conn, plot_id=plot_id,
            image_hash=hashlib.sha256(image_bytes).hexdigest(),
            retention_mode="operational",
            model_version=model_version or "unknown",
            guard_result=guard_result,
            class_=class_, confidence=confidence, severity=severity,
            evidence_type="public-dataset", created_at=_utc_now_iso(),
            demo=demo)
