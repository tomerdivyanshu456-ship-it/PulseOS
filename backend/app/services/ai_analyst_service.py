from app.services.analytics_service import calculate_product_analytics
from app.services.voice_of_customer_service import calculate_voice_of_customer


def _find_topic(voice, words):
    if not voice:
        return None
    for topic in voice.get("topics", []):
        haystack = (topic.get("label", "") + " " + " ".join(topic.get("keywords", []))).lower()
        if any(word in haystack for word in words):
            return topic
    return None


def _evidence_for(voice, words=None):
    if not voice:
        return []
    matches = []
    for item in voice.get("negative_evidence", []):
        review = item.get("review_text", "")
        if not words or any(word in review.lower() for word in words):
            matches.append({
                "type": "customer_review",
                "rating": item.get("rating"),
                "text": review,
                "sentiment": item.get("sentiment"),
            })
    return matches[:6]


def _recommendation(title, action, rationale, validation):
    return {
        "title": title,
        "action": action,
        "rationale": rationale,
        "validation": validation,
    }


def answer_product_question(question, history=None):
    question = question.strip()
    history = history or []
    history_text = " ".join(
        str(item.get("content", ""))
        for item in history[-8:]
        if isinstance(item, dict)
    )
    intent_text = (question + " " + history_text).lower()
    current = question.lower()

    sources, findings, evidence, limitations, recommendations = [], [], [], [], []

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

    if not product and not voice:
        return {
            "question": question,
            "answer": "I can't analyse this question yet because no valid product event or customer review dataset is available. Upload at least one dataset and try again.",
            "findings": [], "evidence": [], "sources": [],
            "limitations": limitations, "recommendations": [],
            "funnel_analysis": None, "context_used": bool(history),
        }

    metrics = product["metrics"] if product else None
    if product:
        sources.append({
            "name": "Product event dataset",
            "detail": f'{metrics["total_events"]} events across {metrics["total_users"]} users; period {product["period"]["start_date"]} to {product["period"]["end_date"]}.',
        })
    if voice:
        sources.append({
            "name": "Customer review dataset",
            "detail": f'{voice["total_reviews"]} valid reviews; average rating {voice["average_rating"]}/5.',
        })

    payment = _find_topic(voice, ["payment", "transaction"])
    crash = _find_topic(voice, ["crash", "stability"])
    support = _find_topic(voice, ["support"])

    checkout_intent = any(word in intent_text for word in ["checkout", "payment", "purchase", "conversion", "abandon", "cart"])
    crash_intent = any(word in intent_text for word in ["crash", "stability", "bug", "app issue"])
    support_intent = any(word in intent_text for word in ["support", "customer service", "complaint"])
    followup_intent = any(word in current for word in [
        "what next", "what should", "how do we", "how can we", "validate",
        "prioritise", "prioritize", "fix first", "recommend", "action",
        "experiment", "measure", "investigate", "why", "how"
    ])

    funnel_analysis = None
    if product:
        sequential = product.get("sequential_funnel", [])
        meta = product.get("sequential_funnel_meta", {})
        stages = {item["stage"]: item["count"] for item in sequential}
        viewed = stages.get("Product Viewed", 0)
        carted = stages.get("Add To Cart", 0)
        purchased = stages.get("Purchase", 0)
        view_to_cart = round(carted / viewed * 100, 1) if viewed else 0
        cart_to_purchase = round(purchased / carted * 100, 1) if carted else 0
        view_to_purchase = round(purchased / viewed * 100, 1) if viewed else 0
        funnel_analysis = {
            "unit": meta.get("unit", "users"),
            "method": meta.get("method", "ordered_events"),
            "reliability_note": meta.get("reliability_note", ""),
            "stages": [
                {"stage": "Product Viewed", "count": viewed},
                {"stage": "Add To Cart", "count": carted},
                {"stage": "Purchase", "count": purchased},
            ],
            "conversion_rates": {
                "view_to_cart": view_to_cart,
                "cart_to_purchase": cart_to_purchase,
                "view_to_purchase": view_to_purchase,
            },
            "drop_offs": {
                "view_to_cart": max(viewed - carted, 0),
                "cart_to_purchase": max(carted - purchased, 0),
            },
        }

    prioritisation_question = any(phrase in current for phrase in [
        "what should we fix first", "what should we fix", "what to fix first",
        "which issue first", "prioritise the issues", "prioritize the issues",
        "what should we investigate first", "highest priority issue",
    ])

    if prioritisation_question:
        ranked_topics = sorted(
            (voice or {}).get("topics", []),
            key=lambda topic: topic.get("priority_score", 0),
            reverse=True,
        )
        if ranked_topics:
            top = ranked_topics[0]
            findings.append({
                "title": "Highest-priority customer issue",
                "detail": f'{top["label"]} has the highest current heuristic priority score ({top["priority_score"]}/100), based on {top["review_count"]} negative review(s) and an average rating of {top["average_rating"]}/5.',
                "type": "customer_feedback",
            })
            evidence.extend(_evidence_for(voice, top.get("keywords", [])))
            recommendations.append(_recommendation(
                f'Investigate {top["label"]} first',
                "Review the underlying customer report, reproduce the issue where possible, and collect event-level or operational data that measures its frequency and impact before committing to a product fix.",
                f'This issue ranks highest among the themes in the uploaded review sample. The score is a prioritisation heuristic, not proof that it affects the most customers.',
                "Measure issue incidence, affected users or sessions, severity, and the relevant product metric before and after a change. Gather more customer reports to validate the pattern.",
            ))
            answer = f'The first issue to investigate is {top["label"]}, which has the highest heuristic priority score in the uploaded review sample ({top["priority_score"]}/100). It is supported by {top["review_count"]} negative review(s), so treat it as the first investigation candidate—not yet as a proven root cause. Validate its frequency and product impact before deciding on a fix.'
        else:
            answer = "There are no grouped customer pain points available to rank yet. Upload valid customer reviews and rerun the analysis."
        if product and funnel_analysis:
            findings.append({
                "title": "Behavioural context",
                "detail": f'Ordered funnel: {funnel_analysis["stages"][0]["count"]} viewed, {funnel_analysis["stages"][1]["count"]} added to cart, and {funnel_analysis["stages"][2]["count"]} purchased.',
                "type": "metric",
            })
        if history:
            limitations.append("The previous conversation was considered, but issue ranking is recalculated from the currently uploaded datasets.")
        limitations.append("Priority scores are heuristic and the review sample is small; validate the issue with additional evidence before shipping a fix.")

    if checkout_intent:
        if funnel_analysis:
            f = funnel_analysis
            findings.append({
                "title": "Sequential funnel progression",
                "detail": (
                    f'{f["stages"][0]["count"]} {f["unit"]} viewed a product, '
                    f'{f["stages"][1]["count"]} progressed to add-to-cart, and '
                    f'{f["stages"][2]["count"]} progressed to purchase in the required order.'
                ),
                "type": "metric",
            })
            findings.append({
                "title": "Largest observed funnel loss",
                "detail": (
                    f'{f["drop_offs"]["view_to_cart"]} {f["unit"]} did not progress from view to cart; '
                    f'{f["drop_offs"]["cart_to_purchase"]} did not progress from cart to purchase.'
                ),
                "type": "metric",
            })
        if payment:
            findings.append({
                "title": "Payment-related feedback",
                "detail": f'{payment["review_count"]} negative review(s) in {payment["label"]}; average rating {payment["average_rating"]}/5. Priority heuristic: {payment["priority_score"]}/100.',
                "type": "customer_feedback",
            })
            evidence.extend(_evidence_for(voice, ["payment", "transaction", "money", "refund"]))
            recommendations.append(_recommendation(
                "Audit payment failure handling",
                "Instrument payment initiation, gateway response, success, failure, timeout and refund/reversal events. Review gateway error codes and transaction-state reconciliation.",
                "The review dataset contains a payment-related complaint, but the event dataset does not currently record payment failure outcomes.",
                "Track payment success rate, failure rate by gateway/error code, duplicate-charge reports and refund completion time. Compare before and after any fix.",
            ))
        if funnel_analysis and funnel_analysis["drop_offs"]["view_to_cart"] > funnel_analysis["drop_offs"]["cart_to_purchase"]:
            recommendations.append(_recommendation(
                "Investigate product-to-cart friction",
                "Inspect product detail pages, price/fee visibility, stock availability and add-to-cart errors. Break the funnel down by product, device and traffic source.",
                "The ordered funnel currently shows a larger loss before add-to-cart than after cart, if the uploaded session/user key is reliable.",
                "Measure view-to-cart conversion by segment and monitor add-to-cart error events after changes.",
            ))
        else:
            recommendations.append(_recommendation(
                "Investigate cart-to-purchase friction",
                "Review checkout steps, shipping/fee disclosure, payment options and form validation. Add events for checkout start, payment attempt and purchase completion.",
                "The ordered funnel suggests the cart-to-purchase transition deserves inspection; this is a diagnostic lead, not proof of a root cause.",
                "Measure cart-to-purchase conversion and payment success rate by checkout step and segment.",
            ))
        answer = "The ordered funnel provides a better view of progression than independent event counts. Customer reviews also contain a payment-related signal. Together, these identify areas to investigate, but the current datasets do not link reviews to sessions or record payment failures, so they cannot establish the cause of abandonment."
        limitations.append("The review dataset is not linked to event users or sessions; the feedback and behavioural signals are separate sources.")
        if funnel_analysis and funnel_analysis["reliability_note"]:
            limitations.append(funnel_analysis["reliability_note"])

    elif crash_intent:
        if crash:
            findings.append({
                "title": crash["label"],
                "detail": f'{crash["review_count"]} negative review(s); average rating {crash["average_rating"]}/5; {crash["evidence_level"]}.',
                "type": "customer_feedback",
            })
            evidence.extend(_evidence_for(voice, ["crash", "bug", "freeze"]))
            recommendations.append(_recommendation(
                "Add crash telemetry and reproduce reports",
                "Capture crash events, app version, device/OS, screen and anonymised session identifiers. Reproduce the reported failure before prioritising a fix.",
                "Customer feedback reports stability problems, but no crash telemetry is present in the uploaded event data.",
                "Track crash-free sessions/users and crash rate by app version and device; verify the rate falls after a release.",
            ))
        if metrics:
            findings.append({
                "title": "Behavioural context",
                "detail": f'{metrics["total_users"]} users generated {metrics["total_events"]} events. The uploaded event schema contains no crash telemetry.',
                "type": "metric",
            })
        answer = "Customer feedback reports an app-stability issue. The behavioural dataset describes activity but does not measure crashes. Treat these reviews as reports to reproduce and instrument, not as a measured crash rate."
        limitations.append("Crash rate requires crash events or crash-free session telemetry.")

    elif support_intent:
        if support:
            findings.append({
                "title": support["label"],
                "detail": f'{support["review_count"]} negative review(s); average rating {support["average_rating"]}/5; {support["evidence_level"]}.',
                "type": "customer_feedback",
            })
            evidence.extend(_evidence_for(voice, ["support", "customer", "agent", "response"]))
            recommendations.append(_recommendation(
                "Measure support responsiveness",
                "Connect support-ticket data with created_at, first_response_at, resolved_at, status and issue category fields.",
                "The reviews mention support dissatisfaction, but there are no ticket timestamps or resolution records to quantify service performance.",
                "Track first-response time, resolution time, reopen rate and satisfaction by ticket category.",
            ))
        answer = "The reviews contain a customer-support signal worth investigating. The current data does not include ticket timestamps or resolution status, so support performance cannot yet be quantified."
        limitations.append("Support SLA metrics require a support-ticket dataset.")

    else:
        if metrics:
            findings.append({
                "title": "Product activity",
                "detail": f'DAU: {metrics["daily_active_users"]}; MAU: {metrics["monthly_active_users"]}; conversion: {metrics["conversion_rate"]:.2f}%; revenue: ₹{metrics["total_revenue"]:,.0f}.',
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
        answer = "Here is a summary of the uploaded product and customer feedback data. Treat these findings as investigation leads: small samples and co-occurring signals do not establish causation."
        if payment:
            recommendations.append(_recommendation(
                "Validate payment reliability",
                "Add payment attempt and outcome events, then reconcile failures with gateway logs and customer complaints.",
                "A payment-related review exists, but the behavioural dataset cannot currently measure payment reliability.",
                "Monitor payment success rate, failure reasons and refund completion.",
            ))

    if followup_intent and history:
        recommendations.append(_recommendation(
            "Turn the finding into a measurable investigation",
            "Create an event or support-data instrumentation task, define a baseline, and review the metric by product and user segment before shipping a change.",
            "A follow-up question was interpreted using the recent conversation, while recommendations remain grounded in currently uploaded data.",
            "Compare the chosen metric against its baseline and check that the change does not worsen adjacent funnel stages.",
        ))

    if voice and voice["total_reviews"] < 30:
        limitations.append(f'Only {voice["total_reviews"]} reviews are available; sentiment shares and theme frequencies are preliminary, not representative estimates.')
    if product and metrics["total_users"] < 30:
        limitations.append(f'Only {metrics["total_users"]} users are present in the event dataset; funnel percentages may be unstable.')

    return {
        "question": question,
        "answer": answer,
        "findings": findings,
        "evidence": evidence[:8],
        "sources": sources,
        "limitations": list(dict.fromkeys(limitations)),
        "recommendations": recommendations,
        "funnel_analysis": funnel_analysis if checkout_intent else None,
        "context_used": bool(history),
    }
