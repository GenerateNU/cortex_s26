"""
Cognee service layer — wraps cognee SDK calls for use by route handlers.
"""

import cognee
from cognee import SearchType


async def search_knowledge_graph(
    query_text: str,
    dataset: str | None = None,
    limit: int = 20,
    search_type: SearchType = SearchType.GRAPH_COMPLETION,
) -> list[dict]:
    """
    Search the Cognee knowledge graph and return raw result dicts.

    Each dict has: text (str), score (float|None), dataset_name (str|None).
    """
    search_kwargs: dict = {
        "query_text": query_text,
        "query_type": search_type,
    }
    if dataset:
        search_kwargs["datasets"] = [dataset]

    raw_results = await cognee.search(**search_kwargs)

    results = []
    for r in raw_results or []:
        # Extract payload and the actual dataset name from the result
        if hasattr(r, "search_result"):
            payload = r.search_result
            result_dataset = getattr(r, "dataset_name", None) or dataset
        elif isinstance(r, dict):
            payload = r.get("search_result", r)
            result_dataset = r.get("dataset_name") or dataset
        else:
            payload = r
            result_dataset = dataset

        if isinstance(payload, list):
            text = " ".join(str(p) for p in payload)
        elif isinstance(payload, dict):
            text = payload.get("text", "") or str(payload)
        else:
            text = str(payload)

        results.append({
            "text": text,
            "score": None,
            "dataset_name": result_dataset,
        })

    return results[:limit]
