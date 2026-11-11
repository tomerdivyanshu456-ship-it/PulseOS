from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="PulseOS API",
    description="Product Intelligence Platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
