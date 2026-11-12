import pandas as pd
import pytest

from app.services import journey_service


@pytest.fixture
def journey_events():
    return pd.DataFrame([
        {"user_id": "u1", "event_name": "product_viewed", "timestamp": "2026-11-01 09:00", "session_id": "s1", "platform": "ios"},
        {"user_id": "u1", "event_name": "add_to_cart", "timestamp": "2026-11-01 09:02", "session_id": "s1", "platform": "ios"},
        {"user_id": "u1", "event_name": "purchase", "timestamp": "2026-11-01 09:05", "session_id": "s1", "platform": "ios"},
        {"user_id": "u2", "event_name": "product_viewed", "timestamp": "2026-11-01 10:00", "session_id": "s2", "platform": "android"},
        {"user_id": "u2", "event_name": "add_to_cart", "timestamp": "2026-11-01 10:03", "session_id": "s2", "platform": "android"},
        {"user_id": "u3", "event_name": "product_viewed", "timestamp": "2026-11-01 11:00", "session_id": "s3", "platform": "ios"},
        {"user_id": "u3", "event_name": "search", "timestamp": "2026-11-01 11:01", "session_id": "s3", "platform": "ios"},
    ])


def test_ordered_funnel_counts_dropoff_and_conversion(monkeypatch, journey_events):
    monkeypatch.setattr(journey_service, "get_latest_dataset", lambda dataset_type: journey_events.copy())
    result = journey_service.calculate_journey_intelligence(
        ["product_viewed", "add_to_cart", "purchase"]
    )
    assert result["unit"] == "sessions"
    assert result["total_units"] == 3
    assert [row["units_reached"] for row in result["funnel"]] == [3, 2, 1]
    assert [row["drop_off_units"] for row in result["funnel"]] == [0, 1, 1]
    assert result["funnel"][1]["conversion_from_previous"] == 66.7
    assert result["funnel"][2]["conversion_from_entry"] == 33.3


def test_funnel_requires_ordered_events_in_same_session(monkeypatch, journey_events):
    events = journey_events.copy()
    events.loc[len(events)] = {
        "user_id": "u4", "event_name": "purchase",
        "timestamp": "2026-11-01 12:00", "session_id": "s4", "platform": "ios",
    }
    monkeypatch.setattr(journey_service, "get_latest_dataset", lambda dataset_type: events.copy())
    result = journey_service.calculate_journey_intelligence(
        ["product_viewed", "purchase"]
    )
    assert [row["units_reached"] for row in result["funnel"]] == [3, 1]


def test_segment_funnel_uses_user_attribute_assignment(monkeypatch, journey_events):
    monkeypatch.setattr(journey_service, "get_latest_dataset", lambda dataset_type: journey_events.copy())
    result = journey_service.calculate_journey_intelligence(
        ["product_viewed", "purchase"], "platform"
    )
    segments = {item["segment"]: item for item in result["segment_funnels"]}
    assert segments["ios"]["units"] == 2
    assert [row["units_reached"] for row in segments["ios"]["funnel"]] == [2, 1]
    assert segments["android"]["funnel"][1]["units_reached"] == 0


def test_invalid_funnel_steps_are_rejected(monkeypatch, journey_events):
    monkeypatch.setattr(journey_service, "get_latest_dataset", lambda dataset_type: journey_events.copy())
    with pytest.raises(ValueError, match="between 2 and 6"):
        journey_service.calculate_journey_intelligence(["product_viewed"])


def test_funnel_without_session_id_falls_back_to_users(monkeypatch):
    events = pd.DataFrame([
        {"user_id": "u1", "event_name": "view", "timestamp": "2026-11-01"},
        {"user_id": "u1", "event_name": "buy", "timestamp": "2026-11-02"},
        {"user_id": "u2", "event_name": "buy", "timestamp": "2026-11-01"},
    ])
    monkeypatch.setattr(journey_service, "get_latest_dataset", lambda dataset_type: events.copy())
    result = journey_service.calculate_journey_intelligence(["view", "buy"])
    assert result["unit"] == "users"
    assert [row["units_reached"] for row in result["funnel"]] == [1, 1]
