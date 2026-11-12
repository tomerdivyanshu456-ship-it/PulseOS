import asyncio
from io import BytesIO

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile

from app.api.routes.datasets import read_upload_limited
from app.security import credentials_are_valid, validate_production_config
from app.middleware import RequestSizeLimitMiddleware
from fastapi import FastAPI, Request
from app.main import app


def test_admin_credentials_are_compared_and_username_is_fixed():
    assert credentials_are_valid("admin", "correct-secret", "correct-secret")
    assert not credentials_are_valid("other", "correct-secret", "correct-secret")
    assert not credentials_are_valid("admin", "wrong-secret", "correct-secret")


def test_production_requires_long_password_and_explicit_https_origins(monkeypatch):
    monkeypatch.setenv("PULSEOS_ENV", "production")
    monkeypatch.setenv("PULSEOS_ADMIN_PASSWORD", "x" * 32)
    monkeypatch.setenv("PULSEOS_CORS_ORIGINS", "https://pulseos.example.com")
    validate_production_config()
    monkeypatch.setenv("PULSEOS_CORS_ORIGINS", "*")
    with pytest.raises(RuntimeError, match="exact HTTPS"):
        validate_production_config()
    monkeypatch.setenv("PULSEOS_CORS_ORIGINS", "https://pulseos.example.com/path")
    with pytest.raises(RuntimeError, match="exact HTTPS"):
        validate_production_config()


def test_production_rejects_short_admin_password(monkeypatch):
    monkeypatch.setenv("PULSEOS_ENV", "production")
    monkeypatch.setenv("PULSEOS_ADMIN_PASSWORD", "short")
    monkeypatch.setenv("PULSEOS_CORS_ORIGINS", "https://pulseos.example.com")
    with pytest.raises(RuntimeError, match="at least 32 characters"):
        validate_production_config()


def test_upload_reader_accepts_file_within_limit():
    upload = UploadFile(filename="small.csv", file=BytesIO(b"a,b\n1,2\n"))
    assert asyncio.run(read_upload_limited(upload, 20)) == b"a,b\n1,2\n"


def test_upload_reader_rejects_file_over_limit():
    upload = UploadFile(filename="large.csv", file=BytesIO(b"123456789"))
    with pytest.raises(HTTPException) as error:
        asyncio.run(read_upload_limited(upload, 8))
    assert error.value.status_code == 413


def test_workspace_api_requires_admin_auth_when_configured(monkeypatch):
    monkeypatch.setenv("PULSEOS_ENV", "development")
    monkeypatch.setenv("PULSEOS_ADMIN_PASSWORD", "local-test-password")
    client = TestClient(app)

    assert client.get("/api/datasets").status_code == 401
    assert client.get("/api/health").status_code == 200
    verified = client.get("/api/auth/verify", auth=("admin", "local-test-password"))
    assert verified.status_code == 200
    assert verified.json() == {"authenticated": True}


def test_request_size_middleware_rejects_oversized_body_before_route():
    test_app = FastAPI()
    test_app.add_middleware(RequestSizeLimitMiddleware, max_bytes=8)

    @test_app.post("/upload")
    async def upload(request: Request):
        return {"size": len(await request.body())}

    response = TestClient(test_app).post("/upload", content=b"123456789")
    assert response.status_code == 413
    assert "server limit" in response.json()["detail"]
