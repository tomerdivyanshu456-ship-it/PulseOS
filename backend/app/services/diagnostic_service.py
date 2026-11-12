"""Evidence-led diagnostic hypotheses assembled from existing PulseOS analyses.

Signals are associations in uploaded observational data, not causal explanations.
"""
from app.services.journey_service import calculate_journey_intelligence
from app.services.opportunity_service import calculate_product_opportunities
from app.services.experiment_service import list_experiments


def _safe(source, function, gaps):
    try:
        return function()
    except (ValueError, KeyError, TypeError) as exc:
        gaps.append(f"{source}: {exc}")
        return None


def build_root_cause_diagnostics():
    gaps = []
    journey = _safe("Funnel analysis unavailable", calculate_journey_intelligence, gaps)
    if journey and not journey.get("segment_funnels") and journey.get("dimensions"):
        dimension = journey["dimensions"][0].get("key")
        if dimension:
            journey = _safe("Segment comparison unavailable", lambda: calculate_journey_intelligence(dimension=dimension), gaps)
    opportunities = _safe("Customer/opportunity analysis unavailable", calculate_product_opportunities, gaps)
    experiments = _safe("Experiment register unavailable", list_experiments, gaps) or []

    hypotheses = []
    funnel = (journey or {}).get("funnel", [])
    for index, step in enumerate(funnel[1:], start=1):
        dropped = int(step.get("drop_off_units", 0) or 0)
        rate = float(step.get("drop_off_rate", 0) or 0)
        if dropped <= 0:
            continue
        previous = funnel[index - 1]
        hypotheses.append({
            "id": f"funnel-{index}",
            "title": f"Investigate the {previous['event_name']} → {step['event_name']} transition",
            "signal_type": "Funnel drop-off",
            "priority_score": round(min(100, rate * 0.7 + min(dropped, 100) * 0.3), 1),
            "severity": "High" if rate >= 50 else "Medium" if rate >= 20 else "Low",
            "observation": (
                f"{dropped} {journey.get('unit', 'units')} did not reach "
                f"{step['event_name']} after reaching {previous['event_name']} "
                f"({rate:.1f}% drop-off from the preceding step)."
            ),
            "evidence": [
                {"label": f"{previous['event_name']} reached", "value": int(previous.get("units_reached", 0))},
                {"label": f"{step['event_name']} reached", "value": int(step.get("units_reached", 0))},
                {"label": "Drop-off rate", "value": rate, "unit": "%"},
            ],
            "customer_context": None,
            "segment_context": None,
            "experiment_context": [],
            "next_steps": [
                f"Inspect errors, latency and validation failures between {previous['event_name']} and {step['event_name']}.",
                "Break the transition down by platform, app version, plan and acquisition channel where those fields are tracked.",
                "Review session recordings or conduct usability tests before changing the flow.",
            ],
            "caveat": "The funnel identifies where progression stops; it does not reveal why users stopped.",
        })

    opportunity_rows = (opportunities or {}).get("opportunities", [])
    for item in opportunity_rows:
        behavior = item.get("behavior_signal")
        customer = item.get("customer_signal") or {}
        if not customer and not behavior:
            continue
        evidence = []
        if customer:
            evidence.extend([
                {"label": "Reviews in theme", "value": int(customer.get("review_count", 0))},
                {"label": "Average rating", "value": customer.get("average_rating"), "unit": "/ 5"},
            ])
        if behavior:
            evidence.append({"label": behavior.get("label", "Behaviour signal"), "value": behavior.get("value"), "unit": behavior.get("unit", "")})
        hypotheses.append({
            "id": f"feedback-{item.get('id', len(hypotheses))}",
            "title": f"Validate friction in {item.get('feature', 'this product area')}",
            "signal_type": "Customer feedback",
            "priority_score": round(min(100, float(item.get("priority_score", 0) or 0) * 0.65 + float(item.get("severity_score", 0) or 0) * 0.35), 1),
            "severity": item.get("priority", "Validate"),
            "observation": (
                f"{customer.get('review_count', 0)} reviews mention {customer.get('topic', item.get('feature', 'this theme'))}; "
                + (behavior.get("detail", "") if behavior else "No matching behavioural signal was available.")
            ),
            "evidence": evidence,
            "customer_context": customer.get("evidence", [])[:2],
            "segment_context": None,
            "experiment_context": [],
            "next_steps": [
                item.get("recommendation", "Inspect the affected product journey and validate the customer problem."),
                "Check whether the same issue appears in support tickets and qualitative user research.",
                "Define a measurable success metric and guardrails before running an experiment.",
            ],
            "caveat": item.get("confidence_note", "Feedback themes and event metrics may come from separate datasets and are not user-level joined."),
        })

    segment_context = []
    if journey and journey.get("segment_funnels"):
        for segment in journey["segment_funnels"]:
            values = segment.get("funnel", [])
            first = int(values[0].get("units_reached", 0)) if values else 0
            last = int(values[-1].get("units_reached", 0)) if values else 0
            if first:
                segment_context.append({
                    "segment": segment.get("segment"),
                    "units": int(segment.get("units", 0)),
                    "entry_to_completion_rate": round(last / first * 100, 1),
                })
        eligible = [row for row in segment_context if row["units"] >= 3]
        if len(eligible) >= 2:
            ranked = sorted(eligible, key=lambda row: row["entry_to_completion_rate"])
            spread = ranked[-1]["entry_to_completion_rate"] - ranked[0]["entry_to_completion_rate"]
            if spread >= 10:
                hypotheses.append({
                    "id": "segment-gap",
                    "title": "Investigate the segment conversion gap",
                    "signal_type": "Segment disparity",
                    "priority_score": round(min(100, spread), 1),
                    "severity": "High" if spread >= 25 else "Medium",
                    "observation": f"Entry-to-completion conversion differs by {spread:.1f} percentage points between {ranked[0]['segment']} ({ranked[0]['entry_to_completion_rate']:.1f}%) and {ranked[-1]['segment']} ({ranked[-1]['entry_to_completion_rate']:.1f}%).",
                    "evidence": [
                        {"label": f"{ranked[0]['segment']} conversion", "value": ranked[0]["entry_to_completion_rate"], "unit": "%"},
                        {"label": f"{ranked[-1]['segment']} conversion", "value": ranked[-1]["entry_to_completion_rate"], "unit": "%"},
                        {"label": "Gap", "value": round(spread, 1), "unit": "pp"},
                    ],
                    "customer_context": None,
                    "segment_context": ranked,
                    "experiment_context": [],
                    "next_steps": ["Compare device, geography, acquisition mix and sample sizes across these segments.", "Inspect the lowest-converting segment's event sequence and error rates.", "Validate the pattern over another time window before prioritising a segment-specific change."],
                    "caveat": "Segment membership is assigned from the most frequently observed attribute value; small samples and composition differences can create apparent gaps.",
                })

    for hypothesis in hypotheses:
        linked = [
            {"name": exp.get("name"), "status": exp.get("status"), "primary_metric": exp.get("primary_metric")}
            for exp in experiments
            if exp.get("opportunity_id") and exp.get("opportunity_id") in hypothesis["id"]
        ]
        hypothesis["experiment_context"] = linked

    hypotheses.sort(key=lambda row: (-row["priority_score"], row["title"]))
    sources = {
        "events": journey is not None,
        "reviews": bool((opportunities or {}).get("sources", {}).get("reviews")),
        "experiments": bool(experiments),
    }
    if not hypotheses:
        status = "no_data" if not any(sources.values()) else "no_signals"
    else:
        status = "ready" if all(sources.values()) else "partial"

    return {
        "status": status,
        "summary": {
            "hypotheses": len(hypotheses),
            "high_priority": sum(1 for item in hypotheses if item["severity"] == "High"),
            "funnel_signals": sum(1 for item in hypotheses if item["signal_type"] == "Funnel drop-off"),
            "customer_signals": sum(1 for item in hypotheses if item["signal_type"] == "Customer feedback"),
        },
        "hypotheses": hypotheses,
        "segment_comparison": segment_context,
        "data_gaps": gaps,
        "sources": sources,
        "methodology": "PulseOS assembles hypotheses from ordered funnel drop-offs, review-theme opportunities and segment conversion disparities. Experiment records are contextual planning metadata only; stored experiment results are not inferred. Signals may originate from separate datasets and are not joined at user level. These are observational associations, not root-cause proof, causal estimates or automatic recommendations to ship changes.",
    }
