"""
Schemas for structured LLM responses.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class BaseResponseModel(BaseModel, ABC):
    """Abstract base class for LLM structured output models.

    Subclasses must implement ``get_response_schema`` so that the LLM
    service can retrieve the JSON schema polymorphically when building
    the ``generationConfig.responseFormat`` payload.
    """

    @classmethod
    @abstractmethod
    def get_response_schema(cls) -> dict:
        """Return the JSON schema describing the expected response structure."""
        ...


class StructuredCriterionResult(BaseResponseModel):
    """Structured result for one analyzed criterion."""

    id: int = Field(..., description="Unique identifier for the criterion")
    assessment: str = Field(..., description="Assessment text")
    status: str = Field(..., description="Conformity status")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    evidence: List[str] = Field(default_factory=list, description="Supporting evidence")
    recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations")

    @classmethod
    def get_response_schema(cls) -> dict:
        """Return the JSON schema for a single criterion result."""
        return cls.model_json_schema()


class StructuredAnalysisOutput(BaseResponseModel):
    """Generic structured analysis output."""

    overall_assessment: str = Field(..., description="Overall assessment")
    detailed_findings: str = Field(default="", description="Detailed findings")
    criteria_results: List[StructuredCriterionResult] = Field(default_factory=list, description="List of structured results for each criterion")
    code_examples: List[Dict[str, Any]] = Field(default_factory=list, description="List of code examples")
    recommendations: List[str] = Field(default_factory=list, description="List of recommendations")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence score")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Analysis metrics")
    file_analysis: Dict[str, Any] = Field(default_factory=dict, description="File analysis details")

    @classmethod
    def get_response_schema(cls) -> dict:
        """Return the JSON schema for the full analysis output."""
        return cls.model_json_schema()