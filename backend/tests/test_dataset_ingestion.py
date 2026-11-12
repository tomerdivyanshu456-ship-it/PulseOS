import pandas as pd
import pytest

from app.services import dataset_service


def test_column_mapping_suggests_common_alternative_headers():
    mapping = dataset_service.suggest_column_mapping(
        ["customer_code", "action", "event_time", "amount"],
        "events",
    )
    assert mapping["user_id"]["column"] == "customer_code"
    assert mapping["event_name"]["column"] == "action"
    assert mapping["timestamp"]["column"] == "event_time"


def test_inspection_detects_event_dataset():
    contents = b"customer_code,action,event_time\nc1,view,2026-11-01 10:00:00\n"
    result = dataset_service.inspect_tabular(contents, "events.csv")
    assert result["suggested_type"] == "events"
    assert result["row_count"] == 1
    assert result["mappings"]["events"]["user_id"]["column"] == "customer_code"


def test_save_dataset_standardises_columns_and_preserves_other_fields(monkeypatch, tmp_path):
    monkeypatch.setattr(dataset_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(dataset_service, "UPLOAD_DIR", tmp_path / "raw")
    monkeypatch.setattr(dataset_service, "DOCUMENT_DIR", tmp_path / "documents")
    monkeypatch.setattr(dataset_service, "DB_PATH", tmp_path / "pulseos.db")
    dataset_service.UPLOAD_DIR.mkdir()
    dataset_service.DOCUMENT_DIR.mkdir()
    contents = (
        b"customer_code,action,event_time,device_type\n"
        b"c1,product_viewed,2026-11-01 10:00:00,mobile\n"
    )
    result = dataset_service.save_dataset(
        contents,
        "customer-events.csv",
        "events",
        {"user_id": "customer_code", "event_name": "action", "timestamp": "event_time"},
    )
    stored = pd.read_csv(dataset_service.UPLOAD_DIR / f'{result["dataset_id"]}.csv')
    assert list(stored.columns) == ["user_id", "event_name", "timestamp", "device_type"]
    assert stored.loc[0, "user_id"] == "c1"
    assert result["rows"] == 1


def test_save_dataset_rejects_duplicate_source_mapping():
    contents = b"customer_code,action,event_time\nc1,view,2026-11-01\n"
    with pytest.raises(ValueError, match="different source column"):
        dataset_service.save_dataset(
            contents,
            "events.csv",
            "events",
            {"user_id": "customer_code", "event_name": "customer_code", "timestamp": "event_time"},
        )


def test_document_upload_rejects_unsupported_extension():
    with pytest.raises(ValueError, match="PDF and DOCX"):
        dataset_service.save_document(b"not a document", "notes.txt")

def test_delete_dataset_removes_only_selected_tabular_file(monkeypatch, tmp_path):
    monkeypatch.setattr(dataset_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(dataset_service, "UPLOAD_DIR", tmp_path / "raw")
    monkeypatch.setattr(dataset_service, "DOCUMENT_DIR", tmp_path / "documents")
    monkeypatch.setattr(dataset_service, "DB_PATH", tmp_path / "pulseos.db")
    dataset_service.UPLOAD_DIR.mkdir()
    dataset_service.DOCUMENT_DIR.mkdir()
    first = dataset_service.save_dataset(
        b"user_id,event_name,timestamp\nu1,view,2026-11-01\n",
        "first.csv", "events",
    )
    second = dataset_service.save_dataset(
        b"user_id,event_name,timestamp\nu2,view,2026-11-02\n",
        "second.csv", "events",
    )
    assert dataset_service.delete_dataset(first["dataset_id"]) is True
    assert not (dataset_service.UPLOAD_DIR / (first["dataset_id"] + ".csv")).exists()
    assert (dataset_service.UPLOAD_DIR / (second["dataset_id"] + ".csv")).exists()
    assert dataset_service.delete_dataset(first["dataset_id"]) is False


def test_delete_dataset_removes_document_text(monkeypatch, tmp_path):
    monkeypatch.setattr(dataset_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(dataset_service, "UPLOAD_DIR", tmp_path / "raw")
    monkeypatch.setattr(dataset_service, "DOCUMENT_DIR", tmp_path / "documents")
    monkeypatch.setattr(dataset_service, "DB_PATH", tmp_path / "pulseos.db")
    dataset_service.UPLOAD_DIR.mkdir()
    dataset_service.DOCUMENT_DIR.mkdir()
    dataset_id = "document-test-id"
    stored = dataset_service.DOCUMENT_DIR / (dataset_id + ".txt")
    stored.write_text("test document", encoding="utf-8")
    with dataset_service.get_connection() as connection:
        connection.execute(
            "INSERT INTO datasets VALUES (?, 'documents', 'brief.docx', ?, 2, '2026-11-01T00:00:00Z')",
            (dataset_id, stored.name),
        )
    assert dataset_service.delete_dataset(dataset_id) is True
    assert not stored.exists()


def test_active_dataset_selection_is_persistent_and_clears_on_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(dataset_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(dataset_service, "UPLOAD_DIR", tmp_path / "raw")
    monkeypatch.setattr(dataset_service, "DOCUMENT_DIR", tmp_path / "documents")
    monkeypatch.setattr(dataset_service, "DB_PATH", tmp_path / "pulseos.db")
    dataset_service.UPLOAD_DIR.mkdir()
    dataset_service.DOCUMENT_DIR.mkdir()
    first = dataset_service.save_dataset(
        b"user_id,event_name,timestamp\nu1,view,2026-11-01\n",
        "first.csv", "events",
    )
    second = dataset_service.save_dataset(
        b"user_id,event_name,timestamp\nu2,view,2026-11-02\n",
        "second.csv", "events",
    )
    dataset_service.set_active_dataset("events", first["dataset_id"])
    assert dataset_service.get_active_datasets()["events"]["id"] == first["dataset_id"]
    dataset_service.delete_dataset(first["dataset_id"])
    assert dataset_service.get_active_datasets()["events"] is None
    with pytest.raises(ValueError, match="No active events dataset"):
        dataset_service.get_dataset_record("events")
