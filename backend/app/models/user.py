"""
User model for VerificAI Backend
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from sqlalchemy import Column, String, Boolean, DateTime, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.security import get_password_hash
from app.models.base import Base, BaseModel, AuditMixin


class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "ADMIN"
    QA_ENGINEER = "QA_ENGINEER"
    DEVELOPER = "DEVELOPER"
    VIEWER = "VIEWER"


class User(Base, BaseModel, AuditMixin):
    """User model"""

    __tablename__ = "users"

    # Basic information
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=True)

    # Authentication
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Role and permissions
    role = Column(SQLEnum(UserRole), default=UserRole.QA_ENGINEER, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)

    # Profile information
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # Preferences
    preferred_language = Column(String(10), default="en", nullable=True)
    timezone = Column(String(50), default="UTC", nullable=True)

    # Security
    last_login = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, nullable=True)
    failed_login_attempts = Column(String(10), default="0", nullable=False)
    locked_until = Column(DateTime, nullable=True)

    # API access
    api_key_hash = Column(String(255), nullable=True)
    api_key_created_at = Column(DateTime, nullable=True)

    # Email preferences
    email_notifications = Column(Boolean, default=True, nullable=False)
    email_analysis_reports = Column(Boolean, default=True, nullable=False)
    email_security_alerts = Column(Boolean, default=True, nullable=False)

    # Relationships
    prompts = relationship("Prompt", back_populates="author", cascade="all, delete-orphan")
    analyses = relationship("Analysis", back_populates="user", cascade="all, delete-orphan")
    prompt_configurations = relationship("PromptConfiguration", back_populates="user", cascade="all, delete-orphan")
    general_criteria = relationship("GeneralCriteria", back_populates="user", cascade="all, delete-orphan")
    general_analysis_results = relationship("GeneralAnalysisResult", back_populates="user", cascade="all, delete-orphan")
    code_entries = relationship("CodeEntry", back_populates="user", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        """Initialize user with password hashing"""
        password = kwargs.pop('password', None)
        if password:
            kwargs['hashed_password'] = get_password_hash(password)
        super().__init__(**kwargs)

    def set_password(self, password: str) -> None:
        """Set user password"""
        self.hashed_password = get_password_hash(password)
        self.password_changed_at = datetime.utcnow()

    def verify_password(self, password: str) -> bool:
        """Verify user password"""
        from app.core.security import verify_password
        return verify_password(password, self.hashed_password)

    def is_locked(self) -> bool:
        """Check if user account is locked"""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until

    def lock_account(self, minutes: int = 30) -> None:
        """Lock user account for specified minutes"""
        self.locked_until = datetime.utcnow() + timedelta(minutes=minutes)

    def unlock_account(self) -> None:
        """Unlock user account"""
        self.locked_until = None
        self.failed_login_attempts = "0"

    def increment_failed_attempts(self) -> None:
        """Increment failed login attempts"""
        current_attempts = int(self.failed_login_attempts or "0")
        self.failed_login_attempts = str(current_attempts + 1)

        # Lock account after 5 failed attempts
        if current_attempts >= 4:
            self.lock_account()

    def reset_failed_attempts(self) -> None:
        """Reset failed login attempts"""
        self.failed_login_attempts = "0"

    def update_last_login(self) -> None:
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()

    def has_role(self, role: UserRole) -> bool:
        """Check if user has specific role"""
        return self.role == role

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        if self.is_admin:
            return True

        role_permissions = {
            UserRole.ADMIN: ["*"],
            UserRole.QA_ENGINEER: [
                "create_analysis", "view_analysis", "edit_prompt",
                "create_prompt", "view_reports"
            ],
            UserRole.DEVELOPER: [
                "create_analysis", "view_analysis", "view_prompt"
            ],
            UserRole.VIEWER: ["view_analysis", "view_prompt", "view_reports"]
        }

        permissions = role_permissions.get(self.role, [])
        return "*" in permissions or permission in permissions

    def to_dict(self, exclude_sensitive: bool = True) -> dict:
        """Convert user to dictionary"""
        data = super().to_dict()

        if exclude_sensitive:
            sensitive_fields = [
                'hashed_password', 'api_key_hash', 'failed_login_attempts',
                'locked_until', 'password_changed_at'
            ]
            for field in sensitive_fields:
                data.pop(field, None)

        return data

    def __repr__(self) -> str:
        """String representation of user"""
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}', role='{self.role}')>"