"""
Ingest service: document processing with cognee.
"""

from __future__ import annotations

import logging
from pathlib import Path

import cognee
from cognee import SearchType

logger = logging.getLogger(__name__)


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
    """
    try:
        await cognee.add(file_path, dataset_name)
        await cognee.cognify([dataset_name])
        structured_data = await _extract_structured_data(dataset_name)

        return {
            "status": "success",
            "document_id": document_id,
            "dataset_name": dataset_name,
            **structured_data,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


async def _extract_structured_data(dataset_name: str) -> dict:
    """
    Query Cognee for structured data after cognify() has run.

    Uses SearchType.SUMMARIES for pre-computed summaries and
    SearchType.CHUNKS for raw text segments.

    Returns summary (str), entities (list), and raw_chunks_count (int).
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