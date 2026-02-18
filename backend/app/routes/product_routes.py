from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any

from app.services.product_service import ProductService
from app.repositories.product_repository import ProductRepository
from app.schemas.product_schemas import ProductIngest, ProductSearchResult, ProductSearchRequest
from app.core.supabase import get_async_supabase
from supabase._async.client import AsyncClient

router = APIRouter(prefix="/products", tags=["products"])

def get_product_service(supabase: AsyncClient = Depends(get_async_supabase)) -> ProductService:
    repository = ProductRepository(supabase)
    return ProductService(repository)

@router.post("/ingest", status_code=201)
async def ingest_product(
    product: ProductIngest,
    service: ProductService = Depends(get_product_service)
):
    """
    Ingest a product into the semantic search engine.
    Extracts text, generates embeddings, and upserts to the database.
    """
    try:
        await service.ingest_product(product)
        return {"message": "Product ingested successfully", "product_id": product.product_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search", response_model=List[ProductSearchResult])
async def search_products(
    request: ProductSearchRequest,
    service: ProductService = Depends(get_product_service)
):
    """
    Perform a hybrid search for products.
    Uses exact ID match if query looks like an ID, otherwise performs semantic vector search.
    """
    try:
        results = await service.search(
            query=request.query,
            limit=request.limit,
            filters=request.filters or {}
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
