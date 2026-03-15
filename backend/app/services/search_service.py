import json
from typing import Any

from supabase._async.client import AsyncClient

from app.core.litellm import LLMClient


class SearchService:
    def __init__(self, supabase: AsyncClient):
        self.supabase = supabase
        self.rag_llm = LLMClient()
        self.rag_llm.set_system_prompt(
            "You are a retrieval-augmented assistant. Answer strictly from the provided "
            "documents. If the documents do not contain enough information, say so plainly. "
            "Cite supporting evidence by document number such as [Document 1]. Do not invent facts."
        )
        self.sql_generation_llm = LLMClient()
        self.sql_generation_llm.set_system_prompt(
            "You translate natural language queries into SQL.\n"
            "The database has one table named 'extracted_files' with the following columns:\n"
            " - file_id (UUID)\n"
            " - file_name (TEXT)\n"
            " - summary (TEXT)\n"
            " - extracted_json (JSONB)\n"
            " - processed_at (TIMESTAMP)\n"
            " - embedding (VECTOR)\n"
            " - file_type (TEXT)\n\n"
            "Rules:\n"
            "1. Only generate SELECT queries.\n"
            "2. Always query the table 'extracted_files'.\n"
            "3. Always return the following columns exactly:\n"
            "   file_id, file_name, summary, extracted_json.\n"
            "4. Do not return other columns.\n"
            "5. Use WHERE clauses to filter results based on the user's query.\n"
            "6. Limit results to at most 10 rows.\n"
            "7. Do NOT include explanations, comments, or markdown.\n"
            "8. Return ONLY the SQL query.\n"
        )

    async def search(
        self, query: str, limit: int = 5, threshold: float = 0.5
    ) -> list[dict[str, Any]]:
        """
        Use an LLM to translate natural language query into a SQL query.
        """
        # 1. Use LLM to generate SQL query
        sql_query_response = await self.sql_generation_llm.chat(
            f"Translate the following natural language query into a SQL query that retrieves relevant rows from the 'extracted_files' table. The query is: '{query}'."
        )
        sql_query = sql_query_response.choices[0].message.content.strip()

        # 2. Validate SQL query - check it only references the 'extracted_files' table and does not contain any harmful statements
        if "extracted_files" not in sql_query.lower():
            raise ValueError("Generated SQL query does not reference the 'extracted_files' table.")
        if any(keyword in sql_query.lower() for keyword in ["delete", "update", "insert", "drop", "alter"]):
            raise ValueError("Generated SQL query contains potentially harmful statements.")

        # 3. Execute SQL query
        response = await self.supabase.rpc(
            "execute_sql",
            {"query": sql_query}
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
        response = await self.rag_llm.chat(
            f"User query:\n{query}\n\n"
            f"Retrieved documents:\n{context}\n\n"
            "Answer the query using only the retrieved documents. Cite document numbers "
            "for every key claim."
        )
        answer = response.choices[0].message.content.strip()

        return {"answer": answer, "sources": results}
