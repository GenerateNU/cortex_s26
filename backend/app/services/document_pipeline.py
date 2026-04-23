"""
Full document processing pipeline.

run_pipeline() is launched as a FastAPI BackgroundTask and drives a single
document through: R2 upload → text extraction → LLM classification →
Cognee ingestion → knowledge-graph build → metadata extraction → DB write.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import cognee
import litellm
from cognee import SearchType

from app.core.supabase import get_async_supabase
from app.services.storage import upload_to_r2
from app.utils.validation import sanitize_dataset_name

logger = logging.getLogger(__name__)

_VALID_DOC_TYPES = {"RFQ", "PO", "CFG", "Client CSV", "Sales CSV"}
_COGNEE_TIMEOUT = int(os.getenv("COGNEE_TIMEOUT_SECONDS", "300"))

# Serialize run_pipeline() across concurrent uploads so we don't burst
# past Gemini's per-minute embedding cap. One doc fully completes (or
# fails) before the next pipeline starts. Upload response still returns
# immediately; docs queue as status="processing".
_PIPELINE_LOCK = asyncio.Lock()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _llm_model() -> str:
    return os.getenv("LLM_MODEL", "gemini/gemini-flash-latest")


def _llm_api_key() -> str:
    return os.getenv("LLM_API_KEY", "")


def _extract_text_from_pdf(file_path: Path, max_pages: int = 2) -> str:
    """Return plain text from the first *max_pages* pages of a PDF."""
    try:
        from pypdf import PdfReader
    except ImportError:
        logger.warning("pypdf not available; skipping PDF text extraction")
        return ""
    try:
        reader = PdfReader(str(file_path))
        return "\n".join(p.extract_text() or "" for p in reader.pages[:max_pages])
    except Exception as exc:
        logger.warning("PDF text extraction failed: %s", exc)
        return ""


async def _call_llm(prompt: str, max_retries: int = 6) -> str:
    """Async LLM call with exponential backoff on rate-limit errors."""
    delay = 15
    for attempt in range(max_retries):
        try:
            response = await litellm.acompletion(
                model=_llm_model(),
                messages=[{"role": "user", "content": prompt}],
                api_key=_llm_api_key(),
            )
            return response.choices[0].message.content.strip()
        except litellm.RateLimitError:
            if attempt == max_retries - 1:
                raise
            wait = delay * (2**attempt)
            logger.warning(
                "LLM rate limit, retrying in %ss (attempt %d/%d)",
                wait,
                attempt + 1,
                max_retries,
            )
            await asyncio.sleep(wait)
    return ""  # pragma: no cover – loop always returns or raises


def _extract_summary_text(result) -> str:
    """SUMMARIES returns payload dicts with a 'text' field."""
    if isinstance(result, dict):
        return result.get("text") or result.get("summary") or ""
    payload = getattr(result, "payload", None)
    if isinstance(payload, dict):
        return payload.get("text") or payload.get("summary") or ""
    return getattr(result, "text", "") or ""


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


async def run_pipeline(
    file_path: Path,
    doc_id: str,
    original_filename: str,
) -> None:
    """
    Full processing pipeline for a single document.

    Progress stages written to DB:
        uploading → ingesting → building_graph → analyzing
        → extracting_insights → completed  (or failed)

    Serialized via `_PIPELINE_LOCK`: if several uploads arrive at once,
    each pipeline waits for the prior one to finish. Upload response still
    returns immediately — docs queue as status="processing".
    """
    async with _PIPELINE_LOCK:
        await _run_pipeline_locked(file_path, doc_id, original_filename)


async def _run_pipeline_locked(
    file_path: Path,
    doc_id: str,
    original_filename: str,
) -> None:
    sb = await get_async_supabase()

    async def _update(**fields) -> None:
        try:
            await sb.table("cortex_documents").update(fields).eq("id", doc_id).execute()
        except Exception as exc:
            logger.warning("DB update failed for doc %s: %s", doc_id, exc)

    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    try:
        # ------------------------------------------------------------------
        # Step 1 – Upload raw file to Cloudflare R2
        # ------------------------------------------------------------------
        r2_key = f"documents/{doc_id}/{original_filename}"
        file_url = await upload_to_r2(str(file_path), r2_key)
        if file_url:
            await _update(file_url=file_url)

        # ------------------------------------------------------------------
        # Step 2 – Extract text, detect client name + document type (1 LLM call)
        # ------------------------------------------------------------------
        await _update(progress_stage="ingesting")

        doc_text = ""
        if file_path.suffix.lower() == ".pdf":
            doc_text = _extract_text_from_pdf(file_path, max_pages=2)

        if doc_text:
            combined_raw = await _call_llm(
                "Answer two questions about this document. Reply with exactly two lines:\n"
                "Line 1: The company or client name (or 'Unknown' if unclear).\n"
                "Line 2: Document type — exactly one of: RFQ, PO, CFG, Client CSV, Sales CSV "
                "(or 'Unknown' if none match).\n\n"
                f"{doc_text[:4000]}"
            )
            lines = [
                ln.strip().strip('"').strip("'")
                for ln in combined_raw.splitlines()
                if ln.strip()
            ]
            client_name_raw = lines[0] if lines else "Unknown"
            doc_type_raw = lines[1] if len(lines) > 1 else "Unknown"
            client_name = sanitize_dataset_name(client_name_raw)
            document_type = doc_type_raw if doc_type_raw in _VALID_DOC_TYPES else None
        else:
            client_name = "Unknown"
            document_type = None

        await _update(dataset_name=client_name)

        # ------------------------------------------------------------------
        # Step 3 – Add to Cognee
        # ------------------------------------------------------------------
        await asyncio.wait_for(
            cognee.add(str(file_path), dataset_name=client_name),
            timeout=_COGNEE_TIMEOUT,
        )
        await _update(progress_stage="building_graph")

        # ------------------------------------------------------------------
        # Step 4 – Cognify (build knowledge graph for this dataset)
        # ------------------------------------------------------------------
        await asyncio.wait_for(
            cognee.cognify(datasets=[client_name]),
            timeout=_COGNEE_TIMEOUT,
        )
        await _update(progress_stage="analyzing")

        # ------------------------------------------------------------------
        # Step 5 – Summary via SearchType.SUMMARIES (pre-generated by cognify)
        # ------------------------------------------------------------------
        summary_results = await asyncio.wait_for(
            cognee.search(
                query_text=original_filename,
                query_type=SearchType.SUMMARIES,
                datasets=[client_name],
            ),
            timeout=_COGNEE_TIMEOUT,
        )
        summary_texts = [
            t for t in (_extract_summary_text(r) for r in (summary_results or [])) if t
        ]
        summary = "\n\n".join(summary_texts[:5])

        # ------------------------------------------------------------------
        # Step 6 – Insights + Entities scoped to this dataset.
        # Cognee tags every node/edge with `dataset_id` in its relational
        # store, so we can read this dataset's subgraph directly — no
        # global snapshot diff, no concurrent-upload race.
        # ------------------------------------------------------------------
        await _update(progress_stage="extracting_insights")

        from cognee.modules.data.methods.get_authorized_dataset_by_name import (
            get_authorized_dataset_by_name,
        )
        from cognee.modules.graph.methods import (
            get_dataset_related_edges,
            get_dataset_related_nodes,
        )
        from cognee.modules.users.methods.get_default_user import get_default_user

        insights: list[str] = []
        entities: list[str] = []

        cognee_user = await get_default_user()
        dataset = await get_authorized_dataset_by_name(
            dataset_name=client_name, user=cognee_user, permission_type="read"
        )
        if dataset is None:
            logger.warning(
                "No Cognee dataset found for client_name=%r (user=%s); "
                "insights/entities will be empty",
                client_name,
                getattr(cognee_user, "email", "?"),
            )
            ds_nodes, ds_edges = [], []
        else:
            ds_nodes = await get_dataset_related_nodes(dataset.id)
            ds_edges = await get_dataset_related_edges(dataset.id)
            logger.info(
                "Dataset %r (id=%s): %d nodes, %d edges",
                client_name,
                dataset.id,
                len(ds_nodes),
                len(ds_edges),
            )

        if ds_nodes or ds_edges:
            _STRUCTURAL_TYPES = {
                "TextDocument",
                "DocumentChunk",
                "TextSummary",
                "IndexSchema",
                "Document",
            }

            def _node_label(node) -> str:
                if node.label:
                    return str(node.label)
                attrs = node.attributes or {}
                return str(
                    attrs.get("name")
                    or attrs.get("text")
                    or attrs.get("label")
                    or node.id
                )

            # Edges reference nodes by `slug` (the DataPoint's original id),
            # not by Node.id (which is a derived uuid5). See cognee's
            # upsert_nodes / upsert_edges.
            entity_nodes_by_slug: dict[str, object] = {}
            for n in ds_nodes:
                if (n.type or "") in _STRUCTURAL_TYPES:
                    continue
                entity_nodes_by_slug[str(n.slug)] = n

            seen_labels: set[str] = set()
            for n in entity_nodes_by_slug.values():
                label = _node_label(n).strip()
                if label and label not in seen_labels:
                    seen_labels.add(label)
                    entities.append(label)

            seen_triplets: set[str] = set()
            for e in ds_edges:
                sid = str(e.source_node_id)
                tid = str(e.destination_node_id)
                src = entity_nodes_by_slug.get(sid)
                dst = entity_nodes_by_slug.get(tid)
                if src is None or dst is None:
                    continue
                source_label = _node_label(src).strip()
                target_label = _node_label(dst).strip()
                rel_label = (
                    str(e.relationship_name or "related_to").replace("_", " ").strip()
                )
                if not (source_label and target_label):
                    continue
                triplet = f"{source_label} → {rel_label} → {target_label}"
                if triplet in seen_triplets:
                    continue
                seen_triplets.add(triplet)
                insights.append(triplet)

        # ------------------------------------------------------------------
        # Step 8 – Write final state to DB
        # ------------------------------------------------------------------
        await _update(
            status="completed",
            progress_stage="completed",
            dataset_name=client_name,
            document_type=document_type,
            summary=summary,
            insights=json.dumps(insights),
            entities=json.dumps(entities),
            raw_chunks_count=len(summary_results) if summary_results else 0,
            completed_at=_now(),
        )

    except Exception as exc:
        logger.exception("Pipeline failed for doc %s: %s", doc_id, exc)
        await _update(
            status="failed",
            progress_stage="failed",
            error_message=str(exc),
            completed_at=_now(),
        )

    finally:
        try:
            file_path.unlink(missing_ok=True)
        except Exception:
            pass
