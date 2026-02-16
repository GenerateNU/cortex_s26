# app/schemas/graph_schemas.py
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """
    Represents a node in the graph.
    """
    tenant_id: str = Field(..., description="Tenant ID")
    uuid: str = Field(..., description="Node identifier (extracted_file_id)")
    label: str = Field(
        ...,
        description="Node label derived from classification name (e.g., PRODUCT_SPECS). "
        "Dynamic per tenant — validated at the repository level.",
    )
    properties: Dict[str, Any] = Field(default_factory=dict, description="Extracted data")


class GraphNodes(BaseModel):
    nodes: List[GraphNode]


class GraphEdge(BaseModel):
    """
    Represents a relationship between two nodes.
    """
    tenant_id: str = Field(..., description="Tenant ID")
    from_uuid: str = Field(..., description="Source node UUID")
    to_uuid: str = Field(..., description="Target node UUID")
    relationship_type: str = Field(
        ...,
        description="Relationship type (e.g., HAS_CUSTOMERS). "
        "Dynamic per tenant — will use semantic names (SOLD_TO, ORDERED_BY) when CORTEX-17 ships.",
    )


class GraphEdges(BaseModel):
    edges: List[GraphEdge]


class GraphSyncResponse(BaseModel):
    """Response from sync_tenant_to_graph"""

    status: str
    message: Optional[str] = None
    nodes_synced: int = 0
    edges_synced: int = 0
    nodes_removed: int = 0


class GraphQueryRequest(BaseModel):
    """
    Request model for executing a graph query.
    SECURITY REVIEW NEEDED: This model enables raw Cypher execution.
    Ensure the route using this validates admin role and consider
    restricting allowed query patterns before production use.
    """
    query: str = Field(..., description="Parameterized Cypher query")
    parameters: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Cypher query parameters"
    )


class GraphQueryResponse(BaseModel):
    records: List[Dict[str, Any]] = Field(
        description="List of result rows returned from the Cypher query"
    )


class PathRequest(BaseModel):
    from_node_id: str = Field(..., description="UUID of the starting node")
    to_node_id: str = Field(..., description="UUID of the ending node")


class GraphPath(BaseModel):
    nodes: GraphNodes
    relationships: GraphEdges