"""
Storage provider abstraction for local filesystem and Vercel Blob.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

from app.core.config import settings
from app.core.logging import app_logger as logger


@dataclass
class StoredFileInfo:
    """Result metadata returned by storage uploads."""

    locator: str
    pathname: str


class StorageProvider:
    """Storage provider that supports local filesystem and Vercel Blob."""

    def __init__(self) -> None:
        self.provider = settings.STORAGE_PROVIDER.strip().lower()
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.blob_access = settings.BLOB_ACCESS.strip().lower()

        # Vercel Blob credentials can be resolved by SDK from env vars.
        self.blob_token = settings.BLOB_READ_WRITE_TOKEN

        self._blob_client = None

    def _is_blob_enabled(self) -> bool:
        if self.provider == "vercel_blob":
            return True
        else:
            return False

    def _safe_name(self, name: str) -> str:
        # Keep only simple, safe characters for paths.
        return re.sub(r"[^A-Za-z0-9._\-/]", "_", name).strip("/") or "file.bin"

    def _build_pathname(self, user_id: int, file_id: str, original_name: str, relative_path: Optional[str]) -> str:
        candidate = relative_path or original_name
        safe_candidate = self._safe_name(candidate)
        safe_original = self._safe_name(original_name)
        return f"uploads/user_{user_id}/{file_id}/{safe_candidate or safe_original}"

    def _is_url(self, value: str) -> bool:
        return value.startswith("http://") or value.startswith("https://")

    def _extract_pathname_from_url(self, value: str) -> str:
        parsed = urlparse(value)
        return parsed.path.lstrip("/")

    def _blob_headers(self) -> dict:
        if self.blob_token:
            return {"Authorization": f"Bearer {self.blob_token}"}
        return {}

    def _ensure_upload_dir(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        test_file = self.upload_dir / ".writetest"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("ok")
        test_file.unlink(missing_ok=True)

    async def _get_blob_client(self):
        if self._blob_client is not None:
            return self._blob_client

        try:
            from vercel.blob import AsyncBlobClient  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "Vercel Blob SDK not available. Install package 'vercel'."
            ) from exc

        self._blob_client = AsyncBlobClient()
        return self._blob_client

    async def upload_bytes(
        self,
        *,
        user_id: int,
        file_id: str,
        original_name: str,
        relative_path: Optional[str],
        content: bytes,
        content_type: Optional[str],
    ) -> StoredFileInfo:
        pathname = self._build_pathname(user_id, file_id, original_name, relative_path)

        if self._is_blob_enabled():
            client = await self._get_blob_client()
            uploaded = await client.put(
                pathname,
                content,
                access=self.blob_access,
                content_type=content_type,
                add_random_suffix=False,
                overwrite=True,
            )
            locator = str(getattr(uploaded, "url", "") or uploaded.get("url"))
            if not locator:
                raise RuntimeError("Blob upload succeeded but no url was returned")
            return StoredFileInfo(locator=locator, pathname=pathname)

        self._ensure_upload_dir()
        file_path = self.upload_dir / f"{file_id}_{self._safe_name(original_name)}"
        with open(file_path, "wb") as buffer:
            buffer.write(content)

        return StoredFileInfo(locator=str(file_path.absolute()), pathname=pathname)

    async def read_bytes(self, locator: str) -> bytes:
        # Local file path
        if not self._is_url(locator):
            with open(locator, "rb") as f:
                return f.read()

        # Blob URL/path read via SDK (preferred)
        if self._is_blob_enabled():
            client = await self._get_blob_client()

            # First attempt: full URL
            result = await client.get(locator, access=self.blob_access)
            if result and getattr(result, "status_code", 0) == 200 and getattr(result, "stream", None):
                chunks = []
                async for chunk in result.stream:
                    chunks.append(chunk)
                return b"".join(chunks)

            # Second attempt: pathname from URL
            pathname = self._extract_pathname_from_url(locator)
            result = await client.get(pathname, access=self.blob_access)
            if result and getattr(result, "status_code", 0) == 200 and getattr(result, "stream", None):
                chunks = []
                async for chunk in result.stream:
                    chunks.append(chunk)
                return b"".join(chunks)

        # Fallback to HTTP request (works for public blobs and for private with bearer token)
        response = requests.get(locator, headers=self._blob_headers(), timeout=30)
        if response.status_code != 200:
            raise FileNotFoundError(f"Unable to read blob content from {locator}")
        return response.content

    async def read_text(self, locator: str, encoding: str = "utf-8") -> str:
        content = await self.read_bytes(locator)
        return content.decode(encoding, errors="replace")

    async def delete(self, locator: str) -> None:
        if not self._is_url(locator):
            path = Path(locator)
            if path.exists():
                path.unlink()
            return

        if self._is_blob_enabled():
            client = await self._get_blob_client()
            await client.delete(locator)
            return

        # If not blob-enabled, try best effort HTTP no-op to keep behavior safe.
        logger.warning("Skipping blob delete because blob provider is not enabled")


_storage_provider: Optional[StorageProvider] = None


def get_storage_provider() -> StorageProvider:
    global _storage_provider
    if _storage_provider is None:
        _storage_provider = StorageProvider()
    return _storage_provider
