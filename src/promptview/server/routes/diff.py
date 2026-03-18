"""Diff routes."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request
from ..schemas import DiffSchema, DiffHunkSchema

router = APIRouter()


@router.get("/diff/{prompt_id}", response_model=DiffSchema)
def get_diff(
    prompt_id: str,
    request: Request,
    v1: Optional[int] = Query(None),
    v2: Optional[int] = Query(None),
):
    repo = request.app.state.repo
    prompt = repo.get_prompt_by_id(prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    diff = repo.diff(prompt_id, old_version_number=v1, new_version_number=v2)
    if diff is None:
        raise HTTPException(status_code=404, detail="No diff available (versions may be identical)")

    return DiffSchema(
        prompt_id=diff.prompt_id,
        prompt_name=diff.prompt_name,
        old_version=diff.old_version,
        new_version=diff.new_version,
        hunks=[
            DiffHunkSchema(
                old_start=h.old_start,
                old_count=h.old_count,
                new_start=h.new_start,
                new_count=h.new_count,
                lines=h.lines,
            )
            for h in diff.hunks
        ],
        additions=diff.additions,
        deletions=diff.deletions,
    )
