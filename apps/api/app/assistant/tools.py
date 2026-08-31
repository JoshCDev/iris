"""IRIS assistant tools: pinned JSON-schema definitions + handlers.

Handlers call internal services DIRECTLY (db helpers, irrigation/fusion/rag
modules) - never HTTP self-calls. The vision pipeline is imported lazily so
the assistant keeps working before/without the vision module ("vision is not
ready").

Image refs: the chat endpoint registers base64 payloads from messages into an
in-memory {ref: image_bytes} dict with a 10-minute TTL via
register_image_ref(); run_vision_triage consumes those refs.
"""
from __future__ import annotations

import base64
import binascii
import json
import secrets
import time
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Image-ref registry (in-memory, 10-min TTL)
# ---------------------------------------------------------------------------

_IMAGE_TTL_S = 600.0
_IMAGE_REFS: dict[str, tuple[bytes, float]] = {}

_now: Callable[[], float] = time.monotonic


def _purge_expired() -> None:
    now = _now()
    expired = [k for k, (_, deadline) in _IMAGE_REFS.items() if now >= deadline]
    for k in expired:
        _IMAGE_REFS.pop(k, None)


def register_image_ref(data: bytes) -> str:
    """Store image bytes and return a short-lived ref for the vision tool."""
    _purge_expired()
    ref = "img_" + secrets.token_hex(8)
    _IMAGE_REFS[ref] = (data, _now() + _IMAGE_TTL_S)
    return ref


def get_image_ref(ref: str) -> bytes | None:
    _purge_expired()
    entry = _IMAGE_REFS.get(ref)
    return entry[0] if entry else None


def register_image_dataref(image_ref: str) -> str:
    """Normalize a chat-message image_ref (raw b64 / data URI / existing ref).

    Existing registered refs pass through; anything else is decoded as base64
    and registered. Raises ValueError on undecodable payloads.
    """
    if image_ref.startswith("img_") and image_ref in _IMAGE_REFS:
        return image_ref
    payload = (image_ref.split(",", 1)[1]
               if image_ref.startswith("data:") else image_ref)
    try:
        data = base64.b64decode(payload, validate=False)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("image_ref is not valid base64") from exc
    if not data:
        raise ValueError("image_ref is empty")
    return register_image_ref(data)


# ---------------------------------------------------------------------------
# Pinned tool schemas (function-calling)
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    {"type": "function", "function": {
        "name": "get_plot_status",
        "description": (
            "Current rice-plot Today status: water level (cm), growth stage, "
            "stored irrigation action + reason codes, confirmation state, "
            "and 72-hour rain. Explain the stored records; do not recompute "
            "a decision. Without plot_id, uses the first registered plot."),
        "parameters": {"type": "object", "properties": {
            "plot_id": {"type": "integer",
                        "description": "Plot ID (optional)"},
        }, "required": []},
    }},
    {"type": "function", "function": {
        "name": "get_weather",
        "description": (
            "Stored weather snapshot for the plot: availability "
            "(fresh/stale-cache/unavailable), 72-hour rain, and a "
            "persistence second opinion (HITL flag). Rain is never "
            "fabricated; when unavailable, say the data is unavailable."),
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "run_vision_triage",
        "description": (
            "Rice-leaf photo check (disease class, confidence, severity, "
            "advisory). This is screening, not a diagnosis. Use the image_ref "
            "from the user's attached message."),
        "parameters": {"type": "object", "properties": {
            "image_ref": {"type": "string",
                          "description": "Registered image reference"},
        }, "required": ["image_ref"]},
    }},
    {"type": "function", "function": {
        "name": "search_kb",
        "description": (
            "Search the IRIS knowledge base (safe AWD, rice growth stages, "
            "disease advisory). Use the facts; do not paste file names into "
            "the farmer-facing reply."),
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string",
                      "description": "Question or keywords"},
        }, "required": ["query"]},
    }},
    {"type": "function", "function": {
        "name": "get_receipt",
        "description": (
            "Season green receipt from E3 backtest (100 days, 1 ha): "
            "37.5% water saved, IPCC Tier-1 CH4 and CO2e, label [simulated]. "
            "Not the 30-day demo-plot window. Literature meta-analyses "
            "(larger CH4 cuts) are a separate aggregate, not this plot."),
        "parameters": {"type": "object", "properties": {
            "plot_id": {"type": "integer",
                        "description": "Plot ID"},
        }, "required": ["plot_id"]},
    }},
    {"type": "function", "function": {
        "name": "get_risk_fusion",
        "description": (
            "Risk fusion: detected disease × AWD water state × wet weather "
            "→ risk level + explanation + irrigation note."),
        "parameters": {"type": "object", "properties": {
            "plot_id": {"type": "integer",
                        "description": "Plot ID"},
        }, "required": ["plot_id"]},
    }},
]

