"""Prompt CRUD routes."""

from fastapi import APIRouter, HTTPException, Request
from typing import Any
from ..schemas import (
    PromptSchema, VersionSchema, CreatePromptRequest, UpdatePromptRequest,
    CommitRequest, CommitSchema, PromptBlockSchema,
)
from ...storage.models import PromptBlock, PromptRole, PromptSource

router = APIRouter()


def _prompt_to_schema(prompt, versions) -> PromptSchema:
    latest_v = max((v.version_number for v in versions), default=0)
    latest_content = next((v.raw_content for v in versions if v.version_number == latest_v), "")
    summary = latest_content[:80].replace("\n", " ")
    if len(latest_content) > 80:
        summary += "..."
    return PromptSchema(
        id=prompt.id,
        name=prompt.name,
        description=prompt.description,
        source=prompt.source.value,
        file_path=prompt.file_path,
        line_number=prompt.line_number,
        variable_name=prompt.variable_name,
        tags=prompt.tags,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
        version_count=len(versions),
        latest_version=latest_v,
        summary=summary,
    )


def _version_to_schema(version) -> VersionSchema:
    return VersionSchema(
        id=version.id,
        prompt_id=version.prompt_id,
        version_number=version.version_number,
        raw_content=version.raw_content,
        blocks=[PromptBlockSchema(role=b.role.value, content=b.content) for b in version.blocks],
        content_hash=version.content_hash,
        commit_id=version.commit_id,
        created_at=version.created_at,
    )


@router.get("/prompts", response_model=list[PromptSchema])
def list_prompts(request: Request):
    repo = request.app.state.repo
    prompts = repo.list_prompts()
    result = []
    for p in prompts:
        versions = repo.list_versions(p.id)
        result.append(_prompt_to_schema(p, versions))
    return result


@router.get("/prompts/{prompt_id}", response_model=PromptSchema)
def get_prompt(prompt_id: str, request: Request):
    repo = request.app.state.repo
    prompt = repo.get_prompt_by_id(prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    versions = repo.list_versions(prompt.id)
    return _prompt_to_schema(prompt, versions)


@router.get("/prompts/{prompt_id}/versions", response_model=list[VersionSchema])
def list_versions(prompt_id: str, request: Request):
    repo = request.app.state.repo
    prompt = repo.get_prompt_by_id(prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    versions = repo.list_versions(prompt.id)
    return [_version_to_schema(v) for v in versions]


@router.post("/prompts", response_model=PromptSchema)
def create_prompt(body: CreatePromptRequest, request: Request):
    repo = request.app.state.repo
    blocks = None
    if body.blocks:
        blocks = [PromptBlock(role=PromptRole(b.role), content=b.content) for b in body.blocks]
    try:
        prompt, version = repo.create_prompt(
            name=body.name,
            content=body.content,
            description=body.description,
            blocks=blocks,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    # Auto-stage
    repo.stage(prompt.id, prompt.name, version.id, "added")
    versions = repo.list_versions(prompt.id)
    return _prompt_to_schema(prompt, versions)


@router.patch("/prompts/{prompt_id}", response_model=PromptSchema)
def update_prompt(prompt_id: str, body: UpdatePromptRequest, request: Request):
    repo = request.app.state.repo
    prompt = repo.get_prompt_by_id(prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if body.name is not None:
        prompt.name = body.name
    if body.description is not None:
        prompt.description = body.description
    repo.db.update_prompt(prompt)

    if body.content is not None:
        version = repo.update_prompt_content(prompt_id, body.content)
        if version and version.commit_id is None:
            repo.stage(prompt.id, prompt.name, version.id, "modified")

    versions = repo.list_versions(prompt.id)
    return _prompt_to_schema(prompt, versions)


@router.delete("/prompts/{prompt_id}")
def delete_prompt(prompt_id: str, request: Request):
    repo = request.app.state.repo
    prompt = repo.get_prompt_by_id(prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    repo.delete_prompt(prompt_id)
    return {"deleted": True, "id": prompt_id}


@router.post("/scan")
def trigger_scan(request: Request):
    """Re-scan the project for new/changed prompts."""
    repo = request.app.state.repo
    from ...scanner import scan_directory
    cfg = repo.get_config()
    extra_excludes = cfg.get("scan", {}).get("exclude", [])
    threshold = cfg.get("scan", {}).get("confidence_threshold", 0.5)
    results = scan_directory(repo.root, extra_excludes=extra_excludes, min_confidence=threshold)
    return {"found": len(results), "prompts": [
        {"file": r.file_path, "line": r.line_number, "name": r.variable_name, "source": r.source.value}
        for r in results
    ]}


@router.post("/commit")
def commit_prompts(body: CommitRequest, request: Request):
    repo = request.app.state.repo
    from ...exceptions import NothingToCommitError
    try:
        commit = repo.commit(body.message)
        return CommitSchema(
            id=commit.id,
            message=commit.message,
            author=commit.author,
            timestamp=commit.timestamp,
            version_ids=commit.version_ids,
        )
    except NothingToCommitError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---- Template Variables ----

@router.get("/{prompt_id}/variables")
def list_variables(prompt_id: str, request: Request):
    """Return stored template variables for a prompt."""
    repo = request.app.state.repo
    variables = repo.db.list_variables(prompt_id)
    return [
        {"id": v.id, "name": v.name, "default_value": v.default_value, "description": v.description}
        for v in variables
    ]


@router.post("/{prompt_id}/variables/sync")
def sync_variables(prompt_id: str, request: Request):
    """Auto-detect {variable} slots in the latest version and store them."""
    from ...template import extract_variables
    from ...storage.models import PromptVariable
    repo = request.app.state.repo
    prompt = repo.get_prompt_by_id(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    versions = repo.db.list_versions(prompt_id)
    if not versions:
        return {"synced": 0, "variables": []}
    raw = versions[-1].raw_content
    found = extract_variables(raw)
    added = []
    for name in found:
        existing = repo.db.get_variable_by_name(prompt_id, name)
        if existing is None:
            v = PromptVariable.new(prompt_id, name)
            repo.db.upsert_variable(v)
            added.append(name)
    all_vars = repo.db.list_variables(prompt_id)
    return {
        "synced": len(found),
        "new": len(added),
        "variables": [
            {"id": v.id, "name": v.name, "default_value": v.default_value, "description": v.description}
            for v in all_vars
        ],
    }


@router.put("/{prompt_id}/variables/{variable_id}")
def update_variable(prompt_id: str, variable_id: str, body: dict[str, Any], request: Request):
    """Update default_value or description for a variable."""
    repo = request.app.state.repo
    existing = repo.db.list_variables(prompt_id)
    var = next((v for v in existing if v.id == variable_id), None)
    if not var:
        raise HTTPException(status_code=404, detail="Variable not found")
    if "default_value" in body:
        var.default_value = body["default_value"]
    if "description" in body:
        var.description = body["description"]
    repo.db.upsert_variable(var)
    return {"id": var.id, "name": var.name, "default_value": var.default_value, "description": var.description}
