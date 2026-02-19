from supabase._async.client import AsyncClient


class SchemaRepository:
    def __init__(self, supabase: AsyncClient):
        self.supabase = supabase

    async def execute_sql(self, sql_query: str) -> None:
        """
        Executes a raw SQL query using the `execute_sql` RPC function.
        """
        await self.supabase.rpc("execute_sql", {"query": sql_query}).execute()
