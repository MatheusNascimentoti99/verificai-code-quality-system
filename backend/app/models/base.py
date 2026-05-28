"""
Base model classes for VerificAI Backend
"""

from datetime import datetime
from typing import Any
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.ext.declarative import declared_attr, declarative_base
from sqlalchemy.sql import func

# Create declarative base
Base = declarative_base()

class BaseModel:
    """Base SQLAlchemy model with common functionality"""

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name"""
        return cls.__name__.lower()

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    def update(self, **kwargs: Any) -> None:
        """Update model attributes"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BaseModel":
        """Create model instance from dictionary"""
        return cls(**data)


class TimestampMixin:
    """Mixin for timestamp fields"""

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class SoftDeleteMixin:
    """Mixin for soft delete functionality"""

    deleted_at = Column(DateTime, nullable=True)
    is_deleted = Column(Integer, default=0, nullable=False)  # 0 = not deleted, 1 = deleted

    def soft_delete(self) -> None:
        """Mark record as deleted"""
        self.deleted_at = datetime.utcnow()
        self.is_deleted = 1

    def restore(self) -> None:
        """Restore soft-deleted record"""
        self.deleted_at = None
        self.is_deleted = 0


class AuditMixin:
    """Mixin for audit fields"""

    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)