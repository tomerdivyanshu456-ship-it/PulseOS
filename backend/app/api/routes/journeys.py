from fastapi import APIRouter, HTTPException, Query

from app.services.journey_service import calculate_journey_intelligence

router = APIRouter(prefix="/api/analytics", tags=["Funnel & Journey Intelligence"])


@router.get("/journeys")
def journey_intelligence(
    steps: str | None = Query(default=None, description="Comma-separated ordered event names"),
    dimension: str | None = Query(default=None),
):
    try:
        selected_steps = [item.strip() for item in steps.split(",")] if steps else None
        return calculate_journey_intelligence(selected_steps, dimension)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Could not calculate funnel and journey intelligence.") from exc
