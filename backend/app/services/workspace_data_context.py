"""Request-scoped, owner-isolated dataset context for analytics services.

The context is populated only after verifying a Supabase JWT. Dataset bytes are
fetched with that user's JWT, so Supabase RLS and Storage policies remain the
authorization boundary. ContextVars prevent concurrent requests from sharing data.
"""
from __future__ import annotations

from contextvars import ContextVar, Token
from io import BytesIO
from typing import Any

import pandas as pd

from app.services.supabase_dataset_repository import (
    DatasetRepositoryError,
    SupabaseDatasetRepository,
)

_workspace_data: ContextVar[dict[str, dict[str, Any]] | None] = ContextVar(
    "pulseos_workspace_data", default=None
)


def current_workspace_data() -> dict[str, dict[str, Any]] | None:
    """Return this request's loaded datasets, or None for legacy admin requests."""
    return _workspace_data.get()


def set_workspace_data(data: dict[str, dict[str, Any]]) -> Token:
    return _workspace_data.set(data)


def reset_workspace_data(token: Token) -> None:
    _workspace_data.reset(token)


def load_workspace_data(claims: dict) -> dict[str, dict[str, Any]]:
    """Load only the authenticated user's active datasets from RLS-protected storage."""
    repository = SupabaseDatasetRepository(
        user_id=claims["sub"],
        access_token=claims["_access_token"],
    )
    try:
        active = repository.get_active_datasets()
        loaded: dict[str, dict[str, Any]] = {}
        for dataset_type, record in active.items():
            if not record:
                continue
            raw = repository.download(record["object_path"])
            if dataset_type == "documents":
                frame = None
                text = raw.decode("utf-8")
            else:
                frame = pd.read_csv(BytesIO(raw))
                text = None
            loaded[dataset_type] = {
                "record": record,
                "dataframe": frame,
                "text": text,
            }
        return loaded
    except DatasetRepositoryError:
        raise
    finally:
        repository.close()
