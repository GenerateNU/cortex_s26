import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase._async.client import AsyncClient

from app.core.supabase import get_async_supabase
from app.services.pattern_recognition_service import PatternRecognitionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pattern-recognition", tags=["Pattern Recognition"])


def get_service(
    supabase: AsyncClient = Depends(get_async_supabase),
) -> PatternRecognitionService:
    return PatternRecognitionService(supabase)


@router.post("/analyze/{tenant_id}")
async def analyze_relationships(
    tenant_id: UUID, service: PatternRecognitionService = Depends(get_service)
):
    """
    Analyzes relationships for the given tenant.
    Note: tenant_id is kept for URL compatibility but ignored by service.
    """
    try:
        return await service.analyze_relationships(tenant_id)
    except Exception:
        logger.exception("Failed to analyze relationships")
        raise HTTPException(
            status_code=500, detail="Failed to analyze relationships"
        ) from None


@router.get("/graph")
async def get_graph_data(service: PatternRecognitionService = Depends(get_service)):
    """
    Returns nodes and edges for the relationship graph.
    """
    try:
        return await service.get_graph_data()
    except Exception:
        logger.exception("Failed to get graph data")
        raise HTTPException(
            status_code=500, detail="Failed to get graph data"
        ) from None
