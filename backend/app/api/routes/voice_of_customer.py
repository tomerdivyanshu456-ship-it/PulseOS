from fastapi import APIRouter, HTTPException

from app.services.voice_of_customer_service import (
    calculate_voice_of_customer,
)

router = APIRouter(
    prefix="/api/analytics",
    tags=["Voice of Customer"],
)


@router.get("/voice-of-customer")
def voice_of_customer():
    try:
        return calculate_voice_of_customer()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not analyse customer reviews.",
        ) from exc
