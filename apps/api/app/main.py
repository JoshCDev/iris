import json
import logging
import os
import secrets
import time as _time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import db
from app.config import get_settings
from app.fusion.risk import assess as fusion_assess
from app.fusion.risk import awd_state_from as fusion_awd_state_from
from app.fusion.risk import wet_weather_from_rain
from app.irrigation.ipcc import build_receipt
from app.irrigation.protocol import stage_on, trigger_level_cm
from app.irrigation.reason_text import english_reason
from app.irrigation.scheduler import REFILL_CM, decide
from app.irrigation.bmkg_areas import ensure_bmkg_areas, lookup_bmkg_areas
from app.irrigation.weather_bmkg import fetch_forecast_72h_rain
from app.irrigation.rain_hitl import weather_payload
from app.receipts import (
    E3_CLAIM_NOTE,
    PLOT_CLAIM_NOTE,
    build_e3_receipt,
    receipt_json,
)
from app.vision.advisory import AdvisoryService
from app.vision.crop_packs import RICE_SLUG, CropPackService
from app.vision.image_guard import ImageGuardService, ImageRejectedError
from app.vision.inference import InferenceService, LowConfidenceRejection
from app.vision.severity import calculate_severity

log = logging.getLogger("iris")

_WIB = timezone(timedelta(hours=7))
_SENSOR_CADENCE_MIN = 15


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _wib_today() -> date:
    return datetime.now(_WIB).date()


def _stage_days(transplant_date: date, today: date | None = None) -> int:
    return max(0, ((today if today is not None else _wib_today())
                   - transplant_date).days)


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


app = FastAPI(title="IRIS API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().web_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


db.init_db(get_settings().iris_db)
if not os.environ.get("IRIS_SKIP_DOTENV"):
    try:
        with db.session_scope() as _conn:
            n_areas = ensure_bmkg_areas(_conn)
            if n_areas:
                log.info("bmkg_areas: %s kelurahan", n_areas)
    except Exception:
        log.warning("bmkg_areas seed skipped", exc_info=True)


# --- vision singletons (rice pack; loaded lazily + on startup) --------------

crop_packs = CropPackService()
inference_service = InferenceService(crop_packs)
advisory_service = AdvisoryService(crop_packs)
image_guard = ImageGuardService()

_VISION_DISEASE_CLASSES = {"bacterial_leaf_blight", "blast", "brown_spot",
                           "tungro"}


def _ensure_vision_loaded() -> bool:
    """Idempotent ONNX load so health/predict work even without lifespan."""
    if not crop_packs.all_active():
        crop_packs.load()
    if not inference_service.onnx.is_loaded(RICE_SLUG):
        try:
            inference_service.load()
        except Exception:
            log.exception("ONNX load failed")
    return inference_service.onnx.is_loaded(RICE_SLUG)


@app.on_event("startup")
def _startup_load_vision() -> None:
    if _ensure_vision_loaded():
        log.info("vision: rice ONNX model loaded")


def require_token(
    token: str | None = Header(default=None, alias="X-IRIS-Token"),
) -> None:
    expected = get_settings().iris_device_token
    if not expected:
        return
    if token is None or not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="bad token")


class ReadingIn(BaseModel):
    device_plot_name: str
    dist_cm: float
    batt_v: float | None = None
    pipe_zero_cm: float | None = None


class PlotPatch(BaseModel):
    bmkg_adm4: str


def _status_payload(conn, plot) -> dict[str, Any]:
    plot_id = int(plot["id"])
    reading = db.latest_reading(conn, plot_id)
    dec = db.latest_decision(conn, plot_id)
    stage = stage_on(_stage_days(date.fromisoformat(plot["transplant_date"])))
    next_check = None
    if dec is not None:
        next_check = (_parse_ts(dec["ts"])
                      + timedelta(minutes=_SENSOR_CADENCE_MIN)).isoformat()
    return {
        "plot_id": plot_id,
        "name": plot["name"],
        "level_cm": float(reading["level_cm"]) if reading else None,
        "stage": stage.value,
        "stage_days": _stage_days(
            date.fromisoformat(plot["transplant_date"])),
        "action": dec["action"] if dec else None,
        "reason_id": english_reason(dec["reason_id"]) if dec else None,
        "rain72_mm": (float(dec["rain72_mm"])
                      if dec is not None and dec["rain72_mm"] is not None
                      else None),
        "next_check": next_check,
        "last_ts": reading["ts"] if reading else None,
        "is_demo": bool(plot["is_demo"]),
    }


