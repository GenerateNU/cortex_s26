from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ProductBase(BaseModel):
    product_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ProductIngest(ProductBase):
    pass

class Product(ProductBase):
    id: int
    searchable_text: str
    created_at: str

class ProductSearchRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = 20

class ProductSearchResult(Product):
    similarity: float
    score: float  # Alias for similarity to be explicit
