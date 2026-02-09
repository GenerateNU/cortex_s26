import json
from collections import defaultdict, deque
from uuid import UUID

import numpy as np
from fastapi import Depends
from supabase._async.client import AsyncClient

from app.core.supabase import get_async_supabase
from app.repositories.schema_repository import SchemaRepository
from app.schemas.classification_schemas import ExtractedFile
from app.services.classification_service import (
    ClassificationService,
    get_classification_service,
)
from app.services.relationship_service import (
    RelationshipService,
    get_relationship_service,
)
from app.services.schema_generation_service import SchemaGenerationService


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two embedding vectors."""
    v1 = np.array(a)
    v2 = np.array(b)
    dot = np.dot(v1, v2)
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 == 0 or n2 == 0:
        return 0.0
    return float(dot / (n1 * n2))


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
        Populates foreign keys using embedding cosine similarity (nearest neighbor).
        Handles ONE_TO_ONE, ONE_TO_MANY, and MANY_TO_MANY relationships.
        """
        # 1. Fetch metadata
        extracted_files = await self.classification_service.get_extracted_files(tenant_id)
        relationships = await self.relationship_service.get_relationships(tenant_id)

        if not extracted_files:
            return {"status": "error", "message": "No extracted files found"}

        schema_name = SchemaGenerationService.get_schema_name(tenant_id)

        # 2. Group files by classification name
        files_by_class: dict[str, list[ExtractedFile]] = defaultdict(list)
        for f in extracted_files:
            if f.classification:
                files_by_class[f.classification.name].append(f)

        # 3. Determine insertion order via topological sort.
        #    Parent tables (the "to" side of FKs) must be inserted before children.
        all_tables = {
            SchemaGenerationService.table_name_for_classification(f.classification)
            for f in extracted_files if f.classification
        }
        table_order = self._topological_sort(all_tables, relationships)

        # 4. Map table_name -> files for ordered insertion
        files_by_table: dict[str, list[ExtractedFile]] = defaultdict(list)
        for f in extracted_files:
            if f.classification:
                tbl = SchemaGenerationService.table_name_for_classification(f.classification)
                files_by_table[tbl].append(f)

        tables_updated: set[str] = set()

        # 5. Insert files in topological order (parents first, then children)
        for table_name in table_order:
            if table_name not in files_by_table:
                continue

            tables_updated.add(table_name)

            for f in files_by_table[table_name]:
                data_to_insert: dict = {
                    "id": str(f.file_upload_id),
                    "tenant_id": str(tenant_id),
                    "data": json.dumps(f.extracted_data),
                }

                # Resolve FK columns for ONE_TO_ONE and ONE_TO_MANY
                relevant_rels = [
                    r for r in relationships
                    if r.from_classification.classification_id == f.classification.classification_id
                    and r.type.value in ("one-to-one", "one-to-many")
                ]
                for rel in relevant_rels:
                    to_table = SchemaGenerationService.table_name_for_classification(rel.to_classification)
                    fk_column = f"{to_table}_id"
                    candidates = files_by_class.get(rel.to_classification.name, [])
                    related_id = self._resolve_fk(f, candidates)
                    data_to_insert[fk_column] = str(related_id) if related_id else None

                await self.schema_repo.upsert_row(schema_name, table_name, data_to_insert)

        # 6. Populate MANY_TO_MANY join tables
        m2m_rels = [r for r in relationships if r.type.value == "many-to-many"]
        for rel in m2m_rels:
            from_table = SchemaGenerationService.table_name_for_classification(rel.from_classification)
            to_table = SchemaGenerationService.table_name_for_classification(rel.to_classification)
            join_table = f"{from_table}_{to_table}_join"

            from_files = files_by_class.get(rel.from_classification.name, [])
            to_files = files_by_class.get(rel.to_classification.name, [])

            if not from_files or not to_files:
                continue

            links = self._resolve_many_to_many(from_files, to_files)
            for from_id, to_id in links:
                await self.schema_repo.insert_join_link(
                    schema_name, join_table,
                    f"{from_table}_id", f"{to_table}_id",
                    from_id, to_id,
                )

            tables_updated.add(join_table)

        return {
            "status": "success",
            "message": f"Synced {len(extracted_files)} files into {len(tables_updated)} tables",
            "tables_updated": list(tables_updated),
            "total_files": len(extracted_files),
        }

    # ------------------------------------------------------------------ #
    #  FK Resolution — embedding nearest neighbor, no magic thresholds    #
    # ------------------------------------------------------------------ #

    def _resolve_fk(
        self,
        source_file: ExtractedFile,
        candidate_files: list[ExtractedFile],
    ) -> UUID | None:
        """
        Find the best matching file in *candidate_files* using embedding
        cosine similarity (argmax — no hardcoded threshold).

        Why no threshold?
        -  The relationship between these two classifications was already
           validated by the pattern-recognition AI.  We know they are
           related.  The only question is *which specific* target file
           corresponds to this source file.
        -  Argmax over cosine similarity is the nearest-neighbor answer
           to that question — mathematically principled, no magic numbers.

        Returns the file_upload_id of the best match, or None if there
        are no embeddable candidates.
        """
        if not source_file.embedding or not candidate_files:
            return None

        best_id: UUID | None = None
        best_sim = -2.0  # cosine similarity is in [-1, 1]

        for candidate in candidate_files:
            if not candidate.embedding:
                continue
            sim = _cosine_similarity(source_file.embedding, candidate.embedding)
            if sim > best_sim:
                best_sim = sim
                best_id = candidate.file_upload_id

        return best_id

    def _resolve_many_to_many(
        self,
        from_files: list[ExtractedFile],
        to_files: list[ExtractedFile],
    ) -> list[tuple[UUID, UUID]]:
        """
        Build links for a MANY_TO_MANY join table using bidirectional
        nearest-neighbor — no arbitrary threshold.

        For each file in A we find its best match in B and vice-versa.
        The *union* of these directed links captures the strongest
        cross-classification connections.
        """
        links: set[tuple[UUID, UUID]] = set()

        # A → B
        for a in from_files:
            if not a.embedding:
                continue
            best_id: UUID | None = None
            best_sim = -2.0
            for b in to_files:
                if not b.embedding:
                    continue
                sim = _cosine_similarity(a.embedding, b.embedding)
                if sim > best_sim:
                    best_sim = sim
                    best_id = b.file_upload_id
            if best_id:
                links.add((a.file_upload_id, best_id))

        # B → A (reverse direction picks up links the forward pass misses)
        for b in to_files:
            if not b.embedding:
                continue
            best_id = None
            best_sim = -2.0
            for a in from_files:
                if not a.embedding:
                    continue
                sim = _cosine_similarity(b.embedding, a.embedding)
                if sim > best_sim:
                    best_sim = sim
                    best_id = a.file_upload_id
            if best_id:
                links.add((best_id, b.file_upload_id))

        return list(links)

    # ------------------------------------------------------------------ #
    #  Topological Sort — ensures parent tables are populated first       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _topological_sort(
        tables: set[str],
        relationships: list,
    ) -> list[str]:
        """
        Kahn's algorithm.  Edges: to_table → from_table  (parent before child).
        Many-to-many relationships are skipped because their join tables are
        populated in a separate pass after all base tables exist.
        """
        in_degree: dict[str, int] = dict.fromkeys(tables, 0)
        graph: dict[str, list[str]] = defaultdict(list)

        for rel in relationships:
            if rel.type.value == "many-to-many":
                continue

            from_table = SchemaGenerationService.table_name_for_classification(rel.from_classification)
            to_table = SchemaGenerationService.table_name_for_classification(rel.to_classification)

            if from_table in tables and to_table in tables:
                graph[to_table].append(from_table)
                in_degree[from_table] = in_degree.get(from_table, 0) + 1

        queue = deque(t for t in sorted(tables) if in_degree.get(t, 0) == 0)
        result: list[str] = []

        while queue:
            t = queue.popleft()
            result.append(t)
            for child in graph[t]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        # Append remaining tables (only if there is a cycle — shouldn't happen)
        seen = set(result)
        result.extend(t for t in sorted(tables) if t not in seen)
        return result


def get_data_sync_service(
    classification_service: ClassificationService = Depends(get_classification_service),
    relationship_service: RelationshipService = Depends(get_relationship_service),
    supabase: AsyncClient = Depends(get_async_supabase),
) -> DataSyncService:
    return DataSyncService(
        classification_service,
        relationship_service,
        SchemaRepository(supabase),
    )
