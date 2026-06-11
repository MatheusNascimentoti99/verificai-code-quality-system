"""
General analysis Pydantic schemas for VerificAI Backend.
"""

from typing import List, Optional, Any, Dict

from pydantic import BaseModel


class GeneralAnalysisRequest(BaseModel):
    """Request model for general analysis."""
    name: str
    description: Optional[str] = None
    file_paths: List[str]
    criteria: List[str]
    llm_provider: str = "openai"
    temperature: float = 0.7
    max_tokens: int = 500000


class AnalyzeSelectedRequest(BaseModel):
    """Request model for analyzing selected criteria."""
    criteria_ids: List[str]
    file_paths: List[str] = []
    use_code_entry: bool = False
    code_entry_id: Optional[str] = None
    analysis_name: Optional[str] = "Análise de Critérios Gerais"
    project_name: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 500000


class GeneralCriteriaResponse(BaseModel):
    """Criteria response model for general analysis."""
    id: str
    text: str
    active: bool = True


class CriterionCreate(BaseModel):
    """Request model for creating a criterion."""
    text: str


class GeneralAnalysisResultResponse(BaseModel):
    """Response model for general analysis results."""
    id: str
    analysis_type: str = "general"
    timestamp: Any
    overall_assessment: str
    criteria_results: List[dict]
    token_usage: Dict[str, Any]
    processing_time: float
    status: str
    project_name: Optional[str] = None