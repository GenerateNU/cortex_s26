from uuid import UUID

from supabase._async.client import AsyncClient


class ClassificationRepository:
    def __init__(self, supabase: AsyncClient):
        self.supabase = supabase

    async def get_classifications_by_tenant(self, tenant_id: UUID) -> list[dict]:
        response = await (
            self.supabase.table("classifications")
            .select("*")
            .eq("tenant_id", str(tenant_id))
            .execute()
        )
        return response.data or []

    async def create_classifications(self, classifications: list[dict]) -> None:
        if not classifications:
            return
        await self.supabase.table("classifications").insert(classifications).execute()

    async def delete_classifications(self, classification_ids: list[str]) -> None:
        if not classification_ids:
            return
        await self.supabase.table("classifications").delete().in_("id", classification_ids).execute()

    async def unlink_files_from_classifications(self, classification_ids: list[str]) -> None:
        if not classification_ids:
            return
        await (
            self.supabase.table("file_uploads")
            .update({"classification_id": None})
            .in_("classification_id", classification_ids)
            .execute()
        )

    async def update_file_classification(self, file_upload_id: UUID, classification_id: UUID) -> bool:
        response = await (
            self.supabase.table("file_uploads")
            .update({"classification_id": str(classification_id)})
            .eq("id", str(file_upload_id))
            .execute()
        )
        return len(response.data) > 0
