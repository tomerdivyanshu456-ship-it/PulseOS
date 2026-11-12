from fastapi import APIRouter, HTTPException

from app.services.opportunity_service import calculate_product_opportunities

router = APIRouter(
    prefix="/api/opportunities",
    tags=["Product Opportunities"],
)


@router.get("")
def product_opportunities():
    try:
        return calculate_product_opportunities()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not identify product opportunities.",
        ) from exc