_WET_WEATHER_MM = 15.0


def _vision_stack():
    """Lazy-import the vision services (singletons live on app.main).

    Kept as a module-level function so tests can simulate the pre-vision
    state by raising ImportError here.
    """
    from app.main import (RICE_SLUG, _ensure_vision_loaded, advisory_service,
                          crop_packs, image_guard, inference_service)
    from app.vision.image_guard import ImageRejectedError
    from app.vision.inference import LowConfidenceRejection
    from app.vision.severity import calculate_severity

    return (RICE_SLUG, _ensure_vision_loaded, advisory_service, crop_packs,
            image_guard, inference_service, ImageRejectedError,
            LowConfidenceRejection, calculate_severity)


def args_summary(args: dict[str, Any]) -> str:
    try:
        return json.dumps(args, ensure_ascii=False, sort_keys=True)[:120]
    except (TypeError, ValueError):
        return str(args)[:120]


# ---------------------------------------------------------------------------
# Handlers (thin wrappers over internal services)
# ---------------------------------------------------------------------------

def get_plot_status(plot_id: int | None = None) -> dict[str, Any]:
    """Return the v1 Today payload: stored recommendation + confirmation
    state. The assistant explains records; it never computes a decision."""
    from app.db import get_plot, session_scope
    from app.routers.water import _today_payload

    with session_scope() as conn:
        if plot_id is None:
            row = conn.execute(
                "SELECT id FROM plots ORDER BY id ASC LIMIT 1").fetchone()
            if row is None:
                return {"error": "no plots registered yet"}
            plot_id = int(row["id"])
        else:
            plot_id = int(plot_id)
        plot = get_plot(conn, plot_id)
        if plot is None:
            return {"error": f"plot {plot_id} not found"}
        return _today_payload(conn, plot)


def get_weather() -> dict[str, Any]:
    """Return the stored weather state; never fabricate a 0 mm value."""
    from app.db import session_scope
    from app.weather.snapshots import latest_weather_snapshot, weather_state_payload

    with session_scope() as conn:
        row = conn.execute(
            "SELECT id FROM plots ORDER BY id ASC LIMIT 1").fetchone()
        if row is None:
            return {"error": "no plots registered yet"}
        state = weather_state_payload(conn, int(row["id"]))
        snap = latest_weather_snapshot(conn, int(row["id"]))
        if snap is not None and snap.availability != "unavailable":
            from app.irrigation.rain_hitl import weather_payload
            state["hitl"] = weather_payload(float(snap.rain72_mm or 0.0), False)
        else:
            state["hitl"] = None
        return state


def run_vision_triage(image_ref: str) -> dict[str, Any]:
    data = get_image_ref(image_ref or "")
    if data is None:
        return {"error": "unknown or expired image_ref"}
    try:
        (rice_slug, ensure_loaded, advisory_service, crop_packs, image_guard,
         inference_service, image_rejected_error, low_confidence_error,
         calculate_severity) = _vision_stack()
    except ImportError:
        return {"error": "vision is not ready"}
    if not ensure_loaded():
        return {"error": "vision is not ready"}

    try:
        quality = image_guard.analyze(data)
        result = inference_service.predict(
            rice_slug, data, file_name="assistant.jpg",
            quality_metrics=quality.metrics)
    except image_rejected_error as exc:
        detail = getattr(exc, "message", str(exc))
        return {"error": f"photo rejected: {detail}"}
    except low_confidence_error as exc:
        detail = getattr(exc, "message", str(exc))
        return {"error": f"need a clearer leaf photo ({detail})"}
    except Exception as exc:
        return {"error": f"triage failed: {exc}"}

    predicted = result.predicted
    disease_class = crop_packs.get_class_by_slug(rice_slug,
                                                 predicted.class_slug)
    risk_rule = crop_packs.risk_rule_for(rice_slug, predicted.class_slug)
    _score, severity_lbl, _review = calculate_severity(
        class_slug=predicted.class_slug,
        confidence=predicted.confidence,
        risk_weight=float(disease_class["risk_weight"]),
        recent_same_area_count=0,
        default_expert_review=bool(
            risk_rule.get("default_expert_review", False)),
    )
    advisories = advisory_service.build_bilingual(rice_slug,
                                                  predicted.class_slug)
    return {
        "top_class": predicted.class_slug,
        "class_label_id": disease_class["name_id"],
        "class_label_en": disease_class["name_en"],
        "confidence": float(predicted.confidence),
        "severity": severity_lbl,
        "advisory_id": advisories["id"]["summary"],
        "advisory_en": advisories["en"]["summary"],
        "note": "screening, not a diagnosis",
    }


