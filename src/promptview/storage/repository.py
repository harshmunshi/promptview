"""Main repository facade - all CLI commands and API routes use this."""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .db import Database
from .diff_engine import compute_diff
from .models import (
    Commit, IndexEntry, Prompt, PromptBlock, PromptRole, PromptSource,
    PromptVersion,
)
from ..exceptions import NotInitializedError, PromptNotFoundError

PROMPTVIEW_DIR = ".promptview"


class PromptRepository:
    def __init__(self, root: Path):
        self.root = root
        self.pv_dir = root / PROMPTVIEW_DIR
        self.db_path = self.pv_dir / "promptview.db"
        self.index_path = self.pv_dir / "index.json"
        self.head_path = self.pv_dir / "HEAD"
        self.config_path = self.pv_dir / "config.toml"
        self.objects_dir = self.pv_dir / "objects"
        self.logs_dir = self.pv_dir / "logs"
        self._db: Optional[Database] = None

    # ---- Lifecycle ----

    def is_initialized(self) -> bool:
        return self.pv_dir.exists() and self.db_path.exists()

    def initialize(self, author: str = "", project_name: str = "") -> None:
        """Create .promptview/ directory structure."""
        self.pv_dir.mkdir(exist_ok=True)
        self.objects_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        (self.pv_dir / "refs").mkdir(exist_ok=True)

        self._db = Database(self.db_path)
        self._db.connect()
        self._db.initialize()

        if not self.index_path.exists():
            self.index_path.write_text(json.dumps({"staged": []}))

        if not self.head_path.exists():
            self.head_path.write_text("UNCOMMITTED")

        if not self.config_path.exists():
            import getpass, tomli_w
            config = {
                "project": {
                    "name": project_name or self.root.name,
                    "author": author or getpass.getuser(),
                    "created_at": datetime.utcnow().isoformat(),
                },
                "scan": {
                    "include": ["**/*.py"],
                    "exclude": [".venv", "venv", "node_modules", "__pycache__", ".git"],
                    "min_prompt_length": 50,
                    "confidence_threshold": 0.5,
                },
            }
            self.config_path.write_bytes(tomli_w.dumps(config).encode())

    def open(self) -> "PromptRepository":
        """Open an existing repository (connect to DB)."""
        if not self.is_initialized():
            raise NotInitializedError(
                f"Not a promptview repository. Run `promptview init` in {self.root}"
            )
        self._db = Database(self.db_path)
        self._db.connect()
        return self

    def close(self) -> None:
        if self._db:
            self._db.close()

    @property
    def db(self) -> Database:
        if self._db is None:
            raise NotInitializedError("Repository not opened.")
        return self._db

    # ---- Config ----

    def get_config(self) -> dict:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore
        if self.config_path.exists():
            with open(self.config_path, "rb") as f:
                return tomllib.load(f)
        return {}

    def get_author(self) -> str:
        cfg = self.get_config()
        return cfg.get("project", {}).get("author", "unknown")

    def get_confidence_threshold(self) -> float:
        cfg = self.get_config()
        return cfg.get("scan", {}).get("confidence_threshold", 0.5)

    # ---- Prompts ----

    def get_prompt_by_name(self, name: str) -> Optional[Prompt]:
        return self.db.get_prompt_by_name(name)

    def get_prompt_by_id(self, pid: str) -> Optional[Prompt]:
        return self.db.get_prompt_by_id(pid)

    def list_prompts(self) -> list[Prompt]:
        return self.db.list_prompts()

    def create_prompt(
        self,
        name: str,
        content: str,
        source: PromptSource = PromptSource.MANUAL,
        file_path: str = "",
        line_number: int = 0,
        variable_name: str = "",
        description: str = "",
        blocks: Optional[list[PromptBlock]] = None,
    ) -> tuple[Prompt, PromptVersion]:
        """Create a new prompt and its first version. Returns (prompt, version)."""
        now = datetime.utcnow()
        prompt = Prompt.new(
            name=name,
            description=description,
            source=source,
            file_path=file_path,
            line_number=line_number,
            variable_name=variable_name,
            created_at=now,
            updated_at=now,
        )
        if blocks is None:
            blocks = [PromptBlock(role=PromptRole.FULL, content=content)]
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        version = PromptVersion.new(
            prompt_id=prompt.id,
            version_number=1,
            blocks=blocks,
            raw_content=content,
            content_hash=content_hash,
            created_at=now,
        )
        self.db.insert_prompt(prompt)
        self.db.insert_version(version)
        self._write_object(content_hash, content)
        return prompt, version

    def update_prompt_content(
        self,
        prompt_id: str,
        new_content: str,
        blocks: Optional[list[PromptBlock]] = None,
    ) -> PromptVersion:
        """Create a new version for an existing prompt."""
        prompt = self.db.get_prompt_by_id(prompt_id)
        if prompt is None:
            raise PromptNotFoundError(prompt_id)
        content_hash = hashlib.sha256(new_content.encode()).hexdigest()
        latest = self.db.get_latest_version(prompt_id)
        if latest and latest.content_hash == content_hash:
            return latest  # no change
        version_number = self.db.next_version_number(prompt_id)
        if blocks is None:
            blocks = [PromptBlock(role=PromptRole.FULL, content=new_content)]
        version = PromptVersion.new(
            prompt_id=prompt_id,
            version_number=version_number,
            blocks=blocks,
            raw_content=new_content,
            content_hash=content_hash,
            parent_version_id=latest.id if latest else None,
        )
        self.db.insert_version(version)
        self._write_object(content_hash, new_content)
        prompt.updated_at = datetime.utcnow()
        self.db.update_prompt(prompt)
        return version

    def delete_prompt(self, prompt_id: str) -> None:
        self.db.delete_prompt(prompt_id)

    def list_versions(self, prompt_id: str) -> list[PromptVersion]:
        return self.db.list_versions(prompt_id)

    def get_version(self, version_id: str) -> Optional[PromptVersion]:
        return self.db.get_version(version_id)

    def get_version_by_number(self, prompt_id: str, number: int) -> Optional[PromptVersion]:
        return self.db.get_version_by_number(prompt_id, number)

    # ---- Staging Index ----

    def _read_index(self) -> dict:
        if self.index_path.exists():
            return json.loads(self.index_path.read_text())
        return {"staged": []}

    def _write_index(self, data: dict) -> None:
        self.index_path.write_text(json.dumps(data, indent=2, default=str))

    def get_staged(self) -> list[IndexEntry]:
        data = self._read_index()
        entries = []
        for item in data.get("staged", []):
            entries.append(IndexEntry(
                prompt_id=item["prompt_id"],
                prompt_name=item["prompt_name"],
                version_id=item["version_id"],
                staged_at=datetime.fromisoformat(item["staged_at"]),
                change_type=item["change_type"],
            ))
        return entries

    def stage(self, prompt_id: str, prompt_name: str, version_id: str,
              change_type: str) -> None:
        data = self._read_index()
        # Remove any existing entry for this prompt
        data["staged"] = [s for s in data["staged"] if s["prompt_id"] != prompt_id]
        data["staged"].append({
            "prompt_id": prompt_id,
            "prompt_name": prompt_name,
            "version_id": version_id,
            "staged_at": datetime.utcnow().isoformat(),
            "change_type": change_type,
        })
        self._write_index(data)

    def unstage(self, prompt_id: str) -> None:
        data = self._read_index()
        data["staged"] = [s for s in data["staged"] if s["prompt_id"] != prompt_id]
        self._write_index(data)

    def clear_index(self) -> None:
        self._write_index({"staged": []})

    # ---- Commits ----

    def commit(self, message: str) -> Commit:
        staged = self.get_staged()
        if not staged:
            from ..exceptions import NothingToCommitError
            raise NothingToCommitError("Nothing to commit. Stage changes with `promptview add`.")

        author = self.get_author()
        version_ids = [s.version_id for s in staged]
        commit = Commit.new(message=message, author=author, version_ids=version_ids)
        self.db.insert_commit(commit)
        for version_id in version_ids:
            self.db.update_version_commit(version_id, commit.id)
        self._write_head(commit.id)
        self._append_log(commit)
        self.clear_index()
        return commit

    def list_commits(self) -> list[Commit]:
        return self.db.list_commits()

    def list_commits_for_prompt(self, prompt_id: str) -> list[Commit]:
        return self.db.list_commits_for_prompt(prompt_id)

    # ---- HEAD / Refs ----

    def get_head(self) -> str:
        if self.head_path.exists():
            return self.head_path.read_text().strip()
        return "UNCOMMITTED"

    def _write_head(self, commit_id: str) -> None:
        self.head_path.write_text(commit_id)
        refs_main = self.pv_dir / "refs" / "main"
        refs_main.write_text(commit_id)

    def _append_log(self, commit: Commit) -> None:
        log_file = self.logs_dir / "HEAD"
        line = f"{commit.id} {commit.author} {commit.timestamp.isoformat()} {commit.message}\n"
        with open(log_file, "a") as f:
            f.write(line)

    # ---- Diffs ----

    def diff(
        self,
        prompt_id: str,
        old_version_number: Optional[int] = None,
        new_version_number: Optional[int] = None,
        staged: bool = False,
    ):
        prompt = self.db.get_prompt_by_id(prompt_id)
        if prompt is None:
            raise PromptNotFoundError(prompt_id)

        if old_version_number is not None:
            old_v = self.db.get_version_by_number(prompt_id, old_version_number)
        else:
            old_v = self.db.get_committed_version(prompt_id)

        if new_version_number is not None:
            new_v = self.db.get_version_by_number(prompt_id, new_version_number)
        else:
            new_v = self.db.get_latest_version(prompt_id)

        if old_v is None or new_v is None:
            return None
        if old_v.id == new_v.id:
            return None

        return compute_diff(prompt_id, prompt.name, old_v, new_v)

    # ---- Objects ----

    def _write_object(self, content_hash: str, content: str) -> None:
        prefix = content_hash[:2]
        suffix = content_hash[2:]
        obj_dir = self.objects_dir / prefix
        obj_dir.mkdir(exist_ok=True)
        obj_path = obj_dir / suffix
        if not obj_path.exists():
            obj_path.write_text(content)

    # ---- Status ----

    def status(self, scanned_prompts=None) -> dict:
        """Return status dict with staged, modified, untracked."""
        staged = self.get_staged()
        staged_ids = {s.prompt_id for s in staged}

        modified = []
        untracked = []

        if scanned_prompts:
            known_prompts = {p.name: p for p in self.list_prompts()}
            for sp in scanned_prompts:
                if sp.variable_name in known_prompts:
                    p = known_prompts[sp.variable_name]
                    committed = self.db.get_committed_version(p.id)
                    if committed:
                        import hashlib as _h
                        ch = _h.sha256(sp.raw_content.encode()).hexdigest()
                        if ch != committed.content_hash and p.id not in staged_ids:
                            modified.append(p)
                    elif p.id not in staged_ids:
                        modified.append(p)
                else:
                    untracked.append(sp)

        return {
            "staged": staged,
            "modified": modified,
            "untracked": untracked,
        }

    @classmethod
    def find_root(cls, start: Optional[Path] = None) -> Path:
        """Walk up from start until finding .promptview/ dir."""
        current = start or Path.cwd()
        for parent in [current] + list(current.parents):
            if (parent / PROMPTVIEW_DIR).exists():
                return parent
        return current  # fallback to cwd
