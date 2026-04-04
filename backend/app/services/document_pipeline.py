"""
Full document processing pipeline.

run_pipeline() is meant to be launched as a FastAPI BackgroundTask.
It drives a single document through all stages: text extraction,
LLM-based client detection and classification, Cognee ingestion,
knowledge-graph build, and final metadata extraction.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import cognee
import litellm
from cognee import SearchType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LLM_MODEL = "gemini/gemini-flash-latest"


def _llm_api_key() -> str:
    return os.getenv("LLM_API_KEY", "")


def _extract_text_from_pdf(file_path: Path, max_pages: int = 2) -> str:
    """Return text from the first *max_pages* pages of a PDF file."""
    try:
        from pypdf import PdfReader  # pypdf ships with cognee
    except ImportError:
        logger.warning("pypdf not available; skipping PDF text extraction")
        return ""

    try:
        reader = PdfReader(str(file_path))
        pages = reader.pages[:max_pages]
        return "\n".join(page.extract_text() or "" for page in pages)
    except Exception as exc:
        logger.warning("PDF text extraction failed: %s", exc)
        return ""


def _call_llm(prompt: str, max_retries: int = 6) -> str:
    """Synchronous wrapper around litellm.completion with exponential backoff."""
    import time

    delay = 15  # seconds between retries
    for attempt in range(max_retries):
        try:
            response = litellm.completion(
                model=_LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                api_key=_llm_api_key(),
            )
            return response.choices[0].message.content.strip()
        except litellm.RateLimitError:
            if attempt == max_retries - 1:
                raise
            wait = delay * (2 ** attempt)
            logger.warning("LLM rate limit hit, retrying in %ss (attempt %d/%d)", wait, attempt + 1, max_retries)
            time.sleep(wait)
    return ""


def _extract_search_text(result) -> str:
    """
    Pull a plain string out of a Cognee SearchResult object, dict, or raw value.
    Handles payload shapes: string, list-of-strings, dict.
    """
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


def _format_insights(raw_results: list) -> list[str]:
    """
    Convert TRIPLET_COMPLETION search results into a list of
    "subject -> predicate -> object" strings.
    """
    formatted: list[str] = []
    for item in raw_results:
        # Unwrap SearchResult wrapper if present
        if hasattr(item, "search_result"):
            payload = item.search_result
        elif isinstance(item, dict):
            payload = item.get("search_result", item)
        else:
            payload = item

        # Triplet as tuple/list
        if isinstance(payload, (tuple, list)) and len(payload) == 3:
            formatted.append(f"{payload[0]} -> {payload[1]} -> {payload[2]}")
            continue

        # String form "A -> rel -> B" or something else
        text = None
        if isinstance(payload, str):
            text = payload
        elif isinstance(payload, list):
            text = " ".join(str(p) for p in payload)
        elif isinstance(payload, dict):
            text = payload.get("text") or str(payload)
        else:
            text = str(payload) if payload is not None else None

        if text:
            parts = [p.strip() for p in text.split(" -> ")]
            if len(parts) == 3:
                formatted.append(f"{parts[0]} -> {parts[1]} -> {parts[2]}")
            else:
                formatted.append(text)

    return formatted


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


async def run_pipeline(
    file_path: Path,
    doc_id: str,
    original_filename: str,
    supabase,
) -> None:
    """
    Full processing pipeline for a single document.

    Progress stages (written to DB):
        uploading  → ingesting → building_graph → analyzing
        → extracting_insights → completed  (or failed)
    """

    def _update(**fields) -> None:
        try:
            from supabase import create_client
            sb = create_client(
                os.getenv("SUPABASE_URL", ""),
                os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
            )
            sb.table("cortex_documents").update(fields).eq("id", doc_id).execute()
        except Exception as exc:
            logger.warning("DB update failed for doc %s: %s", doc_id, exc)

    try:
        # ------------------------------------------------------------------
        # Step 1 – Detect client / company name
        # ------------------------------------------------------------------
        _update(progress_stage="ingesting")

        suffix = file_path.suffix.lower()
        doc_text = ""
        if suffix == ".pdf":
            doc_text = _extract_text_from_pdf(file_path, max_pages=2)

        import re
        if doc_text:
            combined_raw = _call_llm(
                f"Answer two questions about this document. Reply with exactly two lines:\n"
                f"Line 1: The company or client name (or 'Unknown' if unclear).\n"
                f"Line 2: Document type — exactly one of: RFQ, PO, Invoice, Sales, Client Data (or 'Unknown').\n\n"
                f"{doc_text[:4000]}"
            )
            lines = [l.strip().strip('"').strip("'") for l in combined_raw.splitlines() if l.strip()]
            client_name_raw = lines[0] if len(lines) > 0 else "Unknown"
            doc_type_raw = lines[1] if len(lines) > 1 else "Unknown"
            # Cognee dataset names cannot contain spaces or dots
            client_name = re.sub(r"[^A-Za-z0-9_]", "_", client_name_raw).strip("_") or "Unknown"
            document_type = doc_type_raw or "Unknown"
        else:
            client_name = "Unknown"
            document_type = "Unknown"

        _update(dataset_name=client_name)

        # ------------------------------------------------------------------
        # Step 3 – Add to Cognee
        # ------------------------------------------------------------------
        await cognee.add(str(file_path), dataset_name=client_name)
        _update(progress_stage="building_graph")

        # ------------------------------------------------------------------
        # Step 4 – Cognify (build knowledge graph)
        # ------------------------------------------------------------------
        await cognee.cognify(datasets=[client_name])
        _update(progress_stage="analyzing")

        # ------------------------------------------------------------------
        # Step 5 – Extract summary
        # ------------------------------------------------------------------
        summary_results = await cognee.search(
            query_text="Summarize this document",
            query_type=SearchType.CHUNKS,
            datasets=[client_name],
        )
        summary = _extract_search_text(summary_results[0]) if summary_results else ""

        # ------------------------------------------------------------------
        # Step 6 – Extract insights
        # ------------------------------------------------------------------
        _update(progress_stage="extracting_insights")
        insights_results = await cognee.search(
            query_text="What are all the entities and relationships?",
            query_type=SearchType.CHUNKS,
            datasets=[client_name],
        )
        insights: list[str] = [
            _extract_search_text(r) for r in (insights_results or [])
        ]

        # ------------------------------------------------------------------
        # Step 7 – Extract entities
        # ------------------------------------------------------------------
        entity_results = await cognee.search(
            query_text="List all entities",
            query_type=SearchType.CHUNKS,
            datasets=[client_name],
        )
        entities: list[str] = [
            _extract_search_text(r) for r in (entity_results or [])
        ]

        # ------------------------------------------------------------------
        # Step 8 – Write final state to DB
        # ------------------------------------------------------------------
        _update(
            status="completed",
            progress_stage="completed",
            dataset_name=client_name,
            document_type=document_type,
            summary=summary,
            insights=json.dumps(insights),
            entities=json.dumps(entities),
            raw_chunks_count=len(summary_results) if summary_results else 0,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as exc:  # Step 9 – Error handling
        logger.exception("Pipeline failed for doc %s: %s", doc_id, exc)
        try:
            _update(
                status="failed",
                progress_stage="failed",
                error_message=str(exc),
            )
        except Exception:
            pass

    finally:  # Step 10 – Cleanup temp file
        try:
            file_path.unlink(missing_ok=True)
        except Exception:
            pass
