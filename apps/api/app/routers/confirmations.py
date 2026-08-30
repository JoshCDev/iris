"""Human confirmation records for immutable recommendations (ACT-001..005)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import db
from app.db_l1 import (
    insert_action_confirmation,
    recommendation_with_confirmations,
)

router = APIRouter(prefix="/api/v1/recommendations", tags=["confirmations"])


class ConfirmationIn(BaseModel):
    status: Literal["performed", "deferred", "declined", "corrected"]
    note: str | None = Field(default=None, max_length=500)
    volume_m3: float | None = Field(default=None, ge=0.0)
    action_at: str | None = None
    actor_id: int | None = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/{recommendation_id}/confirmations")
def post_confirmation(recommendation_id: int, body: ConfirmationIn):
    with db.session_scope() as conn:
        row = conn.execute(
            "SELECT * FROM recommendations WHERE id = ?",
            (recommendation_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404,
                                detail={"code": "recommendation_not_found",
                                        "message": "recommendation not found"})
        insert_action_confirmation(
            conn, recommendation_id=recommendation_id,
            status=body.status, created_at=_utc_now_iso(),
            actor_id=body.actor_id, action_at=body.action_at,
            volume_m3=body.volume_m3, note=body.note,
            demo=bool(row["demo"]))
        return recommendation_with_confirmations(conn, recommendation_id)


@router.get("/{recommendation_id}")
def get_recommendation(recommendation_id: int):
    with db.session_scope() as conn:
        out = recommendation_with_confirmations(conn, recommendation_id)
    if out is None:
        raise HTTPException(status_code=404,
                            detail={"code": "recommendation_not_found",
                                    "message": "recommendation not found"})
    return out
