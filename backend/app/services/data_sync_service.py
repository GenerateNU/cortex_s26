from uuid import UUID
import json
from fastapi import Depends
from supabase._async.client import AsyncClient

from app.core.supabase import get_async_supabase
from app.services.classification_service import ClassificationService, get_classification_service
from app.services.relationship_service import RelationshipService, get_relationship_service
from app.services.schema_generation_service import SchemaGenerationService
from app.repositories.schema_repository import SchemaRepository

class DataSyncService:
    def __init__(
        self,
        classification_service: ClassificationService,
        relationship_service: RelationshipService,
        schema_repo: SchemaRepository,
    ):
        self.classification_service = classification_service
        self.relationship_service = relationship_service
        self.schema_repo = schema_repo

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
                related_id = self._resolve_fk(source_file=f, target_classification_id=rel.to_classification.classification_id)
                
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
            "total_files": len(extracted_files)
        }

    async def _resolve_fk(self, source_file, target_classification_id: UUID) -> UUID | None:
        """
        Heuristic to find a related record's ID.
        Looks for keys in entry_data that match target_name.
        """
        if not source_file.embedding:
            return None
    
        # 1. Use vector similarity to find candidate files that are related
        matches = await self.schema_repo.call_rpc(
            "match_documents",
            {
                "query_embedding": source_file.embedding,
                "match_threshold": 0.75,
                "match_count": 10,
                "filter_tenant_id": str(source_file.tenant_id),
                # might also want to filter by classification type, add to 006_vectorization.sql file
            }
        )

        # 2. Check if any of the matches have the target classification
        if not matches:
            return None
        
        for match in matches:
            if match["classification_id"] == str(target_classification_id):
                return match["source_file_id"]

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
    return DataSyncService(
        classification_service,
        relationship_service,
        SchemaRepository(supabase)
    )