@app.post("/api/ingest", status_code=201)
def post_reading(body: ReadingIn, _: None = Depends(require_token)):
    today = _wib_today()
    with db.session_scope() as conn:
        plot = db.get_plot_by_name(conn, body.device_plot_name)
        if plot is None:
            if not (0.0 <= body.dist_cm <= 60.0):
                raise HTTPException(
                    status_code=422,
                    detail="dist_cm outside a plausible sensor range")
            pid = db.create_plot(conn, name=body.device_plot_name,
                                 transplant_date=today.isoformat(),
                                 **({"pipe_zero_cm": body.pipe_zero_cm}
                                    if body.pipe_zero_cm is not None else {}))
            plot = db.get_plot(conn, pid)
        elif not (0.0 <= body.dist_cm <= 2.0 * plot["pipe_zero_cm"]):
            raise HTTPException(
                status_code=422,
                detail="dist_cm outside a plausible sensor range")
        level = plot["pipe_zero_cm"] - body.dist_cm
        ts = _utc_now_iso()
        db.insert_reading(conn, plot_id=int(plot["id"]), ts=ts,
                          dist_cm=body.dist_cm, level_cm=level,
                          batt_v=body.batt_v)
        stage = stage_on(_stage_days(
            date.fromisoformat(plot["transplant_date"]), today))
        try:
            rain = fetch_forecast_72h_rain(plot=plot)
        except Exception:
            log.warning("weather fetch failed; using rain72_mm=0.0")
            rain = 0.0
        eff_level = level
        if plot["scaled"]:
            trig = trigger_level_cm(stage)
            if trig is not None and trig < 0:
                eff_level = level * 3.0
        dec = decide(eff_level, stage, rain)
        db.insert_decision(conn, plot_id=int(plot["id"]), ts=ts,
                           stage=stage.value, level_cm=level,
                           action=dec.action, reason_id=dec.reason_id,
                           rain72_mm=rain)
        if dec.action == "IRRIGATE":
            deficit_cm = max(0.0, (dec.refill_to_cm or REFILL_CM) - level)
            if deficit_cm > 0:
                db.insert_irrigation(
                    conn, plot_id=int(plot["id"]), ts=ts,
                    volume_m3=deficit_cm * 100.0 * plot["area_ha"])
        return _status_payload(conn, plot)


@app.get("/api/plots/{plot_id}/status")
def plot_status(plot_id: int):
    with db.session_scope() as conn:
        plot = db.get_plot(conn, plot_id)
        if plot is None:
            raise HTTPException(status_code=404, detail="plot not found")
        return _status_payload(conn, plot)


@app.get("/api/plots/{plot_id}/history")
def plot_history(plot_id: int, days: int = 7):
    if days <= 0 or days > 366:
        raise HTTPException(status_code=422, detail="days must be 1..366")
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with db.session_scope() as conn:
        plot = db.get_plot(conn, plot_id)
        if plot is None:
            raise HTTPException(status_code=404, detail="plot not found")
        readings = [
            {"ts": r["ts"], "dist_cm": float(r["dist_cm"]),
             "level_cm": float(r["level_cm"]),
             "batt_v": float(r["batt_v"]) if r["batt_v"] is not None else None}
            for r in conn.execute(
                "SELECT * FROM readings WHERE plot_id = ? AND ts >= ?"
                " ORDER BY ts ASC", (plot_id, since)).fetchall()]
        decisions = [
            {"ts": d["ts"], "stage": d["stage"],
             "level_cm": float(d["level_cm"]), "action": d["action"],
             "reason_id": d["reason_id"],
             "rain72_mm": float(d["rain72_mm"])
             if d["rain72_mm"] is not None else None}
            for d in conn.execute(
                "SELECT * FROM decisions WHERE plot_id = ? AND ts >= ?"
                " ORDER BY ts ASC", (plot_id, since)).fetchall()]
        return {"plot_id": plot_id, "name": plot["name"], "days": days,
                "readings": readings, "decisions": decisions}


