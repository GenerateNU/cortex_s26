from typing import Any, Dict, List
from fastapi import Depends
from supabase._async.client import AsyncClient

from app.core.supabase import get_async_supabase
from app.core.graph import get_graph_repository
from app.repositories.graph_repository import GraphRepository
from app.repositories.schema_repository import SchemaRepository
from app.services.classification_service import ClassificationService, get_classification_service
from app.services.relationship_service import RelationshipService, get_relationship_service

class GraphService:
    def __init__(
            self, 
            classification_service: ClassificationService,
            relationship_service: RelationshipService, 
            graph_repo: GraphRepository,  
            schema_repo: SchemaRepository):
        self.classification_service = classification_service
        self.relationship_service = relationship_service
        self.graph_repo = graph_repo
        self.schema_repo = schema_repo

    async def sync_tenant_to_graph(self, tenant_id) -> dict:
        """
        Sync tenant data into graph database.
        """
        # 1. Fetch data from supabase
        extracted_files = await self.classification_service.get_extracted_files(tenant_id)
        relationships = await self.relationship_service.get_relationships(tenant_id)

        # 2. Identify file type 
        for f in extracted_files:
            if not f.classification:
                continue
            cls_name = f.classification.name
            extracted_data = f.extracted_data
            # 3. Insert as a node into graph db
            self.graph_repo.create_node(node_label=cls_name, node_id=f.file_upload_id, extracted_data=extracted_data)
            
        # 3. Identify relationships
        for f in extracted_files:
            from_node_id = f.file_upload_id
            relevant_rels = [r for r in relationships if r.from_classification.classification_id == f.classification.classification_id]
            for rel in relevant_rels:
                to_node_id = rel.to_classification.classification_id
                # not sure how to determine yet
                relationship_type = ""
                # 5. Insert as relationship into graph db
                self.graph_repo.create_relationship(from_node_id=from_node_id, to_node_id=to_node_id, relationship_type=relationship_type)
                
        return {
            "status": "success",
            "total_files": len(extracted_files)
        }
    
    def get_nodes_by_tenant(self, tenant_id):
        query = f"""
        MATCH (n {{tenant_id: $tenant_id}})
        RETURN n
        """
        records = self.graph_repo.query(query, tenant_id=tenant_id)
        nodes = [self._serialize_node(record["n"]) for record in records]
        return {"nodes": nodes}
    
    def get_relationships_by_tenant(self, tenant_id):
        query = f"""
        MATCH (a {{tenant_id: $tenant_id}})-[r]->(b {{tenant_id: $tenant_id}})
        RETURN a, r, b
        """
        records = self.graph_repo.query(query, tenant_id=tenant_id)
        relationships = [self._serialize_relationship(record["r"]) for record in records]
        return {"relationships": relationships}
    
    def get_path_between_two_nodes(self, tenant_id, from_node_id, to_node_id):
        query = f"""
        MATCH (start {{tenant_id: $tenant_id, uuid: $from_uuid}}),
        (end {{tenant_id: $tenant_id, uuid: $to_uuid}})
        MATCH p = shortestPath((start)-[*..$max_depth]-(end))
        RETURN p
        """
        records = self.graph_repo.query(
        query,
        tenant_id=tenant_id,
        from_uuid=from_node_id,
        to_uuid=to_node_id,
    )

        if not records:
            return {"nodes": [], "edges": []}

        path = records[0]["p"]

        nodes = [self._serialize_node(n) for n in path.nodes]
        edges = [self._serialize_relationship(r) for r in path.relationships]

        return {
            "nodes": nodes,
            "edges": edges
        }
    
    def run_custom_query(self, query: str, params: dict):
        records = self.graph_repo.query(query, **params)

        results = []
        for record in records:
            row = {}

            for key, value in record.items():
                if hasattr(value, "labels"):  # Node
                    row[key] = self._serialize_node(value)
                elif hasattr(value, "type"):  # Relationship
                    row[key] = self._serialize_relationship(value)
                else:
                    row[key] = value

            results.append(row)

        return {"results": results}


    def _serialize_node(self, n) -> Dict[str, Any]:
        """Convert neo4j.graph.Node → dict"""
        return {
            "id": n.get("uuid"),
            "label": list(n.labels)[0] if n.labels else None,
            "properties": {
                k: v for k, v in dict(n).items()
                if k not in {"uuid", "tenant_id"}
            }
        }

    def _serialize_relationship(self, r) -> Dict[str, Any]:
        """Convert neo4j.graph.Relationship → dict"""
        return {
            "from_id": r.start_node.get("uuid"),
            "to_id": r.end_node.get("uuid"),
            "type": r.type,
            "properties": dict(r)
        }
        
def get_graph_service(
    classification_service: ClassificationService = Depends(get_classification_service),
    relationship_service: RelationshipService = Depends(get_relationship_service),
    graph_repo: GraphRepository = Depends(get_graph_repository),
    supabase: AsyncClient = Depends(get_async_supabase),
) -> GraphService:
    return GraphService(
        classification_service,
        relationship_service,
        graph_repo,
        SchemaRepository(supabase)
    )