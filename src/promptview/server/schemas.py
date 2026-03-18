"""Pydantic schemas for the API."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PromptBlockSchema(BaseModel):
    role: str
    content: str


class PromptSchema(BaseModel):
    id: str
    name: str
    description: str
    source: str
    file_path: str
    line_number: int
    variable_name: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    version_count: int = 0
    latest_version: int = 0
    summary: str = ""


class VersionSchema(BaseModel):
    id: str
    prompt_id: str
    version_number: int
    raw_content: str
    blocks: list[PromptBlockSchema]
    content_hash: str
    commit_id: Optional[str]
    created_at: datetime


class CommitSchema(BaseModel):
    id: str
    message: str
    author: str
    timestamp: datetime
    version_ids: list[str]


class GraphNodeSchema(BaseModel):
    id: str
    name: str
    summary: str
    source: str
    version_count: int
    last_modified: datetime
    file_path: str
    line_number: int
    tags: list[str]


class GraphEdgeSchema(BaseModel):
    source: str
    target: str
    type: str


class GraphSchema(BaseModel):
    nodes: list[GraphNodeSchema]
    edges: list[GraphEdgeSchema]


class DiffHunkSchema(BaseModel):
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[str]


class DiffSchema(BaseModel):
    prompt_id: str
    prompt_name: str
    old_version: int
    new_version: int
    hunks: list[DiffHunkSchema]
    additions: int
    deletions: int


class CreatePromptRequest(BaseModel):
    name: str
    content: str
    description: str = ""
    blocks: Optional[list[PromptBlockSchema]] = None


class UpdatePromptRequest(BaseModel):
    content: Optional[str] = None
    description: Optional[str] = None
    name: Optional[str] = None


class CommitRequest(BaseModel):
    message: str
