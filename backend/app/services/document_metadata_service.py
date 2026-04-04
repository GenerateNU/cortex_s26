"""
Document metadata store — Supabase-backed.
"""
from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timezone


def _client():
    import os
    from supabase import create_client
    return create_client(
        os.getenv("SUPABASE_URL", ""),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
    )


async def create_document(supabase, original_filename: str) -> str:
    doc_id = str(_uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    _client().table("cortex_documents").insert({
        "id": doc_id,
        "original_filename": original_filename,
        "dataset_name": "processing",
        "status": "processing",
        "progress_stage": "uploading",
        "uploaded_at": now,
    }).execute()
    return doc_id


async def get_all_documents(supabase) -> list[dict]:
    result = _client().table("cortex_documents").select("*").order(
        "uploaded_at", desc=True
    ).execute()
    return [_normalize(r) for r in (result.data or [])]


async def get_document(supabase, doc_id: str) -> dict | None:
    result = _client().table("cortex_documents").select("*").eq(
        "id", doc_id
    ).maybe_single().execute()
    return _normalize(result.data) if result.data else None


async def update_document_stage(supabase, doc_id: str, stage: str) -> None:
    _client().table("cortex_documents").update(
        {"progress_stage": stage}
    ).eq("id", doc_id).execute()


def _normalize(row: dict) -> dict:
    """Ensure insights/entities are always lists, not raw JSON strings."""
    row = dict(row)
    for field in ("insights", "entities"):
        val = row.get(field)
        if isinstance(val, str):
            import json
            row[field] = json.loads(val)
        elif val is None:
            row[field] = []
    return row
