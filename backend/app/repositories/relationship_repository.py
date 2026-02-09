from uuid import UUID

from supabase._async.client import AsyncClient

from app.schemas.relationship_schemas import RelationshipCreate


class RelationshipRepository:
    def __init__(self, supabase: AsyncClient):
        self.supabase = supabase

    async def get_relationships_by_tenant(self, tenant_id: UUID) -> list[dict]:
        response = await (
            self.supabase.table("relationships")
            .select(
                "id, tenant_id, from_classification_id, to_classification_id, type, "
                "from_classification:classifications!from_classification_id(id, tenant_id, name), "
                "to_classification:classifications!to_classification_id(id, tenant_id, name)"
            )
            .eq("tenant_id", str(tenant_id))
            .execute()
        )
        return response.data or []

    async def delete_all_for_tenant(self, tenant_id: UUID) -> None:
        await (
            self.supabase.table("relationships")
            .delete()
            .eq("tenant_id", str(tenant_id))
            .execute()
        )

    async def create_relationship(self, new_relationship: RelationshipCreate) -> UUID:
        insert_response = await (
            self.supabase.table("relationships")
            .insert(
                {
                    "tenant_id": str(new_relationship.tenant_id),
                    "from_classification_id": str(new_relationship.from_classification_id),
                    "to_classification_id": str(new_relationship.to_classification_id),
                    "type": new_relationship.type,
                }
            )
            .select("id")
            .execute()
        )
        return insert_response.data[0]["id"]
