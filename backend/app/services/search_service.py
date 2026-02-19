from typing import Any

from supabase._async.client import AsyncClient

from app.services.extraction.embeddings import generate_embedding


class SearchService:
    def __init__(self, supabase: AsyncClient):
        self.supabase = supabase

    async def search(self, query: str, limit: int = 5, threshold: float = 0.5) -> list[dict[str, Any]]:
        """
        Semantic search for extracted files.
        """
        # 1. Generate embedding for query
        query_embedding = await generate_embedding(query)

        # 2. Call RPC function
        response = await self.supabase.rpc(
            "match_extracted_files",
            {
                "query_embedding": query_embedding,
                "match_threshold": threshold,
                "match_count": limit,
            },
        ).execute()

        return response.data or []
