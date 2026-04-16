import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase._async.client import AsyncClient

from app.core.supabase import get_async_supabase
from app.services.migration_service import MigrationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/migrations", tags=["Migrations"])


def get_service(
    supabase: AsyncClient = Depends(get_async_supabase),
) -> MigrationService:
    return MigrationService(supabase)


@router.get("/{tenant_id}")
async def list_migrations(
    tenant_id: UUID, service: MigrationService = Depends(get_service)
):
    try:
        return await service.list_migrations(tenant_id)
    except Exception:
        logger.exception("Failed to list migrations")
        raise HTTPException(
            status_code=500, detail="Failed to list migrations"
        ) from None


@router.post("/generate/{tenant_id}")
async def generate_migrations(
    tenant_id: UUID, service: MigrationService = Depends(get_service)
):
    try:
        return await service.generate_migrations(tenant_id)
    except Exception:
        logger.exception("Failed to generate migrations")
        raise HTTPException(
            status_code=500, detail="Failed to generate migrations"
        ) from None


@router.post("/execute/{tenant_id}")
async def execute_migrations(
    tenant_id: UUID, service: MigrationService = Depends(get_service)
):
    try:
        await service.execute_migrations(tenant_id)
        return {"message": "Migrations executed successfully"}
    except Exception:
        logger.exception("Failed to execute migrations")
        raise HTTPException(
            status_code=500, detail="Failed to execute migrations"
        ) from None


@router.post("/load_data/{tenant_id}")
async def load_data(tenant_id: UUID, service: MigrationService = Depends(get_service)):
    try:
        return await service.load_data(tenant_id)
    except Exception:
        logger.exception("Failed to load data")
        raise HTTPException(status_code=500, detail="Failed to load data") from None


@router.get("/connection-url/{tenant_id}")
async def get_connection_url(
    tenant_id: UUID, service: MigrationService = Depends(get_service)
):
    try:
        return await service.get_connection_url(tenant_id)
    except Exception:
        logger.exception("Failed to get connection URL")
        raise HTTPException(
            status_code=500, detail="Failed to get connection URL"
        ) from None
