from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.datasets import router as datasets_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.voice_of_customer import router as voice_of_customer_router
from app.api.routes.analyst import router as analyst_router
from app.api.routes.opportunities import router as opportunities_router
from app.api.routes.experiments import router as experiments_router
from app.api.routes.strategy import router as strategy_router
from app.api.routes.health_scorecard import router as health_scorecard_router

app = FastAPI(
    title="PulseOS API",
    description="Product Intelligence Platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    # Vite may select a different port when the default ports are busy.
    # Allow local development origins without hardcoding each Vite port.
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):\d+",
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(datasets_router)
app.include_router(analytics_router)
app.include_router(voice_of_customer_router)
app.include_router(analyst_router)
app.include_router(opportunities_router)
app.include_router(experiments_router)
app.include_router(strategy_router)
app.include_router(health_scorecard_router)


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
