import json
from typing import Any
from uuid import UUID

from supabase._async.client import AsyncClient

from app.core.litellm import LLMClient


class ClassificationService:
    def __init__(self, supabase: AsyncClient):
        self.supabase = supabase
        self.llm = LLMClient()

    async def get_classifications(self, tenant_id: UUID) -> list[dict[str, Any]]:
        """Fetch all classifications for a tenant."""
        response = (
            await self.supabase.table("classifications")
            .select("*")
            .eq("tenant_id", str(tenant_id))
            .execute()
        )
        return response.data or []

    async def create_classification(
        self, tenant_id: UUID, name: str, description: str | None = None
    ) -> dict[str, Any]:
        """Create a new classification."""
        # Check if exists
        existing = (
            await self.supabase.table("classifications")
            .select("*")
            .eq("tenant_id", str(tenant_id))
            .eq("name", name)
            .execute()
        )

        if existing.data:
            return existing.data[0]

        response = (
            await self.supabase.table("classifications")
            .insert({"tenant_id": str(tenant_id), "name": name})
            .execute()
        )

        return response.data[0] if response.data else None

    async def create_classifications_batch(
        self, tenant_id: UUID, names: list[str]
    ) -> list[dict[str, Any]]:
        """Create multiple classifications at once."""
        results = []
        for name in names:
            res = await self.create_classification(tenant_id, name)
            if res:
                results.append(res)
        return results

    async def classify_files(self, tenant_id: UUID) -> dict[str, int]:
        """
        Auto-classify unclassified files using LLM.
        """
        # 1. Get all classifications
        classifications = await self.get_classifications(tenant_id)
        if not classifications:
            return {"classified": 0, "failed": 0, "skipped": 0}

        class_names = [c["name"] for c in classifications]

        # 2. Get unclassified files (where classification_id is NULL)
        # Note: In PRD file_uploads links to classification.
        # Check if 'file_uploads' table has 'classification_id'.
        # Based on setup_database.sql, 'file_uploads' has 'classification_id'.

        files_resp = (
            await self.supabase.table("file_uploads")
            .select("*, raw_files(file_name, file_link), extracted_files(summary)")
            .eq("tenant_id", str(tenant_id))
            .is_("classification_id", "null")
            .execute()
        )

        files_to_classify = files_resp.data or []
        classified_count = 0
        failed_count = 0

        for file_record in files_to_classify:
            summary = file_record.get("extracted_files", {}).get("summary")
            file_name = file_record.get("raw_files", {}).get("file_name")

            if not summary:
                continue

            # 3. Ask LLM
            prompt = (
                f"File: {file_name}\n"
                f"Summary: {summary}\n"
                f"Available Classifications: {', '.join(class_names)}\n\n"
                "Task: Assign the best matching classification from the list.\n"
                'Return a JSON object: { "classification": "Exact Name From List" }\n'
                'If none match well, return { "classification": null }'
            )

            try:
                response = await self.llm.chat(prompt, json_response=True)
                # Parse response - assuming LLMClient returns a ModelResponse-like object
                # but we've patched it to return Any (dict) in previous steps.
                # Just in case, let's handle the dict structure carefully.

                content_str = response.choices[0].message.content
                result = json.loads(content_str)
                best_class = result.get("classification")

                if best_class and best_class in class_names:
                    # Find ID
                    class_id = next(
                        c["id"] for c in classifications if c["name"] == best_class
                    )

                    # Update DB
                    await (
                        self.supabase.table("file_uploads")
                        .update({"classification_id": class_id})
                        .eq("id", file_record["id"])
                        .execute()
                    )
                    classified_count += 1
            except Exception as e:
                print(f"Failed to classify file {file_record['id']}: {e}")
                failed_count += 1

        return {"classified": classified_count, "failed": failed_count}

    async def get_clustering_visualization(self, tenant_id: UUID) -> dict[str, Any]:
        """
        Return data for visualization.
        For now, returns a mock structure or simple mapping.
        PRD implies 2D/3D points. We'll return existing files grouped by classification.
        """
        # Fetch all files with classification
        files_resp = (
            await self.supabase.table("file_uploads")
            .select("id, name, classification_id, classifications(name)")
            .eq("tenant_id", str(tenant_id))
            .not_.is_("classification_id", "null")
            .execute()
        )

        data = files_resp.data or []

        # Group logic or just return raw list for frontend to handle?
        # Frontend expects 'VisualizationResponse'.
        # Let's peek at frontend types if needed, but for now return raw data
        # and let frontend helper parse it if possible, or build simple nodes/links.

        return {"points": data}  # Simplified
