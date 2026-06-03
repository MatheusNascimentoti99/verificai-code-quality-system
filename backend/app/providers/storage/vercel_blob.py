"""
Vercel Blob storage provider.
"""

from pathlib import Path
from typing import Optional

import requests

from app.core.config import settings

from .base import StorageProvider, StoredFileInfo


class VercelBlobStorageProvider(StorageProvider):
    provider_name = "vercel_blob"

    def __init__(self) -> None:
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.blob_access = settings.BLOB_ACCESS.strip().lower()
        self.blob_token = settings.BLOB_READ_WRITE_TOKEN
        self._blob_client = None

        if not self.blob_token:
            raise RuntimeError("STORAGE_PROVIDER=vercel_blob requires BLOB_READ_WRITE_TOKEN.")

    def _is_url(self, value: str) -> bool:
        return value.startswith(("http://", "https://"))

    def _extract_pathname_from_url(self, value: str) -> str:
        from urllib.parse import urlparse

        parsed = urlparse(value)
        return parsed.path.lstrip("/")

    def _blob_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.blob_token}"}

    def _path_exists_local(self, locator: str) -> bool:
        return Path(locator).exists()

    def _path_exists_blob(self, locator: str) -> bool:
        response = requests.head(locator, headers=self._blob_headers(), timeout=30, allow_redirects=True)
        return response.status_code < 400

    async def _get_blob_client(self):
        if self._blob_client is not None:
            return self._blob_client

        try:
            from vercel.blob import AsyncBlobClient  # type: ignore
        except Exception as exc:
            raise RuntimeError("Vercel Blob SDK not available. Install package 'vercel'.") from exc

        self._blob_client = AsyncBlobClient()
        return self._blob_client

    async def _upload_blob_bytes(
        self,
        *,
        pathname: str,
        content: bytes,
        content_type: Optional[str],
    ) -> str:
        client = await self._get_blob_client()
        uploaded = await client.put(
            pathname,
            content,
            access=self.blob_access,
            content_type=content_type,
            add_random_suffix=False,
            overwrite=True,
        )
        locator = str(getattr(uploaded, "url", "") or getattr(uploaded, "pathname", ""))
        if not locator:
            raise RuntimeError("Blob upload succeeded but no url was returned")
        return locator

    async def _read_blob_bytes(self, locator: str) -> bytes:
        client = await self._get_blob_client()

        result = await client.get(locator, access=self.blob_access)
        if result and getattr(result, "status_code", 0) == 200 and getattr(result, "stream", None):
            chunks = []
            async for chunk in result.stream:
                chunks.append(chunk)
            return b"".join(chunks)

        pathname = self._extract_pathname_from_url(locator)
        result = await client.get(pathname, access=self.blob_access)
        if result and getattr(result, "status_code", 0) == 200 and getattr(result, "stream", None):
            chunks = []
            async for chunk in result.stream:
                chunks.append(chunk)
            return b"".join(chunks)

        response = requests.get(locator, headers=self._blob_headers(), timeout=30)
        if response.status_code != 200:
            raise FileNotFoundError(f"Unable to read content from {locator}")
        return response.content

    async def _delete_blob_locator(self, locator: str) -> None:
        client = await self._get_blob_client()
        await client.delete(locator)

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
        locator = await self._upload_blob_bytes(pathname=pathname, content=content, content_type=content_type)
        return StoredFileInfo(locator=locator, pathname=pathname)

    def path_exists(self, locator: str) -> bool:
        if not locator:
            return False
        if self._is_url(locator):
            try:
                return self._path_exists_blob(locator)
            except Exception:
                return False
        return self._path_exists_local(locator)

    async def read_bytes(self, locator: str) -> bytes:
        if not self._is_url(locator):
            with open(locator, "rb") as handle:
                return handle.read()
        return await self._read_blob_bytes(locator)

    async def delete(self, locator: str) -> None:
        if not self._is_url(locator):
            path = Path(locator)
            if path.exists():
                path.unlink()
            return
        await self._delete_blob_locator(locator)
