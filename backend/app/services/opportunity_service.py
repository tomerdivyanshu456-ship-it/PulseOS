from app.services.analytics_service import calculate_product_analytics
from app.services.voice_of_customer_service import calculate_voice_of_customer


TOPIC_FEATURE_LINKS = {
    "payments": {
        "feature": "Checkout & Payments",
        "event_terms": ("checkout", "payment", "purchase", "order"),
        "review_terms": ("payment", "transaction", "money", "refund", "gateway", "upi", "card"),
        "action": "Inspect payment failures, checkout errors and transaction-state handling. Segment by payment method and device before selecting a fix.",
    },
    "app_stability": {
        "feature": "App Stability",
        "event_terms": ("app_open", "screen_view", "session", "crash", "error"),
        "review_terms": ("crash", "crashes", "bug", "freeze", "technical"),
        "action": "Compare crash-free sessions and error rates by app version and device, then reproduce the most common failure.",
    },
    "customer_support": {
        "feature": "Customer Support",
        "event_terms": ("support", "help", "ticket", "chat"),
        "review_terms": ("support", "customer", "agent", "help", "response", "reply", "service", "contact"),
        "action": "Connect support contacts to the affected journey and measure first-response time, resolution time and repeat contacts.",
    },
    "delivery": {
        "feature": "Delivery & Fulfilment",
        "event_terms": ("delivery", "order", "shipment", "tracking"),
        "review_terms": ("delivery", "delivered", "deliver", "late", "delay", "order", "courier", "shipping"),
        "action": "Compare promised and actual delivery times by location and fulfilment partner; inspect where tracking updates become stale.",
    },
    "performance": {
        "feature": "App Performance",
        "event_terms": ("load", "screen", "search", "app_open"),
        "review_terms": ("slow", "loading", "load", "lag", "speed", "performance", "hang"),
        "action": "Measure screen-load time and API latency for the affected journey, then prioritise the slowest high-traffic step.",
    },
    "usability": {
        "feature": "Product Discovery & Navigation",
        "event_terms": ("search", "product_viewed", "category", "browse"),
        "review_terms": ("confusing", "difficult", "navigation", "navigate", "interface", "design", "button", "screen", "layout", "search"),
        "action": "Review search and navigation journeys with session-level data and usability tests before redesigning the flow.",
    },
}


def _behavior_signal(product, topic_key):
    if not product:
        return None

    if topic_key == "payments":
        sequential = {item["stage"]: item["count"] for item in product.get("sequential_funnel", [])}
        carted = sequential.get("Add To Cart", 0)
        purchased = sequential.get("Purchase", 0)
        return {
            "label": "Cart-to-purchase progression",
            "value": max(carted - purchased, 0),
            "unit": product.get("sequential_funnel_meta", {}).get("unit", "users"),
            "detail": f"{max(carted - purchased, 0)} {product.get('sequential_funnel_meta', {}).get('unit', 'users')} reached add-to-cart without a later purchase in the measured sequence.",
            "method": product.get("sequential_funnel_meta", {}).get("reliability_note", ""),
        }

    matches = [
        item for item in product.get("event_adoption", [])
        if any(term in item.get("event_name", "").lower() for term in TOPIC_FEATURE_LINKS[topic_key]["event_terms"])
    ]
    if not matches:
        return None
    total_users = max(product.get("metrics", {}).get("total_users", 0), 1)
    active_users = max(item["active_users"] for item in matches)
    return {
        "label": "Related event reach",
        "value": active_users,
        "unit": "users",
        "detail": f"At least {active_users} users triggered a related tracked event ({round(active_users / total_users * 100, 1)}% of observed users).",
        "method": "Event-name matching is a proxy; it does not establish that the event and review describe the same user or session.",
    }


def calculate_product_opportunities():
    product = None
    voice = None
    data_gaps = []

    try:
        product = calculate_product_analytics()
    except ValueError as exc:
        data_gaps.append(str(exc))

    try:
        voice = calculate_voice_of_customer()
    except ValueError as exc:
        data_gaps.append(str(exc))

    if not product and not voice:
        return {
            "status": "no_data",
            "opportunities": [],
            "data_gaps": data_gaps,
            "methodology": "PulseOS needs at least one uploaded event dataset or customer review dataset.",
        }

    topics = {topic["key"]: topic for topic in (voice or {}).get("topics", [])}
    opportunities = []

    for topic_key, mapping in TOPIC_FEATURE_LINKS.items():
        topic = topics.get(topic_key)
        if not topic:
            continue

        behavior = _behavior_signal(product, topic_key)
        count = int(topic.get("review_count", 0))
        average_rating = float(topic.get("average_rating", 3))
        severity = round(((5 - average_rating) / 4) * 100)
        evidence_strength = 20 if count == 1 else 45 if count < 5 else 75 if count < 10 else 100
        behavior_present = behavior is not None and behavior.get("value", 0) > 0

        if severity >= 70 and (evidence_strength >= 45 or behavior_present):
            priority = "Investigate"
        elif severity >= 70 or behavior_present:
            priority = "Validate"
        else:
            priority = "Monitor"

        opportunities.append({
            "id": topic_key,
            "title": f"{mapping['feature']}: investigate customer friction",
            "feature": mapping["feature"],
            "priority": priority,
            "priority_score": int(topic.get("priority_score", 0)),
            "review_count": count,
            "average_rating": average_rating,
            "severity_score": severity,
            "evidence_strength": evidence_strength,
            "customer_signal": {
                "topic": topic.get("label", topic_key),
                "review_count": count,
                "average_rating": average_rating,
                "evidence": topic.get("evidence", [])[:3],
            },
            "behavior_signal": behavior,
            "recommendation": mapping["action"],
            "confidence_note": (
                "Customer feedback and behavioural metrics are separate datasets. "
                "They are combined at a theme level only; no individual review is linked to a user or session."
                if behavior else
                "Customer feedback is available, but no matching behavioural signal was found. Treat this as a feedback-led hypothesis."
            ),
        })

    opportunities.sort(
        key=lambda item: (
            {"Investigate": 0, "Validate": 1, "Monitor": 2}[item["priority"]],
            -item["priority_score"],
            -item["review_count"],
        )
    )

    return {
        "status": "ready" if product and voice else "partial",
        "opportunities": opportunities,
        "data_gaps": data_gaps,
        "sources": {
            "events": product is not None,
            "reviews": voice is not None,
        },
        "methodology": (
            "PulseOS matches review themes to related event groups using transparent keyword mappings. "
            "Priority is a heuristic based on review severity, review volume and whether a related behavioural signal exists. "
            "Separate datasets are not joined at user or session level; this is hypothesis generation, not causal evidence."
        ),
    }
