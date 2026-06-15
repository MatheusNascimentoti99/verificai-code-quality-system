"""
Prompt models for VerificAI Backend.
These models store the configuration for the three main prompt types
and their version history.
"""

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    ForeignKey,
    Enum as SQLEnum,
    UniqueConstraint,
    Boolean,
    JSON,
)
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base, BaseModel, AuditMixin


class PromptType(str, enum.Enum):
    """Enumeration for the three types of prompts."""
    GENERAL = "general"
    ARCHITECTURAL = "architectural"
    BUSINESS = "business"


class PromptCategory(str, enum.Enum):
    """Enumeration for prompt categories."""
    CODE_ANALYSIS = "code_analysis"
    ARCHITECTURE = "architecture"
    BUSINESS = "business"
    QUALITY = "quality"
    SECURITY = "security"
    PERFORMANCE = "performance"
    TESTING = "testing"
    DOCUMENTATION = "documentation"


class PromptStatus(str, enum.Enum):
    """Enumeration for prompt status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


class Prompt(Base, BaseModel, AuditMixin):
    """
    Stores the configuration for a prompt.
    """
    __tablename__ = "prompts"

    name = Column(String(200), nullable=False, default="Novo Prompt")
    description = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Compatibility with PromptService using author_id
    @property
    def author_id(self):
        return self.user_id
    
    @author_id.setter
    def author_id(self, value):
        self.user_id = value

    prompt_type = Column(
        SQLEnum(PromptType, name="prompt_type_enum"),
        nullable=False,
        index=True,
    )

    @property
    def type(self):
        return self.prompt_type
    
    @type.setter
    def type(self, value):
        self.prompt_type = value
    
    # Prompt contents
    system_prompt = Column(Text, nullable=True)
    user_prompt_template = Column(Text, nullable=True)
    output_format_instructions = Column(Text, nullable=True)
    content = Column(Text, nullable=False) # Main content for backward compatibility
    
    # Settings
    temperature = Column(Integer, default=0.7) # Float would be better but keeping consistency if needed
    max_tokens = Column(Integer, default=2000)
    model_name = Column(String(100), default="gpt-4")
    
    # Metadata
    version = Column(Integer, default=1, nullable=False)
    is_public = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    status = Column(SQLEnum(PromptStatus, name="prompt_status_enum"), default=PromptStatus.ACTIVE)
    category = Column(SQLEnum(PromptCategory, name="prompt_category_enum"), default=PromptCategory.CODE_ANALYSIS)
    
    # Lists (JSON)
    tags = Column(JSON, nullable=True)
    supported_languages = Column(JSON, nullable=True)
    supported_file_types = Column(JSON, nullable=True)
    
    # Stats
    usage_count = Column(Integer, default=0)
    success_rate = Column(Integer, default=0) # Should be float in reality

    # Relationships
    history = relationship(
        "PromptHistory",
        back_populates="prompt",
        cascade="all, delete-orphan",
        order_by="desc(PromptHistory.version)",
    )
    author = relationship("User", back_populates="prompts")
    analyses = relationship("Analysis", back_populates="prompt")

    def __repr__(self) -> str:
        return f"<Prompt(name='{self.name}', type='{self.type}', version={self.version})>"

    def increment_usage(self):
        self.usage_count += 1

    def update_success_rate(self, success: bool):
        # Very simple implementation
        pass


class PromptHistory(Base, BaseModel):
    """
    Stores a historical version of a prompt.
    """
    __tablename__ = "prompt_history"

    prompt_id = Column(Integer, ForeignKey("prompts.id"), nullable=False)
    version = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)

    # Relationships
    prompt = relationship("Prompt", back_populates="history")

    __table_args__ = (
        UniqueConstraint("prompt_id", "version", name="uq_prompt_version"),
    )

    def __repr__(self) -> str:
        return f"<PromptHistory(prompt_id={self.prompt_id}, version={self.version})>"


class GeneralCriteria(Base, BaseModel, AuditMixin):
    """
    Stores user-specific criteria for general analysis.
    """
    __tablename__ = "general_criteria"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    order = Column(Integer, default=0, nullable=False)

    # Relationships
    user = relationship("User", back_populates="general_criteria")

    __table_args__ = (
        UniqueConstraint("user_id", "text", name="uq_user_criteria_text"),
    )

    def __repr__(self) -> str:
        return f"<GeneralCriteria(user_id={self.user_id}, text='{self.text[:50]}...', active={self.is_active})>"


class GeneralAnalysisResult(Base, BaseModel, AuditMixin):
    """
    Stores results from general analysis of selected criteria.
    """
    __tablename__ = "general_analysis_results"

    # Analysis metadata
    analysis_name = Column(String(200), nullable=False)
    project_name = Column(String(200), nullable=True)
    criteria_count = Column(Integer, nullable=False)

    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Analysis results (JSON format)
    criteria_results = Column(JSON, nullable=False)  # Extracted criteria with analysis
    raw_response = Column(Text, nullable=False)  # Full LLM response

    # Model information
    model_used = Column(String(100), nullable=True)
    usage = Column(JSON, nullable=True)  # Token usage stats

    # Input data for reference
    file_paths = Column(Text, nullable=True)  # JSON array of analyzed files
    modified_prompt = Column(Text, nullable=True)  # The prompt sent to LLM

    # Processing info
    processing_time = Column(String(50), nullable=True)

    # Relationships
    user = relationship("User", back_populates="general_analysis_results")

    def get_file_paths(self) -> list[str]:
        """Get file paths as list"""
        if not self.file_paths:
            return []
        import json
        return json.loads(self.file_paths)

    def set_file_paths(self, paths: list[str]) -> None:
        """Set file paths from list"""
        import json
        self.file_paths = json.dumps(paths)

    def get_criteria_results(self) -> dict:
        """Get criteria results as dictionary"""
        if not self.criteria_results:
            return {}
        return self.criteria_results

    def set_criteria_results(self, results: dict) -> None:
        """Set criteria results from dictionary"""
        self.criteria_results = results

    def get_usage(self) -> dict:
        """Get usage stats as dictionary"""
        if not self.usage:
            return {}
        return self.usage

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        data = super().to_dict()
        data['file_paths'] = self.get_file_paths()
        data['criteria_results'] = self.get_criteria_results()
        data['usage'] = self.get_usage()
        data['project_name'] = self.project_name
        return data

    def __repr__(self) -> str:
        return f"<GeneralAnalysisResult(id={self.id}, name='{self.analysis_name}', criteria_count={self.criteria_count})>"


class PromptConfiguration(Base, BaseModel, AuditMixin):
    """
    Stores user-specific prompt configurations and settings.
    """
    __tablename__ = "prompt_configurations"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    prompt_type = Column(SQLEnum(PromptType, name="prompt_type_enum"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    settings = Column(JSON, nullable=True)  # Additional configuration settings

    # Relationships
    user = relationship("User", back_populates="prompt_configurations")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_prompt_name"),
        UniqueConstraint("user_id", "prompt_type", name="uq_user_prompt_type"),
    )

    def __repr__(self) -> str:
        return f"<PromptConfiguration(user_id={self.user_id}, prompt_type='{self.prompt_type}', name='{self.name}')>"
