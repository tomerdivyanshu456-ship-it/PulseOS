from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

from app.services.strategy_service import build_product_strategy

router = APIRouter(prefix="/api/strategy", tags=["Product Strategy & Insights"])


class StrategyPrioritiseRequest(BaseModel):
    effort_estimates: dict[str, int] = Field(default_factory=dict)

    @field_validator("effort_estimates")
    @classmethod
    def validate_effort_estimates(cls, values):
        for opportunity_id, effort in values.items():
            if not opportunity_id.strip():
                raise ValueError("Opportunity IDs cannot be empty.")
            if isinstance(effort, bool) or not isinstance(effort, int) or not 1 <= effort <= 5:
                raise ValueError("Effort estimates must be integers from 1 to 5.")
        return values


@router.get("")
def product_strategy():
    try:
        return build_product_strategy()
    except ValueError as exc:
        return {
            "status": "no_data",
            "summary": {"opportunities_reviewed": 0, "high_priority_count": 0, "experiments_linked": 0, "top_recommendation": None},
            "recommendations": [],
            "data_gaps": [str(exc)],
            "sources": {"events": False, "reviews": False},
            "methodology": "Upload product events or customer reviews to generate a strategy.",
        }


@router.post("/prioritise")
def prioritise_strategy(payload: StrategyPrioritiseRequest):
    try:
        return build_product_strategy(payload.effort_estimates)
    except ValueError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=str(exc)) from exc
