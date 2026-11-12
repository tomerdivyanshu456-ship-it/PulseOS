"""Evidence-aware product health scorecard built from uploaded PulseOS datasets.

The score is a diagnostic index against explicit starter thresholds, not an
industry benchmark or a prediction of business outcomes.
"""
from app.services.analytics_service import calculate_product_analytics
from app.services.voice_of_customer_service import calculate_voice_of_customer
from app.services.strategy_service import build_product_strategy


STARTER_THRESHOLDS = {
    "repeat_user_rate_percent": 30.0,
    "dau_mau_ratio": 0.20,
    "conversion_rate_percent": 5.0,
    "positive_review_share_percent": 70.0,
}


def _bounded(value):
    return max(0.0, min(100.0, float(value)))


def _pillar(identifier, title, score, summary, metrics, source, benchmark, caveat):
    score = round(_bounded(score), 1)
    status = "healthy" if score >= 75 else "needs_attention" if score >= 50 else "at_risk"
    return {
        "id": identifier,
        "title": title,
        "score": score,
        "status": status,
        "summary": summary,
        "metrics": metrics,
        "source": source,
        "benchmark": benchmark,
        "caveat": caveat,
    }


def build_product_health():
    """Build a weighted scorecard, omitting pillars without source evidence."""
    pillars = []
    data_gaps = []
    period = None
    sources = {"events": False, "reviews": False, "experiments": False}

    analytics = None
    try:
        analytics = calculate_product_analytics()
        sources["events"] = True
        period = analytics.get("period")
        metrics = analytics["metrics"]
        mau = int(metrics.get("monthly_active_users", 0))
        dau = int(metrics.get("daily_active_users", 0))
        stickiness = (dau / mau) if mau else 0.0
        repeat_rate = float(metrics.get("repeat_user_rate", 0) or 0)
        engagement_score = (
            0.70 * _bounded(repeat_rate / STARTER_THRESHOLDS["repeat_user_rate_percent"] * 100)
            + 0.30 * _bounded(stickiness / STARTER_THRESHOLDS["dau_mau_ratio"] * 100)
        )
        pillars.append(_pillar(
            "engagement", "User engagement", engagement_score,
            "Combines repeat active-day usage and DAU-to-MAU stickiness.",
            [
                {"label": "Repeat user rate", "value": round(repeat_rate, 1), "unit": "%"},
                {"label": "DAU / MAU", "value": round(stickiness * 100, 1), "unit": "%"},
            ],
            "Behavioural events CSV",
            "Starter targets: repeat user rate 30%; DAU/MAU 20%.",
            "Repeat usage means activity on at least two distinct calendar days in the uploaded dataset. DAU/MAU is a rough stickiness proxy.",
        ))
        conversion = float(metrics.get("conversion_rate", 0) or 0)
        conversion_score = _bounded(
            conversion / STARTER_THRESHOLDS["conversion_rate_percent"] * 100
        )
        pillars.append(_pillar(
            "conversion", "Conversion", conversion_score,
            "Measures unique purchasers as a share of unique product viewers.",
            [{"label": "View-to-purchase conversion", "value": round(conversion, 2), "unit": "%"}],
            "Behavioural events CSV",
            "Starter target: 5% view-to-purchase conversion.",
            "This is a user-level ratio across the available 30-day window, not a session-level or ordered funnel conversion rate.",
        ))
    except (ValueError, KeyError, TypeError, ZeroDivisionError) as exc:
        data_gaps.append(f"Behavioural health unavailable: {exc}")

    customer = None
    try:
        customer = calculate_voice_of_customer()
        sources["reviews"] = True
        sentiment = {
            item["sentiment"]: int(item["count"])
            for item in customer.get("sentiment_distribution", [])
        }
        total = int(customer.get("total_reviews", 0))
        positive_share = (sentiment.get("Positive", 0) / total * 100) if total else 0
        rating = float(customer.get("average_rating", 0) or 0)
        customer_score = (
            0.70 * _bounded(positive_share / STARTER_THRESHOLDS["positive_review_share_percent"] * 100)
            + 0.30 * _bounded(rating / 5 * 100)
        )
        negative_share = sentiment.get("Negative", 0) / total * 100 if total else 0
        pillars.append(_pillar(
            "customer_sentiment", "Customer sentiment", customer_score,
            "Combines positive review share and average customer rating.",
            [
                {"label": "Average rating", "value": round(rating, 2), "unit": "/ 5"},
                {"label": "Positive reviews", "value": round(positive_share, 1), "unit": "%"},
                {"label": "Negative reviews", "value": round(negative_share, 1), "unit": "%"},
                {"label": "Reviews analysed", "value": total, "unit": "reviews"},
            ],
            "Customer reviews CSV",
            "Starter target: 70% positive reviews; rating contributes separately.",
            "Sentiment is estimated using the project's keyword lexicon with rating-based fallback; it is not a trained sentiment model.",
        ))
    except (ValueError, KeyError, TypeError, ZeroDivisionError) as exc:
        data_gaps.append(f"Customer sentiment unavailable: {exc}")

    try:
        strategy = build_product_strategy()
        opportunity_count = int(strategy.get("summary", {}).get("opportunities_reviewed", 0))
        linked_count = int(strategy.get("summary", {}).get("experiments_linked", 0))
        sources["experiments"] = linked_count > 0
        if opportunity_count > 0:
            coverage = linked_count / opportunity_count * 100
            pillars.append(_pillar(
                "experimentation", "Experiment coverage", coverage,
                "Share of identified product opportunities linked to at least one saved experiment.",
                [
                    {"label": "Opportunities with experiments", "value": linked_count, "unit": "opportunities"},
                    {"label": "Opportunities reviewed", "value": opportunity_count, "unit": "opportunities"},
                ],
                "Product opportunities + saved experiments",
                "Starter target: 100% of prioritised opportunities have a linked experiment.",
                "Coverage measures planning linkage only; it does not measure experiment quality, completion, statistical validity or learning.",
            ))
        else:
            data_gaps.append("Experiment coverage unavailable until product opportunities can be identified.")
    except (ValueError, KeyError, TypeError) as exc:
        data_gaps.append(f"Experiment coverage unavailable: {exc}")

    if pillars:
        weights = {
            "engagement": 0.25,
            "conversion": 0.25,
            "customer_sentiment": 0.25,
            "experimentation": 0.25,
        }
        available_weight = sum(weights[item["id"]] for item in pillars)
        overall = round(sum(item["score"] * weights[item["id"]] for item in pillars) / available_weight, 1)
        label = "Healthy" if overall >= 75 else "Needs attention" if overall >= 50 else "At risk"
        status = "ready" if len(pillars) == 4 else "partial"
    else:
        overall = None
        label = "Insufficient data"
        status = "no_data"

    strongest = sorted(pillars, key=lambda item: item["score"], reverse=True)[:2]
    weakest = sorted(pillars, key=lambda item: item["score"])[:2]
    return {
        "status": status,
        "overall_score": overall,
        "overall_label": label,
        "score_coverage": {"available_pillars": len(pillars), "total_pillars": 4},
        "period": period,
        "pillars": pillars,
        "strongest_areas": [{"title": item["title"], "score": item["score"]} for item in strongest],
        "areas_to_investigate": [{"title": item["title"], "score": item["score"]} for item in weakest],
        "data_gaps": data_gaps,
        "sources": sources,
        "methodology": (
            "The overall diagnostic index is the equal-weight average of available pillars; missing pillars are omitted and "
            "coverage is shown rather than treated as zero. Engagement combines repeat-user rate (70%) and DAU/MAU (30%). "
            "Conversion is scaled against a configurable 5% starter target. Customer sentiment combines positive-review "
            "share (70%) and average rating (30%). Experiment coverage is the share of identified opportunities linked to "
            "a saved experiment. Starter thresholds are illustrative and should be calibrated to product type, baseline, "
            "market and business model. This is not an industry benchmark, causal estimate or forecast."
        ),
    }
