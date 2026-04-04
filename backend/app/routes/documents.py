"""
Document routes for Cognee-powered document upload and search.
"""

import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pydantic import BaseModel

#from app.services.ingest import ingest_document, search_knowledge_graph

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
    Upload a document, ingest it into Cognee, and return structured results.
    """
    document_id = str(uuid.uuid4())
    suffix = Path(file.filename).suffix if file.filename else ".bin"
    temp_path = UPLOAD_DIR / f"{document_id}{suffix}"

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
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

    finally:
        # Clean up temp file — never leave orphans
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass  # Non-fatal


@router.get("/search", response_model=SearchResponse)
async def search_documents(
    q: str = Query(..., description="Search query text"),
    dataset: Optional[str] = Query(default=None, description="Filter by dataset"),
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
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")
