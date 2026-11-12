import pytest

from app.services import experiment_service


@pytest.fixture
def isolated_database(tmp_path, monkeypatch):
    database = tmp_path / "pulseos-test.db"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr("app.services.dataset_service.DB_PATH", database)
    monkeypatch.setattr("app.services.dataset_service.DATA_DIR", data_dir)
    return database


def test_sample_size_estimates_per_arm_and_duration():
    result = experiment_service.calculate_sample_size(
        baseline_rate=0.10, minimum_detectable_effect=0.02,
        confidence_level=0.95, power=0.80, daily_eligible_users=1000,
    )
    assert result["sample_size_per_arm"] > 0
    assert result["total_sample_size"] == result["sample_size_per_arm"] * 2
    assert result["estimated_duration_days"] == (result["total_sample_size"] + 999) // 1000
    assert "normal approximation" in result["method"]


@pytest.mark.parametrize("kwargs", [
    {"baseline_rate": 0, "minimum_detectable_effect": 0.02},
    {"baseline_rate": 0.99, "minimum_detectable_effect": 0.02},
    {"baseline_rate": 0.1, "minimum_detectable_effect": 0},
    {"baseline_rate": 0.1, "minimum_detectable_effect": 0.9},
    {"baseline_rate": 0.1, "minimum_detectable_effect": 0.02, "confidence_level": 0.93},
])
def test_sample_size_rejects_invalid_parameters(kwargs):
    with pytest.raises(ValueError):
        experiment_service.calculate_sample_size(**kwargs)


def test_generate_plan_uses_opportunity_context():
    plan = experiment_service.generate_experiment_plan({
        "feature": "Checkout & Payments",
        "customer_signal": {"review_count": 12, "average_rating": 2.1},
        "behavior_signal": {"detail": "31 sessions reached cart without purchase."},
    })
    assert "Checkout & Payments" in plan["name"]
    assert "12 review" in plan["rationale"]
    assert "31 sessions" in plan["rationale"]
    assert plan["primary_metric"]["type"] == "binary"
    assert len(plan["guardrails"]) >= 2
    assert "not causal evidence" in plan["evidence_note"]


def test_create_list_and_update_experiment(isolated_database):
    saved = experiment_service.create_experiment({
        "name": "Checkout experiment", "opportunity_id": "payments",
        "opportunity_title": "Payment friction",
        "hypothesis": "Reducing payment steps will increase completed purchases.",
        "rationale": "Payment reviews and funnel drop-off point to friction.",
        "primary_metric": "Purchase conversion rate",
        "secondary_metrics": [{"name": "Time to checkout"}],
        "guardrails": [{"name": "Error rate"}],
        "baseline_rate": 0.10, "minimum_detectable_effect": 0.02,
        "daily_eligible_users": 1000,
    })
    assert saved["status"] == "draft"
    assert saved["sample_size_per_arm"] > 0
    assert len(experiment_service.list_experiments()) == 1
    updated = experiment_service.update_experiment_status(saved["id"], "running")
    assert updated["status"] == "running"
    assert experiment_service.update_experiment_status("missing", "running") is None


def test_analysis_reports_lift_intervals_and_guardrails():
    result = experiment_service.analyze_experiment({
        "control_users": 1000, "control_conversions": 100,
        "variant_users": 1000, "variant_conversions": 125,
        "confidence_level": 0.95, "planned_sample_size_per_arm": 900,
        "guardrails": [{
            "name": "Error rate", "control_rate": 0.02,
            "variant_rate": 0.04, "max_increase": 0.005,
        }],
    })
    assert result["absolute_lift"] == pytest.approx(0.025)
    assert result["relative_lift_percent"] == pytest.approx(25)
    assert result["sample_size_reached"] is True
    assert result["guardrails"][0]["status"] == "review"
    assert len(result["difference_confidence_interval"]) == 2


def test_wilson_interval_rejects_invalid_counts():
    with pytest.raises(ValueError):
        experiment_service.wilson_interval(11, 10)



def test_analysis_rejects_conversions_greater_than_users():
    with pytest.raises(ValueError):
        experiment_service.analyze_experiment({
            "control_users": 10, "control_conversions": 11,
            "variant_users": 10, "variant_conversions": 2,
        })


def test_analysis_guardrail_flags_regression():
    result = experiment_service.analyze_experiment({
        "control_users": 100, "control_conversions": 10,
        "variant_users": 100, "variant_conversions": 12,
        "guardrails": [{
            "name": "Error rate", "control_rate": 0.01,
            "variant_rate": 0.04, "max_increase": 0.01,
        }],
    })
    assert result["guardrails"][0]["status"] == "review"


def test_sample_size_rejects_non_finite_values():
    with pytest.raises(ValueError):
        experiment_service.calculate_sample_size(
            baseline_rate=float("nan"), minimum_detectable_effect=0.02
        )



