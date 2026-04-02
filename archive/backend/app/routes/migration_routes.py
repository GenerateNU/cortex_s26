from uuid import UUID

from fastapi import APIRouter, Depends
from supabase._async.client import AsyncClient

from app.core.supabase import get_async_supabase
from app.services.migration_service import MigrationService

router = APIRouter(prefix="/migrations", tags=["Migrations"])


def get_service(
    supabase: AsyncClient = Depends(get_async_supabase),
) -> MigrationService:
    return MigrationService(supabase)


@router.get("/{tenant_id}")
async def list_migrations(
    tenant_id: UUID, service: MigrationService = Depends(get_service)
):
    return await service.list_migrations(tenant_id)


@router.post("/generate/{tenant_id}")
async def generate_migrations(
    tenant_id: UUID, service: MigrationService = Depends(get_service)
):
    return await service.generate_migrations(tenant_id)


@router.post("/execute/{tenant_id}")
async def execute_migrations(
    tenant_id: UUID, service: MigrationService = Depends(get_service)
):
    await service.execute_migrations(tenant_id)
    return {"message": "Migrations executed successfully"}


@router.post("/load_data/{tenant_id}")
async def load_data(tenant_id: UUID, service: MigrationService = Depends(get_service)):
    return await service.load_data(tenant_id)


@router.get("/connection-url/{tenant_id}")
async def get_connection_url(
    tenant_id: UUID, service: MigrationService = Depends(get_service)
):
    return await service.get_connection_url(tenant_id)
