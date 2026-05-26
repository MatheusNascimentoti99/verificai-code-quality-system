"""
Storage provider factory and compatibility facade.
"""

from typing import Optional

from app.core.config import settings
from app.core.logging import app_logger as logger
from app.providers import (
    FileSystemStorageProvider,
    MinioStorageProvider,
    StorageProvider,
    StoredFileInfo,
    VercelBlobStorageProvider,
)


def _resolve_provider_name(configured_provider: str) -> str:
    normalized = (configured_provider or "").strip().lower().replace("-", "_")
    aliases = {
        "filesystem": "local",
        "file_system": "local",
        "fs": "local",
        "vercelblob": "vercel_blob",
        "minio_storage": "minio",
    }
    normalized = aliases.get(normalized, normalized)

    if normalized == "auto":
        if settings.MINIO_ENDPOINT and settings.MINIO_BUCKET and settings.MINIO_ACCESS_KEY and settings.MINIO_SECRET_KEY:
            return "minio"
        if settings.BLOB_READ_WRITE_TOKEN:
            return "vercel_blob"
        return "local"

    if normalized not in {"local", "vercel_blob", "minio"}:
        logger.warning("Unknown STORAGE_PROVIDER '%s', falling back to local", configured_provider)
        return "local"

    return normalized


def _build_storage_provider() -> StorageProvider:
    provider_name = _resolve_provider_name(settings.STORAGE_PROVIDER)
    if provider_name == "vercel_blob":
        return VercelBlobStorageProvider()
    if provider_name == "minio":
        return MinioStorageProvider()
    return FileSystemStorageProvider()


_storage_provider: Optional[StorageProvider] = None


def get_storage_provider() -> StorageProvider:
    global _storage_provider
    if _storage_provider is None:
        _storage_provider = _build_storage_provider()
    return _storage_provider


__all__ = [
    "StoredFileInfo",
    "StorageProvider",
    "FileSystemStorageProvider",
    "VercelBlobStorageProvider",
    "MinioStorageProvider",
    "get_storage_provider",
]