def test_experiment_api_endpoints_and_validation(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app

    database = tmp_path / "api-experiments.db"
    data_dir = tmp_path / "api-data"
    data_dir.mkdir()
    monkeypatch.setattr("app.services.dataset_service.DB_PATH", database)
    monkeypatch.setattr("app.services.dataset_service.DATA_DIR", data_dir)
    client = TestClient(app)

    sample = client.post("/api/experiments/sample-size", json={
        "baseline_rate": 0.1,
        "minimum_detectable_effect": 0.02,
        "daily_eligible_users": 1000,
    })
    assert sample.status_code == 200
    assert sample.json()["sample_size_per_arm"] > 0

    invalid = client.post("/api/experiments/analyze", json={
        "control_users": 10, "control_conversions": 11,
        "variant_users": 10, "variant_conversions": 2,
    })
    assert invalid.status_code == 422

    created = client.post("/api/experiments", json={
        "name": "API-created experiment",
        "hypothesis": "A simpler checkout will increase completed purchases.",
        "primary_metric": "Purchase conversion rate",
        "baseline_rate": 0.1,
        "minimum_detectable_effect": 0.02,
        "daily_eligible_users": 800,
        "guardrails": [{"name": "Error rate", "direction": "must not increase"}],
    })
    assert created.status_code == 200
    experiment_id = created.json()["id"]

    listed = client.get("/api/experiments")
    assert listed.status_code == 200
    assert any(row["id"] == experiment_id for row in listed.json()["experiments"])

    updated = client.patch(f"/api/experiments/{experiment_id}/status", json={"status": "running"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "running"

    event_data = _event_rows(experiment_id, 5000, 5000, 500, 750)
    monkeypatch.setattr(experiment_service, "get_latest_dataset", lambda _: event_data)
    decision = client.post(f"/api/experiments/{experiment_id}/decision", json={
        "exposure_event": "experiment_exposed",
        "conversion_event": "purchase",
    })
    assert decision.status_code == 200
    assert decision.json()["recommendation"] == "Ship"


def _decision_experiment():
    return experiment_service.create_experiment({
        "name": "Event-backed checkout test",
        "hypothesis": "A clearer checkout will increase completed purchases.",
        "primary_metric": "Purchase conversion rate",
        "baseline_rate": 0.10,
        "minimum_detectable_effect": 0.02,
        "daily_eligible_users": 1000,
    })


def _event_rows(experiment_id, control_users, variant_users,
                control_conversions, variant_conversions, control_errors=0,
                variant_errors=0):
    import pandas as pd

    rows = []
    for arm, total, conversions in (
        ("control", control_users, control_conversions),
        ("variant", variant_users, variant_conversions),
    ):
        for index in range(total):
            user_id = f"{arm}-{index}"
            rows.append({
                "user_id": user_id, "event_name": "experiment_exposed",
                "timestamp": "2026-01-01T10:00:00Z",
                "experiment_id": experiment_id, "experiment_variant": arm,
            })
            if index < conversions:
                rows.append({
                    "user_id": user_id, "event_name": "purchase",
                    "timestamp": "2026-01-01T10:05:00Z",
                    "experiment_id": "", "experiment_variant": "",
                })
            error_count = control_errors if arm == "control" else variant_errors
            if index < error_count:
                rows.append({
                    "user_id": user_id, "event_name": "checkout_error",
                    "timestamp": "2026-01-01T10:06:00Z",
                    "experiment_id": "", "experiment_variant": "",
                })
    return pd.DataFrame(rows)


def test_event_decision_recommends_ship_when_sample_and_positive_interval_reached(
    isolated_database, monkeypatch
):
    saved = _decision_experiment()
    events = _event_rows(saved["id"], 5000, 5000, 500, 750)
    monkeypatch.setattr(experiment_service, "get_latest_dataset", lambda _: events)

    result = experiment_service.analyze_experiment_from_events(
        saved["id"], "experiment_exposed", "purchase"
    )

    assert result["recommendation"] == "Ship"
    assert result["analysis"]["sample_size_reached"] is True
    assert result["analysis"]["difference_confidence_interval"][0] > 0
    assert result["events"]["exposed_users"] == 10000


def test_event_decision_recommends_iterate_for_inconclusive_underpowered_result(
    isolated_database, monkeypatch
):
    saved = _decision_experiment()
    events = _event_rows(saved["id"], 100, 100, 10, 11)
    monkeypatch.setattr(experiment_service, "get_latest_dataset", lambda _: events)

    result = experiment_service.analyze_experiment_from_events(
        saved["id"], "experiment_exposed", "purchase"
    )

    assert result["recommendation"] == "Iterate"
    assert result["analysis"]["sample_size_reached"] is False


def test_event_decision_stops_for_guardrail_regression(isolated_database, monkeypatch):
    saved = _decision_experiment()
    events = _event_rows(
        saved["id"], 1000, 1000, 100, 110,
        control_errors=10, variant_errors=100,
    )
    monkeypatch.setattr(experiment_service, "get_latest_dataset", lambda _: events)

    result = experiment_service.analyze_experiment_from_events(
        saved["id"], "experiment_exposed", "purchase",
        [{"name": "Checkout errors", "event_name": "checkout_error", "max_increase": 0.02}],
    )

    assert result["recommendation"] == "Stop"
    assert result["analysis"]["guardrails"][0]["status"] == "review"


def test_event_decision_rejects_missing_experiment_tracking_columns(
    isolated_database, monkeypatch
):
    import pandas as pd

    saved = _decision_experiment()
    events = pd.DataFrame([{
        "user_id": "u1", "event_name": "experiment_exposed",
        "timestamp": "2026-01-01T10:00:00Z",
    }])
    monkeypatch.setattr(experiment_service, "get_latest_dataset", lambda _: events)

    with pytest.raises(ValueError, match="additional experiment columns"):
        experiment_service.analyze_experiment_from_events(
            saved["id"], "experiment_exposed", "purchase"
        )
