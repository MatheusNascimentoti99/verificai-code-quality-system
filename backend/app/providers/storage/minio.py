"""
MinIO storage provider.
"""

import io
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from app.core.config import settings

from .base import StorageProvider, StoredFileInfo


class MinioStorageProvider(StorageProvider):
    provider_name = "minio"

    def __init__(self) -> None:
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.minio_endpoint = (settings.MINIO_ENDPOINT or "").strip()
        self.minio_bucket = (settings.MINIO_BUCKET or "").strip()
        self.minio_access_key = settings.MINIO_ACCESS_KEY
        self.minio_secret_key = settings.MINIO_SECRET_KEY
        self.minio_secure = bool(settings.MINIO_SECURE)
        self._minio_client = None

        if not (
            self.minio_endpoint
            and self.minio_bucket
            and self.minio_access_key
            and self.minio_secret_key
        ):
            raise RuntimeError(
                "STORAGE_PROVIDER=minio requires MINIO_ENDPOINT, MINIO_BUCKET, MINIO_ACCESS_KEY and MINIO_SECRET_KEY."
            )

    def _is_minio_locator(self, value: str) -> bool:
        return value.startswith("minio://")

    def _extract_minio_reference(self, value: str) -> tuple:
        parsed = urlparse(value)
        bucket = parsed.netloc or self.minio_bucket
        object_name = parsed.path.lstrip("/")
        if not bucket or not object_name:
            raise FileNotFoundError(f"Invalid MinIO locator: {value}")
        return bucket, object_name

    def _path_exists_local(self, locator: str) -> bool:
        return Path(locator).exists()

    def _get_minio_client_sync(self):
        if self._minio_client is not None:
            return self._minio_client

        try:
            from minio import Minio  # type: ignore
        except Exception as exc:
            raise RuntimeError("MinIO SDK not available. Install package 'minio'.") from exc

        self._minio_client = Minio(
            self.minio_endpoint,
            access_key=self.minio_access_key,
            secret_key=self.minio_secret_key,
            secure=self.minio_secure,
        )

        try:
            if not self._minio_client.bucket_exists(self.minio_bucket):
                self._minio_client.make_bucket(self.minio_bucket)
        except Exception as exc:
            raise RuntimeError(f"Unable to initialize MinIO bucket '{self.minio_bucket}': {exc}") from exc

        return self._minio_client

    async def _get_minio_client(self):
        return self._get_minio_client_sync()

    def _minio_locator(self, pathname: str) -> str:
        return f"minio://{self.minio_bucket}/{pathname}"

    def _upload_minio_bytes(
        self,
        *,
        pathname: str,
        content: bytes,
        content_type: Optional[str],
    ) -> str:
        client = self._get_minio_client_sync()
        client.put_object(
            self.minio_bucket,
            pathname,
            io.BytesIO(content),
            len(content),
            content_type=content_type or "application/octet-stream",
        )
        return self._minio_locator(pathname)

    def _read_minio_bytes_sync(self, locator: str) -> bytes:
        client = self._get_minio_client_sync()
        bucket, object_name = self._extract_minio_reference(locator)
        response = client.get_object(bucket, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    async def _read_minio_bytes(self, locator: str) -> bytes:
        return self._read_minio_bytes_sync(locator)

    def _delete_minio_locator_sync(self, locator: str) -> None:
        client = self._get_minio_client_sync()
        bucket, object_name = self._extract_minio_reference(locator)
        client.remove_object(bucket, object_name)

    async def _delete_minio_locator(self, locator: str) -> None:
        self._delete_minio_locator_sync(locator)

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
        locator = await self._upload_minio_bytes(pathname=pathname, content=content, content_type=content_type)
        return StoredFileInfo(locator=locator, pathname=pathname)

    def path_exists(self, locator: str) -> bool:
        if not locator:
            return False
        if self._is_minio_locator(locator):
            try:
                client = self._get_minio_client_sync()
                bucket, object_name = self._extract_minio_reference(locator)
                client.stat_object(bucket, object_name)
                return True
            except Exception:
                return False
        return self._path_exists_local(locator)

    async def read_bytes(self, locator: str) -> bytes:
        if self._is_minio_locator(locator):
            return await self._read_minio_bytes(locator)
        with open(locator, "rb") as handle:
            return handle.read()

    async def delete(self, locator: str) -> None:
        if self._is_minio_locator(locator):
            await self._delete_minio_locator(locator)
            return
        path = Path(locator)
        if path.exists():
            path.unlink()
