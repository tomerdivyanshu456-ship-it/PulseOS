
import sqlite3
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import pandas as pd


# Project directories
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
UPLOAD_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "pulseos.db"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# Required columns for each dataset
REQUIRED_COLUMNS = {
    "events": ["user_id", "event_name", "timestamp"],
    "reviews": ["review_id", "rating", "review_text"],
}


def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    connection.execute("""
        CREATE TABLE IF NOT EXISTS datasets (
            id TEXT PRIMARY KEY,
            dataset_type TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            stored_filename TEXT NOT NULL,
            row_count INTEGER NOT NULL,
            uploaded_at TEXT NOT NULL
        )
    """)

    connection.commit()
    return connection


def validate_dataset(df, dataset_type):
    required = REQUIRED_COLUMNS[dataset_type]

    missing_columns = [
        column for column in required
        if column not in df.columns
    ]

    if missing_columns:
        return [
            f"Missing required columns: {', '.join(missing_columns)}"
        ]

    if df.empty:
        return ["The uploaded CSV contains no records."]

    errors = []

    for column in required:
        missing_count = int(df[column].isna().sum())

        if missing_count:
            errors.append(
                f"{column}: {missing_count} missing values"
            )

    if dataset_type == "events":
        timestamps = pd.to_datetime(
            df["timestamp"], errors="coerce"
        )

        invalid_count = int(timestamps.isna().sum())

        if invalid_count:
            errors.append(
                f"timestamp: {invalid_count} invalid date values"
            )

    if dataset_type == "reviews":
        ratings = pd.to_numeric(
            df["rating"], errors="coerce"
        )

        invalid_ratings = (
            ratings.isna() | ~ratings.between(1, 5)
        )

        invalid_count = int(invalid_ratings.sum())

        if invalid_count:
            errors.append(
                f"rating: {invalid_count} invalid values. "
                "Ratings must be numbers between 1 and 5."
            )

    return errors


def save_dataset(contents, filename, dataset_type):
    if dataset_type not in REQUIRED_COLUMNS:
        raise ValueError("Unsupported dataset type.")

    if len(contents) > 20 * 1024 * 1024:
        raise ValueError("Maximum CSV file size is 20 MB.")

    try:
        df = pd.read_csv(BytesIO(contents))
    except Exception as exc:
        raise ValueError(
            f"Could not read CSV file: {exc}"
        ) from exc

    errors = validate_dataset(df, dataset_type)

    if errors:
        raise ValueError("; ".join(errors))

    dataset_id = str(uuid.uuid4())
    stored_filename = f"{dataset_id}.csv"
    file_path = UPLOAD_DIR / stored_filename

    # Save original CSV only after validation succeeds.
    file_path.write_bytes(contents)

    uploaded_at = datetime.now(timezone.utc).isoformat()

    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO datasets (
                    id,
                    dataset_type,
                    original_filename,
                    stored_filename,
                    row_count,
                    uploaded_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    dataset_id,
                    dataset_type,
                    Path(filename).name,
                    stored_filename,
                    len(df),
                    uploaded_at,
                ),
            )
    except Exception:
        file_path.unlink(missing_ok=True)
        raise

    return {
        "dataset_id": dataset_id,
        "dataset_type": dataset_type,
        "filename": Path(filename).name,
        "rows": len(df),
        "columns": list(df.columns),
        "uploaded_at": uploaded_at,
        "preview": df.head(5).fillna("").to_dict(
            orient="records"
        ),
    }
