
from fastapi import APIRouter, HTTPException

from app.services.analytics_service import (
    calculate_product_analytics,
)

router = APIRouter(
    prefix="/api/analytics",
    tags=["Analytics"],
)


@router.get("/overview")
def analytics_overview():
    try:
        return calculate_product_analytics()

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not calculate product analytics.",
        ) from exc
