from app.services import health_service


def _analytics():
    return {
        "period": {"start_date": "2026-10-01", "end_date": "2026-10-30"},
        "metrics": {
            "daily_active_users": 20,
            "monthly_active_users": 100,
            "repeat_user_rate": 30,
            "conversion_rate": 5,
        },
    }


def _customer():
    return {
        "total_reviews": 100,
        "average_rating": 4.0,
        "sentiment_distribution": [
            {"sentiment": "Positive", "count": 70},
            {"sentiment": "Neutral", "count": 10},
            {"sentiment": "Negative", "count": 20},
        ],
    }


def test_health_scorecard_calculates_all_four_pillars(monkeypatch):
    monkeypatch.setattr(health_service, "calculate_product_analytics", _analytics)
    monkeypatch.setattr(health_service, "calculate_voice_of_customer", _customer)
    monkeypatch.setattr(health_service, "build_product_strategy", lambda: {
        "summary": {"opportunities_reviewed": 4, "experiments_linked": 2}
    })

    result = health_service.build_product_health()

    assert result["status"] == "ready"
    assert result["score_coverage"] == {"available_pillars": 4, "total_pillars": 4}
    assert [item["id"] for item in result["pillars"]] == [
        "engagement", "conversion", "customer_sentiment", "experimentation"
    ]
    assert result["pillars"][0]["score"] == 100
    assert result["pillars"][1]["score"] == 100
    assert result["pillars"][2]["score"] == 100
    assert result["pillars"][3]["score"] == 50
    assert result["overall_score"] == 87.5


def test_missing_sources_produce_partial_score_not_false_zero(monkeypatch):
    def unavailable():
        raise ValueError("No dataset uploaded.")

    monkeypatch.setattr(health_service, "calculate_product_analytics", unavailable)
    monkeypatch.setattr(health_service, "calculate_voice_of_customer", unavailable)
    monkeypatch.setattr(health_service, "build_product_strategy", lambda: {
        "summary": {"opportunities_reviewed": 0, "experiments_linked": 0}
    })

    result = health_service.build_product_health()

    assert result["status"] == "no_data"
    assert result["overall_score"] is None
    assert result["pillars"] == []
    assert len(result["data_gaps"]) >= 2


def test_partial_data_reweights_only_available_pillars(monkeypatch):
    monkeypatch.setattr(health_service, "calculate_product_analytics", _analytics)

    def unavailable():
        raise ValueError("No reviews.")

    monkeypatch.setattr(health_service, "calculate_voice_of_customer", unavailable)
    monkeypatch.setattr(health_service, "build_product_strategy", lambda: {
        "summary": {"opportunities_reviewed": 2, "experiments_linked": 0}
    })

    result = health_service.build_product_health()

    assert result["status"] == "partial"
    assert result["score_coverage"]["available_pillars"] == 3
    assert result["overall_score"] == 83.3


def test_health_pillar_status_boundaries():
    low = health_service._pillar("x", "Test", 49.9, "", [], "", "", "")
    middle = health_service._pillar("x", "Test", 50, "", [], "", "", "")
    high = health_service._pillar("x", "Test", 75, "", [], "", "", "")

    assert low["status"] == "at_risk"
    assert middle["status"] == "needs_attention"
    assert high["status"] == "healthy"
