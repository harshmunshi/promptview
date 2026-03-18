"""Component decomposition and regeneration routes."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class ComponentSchema(BaseModel):
    id: str
    label: str
    content: str
    position: int


class DecomposeRequest(BaseModel):
    provider: str       # "openai" | "anthropic" | "gemini"
    api_key: str
    model: Optional[str] = None
    version_id: Optional[str] = None   # decompose a specific version; defaults to latest


class UpdateComponentsRequest(BaseModel):
    """Full replacement of components list + regenerate the prompt."""
    provider: str
    api_key: str
    model: Optional[str] = None
    components: list[dict]             # [{"label": ..., "content": ...}, ...]


class AddComponentRequest(BaseModel):
    provider: str
    api_key: str
    model: Optional[str] = None
    label: str
    content: str
    position: int                      # insert at this position (0-indexed)


class DeleteComponentRequest(BaseModel):
    provider: str
    api_key: str
    model: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_llm(provider: str, api_key: str, model: Optional[str]):
    from ...llm.client import LLMClient, LLMProvider
    try:
        prov = LLMProvider(provider)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}. Use openai, anthropic, or gemini.")
    return LLMClient(provider=prov, api_key=api_key, model=model)


def _get_version(repo, prompt_id: str, version_id: Optional[str]):
    if version_id:
        v = repo.get_version(version_id)
        if v is None or v.prompt_id != prompt_id:
            raise HTTPException(status_code=404, detail="Version not found")
        return v
    v = repo.db.get_latest_version(prompt_id)
    if v is None:
        raise HTTPException(status_code=404, detail="No versions for this prompt")
    return v


def _components_to_dicts(components) -> list[dict]:
    return [{"label": c.label, "content": c.content} for c in components]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/prompts/{prompt_id}/components", response_model=list[ComponentSchema])
def get_components(prompt_id: str, request: Request, version_id: Optional[str] = None):
    """Return stored components for a prompt version (no LLM call)."""
    repo = request.app.state.repo
    version = _get_version(repo, prompt_id, version_id)
    components = repo.db.get_components(prompt_id, version.id)
    return [ComponentSchema(id=c.id, label=c.label, content=c.content, position=c.position)
            for c in components]


@router.post("/prompts/{prompt_id}/decompose", response_model=list[ComponentSchema])
def decompose_prompt(prompt_id: str, body: DecomposeRequest, request: Request):
    """
    Use an LLM to decompose a prompt into labeled components.
    Stores the result and returns it. Safe to call multiple times.
    """
    repo = request.app.state.repo
    prompt = repo.get_prompt_by_id(prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    version = _get_version(repo, prompt_id, body.version_id)
    llm = _make_llm(body.provider, body.api_key, body.model)

    from ...llm.decomposer import decompose, components_to_models
    try:
        raw_components = decompose(llm, version.raw_content)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    models = components_to_models(raw_components, prompt_id, version.id)
    repo.db.upsert_components(models)

    return [ComponentSchema(id=c.id, label=c.label, content=c.content, position=c.position)
            for c in models]


@router.post("/prompts/{prompt_id}/components/add", response_model=dict)
def add_component(prompt_id: str, body: AddComponentRequest, request: Request):
    """
    Insert a new component at `position`, shift others down, regenerate the prompt,
    and create a new PromptVersion.
    """
    repo = request.app.state.repo
    prompt = repo.get_prompt_by_id(prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    version = _get_version(repo, prompt_id, None)
    existing = repo.db.get_components(prompt_id, version.id)

    # Build updated component list
    comp_dicts = _components_to_dicts(existing)
    new_comp = {"label": body.label, "content": body.content}
    pos = max(0, min(body.position, len(comp_dicts)))
    comp_dicts.insert(pos, new_comp)

    return _apply_component_change(repo, prompt, version, comp_dicts, body.provider, body.api_key, body.model)


@router.delete("/prompts/{prompt_id}/components/{component_id}", response_model=dict)
def delete_component(prompt_id: str, component_id: str, body: DeleteComponentRequest, request: Request):
    """
    Remove a component, regenerate the prompt, and create a new PromptVersion.
    """
    repo = request.app.state.repo
    prompt = repo.get_prompt_by_id(prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    version = _get_version(repo, prompt_id, None)
    existing = repo.db.get_components(prompt_id, version.id)

    comp_dicts = [{"label": c.label, "content": c.content}
                  for c in existing if c.id != component_id]

    if len(comp_dicts) == len(existing):
        raise HTTPException(status_code=404, detail="Component not found")

    return _apply_component_change(repo, prompt, version, comp_dicts, body.provider, body.api_key, body.model)


@router.put("/prompts/{prompt_id}/components", response_model=dict)
def update_components(prompt_id: str, body: UpdateComponentsRequest, request: Request):
    """
    Replace all components (after inline edits), regenerate the prompt,
    and create a new PromptVersion.
    """
    repo = request.app.state.repo
    prompt = repo.get_prompt_by_id(prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    version = _get_version(repo, prompt_id, None)
    return _apply_component_change(repo, prompt, version, body.components, body.provider, body.api_key, body.model)


# ── Shared mutation logic ──────────────────────────────────────────────────────

def _apply_component_change(repo, prompt, old_version, comp_dicts: list[dict],
                             provider: str, api_key: str, model: Optional[str]) -> dict:
    """Regenerate prompt from components, save new version, stage it."""
    if not comp_dicts:
        raise HTTPException(status_code=400, detail="Cannot have zero components")

    llm = _make_llm(provider, api_key, model)

    # Load old components so the LLM can make surgical edits to the original text
    old_comps = repo.db.get_components(prompt.id, old_version.id)
    old_comp_dicts = [{"label": c.label, "content": c.content} for c in old_comps]

    from ...llm.decomposer import regenerate, components_to_models
    try:
        new_content = regenerate(
            llm,
            comp_dicts,
            original_content=old_version.raw_content,
            old_components=old_comp_dicts if old_comp_dicts else None,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error during regeneration: {e}")

    # Create new PromptVersion
    new_version = repo.update_prompt_content(prompt.id, new_content)

    # Store components linked to new version
    models = components_to_models(comp_dicts, prompt.id, new_version.id)
    repo.db.upsert_components(models)

    # Auto-stage
    repo.stage(prompt.id, prompt.name, new_version.id, "modified")

    return {
        "version_id": new_version.id,
        "version_number": new_version.version_number,
        "new_content": new_content,
        "components": [
            {"id": c.id, "label": c.label, "content": c.content, "position": c.position}
            for c in models
        ],
    }
