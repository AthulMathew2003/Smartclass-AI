import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class RagSearchRequest(BaseModel):
    subject_id: uuid.UUID = Field(..., description="The subject to search materials within")
    query: str = Field(..., min_length=1, max_length=1000, description="The semantic search query")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Maximum number of relevant chunks to retrieve")


class RagSearchResultItem(BaseModel):
    material_id: uuid.UUID
    material_title: str
    filename: str
    chunk_index: int
    page_number: Optional[int] = None
    slide_number: Optional[int] = None
    content: str
    score: float = Field(..., description="Similarity or relevance score")


class RagSearchResponse(BaseModel):
    query: str
    subject_id: uuid.UUID
    results_count: int
    results: List[RagSearchResultItem]


class RagIndexStatusResponse(BaseModel):
    material_id: uuid.UUID
    status: str
    indexed_at: Optional[datetime] = None
    chunk_count: int = 0
    content_hash: Optional[str] = None
    error: Optional[str] = None


class RagReindexRequest(BaseModel):
    force: bool = Field(False, description="If True, ignores existing content hash and re-extracts/re-embeds")
