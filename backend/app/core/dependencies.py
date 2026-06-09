"""
Dependency injection utilities for VerificAI Backend - Demo Mode (no Redis)
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.core.exceptions import InvalidTokenError, AuthenticationError
from app.models.user import User
from app.services.general_analysis import GeneralAnalysisService
from app.services.llm_service import llm_service
from app.services.prompt import PromptService, get_prompt_service as build_prompt_service
from app.providers.storage import StorageProvider, get_storage_provider as build_storage_provider
from app.services.file_processor import FileProcessorService
from app.services.llm_orchestrator import LLMOrchestrator

# Security schemes
security = HTTPBearer()


async def get_current_user(
    db: Session = Depends(get_db),
    token: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current authenticated user"""
    try:
        # Verify token
        username = verify_token(token.credentials)
        if username is None:
            raise InvalidTokenError()

        # Get user from database
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise AuthenticationError("User not found")

        if not user.is_active:
            raise AuthenticationError("User account is inactive")

        return user

    except Exception as e:
        if isinstance(e, (InvalidTokenError, AuthenticationError)):
            raise e
        raise AuthenticationError(f"Authentication failed: {str(e)}")


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_optional_user(
    db: Session = Depends(get_db),
    token: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """Get optional current user (for endpoints that work with or without auth)"""
    if token is None:
        return None

    try:
        return await get_current_user(db, token)
    except Exception:
        return None


class CommonQueryParams:
    """Common query parameters for pagination and filtering"""

    def __init__(
        self,
        skip: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = "desc",
        search: Optional[str] = None
    ):
        self.skip = skip
        self.limit = min(limit, 1000)  # Max 1000 items per page
        self.sort_by = sort_by
        self.sort_order = sort_order.lower() if sort_order else "desc"
        self.search = search

        # Validate sort order
        if self.sort_order not in ["asc", "desc"]:
            self.sort_order = "desc"


def get_pagination_params(
    skip: int = 0,
    limit: int = 100
) -> tuple[int, int]:
    """Get pagination parameters"""
    skip = max(0, skip)
    limit = min(max(1, limit), 1000)  # Between 1 and 1000
    return skip, limit


def verify_admin_permission(current_user: User = Depends(get_current_user)) -> User:
    """Verify user has admin permissions"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permissions required"
        )
    return current_user


def verify_api_key_permission(
    api_key: Optional[str] = None,
    current_user: Optional[User] = Depends(get_optional_user)
) -> tuple[bool, Optional[User]]:
    """Verify API key or user authentication"""
    if current_user:
        return True, current_user
    return False, None


class RateLimitDependency:
    """Rate limiting dependency (in-memory, no Redis)"""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute

    async def __call__(self, request):
        # Simple pass-through - rate limiting handled by middleware
        pass


# Common dependencies
common_query_params = CommonQueryParams
rate_limit = RateLimitDependency


def get_prompt_service(db: Session = Depends(get_db)) -> PromptService:
    """Provide a prompt service instance."""
    return build_prompt_service(db)


def get_storage_provider() -> StorageProvider:
    """Provide the configured storage provider instance."""
    return build_storage_provider()


def get_llm_service():
    """Provide the shared LLM service instance."""
    return llm_service


def get_file_processor(
    db: Session = Depends(get_db),
    storage_provider: StorageProvider = Depends(get_storage_provider),
) -> FileProcessorService:
    """Provide a FileProcessorService instance."""
    return FileProcessorService(db=db, storage_provider=storage_provider)


def get_llm_orchestrator(storage_provider: StorageProvider = Depends(get_storage_provider), llm_service_instance = Depends(get_llm_service)) -> LLMOrchestrator:
    """Provide an LLMOrchestrator instance."""
    return LLMOrchestrator(llm_service=llm_service_instance, storage_provider=storage_provider)


def get_general_analysis_service(
    db: Session = Depends(get_db),
    prompt_service: PromptService = Depends(get_prompt_service),
    storage_provider: StorageProvider = Depends(get_storage_provider),
    llm_service_instance = Depends(get_llm_service),
    file_processor: FileProcessorService = Depends(get_file_processor),
    llm_orchestrator: LLMOrchestrator = Depends(get_llm_orchestrator),
) -> GeneralAnalysisService:
    """Provide the general analysis service with its dependencies."""
    return GeneralAnalysisService(
        db=db,
        prompt_service=prompt_service,
        storage_provider=storage_provider,
        llm_service=llm_service_instance,
        file_processor=file_processor,
        llm_orchestrator=llm_orchestrator,
    )