from fastapi import APIRouter, Depends
from app.security import auth_enabled, require_auth

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.get("/config")
def auth_config():
    return {"auth_required": auth_enabled()}

@router.get("/verify")
def verify_auth(_authenticated: bool = Depends(require_auth)):
    return {"authenticated": True}