def search_kb(query: str) -> dict[str, Any]:
    from app.rag import get_kb_search

    ans = get_kb_search().answer(query)
    return {"answer": ans.text, "citations": ans.citations,
            "confident": ans.confident}


def get_receipt(plot_id: int) -> dict[str, Any]:
    from app.db import get_plot, session_scope
    from app.receipts import E3_CLAIM_NOTE, build_e3_receipt, receipt_json

    with session_scope() as conn:
        plot = get_plot(conn, int(plot_id))
        if plot is None:
            return {"error": f"plot {plot_id} not found"}
        receipt = build_e3_receipt(plot["name"])
        return receipt_json(
            int(plot_id), receipt, claim_source="e3_backtest",
            claim_note=E3_CLAIM_NOTE)


def get_risk_fusion(plot_id: int) -> dict[str, Any]:
    """Combined plot concern from the v1 records (leaf_assessments,
    water_observations, recommendations) — the same unified data the
    rest of the app reads, so the assistant's fusion agrees with the
    screens shown on Water/Leaf/Ask."""
    from app.db import get_plot, session_scope
    from app.fusion.risk import assess, awd_state_from

    pid = int(plot_id)
    with session_scope() as conn:
        plot = get_plot(conn, pid)
        if plot is None:
            return {"error": f"plot {pid} not found"}
        obs = conn.execute(
            "SELECT level_cm FROM water_observations WHERE plot_id = ?"
            " ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
        rec = conn.execute(
            "SELECT r.stage, w.rain72_mm FROM recommendations r"
            " LEFT JOIN weather_snapshots w"
            "   ON w.id = r.weather_snapshot_id"
            " WHERE r.plot_id = ? ORDER BY r.id DESC LIMIT 1",
            (pid,)).fetchone()
        leaf = conn.execute(
            "SELECT class FROM leaf_assessments WHERE plot_id = ?"
            " ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
    if obs is None:
        return {"error": "no water observation yet for this plot"}
    level_cm = float(obs["level_cm"])
    stage_val = (rec["stage"] if rec is not None
                 else _stage_for_plot(plot))
    disease = (leaf["class"] if leaf is not None and leaf["class"]
               else "none")
    if disease == "healthy":
        disease = "none"
    rain72 = (float(rec["rain72_mm"])
              if rec is not None and rec["rain72_mm"] is not None
              else 0.0)
    awd_state = awd_state_from(level_cm, stage_val)
    wet = rain72 >= _WET_WEATHER_MM
    result = assess(disease, awd_state, wet)
    return {"plot_id": pid, "disease": disease, "awd_state": awd_state,
            "rain72_mm": rain72, "wet_weather": wet, **result}


def _stage_for_plot(plot) -> str:
    from datetime import date, datetime, timedelta, timezone

    from app.irrigation.protocol import stage_on

    wib = timezone(timedelta(hours=7))
    days = max(0, (datetime.now(wib).date()
                   - date.fromisoformat(plot["transplant_date"])).days)
    return stage_on(days).value


_EXECUTORS: dict[str, Callable[..., Any]] = {
    "get_plot_status": get_plot_status,
    "get_weather": get_weather,
    "run_vision_triage": run_vision_triage,
    "search_kb": search_kb,
    "get_receipt": get_receipt,
    "get_risk_fusion": get_risk_fusion,
}


def dispatch(name: str, args: dict[str, Any]) -> tuple[Any, float]:
    """Run one tool call; returns (result, elapsed_ms). Never raises."""
    fn = _EXECUTORS.get(name)
    if fn is None:
        return {"error": f"unknown tool: {name}"}, 0.0
    started = time.perf_counter()
    try:
        out = fn(**args)
    except TypeError:
        out = {"error": f"invalid arguments for tool {name}"}
    except Exception as exc:
        out = {"error": f"tool failed: {exc}"}
    ms = (time.perf_counter() - started) * 1000.0
    return out, round(ms, 1)
