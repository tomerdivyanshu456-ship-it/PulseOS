import os
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.security import require_auth, validate_production_config
from app.middleware import RequestBodyTooLarge, RequestSizeLimitMiddleware
from app.api.routes.auth import router as auth_router
from app.api.routes.workspace import router as workspace_router

from app.api.routes.datasets import router as datasets_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.voice_of_customer import router as voice_of_customer_router
from app.api.routes.analyst import router as analyst_router
from app.api.routes.opportunities import router as opportunities_router
from app.api.routes.experiments import router as experiments_router
from app.api.routes.strategy import router as strategy_router
from app.api.routes.health_scorecard import router as health_scorecard_router
from app.api.routes.segments import router as segments_router
from app.api.routes.journeys import router as journeys_router
from app.api.routes.diagnostics import router as diagnostics_router
from app.api.routes.ml_intelligence import router as ml_intelligence_router
from app.api.routes.anomalies import router as anomalies_router
from app.api.routes.churn import router as churn_router

validate_production_config()

app = FastAPI(
    title="PulseOS API",
    description="Product Intelligence Platform",
    version="0.1.0",
)


@app.exception_handler(RequestBodyTooLarge)
async def request_body_too_large_handler(_request, _exc):
    return JSONResponse(
        status_code=413,
        content={"detail": "Request body exceeds the 21 MB server limit."},
    )

cors_origins = [item.strip().rstrip("/") for item in os.getenv("PULSEOS_CORS_ORIGINS", "").split(",") if item.strip()]
cors_options = {
    "allow_origins": cors_origins,
    "allow_credentials": False,
    "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    "allow_headers": ["Authorization", "Content-Type"],
}
if os.getenv("PULSEOS_ENV", "development").strip().lower() != "production":
    cors_options["allow_origin_regex"] = r"https?://(localhost|127\.0\.0\.1):\d+"
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=21 * 1024 * 1024)
app.add_middleware(CORSMiddleware, **cors_options)

# Health and auth configuration remain public. All workspace APIs are protected
# whenever an administrator password is configured.
app.include_router(auth_router)
# This router uses Supabase Bearer authentication and database RLS, not admin Basic auth.
app.include_router(workspace_router)
protected = {"dependencies": [Depends(require_auth)]}
app.include_router(datasets_router, **protected)
app.include_router(analytics_router, **protected)
app.include_router(voice_of_customer_router, **protected)
app.include_router(analyst_router, **protected)
app.include_router(opportunities_router, **protected)
app.include_router(experiments_router, **protected)
app.include_router(strategy_router, **protected)
app.include_router(health_scorecard_router, **protected)
app.include_router(segments_router, **protected)
app.include_router(journeys_router, **protected)
app.include_router(diagnostics_router, **protected)
app.include_router(ml_intelligence_router, **protected)
app.include_router(anomalies_router, **protected)
app.include_router(churn_router, **protected)


@app.get("/")
def home():
    return {
        "message": "Welcome to PulseOS",
        "status": "running",
    }


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "application": "PulseOS",
        "version": "0.1.0",
    }
