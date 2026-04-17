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


_BULLET_PREFIXES = ("- ", "* ", "• ", "– ", "— ")


def _split_bulleted(raw: list[str]) -> list[str]:
    """Split bulleted/numbered LLM answers into discrete items.

    GRAPH_COMPLETION returns one narrative string per result; the UI renders
    a list, so we split on newlines and strip leading bullet/number markers.
    """
    items: list[str] = []
    for block in raw:
        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            for prefix in _BULLET_PREFIXES:
                if line.startswith(prefix):
                    line = line[len(prefix) :].strip()
                    break
            else:
                # Strip "1. ", "2) " style numeric prefixes
                head, sep, rest = line.partition(" ")
                if sep and head.rstrip(".)").isdigit():
                    line = rest.strip()
            if line:
                items.append(line)
    return items


def _extract_search_text(result) -> str:
    """Pull a plain string out of a Cognee SearchResult, dict, or raw value."""
    if hasattr(result, "search_result"):
        payload = result.search_result
    elif isinstance(result, dict):
        payload = result.get("search_result", result)
    else:
        payload = result
    if isinstance(payload, list):
        return " ".join(str(p) for p in payload)
    if isinstance(payload, dict):
        return payload.get("text", "") or str(payload)
    return str(payload) if payload is not None else ""


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
    """
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
        # Step 4 – Cognify (build knowledge graph)
        # ------------------------------------------------------------------
        await asyncio.wait_for(
            cognee.cognify(datasets=[client_name]),
            timeout=_COGNEE_TIMEOUT,
        )
        await _update(progress_stage="analyzing")

        # ------------------------------------------------------------------
        # Step 5 – Extract summary
        # ------------------------------------------------------------------
        summary_results = await asyncio.wait_for(
            cognee.search(
                query_text="Provide a concise executive summary of this document.",
                query_type=SearchType.GRAPH_SUMMARY_COMPLETION,
                datasets=[client_name],
            ),
            timeout=_COGNEE_TIMEOUT,
        )
        summary = _extract_search_text(summary_results[0]) if summary_results else ""

        # ------------------------------------------------------------------
        # Step 6 – Extract insights (key relationships & takeaways)
        # ------------------------------------------------------------------
        await _update(progress_stage="extracting_insights")
        insights_results = await asyncio.wait_for(
            cognee.search(
                query_text=(
                    "What are the key insights, relationships, and notable "
                    "takeaways from this document? Return each as a separate "
                    "bullet point."
                ),
                query_type=SearchType.GRAPH_COMPLETION,
                datasets=[client_name],
            ),
            timeout=_COGNEE_TIMEOUT,
        )
        insights: list[str] = _split_bulleted(
            [_extract_search_text(r) for r in (insights_results or [])]
        )

        # ------------------------------------------------------------------
        # Step 7 – Extract entities
        # ------------------------------------------------------------------
        entity_results = await asyncio.wait_for(
            cognee.search(
                query_text=(
                    "List the key named entities in this document "
                    "(people, organizations, products, locations, identifiers). "
                    "Return one entity per line, no descriptions."
                ),
                query_type=SearchType.GRAPH_COMPLETION,
                datasets=[client_name],
            ),
            timeout=_COGNEE_TIMEOUT,
        )
        entities: list[str] = _split_bulleted(
            [_extract_search_text(r) for r in (entity_results or [])]
        )

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
