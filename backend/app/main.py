"""
FastAPI application entry point for VerificAI Code Quality System - Demo Mode
"""

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import create_tables, db_manager
from app.core.logging import setup_logging
from app.core.middleware import (
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    ErrorHandlerMiddleware,
    RateLimitMiddleware
)
from app.api.v1 import auth, users, prompts, analysis, upload, file_paths, general_analysis, simple_analysis, code_entries
import uvicorn

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Initialize logging
setup_logging()

# Import all models to ensure they are registered for create_tables()
from app.models.user import User # noqa: F401
from app.models.code_entry import CodeEntry # noqa: F401
from app.models.analysis import Analysis, AnalysisResult # noqa: F401
from app.models.prompt import Prompt, PromptConfiguration, GeneralCriteria, GeneralAnalysisResult # noqa: F401
from app.models.uploaded_file import UploadedFile # noqa: F401
from app.models.file_path import FilePath # noqa: F401

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-powered code quality analysis system for QA teams",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# CORS - allows specific origins in production, all in development
# Note: allow_credentials=True is incompatible with allow_origins=["*"] in modern browsers
if settings.ENVIRONMENT == "production":
    cors_origins = [
        "https://verificai-code-quality-system-front.vercel.app",
        "https://verificai.vercel.app",
    ] + settings.BACKEND_CORS_ORIGINS
else:
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware stack
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.RATE_LIMIT_REQUESTS_PER_MINUTE)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Include API routers
app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["authentication"])
app.include_router(users.router, prefix=settings.API_V1_STR, tags=["users"])
app.include_router(file_paths.router, prefix=settings.API_V1_STR + "/file-paths", tags=["file_paths"])
app.include_router(code_entries.router, prefix=settings.API_V1_STR, tags=["code_entries"])
app.include_router(prompts.router, prefix=settings.API_V1_STR + "/prompts", tags=["prompts"])
app.include_router(analysis.router, prefix=settings.API_V1_STR, tags=["analysis"])
app.include_router(upload.router, prefix=settings.API_V1_STR, tags=["upload"])
app.include_router(general_analysis.router, prefix=settings.API_V1_STR + "/general-analysis", tags=["general_analysis"])
app.include_router(simple_analysis.router, prefix=settings.API_V1_STR + "/simple-analysis", tags=["simple_analysis"])


@app.on_event("startup")
async def startup_event():
    """Application startup - create tables and cleanup orphan records"""
    from app.core.database import get_db
    from app.core.cleanup_tasks import cleanup_invalid_paths
    from seed_criteria import seed_criteria
    from create_admin import create_admin
    from create_general_prompt import create_general_analysis_prompt
    
    # 1. Create tables if they don't exist
    create_tables()
    
    # 2. Seed initial data after the app is live
    create_admin()
    seed_criteria()
    create_general_analysis_prompt()

    # 3. Run Self-Healing Cleanup (Remove orphan paths from Render ephemeral disk restarts)
    db = next(get_db())
    cleanup_invalid_paths(db)


@app.get("/")
async def root():
    """Root endpoint with health checks"""
    db_ok = db_manager.health_check()
    return {
        "message": "VerificAI Code Quality System API",
        "version": settings.VERSION,
        "docs_url": f"{settings.API_V1_STR}/docs",
        "status": "operational",
        "database": "connected" if db_ok else "disconnected"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Render uptime monitoring"""
    db_health = db_manager.health_check()
    return {
        "status": "healthy" if db_health else "unhealthy",
        "service": "verificai-backend",
        "version": "1.0.1",
        "database": "connected" if db_health else "disconnected"
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    db_health = db_manager.health_check()
    return {
        "status": "ready" if db_health else "not_ready",
        "service": "verificai-backend",
        "database": "connected" if db_health else "disconnected"
    }


@app.get("/setup")
async def setup_first_admin():
    """
    One-time setup: creates the first admin user if no users exist.
    Access: GET /setup  (no auth required)
    Safe: returns error if any user already exists.
    """
    from app.core.database import get_db
    # Import ALL models to ensure SQLAlchemy mapper registry is complete
    from app.models.user import User, UserRole
    from app.models.code_entry import CodeEntry  # noqa: F401
    from app.models.analysis import Analysis, AnalysisResult  # noqa: F401
    from app.models.prompt import Prompt, PromptConfiguration  # noqa: F401
    from app.models.uploaded_file import UploadedFile  # noqa: F401
    from app.models.file_path import FilePath  # noqa: F401

    try:
        db = next(get_db())
        user_count = db.query(User).count()

        if user_count > 0:
            return {
                "success": False,
                "message": f"Setup already done. {user_count} user(s) exist.",
                "hint": "Use /api/v1/login with your credentials."
            }

        # Create first admin user
        admin = User(
            username="admin",
            email="admin@verificai.com",
            password="Admin@2024",
            full_name="Administrador VerificAI",
            role=UserRole.ADMIN,
            is_admin=True,
            is_active=True,
            is_verified=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        return {
            "success": True,
            "message": "Admin user created successfully!",
            "credentials": {
                "username": "admin",
                "password": "Admin@2024",
                "email": "admin@verificai.com"
            },
            "next_step": "Login at your Vercel frontend or POST /api/v1/login"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/public/version")
def get_version():
    """Get API version for deployment verification"""
    return {
        "version": "1.0.1",
        "status": "stable",
        "last_updated": "2026-04-07T03:23:00Z",
        "features": ["bulk_delete_fix", "llm_timeout_fix", "json_parsing_enhanced", "public_version_endpoint"]
    }


@app.get("/api/v1/file-paths/public")
async def get_public_file_paths():
    """Get file paths for public access"""
    from app.core.database import get_db
    from app.models.file_path import FilePath
    from sqlalchemy import desc

    try:
        db = next(get_db())
        file_paths = db.query(FilePath).order_by(desc(FilePath.created_at)).all()
        paths_labeled = [
            {"full_path": fp.full_path, "file_id": fp.file_id} 
            for fp in file_paths if fp.full_path
        ]
        return {
            "file_paths": paths_labeled,
            "total_count": len(paths_labeled),
            "message": f"Found {len(paths_labeled)} file paths - ALL FILES"
        }
    except Exception as e:
        return {"file_paths": [], "total_count": 0, "message": "Error occurred"}


# Global OPTIONS handler removed as it conflicts with CORSMiddleware


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
