from uuid import UUID

from supabase._async.client import AsyncClient


class ExtractionRepository:
    def __init__(self, supabase: AsyncClient):
        self.supabase = supabase

    async def create_queued_extraction(self, file_upload_id: UUID) -> UUID:
        result = await (
            self.supabase.table("extracted_files")
            .insert(
                {
                    "status": "queued",
                    "source_file_id": str(file_upload_id),
                }
            )
            .execute()
        )
        if not result.data:
            raise Exception(f"Failed to create queued extraction record: {result}")
            
        return result.data[0]["id"]

    async def update_status(
        self, extracted_file_id: UUID, status: str, error: str = None
    ) -> None:
        payload = {"status": status}
        if error:
            payload["extracted_data"] = {"error": error}
            payload["extracted_json"] = {"error": error}

        await (
            self.supabase.table("extracted_files")
            .update(payload)
            .eq("id", str(extracted_file_id))
            .execute()
        )

    async def update_extraction_result(
        self,
        extracted_file_id: UUID,
        extracted_data: dict,
        embedding: list[float],
        filename: str | None = None,
        file_type: str | None = None,
        llm_summary: str | None = None,
    ) -> None:
        payload = {
            "status": "completed",
            "extracted_data": extracted_data,
            "extracted_json": extracted_data,
            "embedding": embedding,
        }
        if filename:
            payload["filename"] = filename
        if file_type:
            payload["file_type"] = file_type
        if llm_summary:
            payload["llm_summary"] = llm_summary

        await (
            self.supabase.table("extracted_files")
            .update(payload)
            .eq("id", str(extracted_file_id))
            .execute()
        )

    async def get_extraction_with_file_info(self, extracted_file_id: UUID) -> dict:
        response = await (
            self.supabase.table("extracted_files")
            .select("file_uploads!inner(name, tenant_id)")
            .eq("id", str(extracted_file_id))
            .single()
            .execute()
        )
        return response.data

    async def delete_by_source_file(self, source_file_id: UUID) -> None:
        await (
            self.supabase.table("extracted_files")
            .delete()
            .eq("source_file_id", str(source_file_id))
            .execute()
        )

    async def download_file(self, tenant_id: str, file_name: str) -> bytes:
        storage_path = f"{tenant_id}/{file_name}"
        return await self.supabase.storage.from_("documents").download(storage_path)

    async def get_extracted_files_with_embeddings(self, tenant_id: UUID) -> list[dict]:
        response = await (
            self.supabase.table("extracted_files")
            .select(
                "id, source_file_id, extracted_data, embedding, file_uploads!inner(id, type, name, tenant_id, classifications(id, tenant_id, name))"
            )
            .not_.is_("embedding", "null")
            .eq("file_uploads.tenant_id", str(tenant_id))
            .execute()
        )
        return response.data or []
