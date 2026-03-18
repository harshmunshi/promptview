"""SQLite database layer for PromptView."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import (
    Commit, EvalResult, EvalRun, Prompt, PromptBlock, PromptComponent, PromptRole,
    PromptSource, PromptVersion, TestCase,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS prompts (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,
    description   TEXT DEFAULT '',
    source        TEXT NOT NULL DEFAULT 'raw',
    file_path     TEXT NOT NULL DEFAULT '',
    line_number   INTEGER NOT NULL DEFAULT 0,
    variable_name TEXT DEFAULT '',
    tags          TEXT DEFAULT '[]',
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prompt_versions (
    id                TEXT PRIMARY KEY,
    prompt_id         TEXT NOT NULL REFERENCES prompts(id),
    version_number    INTEGER NOT NULL,
    raw_content       TEXT NOT NULL,
    blocks            TEXT NOT NULL,
    content_hash      TEXT NOT NULL,
    commit_id         TEXT,
    parent_version_id TEXT,
    created_at        TEXT NOT NULL,
    UNIQUE(prompt_id, version_number)
);

CREATE TABLE IF NOT EXISTS commits (
    id          TEXT PRIMARY KEY,
    message     TEXT NOT NULL,
    author      TEXT NOT NULL,
    timestamp   TEXT NOT NULL,
    version_ids TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS remotes (
    name     TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    project  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prompt_components (
    id         TEXT PRIMARY KEY,
    prompt_id  TEXT NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    version_id TEXT NOT NULL,
    label      TEXT NOT NULL,
    content    TEXT NOT NULL,
    position   INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS test_cases (
  id              TEXT PRIMARY KEY,
  prompt_id       TEXT NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
  input           TEXT NOT NULL,
  expected_output TEXT,
  tags            TEXT DEFAULT '[]',
  created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS eval_runs (
  id              TEXT PRIMARY KEY,
  prompt_id       TEXT NOT NULL REFERENCES prompts(id),
  version_id      TEXT NOT NULL REFERENCES prompt_versions(id),
  source          TEXT NOT NULL DEFAULT 'local',
  run_at          TEXT NOT NULL,
  dataset_path    TEXT,
  provider        TEXT,
  model           TEXT,
  total_cases     INTEGER DEFAULT 0,
  passed          INTEGER DEFAULT 0,
  avg_latency_ms  REAL DEFAULT 0,
  avg_cost_usd    REAL DEFAULT 0,
  avg_judge_score REAL,
  custom_metrics  TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS eval_results (
  id               TEXT PRIMARY KEY,
  eval_run_id      TEXT NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
  test_case_id     TEXT REFERENCES test_cases(id),
  actual_output    TEXT,
  passed           INTEGER DEFAULT 0,
  similarity_score REAL,
  judge_score      REAL,
  judge_reasoning  TEXT,
  latency_ms       REAL,
  tokens_used      INTEGER,
  cost_usd         REAL
);
"""


def _fmt(dt: datetime) -> str:
    return dt.isoformat()