def _flooded_days_from_readings(conn, plot_id: int,
                                transplant_date: date,
                                season_days: int) -> tuple[int, bool]:
    """Count distinct WIB days whose LAST reading still stands flooded.

    Returns (flooded_days, has_any_reading_in_window).
    """
    rows = conn.execute(
        "SELECT ts, level_cm FROM readings WHERE plot_id = ? ORDER BY ts ASC",
        (plot_id,),
    ).fetchall()
    if not rows:
        return 0, False
    horizon = transplant_date + timedelta(days=season_days)
    per_day: dict[str, float] = {}
    for r in rows:
        day_wib = _parse_ts(r["ts"]).astimezone(_WIB).date()
        if day_wib < transplant_date or day_wib >= horizon:
            continue
        per_day[day_wib.isoformat()] = float(r["level_cm"])
    flooded = sum(1 for lvl in per_day.values() if lvl >= 0.0)
    return flooded, True


@app.get("/api/plots/{plot_id}/receipt")
def plot_receipt(plot_id: int, season_days: int = 100, claim: str = "e3"):
    if season_days <= 0 or season_days > 366:
        raise HTTPException(status_code=422, detail="season_days must be positive")
    if claim not in ("e3", "plot"):
        raise HTTPException(status_code=422, detail="claim must be e3 or plot")
    with db.session_scope() as conn:
        plot = db.get_plot(conn, plot_id)
        if plot is None:
            raise HTTPException(status_code=404, detail="plot not found")
        if claim == "e3":
            receipt = build_e3_receipt(plot["name"])
            return receipt_json(
                plot_id, receipt, claim_source="e3_backtest",
                claim_note=E3_CLAIM_NOTE)
        transplant = date.fromisoformat(plot["transplant_date"])
        flooded_days, has_data = _flooded_days_from_readings(
            conn, plot_id, transplant, season_days)
        water_actual_m3 = float(conn.execute(
            "SELECT COALESCE(SUM(volume_m3), 0.0) AS v FROM irrigations"
            " WHERE plot_id = ?", (plot_id,)).fetchone()["v"])
        if not has_data or water_actual_m3 <= 0.0:
            raise HTTPException(
                status_code=409,
                detail="no reading/irrigation data yet for a green receipt")
        flooded_days = min(max(flooded_days, 0), season_days)
        if flooded_days <= 0:
            raise HTTPException(
                status_code=409,
                detail="no flooded days recorded; receipt cannot be computed")
        water_baseline_m3 = round(
            water_actual_m3 * season_days / flooded_days, 2)
        try:
            receipt = build_receipt(
                plot_name=plot["name"], season_days=season_days,
                flooded_days=flooded_days,
                water_baseline_m3=water_baseline_m3,
                water_actual_m3=round(water_actual_m3, 2),
                area_ha=float(plot["area_ha"]), label="simulated")
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        return receipt_json(
            plot_id, receipt, claim_source="plot_window",
            claim_note=PLOT_CLAIM_NOTE)


_weather_cache: dict[str, dict[str, Any]] = {}
_WEATHER_TTL_S = 15 * 60.0


def _adm4_for_plot(plot_id: int | None) -> str:
    from app.irrigation.weather_bmkg import DEFAULT_ADM4

    if plot_id is not None:
        with db.session_scope() as conn:
            plot = db.get_plot(conn, plot_id)
            if plot is not None and plot["bmkg_adm4"]:
                return str(plot["bmkg_adm4"])
    return get_settings().bmkg_adm4 or DEFAULT_ADM4


