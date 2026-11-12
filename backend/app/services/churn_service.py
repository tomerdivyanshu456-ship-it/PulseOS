import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.services.analytics_service import get_dataset_by_id


PURCHASE_EVENTS = {"purchase", "purchased", "order_completed"}
FEATURE_COLUMNS = [
    "event_count",
    "active_days",
    "purchase_events",
    "sessions",
    "event_diversity",
    "days_since_last_activity",
    "purchase_revenue",
    "events_per_active_day",
]


def _build_churn_cohort(events):
    required = {"user_id", "event_name", "timestamp"}
    if not required.issubset(events.columns):
        raise ValueError("The event dataset must contain user_id, event_name and timestamp.")

    df = events.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp", "user_id"])
    if df.empty:
        raise ValueError("No valid event records were found.")

    df["date"] = df["timestamp"].dt.tz_convert(None).dt.normalize()
    df["event_name"] = df["event_name"].astype(str).str.strip().str.lower()
    latest_date = df["date"].max()
    observation_end = latest_date - pd.Timedelta(days=7)
    observation_start = latest_date - pd.Timedelta(days=13)

    if (latest_date - df["date"].min()).days < 13:
        raise ValueError(
            "At least 14 calendar days of event history are required: "
            "7 observation days followed by 7 churn-outcome days."
        )

    observation = df[
        (df["date"] >= observation_start) & (df["date"] <= observation_end)
    ].copy()
    outcome = df[
        (df["date"] > observation_end) & (df["date"] <= latest_date)
    ].copy()
    if observation.empty or outcome.empty:
        raise ValueError("Both the 7-day observation window and 7-day outcome window need event records.")

    rows = []
    retained_users = set(outcome["user_id"].astype(str))
    for user_id, group in observation.groupby(observation["user_id"].astype(str)):
        active_days = int(group["date"].nunique())
        last_active = group["date"].max()
        purchases = group[group["event_name"].isin(PURCHASE_EVENTS)]
        if "session_id" in group.columns:
            session_values = group["session_id"].dropna().astype(str).str.strip()
            sessions = int(session_values[session_values.ne("")].nunique())
        else:
            sessions = active_days
        revenue = 0.0
        if "revenue" in group.columns:
            revenue_values = pd.to_numeric(purchases.get("revenue", pd.Series(dtype=float)), errors="coerce").fillna(0)
            revenue = float(revenue_values.sum())
        event_count = int(len(group))
        rows.append({
            "user_id": user_id,
            "event_count": event_count,
            "active_days": active_days,
            "purchase_events": int(len(purchases)),
            "sessions": sessions,
            "event_diversity": int(group["event_name"].nunique()),
            "days_since_last_activity": int((observation_end - last_active).days),
            "purchase_revenue": round(revenue, 2),
            "events_per_active_day": round(event_count / active_days, 3) if active_days else 0.0,
            "churned": int(user_id not in retained_users),
        })

    return pd.DataFrame(rows), observation_start, observation_end, latest_date


def _metrics(y_true, y_pred, probabilities):
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 3),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 3),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 3),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 3),
        "roc_auc": round(float(roc_auc_score(y_true, probabilities)), 3),
    }


