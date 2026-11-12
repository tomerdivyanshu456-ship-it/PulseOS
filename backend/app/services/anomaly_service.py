import pandas as pd
from sklearn.ensemble import IsolationForest

from app.services.analytics_service import get_latest_dataset


METRICS = {
    "event_count": "Daily events",
    "active_users": "Daily active users",
    "purchase_count": "Daily purchases",
    "revenue": "Daily purchase revenue",
}


def detect_product_anomalies():
    """Detect unusual daily product activity with one Isolation Forest per metric."""
    df = get_latest_dataset("events")
    required = {"user_id", "event_name", "timestamp"}
    if not required.issubset(df.columns):
        raise ValueError("The event dataset must contain user_id, event_name and timestamp.")

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp", "user_id"])
    if df.empty:
        raise ValueError("No valid event records were found.")

    df["event_name"] = df["event_name"].astype(str).str.strip().str.lower()
    df["date"] = df["timestamp"].dt.strftime("%Y-%m-%d")
    purchase_names = {"purchase", "purchased", "order_completed"}

    daily = df.groupby("date").agg(
        event_count=("event_name", "size"),
        active_users=("user_id", "nunique"),
    )
    daily["purchase_count"] = df[df["event_name"].isin(purchase_names)].groupby("date").size()
    daily["purchase_count"] = daily["purchase_count"].fillna(0)
    if "revenue" in df.columns:
        purchases = df[df["event_name"].isin(purchase_names)].copy()
        purchases["revenue"] = pd.to_numeric(purchases["revenue"], errors="coerce").fillna(0)
        daily["revenue"] = purchases.groupby("date")["revenue"].sum()
        daily["revenue"] = daily["revenue"].fillna(0)
    daily = daily.sort_index()
    daily = daily.tail(90)

    if len(daily) < 7:
        raise ValueError("At least 7 distinct days of event data are required for anomaly detection.")

    anomalies = []
    skipped = []
    for metric, label in METRICS.items():
        if metric not in daily.columns:
            continue
        values = daily[metric].astype(float)
        if values.nunique() < 2:
            skipped.append(f"{label}: values do not vary across the observation window.")
            continue

        model = IsolationForest(
            n_estimators=200,
            contamination=0.1,
            random_state=42,
        )
        predictions = model.fit_predict(values.to_frame())
        scores = -model.decision_function(values.to_frame())
        for index, prediction in enumerate(predictions):
            if int(prediction) == -1:
                anomalies.append({
                    "date": str(values.index[index]),
                    "metric": metric,
                    "label": label,
                    "value": round(float(values.iloc[index]), 2),
                    "anomaly_score": round(float(scores[index]), 4),
                    "direction": "spike" if values.iloc[index] > values.median() else "drop",
                    "baseline_median": round(float(values.median()), 2),
                })

    anomalies.sort(key=lambda item: (-item["anomaly_score"], item["date"], item["metric"]))
    return {
        "status": "ready",
        "period": {"start_date": str(daily.index.min()), "end_date": str(daily.index.max())},
        "days_analyzed": int(len(daily)),
        "metrics_analyzed": [metric for metric in METRICS if metric in daily.columns and daily[metric].nunique() >= 2],
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
        "daily_metrics": [
            {"date": str(date), **{key: round(float(value), 2) for key, value in row.items()}}
            for date, row in daily.iterrows()
        ],
        "data_gaps": skipped,
        "methodology": (
            "Each daily metric is modelled independently with scikit-learn IsolationForest "
            "(200 trees, contamination=0.1, fixed random seed). The model flags observations "
            "that are unusual relative to the uploaded history; it does not identify causes."
        ),
        "limitations": [
            "At least 7 distinct dates are required; more history generally gives a more useful baseline.",
            "The 10% contamination setting is a modelling assumption, not an estimate of the true incident rate.",
            "Seasonality, promotions, tracking changes and low-volume data can create misleading flags.",
            "An anomaly is a prompt for investigation, not proof of a product issue.",
        ],
    }
