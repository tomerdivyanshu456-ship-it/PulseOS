"""Experiment planning and descriptive analysis for PulseOS."""
import json
import math
import uuid
import pandas as pd
from datetime import datetime, timezone

from app.services.analytics_service import get_latest_dataset
from app.services.dataset_service import get_connection


DEFAULT_METRIC_PLAN = {
    "primary": {"name": "Primary conversion rate", "definition": "Users completing the target action divided by eligible users.", "type": "binary"},
    "secondary": [
        {"name": "Engagement rate", "definition": "Eligible users completing a meaningful engagement event."},
        {"name": "Repeat usage rate", "definition": "Eligible users returning to use the feature again."},
    ],
    "guardrails": [
        {"name": "Crash/error rate", "direction": "must not increase"},
        {"name": "Refund/cancellation rate", "direction": "must not increase"},
        {"name": "Page or task latency", "direction": "must not materially increase"},
    ],
}


def _ensure_experiments_table():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, opportunity_id TEXT,
                opportunity_title TEXT, hypothesis TEXT NOT NULL, rationale TEXT NOT NULL,
                primary_metric TEXT NOT NULL, secondary_metrics TEXT NOT NULL,
                guardrails TEXT NOT NULL, baseline_rate REAL NOT NULL,
                minimum_detectable_effect REAL NOT NULL, confidence_level REAL NOT NULL,
                power REAL NOT NULL, sample_size_per_arm INTEGER NOT NULL,
                duration_days INTEGER NOT NULL, status TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )
        """)


def calculate_sample_size(baseline_rate, minimum_detectable_effect,
                          confidence_level=0.95, power=0.80,
                          daily_eligible_users=1000):
    """Normal-approximation estimate for equal-sized, independent binary arms."""
    values = (baseline_rate, minimum_detectable_effect, confidence_level, power)
    try:
        finite = all(math.isfinite(float(value)) for value in values)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Inputs must be finite numbers.") from exc
    if not finite:
        raise ValueError("Inputs must be finite numbers.")
    if not 0 < baseline_rate < 1:
        raise ValueError("Baseline conversion must be between 0 and 1 (exclusive).")
    if not 0 < minimum_detectable_effect < 1:
        raise ValueError("Minimum detectable effect must be between 0 and 1.")
    if baseline_rate + minimum_detectable_effect >= 1:
        raise ValueError("Baseline plus the expected lift must be below 1.")
    if confidence_level not in (0.90, 0.95, 0.99):
        raise ValueError("Confidence level must be 0.90, 0.95 or 0.99.")
    if power not in (0.80, 0.90):
        raise ValueError("Power must be 0.80 or 0.90.")
    try:
        valid_daily_users = (not isinstance(daily_eligible_users, bool)
                             and math.isfinite(float(daily_eligible_users))
                             and float(daily_eligible_users).is_integer()
                             and int(daily_eligible_users) >= 1)
    except (TypeError, ValueError, OverflowError):
        valid_daily_users = False
    if not valid_daily_users:
        raise ValueError("Daily eligible users must be a positive integer.")
    z_alpha = {0.90: 1.644854, 0.95: 1.959964, 0.99: 2.575829}[confidence_level]
    z_power = {0.80: 0.841621, 0.90: 1.281552}[power]
    p1, p2 = baseline_rate, baseline_rate + minimum_detectable_effect
    pooled = (p1 + p2) / 2
    numerator = (
        z_alpha * math.sqrt(2 * pooled * (1 - pooled))
        + z_power * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    ) ** 2
    per_arm = math.ceil(numerator / minimum_detectable_effect ** 2)
    total = per_arm * 2
    return {
        "sample_size_per_arm": per_arm,
        "total_sample_size": total,
        "daily_eligible_users": int(daily_eligible_users),
        "estimated_duration_days": math.ceil(total / int(daily_eligible_users)),
        "confidence_level": confidence_level,
        "power": power,
        "mde_absolute_percentage_points": round(minimum_detectable_effect * 100, 3),
        "method": "normal approximation for two independent proportions; equal allocation; two-sided test.",
        "caveats": [
            "Planning estimate, not a guarantee of statistical validity.",
            "Assumes independent eligible users, stable allocation and one primary binary metric.",
            "Does not adjust for clustering, repeated exposure, multiple comparisons or attrition.",
            "Allow at least one full weekly cycle and account for seasonality.",
        ],
    }


def generate_experiment_plan(opportunity):
    feature = opportunity.get("feature") or opportunity.get("title") or "the selected product area"
    customer = opportunity.get("customer_signal") or {}
    behavior = opportunity.get("behavior_signal")
    count = int(customer.get("review_count", 0))
    rating = customer.get("average_rating")
    context = behavior.get("detail") if isinstance(behavior, dict) else "No matching behavioural signal is currently available."
    evidence = f"{count} review(s), average rating {rating}/5." if rating is not None else f"{count} customer review(s)."
    return {
        "name": f"Reduce friction in {feature}",
        "hypothesis": (
            f"If we improve the {feature.lower()} journey, then the share of eligible users "
            "completing its target action will increase, because current customer feedback indicates friction."
        ),
        "rationale": f"Observed customer signal: {evidence} Behavioural context: {context}",
        "primary_metric": DEFAULT_METRIC_PLAN["primary"],
        "secondary_metrics": DEFAULT_METRIC_PLAN["secondary"],
        "guardrails": DEFAULT_METRIC_PLAN["guardrails"],
        "design": {
            "type": "A/B test", "control": "Current experience",
            "variant": "One clearly scoped change addressing the selected friction",
            "allocation": "50/50 random assignment at a stable user-level identifier",
            "unit": "Unique eligible user",
            "duration_guidance": "Run until the pre-calculated sample is reached and at least one full weekly cycle has elapsed. Do not stop early based on interim significance.",
            "exclusions": ["Internal/test accounts", "Users without a valid assignment", "Duplicate user identifiers"],
        },
        "evidence_note": (
            "This is a testable hypothesis generated from theme-level signals. Reviews and event aggregates "
            "are not joined at user/session level; the suggested relationship is not causal evidence."
        ),
    }


def create_experiment(payload):
    _ensure_experiments_table()
    estimate = calculate_sample_size(
        float(payload["baseline_rate"]), float(payload["minimum_detectable_effect"]),
        float(payload.get("confidence_level", 0.95)), float(payload.get("power", 0.80)),
        int(payload.get("daily_eligible_users", 1000)),
    )
    status = payload.get("status", "draft")
    if status not in ("draft", "running", "completed", "archived"):
        raise ValueError("Invalid experiment status.")
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "id": str(uuid.uuid4()), "name": payload["name"].strip(),
        "opportunity_id": payload.get("opportunity_id"),
        "opportunity_title": payload.get("opportunity_title"),
        "hypothesis": payload["hypothesis"].strip(),
        "rationale": payload.get("rationale", "").strip(),
        "primary_metric": payload["primary_metric"].strip(),
        "secondary_metrics": payload.get("secondary_metrics", []),
        "guardrails": payload.get("guardrails", []),
        "baseline_rate": float(payload["baseline_rate"]),
        "minimum_detectable_effect": float(payload["minimum_detectable_effect"]),
        "confidence_level": float(payload.get("confidence_level", 0.95)),
        "power": float(payload.get("power", 0.80)),
        "sample_size_per_arm": estimate["sample_size_per_arm"],
        "duration_days": estimate["estimated_duration_days"], "status": status,
        "created_at": now, "updated_at": now, "sample_size": estimate,
    }
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO experiments (
                id, name, opportunity_id, opportunity_title, hypothesis, rationale,
                primary_metric, secondary_metrics, guardrails, baseline_rate,
                minimum_detectable_effect, confidence_level, power,
                sample_size_per_arm, duration_days, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record["id"], record["name"], record["opportunity_id"], record["opportunity_title"],
            record["hypothesis"], record["rationale"], record["primary_metric"],
            json.dumps(record["secondary_metrics"]), json.dumps(record["guardrails"]),
            record["baseline_rate"], record["minimum_detectable_effect"], record["confidence_level"],
            record["power"], record["sample_size_per_arm"], record["duration_days"],
            record["status"], now, now,
        ))
    return record


def _row_to_dict(row):
    item = dict(row)
    item["secondary_metrics"] = json.loads(item["secondary_metrics"])
    item["guardrails"] = json.loads(item["guardrails"])
    return item


def list_experiments():
    _ensure_experiments_table()
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM experiments ORDER BY created_at DESC").fetchall()
    return [_row_to_dict(row) for row in rows]


def update_experiment_status(experiment_id, status):
    if status not in ("draft", "running", "completed", "archived"):
        raise ValueError("Invalid experiment status.")
    _ensure_experiments_table()
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE experiments SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, experiment_id),
        )
        if cursor.rowcount == 0:
            return None
        row = connection.execute("SELECT * FROM experiments WHERE id = ?", (experiment_id,)).fetchone()
    return _row_to_dict(row)


def wilson_interval(successes, trials, confidence_level=0.95):
    if (isinstance(successes, bool) or isinstance(trials, bool)
            or not isinstance(successes, int) or not isinstance(trials, int)):
        raise ValueError("Counts must be integers.")
    if trials <= 0 or successes < 0 or successes > trials:
        raise ValueError("Each arm needs valid counts with 0 <= conversions <= users.")
    z = {0.90: 1.644854, 0.95: 1.959964, 0.99: 2.575829}.get(confidence_level)
    if z is None:
        raise ValueError("Confidence level must be 0.90, 0.95 or 0.99.")
    p = successes / trials
    denom = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denom
    margin = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def analyze_experiment(payload):
    cu, cc = int(payload["control_users"]), int(payload["control_conversions"])
    vu, vc = int(payload["variant_users"]), int(payload["variant_conversions"])
    if cu <= 0 or vu <= 0 or cc < 0 or vc < 0 or cc > cu or vc > vu:
        raise ValueError("Each arm needs positive users and conversions between zero and users.")
    confidence = float(payload.get("confidence_level", 0.95))
    c_low, c_high = wilson_interval(cc, cu, confidence)
    v_low, v_high = wilson_interval(vc, vu, confidence)
    c_rate, v_rate = cc / cu, vc / vu
    absolute = v_rate - c_rate
    relative = absolute / c_rate * 100 if c_rate else None
    z = {0.90: 1.644854, 0.95: 1.959964, 0.99: 2.575829}.get(confidence)
    if z is None:
        raise ValueError("Confidence level must be 0.90, 0.95 or 0.99.")
    se = math.sqrt(c_rate * (1 - c_rate) / cu + v_rate * (1 - v_rate) / vu)
    low, high = absolute - z * se, absolute + z * se
    planned = payload.get("planned_sample_size_per_arm")
    if planned is not None and (isinstance(planned, bool) or not isinstance(planned, int) or planned < 1):
        raise ValueError("Planned sample size per arm must be a positive integer.")
    sample_reached = (cu >= planned and vu >= planned) if planned else None
    guardrail_results = []
    for item in payload.get("guardrails", []):
        baseline, variant = float(item["control_rate"]), float(item["variant_rate"])
        threshold = float(item.get("max_increase", 0))
        if not all(math.isfinite(value) for value in (baseline, variant, threshold)) or not 0 <= baseline <= 1 or not 0 <= variant <= 1 or not 0 <= threshold <= 1:
            raise ValueError("Guardrail rates and thresholds must be finite values between 0 and 1.")
        change = variant - baseline
        guardrail_results.append({
            "name": item["name"], "control_rate": baseline, "variant_rate": variant,
            "absolute_change": change,
            "status": "review" if change > threshold else "within_threshold",
            "threshold": threshold,
        })
    interpretation = (
        "The observed variant rate is higher; the approximate difference interval includes zero."
        if absolute > 0 and low <= 0 <= high else
        "The observed variant rate is lower; the approximate difference interval includes zero."
        if absolute < 0 and low <= 0 <= high else
        "The approximate difference interval excludes zero. Verify randomisation, instrumentation and assumptions."
        if low > 0 or high < 0 else "The observed rates are equal in this sample."
    )
    return {
        "control": {"users": cu, "conversions": cc, "conversion_rate": c_rate, "confidence_interval": [c_low, c_high]},
        "variant": {"users": vu, "conversions": vc, "conversion_rate": v_rate, "confidence_interval": [v_low, v_high]},
        "absolute_lift": absolute, "relative_lift_percent": relative,
        "difference_confidence_interval": [low, high],
        "sample_size_reached": sample_reached, "guardrails": guardrail_results,
        "interpretation": interpretation,
        "methodology": (
            "Descriptive two-arm comparison. Arm intervals use Wilson score intervals; the difference interval "
            "is an unpooled normal approximation. This is not a pre-registered statistical analysis and does not prove causality."
        ),
    }



def analyze_experiment_from_events(experiment_id, exposure_event, conversion_event, guardrails=None):
    """Build a user-level experiment comparison from explicitly tagged exposure events."""
    exposure_event = str(exposure_event or "").strip().lower()
    conversion_event = str(conversion_event or "").strip().lower()
    if not exposure_event or not conversion_event:
        raise ValueError("Exposure event and conversion event are required.")
    if exposure_event == conversion_event:
        raise ValueError("Exposure and conversion events must be different.")

    _ensure_experiments_table()
    with get_connection() as connection:
        experiment = connection.execute(
            "SELECT * FROM experiments WHERE id = ?", (experiment_id,)
        ).fetchone()
    if experiment is None:
        raise LookupError("Experiment not found.")

    events = get_latest_dataset("events").copy()
    required = {"user_id", "event_name", "timestamp", "experiment_id", "experiment_variant"}
    missing = sorted(required.difference(events.columns))
    if missing:
        raise ValueError(
            "The uploaded events CSV needs these additional experiment columns: "
            + ", ".join(missing)
            + ". Tag each experiment exposure row with experiment_id and experiment_variant."
        )

    events["user_id"] = events["user_id"].astype(str).str.strip()
    events["event_name"] = events["event_name"].astype(str).str.strip().str.lower()
    events["timestamp"] = pd.to_datetime(events["timestamp"], errors="coerce", utc=True)
    events = events.dropna(subset=["timestamp"])
    events = events[events["user_id"].ne("")].copy()
    if events.empty:
        raise ValueError("The uploaded events CSV contains no valid user/timestamp records.")

    tagged = events[
        events["experiment_id"].astype(str).str.strip().eq(str(experiment_id))
    ].copy()
    if tagged.empty:
        raise ValueError(
            "No event rows match this experiment ID. Add tagged exposure rows for the selected experiment."
        )

    tagged["experiment_variant"] = (
        tagged["experiment_variant"].astype(str).str.strip().str.lower()
    )
    exposure_rows = tagged[
        tagged["event_name"].eq(exposure_event)
        & tagged["experiment_variant"].isin(["control", "variant"])
    ].copy()
    if exposure_rows.empty:
        raise ValueError(
            f"No valid '{exposure_event}' exposure rows with control/variant assignments were found."
        )

    variant_counts = exposure_rows.groupby("user_id")["experiment_variant"].nunique()
    conflicting_users = set(variant_counts[variant_counts > 1].index)
    valid_exposures = exposure_rows[
        ~exposure_rows["user_id"].isin(conflicting_users)
    ].sort_values("timestamp").drop_duplicates("user_id", keep="first")
    if valid_exposures.empty:
        raise ValueError("No users have a consistent experiment assignment.")

    exposure_map = valid_exposures.set_index("user_id")[["experiment_variant", "timestamp"]]
    exposed_users = set(exposure_map.index)
    if exposure_map["experiment_variant"].nunique() < 2:
        raise ValueError("Both control and variant need at least one valid exposed user.")

    def converted_users(event_name):
        matching = events[
            events["user_id"].isin(exposed_users)
            & events["event_name"].eq(event_name)
        ][["user_id", "timestamp"]].drop_duplicates()
        if matching.empty:
            return set()
        joined = matching.join(exposure_map[["timestamp"]].rename(columns={"timestamp": "exposed_at"}), on="user_id")
        return set(joined.loc[joined["timestamp"] >= joined["exposed_at"], "user_id"].unique())

    conversion_users = converted_users(conversion_event)
    counts = {}
    for arm in ("control", "variant"):
        arm_users = set(
            exposure_map.index[exposure_map["experiment_variant"].eq(arm)]
        )
        counts[f"{arm}_users"] = len(arm_users)
        counts[f"{arm}_conversions"] = len(arm_users.intersection(conversion_users))

    guardrail_inputs = []
    for item in guardrails or []:
        name = str(item.get("name") or "").strip()
        event_name = str(item.get("event_name") or "").strip().lower()
        threshold = float(item.get("max_increase", 0))
        if not name or not event_name:
            raise ValueError("Each guardrail needs a name and an event name.")
        if not math.isfinite(threshold) or not 0 <= threshold <= 1:
            raise ValueError("Guardrail maximum increase must be between 0 and 1.")
        affected_users = converted_users(event_name)
        guardrail_inputs.append({
            "name": name,
            "control_rate": len(
                affected_users.intersection(set(exposure_map.index[exposure_map["experiment_variant"].eq("control")]))
            ) / counts["control_users"],
            "variant_rate": len(
                affected_users.intersection(set(exposure_map.index[exposure_map["experiment_variant"].eq("variant")]))
            ) / counts["variant_users"],
            "max_increase": threshold,
        })

    analysis = analyze_experiment({
        **counts,
        "confidence_level": float(experiment["confidence_level"]),
        "planned_sample_size_per_arm": int(experiment["sample_size_per_arm"]),
        "guardrails": guardrail_inputs,
    })

    lower, upper = analysis["difference_confidence_interval"]
    guardrail_regressions = [
        item for item in analysis["guardrails"] if item["status"] == "review"
    ]
    if guardrail_regressions:
        recommendation = "Stop"
        reasons = [
            "At least one configured guardrail exceeded its allowed absolute increase; pause and investigate before rollout."
        ]
    elif upper < 0:
        recommendation = "Stop"
        reasons = [
            "The approximate confidence interval for the primary-metric difference is entirely below zero."
        ]
    elif analysis["sample_size_reached"] and lower > 0 and guardrail_inputs:
        recommendation = "Ship"
        reasons = [
            "The planned sample size has been reached in both arms.",
            "The approximate confidence interval for the primary-metric lift is entirely above zero.",
            "No configured guardrail exceeded its allowed increase.",
        ]
    else:
        recommendation = "Iterate"
        reasons = []
        if not analysis["sample_size_reached"]:
            reasons.append("The planned sample size has not yet been reached in both arms.")
        if lower <= 0 <= upper:
            reasons.append("The approximate confidence interval includes zero, so the primary-metric result is inconclusive.")
        if not guardrail_inputs:
            reasons.append("No guardrail event was supplied; configure at least one guardrail before considering rollout.")
        if not reasons:
            reasons.append("The evidence does not meet the configured criteria for rollout or stopping.")

    return {
        "experiment_id": experiment_id,
        "experiment_name": experiment["name"],
        "recommendation": recommendation,
        "reasons": reasons,
        "analysis": analysis,
        "events": {
            "exposure_event": exposure_event,
            "conversion_event": conversion_event,
            "source_rows": int(len(events)),
            "tagged_exposure_rows": int(len(exposure_rows)),
            "exposed_users": int(len(exposure_map)),
            "conflicting_assignment_users_excluded": int(len(conflicting_users)),
        },
        "guardrail_note": (
            "Guardrail flags compare observed user rates with user-specified absolute thresholds. "
            "They are screening signals, not separate statistical tests."
        ),
        "limitations": [
            "Only users with a tagged exposure event are included in the denominator.",
            "Conversion and guardrail events are counted once per exposed user and must occur at or after exposure.",
            "The analysis assumes stable user-level assignment and complete event instrumentation.",
            "The recommendation is a decision aid, not proof of causality or an automatic deployment command.",
        ],
    }
