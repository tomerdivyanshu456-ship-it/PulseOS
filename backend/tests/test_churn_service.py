import pandas as pd
import pytest

from app.services import churn_service


def _events(days=14, users=60):
    rows = []
    for user in range(users):
        churns = user < users // 3
        for day in range(days):
            if day >= 7 and churns:
                continue
            count = 1 + (user % 3)
            for event_index in range(count):
                rows.append({
                    "user_id": f"u{user:03d}",
                    "event_name": "purchase" if event_index == count - 1 and user % 4 == 0 else "product_viewed",
                    "timestamp": (pd.Timestamp("2026-10-01") + pd.Timedelta(days=day, minutes=user + event_index)).isoformat(),
                    "session_id": f"s{user}-{day}",
                    "revenue": 100 if event_index == count - 1 and user % 4 == 0 else 0,
                })
    return pd.DataFrame(rows)


def test_predict_customer_churn_returns_holdout_metrics(monkeypatch):
    monkeypatch.setattr(churn_service, "get_dataset_by_id", lambda _dataset_id, _dataset_type: _events())
    result = churn_service.predict_customer_churn("dataset-1")

    assert result["status"] == "ready"
    assert result["cohort_size"] == 60
    assert result["churned_users"] == 20
    assert result["retained_users"] == 40
    assert result["holdout_users"] == 15
    assert {item["model"] for item in result["model_comparison"]} == {"Majority-class baseline", "Logistic Regression", "Random Forest"}
    assert all(0 <= item["metrics"]["roc_auc"] <= 1 for item in result["model_comparison"])
    assert all("predicted_churn_probability" in item for item in result["holdout_predictions"])
    assert result["confusion_matrix"]["true_negative"] + result["confusion_matrix"]["false_positive"] + result["confusion_matrix"]["false_negative"] + result["confusion_matrix"]["true_positive"] == result["holdout_users"]
    for model in result["model_comparison"][1:]:
        assert model["cross_validation"]["folds"] == 5
        assert 0 <= model["cross_validation"]["roc_auc_mean"] <= 1


def test_predict_customer_churn_requires_fourteen_days(monkeypatch):
    monkeypatch.setattr(churn_service, "get_dataset_by_id", lambda _dataset_id, _dataset_type: _events(days=12))
    with pytest.raises(ValueError, match="At least 14 calendar days"):
        churn_service.predict_customer_churn("dataset-1")


def test_predict_customer_churn_requires_both_classes(monkeypatch):
    events = _events()
    # Make every eligible user active during the outcome window.
    extra = events[events["timestamp"] >= "2026-10-08"].copy()
    extra["timestamp"] = pd.to_datetime(extra["timestamp"]) + pd.Timedelta(days=0)
    # Remove the churn pattern by adding outcome events for the first 20 users.
    additions = []
    for user in range(20):
        additions.append({
            "user_id": f"u{user:03d}", "event_name": "product_viewed",
            "timestamp": "2026-10-14T12:00:00", "session_id": f"last-{user}", "revenue": 0,
        })
    events = pd.concat([events, pd.DataFrame(additions)], ignore_index=True)
    monkeypatch.setattr(churn_service, "get_dataset_by_id", lambda _dataset_id, _dataset_type: events)
    with pytest.raises(ValueError, match="too few examples in one class"):
        churn_service.predict_customer_churn()


def test_build_churn_cohort_uses_only_observation_features():
    cohort, start, end, latest = churn_service._build_churn_cohort(_events())
    assert (end - start).days == 6
    assert (latest - end).days == 7
    assert "churned" in cohort.columns
    assert cohort.loc[cohort["user_id"] == "u000", "churned"].iloc[0] == 1
    assert cohort.loc[cohort["user_id"] == "u059", "churned"].iloc[0] == 0
