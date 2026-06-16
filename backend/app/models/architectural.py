"""
SQLAlchemy models for Architectural Analysis feature.
Follows the same patterns as GeneralCriteria and GeneralAnalysisResult in models/prompt.py.
"""

import json
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, JSON, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModel, AuditMixin


class ArchitecturalDoc(Base, BaseModel, AuditMixin):
    """
    Stores architectural documentation submitted by the user.
    Content can be pasted text or extracted from an uploaded file (.txt, .md, .html).
    The sharepoint_url is stored as metadata only — no automatic fetching.
    """
    __tablename__ = "architectural_docs"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    sharepoint_url = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    file_name = Column(String(200), nullable=True)   # original filename if uploaded
    content_type = Column(String(50), nullable=True)  # "text", "markdown", "html"

    # Relationships
    user = relationship("User", back_populates="architectural_docs")
    analysis_results = relationship(
        "ArchitecturalAnalysisResult",
        back_populates="doc",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ArchitecturalDoc(id={self.id}, title='{self.title}', user_id={self.user_id})>"


class ArchitecturalCriteria(Base, BaseModel, AuditMixin):
    """
    Stores user-specific criteria for architectural analysis.
    Mirrors GeneralCriteria but scoped to architectural evaluation.
    """
    __tablename__ = "architectural_criteria"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    order = Column(Integer, default=0, nullable=False)

    # Relationships
    user = relationship("User", back_populates="architectural_criteria")

    __table_args__ = (
        UniqueConstraint("user_id", "text", name="uq_arch_user_criteria_text"),
    )

    def __repr__(self) -> str:
        return (
            f"<ArchitecturalCriteria(user_id={self.user_id}, "
            f"text='{self.text[:50]}...', active={self.is_active})>"
        )


class ArchitecturalAnalysisResult(Base, BaseModel, AuditMixin):
    """
    Stores results from an architectural analysis execution.
    Mirrors GeneralAnalysisResult with additions for doc reference and overall_status.
    """
    __tablename__ = "architectural_analysis_results"

    # Metadata
    analysis_name = Column(String(200), nullable=False)
    overall_status = Column(String(50), nullable=True)   # ADERENTE | PARCIALMENTE_ADERENTE | NAO_ADERENTE
    criteria_count = Column(Integer, nullable=False)

    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doc_id = Column(Integer, ForeignKey("architectural_docs.id"), nullable=True)

    # Results (JSON)
    criteria_results = Column(JSON, nullable=False)      # per-criterion analysis
    raw_response = Column(Text, nullable=False)          # full LLM response

    # Model info
    model_used = Column(String(100), nullable=True)
    usage = Column(JSON, nullable=True)                  # token usage stats

    # Input data for reference
    file_paths = Column(Text, nullable=True)             # JSON array of analyzed files
    modified_prompt = Column(Text, nullable=True)        # prompt sent to LLM
    processing_time = Column(String(50), nullable=True)

    # Relationships
    user = relationship("User", back_populates="architectural_analysis_results")
    doc = relationship("ArchitecturalDoc", back_populates="analysis_results")

    # ------------------------------------------------------------------
    # Helper methods (mirrors GeneralAnalysisResult)
    # ------------------------------------------------------------------

    def get_file_paths(self) -> list:
        if not self.file_paths:
            return []
        return json.loads(self.file_paths)

    def set_file_paths(self, paths: list) -> None:
        self.file_paths = json.dumps(paths)

    def get_criteria_results(self) -> dict:
        if not self.criteria_results:
            return {}
        return self.criteria_results

    def set_criteria_results(self, results: dict) -> None:
        self.criteria_results = results

    def get_usage(self) -> dict:
        if not self.usage:
            return {}
        return self.usage

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["file_paths"] = self.get_file_paths()
        data["criteria_results"] = self.get_criteria_results()
        data["usage"] = self.get_usage()
        return data

    def __repr__(self) -> str:
        return (
            f"<ArchitecturalAnalysisResult(id={self.id}, "
            f"name='{self.analysis_name}', status='{self.overall_status}')>"
        )
