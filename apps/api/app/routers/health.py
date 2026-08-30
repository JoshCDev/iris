from fastapi import APIRouter

from app import db

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("/ready")
def readiness():
    try:
        with db.session_scope() as conn:
            conn.execute("SELECT 1").fetchone()
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {"status": "ok" if db_status == "ok" else "degraded",
            "db": db_status}
