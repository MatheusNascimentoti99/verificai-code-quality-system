"""
Pydantic schemas for Architectural Analysis endpoints.
Follows the same patterns as schemas/general_analysis.py.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


# ---------------------------------------------------------------------------
# ArchitecturalDoc schemas
# ---------------------------------------------------------------------------

class ArchitecturalDocCreate(BaseModel):
    """Schema for creating a new architectural documentation entry."""
    title: str = Field(..., min_length=1, max_length=200)
    sharepoint_url: Optional[str] = Field(None, max_length=500)
    content: str = Field(..., min_length=1, max_length=500_000)
    content_type: Optional[str] = Field("text", pattern="^(text|markdown|html)$")

    @validator("content")
    def content_not_empty(cls, v: str) -> str:  # noqa: N805
        if not v.strip():
            raise ValueError("O conteúdo da documentação não pode estar vazio.")
        return v


class ArchitecturalDocUpdate(BaseModel):
    """Schema for updating an architectural documentation entry."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    sharepoint_url: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = Field(None, min_length=1, max_length=500_000)
    content_type: Optional[str] = Field(None, pattern="^(text|markdown|html)$")


class ArchitecturalDocResponse(BaseModel):
    """Response schema for an architectural documentation entry."""
    id: int
    user_id: int
    title: str
    sharepoint_url: Optional[str]
    content: str
    file_name: Optional[str]
    content_type: Optional[str]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# ArchitecturalCriteria schemas
# ---------------------------------------------------------------------------

class ArchitecturalCriteriaCreate(BaseModel):
    """Schema for creating a new architectural criterion."""
    text: str = Field(..., min_length=1)


class ArchitecturalCriteriaUpdate(BaseModel):
    """Schema for updating an architectural criterion."""
    text: Optional[str] = Field(None, min_length=1)
    is_active: Optional[bool] = None


class ArchitecturalCriteriaResponse(BaseModel):
    """Response schema for an architectural criterion."""
    id: str           # formatted as "arch_criteria_{id}"
    text: str
    active: bool
    order: int = 0

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Analysis execution schemas
# ---------------------------------------------------------------------------

class ArchitecturalAnalyzeRequest(BaseModel):
    """Request schema for running an architectural analysis."""
    analysis_name: Optional[str] = Field("Análise Arquitetural", min_length=1, max_length=200)
    doc_id: Optional[int] = None              # existing saved doc
    criteria_ids: List[str] = Field(default_factory=list)  # "arch_criteria_{id}"
    file_paths: List[str] = Field(default_factory=list)
    use_code_entry: bool = False
    code_entry_id: Optional[str] = None
    temperature: float = Field(0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(500_000, ge=1000)


class ArchitecturalAnalysisResultResponse(BaseModel):
    """Response schema for a completed architectural analysis."""
    id: int
    analysis_name: str
    overall_status: Optional[str]
    criteria_count: int
    criteria_results: Dict[str, Any]
    raw_response: str
    model_used: Optional[str]
    usage: Optional[Dict[str, Any]]
    file_paths: List[str]
    processing_time: Optional[str]
    doc_id: Optional[int]

    class Config:
        from_attributes = True
