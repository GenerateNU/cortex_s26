"""
Ingest service: document processing with cognee.
"""

from __future__ import annotations

import errno
import logging
import os
from pathlib import Path

import cognee
from cognee import SearchType

logger = logging.getLogger(__name__)

# Cognee stores its graph and vector data here by default.
COGNEE_SYSTEM_DIR = Path(os.getenv("COGNEE_SYSTEM_PATH", ".cognee_system"))

# Try to import litellm exceptions for precise API error matching.
try:
    import litellm.exceptions as _litellm_exc

    _LLM_EXCEPTIONS: tuple = (
        _litellm_exc.AuthenticationError,
        _litellm_exc.APIConnectionError,
        _litellm_exc.RateLimitError,
        _litellm_exc.APIError,
    )
except Exception:  # pragma: no cover – litellm not installed or changed API
    _LLM_EXCEPTIONS = ()

# Try to import kuzu-specific runtime errors.
try:
    import kuzu as _kuzu

    _KUZU_EXCEPTIONS: tuple = (
        _kuzu.RuntimeError,
        _kuzu.Exception if hasattr(_kuzu, "Exception") else type(None),
    )
except Exception:  # pragma: no cover
    _KUZU_EXCEPTIONS = ()

_STORAGE_EXCEPTIONS = (PermissionError, OSError) + _KUZU_EXCEPTIONS


def check_cognee_storage() -> None:
    """
    Verify that Cognee's local storage directory is writable.

    Call this at startup so failures are caught early with a clear message
    rather than surfacing mid-request.

    Raises:
        RuntimeError: if the directory cannot be created or written to.
    """
    try:
        COGNEE_SYSTEM_DIR.mkdir(parents=True, exist_ok=True)
        probe = COGNEE_SYSTEM_DIR / ".write_check"
        probe.touch()
        probe.unlink()
    except PermissionError as exc:
        raise RuntimeError(
            f"Cognee storage directory '{COGNEE_SYSTEM_DIR}' is not writable. "
            "Check directory permissions before starting the service."
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            f"Cannot access Cognee storage directory '{COGNEE_SYSTEM_DIR}': {exc}"
        ) from exc


def _is_disk_full(exc: OSError) -> bool:
    return getattr(exc, "errno", None) == errno.ENOSPC


def _is_llm_error(exc: Exception) -> bool:
    """Return True when exc originates from an LLM provider (Gemini, OpenAI, …)."""
    if _LLM_EXCEPTIONS and isinstance(exc, _LLM_EXCEPTIONS):
        return True
    module = type(exc).__module__ or ""
    if any(pkg in module for pkg in ("litellm", "openai", "google.api_core")):
        return True
    lowered = str(exc).lower()
    return any(
        phrase in lowered
        for phrase in (
            "api key",
            "authentication",
            "quota exceeded",
            "rate limit",
            "gemini",
            "openai",
            "invalid_api_key",
        )
    )


def _is_dimension_mismatch(exc: Exception) -> bool:
    lowered = str(exc).lower()
    return "dimension" in lowered or "mismatch" in lowered or "wrong number of dimensions" in lowered