@app.get("/api/weather/forecast")
def weather_forecast(plot_id: int | None = None):
    adm4 = _adm4_for_plot(plot_id)
    now = _time.time()
    entry = _weather_cache.get(adm4)
    fresh = (entry is not None
             and now - entry["ts"] < _WEATHER_TTL_S)
    if fresh:
        return entry["payload"]
    try:
        rain = fetch_forecast_72h_rain(adm4=adm4)
    except Exception:
        log.warning("weather fetch failed; failing open")
        cached = entry["value"] if entry is not None else 0.0
        return weather_payload(cached, True)
    payload = weather_payload(rain, False)
    _weather_cache[adm4] = {"ts": now, "value": rain, "payload": payload}
    return payload


@app.get("/api/weather/areas")
def weather_areas(q: str = "", limit: int = 20):
    cap = max(1, min(int(limit), 50))
    with db.session_scope() as conn:
        ensure_bmkg_areas(conn)
        return {"results": lookup_bmkg_areas(conn, q, cap)}


@app.patch("/api/plots/{plot_id}")
def patch_plot(plot_id: int, body: PlotPatch):
    code = body.bmkg_adm4.strip()
    with db.session_scope() as conn:
        plot = db.get_plot(conn, plot_id)
        if plot is None:
            raise HTTPException(status_code=404, detail="plot not found")
        ensure_bmkg_areas(conn)
        hit = lookup_bmkg_areas(conn, code, 1)
        if not hit or hit[0]["kode_wilayah"] != code:
            raise HTTPException(status_code=400, detail="unknown bmkg_adm4")
        db.update_plot_bmkg_adm4(conn, plot_id, code)
        return {"plot_id": plot_id, "bmkg_adm4": code,
                "nama_wilayah": hit[0]["nama_wilayah"]}


@app.post("/api/demo/seed")
def demo_seed():
    from scripts.seed_demo import seed_demo
    summary = seed_demo()
    return summary


# --- vision endpoints --------------------------------------------------------

_PINNED_VISION_KEYS = {"report_id", "top_class", "class_label_id",
                       "class_label_en", "confidence", "severity",
                       "advisory_id", "advisory_en", "fusion", "is_demo"}