def _parse(s: str) -> datetime:
    return datetime.fromisoformat(s)


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> "Database":
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        # Always apply schema so new tables are created on existing DBs
        self.initialize()
        return self

    def initialize(self) -> None:
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()

    # ---- Prompts ----

    def insert_prompt(self, p: Prompt) -> None:
        self._conn.execute(
            """INSERT INTO prompts (id, name, description, source, file_path,
               line_number, variable_name, tags, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (p.id, p.name, p.description, p.source.value, p.file_path,
             p.line_number, p.variable_name, json.dumps(p.tags),
             _fmt(p.created_at), _fmt(p.updated_at)),
        )
        self._conn.commit()

    def update_prompt(self, p: Prompt) -> None:
        self._conn.execute(
            """UPDATE prompts SET name=?, description=?, source=?, file_path=?,
               line_number=?, variable_name=?, tags=?, updated_at=? WHERE id=?""",
            (p.name, p.description, p.source.value, p.file_path,
             p.line_number, p.variable_name, json.dumps(p.tags),
             _fmt(p.updated_at), p.id),
        )
        self._conn.commit()

    def get_prompt_by_name(self, name: str) -> Optional[Prompt]:
        row = self._conn.execute(
            "SELECT * FROM prompts WHERE name=?", (name,)
        ).fetchone()
        return self._row_to_prompt(row) if row else None

    def get_prompt_by_id(self, pid: str) -> Optional[Prompt]:
        row = self._conn.execute(
            "SELECT * FROM prompts WHERE id=?", (pid,)
        ).fetchone()
        return self._row_to_prompt(row) if row else None

    def list_prompts(self) -> list[Prompt]:
        rows = self._conn.execute(
            "SELECT * FROM prompts ORDER BY name"
        ).fetchall()
        return [self._row_to_prompt(r) for r in rows]

    def delete_prompt(self, pid: str) -> None:
        self._conn.execute("DELETE FROM prompts WHERE id=?", (pid,))
        self._conn.commit()

    def _row_to_prompt(self, row: sqlite3.Row) -> Prompt:
        return Prompt(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            source=PromptSource(row["source"]),
            file_path=row["file_path"] or "",
            line_number=row["line_number"] or 0,
            variable_name=row["variable_name"] or "",
            tags=json.loads(row["tags"] or "[]"),
            created_at=_parse(row["created_at"]),
            updated_at=_parse(row["updated_at"]),
        )

    # ---- PromptVersions ----

    def insert_version(self, v: PromptVersion) -> None:
        self._conn.execute(
            """INSERT INTO prompt_versions
               (id, prompt_id, version_number, raw_content, blocks,
                content_hash, commit_id, parent_version_id, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (v.id, v.prompt_id, v.version_number, v.raw_content,
             json.dumps([b.to_dict() for b in v.blocks]),
             v.content_hash, v.commit_id, v.parent_version_id,
             _fmt(v.created_at)),
        )
        self._conn.commit()

    def update_version_commit(self, version_id: str, commit_id: str) -> None:
        self._conn.execute(
            "UPDATE prompt_versions SET commit_id=? WHERE id=?",
            (commit_id, version_id),
        )
        self._conn.commit()

    def get_version(self, version_id: str) -> Optional[PromptVersion]:
        row = self._conn.execute(
            "SELECT * FROM prompt_versions WHERE id=?", (version_id,)
        ).fetchone()
        return self._row_to_version(row) if row else None

    def get_latest_version(self, prompt_id: str) -> Optional[PromptVersion]:
        row = self._conn.execute(
            """SELECT * FROM prompt_versions WHERE prompt_id=?
               ORDER BY version_number DESC LIMIT 1""",
            (prompt_id,),
        ).fetchone()
        return self._row_to_version(row) if row else None

    def get_committed_version(self, prompt_id: str) -> Optional[PromptVersion]:
        """Get the latest version that has been committed (commit_id IS NOT NULL)."""
        row = self._conn.execute(
            """SELECT * FROM prompt_versions WHERE prompt_id=?
               AND commit_id IS NOT NULL
               ORDER BY version_number DESC LIMIT 1""",
            (prompt_id,),
        ).fetchone()
        return self._row_to_version(row) if row else None

    def list_versions(self, prompt_id: str) -> list[PromptVersion]:
        rows = self._conn.execute(
            """SELECT * FROM prompt_versions WHERE prompt_id=?
               ORDER BY version_number""",
            (prompt_id,),
        ).fetchall()
        return [self._row_to_version(r) for r in rows]

    def get_version_by_number(self, prompt_id: str, number: int) -> Optional[PromptVersion]:
        row = self._conn.execute(
            "SELECT * FROM prompt_versions WHERE prompt_id=? AND version_number=?",
            (prompt_id, number),
        ).fetchone()
        return self._row_to_version(row) if row else None

    def next_version_number(self, prompt_id: str) -> int:
        row = self._conn.execute(
            "SELECT MAX(version_number) as mx FROM prompt_versions WHERE prompt_id=?",
            (prompt_id,),
        ).fetchone()
        return (row["mx"] or 0) + 1

    def _row_to_version(self, row: sqlite3.Row) -> PromptVersion:
        blocks_data = json.loads(row["blocks"] or "[]")
        blocks = [PromptBlock.from_dict(b) for b in blocks_data]
        return PromptVersion(
            id=row["id"],
            prompt_id=row["prompt_id"],
            version_number=row["version_number"],
            raw_content=row["raw_content"],
            blocks=blocks,
            content_hash=row["content_hash"],
            commit_id=row["commit_id"],
            parent_version_id=row["parent_version_id"],
            created_at=_parse(row["created_at"]),
        )

    # ---- Commits ----

    def insert_commit(self, c: Commit) -> None:
        self._conn.execute(
            """INSERT INTO commits (id, message, author, timestamp, version_ids)
               VALUES (?,?,?,?,?)""",
            (c.id, c.message, c.author,
             _fmt(c.timestamp), json.dumps(c.version_ids)),
        )
        self._conn.commit()

    def list_commits(self) -> list[Commit]:
        rows = self._conn.execute(
            "SELECT * FROM commits ORDER BY timestamp DESC"
        ).fetchall()
        return [self._row_to_commit(r) for r in rows]

    def list_commits_for_prompt(self, prompt_id: str) -> list[Commit]:
        """Return commits that include at least one version of this prompt."""
        versions = self._conn.execute(
            "SELECT id, commit_id FROM prompt_versions WHERE prompt_id=? AND commit_id IS NOT NULL",
            (prompt_id,),
        ).fetchall()
        commit_ids = list({r["commit_id"] for r in versions})
        if not commit_ids:
            return []
        placeholders = ",".join("?" * len(commit_ids))
        rows = self._conn.execute(
            f"SELECT * FROM commits WHERE id IN ({placeholders}) ORDER BY timestamp DESC",
            commit_ids,
        ).fetchall()
        return [self._row_to_commit(r) for r in rows]

    def _row_to_commit(self, row: sqlite3.Row) -> Commit:
        return Commit(
            id=row["id"],
            message=row["message"],
            author=row["author"],
            timestamp=_parse(row["timestamp"]),
            version_ids=json.loads(row["version_ids"] or "[]"),
        )

    # ---- PromptComponents ----

    def upsert_components(self, components: list[PromptComponent]) -> None:
        """Replace all components for a (prompt_id, version_id) pair."""
        if not components:
            return
        prompt_id = components[0].prompt_id
        version_id = components[0].version_id
        self._conn.execute(
            "DELETE FROM prompt_components WHERE prompt_id=? AND version_id=?",
            (prompt_id, version_id),
        )
        for c in components:
            self._conn.execute(
                """INSERT INTO prompt_components
                   (id, prompt_id, version_id, label, content, position, created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (c.id, c.prompt_id, c.version_id, c.label, c.content,
                 c.position, _fmt(c.created_at)),
            )
        self._conn.commit()

    def get_components(self, prompt_id: str, version_id: str) -> list[PromptComponent]:
        rows = self._conn.execute(
            """SELECT * FROM prompt_components WHERE prompt_id=? AND version_id=?
               ORDER BY position""",
            (prompt_id, version_id),
        ).fetchall()
        return [self._row_to_component(r) for r in rows]

    def delete_component(self, component_id: str) -> None:
        self._conn.execute(
            "DELETE FROM prompt_components WHERE id=?", (component_id,)
        )
        self._conn.commit()

    def _row_to_component(self, row: sqlite3.Row) -> PromptComponent:
        return PromptComponent(
            id=row["id"],
            prompt_id=row["prompt_id"],
            version_id=row["version_id"],
            label=row["label"],
            content=row["content"],
            position=row["position"],
            created_at=_parse(row["created_at"]),
        )

    # ---- TestCases ----

    def create_test_case(self, tc: TestCase) -> TestCase:
        self._conn.execute(
            """INSERT INTO test_cases (id, prompt_id, input, expected_output, tags, created_at)
               VALUES (?,?,?,?,?,?)""",
            (tc.id, tc.prompt_id, tc.input, tc.expected_output,
             json.dumps(tc.tags), tc.created_at),
        )
        self._conn.commit()
        return tc

    def list_test_cases(self, prompt_id: str) -> list:
        rows = self._conn.execute(
            "SELECT * FROM test_cases WHERE prompt_id=? ORDER BY created_at",
            (prompt_id,),
        ).fetchall()
        return [self._row_to_test_case(r) for r in rows]

    def delete_test_case(self, tc_id: str) -> None:
        self._conn.execute("DELETE FROM test_cases WHERE id=?", (tc_id,))
        self._conn.commit()

    def _row_to_test_case(self, row: sqlite3.Row) -> TestCase:
        return TestCase(
            id=row["id"],
            prompt_id=row["prompt_id"],
            input=row["input"],
            expected_output=row["expected_output"],
            tags=json.loads(row["tags"] or "[]"),
            created_at=row["created_at"],
        )

    # ---- EvalRuns ----

    def create_eval_run(self, run: EvalRun) -> EvalRun:
        self._conn.execute(
            """INSERT INTO eval_runs
               (id, prompt_id, version_id, source, run_at, dataset_path, provider, model,
                total_cases, passed, avg_latency_ms, avg_cost_usd, avg_judge_score, custom_metrics)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (run.id, run.prompt_id, run.version_id, run.source, run.run_at,
             run.dataset_path, run.provider, run.model,
             run.total_cases, run.passed, run.avg_latency_ms, run.avg_cost_usd,
             run.avg_judge_score, json.dumps(run.custom_metrics)),
        )
        self._conn.commit()
        return run

    def list_eval_runs(self, prompt_id: str) -> list:
        rows = self._conn.execute(
            "SELECT * FROM eval_runs WHERE prompt_id=? ORDER BY run_at",
            (prompt_id,),
        ).fetchall()
        return [self._row_to_eval_run(r) for r in rows]

    def get_eval_run(self, run_id: str):
        row = self._conn.execute(
            "SELECT * FROM eval_runs WHERE id=?", (run_id,)
        ).fetchone()
        return self._row_to_eval_run(row) if row else None

    def _row_to_eval_run(self, row: sqlite3.Row) -> EvalRun:
        return EvalRun(
            id=row["id"],
            prompt_id=row["prompt_id"],
            version_id=row["version_id"],
            source=row["source"],
            run_at=row["run_at"],
            dataset_path=row["dataset_path"],
            provider=row["provider"],
            model=row["model"],
            total_cases=row["total_cases"] or 0,
            passed=row["passed"] or 0,
            avg_latency_ms=row["avg_latency_ms"] or 0.0,
            avg_cost_usd=row["avg_cost_usd"] or 0.0,
            avg_judge_score=row["avg_judge_score"],
            custom_metrics=json.loads(row["custom_metrics"] or "{}"),
        )

    # ---- EvalResults ----

    def create_eval_result(self, result: EvalResult) -> EvalResult:
        self._conn.execute(
            """INSERT INTO eval_results
               (id, eval_run_id, test_case_id, actual_output, passed,
                similarity_score, judge_score, judge_reasoning, latency_ms,
                tokens_used, cost_usd)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (result.id, result.eval_run_id, result.test_case_id, result.actual_output,
             1 if result.passed else 0,
             result.similarity_score, result.judge_score, result.judge_reasoning,
             result.latency_ms, result.tokens_used, result.cost_usd),
        )
        self._conn.commit()
        return result

    def list_eval_results(self, eval_run_id: str) -> list:
        rows = self._conn.execute(
            "SELECT * FROM eval_results WHERE eval_run_id=?", (eval_run_id,)
        ).fetchall()
        return [self._row_to_eval_result(r) for r in rows]

    def _row_to_eval_result(self, row: sqlite3.Row) -> EvalResult:
        return EvalResult(
            id=row["id"],
            eval_run_id=row["eval_run_id"],
            test_case_id=row["test_case_id"],
            actual_output=row["actual_output"] or "",
            passed=bool(row["passed"]),
            similarity_score=row["similarity_score"],
            judge_score=row["judge_score"],
            judge_reasoning=row["judge_reasoning"],
            latency_ms=row["latency_ms"] or 0.0,
            tokens_used=row["tokens_used"] or 0,
            cost_usd=row["cost_usd"] or 0.0,
        )