async def ingest_document(
    file_path: str,
    dataset_name: str,
    document_id: str = None,
) -> dict:
    """
    Ingest a document into the knowledge graph.

    Calls cognee.add() to ingest the file, then cognee.cognify() to
    process it into chunks, entities, relationships, and summaries.
    Finally extracts structured data from the processed results.

    Returns a dict with "status": "success" or "status": "error".
    Error dicts include an ``error_type`` key so the route layer can map
    them to the correct HTTP status code without inspecting raw messages.

    error_type values:
        "kuzu_storage"           → 503 Service Unavailable
        "llm_api"                → 502 Bad Gateway
        "vector_dimension_mismatch" → 500 Internal Server Error
        "no_data_added"          → 500 Internal Server Error
        "unknown"                → 500 Internal Server Error
    """
    # ------------------------------------------------------------------ add()
    try:
        await cognee.add(file_path, dataset_name)
    except _STORAGE_EXCEPTIONS as exc:
        if isinstance(exc, OSError) and _is_disk_full(exc):
            msg = "Cognee storage is full — free up disk space and retry."
        else:
            msg = (
                f"Cognee storage error during add() — check that "
                f"'{COGNEE_SYSTEM_DIR}' is writable: {exc}"
            )
        logger.error("Kuzu storage failure during add(): %s", exc, exc_info=True)
        return {"status": "error", "error_type": "kuzu_storage", "error": msg}

    # --------------------------------------------------------------- cognify()
    try:
        await cognee.cognify([dataset_name])
    except _STORAGE_EXCEPTIONS as exc:
        if isinstance(exc, OSError) and _is_disk_full(exc):
            msg = "Cognee storage is full during cognify() — free up disk space and retry."
        else:
            msg = (
                f"Cognee storage error during cognify() — check that "
                f"'{COGNEE_SYSTEM_DIR}' is writable: {exc}"
            )
        logger.error("Kuzu storage failure during cognify(): %s", exc, exc_info=True)
        return {"status": "error", "error_type": "kuzu_storage", "error": msg}
    except Exception as exc:
        if _is_llm_error(exc):
            logger.error("LLM API error during cognify(): %s", exc, exc_info=True)
            return {
                "status": "error",
                "error_type": "llm_api",
                "error": f"LLM API error during cognify(): {exc}",
            }
        if _is_dimension_mismatch(exc):
            msg = (
                "Vector dimension mismatch detected during cognify(). "
                "This happens when the embedding model is changed after data was already stored. "
                "To fix: delete the '.cognee_system/' directory and re-ingest all documents."
            )
            logger.error("Vector dimension mismatch: %s", exc, exc_info=True)
            return {"status": "error", "error_type": "vector_dimension_mismatch", "error": msg}
        lowered = str(exc).lower()
        if any(phrase in lowered for phrase in ("no data", "no documents", "dataset is empty")):
            logger.warning(
                "cognify() called on dataset '%s' with no prior add(): %s",
                dataset_name,
                exc,
            )
            return {
                "status": "error",
                "error_type": "no_data_added",
                "error": (
                    f"No documents were added to dataset '{dataset_name}' before cognify(). "
                    "Call add() first."
                ),
            }
        logger.error("Unexpected error during cognify(): %s", exc, exc_info=True)
        return {"status": "error", "error_type": "unknown", "error": str(exc)}

    # --------------------------------------------------- extract results
    try:
        structured_data = await _extract_structured_data(dataset_name)
    except Exception as exc:
        if _is_dimension_mismatch(exc):
            msg = (
                "Vector dimension mismatch detected during search. "
                "This happens when the embedding model is changed after data was already stored. "
                "To fix: delete the '.cognee_system/' directory and re-ingest all documents."
            )
            logger.error("Vector dimension mismatch during search: %s", exc, exc_info=True)
            return {"status": "error", "error_type": "vector_dimension_mismatch", "error": msg}
        logger.error("Unexpected error during search: %s", exc, exc_info=True)
        return {"status": "error", "error_type": "unknown", "error": str(exc)}

    return {
        "status": "success",
        "document_id": document_id,
        "dataset_name": dataset_name,
        **structured_data,
    }


async def _extract_structured_data(dataset_name: str) -> dict:
    """
    Query Cognee for structured data after cognify() has run.

    Uses SearchType.SUMMARIES for pre-computed summaries and
    SearchType.CHUNKS for raw text segments.

    Returns summary (str), entities (list), and raw_chunks_count (int).
    Empty results are not an error — they return empty/zero values.
    """
    summary_results = await cognee.search(
        query_type=SearchType.SUMMARIES,
        query_text=dataset_name,
    )

    chunk_results = await cognee.search(
        query_type=SearchType.CHUNKS,
        query_text=dataset_name,
    )

    summary = summary_results[0] if summary_results else ""

    entities = []
    for chunk in chunk_results:
        if hasattr(chunk, "entities"):
            entities.extend(chunk.entities)

    return {
        "summary": str(summary),
        "entities": entities,
        "raw_chunks_count": len(chunk_results),
    }


async def ingest_document_background(path: Path, dataset_name: str) -> None:
    """
    For FastAPI BackgroundTasks. Allows ingest_document to run in the
    background for large files.
    """
    try:
        await ingest_document(str(path), dataset_name)
    except Exception:
        logger.error("Background ingest failed for %s", path, exc_info=True)
    finally:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