def predict_customer_churn(dataset_id):
    """Train and evaluate churn models for one explicitly selected events dataset."""
    if not dataset_id:
        raise ValueError("Select an events dataset to analyse.")
    events = get_dataset_by_id(dataset_id, "events")
    cohort, observation_start, observation_end, latest_date = _build_churn_cohort(events)

    class_counts = cohort["churned"].value_counts()
    churned_count = int(class_counts.get(1, 0))
    retained_count = int(class_counts.get(0, 0))
    if len(cohort) < 30 or min(churned_count, retained_count) < 6:
        raise ValueError(
            "The churn cohort is too small or has too few examples in one class. "
            "At least 30 eligible users and 6 churned plus 6 retained users are required."
        )

    X = cohort[FEATURE_COLUMNS].astype(float)
    y = cohort["churned"].astype(int)
    X_train, X_test, y_train, y_test, _, ids_test = train_test_split(
        X, y, cohort["user_id"], test_size=0.25, random_state=42, stratify=y
    )

    models = {
        "Logistic Regression": Pipeline([
            ("scale", StandardScaler()),
            ("model", LogisticRegression(
                class_weight="balanced", max_iter=1000, random_state=42, solver="liblinear"
            )),
        ]),
        "Random Forest": RandomForestClassifier(
            n_estimators=200,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
        ),
    }

    majority_baseline = DummyClassifier(strategy="most_frequent")
    majority_baseline.fit(X_train, y_train)
    baseline_predictions = majority_baseline.predict(X_test)
    baseline_probabilities = majority_baseline.predict_proba(X_test)[:, 1]
    comparison = [{
        "model": "Majority-class baseline",
        "metrics": _metrics(y_test, baseline_predictions, baseline_probabilities),
        "cross_validation": None,
    }]

    folds = min(5, int(class_counts.min()))
    if folds < 2:
        raise ValueError("At least two examples per class are required for cross-validation.")
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)

    for name, model in models.items():
        model.fit(X_train, y_train)
        probabilities = model.predict_proba(X_test)[:, 1]
        predictions = (probabilities >= 0.5).astype(int)
        cv_results = cross_validate(
            clone(model), X, y, cv=cv,
            scoring={"f1": "f1", "roc_auc": "roc_auc"},
            n_jobs=1,
            error_score="raise",
        )
        comparison.append({
            "model": name,
            "metrics": _metrics(y_test, predictions, probabilities),
            "cross_validation": {
                "folds": folds,
                "f1_mean": round(float(cv_results["test_f1"].mean()), 3),
                "f1_std": round(float(cv_results["test_f1"].std()), 3),
                "roc_auc_mean": round(float(cv_results["test_roc_auc"].mean()), 3),
                "roc_auc_std": round(float(cv_results["test_roc_auc"].std()), 3),
            },
        })

    logistic = models["Logistic Regression"]
    logistic_probabilities = logistic.predict_proba(X_test)[:, 1]
    logistic_predictions = (logistic_probabilities >= 0.5).astype(int)
    matrix = confusion_matrix(y_test, logistic_predictions, labels=[0, 1])
    holdout = []
    for user_id, actual, probability in zip(ids_test.tolist(), y_test.tolist(), logistic_probabilities.tolist()):
        holdout.append({
            "user_id": str(user_id),
            "actual_churn": int(actual),
            "predicted_churn_probability": round(float(probability), 4),
            "predicted_label": int(probability >= 0.5),
            "risk_band": "High" if probability >= 0.7 else "Medium" if probability >= 0.4 else "Low",
        })
    holdout.sort(key=lambda item: (-item["predicted_churn_probability"], item["user_id"]))

    return {
        "status": "ready",
        "target_definition": "Churn = no recorded event during the 7 calendar days after a user's 7-day observation window.",
        "observation_window": {"start_date": observation_start.strftime("%Y-%m-%d"), "end_date": observation_end.strftime("%Y-%m-%d")},
        "outcome_window": {"start_date": (observation_end + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), "end_date": latest_date.strftime("%Y-%m-%d")},
        "cohort_size": int(len(cohort)),
        "churned_users": churned_count,
        "retained_users": retained_count,
        "train_users": int(len(X_train)),
        "holdout_users": int(len(X_test)),
        "model_comparison": comparison,
        "confusion_matrix": {
            "labels": ["Retained", "Churn"],
            "true_negative": int(matrix[0, 0]),
            "false_positive": int(matrix[0, 1]),
            "false_negative": int(matrix[1, 0]),
            "true_positive": int(matrix[1, 1]),
        },
        "holdout_predictions": holdout,
        "features_used": FEATURE_COLUMNS,
        "methodology": (
            "Features use only the 7-day observation window; labels use the following 7-day outcome window. "
            "A stratified 75/25 user holdout reports final metrics. A separate stratified cross-validation "
            "on the full eligible cohort reports mean and standard deviation for F1 and ROC-AUC. "
            "A majority-class DummyClassifier is included as a simple baseline."
        ),
        "limitations": [
            "Churn is an inactivity proxy, not confirmed cancellation or subscription termination.",
            "Holdout predictions are retrospective examples, not live scores for current customers.",
            "Cross-validation and holdout results on synthetic data do not establish real-world performance.",
            "Small cohorts and a single observation period can produce unstable estimates.",
            "The models identify associations in event behaviour; they do not establish why a user churned.",
        ],
    }
