"""
Configuration management for VerificAI Backend - Demo Mode
"""

import os
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Default password for demo purposes only. Change in production!
    ADMIN_PASSWORD: str = Field(default="Admin@2024", env="ADMIN_PASSWORD")  
    
    # Project Information
    PROJECT_NAME: str = "VerificAI Code Quality System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Server Configuration
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    DEBUG: bool = Field(default=False, env="DEBUG")

    # Database Configuration - supports Supabase postgres:// URLs
    DATABASE_URL: str = Field(
        default="sqlite:///./verificai.db",
        env="DATABASE_URL"
    )

    @field_validator('DATABASE_URL', mode='before')
    @classmethod
    def fix_database_url(cls, v):
        """Fix Supabase/Render postgres:// format to postgresql://"""
        if not v:
            return "sqlite:///./verificai.db"
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    # Security Configuration
    SECRET_KEY: str = Field(
        default="change-this-secret-key-in-production-min-32-chars",
        env="SECRET_KEY"
    )
    JWT_SECRET_KEY: str = Field(
        default="change-this-jwt-key-in-production-min-32-chars",
        env="JWT_SECRET_KEY"
    )
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440, env="ACCESS_TOKEN_EXPIRE_MINUTES")  # 24h

    # CORS Configuration - accepts frontend URLs from Vercel/localhost
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3011",
            "http://localhost:5173",
        ],
        env="BACKEND_CORS_ORIGINS"
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        """Parse CORS origins from environment variable"""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # LLM API Configuration
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    GEMINI_API_KEY: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    OPENROUTER_API_KEY: Optional[str] = Field(default=None, env="OPENROUTER_API_KEY")

    # LLM Configuration
    MAX_TOKENS: int = Field(default=8000, env="MAX_TOKENS")
    TEMPERATURE: float = Field(default=0.1, env="TEMPERATURE")
    MODEL: str = Field(default="openai/gpt-4o-mini", env="MODEL")
    OPENROUTER_MODEL: str = Field(default="openai/gpt-4o-mini", env="OPENROUTER_MODEL")

    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=30, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    RATE_LIMIT_BURST: int = Field(default=10, env="RATE_LIMIT_BURST")

    # File Upload Configuration
    MAX_FILE_SIZE: int = Field(default=10485760, env="MAX_FILE_SIZE")  # 10MB (reduzido para demo)
    STORAGE_PROVIDER: str = Field(default="local", env="STORAGE_PROVIDER")  # local | vercel_blob | minio
    UPLOAD_DIR: str = Field(default="uploads", env="UPLOAD_DIR")
    BLOB_ACCESS: str = Field(default="private", env="BLOB_ACCESS")  # private | public
    BLOB_READ_WRITE_TOKEN: Optional[str] = Field(default=None, env="BLOB_READ_WRITE_TOKEN")
    MINIO_ENDPOINT: Optional[str] = Field(default=None, env="MINIO_ENDPOINT")
    MINIO_BUCKET: str = Field(default="verificai", env="MINIO_BUCKET")
    MINIO_ACCESS_KEY: Optional[str] = Field(default=None, env="MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: Optional[str] = Field(default=None, env="MINIO_SECRET_KEY")
    MINIO_SECURE: bool = Field(default=False, env="MINIO_SECURE")
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=[".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".h", ".cs", ".php", ".rb", ".go", ".rs"],
        env="ALLOWED_EXTENSIONS"
    )

    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")

    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")

    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


# Global settings instance
settings = Settings()