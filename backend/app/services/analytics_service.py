
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
        },
        "funnel": funnel,
        "daily_activity": [
            {
                "date": date,
                "active_users": int(users),
            }
            for date, users in daily_users.items()
        ],
    }
