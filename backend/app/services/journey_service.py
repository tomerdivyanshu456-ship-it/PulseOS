from collections import Counter
import pandas as pd

from app.services.analytics_service import get_latest_dataset
from app.services.segment_service import _available_dimensions


DEFAULT_STEP_GROUPS = (
    ("product_viewed", "view_product", "product_view"),
    ("add_to_cart", "cart_add"),
    ("purchase", "purchased", "order_completed"),
)


def _unit_key(row, use_sessions):
    if use_sessions and pd.notna(row.get("session_id")) and str(row.get("session_id")).strip():
        return f"session:{row['user_id']}:{str(row['session_id']).strip()}"
    return f"user:{row['user_id']}"


def _ordered_stage_counts(names, steps):
    counts = [0] * len(steps)
    for sequence in names:
        next_stage = 0
        for event_name in sequence:
            if next_stage < len(steps) and event_name == steps[next_stage]:
                counts[next_stage] += 1
                next_stage += 1
                if next_stage == len(steps):
                    break
    return counts


def _compress_path(names, limit=6):
    compressed = []
    for name in names:
        if not compressed or compressed[-1] != name:
            compressed.append(name)
        if len(compressed) >= limit:
            break
    return compressed


def calculate_journey_intelligence(steps=None, dimension=None):
    """Analyse ordered event progression and common paths within sessions/users."""
    events = get_latest_dataset("events")
    required = {"user_id", "event_name", "timestamp"}
    if not required.issubset(events.columns):
        raise ValueError("The event dataset has an invalid structure.")

    events = events.copy()
    events["user_id"] = events["user_id"].astype("string").str.strip()
    events["event_name"] = events["event_name"].astype(str).str.strip().str.lower()
    events["timestamp"] = pd.to_datetime(events["timestamp"], errors="coerce")
    events = events.dropna(subset=["user_id", "timestamp"])
    events = events[events["user_id"].ne("")]
    events = events[events["event_name"].ne("")]
    if events.empty:
        raise ValueError("No valid event records were found.")

    event_counts = events["event_name"].value_counts()
    event_catalog = [
        {"event_name": str(name), "event_count": int(count)}
        for name, count in event_counts.head(30).items()
    ]
    available_events = set(event_counts.index)

    if steps is None:
        selected_steps = []
        for aliases in DEFAULT_STEP_GROUPS:
            match = next((alias for alias in aliases if alias in available_events), None)
            if match:
                selected_steps.append(match)
        if len(selected_steps) < 2:
            selected_steps = [str(name) for name in event_counts.head(3).index]
    else:
        selected_steps = [str(item).strip().lower() for item in steps if str(item).strip()]
        if not 2 <= len(selected_steps) <= 6:
            raise ValueError("Choose between 2 and 6 funnel events.")
        if len(set(selected_steps)) != len(selected_steps):
            raise ValueError("Funnel events must be unique.")
        unknown = [item for item in selected_steps if item not in available_events]
        if unknown:
            raise ValueError("One or more selected funnel events are not present in the dataset.")

    if len(selected_steps) < 2:
        return {
            "status": "insufficient_events",
            "event_catalog": event_catalog,
            "dimensions": _available_dimensions(events),
            "selected_dimension": None,
            "steps": selected_steps,
            "funnel": [],
            "journey_paths": [],
            "unit": "sessions" if "session_id" in events.columns else "users",
            "methodology": "At least two distinct event types are required to analyse a journey.",
        }

    dimensions = _available_dimensions(events)
    use_sessions = "session_id" in events.columns
    events["_unit"] = events.apply(lambda row: _unit_key(row, use_sessions), axis=1)
    events = events.sort_values(["_unit", "timestamp"], kind="mergesort")
    sequences = {
        unit: group["event_name"].tolist()
        for unit, group in events.groupby("_unit", sort=False)
    }
    total_units = len(sequences)
    stage_counts = _ordered_stage_counts(list(sequences.values()), selected_steps)

    funnel = []
    previous = None
    for index, (event_name, reached) in enumerate(zip(selected_steps, stage_counts)):
        entered = reached if index == 0 else previous
        dropped = max(0, entered - reached)
        funnel.append({
            "step": index + 1,
            "event_name": event_name,
            "units_reached": reached,
            "drop_off_units": dropped,
            "conversion_from_previous": round(reached / entered * 100, 1) if entered else 0,
            "drop_off_rate": round(dropped / entered * 100, 1) if entered else 0,
            "conversion_from_entry": round(reached / stage_counts[0] * 100, 1) if stage_counts[0] else 0,
        })
        previous = reached

    path_counts = Counter(
        " → ".join(_compress_path(names))
        for names in sequences.values()
        if names
    )
    journey_paths = [
        {
            "path": path,
            "units": int(count),
            "share": round(count / total_units * 100, 1) if total_units else 0,
        }
        for path, count in path_counts.most_common(8)
    ]

    selected_dimension = dimension or None
    segment_funnels = []
    if selected_dimension:
        if selected_dimension not in {item["key"] for item in dimensions}:
            raise ValueError("The selected segment dimension is unavailable.")
        tagged = events[["user_id", selected_dimension]].copy()
        tagged[selected_dimension] = tagged[selected_dimension].astype("string").str.strip()
        tagged = tagged.dropna(subset=[selected_dimension])
        tagged = tagged[tagged[selected_dimension].ne("")]
        assignments = (
            tagged.groupby(["user_id", selected_dimension], dropna=True).size()
            .rename("observations").reset_index()
            .sort_values(["user_id", "observations", selected_dimension],
                         ascending=[True, False, True], kind="mergesort")
            .drop_duplicates("user_id")
            .set_index("user_id")[selected_dimension]
        )
        events["_segment"] = events["user_id"].map(assignments)
        unit_segments = events.dropna(subset=["_segment"]).groupby("_unit")["_segment"].first()
        unit_users = events.groupby("_unit")["user_id"].first()
        for segment_value in sorted(unit_segments.unique().tolist(), key=str):
            matching_units = [
                unit for unit, value in unit_segments.items()
                if value == segment_value and unit in sequences
            ]
            counts = _ordered_stage_counts([sequences[unit] for unit in matching_units], selected_steps)
            segment_funnels.append({
                "segment": str(segment_value),
                "units": len(matching_units),
                "funnel": [
                    {"event_name": event_name, "units_reached": count}
                    for event_name, count in zip(selected_steps, counts)
                ],
            })

    return {
        "status": "ready",
        "period": {
            "start_date": events["timestamp"].min().strftime("%Y-%m-%d"),
            "end_date": events["timestamp"].max().strftime("%Y-%m-%d"),
        },
        "unit": "sessions" if use_sessions else "users",
        "total_units": total_units,
        "event_catalog": event_catalog,
        "dimensions": dimensions,
        "selected_dimension": selected_dimension,
        "steps": selected_steps,
        "funnel": funnel,
        "journey_paths": journey_paths,
        "segment_funnels": segment_funnels,
        "methodology": (
            "A unit is a session when session_id is available; rows with a missing session_id "
            "fall back to a user-level unit. Each funnel step must occur after the previous "
            "selected event within the same unit; intervening events are allowed. A unit is "
            "counted once per step. Journey paths collapse consecutive duplicate event names "
            "and show up to the first six events. Segment assignment uses each user's most "
            "frequently observed non-empty attribute value, with alphabetical tie-breaking. "
            "All results are descriptive and do not establish causality."
        ),
    }
