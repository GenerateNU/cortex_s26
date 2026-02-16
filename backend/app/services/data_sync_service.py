from uuid import UUID
import json
from fastapi import Depends
from supabase._async.client import AsyncClient

from app.core.supabase import get_async_supabase
from app.services.classification_service import ClassificationService, get_classification_service
from app.services.relationship_service import RelationshipService, get_relationship_service
from app.services.schema_generation_service import SchemaGenerationService
from app.repositories.schema_repository import SchemaRepository
from app.services.graph_service import GraphService
from app.core.neo4j import get_graph_repo

class DataSyncService:
    def __init__(
        self,
        classification_service: ClassificationService,
        relationship_service: RelationshipService,
        schema_repo: SchemaRepository,
        graph_service: GraphService | None = None,
    ):
        self.classification_service = classification_service
        self.relationship_service = relationship_service
        self.schema_repo = schema_repo
        self.graph_service = graph_service

    async def sync_tenant(self, tenant_id: UUID) -> dict:
        """
        Sync all extracted data into tenant-specific tables.
        This includes populating foreign keys based on AI-discovered relationships.
        """
        # 1. Fetch metadata
        extracted_files = await self.classification_service.get_extracted_files(tenant_id)
        relationships = await self.relationship_service.get_relationships(tenant_id)
        
        if not extracted_files:
            return {"status": "error", "message": "No extracted files found"}

        schema_name = SchemaGenerationService.get_schema_name(tenant_id)
        tables_updated = set()

        # 2. Build ID and context maps for FK resolution
        # Map: filename -> file_upload_id
        file_id_map = {f.name: f.file_upload_id for f in extracted_files}
        
        # Map: classification -> list of files
        files_by_class = {}
        for f in extracted_files:
            if not f.classification:
                continue
            cls_name = f.classification.name
            if cls_name not in files_by_class:
                files_by_class[cls_name] = []
            files_by_class[cls_name].append(f)

        # 3. Process each file for insertion
        for f in extracted_files:
            if not f.classification:
                continue
            
            table_name = SchemaGenerationService.table_name_for_classification(f.classification)
            tables_updated.add(table_name)
            
            # Basic data
            data_to_insert = {
                "id": str(f.file_upload_id),
                "tenant_id": str(tenant_id),
                "data": json.dumps(f.extracted_data)
            }
            
            # 4. Resolve Foreign Keys
            # Find relationships where this classification is the source (from)
            relevant_rels = [r for r in relationships if r.from_classification.classification_id == f.classification.classification_id]
            
            for rel in relevant_rels:
                to_table_name = SchemaGenerationService.table_name_for_classification(rel.to_classification)
                fk_column = f"{to_table_name}_id"
                
                # Try to find the related ID in extracted data
                # We look for keys that match the related classification name or table name
                related_id = self._resolve_fk(f.extracted_data, rel.to_classification.name, files_by_class.get(rel.to_classification.name, []))
                
                if related_id:
                    data_to_insert[fk_column] = str(related_id)
                else:
                    data_to_insert[fk_column] = None

            # 5. Execute UPSERT
            # Build dynamic SQL to include the dynamically discovered FK columns
            columns = ", ".join([f'"{col}"' for col in data_to_insert.keys()])
            placeholders = ", ".join(["%s"] * len(data_to_insert))
            
            # Converting to a raw SQL string for the RPC
            # Note: We need to escape single quotes in JSON
            val_strings = []
            for v in data_to_insert.values():
                if v is None:
                    val_strings.append("NULL")
                elif isinstance(v, str):
                    escaped = v.replace("'", "''")
                    val_strings.append(f"'{escaped}'")
                else:
                    val_strings.append(str(v))
            
            vals = ", ".join(val_strings)
            
            sql = f"""
INSERT INTO "{schema_name}"."{table_name}" ({columns})
VALUES ({vals})
ON CONFLICT (id) DO UPDATE SET
    data = EXCLUDED.data,
    {", ".join([f'"{col}" = EXCLUDED."{col}"' for col in data_to_insert.keys() if col not in ['id', 'tenant_id']])}
;
""".strip()
            
            await self.schema_repo.execute_sql(sql)

        return {
            "status": "success",
            "tables_updated": list(tables_updated),
            "total_files": len(extracted_files),
            "graph_sync": await self._sync_graph(tenant_id),
        }

    async def _sync_graph(self, tenant_id: UUID) -> dict:
        """
        Chain graph sync after Supabase data sync.
        Gracefully handles failures so Supabase sync result isn't lost.
        """
        if not self.graph_service:
            return {"status": "skipped", "message": "Graph service not configured"}

        try:
            result = await self.graph_service.sync_tenant_to_graph(tenant_id)
            return result.model_dump()
        except Exception as e:
            print(f"Graph sync failed (non-fatal): {e}", flush=True)
            return {"status": "error", "message": str(e)}

    def _resolve_fk(self, entry_data: dict, target_name: str, candidate_files: list) -> UUID | None:
        """
        Heuristic to find a related record's ID.
        Looks for keys in entry_data that match target_name.
        """
        # 1. Look for direct key matches (e.g. "Model": "XYZ")
        target_keys = [target_name.lower(), target_name.replace(" ", "_").lower(), "model", "type", "category"]
        
        # Flattened lookup
        flat_data = self._flatten_dict(entry_data)
        
        for key, value in flat_data.items():
            if any(tk in key.lower() for tk in target_keys):
                # We found a potential link value (e.g. "XYZ")
                # Now find a file in candidate_files whose data or name matches this value
                match = self._find_matching_file(value, candidate_files)
                if match:
                    return match.file_upload_id
        
        return None

    def _flatten_dict(self, d: dict, parent_key: str = '', sep: str = '_') -> dict:
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def _find_matching_file(self, search_val, candidate_files: list):
        """Find a file that represents this search value"""
        if not search_val:
            return None
            
        search_val_str = str(search_val).lower()
        
        for f in candidate_files:
            # Check filename
            if search_val_str in f.name.lower():
                return f
            # Check extracted data (model name, etc)
            # This is very broad but effective for small datasets
            data_str = json.dumps(f.extracted_data).lower()
            if f'"{search_val_str}"' in data_str:
                return f
        
        return None

def get_data_sync_service(
    classification_service: ClassificationService = Depends(get_classification_service),
    relationship_service: RelationshipService = Depends(get_relationship_service),
    supabase: AsyncClient = Depends(get_async_supabase),
) -> DataSyncService:
    graph_repo = get_graph_repo()
    graph_service = GraphService(
        classification_service, relationship_service, graph_repo
    ) if graph_repo else None

    return DataSyncService(
        classification_service,
        relationship_service,
        SchemaRepository(supabase),
        graph_service,
    )