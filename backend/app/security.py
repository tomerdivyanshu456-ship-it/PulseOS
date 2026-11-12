import os
import secrets
from urllib.parse import urlsplit

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

basic_auth = HTTPBasic(auto_error=False)

def is_production():
    return os.getenv("PULSEOS_ENV", "development").strip().lower() == "production"

def configured_admin_password():
    return os.getenv("PULSEOS_ADMIN_PASSWORD", "")

def auth_enabled():
    return bool(configured_admin_password())

def credentials_are_valid(username, password, expected_password):
    username_ok = secrets.compare_digest(str(username).encode("utf-8"), b"admin")
    password_ok = secrets.compare_digest(str(password).encode("utf-8"), str(expected_password).encode("utf-8"))
    return username_ok and password_ok

def validate_production_config():
    if not is_production():
        return
    password = configured_admin_password()
    if len(password) < 32:
        raise RuntimeError("Production requires PULSEOS_ADMIN_PASSWORD to contain at least 32 characters.")
    origins = [item.strip().rstrip("/") for item in os.getenv("PULSEOS_CORS_ORIGINS", "").split(",") if item.strip()]
    if not origins:
        raise RuntimeError("Production requires PULSEOS_CORS_ORIGINS with exact HTTPS frontend origins.")
    for origin in origins:
        parsed = urlsplit(origin)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
            or "*" in origin
        ):
            raise RuntimeError("Production CORS origins must be exact HTTPS origins without paths or wildcards.")

def require_auth(credentials: HTTPBasicCredentials | None = Depends(basic_auth)):
    expected = configured_admin_password()
    if not expected and not is_production():
        return True
    if credentials is None or not credentials_are_valid(credentials.username, credentials.password, expected):
        raise HTTPException(status_code=401, detail="Authentication required. Sign in to PulseOS.", headers={"WWW-Authenticate": 'Basic realm="PulseOS"'})
    return True
