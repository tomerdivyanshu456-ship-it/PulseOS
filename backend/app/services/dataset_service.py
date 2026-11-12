import sqlite3
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher
from io import BytesIO
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
UPLOAD_DIR = DATA_DIR / "raw"
DOCUMENT_DIR = DATA_DIR / "documents"
DB_PATH = DATA_DIR / "pulseos.db"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_COLUMNS = {
    "events": ["user_id", "event_name", "timestamp"],
    "reviews": ["review_id", "rating", "review_text"],
}

COLUMN_ALIASES = {
    "user_id": ["user_id", "userid", "user", "customer_id", "customerid", "customer_code", "client_id", "account_id"],
    "event_name": ["event_name", "event", "action", "activity", "event_type", "eventname", "activity_name"],
    "timestamp": ["timestamp", "event_time", "event_date", "datetime", "date_time", "created_at", "occurred_at", "time"],
    "review_id": ["review_id", "reviewid", "feedback_id", "comment_id", "id"],
    "rating": ["rating", "stars", "score", "review_rating", "customer_rating"],
    "review_text": ["review_text", "review", "feedback", "comment", "text", "content", "description"],
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
    connection.execute("""
        CREATE TABLE IF NOT EXISTS active_datasets (
            dataset_type TEXT PRIMARY KEY,
            dataset_id TEXT,
            updated_at TEXT NOT NULL
        )
    """)
    connection.commit()
    return connection


def get_dataset_record(dataset_type):
    """Return the selected dataset metadata, or the latest upload before a selection exists."""
    connection = get_connection()
    try:
        active = connection.execute(
            "SELECT dataset_id FROM active_datasets WHERE dataset_type = ?",
            (dataset_type,),
        ).fetchone()
        if active is not None:
            if not active["dataset_id"]:
                raise ValueError(f"No active {dataset_type} dataset is selected.")
            row = connection.execute(
                "SELECT id, dataset_type, stored_filename, original_filename, row_count "
                "FROM datasets WHERE id = ? AND dataset_type = ?",
                (active["dataset_id"], dataset_type),
            ).fetchone()
            if row is None:
                raise ValueError(f"The active {dataset_type} dataset is no longer available.")
            return dict(row)
        row = connection.execute(
            "SELECT id, dataset_type, stored_filename, original_filename, row_count "
            "FROM datasets WHERE dataset_type = ? ORDER BY uploaded_at DESC LIMIT 1",
            (dataset_type,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def set_active_dataset(dataset_type, dataset_id):
    """Persist a dataset selection; a null ID explicitly clears the selection."""
    if dataset_type not in ("events", "reviews", "documents"):
        raise ValueError("Dataset type must be events, reviews or documents.")
    with get_connection() as connection:
        if dataset_id is not None:
            row = connection.execute(
                "SELECT id FROM datasets WHERE id = ? AND dataset_type = ?",
                (dataset_id, dataset_type),
            ).fetchone()
            if row is None:
                raise ValueError(f"Selected {dataset_type} dataset was not found.")
        connection.execute(
            """INSERT INTO active_datasets (dataset_type, dataset_id, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(dataset_type) DO UPDATE SET
               dataset_id = excluded.dataset_id, updated_at = excluded.updated_at""",
            (dataset_type, dataset_id, datetime.now(timezone.utc).isoformat()),
        )
    return get_dataset_record(dataset_type)


def get_active_datasets():
    result = {}
    for kind in ("events", "reviews", "documents"):
        try:
            result[kind] = get_dataset_record(kind)
        except ValueError:
            result[kind] = None
    return result


def _read_tabular(contents, filename):
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".csv":
            return pd.read_csv(BytesIO(contents))
        if suffix == ".xlsx":
            return pd.read_excel(BytesIO(contents))
    except Exception as exc:
        raise ValueError(f"Could not read the file: {exc}") from exc
    raise ValueError("Supported tabular formats are CSV and XLSX.")


def _normalise_header(value):
    return "".join(character.lower() for character in str(value).strip() if character.isalnum())


def suggest_column_mapping(columns, dataset_type):
    if dataset_type not in REQUIRED_COLUMNS:
        raise ValueError("Dataset type must be events or reviews.")
    suggestions = {}
    for canonical in REQUIRED_COLUMNS[dataset_type]:
        aliases = {_normalise_header(item) for item in COLUMN_ALIASES[canonical]}
        ranked = []
        for column in columns:
            candidate = _normalise_header(column)
            if candidate in aliases:
                score = 1.0
            else:
                score = max((SequenceMatcher(None, candidate, alias).ratio() for alias in aliases), default=0)
            ranked.append((score, str(column)))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        suggestions[canonical] = {
            "column": ranked[0][1] if ranked and ranked[0][0] >= 0.72 else "",
            "confidence": round(ranked[0][0], 2) if ranked else 0,
        }
    return suggestions


def inspect_tabular(contents, filename):
    if len(contents) > 20 * 1024 * 1024:
        raise ValueError("Maximum tabular file size is 20 MB.")
    df = _read_tabular(contents, filename)
    if df.empty:
        raise ValueError("The uploaded file contains no records.")
    columns = [str(column) for column in df.columns]
    candidates = {}
    for dataset_type in REQUIRED_COLUMNS:
        candidates[dataset_type] = suggest_column_mapping(columns, dataset_type)
    scores = {
        kind: sum(1 for item in mapping.values() if item["column"] and item["confidence"] >= 0.85)
        for kind, mapping in candidates.items()
    }
    detected_type = max(scores, key=scores.get) if max(scores.values()) else None
    return {
        "filename": Path(filename).name,
        "columns": columns,
        "row_count": int(len(df)),
        "suggested_type": detected_type,
        "mappings": candidates,
        "preview": df.head(5).fillna("").astype(str).to_dict(orient="records"),
    }


def validate_dataset(df, dataset_type):
    if dataset_type not in REQUIRED_COLUMNS:
        return ["Dataset type must be events or reviews."]
    required = REQUIRED_COLUMNS[dataset_type]
    missing_columns = [column for column in required if column not in df.columns]
    if missing_columns:
        return [f"Missing required columns: {', '.join(missing_columns)}"]
    if df.empty:
        return ["The uploaded file contains no records."]
    errors = []
    for column in required:
        missing_count = int(df[column].isna().sum())
        if missing_count:
            errors.append(f"{column}: {missing_count} missing values")
    if dataset_type == "events":
        timestamps = pd.to_datetime(df["timestamp"], errors="coerce")
        invalid_count = int(timestamps.isna().sum())
        if invalid_count:
            errors.append(f"timestamp: {invalid_count} invalid date values")
    if dataset_type == "reviews":
        ratings = pd.to_numeric(df["rating"], errors="coerce")
        invalid_ratings = ratings.isna() | ~ratings.between(1, 5)
        invalid_count = int(invalid_ratings.sum())
        if invalid_count:
            errors.append(f"rating: {invalid_count} invalid values. Ratings must be numbers between 1 and 5.")
    return errors


def save_dataset(contents, filename, dataset_type, mapping=None):
    if dataset_type not in REQUIRED_COLUMNS:
        raise ValueError("Unsupported dataset type.")
    df = _read_tabular(contents, filename)
    mapping = mapping or {}
    rename = {}
    selected_sources = []
    for canonical in REQUIRED_COLUMNS[dataset_type]:
        source = mapping.get(canonical) or canonical
        if source not in df.columns:
            raise ValueError(f"Please map a source column to {canonical}.")
        selected_sources.append(source)
        rename[source] = canonical
    if len(set(selected_sources)) != len(selected_sources):
        raise ValueError("Each required field must use a different source column.")
    df = df.rename(columns=rename)
    errors = validate_dataset(df, dataset_type)
    if errors:
        raise ValueError("; ".join(errors))

    dataset_id = str(uuid.uuid4())
    stored_filename = f"{dataset_id}.csv"
    file_path = UPLOAD_DIR / stored_filename
    df.to_csv(file_path, index=False)
    uploaded_at = datetime.now(timezone.utc).isoformat()
    try:
        with get_connection() as connection:
            connection.execute(
                """INSERT INTO datasets (id, dataset_type, original_filename, stored_filename, row_count, uploaded_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (dataset_id, dataset_type, Path(filename).name, stored_filename, len(df), uploaded_at),
            )
            connection.execute(
                """INSERT INTO active_datasets (dataset_type, dataset_id, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(dataset_type) DO NOTHING""",
                (dataset_type, dataset_id, uploaded_at),
            )
    except Exception:
        file_path.unlink(missing_ok=True)
        raise
    return {
        "dataset_id": dataset_id, "dataset_type": dataset_type,
        "filename": Path(filename).name, "rows": len(df),
        "columns": list(df.columns), "uploaded_at": uploaded_at,
        "preview": df.head(5).fillna("").astype(str).to_dict(orient="records"),
    }


def save_document(contents, filename):
    suffix = Path(filename).suffix.lower()
    if suffix not in (".pdf", ".docx"):
        raise ValueError("Supported document formats are PDF and DOCX.")
    if len(contents) > 15 * 1024 * 1024:
        raise ValueError("Maximum document size is 15 MB.")
    try:
        if suffix == ".pdf":
            import fitz
            document = fitz.open(stream=contents, filetype="pdf")
            text_content = "\n\n".join(page.get_text() for page in document)
            page_count = len(document)
            document.close()
        else:
            from docx import Document
            document = Document(BytesIO(contents))
            text_content = "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())
            page_count = 0
    except Exception as exc:
        raise ValueError(f"Could not extract document text: {exc}") from exc
    if not text_content.strip():
        raise ValueError("No extractable text found. Scanned PDFs require OCR, which is not enabled yet.")
    dataset_id = str(uuid.uuid4())
    stored_filename = f"{dataset_id}.txt"
    file_path = DOCUMENT_DIR / stored_filename
    file_path.write_text(text_content, encoding="utf-8")
    uploaded_at = datetime.now(timezone.utc).isoformat()
    try:
        with get_connection() as connection:
            connection.execute(
                """INSERT INTO datasets (id, dataset_type, original_filename, stored_filename, row_count, uploaded_at)
                   VALUES (?, 'documents', ?, ?, ?, ?)""",
                (dataset_id, Path(filename).name, stored_filename, len(text_content.split()), uploaded_at),
            )
            connection.execute(
                """INSERT INTO active_datasets (dataset_type, dataset_id, updated_at)
                   VALUES ('documents', ?, ?)
                   ON CONFLICT(dataset_type) DO NOTHING""",
                (dataset_id, uploaded_at),
            )
    except Exception:
        file_path.unlink(missing_ok=True)
        raise
    return {
        "dataset_id": dataset_id, "dataset_type": "documents",
        "filename": Path(filename).name, "rows": len(text_content.split()),
        "characters": len(text_content), "pages": page_count,
        "uploaded_at": uploaded_at,
    }

def delete_dataset(dataset_id):
    """Delete one uploaded dataset/document and its stored file."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT dataset_type, stored_filename FROM datasets WHERE id = ?",
            (dataset_id,),
        ).fetchone()
        if row is None:
            return False

        base_dir = DOCUMENT_DIR if row["dataset_type"] == "documents" else UPLOAD_DIR
        file_path = (base_dir / row["stored_filename"]).resolve()
        if file_path.parent != base_dir.resolve():
            raise ValueError("Stored file path is invalid.")

        connection.execute(
            "UPDATE active_datasets SET dataset_id = NULL, updated_at = ? "
            "WHERE dataset_id = ?",
            (datetime.now(timezone.utc).isoformat(), dataset_id),
        )
        connection.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))
        file_path.unlink(missing_ok=True)
    return True
