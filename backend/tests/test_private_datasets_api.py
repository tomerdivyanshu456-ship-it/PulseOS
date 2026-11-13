from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import private_datasets
from app.security import require_supabase_user


CLAIMS = {
    "sub": "6f8f8d2e-9f6c-4b63-8b9c-4dce1c1a7a11",
    "_access_token": "verified-user-jwt",
}


class FakeRepository:
    def __init__(self):
        self.closed = False
        self.upload_args = None

    def close(self):
        self.closed = True

    def list_datasets(self):
        return [{"id": "dataset-1", "dataset_type": "events"}]

    def get_active_datasets(self):
        return {"events": None, "reviews": None, "documents": None}

    def get_dataset(self, dataset_id):
        return {
            "id": dataset_id,
            "dataset_type": "documents",
            "original_filename": "research.docx",
            "row_count": 3,
            "object_path": f"{CLAIMS['sub']}/{dataset_id}/research.docx",
        }

    def download(self, object_path):
        return b"Extracted document text for preview."

    def upload(self, **kwargs):
        self.upload_args = kwargs
        return {
            "id": kwargs["dataset_id"],
            "dataset_type": kwargs["dataset_type"],
            "original_filename": kwargs["filename"],
            "row_count": kwargs["row_count"],
            "uploaded_at": "2026-11-13T00:00:00Z",
        }


def make_client(monkeypatch, authenticated=True):
    app = FastAPI()
    app.include_router(private_datasets.router)
    if authenticated:
        app.dependency_overrides[require_supabase_user] = lambda: CLAIMS
    return TestClient(app)


def test_private_dataset_routes_require_supabase_bearer_auth():
    client = make_client(None, authenticated=False)
    response = client.get("/api/workspace/datasets")
    assert response.status_code == 401


def test_list_datasets_uses_authenticated_repository(monkeypatch):
    repository = FakeRepository()
    monkeypatch.setattr(private_datasets, "_repository", lambda claims: repository)
    client = make_client(monkeypatch)

    response = client.get("/api/workspace/datasets")

    assert response.status_code == 200
    assert response.json()["datasets"] == [{"id": "dataset-1", "dataset_type": "events"}]
    assert repository.closed


def test_upload_normalizes_and_persists_csv_under_verified_user(monkeypatch):
    repository = FakeRepository()
    monkeypatch.setattr(private_datasets, "_repository", lambda claims: repository)
    client = make_client(monkeypatch)
    csv = b"customer_id,action,event_time\nu-1,view,2026-11-01T10:00:00Z\n"

    response = client.post(
        "/api/workspace/datasets/upload/events",
        files={"file": ("events.csv", csv, "text/csv")},
        data={"mapping": '{"user_id":"customer_id","event_name":"action","timestamp":"event_time"}'},
    )

    assert response.status_code == 200, response.text
    assert repository.upload_args["dataset_type"] == "events"
    assert repository.upload_args["row_count"] == 1
    assert repository.upload_args["content_type"] == "text/csv"
    assert b"user_id,event_name,timestamp" in repository.upload_args["contents"]
    assert repository.closed


def test_invalid_dataset_mapping_does_not_upload(monkeypatch):
    repository = FakeRepository()
    monkeypatch.setattr(private_datasets, "_repository", lambda claims: repository)
    client = make_client(monkeypatch)

    response = client.post(
        "/api/workspace/datasets/upload/events",
        files={"file": ("events.csv", b"wrong,columns\na,b\n", "text/csv")},
    )

    assert response.status_code == 422
    assert repository.upload_args is None
    assert repository.closed


def test_active_dataset_listing_is_scoped_through_repository(monkeypatch):
    repository = FakeRepository()
    monkeypatch.setattr(private_datasets, "_repository", lambda claims: repository)
    client = make_client(monkeypatch)

    response = client.get("/api/workspace/datasets/active")

    assert response.status_code == 200
    assert response.json()["active_datasets"]["events"] is None
    assert repository.closed



def test_upload_docx_extracts_text_and_stores_it_privately(monkeypatch):
    from io import BytesIO
    from docx import Document

    document = Document()
    document.add_paragraph("Private product research")
    document.add_paragraph("Customer interview findings")
    buffer = BytesIO()
    document.save(buffer)

    repository = FakeRepository()
    monkeypatch.setattr(private_datasets, "_repository", lambda claims: repository)
    client = make_client(monkeypatch)

    response = client.post(
        "/api/workspace/datasets/upload-document",
        files={"file": ("research.docx", buffer.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["dataset_type"] == "documents"
    assert response.json()["data"]["rows"] > 0
    assert repository.upload_args["dataset_type"] == "documents"
    assert repository.upload_args["content_type"].startswith("text/plain")
    assert b"Private product research" in repository.upload_args["contents"]
    assert repository.closed


def test_document_preview_returns_extracted_text(monkeypatch):
    repository = FakeRepository()
    monkeypatch.setattr(private_datasets, "_repository", lambda claims: repository)
    client = make_client(monkeypatch)

    response = client.get("/api/workspace/datasets/document-1/preview")

    assert response.status_code == 200
    assert response.json()["dataset_type"] == "documents"
    assert "Extracted document text" in response.json()["extracted_text"]
    assert repository.closed
