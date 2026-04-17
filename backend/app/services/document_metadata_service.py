"""
Document metadata store — Supabase-backed (async).
"""

from __future__ import annotations

import logging
import uuid as _uuid
from datetime import datetime, timedelta, timezone

from app.core.supabase import get_async_supabase

logger = logging.getLogger(__name__)


async def create_document(
    original_filename: str, content_hash: str | None = None
) -> str:
    doc_id = str(_uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    sb = await get_async_supabase()
    row: dict = {
        "id": doc_id,
        "original_filename": original_filename,
        "dataset_name": "processing",
        "status": "processing",
        "progress_stage": "uploading",
        "uploaded_at": now,
    }
    if content_hash:
        row["content_hash"] = content_hash
    await sb.table("cortex_documents").insert(row).execute()
    return doc_id


async def find_document_by_hash(content_hash: str) -> dict | None:
    """Return the first completed document with a matching content hash, or None."""
    sb = await get_async_supabase()
    result = await (
        sb.table("cortex_documents")
        .select("*")
        .eq("content_hash", content_hash)
        .eq("status", "completed")
        .order("uploaded_at", desc=True)
        .limit(1)
        .execute()
    )
    row = result.data[0] if result.data else None
    return _normalize(row) if row else None


async def get_all_documents() -> list[dict]:
    sb = await get_async_supabase()
    result = (
        await sb.table("cortex_documents")
        .select("*")
        .order("uploaded_at", desc=True)
        .execute()
    )
    return [_normalize(r) for r in (result.data or [])]


async def get_document(doc_id: str) -> dict | None:
    sb = await get_async_supabase()
    result = (
        await sb.table("cortex_documents")
        .select("*")
        .eq("id", doc_id)
        .maybe_single()
        .execute()
    )
    if result is None or not getattr(result, "data", None):
        return None
    return _normalize(result.data)


async def update_document_stage(doc_id: str, stage: str) -> None:
    sb = await get_async_supabase()
    await (
        sb.table("cortex_documents")
        .update({"progress_stage": stage})
        .eq("id", doc_id)
        .execute()
    )


def _normalize(row: dict) -> dict:
    """Ensure insights/entities are always lists and file_url is present."""
    import json

    row = dict(row)
    for field in ("insights", "entities"):
        val = row.get(field)
        if isinstance(val, str):
            row[field] = json.loads(val)
        elif val is None:
            row[field] = []
    row.setdefault("file_url", None)
    return row


async def recover_stale_documents(stale_minutes: int = 30) -> int:
    """Mark documents stuck in 'processing' for >stale_minutes as 'failed'."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)).isoformat()
    sb = await get_async_supabase()
    result = await (
        sb.table("cortex_documents")
        .update(
            {
                "status": "failed",
                "progress_stage": "failed",
                "error_message": "Recovered: pipeline did not complete (server restart)",
            }
        )
        .eq("status", "processing")
        .lt("uploaded_at", cutoff)
        .execute()
    )
    count = len(result.data or [])
    if count:
        logger.info("Recovered %d stale documents", count)
    return count
