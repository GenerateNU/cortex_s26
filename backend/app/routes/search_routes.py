from fastapi import APIRouter, Depends, HTTPException
from supabase._async.client import AsyncClient

from app.core.supabase import get_async_supabase
from app.schemas.search_schemas import SearchRequest, SearchResponse, SearchResult
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["Search"])

def get_search_service(supabase: AsyncClient = Depends(get_async_supabase)) -> SearchService:
    return SearchService(supabase)

@router.post("/", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    service: SearchService = Depends(get_search_service)
):
    """
    Semantic search across extracted documents.
    """
    try:
        results = await service.search(request.query, request.limit, request.threshold)

        # Map to schema
        mapped_results = [
            SearchResult(
                file_id=r["file_id"],
                file_name=r.get("file_name"),
                file_type=r.get("file_type"),
                summary=r.get("summary"),
                extracted_json=r.get("extracted_json"),
                similarity=r["similarity"]
            )
            for r in results
        ]

        return SearchResponse(results=mapped_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
