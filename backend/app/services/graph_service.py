# app/services/graph_service.py
import asyncio
import json
import re
from functools import partial
from uuid import UUID

from fastapi import Depends

from app.core.neo4j import get_graph_repo
from app.repositories.graph_repository import GraphRepository
from app.schemas.classification_schemas import ExtractedFile
from app.schemas.graph_schemas import GraphSyncResponse
from app.schemas.relationship_schemas import Relationship
from app.services.classification_service import (
    ClassificationService,
    get_classification_service,
)
from app.services.relationship_service import (
    RelationshipService,
    get_relationship_service,
)


class GraphService:
    """
    Syncs tenant data from Supabase into Neo4j.

    Called after DataSyncService.sync_tenant() populates tenant-specific
    Supabase tables. Reads extracted_files and relationships, then MERGEs
    nodes and edges into Neo4j.

    Node model:
        - One node per extracted_files row
        - Label = sanitized classification name (e.g. "SalesRecords")
        - MERGE key = extracted_file_id
        - Properties = flattened extracted_data + identity fields

    Edge model:
        - Defined by relationships table (which classifications connect)
        - Resolved by FK heuristics (which specific records connect)
        - Type = derived from classification names (e.g. HAS_CUSTOMER)
        - Will use semantic names when CORTEX-17 adds relationship.name

    Tenant isolation:
        - All tenants share one Neo4j database
        - tenant_id is a property on every node
        - All queries filter by tenant_id
    """

    def __init__(
        self,
        classification_service: ClassificationService,
        relationship_service: RelationshipService,
        graph_repo: GraphRepository,
    ):
        # NOTE: Could optimize by accepting pre-fetched data from DataSyncService
        # instead of re-fetching from Supabase. Not needed at current scale.
        self.classification_service = classification_service
        self.relationship_service = relationship_service
        self.graph_repo = graph_repo

    async def sync_tenant_to_graph(self, tenant_id: UUID) -> GraphSyncResponse:
        """
        Full graph sync for a tenant.

        1. Fetch extracted files and relationships from Supabase
        2. MERGE nodes (one per extracted file, labeled by classification)
        3. MERGE edges between specific nodes using FK resolution
        4. Clean up orphaned nodes that no longer exist in Supabase

        Returns:
            GraphSyncResponse with counts of nodes/edges synced.
        """
        print(f"Graph sync starting for tenant {tenant_id}", flush=True)

        # 1. Fetch data from Supabase
        extracted_files = await self.classification_service.get_extracted_files(
            tenant_id
        )
        relationships = await self.relationship_service.get_relationships(tenant_id)

        print(
            f"  Found {len(extracted_files)} extracted files, "
            f"{len(relationships)} relationships",
            flush=True,
        )

        if not extracted_files:
            return GraphSyncResponse(
                status="skipped",
                message="No extracted files found for graph sync",
            )

        # Build lookup maps
        files_by_class: dict[str, list[ExtractedFile]] = {}
        for f in extracted_files:
            if not f.classification:
                continue
            cls_name = f.classification.name
            if cls_name not in files_by_class:
                files_by_class[cls_name] = []
            files_by_class[cls_name].append(f)

        print(
            f"  Classifications with files: {list(files_by_class.keys())}",
            flush=True,
        )

        # Set valid labels and edge types from this tenant's actual data
        valid_labels = {
            self._sanitize_label(f.classification.name)
            for f in extracted_files
            if f.classification
        }
        valid_edge_types = {self._derive_edge_type(r) for r in relationships}
        self.graph_repo.set_valid_labels(valid_labels)
        self.graph_repo.set_valid_relationship_types(valid_edge_types)

        # Track current extracted_file_ids for orphan cleanup
        current_ids = {
            str(f.extracted_file_id) for f in extracted_files if f.classification
        }

        tenant_id_str = str(tenant_id)

        # 2. MERGE nodes
        nodes_synced = 0
        for f in extracted_files:
            if not f.classification:
                print(
                    f"  WARNING: Skipping unclassified file: {f.name}",
                    flush=True,
                )
                continue

            label = self._sanitize_label(f.classification.name)
            properties = self._build_node_properties(f, tenant_id)

            print(f"  MERGE node: {label} ({f.name})", flush=True)
            await self._run_sync(
                self._merge_node, tenant_id_str, label, str(f.extracted_file_id), properties
            )
            nodes_synced += 1

        # 3. MERGE edges
        edges_synced = 0
        for f in extracted_files:
            if not f.classification:
                continue

            # Find relationships where this file's classification is the source
            relevant_rels = [
                r
                for r in relationships
                if r.from_classification.classification_id
                == f.classification.classification_id
            ]

            for rel in relevant_rels:
                # Get candidate target files
                target_class_name = rel.to_classification.name
                candidate_files = files_by_class.get(target_class_name, [])

                if not candidate_files:
                    continue

                # Resolve which specific target node this source connects to
                target_file = self._resolve_fk(
                    f.extracted_data, target_class_name, candidate_files
                )

                if not target_file:
                    print(
                        f"  No FK match: {f.name} -> {target_class_name} (skipped)",
                        flush=True,
                    )
                    continue

                edge_type = self._derive_edge_type(rel)
                print(
                    f"  MERGE edge: {f.name} -[{edge_type}]-> {target_file.name}",
                    flush=True,
                )
                await self._run_sync(
                    self._merge_edge,
                    tenant_id_str,
                    str(f.extracted_file_id),
                    str(target_file.extracted_file_id),
                    edge_type,
                )
                edges_synced += 1

        # 4. Clean up orphaned nodes for this tenant
        nodes_removed = await self._run_sync(
            self._cleanup_orphaned_nodes, tenant_id_str, current_ids
        )
        print(f"  Orphan cleanup: removed {nodes_removed} stale nodes", flush=True)

        print(
            f"Graph sync complete: {nodes_synced} nodes, "
            f"{edges_synced} edges, {nodes_removed} removed",
            flush=True,
        )

        return GraphSyncResponse(
            status="success",
            nodes_synced=nodes_synced,
            edges_synced=edges_synced,
            nodes_removed=nodes_removed,
        )

    # -------------------------------------------------------------------------
    # Neo4j operations (synchronous — called via run_in_executor)
    # -------------------------------------------------------------------------

    def _merge_node(self, tenant_id: str, label: str, node_id: str, properties: dict) -> None:
        """
        MERGE a node via graph_repository.create_node.
        Passes extracted_file_id as the uuid for the repo's MERGE key.
        """
        self.graph_repo.create_node(
            tenant_id=tenant_id,
            node_label=label,
            node_id=node_id,
            extracted_data=properties,
        )

    def _merge_edge(
        self, tenant_id: str, from_id: str, to_id: str, edge_type: str
    ) -> None:
        """
        MERGE an edge via graph_repository.create_relationship.
        """
        self.graph_repo.create_relationship(
            tenant_id=tenant_id,
            from_node_id=from_id,
            to_node_id=to_id,
            relationship_type=edge_type,
        )

    def _cleanup_orphaned_nodes(
        self, tenant_id: str, current_ids: set[str]
    ) -> int:
        """
        Remove nodes for this tenant that no longer exist in Supabase.
        Delegates Cypher execution to graph_repository.cleanup_orphaned_nodes.
        """
        return self.graph_repo.cleanup_orphaned_nodes(tenant_id, current_ids)

    # -------------------------------------------------------------------------
    # Helper methods
    # -------------------------------------------------------------------------

    async def _run_sync(self, fn, *args):
        """
        Wrap a synchronous GraphRepository call in run_in_executor
        so it doesn't block the async event loop.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(fn, *args))

    @staticmethod
    def _sanitize_label(classification_name: str) -> str:
        """
        Convert a classification name to a valid Neo4j label.
        "Product Specs" -> "ProductSpecs"
        "RFQs/Questionnaire" -> "RFQsQuestionnaire"
        """
        # Remove non-alphanumeric characters, keep spaces for CamelCase
        words = re.split(r"[^a-zA-Z0-9]+", classification_name)
        label = "_".join(word.upper() for word in words if word)
        # Neo4j labels can't start with a digit
        if label and label[0].isdigit():
            label = "N" + label
        return label

    @staticmethod
    def _build_node_properties(f: ExtractedFile, tenant_id: UUID) -> dict:
        """
        Build the property dict for a Neo4j node.
        Includes identity fields + flattened extracted data.

        Neo4j can't store nested dicts or lists of dicts as properties,
        so we flatten and skip non-primitive values.
        """
        props = {
            "extracted_file_id": str(f.extracted_file_id),
            "file_upload_id": str(f.file_upload_id),
            "tenant_id": str(tenant_id),
            "_identity_name": f.name,
            "_identity_classification": f.classification.name if f.classification else None,
        }

        # Flatten extracted_data and add primitive values as properties
        flat = GraphService._flatten_dict(f.extracted_data)
        for key, value in flat.items():
            safe_key = re.sub(r"[^a-zA-Z0-9_]", "_", key)
            # Neo4j supports: str, int, float, bool, and lists of primitives
            if isinstance(value, (str, int, float, bool)):
                props[safe_key] = value
            elif isinstance(value, list) and all(
                isinstance(v, (str, int, float, bool)) for v in value
            ):
                props[safe_key] = value
            elif value is None:
                continue
            else:
                # Convert complex types to JSON string
                try:
                    props[safe_key] = json.dumps(value)
                except (TypeError, ValueError):
                    continue

        return props

    @staticmethod
    def _derive_edge_type(rel: Relationship) -> str:
        """
        Derive a Neo4j edge type from a relationship.

        Currently uses classification names since semantic naming
        (CORTEX-17) hasn't shipped yet. Format: HAS_{TARGET_CLASSIFICATION}

        When relationship.name is available, this will use that instead.
        """
        # TODO: When CORTEX-17 adds relationship.name field, use it:
        # if hasattr(rel, 'name') and rel.name:
        #     return re.sub(r"[^A-Z0-9_]", "_", rel.name.upper())

        target_name = rel.to_classification.name.upper()
        sanitized = re.sub(r"[^A-Z0-9]+", "_", target_name).strip("_")
        return f"HAS_{sanitized}"

    # -------------------------------------------------------------------------
    # FK resolution (same pattern as DataSyncService)
    # TODO: These three methods (_resolve_fk, _flatten_dict, _find_matching_file)
    # are duplicated from DataSyncService. Extract to a shared utility module
    # (e.g. app/utils/fk_resolution.py) so improvements from CORTEX-16
    # (explicit key matching) apply to both Supabase sync and graph sync.
    # -------------------------------------------------------------------------

    @staticmethod
    def _resolve_fk(
        entry_data: dict, target_name: str, candidate_files: list[ExtractedFile]
    ) -> ExtractedFile | None:
        """
        Heuristic FK resolution — find which specific file in candidate_files
        is referenced by entry_data.

        Same logic as DataSyncService._resolve_fk:
        1. Flatten the source extracted data
        2. Look for keys matching the target classification name
        3. Search candidate files for matching values
        """
        target_keys = [
            target_name.lower(),
            target_name.replace(" ", "_").lower(),
            "model",
            "type",
            "category",
        ]

        flat_data = GraphService._flatten_dict(entry_data)

        for key, value in flat_data.items():
            if any(tk in key.lower() for tk in target_keys):
                match = GraphService._find_matching_file(value, candidate_files)
                if match:
                    return match

        return None

    @staticmethod
    def _flatten_dict(d: dict, parent_key: str = "", sep: str = "_") -> dict:
        """Flatten nested dict into single-level dict with joined keys."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(
                    GraphService._flatten_dict(v, new_key, sep=sep).items()
                )
            else:
                items.append((new_key, v))
        return dict(items)

    @staticmethod
    def _find_matching_file(
        search_val, candidate_files: list[ExtractedFile]
    ) -> ExtractedFile | None:
        """Find a candidate file whose name or data matches search_val."""
        if not search_val:
            return None

        search_val_str = str(search_val).lower()

        for f in candidate_files:
            # Check filename
            if search_val_str in f.name.lower():
                return f
            # Check extracted data
            data_str = json.dumps(f.extracted_data).lower()
            if f'"{search_val_str}"' in data_str:
                return f

        return None


def get_graph_service(
    classification_service: ClassificationService = Depends(
        get_classification_service
    ),
    relationship_service: RelationshipService = Depends(
        get_relationship_service
    ),
) -> GraphService:
    """FastAPI dependency injection for GraphService."""
    graph_repo = get_graph_repo()
    if not graph_repo:
        raise Exception("Neo4j is not available")

    return GraphService(
        classification_service,
        relationship_service,
        graph_repo,
    )