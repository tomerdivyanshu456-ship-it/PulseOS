from app.services import strategy_service


def _opportunity(identifier, feature, severity, evidence, reach, priority=70):
    return {
        "id": identifier,
        "title": f"{feature}: investigate customer friction",
        "feature": feature,
        "priority": "Investigate",
        "priority_score": priority,
        "severity_score": severity,
        "evidence_strength": evidence,
        "customer_signal": {
            "review_count": 8,
            "average_rating": 2.0,
            "evidence": [{"rating": 1, "review_text": "Example complaint"}],
        },
        "behavior_signal": {
            "label": "Related event reach",
            "value": reach,
            "unit": "users",
            "detail": f"{reach} users triggered a related event.",
        } if reach else None,
        "recommendation": "Inspect the journey.",
        "confidence_note": "Theme-level evidence only.",
    }


def test_strategy_returns_ranked_evidence_and_transparent_score(monkeypatch):
    monkeypatch.setattr(
        strategy_service,
        "calculate_product_opportunities",
        lambda: {
            "status": "ready",
            "opportunities": [
                _opportunity("payments", "Checkout & Payments", 90, 80, 100),
                _opportunity("support", "Customer Support", 70, 60, 25),
            ],
            "data_gaps": [],
            "sources": {"events": True, "reviews": True},
        },
    )
    monkeypatch.setattr(strategy_service, "list_experiments", lambda: [
        {"opportunity_id": "payments", "name": "Checkout test"}
    ])

    result = strategy_service.build_product_strategy()

    assert result["summary"]["opportunities_reviewed"] == 2
    assert result["summary"]["experiments_linked"] == 1
    assert result["recommendations"][0]["id"] == "payments"
    assert result["recommendations"][0]["rank"] == 1
    assert result["recommendations"][0]["expected_metric"] == "Cart-to-purchase conversion rate"
    assert result["recommendations"][0]["experiment_names"] == ["Checkout test"]
    assert "not measured business impact" in result["methodology"]


def test_effort_override_changes_priority_without_changing_impact(monkeypatch):
    monkeypatch.setattr(
        strategy_service,
        "calculate_product_opportunities",
        lambda: {
            "status": "ready",
            "opportunities": [_opportunity("payments", "Checkout & Payments", 90, 80, 100)],
            "data_gaps": [],
            "sources": {"events": True, "reviews": True},
        },
    )
    monkeypatch.setattr(strategy_service, "list_experiments", lambda: [])

    default = strategy_service.build_product_strategy()
    high_effort = strategy_service.build_product_strategy({"payments": 5})

    assert high_effort["recommendations"][0]["impact_score"] == default["recommendations"][0]["impact_score"]
    assert high_effort["recommendations"][0]["priority_score"] < default["recommendations"][0]["priority_score"]
    assert high_effort["recommendations"][0]["effort_estimate"] == 5


def test_strategy_handles_no_opportunities(monkeypatch):
    monkeypatch.setattr(
        strategy_service,
        "calculate_product_opportunities",
        lambda: {"status": "no_data", "opportunities": [], "data_gaps": ["No dataset"], "sources": {"events": False, "reviews": False}},
    )
    monkeypatch.setattr(strategy_service, "list_experiments", lambda: [])

    result = strategy_service.build_product_strategy()

    assert result["recommendations"] == []
    assert result["summary"]["opportunities_reviewed"] == 0
    assert result["data_gaps"] == ["No dataset"]


def test_strategy_rejects_invalid_effort_override(monkeypatch):
    monkeypatch.setattr(
        strategy_service,
        "calculate_product_opportunities",
        lambda: {"status": "ready", "opportunities": [_opportunity("payments", "Checkout & Payments", 90, 80, 100)]},
    )
    monkeypatch.setattr(strategy_service, "list_experiments", lambda: [])

    try:
        strategy_service.build_product_strategy({"payments": 8})
    except ValueError as exc:
        assert "1 to 5" in str(exc)
    else:
        raise AssertionError("Expected invalid effort to be rejected.")
