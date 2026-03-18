"""FastAPI application factory."""

from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .routes.prompts import router as prompts_router
from .routes.graph import router as graph_router
from .routes.diff import router as diff_router
from .routes.components import router as components_router
from .routes.evals import router as evals_router
from .routes.branches import router as branches_router
from ..storage.repository import PromptRepository

STATIC_DIR = Path(__file__).parent / "static"


def create_app(repo: PromptRepository) -> FastAPI:
    app = FastAPI(title="PromptView", version="0.1.0")
    app.state.repo = repo

    app.include_router(prompts_router, prefix="/api")
    app.include_router(graph_router, prefix="/api")
    app.include_router(diff_router, prefix="/api")
    app.include_router(components_router, prefix="/api")
    app.include_router(evals_router, prefix="/api")
    app.include_router(branches_router, prefix="/api")

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def index():
        return FileResponse(str(STATIC_DIR / "index.html"))

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
