import re
import json
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from app.repositories.product_repository import ProductRepository
from app.schemas.product_schemas import ProductIngest, ProductSearchResult

# Global variable to cache the model
_model = None

def get_model():
    global _model
    if _model is None:
        # Using a retrieval-optimized model as requested
        # 'intfloat/e5-base-v2' is excellent for semantic search
        _model = SentenceTransformer('intfloat/e5-base-v2')
    return _model

class ProductService:
    def __init__(self, product_repository: ProductRepository):
        self.repository = product_repository
        self.model = get_model()

    def build_searchable_text(self, product_json: Dict[str, Any]) -> str:
        """
        Extract meaningful text from product JSON.
        Excludes explicit ID fields and system timestamps.
        """
        # Define fields to skip (system fields, IDs, etc.)
        skip_keys = {'id', 'product_id', 'created_at', 'updated_at', 'sku', 'metadata'}
        
        parts = []
        
        # Prioritize key fields if they exist
        if 'name' in product_json:
            parts.append(f"Product Name: {product_json['name']}")
        if 'category' in product_json:
             parts.append(f"Category: {product_json['category']}")
        if 'description' in product_json:
            parts.append(f"Description: {product_json['description']}")
            
        # Process remaining fields dynamically
        features = []
        for key, value in product_json.items():
            if key in skip_keys or key in ['name', 'category', 'description']:
                continue
            if value and isinstance(value, (str, int, float, bool)):
                features.append(f"{key}: {value}")
            elif isinstance(value, list):
                features.append(f"{key}: {', '.join(map(str, value))}")
        
        if features:
            parts.append("Features: " + ", ".join(features))
            
        return "\n".join(parts)

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate normalized embedding for the given text.
        Prefix with 'passage: ' for e5 models when encoding documents.
        """
        # e5 models require 'passage: ' prefix for documents
        input_text = f"passage: {text}"
        embedding = self.model.encode(input_text, normalize_embeddings=True)
        return embedding.tolist()

    def encode_query(self, query: str) -> List[float]:
        """
        Generate normalized embedding for a search query.
        Prefix with 'query: ' for e5 models.
        """
        input_text = f"query: {query}"
        embedding = self.model.encode(input_text, normalize_embeddings=True)
        return embedding.tolist()

    async def ingest_product(self, product_data: ProductIngest) -> None:
        """
        Ingest a product: structured extraction -> embedding -> upsert.
        """
        # 1. Extract searchable text
        # Combine top-level fields plus any metadata for extraction
        full_data = product_data.metadata.copy()
        full_data['product_id'] = product_data.product_id
        # Assuming product_data might have other fields if extended, but here we work with what we have
        
        searchable_text = self.build_searchable_text(full_data)
        
        # 2. Generate embedding
        embedding = self.generate_embedding(searchable_text)
        
        # 3. Prepare DB record
        db_record = {
            "product_id": product_data.product_id,
            "metadata": product_data.metadata,
            "searchable_text": searchable_text,
            "embedding": embedding
        }
        
        # 4. Upsert
        await self.repository.upsert_product(db_record)

    async def search(self, query: str, limit: int = 20, filters: Dict[str, Any] = {}) -> List[ProductSearchResult]:
        """
        Perform hybrid search:
        1. Try exact Product ID match.
        2. If no ID match, perform semantic vector search.
        """
        results = []

        # A) Exact Product ID Lookup
        # Simple heuristic: if query looks like an ID (alphanumeric, no spaces, short-ish)
        # Adjust pattern as needed for specific ID format
        if re.match(r'^[a-zA-Z0-9_\-]+$', query):
            exact_match = await self.repository.get_by_product_id(query)
            if exact_match:
                # Convert to result format
                return [ProductSearchResult(
                    **exact_match,
                    similarity=1.0,
                    score=1.0
                )]

        # B) Semantic Search
        query_embedding = self.encode_query(query)
        
        matches = await self.repository.search_products(
            query_embedding=query_embedding,
            match_threshold=0.7, # Configurable
            match_count=limit,
            filters=filters
        )
        
        # Convert to Pydantic models
        for match in matches:
            results.append(ProductSearchResult(
                id=match['id'],
                product_id=match['product_id'],
                metadata=match['metadata'],
                searchable_text=match['searchable_text'],
                created_at=match.get('created_at', ''), # Handle missing if projection differs
                similarity=match['similarity'],
                score=match['similarity']
            ))
            
        return results
