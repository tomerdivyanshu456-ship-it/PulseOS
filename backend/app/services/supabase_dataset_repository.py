"""RLS-backed Supabase persistence for user-owned PulseOS datasets.

This repository deliberately accepts the verified caller JWT for every request.
It must never be initialized with a service-role key: PostgreSQL and Storage RLS
are the authority for tenant isolation.
"""
from __future__ import annotations

import os
from pathlib import PurePosixPath
from typing import Any
from uuid import UUID

import httpx


BUCKET = "pulseos-private"
DATASET_TYPES = {"events", "reviews", "documents"}


class DatasetRepositoryError(RuntimeError):
    """A safe-to-report dataset persistence failure."""


class SupabaseDatasetRepository:
    def __init__(
        self,
        *,
        user_id: str,
        access_token: str,
        base_url: str | None = None,
        publishable_key: str | None = None,
        timeout: float = 20.0,
        client: httpx.Client | None = None,
    ):
        try:
            self.user_id = str(UUID(user_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("A valid authenticated user ID is required.") from exc
        if not access_token:
            raise ValueError("A verified user access token is required.")
        self.base_url = (base_url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.publishable_key = publishable_key or os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
        if not self.base_url or not self.publishable_key:
            raise DatasetRepositoryError("Supabase dataset storage is not configured.")
        self._owns_client = client is None
        self.client = client or httpx.Client(timeout=timeout)
        self.headers = {
            "apikey": self.publishable_key,
            "Authorization": f"Bearer {access_token}",
        }

    def close(self):
        if self._owns_client:
            self.client.close()

    def _request(self, method: str, path: str, **kwargs) -> Any:
        try:
            response = self.client.request(
                method, f"{self.base_url}{path}", headers={**self.headers, **kwargs.pop("headers", {})}, **kwargs
            )
        except httpx.RequestError as exc:
            raise DatasetRepositoryError("Supabase dataset storage is temporarily unavailable.") from exc
        if response.status_code >= 400:
            # Do not include upstream body: it can contain user-controlled values.
            raise DatasetRepositoryError(f"Supabase dataset operation failed (HTTP {response.status_code}).")
        if response.status_code == 204 or not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise DatasetRepositoryError("Supabase returned an invalid dataset response.") from exc

    @staticmethod
    def _validate_type(dataset_type: str):
        if dataset_type not in DATASET_TYPES:
            raise ValueError("Dataset type must be events, reviews or documents.")

    def _object_path(self, dataset_id: str, filename: str) -> str:
        safe_name = PurePosixPath(filename.replace("\\", "/")).name
        if not safe_name or safe_name in {".", ".."}:
            raise ValueError("A valid filename is required.")
        return f"{self.user_id}/{dataset_id}/{safe_name}"

    def upload(
        self,
        *,
        dataset_id: str,
        dataset_type: str,
        filename: str,
        contents: bytes,
        row_count: int,
        content_type: str,
    ) -> dict:
        self._validate_type(dataset_type)
        dataset_uuid = str(UUID(dataset_id))
        if row_count < 0:
            raise ValueError("Row count cannot be negative.")
        object_path = self._object_path(dataset_uuid, filename)
        storage_path = f"/storage/v1/object/{BUCKET}/{object_path}"
        self._request(
            "POST",
            storage_path,
            content=contents,
            headers={"Content-Type": content_type or "application/octet-stream", "x-upsert": "false"},
        )
        try:
            rows = self._request(
                "POST",
                "/rest/v1/pulseos_datasets",
                json={
                    "id": dataset_uuid,
                    "owner_id": self.user_id,
                    "dataset_type": dataset_type,
                    "original_filename": PurePosixPath(filename.replace("\\", "/")).name,
                    "object_path": object_path,
                    "row_count": row_count,
                    "content_type": content_type,
                },
                headers={"Prefer": "return=representation"},
            )
        except Exception:
            # Compensate for a metadata insert failure; RLS limits deletion to caller's folder.
            try:
                self._request(
                    "DELETE",
                    f"/storage/v1/object/{BUCKET}",
                    json={"prefixes": [object_path]},
                )
            except DatasetRepositoryError:
                pass
            raise
        if not rows:
            raise DatasetRepositoryError("Supabase did not confirm dataset metadata creation.")
        return rows[0]

    def list_datasets(self) -> list[dict]:
        rows = self._request(
            "GET",
            "/rest/v1/pulseos_datasets",
            params={
                "select": "id,dataset_type,original_filename,row_count,uploaded_at",
                "order": "uploaded_at.desc",
            },
        )
        return rows or []

    def get_dataset(self, dataset_id: str) -> dict | None:
        try:
            dataset_uuid = str(UUID(dataset_id))
        except (ValueError, TypeError, AttributeError):
            return None
        rows = self._request(
            "GET",
            "/rest/v1/pulseos_datasets",
            params={"select": "*", "id": f"eq.{dataset_uuid}", "limit": "1"},
        )
        return rows[0] if rows else None

    def download(self, object_path: str) -> bytes:
        # Never accept arbitrary object paths from a caller; require this user's prefix.
        if not object_path.startswith(f"{self.user_id}/"):
            raise DatasetRepositoryError("Dataset not found.")
        try:
            response = self.client.get(
                f"{self.base_url}/storage/v1/object/{BUCKET}/{object_path}",
                headers=self.headers,
            )
        except httpx.RequestError as exc:
            raise DatasetRepositoryError("Supabase dataset storage is temporarily unavailable.") from exc
        if response.status_code == 404:
            raise DatasetRepositoryError("Stored dataset file was not found.")
        if response.status_code >= 400:
            raise DatasetRepositoryError(f"Supabase dataset download failed (HTTP {response.status_code}).")
        return response.content

    def get_active_datasets(self) -> dict[str, dict | None]:
        rows = self._request(
            "GET",
            "/rest/v1/pulseos_active_datasets",
            params={"select": "dataset_type,dataset_id",},
        ) or []
        result = {kind: None for kind in DATASET_TYPES}
        for row in rows:
            if row.get("dataset_id"):
                result[row["dataset_type"]] = self.get_dataset(row["dataset_id"])
        return result

    def set_active_dataset(self, dataset_type: str, dataset_id: str | None) -> dict | None:
        self._validate_type(dataset_type)
        normalized_id = str(UUID(dataset_id)) if dataset_id is not None else None
        if normalized_id is not None:
            record = self.get_dataset(normalized_id)
            if not record or record["dataset_type"] != dataset_type:
                raise ValueError(f"Selected {dataset_type} dataset was not found.")
        self._request(
            "POST",
            "/rest/v1/pulseos_active_datasets",
            params={"on_conflict": "owner_id,dataset_type"},
            json={"owner_id": self.user_id, "dataset_type": dataset_type, "dataset_id": normalized_id},
            headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )
        return self.get_dataset(normalized_id) if normalized_id else None

    def delete_dataset(self, dataset_id: str) -> bool:
        record = self.get_dataset(dataset_id)
        if not record:
            return False
        object_path = record.get("object_path", "")
        if not object_path.startswith(f"{self.user_id}/"):
            return False
        self._request(
            "DELETE",
            f"/storage/v1/object/{BUCKET}",
            json={"prefixes": [object_path]},
        )
        self._request(
            "DELETE",
            "/rest/v1/pulseos_datasets",
            params={"id": f"eq.{record['id']}"},
        )
        return True
