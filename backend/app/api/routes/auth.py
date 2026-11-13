from fastapi import APIRouter, Depends
from app.security import auth_enabled, require_auth, require_supabase_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.get("/config")
def auth_config():
    return {"auth_required": auth_enabled(), "google_auth_available": True}


@router.get("/verify")
def verify_auth(_authenticated: bool = Depends(require_auth)):
    return {"authenticated": True}


@router.get("/me")
def current_user(claims: dict = Depends(require_supabase_user)):
    # Only claims from the cryptographically verified bearer token are returned.
    return {
        "authenticated": True,
        "user_id": claims["sub"],
        "email": claims.get("email"),
        "role": claims.get("role"),
    }
