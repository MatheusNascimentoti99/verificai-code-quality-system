"""
Database configuration for VerificAI Backend - Demo Mode (Supabase compatible)
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from urllib.parse import urlparse, urlunparse, quote
from typing import Generator
import logging

from app.core.config import settings
from app.models.base import Base

# Import all models to ensure they are registered with SQLAlchemy
from app.models.user import User
from app.models.prompt import Prompt, PromptConfiguration, GeneralCriteria, GeneralAnalysisResult
from app.models.analysis import Analysis, AnalysisResult
from app.models.uploaded_file import UploadedFile
from app.models.file_path import FilePath
from app.models.code_entry import CodeEntry
from app.models.architectural import ArchitecturalDoc, ArchitecturalCriteria, ArchitecturalAnalysisResult  # noqa: F401

logger = logging.getLogger(__name__)


def _fix_database_url(url: str) -> str:
    """
    Fix DATABASE_URL for Supabase/Render compatibility:
    1. Replaces postgres:// with postgresql://
    2. URL-encodes special characters in the password (e.g. @ becomes %40)
    """
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    # Parse and re-encode the URL to safely handle special chars in password
    try:
        parsed = urlparse(url)
        if parsed.password and "@" in parsed.password:
            safe_password = quote(parsed.password, safe="")
            netloc = f"{parsed.username}:{safe_password}@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            url = urlunparse(parsed._replace(netloc=netloc))
    except Exception:
        pass  # If parsing fails, use URL as-is

    return url


database_url = _fix_database_url(settings.DATABASE_URL)

# Build connect_args for cloud Hosting (PostgreSQL usually requires SSL)
_connect_args = {}
_is_postgres = database_url.startswith("postgresql")
if _is_postgres:
    # For local Docker development (localhost, postgres), disable SSL
    # For cloud hosting (Supabase, Render), require SSL
    if "localhost" in database_url or "postgres" in database_url.split("@")[1].split(":")[0]:
        _connect_args["sslmode"] = "disable"
    else:
        _connect_args["sslmode"] = "require"

# SQLAlchemy engine - small pool for free-tier cloud hosting
engine = create_engine(
    database_url,
    poolclass=QueuePool,
    pool_size=3,
    max_overflow=2,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=settings.DEBUG,
    connect_args=_connect_args,
)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
Base.metadata.naming_convention = convention


def get_db() -> Generator[Session, None, None]:
    """Database dependency for FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_tables():
    """Create database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        update_schema() # Attempt to update schema with new columns
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        # We don't re-raise to allow the app to start and respond to health checks
        # though most endpoints will fail until DB is fixed.


def update_schema():
    """Attempt to add new columns to existing tables (self-healing)"""
    try:
        with engine.connect() as conn:
            is_sqlite = engine.dialect.name == "sqlite"
            
            def column_exists(table_name, column_name):
                if is_sqlite:
                    res = conn.execute(text(f"PRAGMA table_info({table_name})"))
                    columns = [row[1] for row in res.fetchall()]
                    return column_name in columns
                else:
                    res = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table_name}' AND column_name='{column_name}'"))
                    return res.first() is not None

            # Columns to add to 'prompts' table
            prompt_columns = [
                ("name", "VARCHAR(200) DEFAULT 'Novo Prompt'"),
                ("description", "TEXT"),
                ("is_public", "BOOLEAN DEFAULT FALSE"),
                ("is_featured", "BOOLEAN DEFAULT FALSE"),
                ("system_prompt", "TEXT"),
                ("user_prompt_template", "TEXT"),
                ("output_format_instructions", "TEXT"),
                ("temperature", "FLOAT DEFAULT 0.7"),
                ("max_tokens", "INTEGER DEFAULT 2000"),
                ("model_name", "VARCHAR(100) DEFAULT 'gpt-4'"),
                ("tags", "JSON"),
                ("supported_languages", "JSON"),
                ("supported_file_types", "JSON"),
                ("usage_count", "INTEGER DEFAULT 0"),
                ("success_rate", "FLOAT DEFAULT 0.0"),
                ("category", "VARCHAR(50) DEFAULT 'code_analysis'"),
                ("status", "VARCHAR(50) DEFAULT 'active'")
            ]
            
            for col_name, col_type in prompt_columns:
                try:
                    if not column_exists('prompts', col_name):
                        conn.execute(text(f"ALTER TABLE prompts ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                except Exception as col_e:
                    logger.warning(f"Could not add column {col_name}: {col_e}")

            # Special case: rename 'type' to 'prompt_type' if 'prompt_type' doesn't exist
            try:
                if not column_exists('prompts', 'prompt_type'):
                    # If prompt_type doesn't exist, try to rename type
                    if column_exists('prompts', 'type'):
                        conn.execute(text("ALTER TABLE prompts RENAME COLUMN type TO prompt_type"))
                        conn.commit()
                        logger.info("Renamed column 'type' to 'prompt_type' in prompts table")
            except Exception as rename_e:
                logger.warning(f"Could not rename type column: {rename_e}")

            # Columns to add to 'general_analysis_results' table
            try:
                if not column_exists('general_analysis_results', 'project_name'):
                    conn.execute(text("ALTER TABLE general_analysis_results ADD COLUMN project_name VARCHAR(200)"))
                    conn.commit()
            except Exception as e:
                logger.warning(f"Could not add project_name column: {e}")

    except Exception as e:
        logger.error(f"Error updating schema: {e}")


def drop_tables():
    """Drop database tables (use with caution)"""
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Error dropping database tables: {e}")
        raise


class DatabaseManager:
    """Database connection manager"""

    def __init__(self):
        self.engine = engine
        self.session_factory = SessionLocal

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.session_factory()

    def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database manager instance
db_manager = DatabaseManager()
