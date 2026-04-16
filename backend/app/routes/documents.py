"""
Document routes for the Cortex document-intelligence pipeline.

Endpoints
---------
POST /api/documents/upload          – upload up to 5 files, kick off pipeline
GET  /api/documents/graph           – D3-compatible knowledge-graph data
GET  /api/documents/search          – full-text / semantic search
GET  /api/documents/                – list all documents
GET  /api/documents/{doc_id}        – single document by id
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from cognee import SearchType
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.services.cognee_service import search_knowledge_graph
from app.services.document_metadata_service import (
    create_document,
    get_all_documents,
    get_document,
)
from app.services.document_pipeline import run_pipeline
from app.services.graph_service import get_graph_data
from app.services.storage import get_presigned_url

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class UploadedFile(BaseModel):
    id: str
    filename: str


class UploadResponse(BaseModel):
    uploaded: list[UploadedFile]


class DocumentSource(BaseModel):
    id: str
    original_filename: str
    document_type: str | None = None
    dataset_name: str


class SearchResult(BaseModel):
    text: str
    score: float | None = None
    dataset_name: str | None = None
    sources: list[DocumentSource] = []


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = Path("/tmp/cognee_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".csv", ".txt"}
MAX_FILES = 5


# ---------------------------------------------------------------------------
# Endpoints — NOTE: static paths (/graph, /search) must come before /{doc_id}
# ---------------------------------------------------------------------------


@router.post("/upload", response_model=UploadResponse)
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
):
    """
    Accept up to 5 files (.pdf, .csv, .txt), save them to disk, create DB
    records and launch the processing pipeline for each one in the background.
    Returns immediately with the list of doc ids / filenames.
    """
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Maximum {MAX_FILES} files per request.",
        )

    uploaded: list[UploadedFile] = []

    for upload_file in files:
        filename = upload_file.filename or "upload"
        suffix = Path(filename).suffix.lower()

        if suffix not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"File '{filename}' has unsupported extension '{suffix}'. "
                    f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
                ),
            )

        doc_id = await create_document(filename)
        temp_path = UPLOAD_DIR / f"{uuid.uuid4()}{suffix}"

        # Save file to disk
        try:
            contents = await upload_file.read()
            temp_path.write_bytes(contents)
        finally:
            await upload_file.close()

        # Fire-and-forget pipeline
        background_tasks.add_task(run_pipeline, temp_path, doc_id, filename)

        uploaded.append(UploadedFile(id=doc_id, filename=filename))

    return UploadResponse(uploaded=uploaded)


@router.get("/graph")
async def get_graph(
    dataset: str | None = Query(
        default=None, description="Filter by dataset/client name"
    ),
):
    """
    Return a D3-compatible knowledge graph for all documents or a specific
    dataset.
    """
    try:
        data = await get_graph_data(dataset=dataset)
        return data
    except Exception:
        logger.exception("Graph retrieval failed")
        raise HTTPException(status_code=500, detail="Graph retrieval failed") from None


@router.get("/search", response_model=SearchResponse)
async def search_documents(
    q: str = Query(..., description="Search query text"),
    dataset: str | None = Query(default=None, description="Filter by dataset"),
    limit: int = Query(default=20, description="Max results to return"),
    search_type: SearchType = Query(
        default=SearchType.GRAPH_COMPLETION,
        description=(
            "Cognee search type: GRAPH_COMPLETION, CHUNKS, SUMMARIES, "
            "TRIPLET_COMPLETION, GRAPH_COMPLETION_COT"
        ),
    ),
):
    """
    Search the Cognee knowledge graph. Each result includes up to 3 source
    documents from the matching dataset so the frontend can show provenance.
    """
    from app.core.supabase import get_async_supabase

    try:
        raw_results = await search_knowledge_graph(
            query_text=q, dataset=dataset, limit=limit, search_type=search_type
        )

        # Collect unique dataset names across all results
        dataset_names = {
            r["dataset_name"] for r in raw_results if r.get("dataset_name")
        }

        # Batch-fetch up to 3 completed docs per dataset from Supabase
        sb = await get_async_supabase()
        dataset_docs: dict[str, list[DocumentSource]] = {}
        for ds in dataset_names:
            rows = await (
                sb.table("cortex_documents")
                .select("id,original_filename,document_type,dataset_name")
                .eq("dataset_name", ds)
                .eq("status", "completed")
                .order("uploaded_at", desc=True)
                .limit(3)
                .execute()
            )
            dataset_docs[ds] = [DocumentSource(**row) for row in (rows.data or [])]

        # Fallback: top-3 completed docs regardless of dataset
        fallback_rows = await (
            sb.table("cortex_documents")
            .select("id,original_filename,document_type,dataset_name")
            .eq("status", "completed")
            .order("uploaded_at", desc=True)
            .limit(3)
            .execute()
        )
        fallback_docs = [DocumentSource(**row) for row in (fallback_rows.data or [])]

        results = [
            SearchResult(
                text=r["text"],
                score=r.get("score"),
                dataset_name=r.get("dataset_name"),
                sources=dataset_docs.get(r.get("dataset_name", ""), fallback_docs),
            )
            for r in raw_results
        ]

        return SearchResponse(query=q, results=results, total=len(results))

    except Exception:
        logger.exception("Search failed")
        raise HTTPException(status_code=500, detail="Search failed") from None


@router.get("/")
async def list_documents():
    """Return all document records ordered by upload date (newest first)."""
    try:
        return await get_all_documents()
    except Exception:
        logger.exception("Failed to fetch documents")
        raise HTTPException(
            status_code=500, detail="Failed to fetch documents"
        ) from None


@router.get("/{doc_id}/file-url")
async def get_file_url(doc_id: str):
    """
    Return a short-lived pre-signed URL for viewing/downloading the raw file
    stored in Cloudflare R2. 404 if no file has been stored yet.
    """
    try:
        doc = await get_document(doc_id)
    except Exception:
        logger.exception("Failed to retrieve document for file-url")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve document"
        ) from None

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    r2_key = doc.get("file_url")
    if not r2_key:
        raise HTTPException(
            status_code=404, detail="No raw file stored for this document."
        )

    url = get_presigned_url(r2_key)
    if not url:
        raise HTTPException(status_code=503, detail="Object storage not configured.")

    return {"url": url, "filename": doc["original_filename"]}


@router.get("/{doc_id}")
async def get_document_by_id(doc_id: str):
    """Return a single document record. 404 if not found."""
    try:
        doc = await get_document(doc_id)
    except Exception:
        logger.exception("Failed to fetch document")
        raise HTTPException(
            status_code=500, detail="Failed to fetch document"
        ) from None

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")

    return doc
