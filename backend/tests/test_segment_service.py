import pandas as pd
import pytest

from app.services import segment_service


@pytest.fixture
def sample_events():
    return pd.DataFrame([
        {"user_id": "u1", "event_name": "app_open", "timestamp": "2026-10-01", "platform": "ios", "revenue": 0},
        {"user_id": "u1", "event_name": "purchase", "timestamp": "2026-10-03", "platform": "ios", "revenue": 100},
        {"user_id": "u2", "event_name": "app_open", "timestamp": "2026-10-01", "platform": "android", "revenue": 0},
        {"user_id": "u2", "event_name": "app_open", "timestamp": "2026-10-04", "platform": "android", "revenue": 0},
        {"user_id": "u3", "event_name": "app_open", "timestamp": "2026-10-02", "platform": "ios", "revenue": 0},
    ])


def test_segment_comparison_assigns_each_user_once(monkeypatch, sample_events):
    monkeypatch.setattr(segment_service, "get_latest_dataset", lambda dataset_type: sample_events.copy())
    result = segment_service.calculate_segment_intelligence("platform")
    assert result["status"] == "ready"
    assert result["total_users"] == 3
    assert sum(row["users"] for row in result["segments"]) == 3
    segments = {row["segment"]: row for row in result["segments"]}
    assert segments["ios"]["users"] == 2
    assert segments["ios"]["purchasing_users"] == 1
    assert segments["android"]["repeat_users"] == 1
    assert segments["ios"]["purchase_revenue"] == 100.0


def test_unknown_dimension_is_rejected(monkeypatch, sample_events):
    monkeypatch.setattr(segment_service, "get_latest_dataset", lambda dataset_type: sample_events.copy())
    with pytest.raises(ValueError, match="unavailable"):
        segment_service.calculate_segment_intelligence("unknown_dimension")


def test_no_eligible_dimensions_returns_guidance(monkeypatch):
    events = pd.DataFrame([
        {"user_id": "u1", "event_name": "open", "timestamp": "2026-10-01"},
        {"user_id": "u2", "event_name": "open", "timestamp": "2026-10-02"},
    ])
    monkeypatch.setattr(segment_service, "get_latest_dataset", lambda dataset_type: events.copy())
    result = segment_service.calculate_segment_intelligence()
    assert result["status"] == "no_dimensions"
    assert result["segments"] == []