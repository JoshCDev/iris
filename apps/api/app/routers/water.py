"""Plot-scoped v1 water observation + Today aggregation."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import db
from app.db_l1 import (
    insert_recommendation,
    insert_water_observation,
    latest_recommendation,
    supersede_older_recommendations,
)
from app.irrigation.protocol import stage_on
from app.irrigation.scheduler import decide
from app.weather.snapshots import (
    capture_weather_snapshot,
    latest_weather_snapshot,
    weather_state_payload,
)

router = APIRouter(prefix="/api/v1/plots", tags=["water"])

_WIB = timezone(timedelta(hours=7))  # noqa: F821 — see note below
RULESET_VERSION = "safe-awd-v1"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _wib_today() -> date:
    return datetime.now(_WIB).date()


def _stage_days(transplant_date: date) -> int:
    return max(0, (_wib_today() - transplant_date).days)


def _correlation_id() -> str:
    import uuid
    return str(uuid.uuid4())


def _stage_for(plot) -> str:
    return stage_on(_stage_days(date.fromisoformat(plot["transplant_date"])))


def _data_kind(source: str | None) -> str:
    """§11.2 data-kind distinction: manual | sensor | simulation | other.

    Maps the stored observation source onto the chart legend vocabulary;
    unknown/legacy sources fall back to "other" (no claim made)."""
    if source is None:
        return "other"
    if source == "manual":
        return "manual"
    if source == "sensor":
        return "sensor"
    if source in ("simulation", "demo"):
        return "simulation"
    return "other"


class WaterObservationIn(BaseModel):
    level_cm: float
    source: Literal["manual", "sensor", "imported", "demo", "simulation"] = "manual"
    observed_at: str | None = None
    raw_distance: float | None = None
    actor: str | None = None


def _today_payload(conn, plot) -> dict[str, Any]:
    pid = int(plot["id"])
    obs = conn.execute(
        "SELECT * FROM water_observations WHERE plot_id = ?"
        " ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
    rec = latest_recommendation(conn, pid)
    weather = weather_state_payload(conn, pid)
    leaf = conn.execute(
        "SELECT * FROM leaf_assessments WHERE plot_id = ?"
        " ORDER BY id DESC LIMIT 1", (pid,)).fetchone()

    freshness = {"state": "current", "last_observed_at": None}
    water = {"level_cm": None, "source": None, "kind": "other",
             "stage": _stage_for(plot)}
    if obs is not None:
        freshness["last_observed_at"] = obs["observed_at"]
        water = {"level_cm": float(obs["level_cm"]),
                 "source": obs["source"], "kind": _data_kind(obs["source"]),
                 "stage": _stage_for(plot)}

    recommendation = None
    if rec is not None:
        conf = conn.execute(
            "SELECT status FROM action_confirmations"
            " WHERE recommendation_id = ? ORDER BY id DESC LIMIT 1",
            (rec["id"],)).fetchone()
        # The latest confirmation only counts as "confirmed" when the farmer
        # actually performed the action; a defer/decline/correction leaves the
        # recommendation pending (final whole-branch review, Finding 1).
        confirmed = conf is not None and conf["status"] == "performed"
        recommendation = {
            "id": int(rec["id"]),
            "action": rec["action"],
            "reason_codes": json.loads(rec["reason_codes"]),
            "ruleset_version": rec["ruleset_version"],
            "needs_review": bool(rec["needs_review"]),
            "confirmation_state": "confirmed" if confirmed else "pending",
        }

    latest_leaf = None
    if leaf is not None:
        latest_leaf = {
            "id": int(leaf["id"]),
            "class": leaf["class"],
            "confidence": (float(leaf["confidence"])
                           if leaf["confidence"] is not None else None),
            "severity": leaf["severity"],
            "evidence_type": leaf["evidence_type"],
            "created_at": leaf["created_at"],
        }

    return {
        "plot": {"id": pid, "name": plot["name"],
                 "is_demo": bool(plot["is_demo"])},
        "freshness": freshness,
        "water": water,
        "weather": weather,
        "recommendation": recommendation,
        "latest_leaf": latest_leaf,
    }


@router.get("/{plot_id}/today")
def plot_today(plot_id: int):
    with db.session_scope() as conn:
        plot = db.get_plot(conn, plot_id)
        if plot is None:
            raise HTTPException(status_code=404,
                                detail={"code": "plot_not_found",
                                        "message": "plot not found"})
        return _today_payload(conn, plot)


@router.get("/{plot_id}/weather")
def plot_weather(plot_id: int):
    from app.irrigation.rain_hitl import weather_payload

    with db.session_scope() as conn:
        plot = db.get_plot(conn, plot_id)
        if plot is None:
            raise HTTPException(status_code=404,
                                detail={"code": "plot_not_found",
                                        "message": "plot not found"})
        state = weather_state_payload(conn, plot_id)
        snap = latest_weather_snapshot(conn, plot_id)
        if snap is not None and snap.availability != "unavailable":
            hitl = weather_payload(float(snap.rain72_mm or 0.0), False)
        else:
            hitl = None
        state["hitl"] = hitl
        return state


@router.get("/{plot_id}/water-history")
def water_history(plot_id: int, limit: int = 20, offset: int = 0):
    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))
    with db.session_scope() as conn:
        plot = db.get_plot(conn, plot_id)
        if plot is None:
            raise HTTPException(status_code=404,
                                detail={"code": "plot_not_found",
                                        "message": "plot not found"})
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM water_observations WHERE plot_id = ?",
            (plot_id,)).fetchone()["n"]
        obs = [
            {"id": int(o["id"]), "level_cm": float(o["level_cm"]),
             "source": o["source"], "kind": _data_kind(o["source"]),
             "observed_at": o["observed_at"],
             "received_at": o["received_at"],
             "quality_state": o["quality_state"], "demo": bool(o["demo"])}
            for o in conn.execute(
                "SELECT * FROM water_observations WHERE plot_id = ?"
                " ORDER BY id DESC LIMIT ? OFFSET ?",
                (plot_id, limit, offset)).fetchall()]
        recs = [
            {"id": int(r["id"]), "action": r["action"],
             "reason_codes": json.loads(r["reason_codes"]),
             "ruleset_version": r["ruleset_version"],
             "created_at": r["created_at"], "superseded_at": r["superseded_at"],
             "needs_review": bool(r["needs_review"])}
            for r in conn.execute(
                "SELECT * FROM recommendations WHERE plot_id = ?"
                " ORDER BY id DESC LIMIT ? OFFSET ?",
                (plot_id, limit, offset)).fetchall()]
    return {"plot_id": plot_id, "observations": obs,
            "recommendations": recs, "total": int(total)}


@router.post("/{plot_id}/water-observations")
def post_water_observation(plot_id: int, body: WaterObservationIn):
    with db.session_scope() as conn:
        plot = db.get_plot(conn, plot_id)
        if plot is None:
            raise HTTPException(status_code=404,
                                detail={"code": "plot_not_found",
                                        "message": "plot not found"})
        if not -30.0 <= body.level_cm <= 30.0:
            return JSONResponse(
                status_code=422,
                content={"code": "implausible_level",
                         "message": "level_cm must be between -30 and 30 cm",
                         "correlation_id": _correlation_id()})
        observed_at = body.observed_at or _utc_now_iso()
        received_at = _utc_now_iso()
        obs_id = insert_water_observation(
            conn, plot_id=plot_id, source=body.source,
            level_cm=body.level_cm, observed_at=observed_at,
            received_at=received_at, raw_distance=body.raw_distance,
            actor=body.actor, quality_state="ok",
            demo=bool(plot["is_demo"]))
        snap = capture_weather_snapshot(
            conn, plot_id, demo=bool(plot["is_demo"]))
        stage = stage_on(_stage_days(date.fromisoformat(plot["transplant_date"])))
        rain = snap.rain72_mm if snap.availability != "unavailable" else 0.0
        dec = decide(
            body.level_cm, stage, rain,
            water_fresh=True, weather_availability=snap.availability)
        rec_id = insert_recommendation(
            conn, plot_id=plot_id, observation_id=obs_id,
            weather_snapshot_id=snap.id, stage=stage.value,
            action=dec.action, reason_codes=json.dumps([dec.reason_id]),
            ruleset_version=RULESET_VERSION,
            created_at=_utc_now_iso(),
            needs_review=(weather_state_payload(conn, plot_id)
                          ["secondary_review"]["needs_review"]),
            demo=bool(plot["is_demo"]))
        supersede_older_recommendations(
            conn, plot_id, keep_id=rec_id, superseded_at=_utc_now_iso())
        return _today_payload(conn, plot)
