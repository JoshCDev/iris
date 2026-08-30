from fastapi import APIRouter

from app import db

router = APIRouter(prefix="/api/v1/plots", tags=["plots"])


@router.get("")
def list_plots():
    with db.session_scope() as conn:
        rows = conn.execute(
            "SELECT id, name, is_demo FROM plots ORDER BY id ASC").fetchall()
    return {"plots": [
        {"id": int(r["id"]), "name": r["name"], "is_demo": bool(r["is_demo"])}
        for r in rows]}
