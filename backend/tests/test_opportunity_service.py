from app.services import opportunity_service


def test_payment_opportunity_combines_review_and_behavior_signals(monkeypatch):
    product = {
        "metrics": {"total_users": 3},
        "sequential_funnel": [
            {"stage": "Product Viewed", "count": 3},
            {"stage": "Add To Cart", "count": 2},
            {"stage": "Purchase", "count": 1},
        ],
        "sequential_funnel_meta": {
            "unit": "sessions",
            "reliability_note": "Ordered progression is measured within session_id.",
        },
        "event_adoption": [],
    }
    voice = {
        "topics": [{
            "key": "payments",
            "label": "Payments & Transactions",
            "review_count": 1,
            "average_rating": 1.0,
            "priority_score": 73,
            "evidence": [{"rating": 1, "review_text": "Payment failed and money was deducted"}],
        }]
    }
    monkeypatch.setattr(opportunity_service, "calculate_product_analytics", lambda: product)
    monkeypatch.setattr(opportunity_service, "calculate_voice_of_customer", lambda: voice)

    result = opportunity_service.calculate_product_opportunities()

    assert result["status"] == "ready"
    assert len(result["opportunities"]) == 1
    opportunity = result["opportunities"][0]
    assert opportunity["feature"] == "Checkout & Payments"
    assert opportunity["priority"] == "Validate"
    assert opportunity["behavior_signal"]["value"] == 1
    assert opportunity["customer_signal"]["review_count"] == 1
    assert "not joined at user or session level" in result["methodology"]


def test_opportunities_return_partial_status_when_one_source_is_missing(monkeypatch):
    monkeypatch.setattr(
        opportunity_service,
        "calculate_product_analytics",
        lambda: (_ for _ in ()).throw(ValueError("No events uploaded")),
    )
    monkeypatch.setattr(
        opportunity_service,
        "calculate_voice_of_customer",
        lambda: {"topics": []},
    )

    result = opportunity_service.calculate_product_opportunities()

    assert result["status"] == "partial"
    assert result["opportunities"] == []
    assert result["data_gaps"] == ["No events uploaded"]


def test_opportunities_return_no_data_when_both_sources_are_missing(monkeypatch):
    def missing():
        raise ValueError("Dataset missing")

    monkeypatch.setattr(opportunity_service, "calculate_product_analytics", missing)
    monkeypatch.setattr(opportunity_service, "calculate_voice_of_customer", missing)

    result = opportunity_service.calculate_product_opportunities()

    assert result["status"] == "no_data"
    assert result["opportunities"] == []
    assert len(result["data_gaps"]) == 2
