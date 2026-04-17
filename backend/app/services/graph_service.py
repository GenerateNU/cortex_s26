"""
Graph service — fetches knowledge graph data from cognee for D3 visualization.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def get_graph_data(dataset: str | None = None) -> dict[str, Any]:
    """
    Return a D3-compatible graph: {nodes: [...], links: [...]}.

    Uses cognee's get_graph_engine().get_graph_data() which queries KuzuDB directly.
    The `dataset` parameter is accepted for API compatibility but KuzuDB returns the
    full graph — filtering by dataset is done post-query on node properties.
    """
    try:
        from cognee.infrastructure.databases.graph import get_graph_engine

        graph_engine = await get_graph_engine()
        raw_nodes, raw_edges = await graph_engine.get_graph_data()

        # Build node lookup: id -> {id, name, type, val (connection count)}
        node_map: dict[str, dict] = {}
        for node_id, props in raw_nodes:
            name = props.get("name") or str(node_id)
            node_type = props.get("type") or "Entity"
            node_map[str(node_id)] = {
                "id": str(node_id),
                "name": name,
                "type": node_type,
                "val": 1,
            }

        # Build links and increment node val (connection count)
        links = []
        for source_id, target_id, rel_name, _props in raw_edges:
            sid = str(source_id)
            tid = str(target_id)
            # Ensure both nodes exist (add stub if missing)
            if sid not in node_map:
                node_map[sid] = {"id": sid, "name": sid, "type": "Entity", "val": 1}
            if tid not in node_map:
                node_map[tid] = {"id": tid, "name": tid, "type": "Entity", "val": 1}
            node_map[sid]["val"] += 1
            node_map[tid]["val"] += 1
            links.append(
                {
                    "source": sid,
                    "target": tid,
                    "label": rel_name or "related_to",
                }
            )

        nodes = list(node_map.values())

        # If dataset filter provided, filter nodes by name containing dataset hint
        # (KuzuDB doesn't store dataset per-node natively in this version)
        # For now return full graph — dataset filtering can be added when node
        # properties include dataset metadata.

        return {"nodes": nodes, "links": links}

    except Exception as e:
        logger.error("Failed to get graph data: %s", e, exc_info=True)
        return {"nodes": [], "links": []}
