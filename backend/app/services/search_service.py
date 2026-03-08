import json
from typing import Any

from supabase._async.client import AsyncClient

from app.core.litellm import LLMClient
from app.services.extraction.embeddings import generate_embedding


class SearchService:
    def __init__(self, supabase: AsyncClient):
        self.supabase = supabase
        self.llm = LLMClient()
        self.llm.set_system_prompt(
            "You are a retrieval-augmented assistant. Answer strictly from the provided "
            "documents. If the documents do not contain enough information, say so plainly. "
            "Cite supporting evidence by document number such as [Document 1]. Do not invent facts."
        )

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

    async def rag_search(
        self, query: str, limit: int = 5, threshold: float = 0.5
    ) -> dict[str, Any]:
        """
        Semantic search followed by grounded answer generation.
        """
        results = await self.search(query, limit, threshold)

        if not results:
            return {
                "answer": "I could not find any relevant source documents for that query.",
                "sources": [],
            }

        context_parts = []
        for idx, result in enumerate(results, start=1):
            context_parts.append(

                    f"[Document {idx}]\n"
                    f"file_name: {result.get('file_name') or 'Unknown'}\n"
                    f"file_type: {result.get('file_type') or 'Unknown'}\n"
                    f"similarity: {result.get('similarity')}\n"
                    f"summary: {result.get('summary') or 'None'}\n"
                    f"extracted_json: "
                    f"{json.dumps(result.get('extracted_json') or {}, ensure_ascii=False)}"

            )

        context = "\n\n".join(context_parts)
        response = await self.llm.chat(

                f"User query:\n{query}\n\n"
                f"Retrieved documents:\n{context}\n\n"
                "Answer the query using only the retrieved documents. Cite document numbers "
                "for every key claim."
            
        )
        answer = response.choices[0].message.content.strip()

        return {"answer": answer, "sources": results}
