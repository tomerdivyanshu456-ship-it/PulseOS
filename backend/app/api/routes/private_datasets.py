"""Google-authenticated dataset endpoints backed by Supabase Storage and RLS.

These endpoints are intentionally separate from the legacy SQLite API until every
analytics consumer has been migrated to owner-scoped reads.
"""
import json
from io import BytesIO, StringIO
from pathlib import Path
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.security import require_supabase_user
from app.services.dataset_service import (
    REQUIRED_COLUMNS,
    _read_tabular,
    inspect_tabular,
    validate_dataset,
)
from app.services.supabase_dataset_repository import (
    DatasetRepositoryError,
    SupabaseDatasetRepository,
)

router = APIRouter(prefix="/api/workspace/datasets", tags=["Private datasets"])


def _repository(claims: dict) -> SupabaseDatasetRepository:
    try:
        return SupabaseDatasetRepository(
            user_id=claims["sub"],
            access_token=claims["_access_token"],
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid authenticated workspace identity.") from exc
    except DatasetRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


async def _read_limited(file: UploadFile, limit: int) -> bytes:
    chunks = []
    total = 0
    while True:
        chunk = await file.read(min(1024 * 1024, limit - total + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(status_code=413, detail="Uploaded file exceeds the size limit.")
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/inspect")
async def inspect_private_dataset(
    file: UploadFile = File(...),
    claims: dict = Depends(require_supabase_user),
):
    if not file.filename or Path(file.filename).suffix.lower() not in (".csv", ".xlsx"):
        raise HTTPException(status_code=400, detail="Please upload a CSV or XLSX file.")
    try:
        contents = await _read_limited(file, 20 * 1024 * 1024)
        return inspect_tabular(contents, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        await file.close()


@router.post("/upload/{dataset_type}")
async def upload_private_dataset(
    dataset_type: str,
    file: UploadFile = File(...),
    mapping: str = Form("{}"),
    claims: dict = Depends(require_supabase_user),
):
    if dataset_type not in ("events", "reviews"):
        raise HTTPException(status_code=400, detail="Dataset type must be events or reviews.")
    if not file.filename or Path(file.filename).suffix.lower() not in (".csv", ".xlsx"):
        raise HTTPException(status_code=400, detail="Please upload a CSV or XLSX file.")
    repository = _repository(claims)
    try:
        try:
            column_mapping = json.loads(mapping)
            if not isinstance(column_mapping, dict):
                raise ValueError("Column mapping must be an object.")
            contents = await _read_limited(file, 20 * 1024 * 1024)
            frame = _read_tabular(contents, file.filename)
            rename = {}
            selected = []
            for canonical in REQUIRED_COLUMNS[dataset_type]:
                source = column_mapping.get(canonical) or canonical
                if source not in frame.columns:
                    raise ValueError(f"Please map a source column to {canonical}.")
                selected.append(source)
                rename[source] = canonical
            if len(set(selected)) != len(selected):
                raise ValueError("Each required field must use a different source column.")
            frame = frame.rename(columns=rename)
            errors = validate_dataset(frame, dataset_type)
            if errors:
                raise ValueError("; ".join(errors))
            output = StringIO()
            frame.to_csv(output, index=False)
            dataset_id = str(uuid4())
            result = repository.upload(
                dataset_id=dataset_id,
                dataset_type=dataset_type,
                filename=Path(file.filename).name,
                contents=output.getvalue().encode("utf-8"),
                row_count=len(frame),
                content_type="text/csv",
            )
            return {
                "message": "Dataset uploaded and validated successfully.",
                "data": {
                    "dataset_id": result["id"],
                    "dataset_type": result["dataset_type"],
                    "filename": result["original_filename"],
                    "rows": result["row_count"],
                    "columns": list(frame.columns),
                    "uploaded_at": result.get("uploaded_at"),
                    "preview": frame.head(5).fillna("").astype(str).to_dict(orient="records"),
                },
            }
        except HTTPException:
            raise
        except (ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except DatasetRepositoryError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Could not store the private dataset.") from exc
    finally:
        repository.close()
        await file.close()


@router.get("")
def list_private_datasets(claims: dict = Depends(require_supabase_user)):
    repository = _repository(claims)
    try:
        return {"datasets": repository.list_datasets()}
    except DatasetRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        repository.close()


@router.get("/active")
def get_private_active_datasets(claims: dict = Depends(require_supabase_user)):
    repository = _repository(claims)
    try:
        return {"active_datasets": repository.get_active_datasets()}
    except DatasetRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        repository.close()


@router.put("/active/{dataset_type}")
def set_private_active_dataset(
    dataset_type: str,
    dataset_id: str | None = None,
    claims: dict = Depends(require_supabase_user),
):
    repository = _repository(claims)
    try:
        selected = repository.set_active_dataset(dataset_type, dataset_id)
        return {"dataset_type": dataset_type, "dataset": selected}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DatasetRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        repository.close()


@router.get("/{dataset_id}/preview")
def preview_private_dataset(dataset_id: str, claims: dict = Depends(require_supabase_user)):
    repository = _repository(claims)
    try:
        record = repository.get_dataset(dataset_id)
        if not record:
            raise HTTPException(status_code=404, detail="Dataset not found.")
        raw = repository.download(record["object_path"])
        frame = pd.read_csv(BytesIO(raw), nrows=10)
        return {
            "filename": record["original_filename"],
            "dataset_type": record["dataset_type"],
            "total_rows": record["row_count"],
            "preview": frame.fillna("").astype(str).to_dict(orient="records"),
        }
    except HTTPException:
        raise
    except DatasetRepositoryError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 503, detail=str(exc)) from exc
    finally:
        repository.close()


@router.delete("/{dataset_id}")
def delete_private_dataset(dataset_id: str, claims: dict = Depends(require_supabase_user)):
    repository = _repository(claims)
    try:
        if not repository.delete_dataset(dataset_id):
            raise HTTPException(status_code=404, detail="Dataset not found.")
        return {"message": "Uploaded file deleted successfully.", "dataset_id": dataset_id}
    except HTTPException:
        raise
    except DatasetRepositoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        repository.close()
