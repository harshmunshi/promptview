"""Branch management API routes."""

from typing import List

from fastapi import APIRouter, HTTPException, Request

from ..schemas import BranchCreate, BranchResponse, MergeRequest

router = APIRouter()


def _repo(request: Request):
    return request.app.state.repo


def _branch_to_response(b) -> BranchResponse:
    return BranchResponse(
        id=b.id,
        name=b.name,
        prompt_id=b.prompt_id,
        head_version_id=b.head_version_id,
        base_version_id=b.base_version_id,
        is_default=b.is_default,
        created_at=b.created_at,
        merged_at=b.merged_at,
    )


# GET /api/prompts/{id}/branches — list all branches
@router.get("/prompts/{prompt_id}/branches", response_model=List[BranchResponse])
def list_branches(prompt_id: str, request: Request):
    repo = _repo(request)
    prompt = repo.get_prompt_by_id(prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    branches = repo.list_branches(prompt_id)
    return [_branch_to_response(b) for b in branches]


# POST /api/prompts/{id}/branches — create branch
@router.post("/prompts/{prompt_id}/branches", response_model=BranchResponse, status_code=201)
def create_branch(prompt_id: str, body: BranchCreate, request: Request):
    repo = _repo(request)
    prompt = repo.get_prompt_by_id(prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    # Check for duplicate name
    existing = repo.db.get_branch(prompt_id, body.name)
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"Branch '{body.name}' already exists")
    branch = repo.create_branch(prompt_id, body.name, from_version_id=body.from_version_id)
    return _branch_to_response(branch)


# DELETE /api/prompts/{id}/branches/{name} — delete branch
@router.delete("/prompts/{prompt_id}/branches/{name}", status_code=204)
def delete_branch(prompt_id: str, name: str, request: Request):
    repo = _repo(request)
    prompt = repo.get_prompt_by_id(prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    if name == "main":
        raise HTTPException(status_code=400, detail="Cannot delete the 'main' branch")
    branch = repo.db.get_branch(prompt_id, name)
    if branch is None:
        raise HTTPException(status_code=404, detail=f"Branch '{name}' not found")
    repo.db.delete_branch(branch.id)


# POST /api/prompts/{id}/branches/{name}/checkout — set active branch
@router.post("/prompts/{prompt_id}/branches/{name}/checkout")
def checkout_branch(prompt_id: str, name: str, request: Request):
    repo = _repo(request)
    prompt = repo.get_prompt_by_id(prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    branch = repo.db.get_branch(prompt_id, name)
    if branch is None:
        raise HTTPException(status_code=404, detail=f"Branch '{name}' not found")
    repo.set_current_branch(prompt_id, name)
    return {"branch": name, "prompt_id": prompt_id}


# POST /api/prompts/{id}/branches/merge — merge branches
@router.post("/prompts/{prompt_id}/branches/merge")
def merge_branches(prompt_id: str, body: MergeRequest, request: Request):
    repo = _repo(request)
    prompt = repo.get_prompt_by_id(prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    try:
        new_version = repo.merge_branch(prompt_id, body.source, target_branch=body.target)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "merged": True,
        "source": body.source,
        "target": body.target,
        "new_version_id": new_version.id,
        "new_version_number": new_version.version_number,
    }


# GET /api/prompts/{id}/branches/current — get current branch name
@router.get("/prompts/{prompt_id}/branches/current")
def get_current_branch(prompt_id: str, request: Request):
    repo = _repo(request)
    prompt = repo.get_prompt_by_id(prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    current = repo.get_current_branch(prompt_id)
    return {"branch": current, "prompt_id": prompt_id}
