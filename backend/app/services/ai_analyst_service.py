from app.services.analytics_service import calculate_product_analytics
from app.services.voice_of_customer_service import calculate_voice_of_customer
from app.services.opportunity_service import calculate_product_opportunities
from app.services.document_retrieval_service import retrieve_document_evidence, synthesize_document_answer


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
    document_result = retrieve_document_evidence(question)
    document_evidence = document_result.get("passages", [])\n    document_answer = synthesize_document_answer(question, document_evidence)
    if document_evidence:
        sources.append({
            "name": "Selected product document",
            "detail": f'{document_result.get("document_name", "Document")} · {len(document_evidence)} relevant passage(s) retrieved using local TF-IDF.',
        })
        limitations.extend(document_result.get("limitations", []))
    elif document_result.get("status") not in ("no_documents", "no_active_document"):
        limitations.append(document_result.get("message", "Document retrieval was unavailable."))

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
        if document_evidence:
            answer = (
                document_answer["text"] if document_answer and document_answer.get("status") == "ready"
                else "I found relevant document passages, but could not extract a supported answer from them."
            )
            limitations.append(
                "Document answers are extractive: source lines are selected and quoted, not paraphrased by a generative model."
            )
            limitations.append("Chunk citations identify retrieved text segments, not PDF page numbers.")
            return {
                "question": question, "answer": answer, "findings": [],
                "evidence": [], "sources": sources,
                "limitations": list(dict.fromkeys(limitations)),
                "recommendations": [], "priority_matrix": [],
                "funnel_analysis": None, "context_used": bool(history),
                "document_evidence": document_evidence,\n        "document_answer": document_answer,
                "document_answer": document_answer,
            }
        return {
            "question": question,
            "answer": "I can't analyse this question yet because no valid product event, customer review or searchable document evidence is available. Upload or select a dataset and try again.",
            "findings": [], "evidence": [], "sources": [],
            "limitations": limitations, "recommendations": [],
            "priority_matrix": [], "funnel_analysis": None,
            "context_used": bool(history), "document_evidence": [],
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
        "which product opportunity", "which opportunity", "product opportunity",
        "what opportunity", "which problem should", "what should we investigate",
    ])

    priority_matrix = []
    if voice:
        for topic in voice.get("topics", []):
            count = int(topic.get("review_count", 0))
            rating = float(topic.get("average_rating", 3))
            severity = round(((5 - rating) / 4) * 100)
            evidence_strength = 20 if count == 1 else 45 if count < 5 else 75 if count < 10 else 100
            evidence_label = (
                "Very limited" if count == 1 else
                "Emerging" if count < 5 else
                "Repeated" if count < 10 else "Strong volume"
            )
            quadrant = (
                "Investigate first" if severity >= 70 and evidence_strength >= 45 else
                "Gather more evidence" if severity >= 70 else
                "Validate severity" if evidence_strength >= 45 else
                "Monitor"
            )
            priority_matrix.append({
                "label": topic["label"],
                "review_count": count,
                "average_rating": rating,
                "priority_score": topic.get("priority_score", 0),
                "severity_score": severity,
                "evidence_strength": evidence_strength,
                "evidence_label": evidence_label,
                "quadrant": quadrant,
            })
        priority_matrix.sort(
            key=lambda item: (item["priority_score"], item["severity_score"], item["review_count"]),
            reverse=True,
        )

    if prioritisation_question:
        opportunity_result = {}
        try:
            opportunity_result = calculate_product_opportunities()
        except ValueError as exc:
            limitations.append(str(exc))

        ranked_opportunities = opportunity_result.get("opportunities", [])
        if ranked_opportunities:
            top_opportunity = ranked_opportunities[0]
            customer_signal = top_opportunity["customer_signal"]
            behavior_signal = top_opportunity.get("behavior_signal")
            behavior_detail = (
                behavior_signal["detail"] if behavior_signal
                else "No matching behavioural signal was available."
            )
            answer = (
                f'The strongest cross-source investigation candidate is {top_opportunity["feature"]} '
                f'({top_opportunity["priority"]}). The review sample contains '
                f'{customer_signal["review_count"]} negative review(s) for this theme '
                f'with an average rating of {customer_signal["average_rating"]}/5. '
                f'{behavior_detail} Treat this as a hypothesis to validate, not a proven root cause.'
            )
            findings.append({
                "title": "Top cross-source opportunity: " + top_opportunity["feature"],
                "detail": (
                    f'{top_opportunity["priority"]} · {customer_signal["review_count"]} negative review(s), '
                    f'average rating {customer_signal["average_rating"]}/5. {behavior_detail}'
                ),
                "type": "customer_feedback",
            })
            matching_topic = next(
                (topic for topic in (voice or {}).get("topics", []) if topic.get("key") == top_opportunity["id"]),
                None,
            )
            if matching_topic:
                evidence.extend(_evidence_for(voice, matching_topic.get("keywords", [])))
            recommendations.append(_recommendation(
                "Investigate " + top_opportunity["feature"],
                top_opportunity["recommendation"],
                top_opportunity["confidence_note"],
                "Establish a baseline for the relevant funnel conversion and complaint frequency. "
                "Instrument the suspected failure point, then compare the same metrics after a controlled change.",
            ))
            limitations.append(
                "The cross-source priority is a theme-level heuristic. Reviews are not linked to event users or sessions, "
                "and a behavioural drop-off does not prove that the complaint caused it."
            )
        else:
            ranked_topics = sorted(
                (voice or {}).get("topics", []),
                key=lambda topic: topic.get("priority_score", 0),
                reverse=True,
            )
            if ranked_topics:
                top_score = ranked_topics[0].get("priority_score", 0)
                top_topics = [topic for topic in ranked_topics if topic.get("priority_score", 0) == top_score]
                tie_names = [topic["label"] for topic in top_topics]
                if len(top_topics) > 1:
                    issue_names = " and ".join(tie_names)
                    answer = f'{issue_names} are joint top priorities, each scoring {top_score}/100 in the review sample. The data does not justify choosing one over the other. Investigate both and collect evidence about frequency, severity and affected users before committing to fixes.'
                    findings.append({
                        "title": "Joint highest-priority review themes",
                        "detail": f'{issue_names} are tied at {top_score}/100. Scores are based on the current review sample only.',
                        "type": "customer_feedback",
                    })
                    for topic in top_topics:
                        evidence.extend(_evidence_for(voice, topic.get("keywords", [])))
                        recommendations.append(_recommendation(
                            "Investigate " + topic["label"],
                            "Reproduce the reported issue and collect event-level or operational data to measure its frequency and impact.",
                            f'This review theme is tied at {topic["priority_score"]}/100, a triage heuristic rather than proof of prevalence.',
                            "Measure issue incidence, affected users or sessions, severity and the relevant product metric before and after a change.",
                        ))
                else:
                    top = top_topics[0]
                    answer = f'The highest-ranked review theme is {top["label"]} ({top_score}/100). This is based on {top["review_count"]} negative review(s), so validate its frequency and product impact before choosing a fix.'
                    findings.append({
                        "title": "Highest-priority customer issue",
                        "detail": f'{top["label"]}: {top["review_count"]} negative review(s), average rating {top["average_rating"]}/5.',
                        "type": "customer_feedback",
                    })
                    evidence.extend(_evidence_for(voice, top.get("keywords", [])))
                    recommendations.append(_recommendation(
                        "Investigate " + top["label"],
                        "Reproduce the customer-reported issue and collect event-level or operational data to measure frequency and impact.",
                        "The review theme ranks highest in the uploaded sample; this does not establish prevalence or business impact.",
                        "Measure issue incidence, affected users or sessions, severity and the relevant product metric before and after a change.",
                    ))
            else:
                answer = "There are no grouped customer pain points or cross-source opportunities available to rank yet."
        if product and funnel_analysis:
            findings.append({
                "title": "Behavioural context",
                "detail": f'Ordered funnel: {funnel_analysis["stages"][0]["count"]} viewed, {funnel_analysis["stages"][1]["count"]} added to cart, and {funnel_analysis["stages"][2]["count"]} purchased.',
                "type": "metric",
            })
        if history:
            limitations.append("The previous conversation was considered, but priorities are recalculated from the currently uploaded datasets.")
        limitations.append("Review-only priority matrix scores are heuristic triage aids; cross-source opportunity priority additionally considers a matching behavioural signal. Neither measures business impact.")

    elif checkout_intent:
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

    # Deduplicate repeated review evidence while preserving its original order.
    unique_evidence = []
    seen_evidence = set()
    for item in evidence:
        key = (item.get("rating"), item.get("text", ""))
        if key not in seen_evidence:
            seen_evidence.add(key)
            unique_evidence.append(item)

    return {
        "question": question,
        "answer": answer,
        "findings": findings,
        "evidence": unique_evidence[:8],
        "sources": sources,
        "limitations": list(dict.fromkeys(limitations)),
        "recommendations": recommendations,
        "priority_matrix": priority_matrix,
        "funnel_analysis": funnel_analysis if checkout_intent else None,
        "context_used": bool(history),
        "document_evidence": document_evidence,
    }
