from uuid import UUID

from supabase._async.client import AsyncClient

from app.schemas.migration_schemas import MigrationCreate


class MigrationRepository:
    def __init__(self, supabase: AsyncClient):
        self.supabase = supabase

    async def get_migrations_by_tenant(self, tenant_id: UUID) -> list[dict]:
        response = await (
            self.supabase.table("migrations")
            .select("id, tenant_id, name, sql, sequence")
            .order("sequence", desc=False)
            .eq("tenant_id", str(tenant_id))
            .execute()
        )
        return response.data or []

    async def create_migration(self, new_migration: MigrationCreate) -> UUID:
        insert_response = await (
            self.supabase.table("migrations")
            .insert(
                {
                    "tenant_id": str(new_migration.tenant_id),
                    "name": new_migration.name,
                    "sql": new_migration.sql,
                    "sequence": new_migration.sequence,
                }
            )
            .execute()
        )
        return insert_response.data[0]["id"]
