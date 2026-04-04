"""
Ingest service: document processing with cognee.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.services.cognee_service import ingest_document as _cognee_ingest

logger = logging.getLogger(__name__)


async def ingest_document(path: Path, dataset_name: str) -> dict:
    return await _cognee_ingest(str(path), dataset_name=dataset_name)


async def ingest_document_background(path: Path, dataset_name: str) -> None:
    """
    For FastAPI BackgroundTasks. Allows ingest_document to run in the background for large files.
    """
    try:
        await ingest_document(path, dataset_name)
    except Exception:
        logger.error("Background ingest failed for %s", path, exc_info=True)
    finally:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