@app.post("/api/vision/predict")
async def vision_predict(
    image: UploadFile = File(...),
    plot_id: int | None = Form(default=None),
    language: str = Form(default="en"),
):
    language = "en" if language == "en" else "id"
    if not _ensure_vision_loaded():
        raise HTTPException(status_code=503, detail="vision model unavailable")
    image_bytes = await image.read()
    file_name = Path(image.filename or "upload.jpg").name

    # Stage 1: deterministic quality guard (blank/solid/non-leaf rejection).
    try:
        quality = image_guard.analyze(image_bytes)
    except ImageRejectedError as exc:
        return JSONResponse(status_code=422,
                            content={"code": "image_rejected",
                                     "detail": exc.message})

    # Stage 2: real ONNX triage - judge photos take the identical live path.
    try:
        result = inference_service.predict(
            RICE_SLUG, image_bytes, file_name=file_name,
            quality_metrics=quality.metrics)
    except LowConfidenceRejection as exc:
        return JSONResponse(status_code=422,
                            content={"code": "low_confidence",
                                     "detail": exc.message})
    predicted = result.predicted
    disease_class = crop_packs.get_class_by_slug(RICE_SLUG,
                                                 predicted.class_slug)
    risk_rule = crop_packs.risk_rule_for(RICE_SLUG, predicted.class_slug)
    _score, severity_lbl, _review = calculate_severity(
        class_slug=predicted.class_slug,
        confidence=predicted.confidence,
        risk_weight=float(disease_class["risk_weight"]),
        recent_same_area_count=0,
        default_expert_review=bool(risk_rule.get("default_expert_review",
                                                 False)),
    )
    advisories = advisory_service.build_bilingual(RICE_SLUG,
                                                  predicted.class_slug)

    # Stage 3: fusion with AWD hydrology + weather when a plot is given.
    fusion_payload: dict[str, Any] | None = None
    if plot_id is not None:
        with db.session_scope() as conn:
            plot = db.get_plot(conn, plot_id)
            if plot is None:
                raise HTTPException(status_code=404, detail="plot not found")
            dec = db.latest_decision(conn, plot_id)
        if dec is not None:
            awd_state = fusion_awd_state_from(float(dec["level_cm"]),
                                              dec["stage"])
            rain72 = float(dec["rain72_mm"]) if dec["rain72_mm"] is not None \
                else 0.0
            disease_for_fusion = (predicted.class_slug
                                  if predicted.class_slug
                                  in _VISION_DISEASE_CLASSES else "none")
            fusion_payload = fusion_assess(disease_for_fusion, awd_state,
                                           wet_weather_from_rain(rain72))

    ts = _utc_now_iso()
    with db.session_scope() as conn:
        cur = conn.execute(
            "INSERT INTO vision_reports (plot_id, ts, image_path, top_class,"
            " confidence, severity, language, advisory_json, fusion_json,"
            " is_demo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
            (plot_id, ts, file_name, predicted.class_slug,
             float(predicted.confidence), severity_lbl, language,
             json.dumps(advisories),
             json.dumps(fusion_payload) if fusion_payload is not None
             else None))
        report_id = int(cur.lastrowid)

    payload = {
        "report_id": report_id,
        "top_class": predicted.class_slug,
        "class_label_id": disease_class["name_id"],
        "class_label_en": disease_class["name_en"],
        "confidence": float(predicted.confidence),
        "severity": severity_lbl,
        "advisory_id": advisories["id"]["summary"],
        "advisory_en": advisories["en"]["summary"],
        "fusion": fusion_payload,
        "is_demo": False,
    }
    assert set(payload.keys()) == _PINNED_VISION_KEYS
    return payload


@app.get("/api/vision/reports")
def vision_reports_list():
    with db.session_scope() as conn:
        rows = conn.execute(
            "SELECT * FROM vision_reports ORDER BY id DESC LIMIT 20"
        ).fetchall()
    return {"reports": [
        {
            "report_id": r["id"],
            "ts": r["ts"],
            "plot_id": r["plot_id"],
            "top_class": r["top_class"],
            "confidence": float(r["confidence"]),
            "severity": r["severity"],
            "language": r["language"],
            "fusion": json.loads(r["fusion_json"])
            if r["fusion_json"] else None,
            "is_demo": bool(r["is_demo"]),
        }
        for r in rows
    ]}


@app.get("/api/health")
def health():
    from app.assistant.agent import fallback_engaged_recently, llm_status

    try:
        with db.session_scope() as conn:
            conn.execute("SELECT COUNT(*) FROM plots").fetchone()
        db_status = "ok"
    except Exception:
        db_status = "error"
    onnx_status = "loaded" if _ensure_vision_loaded() else "not_loaded"
    llm = llm_status()
    mode = ("offline"
            if llm == "unreachable" or fallback_engaged_recently()
            else "live")
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "db": db_status,
        "onnx": onnx_status,
        "llm": llm,
        "mode": mode,
    }


# ---------------------------------------------------------------------------
# Task D (M5): AI Assistant - additive block (pinned chat contract).
# ---------------------------------------------------------------------------

class ChatMessageIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    image_ref: str | None = None


class ChatIn(BaseModel):
    session_id: str
    messages: list[ChatMessageIn]


@app.post("/api/assistant/chat")
def assistant_chat(body: ChatIn):
    from app.assistant.agent import chat as agent_chat
    from app.assistant.tools import register_image_dataref

    msgs: list[dict[str, Any]] = []
    for m in body.messages:
        item: dict[str, Any] = {"role": m.role, "content": m.content}
        if m.image_ref:
            try:
                item["image_ref"] = register_image_dataref(m.image_ref)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc))
        msgs.append(item)
    return agent_chat(body.session_id, msgs)
