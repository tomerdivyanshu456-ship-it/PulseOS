from app.services import diagnostic_service


def test_diagnostics_combine_funnel_and_customer_signals(monkeypatch):
    monkeypatch.setattr(diagnostic_service, "calculate_journey_intelligence", lambda: {
        "unit": "sessions",
        "funnel": [
            {"event_name": "view", "units_reached": 100, "drop_off_units": 0, "drop_off_rate": 0},
            {"event_name": "checkout", "units_reached": 40, "drop_off_units": 60, "drop_off_rate": 60},
        ],
        "segment_funnels": [],
    })
    monkeypatch.setattr(diagnostic_service, "calculate_product_opportunities", lambda: {
        "sources": {"reviews": True},
        "opportunities": [{
            "id": "payments", "feature": "Checkout", "priority_score": 80,
            "severity_score": 90, "priority": "Investigate",
            "customer_signal": {"topic": "Payments", "review_count": 5, "average_rating": 1.8, "evidence": []},
            "behavior_signal": {"label": "Payment reach", "value": 20, "unit": "users", "detail": "20 users attempted payment."},
            "recommendation": "Inspect payment errors.", "confidence_note": "Theme-level association.",
        }],
    })
    monkeypatch.setattr(diagnostic_service, "list_experiments", lambda: [])

    result = diagnostic_service.build_root_cause_diagnostics()

    assert result["status"] == "partial"
    assert result["summary"]["hypotheses"] == 2
    assert result["hypotheses"][0]["signal_type"] == "Funnel drop-off"
    assert result["hypotheses"][0]["evidence"][2]["value"] == 60


def test_diagnostics_handle_missing_sources(monkeypatch):
    def missing():
        raise ValueError("No uploaded dataset")

    monkeypatch.setattr(diagnostic_service, "calculate_journey_intelligence", missing)
    monkeypatch.setattr(diagnostic_service, "calculate_product_opportunities", missing)
    monkeypatch.setattr(diagnostic_service, "list_experiments", lambda: [])

    result = diagnostic_service.build_root_cause_diagnostics()

    assert result["status"] == "no_data"
    assert result["hypotheses"] == []
    assert len(result["data_gaps"]) == 2


def test_diagnostics_flag_segment_conversion_disparity(monkeypatch):
    monkeypatch.setattr(diagnostic_service, "calculate_journey_intelligence", lambda: {
        "unit": "users",
        "funnel": [],
        "segment_funnels": [
            {"segment": "A", "units": 20, "funnel": [{"units_reached": 20}, {"units_reached": 5}]},
            {"segment": "B", "units": 20, "funnel": [{"units_reached": 20}, {"units_reached": 15}]},
        ],
    })
    monkeypatch.setattr(diagnostic_service, "calculate_product_opportunities", lambda: {
        "sources": {"reviews": False}, "opportunities": [],
    })
    monkeypatch.setattr(diagnostic_service, "list_experiments", lambda: [])

    result = diagnostic_service.build_root_cause_diagnostics()

    segment = next(item for item in result["hypotheses"] if item["id"] == "segment-gap")
    assert segment["priority_score"] == 50
    assert len(segment["segment_context"]) == 2
