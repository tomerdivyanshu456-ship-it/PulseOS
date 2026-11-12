from fastapi import APIRouter

from app.services.health_service import build_product_health

router = APIRouter(prefix="/api/health-scorecard", tags=["Product Health"])


@router.get("")
def product_health_scorecard():
    return build_product_health()
