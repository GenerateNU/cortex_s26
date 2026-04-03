"""
Document routes for Cognee-powered document upload and search.
Stub endpoints with hardcoded responses for now.
"""

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pydantic import BaseModel

from app.utils.validation import validate_dataset_name

# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------


class UploadResponse(BaseModel):
    status: str
    document_id: str
    dataset: str
    summary: str = ""
    entities: list[str] = []
    raw_chunks_count: int = 0
    error: str = ""


class SearchResult(BaseModel):
    text: str
    score: Optional[float] = None
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
    file: UploadFile = File(...),
    dataset_name: str = Query(default="main"),
):
    """
    Upload a document for Cognee processing.
    Currently returns a hardcoded placeholder response.
    Real logic will be wired in TICKET-10.
    """
    try:
        validate_dataset_name(dataset_name)
    except ValueError as e:
        raise HTTPException(status_code=422)
    return UploadResponse(
        status="ok",
        document_id="test-123",
        dataset=dataset_name,
    )


@router.get("/search", response_model=SearchResponse)
async def search_documents(
    q: str = Query(..., description="Search query text"),
    datasets: Optional[str] = Query(default=None, description="Comma-separated dataset names)"),
    limit: int = Query(default=20, description="Max results to return"),
):
    """
    Search documents via the Cognee knowledge graph.
    Currently returns a hardcoded empty results list.
    Real logic will be wired in TICKET-10.
    """
    # Convert comma-separated string to list
    dataset_list: list[str] = []
    if datasets:
        dataset_list = [d.strip() for d in datasets.split(",")]
    
    return SearchResponse(
        query=q,
        results=[],
        total=0,
    )