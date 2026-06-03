"""
Shared storage provider base class.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class StoredFileInfo:
    """Result metadata returned by storage uploads."""

    locator: str
    pathname: str


class StorageProvider(ABC):
    """Abstract storage provider shared by the concrete backends."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError

    def _safe_name(self, name: str) -> str:
        return re.sub(r"[^A-Za-z0-9._\-/]", "_", name).strip("/") or "file.bin"

    def _build_pathname(
        self,
        user_id: int,
        file_id: str,
        original_name: str,
        relative_path: Optional[str],
    ) -> str:
        candidate = relative_path or original_name
        safe_candidate = self._safe_name(candidate)
        safe_original = self._safe_name(original_name)
        return f"uploads/user_{user_id}/{file_id}/{safe_candidate or safe_original}"

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def path_exists(self, locator: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def read_bytes(self, locator: str) -> bytes:
        raise NotImplementedError

    async def read_text(self, locator: str, encoding: str = "utf-8") -> str:
        content = await self.read_bytes(locator)
        return content.decode(encoding, errors="replace")

    @abstractmethod
    async def delete(self, locator: str) -> None:
        raise NotImplementedError
