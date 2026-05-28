"""
Schemas for structured LLM responses.
"""

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class StructuredCriterionResult(BaseModel):
    """Structured result for one analyzed criterion."""

    id: int = Field(..., description="Unique identifier for the criterion")
    assessment: str = Field(..., description="Assessment text")
    status: str = Field(..., description="Conformity status")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    evidence: List[str] = Field(default_factory=list, description="Supporting evidence")
    recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations")


class StructuredAnalysisOutput(BaseModel):
    """Generic structured analysis output."""

    overall_assessment: str = Field(..., description="Overall assessment")
    detailed_findings: str = Field(default="", description="Detailed findings")
    criteria_results: List[StructuredCriterionResult] = Field(default_factory=list)
    code_examples: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    file_analysis: Dict[str, Any] = Field(default_factory=dict)