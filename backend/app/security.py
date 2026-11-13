import os
import secrets
from functools import lru_cache
from urllib.parse import urlsplit

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials, HTTPBearer
from jwt import PyJWKClient, PyJWTError

basic_auth = HTTPBasic(auto_error=False)
bearer_auth = HTTPBearer(auto_error=False)
JWT_ALGORITHMS = ["ES256", "RS256", "EdDSA"]


def is_production():
    return os.getenv("PULSEOS_ENV", "development").strip().lower() == "production"


def configured_admin_password():
    return os.getenv("PULSEOS_ADMIN_PASSWORD", "")


def auth_enabled():
    return bool(configured_admin_password())


def supabase_url():
    return os.getenv("SUPABASE_URL", "").strip().rstrip("/")


def supabase_issuer():
    configured = os.getenv("SUPABASE_JWT_ISSUER", "").strip()
    return configured or (f"{supabase_url()}/auth/v1" if supabase_url() else "")


@lru_cache(maxsize=4)
def _jwks_client(jwks_url: str):
    return PyJWKClient(jwks_url, cache_keys=True, lifespan=300)


def verify_supabase_access_token(token: str) -> dict:
    """Verify an asymmetric Supabase Auth access token and return trusted claims."""
    url = supabase_url()
    issuer = supabase_issuer()
    if not url or not issuer:
        raise HTTPException(status_code=503, detail="Supabase authentication is not configured.")
    try:
        signing_key = _jwks_client(f"{url}/auth/v1/.well-known/jwks.json").get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=JWT_ALGORITHMS,
            audience="authenticated",
            issuer=issuer,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
    except PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired Supabase access token.") from exc
    except Exception as exc:
        # Network/JWKS lookup failures are service errors, not successful authentication.
        raise HTTPException(status_code=503, detail="Could not validate Supabase signing keys.") from exc

    if claims.get("role") != "authenticated" or not isinstance(claims.get("sub"), str):
        raise HTTPException(status_code=401, detail="Token does not represent an authenticated user.")
    return claims


def require_supabase_user(credentials=Depends(bearer_auth)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="A Supabase bearer token is required.", headers={"WWW-Authenticate": "Bearer"})
    return verify_supabase_access_token(credentials.credentials)


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
