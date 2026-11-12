from app.services import ai_analyst_service


def test_ai_analyst_includes_cross_source_opportunity(monkeypatch):
    product = {
        "metrics": {
            "total_events": 4,
            "total_users": 2,
            "daily_active_users": 2,
            "monthly_active_users": 2,
            "conversion_rate": 50,
            "total_revenue": 499,
        },
        "period": {"start_date": "2026-11-01", "end_date": "2026-11-01"},
        "sequential_funnel": [
            {"stage": "Product Viewed", "count": 2},
            {"stage": "Add To Cart", "count": 2},
            {"stage": "Purchase", "count": 1},
        ],
        "sequential_funnel_meta": {"unit": "sessions", "method": "ordered_events_within_session", "reliability_note": "Measured within session_id."},
    }
    voice = {
        "topics": [],
        "negative_evidence": [],
        "total_reviews": 1,
        "average_rating": 1.0,
        "sentiment_distribution": [{"sentiment": "Negative", "count": 1}],
    }
    opportunity = {
        "status": "ready",
        "opportunities": [{
            "feature": "Checkout & Payments",
            "priority": "Investigate",
            "customer_signal": {"review_count": 1, "average_rating": 1.0},
            "behavior_signal": {"detail": "1 session reached cart without a later purchase."},
            "recommendation": "Inspect payment failures and checkout errors.",
            "confidence_note": "Theme-level association only; no user-level join.",
        }],
    }
    monkeypatch.setattr(ai_analyst_service, "calculate_product_analytics", lambda: product)
    monkeypatch.setattr(ai_analyst_service, "calculate_voice_of_customer", lambda: voice)
    monkeypatch.setattr(ai_analyst_service, "calculate_product_opportunities", lambda: opportunity)

    result = ai_analyst_service.answer_product_question(
        "Which product opportunity should we investigate first?"
    )

    assert any(item["title"] == "Cross-source opportunity: Checkout & Payments" for item in result["findings"])
    assert any(item["title"] == "Investigate Checkout & Payments" for item in result["recommendations"])
    assert any("Cross-source opportunity detection" in item for item in result["limitations"])
