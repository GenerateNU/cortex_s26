"""
Ingest service: document processing with cognee.
"""

from __future__ import annotations

import logging
from pathlib import Path


logger = logging.getLogger(__name__)


async def ingest_document(path: Path, dataset_name: str) -> dict:
   pass

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