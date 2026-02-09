from uuid import UUID

from supabase._async.client import AsyncClient


class SchemaRepository:
    def __init__(self, supabase: AsyncClient):
        self.supabase = supabase

    async def execute_sql(self, sql_query: str) -> None:
        """
        Executes a raw SQL query using the `execute_sql` RPC function.
        """
        await self.supabase.rpc("execute_sql", {"query": sql_query}).execute()

    async def upsert_row(
        self,
        schema_name: str,
        table_name: str,
        data: dict,
    ) -> None:
        """
        Build and execute a dynamic UPSERT into a tenant-schema table.
        ON CONFLICT (id) updates all columns except id and tenant_id.
        """
        columns = ", ".join(f'"{col}"' for col in data)

        val_parts: list[str] = []
        for v in data.values():
            if v is None:
                val_parts.append("NULL")
            elif isinstance(v, str):
                val_parts.append(f"'{v.replace(chr(39), chr(39) + chr(39))}'")
            else:
                val_parts.append(str(v))
        vals = ", ".join(val_parts)

        update_cols = [
            f'"{col}" = EXCLUDED."{col}"'
            for col in data if col not in ("id", "tenant_id")
        ]
        update_clause = (
            ", ".join(update_cols) if update_cols else 'data = EXCLUDED."data"'
        )

        sql = f"""
INSERT INTO "{schema_name}"."{table_name}" ({columns})
VALUES ({vals})
ON CONFLICT (id) DO UPDATE SET {update_clause};
""".strip()

        await self.execute_sql(sql)

    async def insert_join_link(
        self,
        schema_name: str,
        join_table: str,
        from_column: str,
        to_column: str,
        from_id: UUID,
        to_id: UUID,
    ) -> None:
        """
        Insert a single row into a many-to-many join table.
        ON CONFLICT DO NOTHING avoids duplicate link errors.
        """
        sql = f"""
INSERT INTO "{schema_name}"."{join_table}" ("{from_column}", "{to_column}")
VALUES ('{from_id}', '{to_id}')
ON CONFLICT DO NOTHING;
""".strip()

        await self.execute_sql(sql)
