"""
Filesystem storage provider.
"""

from pathlib import Path
from typing import Optional

from app.core.config import settings

from .base import StorageProvider, StoredFileInfo


class FileSystemStorageProvider(StorageProvider):
    provider_name = "local"

    def __init__(self) -> None:
        self.upload_dir = Path(settings.UPLOAD_DIR)

    def _ensure_upload_dir(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        test_file = self.upload_dir / ".writetest"
        with open(test_file, "w", encoding="utf-8") as handle:
            handle.write("ok")
        test_file.unlink(missing_ok=True)

    def _path_exists_local(self, locator: str) -> bool:
        return Path(locator).exists()

    def _upload_local_bytes(
        self,
        *,
        pathname: str,
        content: bytes,
    ) -> str:
        target_path = self.upload_dir / pathname
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "wb") as handle:
            handle.write(content)
        return str(target_path)

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
        self._ensure_upload_dir()
        locator = self._upload_local_bytes(pathname=pathname, content=content)
        return StoredFileInfo(locator=locator, pathname=pathname)

    def path_exists(self, locator: str) -> bool:
        if not locator:
            return False
        return self._path_exists_local(locator)

    async def read_bytes(self, locator: str) -> bytes:
        with open(locator, "rb") as handle:
            return handle.read()

    async def delete(self, locator: str) -> None:
        path = Path(locator)
        if path.exists():
            path.unlink()
