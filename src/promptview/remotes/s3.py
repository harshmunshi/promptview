"""S3 remote backend for PromptView. Requires: pip install promptview[s3]"""
from pathlib import Path
from .base import RemoteBackend


class S3Backend(RemoteBackend):
    """Store the PromptView DB in an S3 bucket."""

    def __init__(self, bucket: str, key: str):
        self.bucket = bucket
        self.key = key  # e.g. "promptview/promptview.db"

    @classmethod
    def from_url(cls, url: str) -> "S3Backend":
        # s3://bucket-name/path/to/dir  ->  bucket=bucket-name, key=path/to/dir/promptview.db
        without_scheme = url[len("s3://"):]
        parts = without_scheme.split("/", 1)
        bucket = parts[0]
        prefix = parts[1].rstrip("/") if len(parts) > 1 else ""
        key = f"{prefix}/promptview.db" if prefix else "promptview.db"
        return cls(bucket=bucket, key=key)

    def _client(self):
        try:
            import boto3
        except ImportError:
            raise ImportError("S3 backend requires boto3: pip install promptview[s3]")
        return boto3.client("s3")

    def push(self, db_path: Path) -> None:
        client = self._client()
        client.upload_file(str(db_path), self.bucket, self.key)

    def pull(self, db_path: Path) -> None:
        client = self._client()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        client.download_file(self.bucket, self.key, str(db_path))

    def exists(self) -> bool:
        try:
            client = self._client()
            client.head_object(Bucket=self.bucket, Key=self.key)
            return True
        except Exception:
            return False
