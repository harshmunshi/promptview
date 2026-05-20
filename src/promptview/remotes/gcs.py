"""GCS remote backend for PromptView. Requires: pip install promptview[gcs]"""
from pathlib import Path
from .base import RemoteBackend


class GCSBackend(RemoteBackend):
    """Store the PromptView DB in a GCS bucket."""

    def __init__(self, bucket: str, blob_name: str):
        self.bucket = bucket
        self.blob_name = blob_name

    @classmethod
    def from_url(cls, url: str) -> "GCSBackend":
        without_scheme = url[len("gcs://"):]
        parts = without_scheme.split("/", 1)
        bucket = parts[0]
        prefix = parts[1].rstrip("/") if len(parts) > 1 else ""
        blob_name = f"{prefix}/promptview.db" if prefix else "promptview.db"
        return cls(bucket=bucket, blob_name=blob_name)

    def _bucket_obj(self):
        try:
            from google.cloud import storage
        except ImportError:
            raise ImportError("GCS backend requires google-cloud-storage: pip install promptview[gcs]")
        client = storage.Client()
        return client.bucket(self.bucket)

    def push(self, db_path: Path) -> None:
        bucket = self._bucket_obj()
        blob = bucket.blob(self.blob_name)
        blob.upload_from_filename(str(db_path))

    def pull(self, db_path: Path) -> None:
        bucket = self._bucket_obj()
        blob = bucket.blob(self.blob_name)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(db_path))

    def exists(self) -> bool:
        try:
            bucket = self._bucket_obj()
            blob = bucket.blob(self.blob_name)
            return blob.exists()
        except Exception:
            return False
