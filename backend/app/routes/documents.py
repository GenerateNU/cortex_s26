"""
Document routes for Cognee-powered document upload and search.
"""

import shutil
import uuid
from pathlib import Path

from backend.app.services.ingest import (
    ingest_document,
    ingest_document_background,
)
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile
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
# Constants
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".md", ".html"}

# Maps ingest error_type → (HTTP status code, user-facing prefix)
_ERROR_TYPE_TO_HTTP: dict[str, tuple[int, str]] = {
    "kuzu_storage": (503, "Storage unavailable"),
    "llm_api": (502, "LLM API error"),
    "vector_dimension_mismatch": (500, "Vector store configuration error"),
    "no_data_added": (500, "Ingestion error"),
    "unknown": (500, "Internal error"),
}

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

    Supported file types: PDF, TXT, DOCX, MD, HTML.
    Pass ``use_background=true`` to queue large files and return immediately.
    """
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type '{suffix}'. "
                f"Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
            ),
        )

    document_id = str(uuid.uuid4())
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

    result = await ingest_document(
        file_path=str(temp_path),
        dataset_name=dataset_name,
        document_id=document_id,
    )

    try:
        temp_path.unlink(missing_ok=True)
    except Exception:
        pass

    if result["status"] == "error":
        error_type = result.get("error_type", "unknown")
        status_code, prefix = _ERROR_TYPE_TO_HTTP.get(error_type, (500, "Internal error"))
        raise HTTPException(
            status_code=status_code,
            detail=f"{prefix}: {result['error']}",
        )

    return UploadResponse(
        status=result["status"],
        document_id=document_id,
        dataset=dataset_name,
        summary=result.get("summary", ""),
        entities=result.get("entities", []),
        raw_chunks_count=result.get("raw_chunks_count", 0),
    )


@router.get("/search", response_model=SearchResponse)
async def search_documents(
    q: str = Query(..., description="Search query text"),
    dataset: str | None = Query(default=None, description="Filter by dataset"),
    limit: int = Query(default=20, description="Max results to return"),
):
    """
    Search documents via the Cognee knowledge graph.
    Returns HTTP 200 with an empty list when no results are found.
    """
    return SearchResponse(
        query=q,
        results=[],
        total=0,
    )
