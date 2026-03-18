"""Graph endpoint - nodes and edges for the UI."""

from fastapi import APIRouter, Request
from ..schemas import GraphSchema, GraphNodeSchema, GraphEdgeSchema

router = APIRouter()


@router.get("/graph", response_model=GraphSchema)
def get_graph(request: Request):
    repo = request.app.state.repo
    prompts = repo.list_prompts()

    nodes = []
    for p in prompts:
        versions = repo.list_versions(p.id)
        latest_v_num = max((v.version_number for v in versions), default=0)
        latest_content = next(
            (v.raw_content for v in versions if v.version_number == latest_v_num), ""
        )
        summary = latest_content[:80].replace("\n", " ")
        if len(latest_content) > 80:
            summary += "..."
        nodes.append(GraphNodeSchema(
            id=p.id,
            name=p.name,
            summary=summary,
            source=p.source.value,
            version_count=len(versions),
            last_modified=p.updated_at,
            file_path=p.file_path,
            line_number=p.line_number,
            tags=p.tags,
        ))

    # Build edges from prompt content cross-references
    # (detect when one prompt's variable name appears in another prompt's content)
    name_to_id = {p.name: p.id for p in prompts}
    var_to_id = {p.variable_name: p.id for p in prompts if p.variable_name}
    edges = []
    seen_edges: set[tuple] = set()

    for p in prompts:
        versions = repo.list_versions(p.id)
        latest_content = next(
            (v.raw_content for v in versions if v.version_number ==
             max((v.version_number for v in versions), default=0)), ""
        )
        for other_name, other_id in name_to_id.items():
            if other_id != p.id and other_name in latest_content:
                edge_key = (other_id, p.id)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append(GraphEdgeSchema(
                        source=other_id,
                        target=p.id,
                        type="referenced_by",
                    ))
        for var_name, other_id in var_to_id.items():
            if other_id != p.id and f"{{{var_name}}}" in latest_content:
                edge_key = (other_id, p.id)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append(GraphEdgeSchema(
                        source=other_id,
                        target=p.id,
                        type="injected_into",
                    ))

    return GraphSchema(nodes=nodes, edges=edges)
