from fastapi import APIRouter

from app.evidence import e3_evidence_payload, vision_evidence_payload

router = APIRouter(prefix="/api/v1/evidence", tags=["evidence"])


@router.get("/e3")
def evidence_e3():
    return e3_evidence_payload()


@router.get("/vision")
def evidence_vision():
    return vision_evidence_payload()
