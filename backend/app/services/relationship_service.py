# app/services/relationship_service.py
from uuid import UUID

from fastapi import Depends
from supabase._async.client import AsyncClient

from app.core.supabase import get_async_supabase
from app.repositories.relationship_repository import RelationshipRepository
from app.schemas.classification_schemas import Classification
from app.schemas.relationship_schemas import Relationship, RelationshipCreate


class RelationshipService:
    def __init__(self, relationship_repo: RelationshipRepository):
        self.relationship_repo = relationship_repo

    async def get_relationships(self, tenant_id: UUID) -> list[Relationship]:
        """
        Query relationships for the given tenant joining classifications.
        """
        rows = await self.relationship_repo.get_relationships_by_tenant(tenant_id)

        if not rows:
            return []

        return [
            Relationship(
                relationship_id=row["id"],
                tenant_id=row["tenant_id"],
                type=row["type"],
                from_classification=Classification(
                    classification_id=row["from_classification"]["id"],
                    tenant_id=row["from_classification"]["tenant_id"],
                    name=row["from_classification"]["name"],
                ),
                to_classification=Classification(
                    classification_id=row["to_classification"]["id"],
                    tenant_id=row["to_classification"]["tenant_id"],
                    name=row["to_classification"]["name"],
                ),
            )
            for row in rows
        ]

    async def create_relationship(self, new_relationship: RelationshipCreate) -> UUID:
        """
        Create a new relationship for a tenant.
        """
        return await self.relationship_repo.create_relationship(new_relationship)


def get_relationship_service(
    supabase: AsyncClient = Depends(get_async_supabase),
) -> RelationshipService:
    """Instantiates a RelationshipService object in route parameters"""
    return RelationshipService(RelationshipRepository(supabase))
