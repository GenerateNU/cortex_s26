from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

class GraphLabel(str, Enum):
    PRODUCT_SPECS = "Product Specs"
    SALES_RECORDS = "Sales Records"
    CUSTOMERS = "Customers"
    RFQS = "RFQs"
    CONFIGURATIONS = "Configurations"
    QUOTES = "Quotes"
    PURCHASE_ORDERS = "Purchase Orders"

class RelationshipType(str, Enum):
    SOLD_TO = "SOLD_TO"
    CONTAINS_ITEM = "CONTAINS_ITEM"
    CONFIGURED_FOR = "CONFIGURED_FOR"
    QUOTED_FOR = "QUOTED_FOR"
    ORDERED_BY = "ORDERED_BY"

class GraphNode(BaseModel):
    """
    Represents a node in the graph.
    """
    tenant_id: str = Field(..., description="tenant id")
    uuid: str = Field(..., description="File upload id")
    label: GraphLabel = Field(..., description="Node label (e.g., Product, Customer)")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Extracted data")

class GraphNodes(BaseModel):
    nodes: List[GraphNode]

class GraphEdge(BaseModel):
    """
    Represents a relationship between two nodes.
    """
    tenant_id: str = Field(..., description="tenant id")
    from_uuid: str = Field(..., description="Source node UUID")
    to_uuid: str = Field(..., description="Target node UUID")
    relationship_type: RelationshipType = Field(..., description="Relationship type (e.g., SOLD_TO)")

class GraphEdges(BaseModel):
    nodes: List[GraphEdge]

class GraphQueryRequest(BaseModel):
    """
    Request model for executing a graph query.
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