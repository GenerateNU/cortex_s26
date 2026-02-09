# app/services/classification_service.py
import json
from uuid import UUID

from fastapi import Depends
from supabase._async.client import AsyncClient

from app.core.supabase import get_async_supabase
from app.repositories.classification_repository import ClassificationRepository
from app.repositories.extraction_repository import ExtractionRepository
from app.schemas.classification_schemas import Classification, ExtractedFile


class ClassificationService:
    def __init__(self, classification_repo: ClassificationRepository, extraction_repo: ExtractionRepository):
        self.classification_repo = classification_repo
        self.extraction_repo = extraction_repo

    async def get_extracted_files(self, tenant_id: UUID) -> list[ExtractedFile]:
        """
        Query extracted files with embeddings joined to file uploads
        """
        rows = await self.extraction_repo.get_extracted_files_with_embeddings(tenant_id)

        if not rows:
            return []

        return [
            ExtractedFile(
                file_upload_id=row["file_uploads"]["id"],
                type=row["file_uploads"]["type"],
                name=row["file_uploads"]["name"],
                tenant_id=row["file_uploads"]["tenant_id"],
                extracted_file_id=row["id"],
                extracted_data=row["extracted_data"],
                embedding=json.loads(row["embedding"])
                if isinstance(row["embedding"], str)
                else row["embedding"],
                classification=Classification(
                    classification_id=row["file_uploads"]["classifications"]["id"],
                    tenant_id=row["file_uploads"]["classifications"]["tenant_id"],
                    name=row["file_uploads"]["classifications"]["name"],
                )
                if row["file_uploads"].get("classifications")
                else None,
            )
            for row in rows
        ]

    async def get_classifications(self, tenant_id: UUID) -> list[Classification]:
        """
        Query classifications for the given tenant
        """
        rows = await self.classification_repo.get_classifications_by_tenant(tenant_id)

        return [
            Classification(
                classification_id=row["id"],
                tenant_id=row["tenant_id"],
                name=row["name"],
            )
            for row in rows
        ]

    async def set_classifications(
        self, tenant_id: UUID, classification_names: list[str]
    ) -> list[Classification]:
        """
        Set classifications for a tenant. Creates new ones, keeps existing ones, and deletes missing ones.
        Files linked to deleted classifications will have their classification_id set to NULL.
        """
        # Get existing classifications
        existing = await self.get_classifications(tenant_id)
        existing_names = {c.name for c in existing}
        existing_by_name = {c.name: c for c in existing}

        new_names = set(classification_names)

        # Determine operations
        to_create = new_names - existing_names
        to_delete = existing_names - new_names

        # Create new classifications
        if to_create:
            await self.classification_repo.create_classifications(
                [{"tenant_id": str(tenant_id), "name": name} for name in to_create]
            )

        # Delete removed classifications
        if to_delete:
            ids_to_delete = [
                str(existing_by_name[name].classification_id) for name in to_delete
            ]

            # First, unlink files
            await self.classification_repo.unlink_files_from_classifications(ids_to_delete)

            # Then delete classifications
            await self.classification_repo.delete_classifications(ids_to_delete)

        # Return updated list
        return await self.get_classifications(tenant_id)

    async def classify_file(
        self, file_upload_id: UUID, classification_id: UUID
    ) -> bool:
        """
        Set the classification for a file upload.
        Returns True if successful, False otherwise.
        """
        return await self.classification_repo.update_file_classification(file_upload_id, classification_id)


def get_classification_service(
    supabase: AsyncClient = Depends(get_async_supabase),
) -> ClassificationService:
    """Instantiates a ClassificationService object in route parameters"""
    return ClassificationService(
        ClassificationRepository(supabase),
        ExtractionRepository(supabase)
    )
