from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_current_admin
from app.schemas.graph_schemas import (
    GraphNodes,
    GraphEdges,
    GraphQueryRequest,
    GraphQueryResponse,
    PathRequest,
    GraphPath,
)
from app.services.graph_service import (GraphService, get_graph_service)



router = APIRouter(prefix="/graph", tags=["Graph"])

@router.post("/sync/{tenant_id}")
async def sync_tenant(tenant_id: UUID, graph_service: GraphService = Depends(get_graph_service)):
    """
    Sync tenant data into Neo4j.
    """
    try :
        return await graph_service.sync_tenant_to_graph(tenant_id=tenant_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

   

@router.get("/{tenant_id}/nodes", 
            response_model = GraphNodes)
async def get_nodes(tenant_id: UUID, graph_service: GraphService = Depends(get_graph_service)):
    try:
        graph_service.get_nodes_by_tenant(tenant_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.get("/{tenant_id}/relationships", 
            response_model = GraphEdges)
async def get_tenant_relationships(tenant_id: UUID, graph_service: GraphService = Depends(get_graph_service)):
    try:
        graph_service.get_relationships_by_tenant(tenant_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.post("/{tenant_id}/query", 
            response_model = GraphQueryResponse)
async def get_query(tenant_id: UUID, body: GraphQueryRequest, graph_service: GraphService = Depends(get_graph_service)):
    params = body.params or {}
    params["tenant_id"] = tenant_id

    try:
        records = graph_service.run_custom_query(body.query, **params)
        return records
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{tenant_id}/path", 
            response_model = GraphPath)
async def get_path(tenant_id: UUID, body: PathRequest, graph_service: GraphService = Depends(get_graph_service)):
    try:
        return graph_service.get_path_between_two_nodes(tenant_id, body.from_node_id, body.to_node_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e