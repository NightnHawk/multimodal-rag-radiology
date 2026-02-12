"""Pydantic models for API requests and responses."""
from pydantic import BaseModel, Field
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
    mean_similarity: Optional[float] = None  # Mean similarity score from validation


class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    query_id: str
    generated_description: str
    retrieved_documents: List[RetrievedDocument]
    quality_score: Optional[float] = None
    quality_approved: bool
    message: Optional[str] = None
    validation_info: Optional[Dict[str, Any]] = None  # Description validation results
    prompt_used: Optional[str] = None  # The prompt that was sent to GPT-4o


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


class StructuredDescription(BaseModel):
    """Structured output model for GPT-4o response."""
    overall_assessment: str = Field(
        description="Overall assessment of the RTG scan, including general observations and initial impressions"
    )
    key_findings: List[str] = Field(
        description="List of key findings, abnormalities, or notable features observed in the scan"
    )
    notable_features: List[str] = Field(
        default_factory=list,
        description="List of notable anatomical features, structures, or patterns visible in the scan"
    )
    abnormalities: List[str] = Field(
        default_factory=list,
        description="List of any abnormalities, pathologies, or concerning findings. Empty list if none found."
    )
    comparison_with_references: Optional[str] = Field(
        default=None,
        description="Comparison with reference cases if provided, or None if no references were used"
    )
    clinical_notes: Optional[str] = Field(
        default=None,
        description="Additional clinical notes or recommendations if relevant"
    )
    
    def to_formatted_string(self) -> str:
        """Convert structured output to a formatted string description."""
        parts = []
        
        parts.append(f"Overall Assessment:\n{self.overall_assessment}\n")
        
        if self.key_findings:
            parts.append(f"Key Findings:")
            for finding in self.key_findings:
                parts.append(f"- {finding}")
            parts.append("")
        
        if self.notable_features:
            parts.append(f"Notable Features:")
            for feature in self.notable_features:
                parts.append(f"- {feature}")
            parts.append("")
        
        if self.abnormalities:
            parts.append(f"Abnormalities:")
            for abnormality in self.abnormalities:
                parts.append(f"- {abnormality}")
            parts.append("")
        else:
            parts.append("Abnormalities: None detected\n")
        
        if self.comparison_with_references:
            parts.append(f"Comparison with Reference Cases:\n{self.comparison_with_references}\n")
        
        if self.clinical_notes:
            parts.append(f"Clinical Notes:\n{self.clinical_notes}\n")
        
        return "\n".join(parts)

