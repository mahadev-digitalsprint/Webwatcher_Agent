from pathlib import Path

from webwatcher.core.config import get_settings

try:
    from azure.storage.blob import BlobServiceClient
except Exception:  # pragma: no cover - optional dependency at runtime
    BlobServiceClient = None


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base = Path(self.settings.base_download_path)
        self.base.mkdir(parents=True, exist_ok=True)

    def build_path(self, company_id: int, timestamp: str, filename: str) -> str:
        return f"{company_id}/{timestamp}/{filename}"

    def save_local(self, relative_path: str, data: bytes) -> str:
        path = self.base / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    def upload(self, container: str, relative_path: str, data: bytes) -> str:
        if self.settings.azure_storage_connection_string and BlobServiceClient is not None:
            client = BlobServiceClient.from_connection_string(
                self.settings.azure_storage_connection_string
            )
            blob = client.get_blob_client(container=container, blob=relative_path)
            blob.upload_blob(data, overwrite=True)
            return relative_path
        return self.save_local(relative_path, data)

