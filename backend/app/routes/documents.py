"""
Document routes for Cognee-powered document upload and search.
Stub endpoints with hardcoded responses for now.
"""

import shutil
import uuid
from pathlib import Path

from backend.app.services.ingest import (
    ingest_document_background,
)
from fastapi import APIRouter, BackgroundTasks, File, Query, UploadFile
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------


class UploadResponse(BaseModel):
    status: str
    document_id: str
    dataset: str
    summary: str | None = ""
    entities: list[str] | None = []
    raw_chunks_count: int | None = 0
    error: str = ""


class SearchResult(BaseModel):
    text: str
    score: float | None = None
    metadata: dict = {}


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int


# ---------------------------------------------------------------------------
# Router setup
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/documents", tags=["documents"])

# Ensure upload directory exists
UPLOAD_DIR = Path("/tmp/cognee_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    dataset_name: str = Query(default="main"),
    use_background: bool = Query(default=False),
):
    """
    Upload a document for Cognee processing.
    Currently returns a hardcoded placeholder response.
    Real logic will be wired in TICKET-10.
    """
    document_id = str(uuid.uuid4())
    suffix = Path(file.filename).suffix
    temp_path = UPLOAD_DIR / f"{document_id}{suffix}"

    try:
        with temp_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
    finally:
        file.file.close()

    if use_background:
        background_tasks.add_task(ingest_document_background, temp_path, dataset_name)
        return UploadResponse(
            status="processing",
            document_id=document_id,
            dataset=dataset_name,
        )

    return UploadResponse(
        status="ok",
        document_id=document_id,
        dataset=dataset_name,
    )


@router.get("/search", response_model=SearchResponse)
async def search_documents(
    q: str = Query(..., description="Search query text"),
    dataset: str | None = Query(default=None, description="Filter by dataset"),
    limit: int = Query(default=20, description="Max results to return"),
):
    """
    Search documents via the Cognee knowledge graph.
    Currently returns a hardcoded empty results list.
    Real logic will be wired in TICKET-10.
    """
    return SearchResponse(
        query=q,
        results=[],
        total=0,
    )

