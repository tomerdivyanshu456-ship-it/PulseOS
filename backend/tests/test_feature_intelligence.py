import pandas as pd

from app.services.analytics_service import calculate_feature_intelligence


def test_feature_intelligence_calculates_adoption_and_repeat_usage():
    events = pd.DataFrame([
        {"user_id": "u1", "event_name": "product_viewed"},
        {"user_id": "u1", "event_name": "add_to_cart"},
        {"user_id": "u1", "event_name": "add_to_cart"},
        {"user_id": "u2", "event_name": "product_viewed"},
        {"user_id": "u3", "event_name": "purchase"},
        {"user_id": "u3", "event_name": "payment_succeeded"},
    ])

    result = calculate_feature_intelligence(events, total_users=4)
    features = {item["feature"]: item for item in result["features"]}

    assert result["mapped_feature_count"] == 3
    assert features["Product Discovery"]["active_users"] == 2
    assert features["Product Discovery"]["adoption_rate"] == 50.0
    assert features["Cart & Wishlist"]["repeat_users"] == 1
    assert features["Cart & Wishlist"]["repeat_usage_rate"] == 100.0
    assert features["Checkout & Payments"]["active_users"] == 1


def test_feature_intelligence_returns_empty_list_for_unmapped_events():
    events = pd.DataFrame([
        {"user_id": "u1", "event_name": "custom_action"},
        {"user_id": "u2", "event_name": "another_custom_action"},
    ])

    result = calculate_feature_intelligence(events, total_users=2)

    assert result["features"] == []
    assert result["mapped_feature_count"] == 0
    assert "starter taxonomy" in result["mapping_note"]
