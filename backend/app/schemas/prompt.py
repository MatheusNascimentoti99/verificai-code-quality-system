"""
Prompt Pydantic schemas for VerificAI Backend
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator

from app.models.prompt import PromptType, PromptCategory, PromptStatus


class PromptBase(BaseModel):
    """Base prompt schema"""
    name: str = Field(..., min_length=1, max_length=200, description="Prompt name")
    description: Optional[str] = Field(None, description="Prompt description")
    prompt_type: PromptType = Field(..., description="Prompt type")
    content: str = Field(..., description="Prompt content")
    is_active: bool = Field(default=True, description="Is active")
    is_default: bool = Field(default=False, description="Is default")
    settings: Optional[dict] = Field(None, description="Additional configuration settings")


class PromptCreate(PromptBase):
    """Prompt creation schema"""
    pass


class PromptUpdate(BaseModel):
    """Prompt update schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Prompt name")
    description: Optional[str] = Field(None, description="Prompt description")
    prompt_type: Optional[PromptType] = Field(None, description="Prompt type")
    content: Optional[str] = Field(None, description="Prompt content")
    is_active: Optional[bool] = Field(None, description="Is active")
    is_default: Optional[bool] = Field(None, description="Is default")
    settings: Optional[dict] = Field(None, description="Additional configuration settings")


class PromptResponse(PromptBase):
    """Prompt response schema"""
    id: int = Field(..., description="Prompt ID")
    user_id: int = Field(..., description="User ID")
    version: int = Field(..., description="Version")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Update time")

    class Config:
        from_attributes = True


class PromptListResponse(BaseModel):
    """Prompt list response schema"""
    prompts: List[PromptResponse]
    total: int
    page: int
    per_page: int


class PromptSearchFilters(BaseModel):
    """Prompt search filters schema"""
    prompt_type: Optional[PromptType] = Field(None, description="Filter by prompt type")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    is_public: Optional[bool] = Field(None, description="Filter by public status")
    is_featured: Optional[bool] = Field(None, description="Filter by featured status")
    author_id: Optional[int] = Field(None, description="Filter by author")
    supported_language: Optional[str] = Field(None, description="Filter by supported language")
    supported_file_type: Optional[str] = Field(None, description="Filter by supported file type")
    created_after: Optional[str] = Field(None, description="Created after date")
    created_before: Optional[str] = Field(None, description="Created before date")
    search: Optional[str] = Field(None, description="Search term")


class PromptUsageStats(BaseModel):
    """Prompt usage statistics schema"""
    prompt_id: int
    total_usage: int
    successful_usage: int
    failed_usage: int
    success_rate: float
    average_response_time: float
    last_used: Optional[datetime]


class PromptTypeStats(BaseModel):
    """Prompt type statistics schema"""
    prompt_type: PromptType
    total_prompts: int
    active_prompts: int
    total_usage: int
    average_success_rate: float


class PromptVersion(BaseModel):
    """Prompt version schema"""
    id: int
    name: str
    version: str
    created_at: datetime
    is_current: bool


class PromptTestRequest(BaseModel):
    """Prompt test request schema"""
    code_content: str = Field(..., description="Code content to test")
    language: str = Field(..., description="Programming language")
    file_name: Optional[str] = Field(None, description="File name")
    override_settings: Optional[dict] = Field(None, description="Override prompt settings")


class PromptTestResponse(BaseModel):
    """Prompt test response schema"""
    success: bool
    response: str
    tokens_used: Optional[int]
    processing_time: Optional[float]
    cost_estimate: Optional[float]
    error_message: Optional[str]


class PromptCloneRequest(BaseModel):
    """Prompt clone request schema"""
    new_name: str = Field(..., description="New prompt name")
    new_description: Optional[str] = Field(None, description="New description")


class PromptExportRequest(BaseModel):
    """Prompt export request schema"""
    format: str = Field(default="json", description="Export format")
    include_metadata: bool = Field(default=True, description="Include metadata")
    include_usage_stats: bool = Field(default=False, description="Include usage stats")


class PromptImportRequest(BaseModel):
    """Prompt import request schema"""
    file_content: str = Field(..., description="File content")
    format: str = Field(default="json", description="Import format")


class PromptValidationResult(BaseModel):
    """Prompt validation result schema"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]


class PromptConfigsUpdate(BaseModel):
    """Schema for updating multiple prompt configurations at once"""
    general: Optional[dict] = None
    architectural: Optional[dict] = None
    business: Optional[dict] = None