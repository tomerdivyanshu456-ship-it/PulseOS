from fastapi import APIRouter, HTTPException, Query

from app.services.churn_service import predict_customer_churn

router = APIRouter(prefix="/api/ml", tags=["ML Intelligence"])


@router.get("/customer-churn")
def customer_churn(dataset_id: str = Query(..., min_length=1)):
    try:
        return predict_customer_churn(dataset_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Could not train the customer churn models.") from exc
