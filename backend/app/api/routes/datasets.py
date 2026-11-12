
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.dataset_service import (
    UPLOAD_DIR,
    get_connection,
    save_dataset,
)

router = APIRouter(prefix="/api/datasets", tags=["Datasets"])


@router.post("/upload/{dataset_type}")
async def upload_dataset(
    dataset_type: str,
    file: UploadFile = File(...),
):
    if dataset_type not in ("events", "reviews"):
        raise HTTPException(
            status_code=400,
            detail="Dataset type must be events or reviews.",
        )

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file.",
        )

    contents = await file.read()

    try:
        result = save_dataset(
            contents=contents,
            filename=file.filename,
            dataset_type=dataset_type,
        )
        return {
            "message": "Dataset uploaded and validated successfully.",
            "data": result,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not store the dataset.",
        ) from exc

    finally:
        await file.close()


@router.get("")
def list_datasets():
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT id, dataset_type, original_filename,
                   row_count, uploaded_at
            FROM datasets
            ORDER BY uploaded_at DESC
            """
        ).fetchall()

        return {
            "datasets": [dict(row) for row in rows]
        }
    finally:
        connection.close()


@router.get("/{dataset_id}/preview")
def preview_dataset(dataset_id: str):
    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT stored_filename, original_filename,
                   dataset_type, row_count
            FROM datasets
            WHERE id = ?
            """,
            (dataset_id,),
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found.",
        )

    file_path = UPLOAD_DIR / row["stored_filename"]

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Stored CSV file could not be found.",
        )

    df = pd.read_csv(file_path, nrows=10)

    return {
        "filename": row["original_filename"],
        "dataset_type": row["dataset_type"],
        "total_rows": row["row_count"],
        "preview": df.fillna("").to_dict(orient="records"),
    }
