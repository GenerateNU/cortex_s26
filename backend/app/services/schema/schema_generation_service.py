import re
from typing import Any


class SchemaGenerationService:
    """
    Pure service to generate SQL based on classifications and relationships.
    """

    @staticmethod
    def generate_migrations(
        tenant_id: str,
        classifications: list[dict[str, Any]],
        relationships: list[dict[str, Any]]
    ) -> list[str]:
        """
        Generates a list of SQL statements (migrations).
        """
        migration_sqls = []

        # 1. Create Schema for Tenant
        schema_name = f"tenant_{tenant_id.replace('-', '_')}"
        migration_sqls.append(f"CREATE SCHEMA IF NOT EXISTS {schema_name};")

        # 2. Create Tables for Classifications
        for cls in classifications:
            table_name = SchemaGenerationService._sanitize_name(cls["name"])

            # Basic table structure for extracted data
            # Including jsonb_data for flexibility
            sql = f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.{table_name} (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                file_id UUID REFERENCES public.raw_files(file_id),
                data JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """
            migration_sqls.append(sql.strip())

        # 3. Create Foreign Keys from Relationships?
        # If relationships are "Supplier" -> "Order", how is that mapped?
        # For now, let's keep it simple: tables are created.
        # Relationships might be implemented as link tables or FKs if cardinality is known.
        # Given PRD says "Relationships become foreign keys", we'd need to know source/target.
        # But `relationships` table groups files. Matches are `file_id` <-> `relationship_id`.
        # This part is tricky without clear "Class A -> Class B" definition.
        # relationships table is more like "Clusters".
        # Let's assume for this MVP we just create the tables for the classifications.

        return migration_sqls

    @staticmethod
    def _sanitize_name(name: str) -> str:
        # Lowercase, replace spaces/special chars with underscores
        clean = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
        # Ensure starts with letter
        if not clean[0].isalpha():
            clean = "tbl_" + clean
        return clean[:63] # Postgres limit
