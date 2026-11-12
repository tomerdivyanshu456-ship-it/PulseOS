from app.services.analytics_service import calculate_product_analytics
from app.services.voice_of_customer_service import calculate_voice_of_customer


def _find_topic(voice, words):
    for topic in voice.get("topics", []):
        haystack = (topic.get("label", "") + " " + " ".join(topic.get("keywords", []))).lower()
        if any(word in haystack for word in words):
            return topic
    return None


def _evidence_for(voice, words=None):
    matches = []
    for item in voice.get("negative_evidence", []):
        text = item.get("review_text", "")
        if not words or any(word in text.lower() for word in words):
            matches.append({
                "type": "customer_review",
                "rating": item.get("rating"),
                "text": text,
                "sentiment": item.get("sentiment"),
            })
    return matches[:5]


def answer_product_question(question):
    question_lower = question.lower()
    sources = []
    findings = []
    evidence = []
    limitations = []

    try:
        product = calculate_product_analytics()
    except ValueError as exc:
        product = None
        limitations.append(str(exc))

    try:
        voice = calculate_voice_of_customer()
    except ValueError as exc:
        voice = None
        limitations.append(str(exc))

    if product:
        metrics = product["metrics"]
        funnel = product["funnel"]
        sources.append({
            "name": "Product event dataset",
            "detail": f'{metrics["total_events"]} events across {metrics["total_users"]} users; period {product["period"]["start_date"]} to {product["period"]["end_date"]}.',
        })
    else:
        metrics = None
        funnel = []

    if voice:
        sources.append({
            "name": "Customer review dataset",
            "detail": f'{voice["total_reviews"]} valid reviews; average rating {voice["average_rating"]}/5.',
        })

    if not product and not voice:
        return {
            "question": question,
            "answer": "I can't analyse this question yet because no valid product event or customer review dataset is available. Upload at least one dataset and try again.",
            "findings": [],
            "evidence": [],
            "sources": [],
            "limitations": limitations,
        }

    payment_topic = _find_topic(voice, ["payment", "transaction"]) if voice else None
    crash_topic = _find_topic(voice, ["crash", "stability"]) if voice else None
    support_topic = _find_topic(voice, ["support"]) if voice else None

    if any(word in question_lower for word in ["checkout", "payment", "purchase", "conversion", "abandon"]):
        if metrics:
            viewers = next((stage["users"] for stage in funnel if stage["stage"].lower() == "product viewed"), 0)
            carts = next((stage["users"] for stage in funnel if stage["stage"].lower() == "add to cart"), 0)
            buyers = next((stage["users"] for stage in funnel if stage["stage"].lower() == "purchase"), 0)
            findings.append({
                "title": "Observed product funnel",
                "detail": f"{viewers} unique users viewed a product, {carts} added to cart and {buyers} purchased. The reported user-level conversion rate is {metrics['conversion_rate']:.2f}%.",
                "type": "metric",
            })
            if viewers:
                findings.append({
                    "title": "View-to-cart progression",
                    "detail": f"{(carts / viewers) * 100:.1f}% of product viewers also appear as users with an add-to-cart event in this dataset.",
                    "type": "metric",
                })
        if payment_topic:
            findings.append({
                "title": "Payment feedback signal",
                "detail": f'{payment_topic["review_count"]} negative review(s) were grouped under {payment_topic["label"]}. Average rating: {payment_topic["average_rating"]}/5. Priority score: {payment_topic["priority_score"]}/100.',
                "type": "customer_feedback",
            })
            evidence.extend(_evidence_for(voice, ["payment", "transaction", "money", "refund"]))
        answer = "The available data shows the current funnel and a payment-related customer feedback signal. This makes payment flow a reasonable area to investigate. However, the event sample does not identify failed payment attempts or connect individual reviews to user journeys, so it cannot establish that payment problems caused abandonment."
        limitations.append("The uploaded event schema does not currently record payment failures, checkout errors or session-level step transitions.")
        limitations.append("Review records are not linked to event users or sessions; feedback and funnel metrics are separate evidence sources.")
    elif any(word in question_lower for word in ["crash", "stability", "bug", "app issue"]):
        if crash_topic:
            findings.append({
                "title": crash_topic["label"],
                "detail": f'{crash_topic["review_count"]} negative review(s); average rating {crash_topic["average_rating"]}/5; {crash_topic["evidence_level"]}.',
                "type": "customer_feedback",
            })
            evidence.extend(_evidence_for(voice, ["crash", "bug", "freeze"]))
        if metrics:
            findings.append({
                "title": "Behavioural context",
                "detail": f'{metrics["total_users"]} users generated {metrics["total_events"]} events in the selected event dataset. The current schema has no crash telemetry.',
                "type": "metric",
            })
        answer = "Customer feedback contains a signal about app stability. The uploaded event data can describe user activity, but it does not contain crash logs, app versions or device details. Treat the reviews as reports to investigate, not a measured crash rate."
        limitations.append("Crash rate cannot be calculated without crash events, app sessions or telemetry.")
    elif any(word in question_lower for word in ["support", "customer service", "complaint"]):
        if support_topic:
            findings.append({
                "title": support_topic["label"],
                "detail": f'{support_topic["review_count"]} negative review(s); average rating {support_topic["average_rating"]}/5; {support_topic["evidence_level"]}.',
                "type": "customer_feedback",
            })
            evidence.extend(_evidence_for(voice, ["support", "customer", "agent", "response"]))
        answer = "The review dataset contains customer-support feedback that can help identify a service area to investigate. The current data does not include ticket timestamps, first-response time or resolution status, so support performance cannot be quantified."
        limitations.append("Support SLA and resolution metrics require a support-ticket dataset.")
    else:
        if metrics:
            findings.append({
                "title": "Product activity",
                "detail": f'DAU: {metrics["daily_active_users"]}; MAU: {metrics["monthly_active_users"]}; conversion: {metrics["conversion_rate"]:.2f}%; revenue: ₹{metrics["total_revenue"]:,.0f}.',
                "type": "metric",
            })
            if funnel:
                findings.append({
                    "title": "Conversion funnel",
                    "detail": " → ".join(f'{stage["stage"]}: {stage["users"]}' for stage in funnel),
                    "type": "metric",
                })
        if voice:
            negative_count = next((item["count"] for item in voice["sentiment_distribution"] if item["sentiment"] == "Negative"), 0)
            findings.append({
                "title": "Customer sentiment",
                "detail": f'{negative_count} of {voice["total_reviews"]} reviews were classified as negative; average rating {voice["average_rating"]}/5.',
                "type": "customer_feedback",
            })
            for topic in voice.get("topics", [])[:3]:
                findings.append({
                    "title": topic["label"],
                    "detail": f'{topic["review_count"]} review(s), priority {topic["priority_score"]}/100. {topic["evidence_level"]}.',
                    "type": "customer_feedback",
                })
            evidence.extend(_evidence_for(voice))
        answer = "Here is a summary of the uploaded product and customer feedback data. Use the findings as investigation leads: the current sample sizes are small, and co-occurring metrics and review themes do not prove causation."
        limitations.append("This analyst uses deterministic rules and uploaded data; it is not a generative language model and does not infer facts absent from the datasets.")

    if voice and voice["total_reviews"] < 30:
        limitations.append(f'Only {voice["total_reviews"]} reviews are available. Theme frequencies and sentiment shares are preliminary signals, not representative estimates.')

    if product and metrics["total_users"] < 30:
        limitations.append(f'Only {metrics["total_users"]} users are present in the event dataset. Funnel percentages may be unstable.')

    return {
        "question": question,
        "answer": answer,
        "findings": findings,
        "evidence": evidence[:8],
        "sources": sources,
        "limitations": list(dict.fromkeys(limitations)),
    }
