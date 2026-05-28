"""
Custom exceptions for VerificAI Backend
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from pydantic import BaseModel


class BaseAPIException(HTTPException):
    """Base exception for API errors"""

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        detail: Optional[Any] = None,
        headers: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.message = message
        super().__init__(
            status_code=status_code,
            detail={
                "error_code": error_code,
                "message": message,
                "detail": detail
            },
            headers=headers
        )


class ErrorResponse(BaseModel):
    """Standard error response model"""

    error_code: str
    message: str
    detail: Optional[Any] = None


# Authentication and Authorization Exceptions
class AuthenticationError(BaseAPIException):
    """Authentication failed"""

    def __init__(
        self,
        message: str = "Authentication failed",
        detail: Optional[Any] = None
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_ERROR",
            message=message,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationError(BaseAPIException):
    """Authorization failed"""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        detail: Optional[Any] = None
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHZ_ERROR",
            message=message,
            detail=detail
        )


class InvalidTokenError(BaseAPIException):
    """Invalid or expired token"""

    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="INVALID_TOKEN",
            message=message,
            headers={"WWW-Authenticate": "Bearer"}
        )


class TokenExpiredError(BaseAPIException):
    """Token has expired"""

    def __init__(self, message: str = "Token has expired"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="TOKEN_EXPIRED",
            message=message,
            headers={"WWW-Authenticate": "Bearer"}
        )


# Validation Exceptions
class ValidationError(BaseAPIException):
    """Validation error"""

    def __init__(
        self,
        message: str = "Validation failed",
        detail: Optional[Any] = None
    ):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            message=message,
            detail=detail
        )


class DuplicateResourceError(BaseAPIException):
    """Resource already exists"""

    def __init__(
        self,
        resource_type: str,
        identifier: str
    ):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="DUPLICATE_RESOURCE",
            message=f"{resource_type} with identifier '{identifier}' already exists"
        )


# Resource Not Found Exceptions
class NotFoundError(BaseAPIException):
    """Resource not found"""

    def __init__(self, resource_type: str, identifier: Any):
        import traceback
        import sys
        print(f"DEBUG: NotFoundError initialized for {resource_type} with ID {identifier}", file=sys.stderr)
        traceback.print_stack(file=sys.stderr)
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            message=f"{resource_type} with identifier '{identifier}' not found"
        )


class UserNotFoundError(NotFoundError):
    """User not found"""

    def __init__(self, user_id: str):
        super().__init__("User", user_id)


class PromptNotFoundError(NotFoundError):
    """Prompt not found"""

    def __init__(self, prompt_id: str):
        super().__init__("Prompt", prompt_id)


class AnalysisNotFoundError(NotFoundError):
    """Analysis not found"""

    def __init__(self, analysis_id: str):
        super().__init__("Analysis", analysis_id)


# Business Logic Exceptions
class BusinessRuleError(BaseAPIException):
    """Business rule violation"""

    def __init__(
        self,
        message: str = "Business rule violated",
        detail: Optional[Any] = None
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="BUSINESS_RULE_ERROR",
            message=message,
            detail=detail
        )


class InvalidStateError(BaseAPIException):
    """Invalid state transition"""

    def __init__(
        self,
        resource_type: str,
        current_state: str,
        desired_state: str
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_STATE",
            message=f"Cannot transition {resource_type} from {current_state} to {desired_state}"
        )


# Rate Limiting Exceptions
class RateLimitExceededError(BaseAPIException):
    """Rate limit exceeded"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None
    ):
        headers = None
        if retry_after:
            headers = {"Retry-After": str(retry_after)}

        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            message=message,
            headers=headers
        )


# External Service Exceptions
class ExternalServiceError(BaseAPIException):
    """External service unavailable"""

    def __init__(
        self,
        service_name: str,
        message: Optional[str] = None
    ):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="EXTERNAL_SERVICE_ERROR",
            message=message or f"External service '{service_name}' unavailable"
        )


class DatabaseError(BaseAPIException):
    """Database operation failed"""

    def __init__(
        self,
        message: str = "Database operation failed",
        detail: Optional[Any] = None
    ):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
            message=message,
            detail=detail
        )


class FileProcessingError(BaseAPIException):
    """File processing failed"""

    def __init__(
        self,
        message: str = "File processing failed",
        detail: Optional[Any] = None
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="FILE_PROCESSING_ERROR",
            message=message,
            detail=detail
        )


class ConfigurationError(BaseAPIException):
    """Configuration error"""

    def __init__(
        self,
        message: str = "Configuration error",
        detail: Optional[Any] = None
    ):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="CONFIGURATION_ERROR",
            message=message,
            detail=detail
        )