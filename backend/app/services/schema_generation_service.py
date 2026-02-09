import hashlib

from app.schemas.classification_schemas import Classification
from app.schemas.migration_schemas import Migration, MigrationCreate
from app.schemas.relationship_schemas import Relationship


class SchemaGenerationService:
    @staticmethod
    def table_name_for_classification(c: Classification) -> str:
        """
        Deterministic mapping from classification name to SQL table name.
        Converts spaces and special characters to underscores, keeps only alphanumeric and underscores.
        Example: "Product Brochure/Leaflet" -> "product_brochure_leaflet"
        Example: "Robot Specifications" -> "robot_specifications"
        """
        name = c.name.lower()
        name = "".join(char if char.isalnum() else "_" for char in name)
        while "__" in name:
            name = name.replace("__", "_")
        name = name.strip("_")

        if name and name[0].isdigit():
            name = "tbl_" + name

        return name

    @staticmethod
    def get_schema_name(tenant_id) -> str:
        return f"tenant_{str(tenant_id).replace('-', '_')}"

    @staticmethod
    def _get_created_tables(migrations: list[Migration], schema_name: str) -> set[str]:
        created_tables = set()
        prefix = f"create_table_{schema_name}_"
        for m in migrations:
            if m.name.startswith(prefix):
                table_name = m.name.replace(prefix, "")
                created_tables.add(table_name)
        return created_tables

    @staticmethod
    def _get_dropped_tables(migrations: list[Migration], schema_name: str) -> set[str]:
        dropped = set()
        prefix = f"drop_table_{schema_name}_"
        for m in migrations:
            if m.name.startswith(prefix):
                table_name = m.name.replace(prefix, "")
                dropped.add(table_name)
        return dropped

    @staticmethod
    def _truncate_constraint_name(name: str, max_length: int = 63) -> str:
        name_bytes = name.encode("utf-8")
        if len(name_bytes) <= max_length:
            return name

        truncated_bytes = name_bytes[:max_length]
        while truncated_bytes and (truncated_bytes[-1] & 0xC0) == 0x80:
            truncated_bytes = truncated_bytes[:-1]

        return truncated_bytes.decode("utf-8", errors="ignore")

    @classmethod
    def _make_unique_constraint_name(cls, base_name: str, existing_names: set[str], max_length: int = 63) -> str:
        if base_name not in existing_names:
            truncated = cls._truncate_constraint_name(base_name, max_length)
            if truncated not in existing_names:
                existing_names.add(truncated)
                return truncated

        truncated = cls._truncate_constraint_name(base_name, max_length - 9)
        hash_suffix = hashlib.md5(base_name.encode("utf-8")).hexdigest()[:8]
        unique_name = f"{truncated}_{hash_suffix}"
        unique_name = cls._truncate_constraint_name(unique_name, max_length)

        counter = 0
        while unique_name in existing_names and counter < 100:
            counter += 1
            hash_suffix = hashlib.md5(f"{base_name}_{counter}".encode()).hexdigest()[:8]
            unique_name = cls._truncate_constraint_name(f"{truncated}_{hash_suffix}", max_length)

        existing_names.add(unique_name)
        return unique_name

    @classmethod
    def create_migrations(
        cls,
        classifications: list[Classification],
        relationships: list[Relationship],
        initial_migrations: list[Migration],
    ) -> list[MigrationCreate]:
        """
        PURE FUNCTION.
        Given classifications, relationships, and existing migrations, return new migrations.
        """
        if not classifications:
            return []

        existing_names = {m.name for m in initial_migrations}
        base_sequence = max((m.sequence for m in initial_migrations), default=0)
        next_seq = base_sequence + 1
        new_migrations: list[MigrationCreate] = []

        tenant_id = classifications[0].tenant_id if classifications else None
        if not tenant_id and initial_migrations:
            tenant_id = initial_migrations[0].tenant_id

        schema_name = cls.get_schema_name(tenant_id) if tenant_id else "public"

        # Step 0: Create Schema
        schema_migration_name = f"create_schema_{schema_name}"
        if schema_migration_name not in existing_names:
            new_migrations.append(
                MigrationCreate(
                    tenant_id=tenant_id,
                    name=schema_migration_name,
                    sql=f'CREATE SCHEMA IF NOT EXISTS "{schema_name}";',
                    sequence=next_seq,
                )
            )
            existing_names.add(schema_migration_name)
            next_seq += 1

        # Step 1: Handle DROPS
        created_tables = cls._get_created_tables(initial_migrations, schema_name)
        dropped_tables = cls._get_dropped_tables(initial_migrations, schema_name)
        active_tables = created_tables - dropped_tables

        current_classification_tables = {cls.table_name_for_classification(c) for c in classifications}
        tables_to_drop = active_tables - current_classification_tables

        for table_name in sorted(tables_to_drop):
            clean_table_name = table_name.split(".")[-1] if "." in table_name else table_name
            mig_name = f"drop_table_{schema_name}_{clean_table_name}"
            if mig_name in existing_names:
                continue
            sql = f'DROP TABLE IF EXISTS "{schema_name}"."{clean_table_name}" CASCADE;'
            if tenant_id:
                new_migrations.append(
                    MigrationCreate(
                        tenant_id=tenant_id,
                        name=mig_name,
                        sql=sql,
                        sequence=next_seq,
                    )
                )
                existing_names.add(mig_name)
                next_seq += 1

        # Step 2: Create Tables
        for c in classifications:
            table_name = cls.table_name_for_classification(c)
            mig_name = f"create_table_{schema_name}_{table_name}"
            if mig_name in existing_names:
                continue

            sql = f"""
CREATE TABLE IF NOT EXISTS "{schema_name}"."{table_name}" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
""".strip()
            new_migrations.append(
                MigrationCreate(
                    tenant_id=c.tenant_id,
                    name=mig_name,
                    sql=sql,
                    sequence=next_seq,
                )
            )
            existing_names.add(mig_name)
            next_seq += 1

        # Step 3: Drop Relationships
        def _parse_relationship_migration_name(name: str) -> tuple[str, str, str] | None:
            if not name.startswith("rel_"):
                return None
            parts = name.split("_")
            if len(parts) < 5:
                return None
            rel_type = "_".join(parts[1:-3])
            from_table = parts[-2]
            to_table = parts[-1]
            return rel_type.upper(), from_table, to_table

        existing_relationships = set()
        relationships_on_dropped_tables = set()
        for m in initial_migrations:
            parsed = _parse_relationship_migration_name(m.name)
            if not parsed:
                continue
            rel_type, from_table, to_table = parsed
            if from_table in tables_to_drop or to_table in tables_to_drop:
                relationships_on_dropped_tables.add(parsed)
            elif from_table in active_tables and to_table in active_tables:
                existing_relationships.add(parsed)

        desired_relationships = set()
        for rel in relationships:
            from_table = cls.table_name_for_classification(rel.from_classification)
            to_table = cls.table_name_for_classification(rel.to_classification)
            if from_table not in current_classification_tables or to_table not in current_classification_tables:
                continue
            raw_type = getattr(rel.type, "value", rel.type)
            rel_type_norm = str(raw_type).upper().replace("-", "_")
            desired_relationships.add((rel_type_norm, from_table, to_table))

        relationships_to_drop = existing_relationships - desired_relationships
        relationships_to_drop |= relationships_on_dropped_tables

        for rel_type_norm, from_table, to_table in sorted(relationships_to_drop):
            mig_name = f"drop_rel_{rel_type_norm.lower()}_{schema_name}_{from_table}_{to_table}"
            if mig_name in existing_names:
                continue

            if rel_type_norm in {"ONE_TO_MANY", "ONE_TO_ONE"}:
                sql = f"""
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = '{schema_name}'
          AND table_name = '{from_table}'
    ) THEN
        ALTER TABLE "{schema_name}"."{from_table}"
        DROP COLUMN IF EXISTS "{to_table}_id" CASCADE;
    END IF;
END $$;
""".strip()
            elif rel_type_norm == "MANY_TO_MANY":
                join_table = f"{from_table}_{to_table}_join"
                sql = f'DROP TABLE IF EXISTS "{schema_name}"."{join_table}" CASCADE;'
            else:
                sql = f"-- TODO: drop logic for relationship type {rel_type_norm}"

            new_migrations.append(
                MigrationCreate(
                    tenant_id=tenant_id,
                    name=mig_name,
                    sql=sql,
                    sequence=next_seq,
                )
            )
            existing_names.add(mig_name)
            next_seq += 1

        # Step 4: Create Relationships
        constraint_names_used = set()
        for rel in relationships:
            from_table = cls.table_name_for_classification(rel.from_classification)
            to_table = cls.table_name_for_classification(rel.to_classification)

            if from_table not in current_classification_tables or to_table not in current_classification_tables:
                continue

            raw_type = getattr(rel.type, "value", rel.type)
            rel_type_norm = str(raw_type).upper().replace("-", "_")
            mig_name = f"rel_{rel_type_norm.lower()}_{schema_name}_{from_table}_{to_table}"

            if mig_name in existing_names:
                continue

            if rel_type_norm == "ONE_TO_MANY":
                base_constraint_name = f"fk_{from_table}_{to_table}"
                constraint_name = cls._make_unique_constraint_name(base_constraint_name, constraint_names_used)
                sql = f"""
DO $$
BEGIN
    ALTER TABLE "{schema_name}"."{from_table}"
    ADD COLUMN IF NOT EXISTS "{to_table}_id" UUID;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_namespace n ON c.connamespace = n.oid
        WHERE c.conname = '{constraint_name}'
        AND n.nspname = '{schema_name}'
    ) THEN
        ALTER TABLE "{schema_name}"."{from_table}"
        ADD CONSTRAINT "{constraint_name}"
        FOREIGN KEY ("{to_table}_id")
        REFERENCES "{schema_name}"."{to_table}"(id);
    END IF;
END $$;
""".strip()

            elif rel_type_norm == "ONE_TO_ONE":
                base_constraint_name = f"fk_{from_table}_{to_table}"
                constraint_name = cls._make_unique_constraint_name(base_constraint_name, constraint_names_used)
                base_unique_constraint_name = f"{base_constraint_name}_unique"
                unique_constraint_name = cls._make_unique_constraint_name(base_unique_constraint_name, constraint_names_used)
                sql = f"""
DO $$
BEGIN
    ALTER TABLE "{schema_name}"."{from_table}"
    ADD COLUMN IF NOT EXISTS "{to_table}_id" UUID;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_namespace n ON c.connamespace = n.oid
        WHERE c.conname = '{constraint_name}'
        AND n.nspname = '{schema_name}'
    ) THEN
        ALTER TABLE "{schema_name}"."{from_table}"
        ADD CONSTRAINT "{constraint_name}"
        FOREIGN KEY ("{to_table}_id")
        REFERENCES "{schema_name}"."{to_table}"(id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_namespace n ON c.connamespace = n.oid
        WHERE c.conname = '{unique_constraint_name}'
        AND n.nspname = '{schema_name}'
    ) THEN
        ALTER TABLE "{schema_name}"."{from_table}"
        ADD CONSTRAINT "{unique_constraint_name}" UNIQUE ("{to_table}_id");
    END IF;
END $$;
""".strip()

            elif rel_type_norm == "MANY_TO_MANY":
                join_table = f"{from_table}_{to_table}_join"
                base_fk_from_name = f"fk_{join_table}_{from_table}"
                base_fk_to_name = f"fk_{join_table}_{to_table}"
                fk_from_constraint = cls._make_unique_constraint_name(base_fk_from_name, constraint_names_used)
                fk_to_constraint = cls._make_unique_constraint_name(base_fk_to_name, constraint_names_used)

                sql = f"""
CREATE TABLE IF NOT EXISTS "{schema_name}"."{join_table}" (
    "{from_table}_id" UUID NOT NULL,
    "{to_table}_id" UUID NOT NULL,
    CONSTRAINT "{fk_from_constraint}"
        FOREIGN KEY ("{from_table}_id")
        REFERENCES "{schema_name}"."{from_table}"(id),
    CONSTRAINT "{fk_to_constraint}"
        FOREIGN KEY ("{to_table}_id")
        REFERENCES "{schema_name}"."{to_table}"(id),
    PRIMARY KEY ("{from_table}_id", "{to_table}_id")
);
""".strip()
            else:
                sql = f"-- TODO: implement SQL for relationship {mig_name}"

            new_migrations.append(
                MigrationCreate(
                    tenant_id=rel.tenant_id,
                    name=mig_name,
                    sql=sql,
                    sequence=next_seq,
                )
            )
            existing_names.add(mig_name)
            next_seq += 1

        return new_migrations

def get_schema_generation_service() -> SchemaGenerationService:
    return SchemaGenerationService()
