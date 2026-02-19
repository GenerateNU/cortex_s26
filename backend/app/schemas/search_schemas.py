from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=20)
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)

class SearchResult(BaseModel):
    file_id: UUID
    file_name: Optional[str]
    file_type: Optional[str]
    summary: Optional[str]
    extracted_json: Optional[dict[str, Any]]
    similarity: float

class SearchResponse(BaseModel):
    results: list[SearchResult]
