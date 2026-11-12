from fastapi import APIRouter, HTTPException

from app.services.diagnostic_service import build_root_cause_diagnostics

router = APIRouter(prefix="/api/diagnostics", tags=["Product Root Cause Explorer"])


@router.get("/root-causes")
def root_cause_diagnostics():
    try:
        return build_root_cause_diagnostics()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not assemble product diagnostic hypotheses.",
        ) from exc
