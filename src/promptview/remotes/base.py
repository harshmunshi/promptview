"""Abstract base class for PromptView remote storage backends."""
from abc import ABC, abstractmethod
from pathlib import Path


class RemoteBackend(ABC):
    """Push/pull the .promptview/ SQLite DB to/from a remote location."""

    @abstractmethod
    def push(self, db_path: Path) -> None:
        """Upload the SQLite DB file to the remote."""

    @abstractmethod
    def pull(self, db_path: Path) -> None:
        """Download the remote DB file and overwrite the local one."""

    @abstractmethod
    def exists(self) -> bool:
        """Return True if a remote DB already exists at this location."""

    @classmethod
    def from_url(cls, url: str) -> "RemoteBackend":
        """Factory: parse s3://, gcs://, or http(s):// and return the right backend."""
        if url.startswith("s3://"):
            from .s3 import S3Backend
            return S3Backend.from_url(url)
        elif url.startswith("gcs://"):
            from .gcs import GCSBackend
            return GCSBackend.from_url(url)
        elif url.startswith("http://") or url.startswith("https://"):
            from .http import HTTPBackend
            return HTTPBackend.from_url(url)
        else:
            raise ValueError(f"Unsupported remote URL scheme: {url!r}. Use s3://, gcs://, or https://")
