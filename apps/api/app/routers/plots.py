from fastapi import APIRouter, Depends

from app import db
from app.security import require_demo_interaction

router = APIRouter(prefix="/api/v1/plots", tags=["plots"],
                   dependencies=[Depends(require_demo_interaction)])


@router.get("")
def list_plots():
    with db.session_scope() as conn:
        rows = conn.execute(
            "SELECT id, name, is_demo FROM plots ORDER BY id ASC").fetchall()
    return {"plots": [
        {"id": int(r["id"]), "name": r["name"], "is_demo": bool(r["is_demo"])}
        for r in rows]}
