from fastapi import APIRouter, HTTPException, Query

from app.services.ml_review_service import cluster_review_themes

router = APIRouter(prefix="/api/ml", tags=["ML Intelligence"])


@router.get("/review-clusters")
def review_clusters(n_clusters: int = Query(default=4, ge=2, le=8)):
    try:
        return cluster_review_themes(n_clusters=n_clusters)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Could not cluster customer reviews.") from exc
