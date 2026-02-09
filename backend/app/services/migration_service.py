# app/services/migration_service.py
from uuid import UUID

from fastapi import Depends
from supabase._async.client import AsyncClient

from app.core.supabase import get_async_supabase
from app.repositories.migration_repository import MigrationRepository
from app.repositories.schema_repository import SchemaRepository
from app.schemas.migration_schemas import Migration, MigrationCreate


class MigrationService:
    def __init__(self, migration_repo: MigrationRepository, schema_repo: SchemaRepository):
        self.migration_repo = migration_repo
        self.schema_repo = schema_repo

    async def get_migrations(self, tenant_id: UUID) -> list[Migration]:
        rows = await self.migration_repo.get_migrations_by_tenant(tenant_id)
        return [
            Migration(
                migration_id=row["id"],
                tenant_id=row["tenant_id"],
                name=row["name"],
                sql=row["sql"],
                sequence=row["sequence"],
            )
            for row in rows
        ]

    async def create_migration(self, new_migration: MigrationCreate) -> UUID:
        """
        Create a new migration for a tenant.
        """
        return await self.migration_repo.create_migration(new_migration)

    async def execute_migration(self, str_sql: str) -> None:
        await self.schema_repo.execute_sql(str_sql)

    async def execute_migrations(self, tenant_id: UUID) -> None:
        migrations = await self.get_migrations(tenant_id)
        for migration in migrations:
            await self.execute_migration(migration.sql)


def get_migration_service(
    supabase: AsyncClient = Depends(get_async_supabase),
) -> MigrationService:
    return MigrationService(
        MigrationRepository(supabase),
        SchemaRepository(supabase)
    )
