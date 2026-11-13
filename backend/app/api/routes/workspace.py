import logging
import os
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.security import require_supabase_user

router = APIRouter(prefix="/api/workspace", tags=["Workspace"])
logger = logging.getLogger(__name__)


def _supabase_config():
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
    if not url or not key:
        raise HTTPException(
            status_code=503,
            detail="Supabase workspace access is not configured on the API.",
        )
    return url, key


@router.get("")
def get_workspace(claims: dict = Depends(require_supabase_user)):
    """Read only the authenticated user's workspace through Supabase RLS."""
    try:
        user_id = str(UUID(claims["sub"]))
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid authenticated user identifier.") from exc

    url, key = _supabase_config()
    try:
        response = httpx.get(
            f"{url}/rest/v1/pulseos_workspaces",
            params={
                "select": "user_id,display_name,created_at,updated_at",
                "user_id": f"eq.{user_id}",
                "limit": "1",
            },
            headers={
                "apikey": key,
                "Authorization": f"Bearer {claims.get('_access_token', '')}",
            },
            timeout=8.0,
        )
    except httpx.RequestError as exc:
        logger.exception("Supabase workspace request failed before receiving a response (%s).", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Supabase workspace service is temporarily unavailable.") from exc

    if response.status_code in (401, 403):
        raise HTTPException(status_code=401, detail="Supabase rejected the workspace access token.")
    if response.status_code >= 500:
        logger.error(
            "Supabase workspace REST returned HTTP %s; response body: %s",
            response.status_code,
            response.text[:1000],
        )
        raise HTTPException(status_code=503, detail="Supabase workspace service is temporarily unavailable.")
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="Could not retrieve the private workspace.")

    try:
        rows = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Supabase returned an invalid workspace response.") from exc
    if not rows:
        raise HTTPException(status_code=404, detail="Workspace record was not found for this account.")
    return {"workspace": rows[0]}
