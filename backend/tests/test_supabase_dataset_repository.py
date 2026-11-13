import json
from uuid import uuid4

import httpx
import pytest

from app.services.supabase_dataset_repository import (
    DatasetRepositoryError,
    SupabaseDatasetRepository,
)


USER_ID = "6f8f8d2e-9f6c-4b63-8b9c-4dce1c1a7a11"
DATASET_ID = "a9f3e7c2-9c6a-4c2b-a3d1-1a7f4b9c2d33"


def make_repository(handler):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return SupabaseDatasetRepository(
        user_id=USER_ID,
        access_token="test-user-jwt",
        base_url="https://example.supabase.co",
        publishable_key="test-publishable-key",
        client=client,
    )


def test_upload_uses_caller_identity_and_private_storage_path():
    seen = []

    def handler(request):
        seen.append(request)
        if request.url.path.startswith("/storage/"):
            return httpx.Response(200, json={"Key": "stored"})
        return httpx.Response(201, json=[{"id": DATASET_ID, "owner_id": USER_ID}])

    repository = make_repository(handler)
    result = repository.upload(
        dataset_id=DATASET_ID,
        dataset_type="events",
        filename="events.csv",
        contents=b"user_id,event_name,timestamp\nu1,view,2026-11-01",
        row_count=1,
        content_type="text/csv",
    )

    assert result["owner_id"] == USER_ID
    assert seen[0].url.path.endswith(f"/{USER_ID}/{DATASET_ID}/events.csv")
    assert seen[0].headers["authorization"] == "Bearer test-user-jwt"
    metadata = json.loads(seen[1].content)
    assert metadata["owner_id"] == USER_ID
    assert metadata["object_path"] == f"{USER_ID}/{DATASET_ID}/events.csv"


def test_upload_rejects_invalid_dataset_type_before_network_call():
    repository = make_repository(lambda request: pytest.fail("network must not be called"))
    with pytest.raises(ValueError, match="Dataset type"):
        repository.upload(
            dataset_id=DATASET_ID,
            dataset_type="unknown",
            filename="x.csv",
            contents=b"x",
            row_count=0,
            content_type="text/csv",
        )


def test_download_rejects_another_users_object_path():
    repository = make_repository(lambda request: pytest.fail("network must not be called"))
    with pytest.raises(DatasetRepositoryError, match="Dataset not found"):
        repository.download(f"{uuid4()}/{DATASET_ID}/events.csv")


def test_metadata_failure_compensates_by_deleting_uploaded_object():
    requests = []

    def handler(request):
        requests.append(request)
        if request.method == "POST" and request.url.path.startswith("/storage/"):
            return httpx.Response(200, json={"Key": "stored"})
        if request.url.path.endswith("/pulseos_datasets"):
            return httpx.Response(500, json={"message": "database unavailable"})
        return httpx.Response(200, json={"message": "deleted"})

    repository = make_repository(handler)
    with pytest.raises(DatasetRepositoryError, match="HTTP 500"):
        repository.upload(
            dataset_id=DATASET_ID,
            dataset_type="events",
            filename="events.csv",
            contents=b"x",
            row_count=1,
            content_type="text/csv",
        )

    assert [request.method for request in requests] == ["POST", "POST", "DELETE"]
    assert requests[2].url.path.endswith("/pulseos-private")
    assert json.loads(requests[2].content)["prefixes"] == [
        f"{USER_ID}/{DATASET_ID}/events.csv"
    ]


def test_dataset_metadata_request_uses_verified_bearer_token():
    def handler(request):
        assert request.headers["authorization"] == "Bearer test-user-jwt"
        assert request.headers["apikey"] == "test-publishable-key"
        return httpx.Response(200, json=[])

    repository = make_repository(handler)
    assert repository.list_datasets() == []
