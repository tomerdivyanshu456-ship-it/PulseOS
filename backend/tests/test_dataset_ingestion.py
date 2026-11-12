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
