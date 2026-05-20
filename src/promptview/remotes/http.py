"""HTTP/HTTPS remote backend for PromptView. Uses httpx (always installed)."""
from pathlib import Path
from .base import RemoteBackend


class HTTPBackend(RemoteBackend):
    """Push/pull the PromptView DB over HTTP(S).

    Expects:
      PUT  {base_url}/promptview.db  -- upload DB (request body = raw bytes)
      GET  {base_url}/promptview.db  -- download DB
      HEAD {base_url}/promptview.db  -- check existence
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.db_url = f"{self.base_url}/promptview.db"

    @classmethod
    def from_url(cls, url: str) -> "HTTPBackend":
        return cls(base_url=url)

    def push(self, db_path: Path) -> None:
        import httpx
        with open(db_path, "rb") as f:
            data = f.read()
        resp = httpx.put(self.db_url, content=data, timeout=60.0)
        resp.raise_for_status()

    def pull(self, db_path: Path) -> None:
        import httpx
        resp = httpx.get(self.db_url, timeout=60.0)
        resp.raise_for_status()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with open(db_path, "wb") as f:
            f.write(resp.content)

    def exists(self) -> bool:
        try:
            import httpx
            resp = httpx.head(self.db_url, timeout=10.0)
            return resp.status_code == 200
        except Exception:
            return False
