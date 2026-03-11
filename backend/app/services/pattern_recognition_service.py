import json
from typing import Any
from uuid import UUID

from supabase._async.client import AsyncClient

from app.core.litellm import LLMClient


class PatternRecognitionService:
    def __init__(self, supabase: AsyncClient):
        self.supabase = supabase
        self.llm = LLMClient()
        self.llm.set_system_prompt(
            "You are a Relationship Detector for a manufacturing Knowledge Base. "
            "Your job is to group documents into high-level business relationships (e.g., 'Supplier: Acme Corp', 'Project: Orbital', 'Competitor: X'). "
            "Avoid creating duplicate or slightly different names for the same thing."
        )

    async def analyze_relationships(self, tenant_id: UUID = None) -> list[dict[str, Any]]:
        """
        Scans all unlinked files and tries to link them to relationships.
        Note: tenant_id is deprecated and ignored in single-tenant mode.
        """
        # 1. Fetch unlinked files (file_relationships is empty for them)
        # However, supabase filtering for "doesn't have relation" is hard.
        # Let's get all files and then check? Or just get recent ones?
        # For MVP, let's process ALL files that have extracted_json data.

        files_resp = await self.supabase.table("extracted_files")\
            .select("file_id, extracted_json")\
            .execute()

        files = files_resp.data or []
        results = []

        for f in files:
            extracted_json = f.get("extracted_json")
            file_id = f.get("file_id")
            if not extracted_json:
                continue

            # Check if linked
            linked_resp = await self.supabase.table("file_relationships")\
                .select("relationship_id")\
                .eq("file_id", file_id)\
                .execute()

            if linked_resp.data:
                continue # Already linked

            await self.detect_and_link(file_id, extracted_json)
            results.append({"file_id": file_id, "status": "linked"})

        return results

    async def detect_and_link(self, file_id: UUID, extracted_json: dict, manual_context: str = None) -> None:
        """
        Detects relationships for a file based on its extracted JSON and links them.
        """
        # 1. Fetch existing relationships to avoid duplicates
        response = await self.supabase.table("relationships").select("relationship_name, relationship_description").execute()
        existing_relationships = response.data or []

        existing_list_str = "\n".join([f"- {r['relationship_name']}: {r['relationship_description']}" for r in existing_relationships])

        # 2. Ask LLM
        # Convert dictionary to a readable JSON string for the prompt
        extracted_data_str = json.dumps(extracted_json, indent=2) if isinstance(extracted_json, dict) else str(extracted_json)
        
        prompt = (
            f"Document Extracted Data:\n{extracted_data_str}\n"
            f"Manual Context (if any): \"{manual_context or 'None'}\"\n\n"
            f"Existing Relationships:\n{existing_list_str}\n\n"
            "Task:\n"
            "1. Does this document belong to any EXISTING relationship? If so, match it.\n"
            "2. If it clearly represents a NEW business entity (Supplier, Customer, Project) not in the list, create a NEW one.\n"
            "3. Return a JSON object with a list 'matches': [{ 'name': '...', 'description': '...', 'is_new': boolean, 'confidence': 0.0-1.0 }].\n"
            "   - Use 'confidence' >= 0.7 for valid matches.\n"
            "   - 'description' is required for new relationships.\n"
            "Returning JSON only."
        )

        try:
            llm_response = await self.llm.chat(prompt, json_response=True)
            # Handle potential dict return from our patched client
            if isinstance(llm_response, dict):
                 content_str = llm_response['choices'][0]['message']['content']
            else:
                 content_str = llm_response.choices[0].message.content

            content = json.loads(content_str)
            matches = content.get("matches", [])
        except Exception as e:
            print(f"Relationship detection failed: {e}")
            return

        # 3. Process matches
        for match in matches:
            if match.get("confidence", 0) < 0.7:
                continue

            rel_name = match["name"]
            rel_desc = match.get("description", "Auto-generated from analysis")

            rel_id = None

            # Check strictly if it exists in our cache or DB to be safe
            existing_match = next((r for r in existing_relationships if r["relationship_name"].lower() == rel_name.lower()), None)

            if existing_match:
                # Get ID from DB
                r_group = await self.supabase.table("relationships").select("relationship_id").eq("relationship_name", existing_match["relationship_name"]).single().execute()
                if r_group.data:
                    rel_id = r_group.data["relationship_id"]
            else:
                # Create NEW
                try:
                    new_rel = await self.supabase.table("relationships").insert({
                        "relationship_name": rel_name,
                        "relationship_description": rel_desc,
                    }).execute()
                    if new_rel.data:
                        rel_id = new_rel.data[0]["relationship_id"]
                except Exception as e:
                    print(f"Could not create relationship {rel_name}: {e}")
                    # Try to fetch again in case of race
                    continue

            if rel_id:
                # Link File to Relationship
                try:
                    await self.supabase.table("file_relationships").insert({
                        "file_id": str(file_id),
                        "relationship_id": rel_id,
                        "confidence_score": match["confidence"],
                        "source": "ai_inference"
                    }).execute()
                    print(f"Linked file {file_id} to relationship {rel_name}")
                except Exception as e:
                    print(f"Link failed: {e}")

    async def get_graph_data(self) -> dict[str, list[Any]]:
        """
        Fetches all graph data (Nodes and Edges) for visualization.
        """
        # 1. Fetch Relationships (Nodes type A)
        rels_resp = await self.supabase.table("relationships").select("*").execute()
        relationships = rels_resp.data or []

        # 2. Fetch Files that have relationships (Nodes type B)
        # We need file metadata. simpler to just fetch all files?
        # Let's fetch file_relationships joined with raw_files metadata if possible.
        # Supabase join: select(*, raw_files(file_name))

        links_resp = await self.supabase.table("file_relationships")\
            .select("*, raw_files(file_name)")\
            .execute()
        links = links_resp.data or []

        # 3. Construct Nodes and Edges
        nodes = []
        edges = []

        # Add Relationship Nodes
        for r in relationships:
            nodes.append({
                "id": r["relationship_id"],
                "label": r["relationship_name"],
                "type": "relationship",
                "description": r["relationship_description"]
            })

        # Add File Nodes and Edges
        # We want unique file nodes.
        seen_files = set()

        for link in links:
            file_id = link["file_id"]
            rel_id = link["relationship_id"]
            file_name = link["raw_files"]["file_name"] if link["raw_files"] else "Unknown File"

            if file_id not in seen_files:
                nodes.append({
                    "id": file_id,
                    "label": file_name,
                    "type": "file"
                })
                seen_files.add(file_id)

            edges.append({
                "source": file_id,
                "target": rel_id,
                "id": f"{file_id}-{rel_id}",
                "confidence": link.get("confidence_score")
            })

        return {"nodes": nodes, "edges": edges}
