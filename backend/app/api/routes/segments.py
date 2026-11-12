from fastapi import APIRouter, HTTPException, Query

from app.services.segment_service import calculate_segment_intelligence

router = APIRouter(prefix="/api/analytics", tags=["Cohort & Segment Intelligence"])


@router.get("/segments")
def segment_intelligence(dimension: str | None = Query(default=None)):
    try:
        return calculate_segment_intelligence(dimension)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Could not calculate segment intelligence.") from exc