import pandas as pd

from app.services.analytics_service import get_latest_dataset


PURCHASE_EVENTS = {"purchase", "purchased", "order_completed"}
EXCLUDED_DIMENSIONS = {
    "user_id", "event_name", "timestamp", "session_id", "event_id",
    "request_id", "transaction_id", "order_id", "review_id",
}


def _available_dimensions(events):
    dimensions = []
    for column in events.columns:
        if column.lower() in EXCLUDED_DIMENSIONS:
            continue
        values = events[column].dropna().astype(str).str.strip()
        values = values[values.ne("")]
        unique_count = values.nunique()
        if 2 <= unique_count <= 12:
            dimensions.append({
                "key": column,
                "label": column.replace("_", " ").strip().title(),
                "values": int(unique_count),
            })
    return dimensions


def calculate_segment_intelligence(dimension=None):
    """Compare user-level segments inferred from event attributes.

    Each user is assigned to their most frequently observed non-empty value.
    Ties are resolved lexicographically for deterministic results.
    """
    events = get_latest_dataset("events")
    required = {"user_id", "event_name", "timestamp"}
    if not required.issubset(events.columns):
        raise ValueError("The event dataset has an invalid structure.")

    events = events.copy()
    events["user_id"] = events["user_id"].astype(str).str.strip()
    events["event_name"] = events["event_name"].astype(str).str.strip().str.lower()
    events["timestamp"] = pd.to_datetime(events["timestamp"], errors="coerce")
    events = events.dropna(subset=["timestamp"])
    events = events[events["user_id"].ne("")]
    if events.empty:
        raise ValueError("No valid event records were found.")

    dimensions = _available_dimensions(events)
    if not dimensions:
        return {
            "status": "no_dimensions", "dimensions": [],
            "selected_dimension": None, "segments": [],
            "total_users": int(events["user_id"].nunique()),
            "methodology": (
                "No eligible categorical event attributes were found. Add a stable "
                "attribute such as platform, plan, region, or acquisition_channel."
            ),
        }

    selected = dimension or dimensions[0]["key"]
    if selected not in {item["key"] for item in dimensions}:
        raise ValueError("The selected dimension is unavailable or has too many distinct values.")

    tagged = events[["user_id", selected]].copy()
    tagged[selected] = tagged[selected].astype("string").str.strip()
    tagged = tagged.dropna(subset=[selected])
    tagged = tagged[tagged[selected].ne("")]
    if tagged.empty:
        raise ValueError("The selected dimension contains no usable values.")

    counts = (
        tagged.groupby(["user_id", selected], dropna=True).size()
        .rename("observations").reset_index()
        .sort_values(["user_id", "observations", selected],
                     ascending=[True, False, True], kind="mergesort")
    )
    assignments = counts.drop_duplicates("user_id").set_index("user_id")[selected]
    events["segment"] = events["user_id"].map(assignments)
    segmented = events.dropna(subset=["segment"]).copy()

    total_users = int(events["user_id"].nunique())
    purchase_users = set(events.loc[events["event_name"].isin(PURCHASE_EVENTS), "user_id"].unique())
    has_revenue = "revenue" in events.columns
    rows = []
    for value, group in segmented.groupby("segment", sort=True):
        user_count = int(group["user_id"].nunique())
        if not user_count:
            continue
        active_days = group.groupby("user_id")["timestamp"].apply(
            lambda series: series.dt.date.nunique()
        )
        repeat_users = int((active_days >= 2).sum())
        users = set(group["user_id"].unique())
        converted_users = len(users.intersection(purchase_users))
        row = {
            "segment": str(value), "users": user_count,
            "user_share": round(user_count / total_users * 100, 1) if total_users else 0,
            "events": int(len(group)),
            "events_per_user": round(len(group) / user_count, 2),
            "repeat_users": repeat_users,
            "repeat_user_rate": round(repeat_users / user_count * 100, 1),
            "purchasing_users": int(converted_users),
            "purchase_user_rate": round(converted_users / user_count * 100, 1),
        }
        if has_revenue:
            revenue = pd.to_numeric(
                group.loc[group["event_name"].isin(PURCHASE_EVENTS), "revenue"],
                errors="coerce",
            ).fillna(0)
            row["purchase_revenue"] = round(float(revenue.sum()), 2)
            row["revenue_per_user"] = round(float(revenue.sum()) / user_count, 2)
        rows.append(row)

    rows.sort(key=lambda item: (item["users"], item["segment"]), reverse=True)
    return {
        "status": "ready", "dimensions": dimensions,
        "selected_dimension": selected, "total_users": total_users,
        "period": {
            "start_date": events["timestamp"].min().strftime("%Y-%m-%d"),
            "end_date": events["timestamp"].max().strftime("%Y-%m-%d"),
        },
        "segments": rows,
        "methodology": (
            "Each user is assigned to the most frequently observed non-empty value "
            "of the selected event attribute; ties use alphabetical order. Metrics "
            "are descriptive. Purchase-user rate is the share of assigned users with "
            "at least one purchase event anywhere in the observed dataset. Revenue "
            "metrics appear only when a revenue column is available."
        ),
    }