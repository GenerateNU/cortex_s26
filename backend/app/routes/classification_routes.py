import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase._async.client import AsyncClient

from app.core.supabase import get_async_supabase
from app.services.classification_service import ClassificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/classification", tags=["Classification"])


def get_service(
    supabase: AsyncClient = Depends(get_async_supabase),
) -> ClassificationService:
    return ClassificationService(supabase)


@router.get("/list/{tenant_id}")
async def list_classifications(
    tenant_id: UUID, service: ClassificationService = Depends(get_service)
):
    try:
        return await service.get_classifications(tenant_id)
    except Exception:
        logger.exception("Failed to list classifications")
        raise HTTPException(
            status_code=500, detail="Failed to list classifications"
        ) from None


@router.post("/create_classifications/{tenant_id}")
async def create_classifications(
    tenant_id: UUID,
    service: ClassificationService = Depends(get_service),
):
    """
    Generate valid classifications based on existing unclassified documents.
    """
    try:
        defaults = ["Invoices", "Contracts", "Specifications", "Receipts"]
        return await service.create_classifications_batch(tenant_id, defaults)
    except Exception:
        logger.exception("Failed to create classifications")
        raise HTTPException(
            status_code=500, detail="Failed to create classifications"
        ) from None


@router.post("/classify_files/{tenant_id}")
async def classify_files(
    tenant_id: UUID, service: ClassificationService = Depends(get_service)
):
    """
    Assign existing classifications to unclassified files.
    """
    try:
        return await service.classify_files(tenant_id)
    except Exception:
        logger.exception("Failed to classify files")
        raise HTTPException(
            status_code=500, detail="Failed to classify files"
        ) from None


@router.get("/visualize_clustering/{tenant_id}")
async def visualize_clustering(
    tenant_id: UUID, service: ClassificationService = Depends(get_service)
):
    try:
        return await service.get_clustering_visualization(tenant_id)
    except Exception:
        logger.exception("Failed to visualize clustering")
        raise HTTPException(
            status_code=500, detail="Failed to visualize clustering"
        ) from None
