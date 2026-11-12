import json
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services.dataset_service import (
    DOCUMENT_DIR, UPLOAD_DIR, get_connection, inspect_tabular,
    save_dataset, save_document, delete_dataset, get_active_datasets, set_active_dataset,
)

router = APIRouter(prefix="/api/datasets", tags=["Datasets"])


@router.post("/inspect")
async def inspect_dataset(file: UploadFile = File(...)):
    if not file.filename or Path(file.filename).suffix.lower() not in (".csv", ".xlsx"):
        raise HTTPException(status_code=400, detail="Please upload a CSV or XLSX file.")
    try:
        return inspect_tabular(await file.read(), file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        await file.close()


@router.post("/upload/{dataset_type}")
async def upload_dataset(
    dataset_type: str,
    file: UploadFile = File(...),
    mapping: str = Form("{}"),
):
    if dataset_type not in ("events", "reviews"):
        raise HTTPException(status_code=400, detail="Dataset type must be events or reviews.")
    if not file.filename or Path(file.filename).suffix.lower() not in (".csv", ".xlsx", ".xls"):
        raise HTTPException(status_code=400, detail="Please upload a CSV or Excel file.")
    try:
        column_mapping = json.loads(mapping)
        if not isinstance(column_mapping, dict):
            raise ValueError("Column mapping must be an object.")
        result = save_dataset(await file.read(), file.filename, dataset_type, column_mapping)
        return {"message": "Dataset uploaded and validated successfully.", "data": result}
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Could not store the dataset.") from exc
    finally:
        await file.close()


@router.post("/upload-document")
async def upload_document(file: UploadFile = File(...)):
    try:
        if not file.filename:
            raise ValueError("A filename is required.")
        result = save_document(await file.read(), file.filename)
        return {"message": "Document uploaded and text extracted successfully.", "data": result}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Could not store the document.") from exc
    finally:
        await file.close()



@router.get("/active")
def active_datasets():
    return {"active_datasets": get_active_datasets()}


@router.put("/active/{dataset_type}")
def update_active_dataset(dataset_type: str, dataset_id: str | None = None):
    try:
        selected = set_active_dataset(dataset_type, dataset_id)
        return {"dataset_type": dataset_type, "dataset": selected}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/{dataset_id}")
def remove_dataset(dataset_id: str):
    try:
        deleted = delete_dataset(dataset_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return {"message": "Uploaded file deleted successfully.", "dataset_id": dataset_id}


@router.get("")
def list_datasets():
    connection = get_connection()
    try:
        rows = connection.execute(
            """SELECT id, dataset_type, original_filename, row_count, uploaded_at
               FROM datasets ORDER BY uploaded_at DESC"""
        ).fetchall()
        return {"datasets": [dict(row) for row in rows]}
    finally:
        connection.close()


@router.get("/{dataset_id}/preview")
def preview_dataset(dataset_id: str):
    connection = get_connection()
    try:
        row = connection.execute(
            """SELECT stored_filename, original_filename, dataset_type, row_count
               FROM datasets WHERE id = ?""", (dataset_id,)
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    if row["dataset_type"] == "documents":
        file_path = DOCUMENT_DIR / row["stored_filename"]
        if not file_path.is_file():
            raise HTTPException(status_code=404, detail="Stored document could not be found.")
        return {
            "filename": row["original_filename"], "dataset_type": "documents",
            "total_rows": row["row_count"],
            "extracted_text": file_path.read_text(encoding="utf-8")[:6000],
        }
    file_path = UPLOAD_DIR / row["stored_filename"]
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Stored dataset could not be found.")
    df = pd.read_csv(file_path, nrows=10)
    return {
        "filename": row["original_filename"], "dataset_type": row["dataset_type"],
        "total_rows": row["row_count"], "preview": df.fillna("").astype(str).to_dict(orient="records"),
    }
