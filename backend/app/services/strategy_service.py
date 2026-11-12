"""Evidence-led product strategy synthesis built on existing PulseOS signals.

Scores are prioritisation heuristics, not financial forecasts or causal estimates.
"""
from app.services.opportunity_service import calculate_product_opportunities
from app.services.experiment_service import list_experiments


FEATURE_PLAYBOOK = {
    "Checkout & Payments": {
        "metric": "Cart-to-purchase conversion rate",
        "action": "Map the checkout journey by payment method and device. Instrument payment attempts, failures and successful transactions before changing the flow.",
        "success": "Improve the cart-to-purchase rate without increasing payment errors, refunds or duplicate charges.",
        "effort": 3,
    },
    "App Stability": {
        "metric": "Crash-free sessions and error rate",
        "action": "Segment crashes and errors by app version, device and operating system. Reproduce the most frequent high-impact failure before prioritising a fix.",
        "success": "Increase crash-free sessions and reduce the targeted error rate without degrading core journey completion.",
        "effort": 4,
    },
    "Customer Support": {
        "metric": "First-response time and repeat contact rate",
        "action": "Classify support contacts by journey and issue. Identify the largest avoidable contact driver and test a focused self-service or workflow improvement.",
        "success": "Reduce repeat contacts and time to resolution while maintaining customer satisfaction.",
        "effort": 3,
    },
    "Delivery & Fulfilment": {
        "metric": "On-time delivery rate",
        "action": "Compare promised and actual delivery times by location and fulfilment partner. Find where tracking becomes stale or delivery misses cluster.",
        "success": "Improve on-time delivery and reduce delivery-related complaints in the affected segment.",
        "effort": 4,
    },
    "App Performance": {
        "metric": "Journey load time and completion rate",
        "action": "Measure screen-load time and API latency for the affected journey. Prioritise the slowest high-traffic step and validate with a before/after cohort.",
        "success": "Reduce load time while maintaining or improving journey completion.",
        "effort": 3,
    },
    "Product Discovery & Navigation": {
        "metric": "Search-to-product-view and view-to-cart conversion",
        "action": "Inspect search refinement, zero-result queries and navigation paths. Validate the main usability friction with a small usability test before redesigning.",
        "success": "Improve discovery-to-product-view and view-to-cart conversion without increasing search abandonment.",
        "effort": 3,
    },
}


def _bounded_score(value):
    try:
        return max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def build_product_strategy(effort_estimates=None):
    """Rank investigation opportunities using impact, evidence confidence and effort."""
    effort_estimates = effort_estimates or {}
    opportunity_result = calculate_product_opportunities()
    opportunities = opportunity_result.get("opportunities", [])
    experiments = list_experiments()
    max_reach = max(
        [float((item.get("behavior_signal") or {}).get("value", 0) or 0) for item in opportunities]
        or [0.0]
    )

    recommendations = []
    for item in opportunities:
        feature = item.get("feature", "Product experience")
        playbook = FEATURE_PLAYBOOK.get(feature, {
            "metric": "Task completion rate",
            "action": item.get("recommendation", "Investigate the customer journey and instrument the suspected friction point."),
            "success": "Improve the relevant journey metric without worsening customer or operational guardrails.",
            "effort": 3,
        })
        severity = _bounded_score(item.get("severity_score", 0))
        reach = float((item.get("behavior_signal") or {}).get("value", 0) or 0)
        reach_score = (reach / max_reach * 100) if max_reach > 0 and reach > 0 else 0.0
        legacy_priority = _bounded_score(item.get("priority_score", 0))
        impact_score = round(severity * 0.60 + reach_score * 0.25 + legacy_priority * 0.15, 1)
        confidence_score = _bounded_score(item.get("evidence_strength", 0))
        effort = effort_estimates.get(item.get("id"), playbook["effort"])
        if isinstance(effort, bool) or not isinstance(effort, int) or not 1 <= effort <= 5:
            raise ValueError("Effort estimates must be integers from 1 to 5.")

        priority_score = round(impact_score * (confidence_score / 100) * (3 / effort), 1)
        linked_experiments = [
            experiment for experiment in experiments
            if experiment.get("opportunity_id") == item.get("id")
        ]
        recommendations.append({
            "id": item.get("id"),
            "title": item.get("title"),
            "feature": feature,
            "priority": item.get("priority", "Monitor"),
            "priority_score": min(priority_score, 100.0),
            "impact_score": impact_score,
            "confidence_score": confidence_score,
            "effort_estimate": effort,
            "effort_label": {1: "Very low", 2: "Low", 3: "Medium", 4: "High", 5: "Very high"}[effort],
            "customer_evidence": {
                "review_count": int(item.get("customer_signal", {}).get("review_count", 0)),
                "average_rating": item.get("customer_signal", {}).get("average_rating"),
                "examples": item.get("customer_signal", {}).get("evidence", [])[:2],
            },
            "behavioral_evidence": item.get("behavior_signal"),
            "action": playbook["action"],
            "expected_metric": playbook["metric"],
            "success_measurement": playbook["success"],
            "linked_experiment_count": len(linked_experiments),
            "experiment_names": [experiment.get("name") for experiment in linked_experiments[:3]],
            "evidence_note": item.get("confidence_note", ""),
            "score_explanation": (
                "Priority score = impact score × evidence confidence × (3 ÷ effort). "
                "Impact weights: customer severity 60%, relative behavioural reach 25%, "
                "existing opportunity priority 15%. Effort is an editable 1–5 estimate."
            ),
        })

    recommendations.sort(
        key=lambda item: (item["priority_score"], item["impact_score"], item["confidence_score"]),
        reverse=True,
    )
    for index, item in enumerate(recommendations, start=1):
        item["rank"] = index

    return {
        "status": opportunity_result.get("status", "no_data"),
        "summary": {
            "opportunities_reviewed": len(recommendations),
            "high_priority_count": sum(item["priority_score"] >= 50 for item in recommendations),
            "experiments_linked": sum(item["linked_experiment_count"] > 0 for item in recommendations),
            "top_recommendation": recommendations[0]["feature"] if recommendations else None,
        },
        "recommendations": recommendations,
        "data_gaps": opportunity_result.get("data_gaps", []),
        "sources": opportunity_result.get("sources", {"events": False, "reviews": False}),
        "methodology": (
            "This decision-support ranking combines customer complaint severity, review evidence volume, "
            "theme-level behavioural reach and an editable effort estimate. Review and event datasets are "
            "not joined at user/session level. Impact and confidence are heuristic scores, not measured "
            "business impact, statistical confidence intervals or causal effects."
        ),
    }
