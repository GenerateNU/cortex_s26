"""
Cognee service layer — wraps cognee SDK calls for use by route handlers.
"""

import cognee
from cognee import SearchType


async def ingest_document(file_path: str, dataset_name: str = "main") -> dict:
    """
    Add a document to Cognee and run the cognify pipeline.

    Returns a dict with summary, entities, and chunk count.
    """
    await cognee.add(file_path, dataset_name=dataset_name)
    await cognee.cognify(datasets=[dataset_name])

    summary_results = await cognee.search(
        query_text="Summarize the document",
        query_type=SearchType.CHUNKS,
        datasets=[dataset_name],
    )
    entity_results = await cognee.search(
        query_text="What entities are mentioned?",
        query_type=SearchType.CHUNKS,
        datasets=[dataset_name],
    )

    def _extract_text(r) -> str:
        if hasattr(r, "search_result"):
            payload = r.search_result
        elif isinstance(r, dict):
            payload = r.get("search_result", r)
        else:
            payload = r
        if isinstance(payload, list):
            return " ".join(str(p) for p in payload)
        if isinstance(payload, dict):
            return payload.get("text", "") or str(payload)
        return str(payload)

    summary = _extract_text(summary_results[0]) if summary_results else ""
    entities = [_extract_text(r) for r in entity_results] if entity_results else []

    return {
        "summary": summary,
        "entities": entities,
        "raw_chunks_count": len(summary_results) if summary_results else 0,
    }


async def search_knowledge_graph(
    query_text: str,
    dataset: str | None = None,
    limit: int = 20,
    search_type: SearchType = SearchType.GRAPH_COMPLETION,
) -> list[dict]:
    """
    Search the Cognee knowledge graph and return raw result dicts.
    """
    search_kwargs = {
        "query_text": query_text,
        "query_type": search_type,
    }
    if dataset:
        search_kwargs["datasets"] = [dataset]

    raw_results = await cognee.search(**search_kwargs)

    results = []
    for r in raw_results or []:
        # r is a SearchResult pydantic model or dict
        if hasattr(r, "search_result"):
            payload = r.search_result
            dataset = r.dataset_name
        elif isinstance(r, dict):
            payload = r.get("search_result", r)
            dataset = r.get("dataset_name")
        else:
            payload = r
            dataset = None

        # payload can be a list, dict, or string
        if isinstance(payload, list):
            text = " ".join(str(p) for p in payload)
        elif isinstance(payload, dict):
            text = payload.get("text", "") or str(payload)
        else:
            text = str(payload)

        metadata = {"dataset": dataset} if dataset else {}
        results.append({"text": text, "score": None, "metadata": metadata})

    return results[:limit]
