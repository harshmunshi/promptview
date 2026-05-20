"""Main repository facade - all CLI commands and API routes use this."""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .db import Database
from .diff_engine import compute_diff
from .models import (
    Commit, IndexEntry, Prompt, PromptBlock, PromptBranch, PromptRole,
    PromptSource, PromptVersion,
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

    # ---- Branches ----

    def list_branches(self, prompt_id: str) -> list[PromptBranch]:
        return self.db.list_branches(prompt_id)

    def create_branch(
        self,
        prompt_id: str,
        name: str,
        from_version_id: Optional[str] = None,
    ) -> PromptBranch:
        """Create a new branch from the given version (or latest if not specified)."""
        if from_version_id is None:
            latest = self.db.get_latest_version(prompt_id)
            from_version_id = latest.id if latest else None
        branch = PromptBranch.new(
            name=name,
            prompt_id=prompt_id,
            base_version_id=from_version_id,
            is_default=(name == "main"),
        )
        return self.db.create_branch(branch)

    def delete_branch(self, prompt_id: str, name: str) -> None:
        """Delete a branch by name. Raises ValueError if not found."""
        branch = self.db.get_branch(prompt_id, name)
        if branch is None:
            raise ValueError(f"Branch '{name}' not found for prompt {prompt_id}")
        self.db.delete_branch(branch.id)

    def merge_branch(
        self,
        prompt_id: str,
        source_branch: str,
        target_branch: str = "main",
    ) -> PromptVersion:
        """Merge source branch HEAD content into target branch as a new version."""
        src = self.db.get_branch(prompt_id, source_branch)
        if src is None:
            raise ValueError(f"Source branch '{source_branch}' not found")
        tgt = self.db.get_branch(prompt_id, target_branch)
        if tgt is None:
            raise ValueError(f"Target branch '{target_branch}' not found")
        if src.head_version_id is None:
            raise ValueError(f"Source branch '{source_branch}' has no commits")

        # Fetch the content from the source branch head
        src_version = self.db.get_version(src.head_version_id)
        if src_version is None:
            raise ValueError(f"Source head version not found: {src.head_version_id}")

        # Create a new version on the target branch with source content
        new_version = self.update_prompt_content(
            prompt_id,
            src_version.raw_content,
            blocks=src_version.blocks,
        )
        # Advance the target branch HEAD to the new version
        self.db.update_branch_head(tgt.id, new_version.id)
        # Mark the source branch as merged
        self.db.mark_branch_merged(src.id)
        return new_version

    def get_current_branch(self, prompt_id: str) -> str:
        """Return the active branch name for a prompt (reads config.toml)."""
        cfg = self.get_config()
        return cfg.get("branches", {}).get(f"prompt_{prompt_id}", "main")

    def set_current_branch(self, prompt_id: str, branch_name: str) -> None:
        """Write the active branch for a prompt into config.toml."""
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore
        import tomli_w

        if self.config_path.exists():
            with open(self.config_path, "rb") as f:
                cfg = tomllib.load(f)
        else:
            cfg = {}

        if "branches" not in cfg:
            cfg["branches"] = {}
        cfg["branches"][f"prompt_{prompt_id}"] = branch_name
        self.config_path.write_bytes(tomli_w.dumps(cfg).encode())

    def ensure_main_branch(self, prompt_id: str) -> PromptBranch:
        """Create 'main' branch if it doesn't exist. Called on init/scan."""
        existing = self.db.get_branch(prompt_id, "main")
        if existing is not None:
            return existing
        latest = self.db.get_latest_version(prompt_id)
        branch = PromptBranch.new(
            name="main",
            prompt_id=prompt_id,
            base_version_id=latest.id if latest else None,
            is_default=True,
        )
        return self.db.create_branch(branch)

    # ---- Remote Ingestion ----

    def ingest_remote_prompts(self, remote_data: list[dict], source: str) -> dict:
        """Ingest a list of prompt dicts fetched from a remote into the local repo.

        Each item in remote_data must have at minimum:
            {"name": str, "content": str}
        Optional fields: "version" (int), "labels" (list), "created_at" (str)

        For each item:
        - If a local prompt with the same name already exists, add a new version
          only if the content hash differs from all existing versions.
        - If no local prompt exists, create it with source=PromptSource.MANUAL and
          description="Pulled from <source>".

        Returns:
            {"created": N, "updated": N, "skipped": N}
        """
        created = 0
        updated = 0
        skipped = 0

        for item in remote_data:
            name = item.get("name", "").strip()
            content = item.get("content", "").strip()
            if not name or not content:
                skipped += 1
                continue

            # Compute content hash (short, matching existing convention)
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

            existing_prompt = self.db.get_prompt_by_name(name)

            if existing_prompt is None:
                # Create a brand-new prompt
                prompt, _version = self.create_prompt(
                    name=name,
                    content=content,
                    source=PromptSource.MANUAL,
                    description=f"Pulled from {source}",
                )
                created += 1
            else:
                # Check if any existing version has the same hash
                existing_versions = self.db.list_versions(existing_prompt.id)
                hashes = {v.content_hash for v in existing_versions}
                if content_hash in hashes:
                    skipped += 1
                    continue
                # Add a new version
                self.update_prompt_content(existing_prompt.id, content)
                updated += 1

        return {"created": created, "updated": updated, "skipped": skipped}

    @classmethod
    def find_root(cls, start: Optional[Path] = None) -> Path:
        """Walk up from start until finding .promptview/ dir."""
        current = start or Path.cwd()
        for parent in [current] + list(current.parents):
            if (parent / PROMPTVIEW_DIR).exists():
                return parent
        return current  # fallback to cwd
