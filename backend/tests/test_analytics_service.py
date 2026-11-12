import pandas as pd

from app.services import analytics_service


def test_repeat_engagement_metrics(monkeypatch):
    events = pd.DataFrame(
        [
            {"user_id": "u1", "event_name": "product_viewed", "timestamp": "2026-11-01 09:00:00"},
            {"user_id": "u1", "event_name": "add_to_cart", "timestamp": "2026-11-01 09:05:00"},
            {"user_id": "u2", "event_name": "product_viewed", "timestamp": "2026-11-01 10:00:00"},
        ]
    )
    monkeypatch.setattr(
        analytics_service,
        "get_latest_dataset",
        lambda dataset_type: events.copy(),
    )

    result = analytics_service.calculate_product_analytics()

    assert result["metrics"]["total_users"] == 2
    assert result["metrics"]["repeat_users"] == 0
    assert result["metrics"]["repeat_user_rate"] == 0
    assert result["metrics"]["average_events_per_user"] == 1.5


def test_weekly_retention_uses_only_fully_elapsed_weeks(monkeypatch):
    events = pd.DataFrame(
        [
            {"user_id": "u1", "event_name": "app_open", "timestamp": "2026-10-26 09:00:00"},
            {"user_id": "u2", "event_name": "app_open", "timestamp": "2026-10-27 09:00:00"},
            {"user_id": "u1", "event_name": "app_open", "timestamp": "2026-11-03 09:00:00"},
            {"user_id": "u3", "event_name": "app_open", "timestamp": "2026-11-03 10:00:00"},
            {"user_id": "u1", "event_name": "app_open", "timestamp": "2026-11-08 09:00:00"},
        ]
    )
    monkeypatch.setattr(
        analytics_service,
        "get_latest_dataset",
        lambda dataset_type: events.copy(),
    )

    result = analytics_service.calculate_product_analytics()
    cohorts = {item["cohort"]: item for item in result["retention_cohorts"]}

    first_cohort = cohorts["2026-10-26"]
    assert first_cohort["cohort_size"] == 2
    assert [cell["week"] for cell in first_cohort["weeks"]] == [0, 1]
    assert first_cohort["weeks"][1]["active_users"] == 1
    assert first_cohort["weeks"][1]["retention_rate"] == 50.0

    second_cohort = cohorts["2026-11-02"]
    assert second_cohort["cohort_size"] == 1
    assert [cell["week"] for cell in second_cohort["weeks"]] == [0]
