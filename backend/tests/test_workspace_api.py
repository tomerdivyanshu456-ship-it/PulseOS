import httpx
import pytest
from fastapi import HTTPException

from app.api.routes import workspace


def test_workspace_uses_verified_user_token_and_rls(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test")
    captured = {}

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return [{
                "user_id": "11111111-1111-4111-8111-111111111111",
                "display_name": "Test User",
                "created_at": "2026-11-13T00:00:00Z",
                "updated_at": "2026-11-13T00:00:00Z",
            }]

    def fake_get(url, *, params, headers, timeout):
        captured.update(url=url, params=params, headers=headers, timeout=timeout)
        return Response()

    monkeypatch.setattr(workspace.httpx, "get", fake_get)
    result = workspace.get_workspace({
        "sub": "11111111-1111-4111-8111-111111111111",
        "_access_token": "verified-user-jwt",
    })

    assert result["workspace"]["display_name"] == "Test User"
    assert captured["headers"]["Authorization"] == "Bearer verified-user-jwt"
    assert captured["headers"]["apikey"] == "sb_publishable_test"
    assert captured["params"]["user_id"] == "eq.11111111-1111-4111-8111-111111111111"


def test_workspace_rejects_missing_supabase_config(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    with pytest.raises(HTTPException) as error:
        workspace.get_workspace({
            "sub": "11111111-1111-4111-8111-111111111111",
            "_access_token": "verified-user-jwt",
        })
    assert error.value.status_code == 503


def test_workspace_rejects_non_uuid_subject(monkeypatch):
    with pytest.raises(HTTPException) as error:
        workspace.get_workspace({"sub": "not-a-uuid", "_access_token": "token"})
    assert error.value.status_code == 401
