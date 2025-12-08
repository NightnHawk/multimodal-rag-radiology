"""Pydantic models for API requests and responses."""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class IndexRequest(BaseModel):
    """Request model for batch indexing."""
    json_path: Optional[str] = None
    dicom_folder: Optional[str] = None


class QueryRequest(BaseModel):
    """Request model for querying."""
    query_id: Optional[str] = None


class RegenerateRequest(BaseModel):
    """Request model for regeneration."""
    query_id: str
    use_same_retrieval: bool = True


class RetrievedDocument(BaseModel):
    """Model for retrieved document from OpenSearch."""
    image_path: str
    short_description: str
    full_description: str
    score: float


class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    query_id: str
    generated_description: str
    retrieved_documents: List[RetrievedDocument]
    quality_score: Optional[float] = None
    quality_approved: bool
    message: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    message: str


class OpenSearchStatusResponse(BaseModel):
    """Response model for OpenSearch status."""
    connected: bool
    index_exists: bool
    document_count: Optional[int] = None
    message: str

