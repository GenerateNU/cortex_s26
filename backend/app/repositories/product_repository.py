from typing import List, Dict, Any, Optional
from supabase._async.client import AsyncClient
from app.schemas.product_schemas import ProductIngest, Product

class ProductRepository:
    def __init__(self, supabase: AsyncClient):
        self.supabase = supabase

    async def upsert_product(self, product_data: Dict[str, Any]) -> None:
        """
        Upsert a product record into the database.
        """
        result = await (
            self.supabase.table("products")
            .upsert(product_data, on_conflict="product_id")
            .execute()
        )
        if not result.data:
            # Supabase upsert might return empty list if successful but nothing returned, 
            # or raise error if failed. We rely on exception handling for failures.
            pass

    async def search_products(
        self, 
        query_embedding: List[float], 
        match_threshold: float = 0.7, 
        match_count: int = 20,
        filters: Dict[str, Any] = {}
    ) -> List[Dict[str, Any]]:
        """
        Perform a hybrid search using the match_products RPC function.
        """
        params = {
            "query_embedding": query_embedding,
            "match_threshold": match_threshold,
            "match_count": match_count,
            "filter_metadata": filters
        }
        
        result = await self.supabase.rpc("match_products", params).execute()
        return result.data or []

    async def get_by_product_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Exact lookup by product_id.
        """
        result = await (
            self.supabase.table("products")
            .select("*")
            .eq("product_id", product_id)
            .execute()
        )
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
