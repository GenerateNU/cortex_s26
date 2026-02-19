from typing import Any
from uuid import UUID

from supabase._async.client import AsyncClient


class ExtractionRepository:
    def __init__(self, supabase: AsyncClient):
        self.supabase = supabase

    async def create_queued_extraction(self, file_id: UUID) -> UUID:
        """
        Creates an initial entry in extracted_files for a raw_file.
        """
        # In new schema, extracted_files has a strict 1:1 with raw_files
        # and file_id is the primary key.
        response = await (
            self.supabase.table("extracted_files")
            .insert(
                {
                    "file_id": str(file_id),
                    "extracted_json": {},  # Initial empty JSON
                    "summary": "Queued for extraction",
                }
            )
            .execute()
        )
        return UUID(response.data[0]["file_id"])

    async def update_status(self, file_id: UUID, status: str, error_message: str = None) -> None:
        """
        Updates the summary/status of the extraction.
        NOTE: The new schema doesn't have a specific 'status' column, 
        so we might encode status in summary or metadata for now, 
        or rely on presence of jsonb_data.
        For this refactor, I'll update the 'summary' to reflect status.
        """
        update_data = {"summary": f"Status: {status}"}
        if error_message:
            update_data["summary"] = f"Failed: {error_message}"

        await (
            self.supabase.table("extracted_files")
            .update(update_data)
            .eq("file_id", str(file_id))
            .execute()
        )

    async def update_extraction_result(
        self,
        file_id: UUID,
        extracted_data: dict, # wrapper containing file_type, summary, extracted_json
        embedding: list[float]
    ) -> None:
        """
        Updates the extraction result with the final data, summary, classification, and embedding.
        Wrapper expected: { "file_type": ..., "summary": ..., "extracted_json": ... }
        """

        # Unpack from the strategy result
        file_type = extracted_data.get("file_type")
        summary = extracted_data.get("summary")
        extracted_json = extracted_data.get("extracted_json", {})

        await (
            self.supabase.table("extracted_files")
            .update(
                {
                    "file_type": file_type,
                    "summary": summary,
                    "extracted_json": extracted_json,
                    "embedding": embedding,
                    "processed_at": "now()",
                }
            )
            .eq("file_id", str(file_id))
            .execute()
        )

    async def get_extraction_with_file_info(self, file_id: UUID) -> dict[str, Any]:
        """
        Fetches extraction data joined with raw_files metadata.
        """
        response = await (
            self.supabase.table("extracted_files")
            .select("*, raw_files(*)")
            .eq("file_id", str(file_id))
            .single()
            .execute()
        )
        return response.data

    async def download_file(self, file_path_or_link: str) -> bytes:
        """
        Downloads a file from storage.
        Assuming 'documents' bucket for now, or determining bucket from link.
        Refactor: The 'file_link' in raw_files might be a public URL or storage path. 
        If strict storage path is needed, we assume 'documents' bucket.
        """
        # Simplified download logic assuming standard Supabase storage path
        # If file_link is full URL, might need different logic.
        # For now assuming it stores the path within 'documents' bucket.
        try:
            # Clean path if needed
            # Handle full URL or internal path "documents/xyz.pdf"
            if "documents/" in file_path_or_link:
                path = file_path_or_link.split("documents/")[-1]
            else:
                path = file_path_or_link

            return await self.supabase.storage.from_("documents").download(path)
        except Exception as e:
            print(f"Download Error: {e}")
            raise

    async def delete_by_file_id(self, file_id: UUID) -> None:
        await self.supabase.table("extracted_files").delete().eq("file_id", str(file_id)).execute()
