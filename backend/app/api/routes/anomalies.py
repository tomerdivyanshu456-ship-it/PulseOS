from fastapi import APIRouter, HTTPException

from app.services.anomaly_service import detect_product_anomalies

router = APIRouter(prefix="/api/ml", tags=["ML Intelligence"])


@router.get("/product-anomalies")
def product_anomalies():
    try:
        return detect_product_anomalies()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Could not detect product anomalies.") from exc
