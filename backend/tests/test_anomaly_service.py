import pandas as pd
import pytest

from app.services import anomaly_service


def test_detect_product_anomalies_returns_daily_metrics_and_flags(monkeypatch):
    rows = []
    for day in range(12):
        count = 10 if day != 8 else 120
        for user in range(count):
            rows.append({
                "user_id": f"{day}-{user}",
                "event_name": "purchase" if user % 5 == 0 else "product_viewed",
                "timestamp": f"2026-10-{day + 1:02d}T12:00:00",
                "revenue": 100 if user % 5 == 0 else 0,
            })
    monkeypatch.setattr(anomaly_service, "get_latest_dataset", lambda _: pd.DataFrame(rows))

    result = anomaly_service.detect_product_anomalies()

    assert result["status"] == "ready"
    assert result["days_analyzed"] == 12
    assert result["daily_metrics"]
    assert result["anomaly_count"] > 0
    assert all(item["date"] and item["metric"] for item in result["anomalies"])


def test_detect_product_anomalies_requires_seven_days(monkeypatch):
    rows = [
        {"user_id": "u1", "event_name": "view", "timestamp": f"2026-10-0{day}T12:00:00"}
        for day in range(1, 6)
    ]
    monkeypatch.setattr(anomaly_service, "get_latest_dataset", lambda _: pd.DataFrame(rows))

    with pytest.raises(ValueError, match="At least 7 distinct days"):
        anomaly_service.detect_product_anomalies()


def test_detect_product_anomalies_rejects_invalid_schema(monkeypatch):
    monkeypatch.setattr(anomaly_service, "get_latest_dataset", lambda _: pd.DataFrame({"user_id": ["u1"]}))
    with pytest.raises(ValueError, match="must contain user_id"):
        anomaly_service.detect_product_anomalies()
