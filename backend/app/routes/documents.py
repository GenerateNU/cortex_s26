"""
Document routes for Cognee-powered document upload and search.
"""

import os
import shutil
import uuid
from pathlib import Path

from backend.app.services.ingest import ingest_document, search_knowledge_graph
from backend.app.services.storage import (
    download_file_cloudflare,
    upload_file_cloudflare,
)
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

#from app.services.ingest import ingest_document, search_knowledge_graph

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
    Upload a document, ingest it into Cognee, and return structured results.
    """
    document_id = str(uuid.uuid4())
    suffix = Path(file.filename).suffix if file.filename else ".bin"
    temp_path = UPLOAD_DIR / f"{document_id}{suffix}"

    upload_file_cloudflare(temp_path, bucket=os.getenv("CLOUDFLARE_R2_BUCKET_NAME"), key=f"{dataset_name}/{document_id}{suffix}")

    try:
        # Save uploaded file to disk
        with temp_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        file.file.close()

        # Ingest into Cognee
        result = await ingest_document(str(temp_path), dataset_name=dataset_name)

        return UploadResponse(
            status="ok",
            document_id=document_id,
            dataset=dataset_name,
            summary=result["summary"],
            entities=result["entities"],
            raw_chunks_count=result["raw_chunks_count"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}") from e

    finally:
        # Clean up temp file — never leave orphans
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass  # Non-fatal


@router.get("/search", response_model=SearchResponse)
async def search_documents(
    q: str = Query(..., description="Search query text"),
    dataset: str | None = Query(default=None, description="Filter by dataset"),
    limit: int = Query(default=20, description="Max results to return"),
):
    """
    Search the Cognee knowledge graph and return matching results.
    """
    try:
        raw_results = await search_knowledge_graph(
            query_text=q, dataset=dataset, limit=limit
        )

        results = [SearchResult(**r) for r in raw_results]

        return SearchResponse(
            query=q,
            results=results,
            total=len(results),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}") from e

@router.get("/{document_id}", response_model=bytes)
async def get_document(document_id: str, dataset: str):
    """
    Download a document by ID.
    """
    key = f"{dataset}/{document_id}"
    file_bytes = await download_file_cloudflare(bucket=os.getenv("CLOUDFLARE_R2_BUCKET_NAME"), key=key)
    return file_bytes
