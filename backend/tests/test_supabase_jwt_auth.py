from fastapi.testclient import TestClient

from app.main import app


def test_supabase_identity_endpoint_requires_bearer_token():
    response = TestClient(app).get("/api/auth/me")
    assert response.status_code == 401


def test_supabase_identity_endpoint_uses_verified_subject(monkeypatch):
    import app.security as security

    monkeypatch.setattr(
        security,
        "verify_supabase_access_token",
        lambda token: {
            "sub": "user-123",
            "email": "person@example.com",
            "role": "authenticated",
        } if token == "valid-test-token" else {},
    )

    response = TestClient(app).get(
        "/api/auth/me",
        headers={"Authorization": "Bearer valid-test-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "authenticated": True,
        "user_id": "user-123",
        "email": "person@example.com",
        "role": "authenticated",
    }
