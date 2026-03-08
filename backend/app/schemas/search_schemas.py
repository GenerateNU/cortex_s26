from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=20)
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)

class SearchResult(BaseModel):
    file_id: UUID
    file_name: str | None
    file_type: str | None
    summary: str | None
    extracted_json: dict[str, Any] | None
    similarity: float

class SearchResponse(BaseModel):
    results: list[SearchResult]

class RAGSearchResponse(BaseModel):
    answer: str
    sources: list[SearchResult]
