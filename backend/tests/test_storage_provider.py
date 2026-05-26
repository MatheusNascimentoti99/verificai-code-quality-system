import pytest

from app.providers.filesystem import FileSystemStorageProvider
from app.providers.minio import MinioStorageProvider


@pytest.fixture(autouse=True)
def reset_storage_settings(monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.storage_provider.settings.STORAGE_PROVIDER", "local")
    monkeypatch.setattr("app.services.storage_provider.settings.UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr("app.services.storage_provider.settings.BLOB_ACCESS", "private")
    monkeypatch.setattr("app.services.storage_provider.settings.BLOB_READ_WRITE_TOKEN", None)
    monkeypatch.setattr("app.services.storage_provider.settings.MINIO_ENDPOINT", None)
    monkeypatch.setattr("app.services.storage_provider.settings.MINIO_BUCKET", "verificai")
    monkeypatch.setattr("app.services.storage_provider.settings.MINIO_ACCESS_KEY", None)
    monkeypatch.setattr("app.services.storage_provider.settings.MINIO_SECRET_KEY", None)
    monkeypatch.setattr("app.services.storage_provider.settings.MINIO_SECURE", False)


@pytest.mark.asyncio
async def test_local_storage_provider_roundtrip(tmp_path):
    provider = FileSystemStorageProvider()

    stored = await provider.upload_bytes(
        user_id=7,
        file_id="file_test",
        original_name="hello.txt",
        relative_path="hello.txt",
        content=b"hello world",
        content_type="text/plain",
    )

    assert stored.pathname == "uploads/user_7/file_test/hello.txt"
    assert provider.path_exists(stored.locator)
    assert await provider.read_text(stored.locator) == "hello world"

    await provider.delete(stored.locator)
    assert not provider.path_exists(stored.locator)


def test_auto_prefers_minio_when_configured(monkeypatch):
    monkeypatch.setattr("app.services.storage_provider.settings.STORAGE_PROVIDER", "auto")
    monkeypatch.setattr("app.services.storage_provider.settings.MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setattr("app.services.storage_provider.settings.MINIO_BUCKET", "verificai")
    monkeypatch.setattr("app.services.storage_provider.settings.MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setattr("app.services.storage_provider.settings.MINIO_SECRET_KEY", "minioadmin")

    provider = MinioStorageProvider()

    assert provider.provider == "minio"


def test_minio_provider_requires_credentials(monkeypatch):
    monkeypatch.setattr("app.services.storage_provider.settings.STORAGE_PROVIDER", "minio")

    with pytest.raises(RuntimeError, match="requires MINIO_ENDPOINT"):
        MinioStorageProvider()