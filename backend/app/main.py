
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.datasets import router as datasets_router
from app.api.routes.analytics import router as analytics_router

app = FastAPI(
    title="PulseOS API",
    description="Product Intelligence Platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
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
