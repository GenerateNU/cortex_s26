"""
Cognee service layer — wraps cognee SDK calls for use by route handlers.
"""

import cognee
from cognee.api.v1.search import SearchType


async def ingest_document(file_path: str, dataset_name: str = "main") -> dict:
    """
    Add a document to Cognee and run the cognify pipeline.

    Returns a dict with summary, entities, and chunk count.
    """
    await cognee.add(file_path, dataset_name=dataset_name)
    await cognee.cognify(datasets=[dataset_name])

    # Pull back summary + entities via search
    summary_results = await cognee.search(
        query_text="Summarize the document",
        query_type=SearchType.CHUNKS,
    )
    entity_results = await cognee.search(
        query_text="What entities are mentioned?",
        query_type=SearchType.CHUNKS,
    )

    summary = summary_results[0].get("text", "") if summary_results else ""
    entities = [
        r.get("text", "") for r in entity_results if r.get("text")
    ] if entity_results else []

    return {
        "summary": summary,
        "entities": entities,
        "raw_chunks_count": len(summary_results) if summary_results else 0,
    }


async def search_knowledge_graph(
    query_text: str,
    dataset: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """
    Search the Cognee knowledge graph and return raw result dicts.
    """
    raw_results = await cognee.search(
        query_text=query_text,
        query_type=SearchType.CHUNKS,
    )

    results = [
        {
            "text": r.get("text", ""),
            "score": r.get("score"),
            "metadata": r.get("metadata", {}),
        }
        for r in (raw_results or [])
    ]

    return results[:limit]
