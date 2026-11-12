
import pandas as pd

from app.services.dataset_service import (
    UPLOAD_DIR,
    get_connection,
)


def get_latest_dataset(dataset_type):
    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT stored_filename, original_filename
            FROM datasets
            WHERE dataset_type = ?
            ORDER BY uploaded_at DESC
            LIMIT 1
            """,
            (dataset_type,),
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        raise ValueError(
            f"No {dataset_type} dataset has been uploaded."
        )

    file_path = UPLOAD_DIR / row["stored_filename"]

    if not file_path.is_file():
        raise ValueError("The stored dataset file is missing.")

    return pd.read_csv(file_path)



def get_dataset_by_id(dataset_id, dataset_type):
    connection = get_connection()
    try:
        row = connection.execute(
            """SELECT stored_filename FROM datasets WHERE id = ? AND dataset_type = ?""",
            (dataset_id, dataset_type),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise ValueError(f"Selected {dataset_type} dataset was not found.")
    file_path = UPLOAD_DIR / row["stored_filename"]
    if not file_path.is_file():
        raise ValueError("The selected dataset file is missing.")
    return pd.read_csv(file_path)

# Transparent starter taxonomy. Teams can extend these aliases to match
# the event names emitted by their own product.
FEATURE_TAXONOMY = {
    "Product Discovery": ("product_viewed", "view_product", "product_view", "search", "search_submitted", "category_viewed", "browse"),
    "Cart & Wishlist": ("add_to_cart", "cart_add", "remove_from_cart", "cart_viewed", "wishlist", "save_item"),
    "Checkout & Payments": ("checkout", "payment", "purchase", "purchased", "order_completed", "transaction"),
    "Account & Onboarding": ("sign_up", "signup", "register", "login", "account_created", "onboarding"),
    "Customer Support": ("support", "help", "ticket", "chat_started", "contact_support"),
}


def calculate_feature_intelligence(events, total_users):
    """Summarise adoption and usage depth for mapped product feature groups."""
    rows = []
    normalised = events["event_name"].astype(str).str.strip().str.lower()

    for feature, aliases in FEATURE_TAXONOMY.items():
        mask = normalised.apply(lambda event: any(alias in event for alias in aliases))
        feature_events = events.loc[mask]
        if feature_events.empty:
            continue

        user_event_counts = feature_events.groupby("user_id").size()
        active_users = int(user_event_counts.size)
        event_count = int(len(feature_events))
        adoption_rate = round(active_users / total_users * 100, 1) if total_users else 0
        repeat_users = int((user_event_counts >= 2).sum())

        if adoption_rate < 25:
            reach_label = "Low reach"
            interpretation = "A small share of observed users interacted with this feature."
        elif adoption_rate < 60:
            reach_label = "Moderate reach"
            interpretation = "Feature adoption is meaningful but does not yet reach most observed users."
        else:
            reach_label = "Broad reach"
            interpretation = "A majority of observed users interacted with this feature."

        rows.append({
            "feature": feature,
            "active_users": active_users,
            "event_count": event_count,
            "adoption_rate": adoption_rate,
            "events_per_active_user": round(event_count / active_users, 2) if active_users else 0,
            "repeat_users": repeat_users,
            "repeat_usage_rate": round(repeat_users / active_users * 100, 1) if active_users else 0,
            "reach_label": reach_label,
            "interpretation": interpretation,
        })

    rows.sort(key=lambda item: (item["adoption_rate"], item["active_users"]), reverse=True)
    return {
        "features": rows,
        "mapped_feature_count": len(rows),
        "mapping_note": (
            "Feature groups are inferred from event-name aliases in a starter taxonomy. "
            "Review and customise the mapping for your product's tracking plan. "
            "Adoption is the share of unique users with at least one mapped event; "
            "repeat usage means two or more mapped events, not necessarily separate sessions."
        ),
    }

def calculate_product_analytics():
    df = get_latest_dataset("events")

    required = ["user_id", "event_name", "timestamp"]

    if not all(column in df.columns for column in required):
        raise ValueError("The event dataset has an invalid structure.")

    df["timestamp"] = pd.to_datetime(
        df["timestamp"], errors="coerce"
    )

    df["event_name"] = (
        df["event_name"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    df = df.dropna(subset=["user_id", "timestamp"])

    if df.empty:
        raise ValueError("No valid event records were found.")

    # Use the dates available in the dataset rather than
    # assuming the sample data represents today's activity.
    latest_date = df["timestamp"].max().normalize()
    start_date = latest_date - pd.Timedelta(days=29)

    recent_df = df[
        (df["timestamp"] >= start_date)
        & (df["timestamp"] < latest_date + pd.Timedelta(days=1))
    ].copy()

    # Daily Active Users
    daily_users = (
        recent_df.groupby(
            recent_df["timestamp"].dt.strftime("%Y-%m-%d")
        )["user_id"]
        .nunique()
        .sort_index()
    )

    dau = int(
        df[
            df["timestamp"].dt.date == latest_date.date()
        ]["user_id"].nunique()
    )

    mau = int(recent_df["user_id"].nunique())

    # Funnel: unique users at each stage
    event_aliases = {
        "product_viewed": [
            "product_viewed",
            "view_product",
            "product_view",
        ],
        "add_to_cart": [
            "add_to_cart",
            "cart_add",
        ],
        "purchase": [
            "purchase",
            "purchased",
            "order_completed",
        ],
    }

    funnel = []

    for stage, aliases in event_aliases.items():
        users = int(
            recent_df[
                recent_df["event_name"].isin(aliases)
            ]["user_id"].nunique()
        )

        funnel.append({
            "stage": stage.replace("_", " ").title(),
            "users": users,
        })

    viewers = funnel[0]["users"]
    purchasers = funnel[2]["users"]

    conversion_rate = (
        round((purchasers / viewers) * 100, 2)
        if viewers > 0 else 0
    )

    # Sequential funnel: require each stage to occur after the previous stage.
    # Prefer session_id when available; otherwise use user_id as a weaker proxy.
    sequence_key = "session_id" if "session_id" in recent_df.columns else "user_id"
    sequential_counts = {"Product Viewed": 0, "Add To Cart": 0, "Purchase": 0}

    sequence_df = recent_df.dropna(subset=[sequence_key]).copy()
    sequence_df = sequence_df[sequence_df[sequence_key].astype(str).str.strip().ne("")]
    for _, group in sequence_df.sort_values("timestamp").groupby(sequence_key):
        names = group["event_name"].tolist()
        view_positions = [i for i, name in enumerate(names) if name in event_aliases["product_viewed"]]
        cart_positions = [i for i, name in enumerate(names) if name in event_aliases["add_to_cart"]]
        purchase_positions = [i for i, name in enumerate(names) if name in event_aliases["purchase"]]

        if view_positions:
            sequential_counts["Product Viewed"] += 1
            first_view = view_positions[0]
            later_carts = [i for i in cart_positions if i > first_view]
            if later_carts:
                sequential_counts["Add To Cart"] += 1
                first_cart = later_carts[0]
                if any(i > first_cart for i in purchase_positions):
                    sequential_counts["Purchase"] += 1

    sequential_funnel = [
        {"stage": stage, "count": count}
        for stage, count in sequential_counts.items()
    ]
    sequential_funnel_meta = {
        "unit": "sessions" if sequence_key == "session_id" else "users",
        "method": "ordered_events_within_session" if sequence_key == "session_id" else "ordered_events_within_user",
        "reliability_note": (
            "Ordered progression is measured within session_id."
            if sequence_key == "session_id"
            else "session_id was unavailable; ordered progression is approximated within user_id and may combine separate visits."
        ),
    }

    # Revenue: sum revenue only for purchase events
    revenue = 0.0

    if "revenue" in recent_df.columns:
        purchase_aliases = event_aliases["purchase"]

        purchase_rows = recent_df[
            recent_df["event_name"].isin(purchase_aliases)
        ].copy()

        purchase_rows["revenue"] = pd.to_numeric(
            purchase_rows["revenue"],
            errors="coerce",
        ).fillna(0)

        revenue = round(
            float(purchase_rows["revenue"].sum()), 2
        )

    # Weekly retention cohorts: cohort week is the week of a user's first observed event.
    # Only show fully elapsed follow-up weeks; partial weeks would understate retention.
    cohort_df = df[["user_id", "timestamp"]].copy()
    cohort_df["activity_week"] = cohort_df["timestamp"].dt.to_period("W-SUN").dt.start_time
    first_weeks = cohort_df.groupby("user_id")["activity_week"].min().rename("cohort_week")
    cohort_df = cohort_df.join(first_weeks, on="user_id")
    cohort_df["week_number"] = (
        (cohort_df["activity_week"] - cohort_df["cohort_week"]).dt.days // 7
    ).astype(int)
    cohort_sizes = first_weeks.groupby(first_weeks).size()
    retention_rows = []
    for cohort_week, cohort_size in cohort_sizes.items():
        cohort_events = cohort_df[cohort_df["cohort_week"] == cohort_week]
        elapsed_days = int((latest_date - cohort_week.normalize()).days)
        # Week 0 is the cohort baseline. Week N is reported only after
        # its full seven-day observation window has elapsed.
        max_complete_week = max(0, (elapsed_days - 6) // 7)
        cells = []
        for week_number in range(max_complete_week + 1):
            retained_users = int(
                cohort_events[cohort_events["week_number"] == week_number]["user_id"].nunique()
            )
            cells.append({
                "week": week_number,
                "active_users": retained_users,
                "retention_rate": round(retained_users / int(cohort_size) * 100, 1),
                "is_complete": True,
            })
        retention_rows.append({
            "cohort": cohort_week.strftime("%Y-%m-%d"),
            "cohort_size": int(cohort_size),
            "weeks": cells,
        })

    # Repeat usage is measured across distinct active calendar days.
    total_users = int(df["user_id"].nunique())
    active_days_per_user = df.groupby("user_id")["timestamp"].apply(
        lambda values: values.dt.date.nunique()
    )
    repeat_users = int((active_days_per_user >= 2).sum())
    repeat_user_rate = round(repeat_users / total_users * 100, 1) if total_users else 0
    average_events_per_user = round(len(df) / total_users, 2) if total_users else 0

    # Event adoption is a proxy for feature adoption until the product
    # supplies a maintained event-to-feature taxonomy.
    event_adoption = (
        df.groupby("event_name")
        .agg(
            active_users=("user_id", "nunique"),
            event_count=("user_id", "size"),
        )
        .reset_index()
        .sort_values(["active_users", "event_count"], ascending=False)
    )
    adoption_rows = [
        {
            "event_name": str(row.event_name),
            "active_users": int(row.active_users),
            "event_count": int(row.event_count),
            "user_adoption_rate": round(int(row.active_users) / total_users * 100, 1) if total_users else 0,
        }
        for row in event_adoption.head(12).itertuples(index=False)
    ]

    return {
        "data_source": "uploaded_csv",
        "period": {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": latest_date.strftime("%Y-%m-%d"),
        },
        "metrics": {
            "daily_active_users": dau,
            "monthly_active_users": mau,
            "conversion_rate": conversion_rate,
            "total_revenue": revenue,
            "total_users": int(df["user_id"].nunique()),
            "total_events": int(len(df)),
            "repeat_users": repeat_users,
            "repeat_user_rate": repeat_user_rate,
            "average_events_per_user": average_events_per_user,
        },
        "funnel": funnel,
        "sequential_funnel": sequential_funnel,
        "sequential_funnel_meta": sequential_funnel_meta,
        "daily_activity": [
            {
                "date": date,
                "active_users": int(users),
            }
            for date, users in daily_users.items()
        ],
        "retention_cohorts": retention_rows,
        "event_adoption": adoption_rows,
        "feature_intelligence": calculate_feature_intelligence(df, total_users),
        "adoption_note": "Event adoption is used as a proxy for feature adoption. Map events to product features for a true feature-level view.",
    }
